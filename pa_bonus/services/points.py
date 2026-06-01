"""
Points allocation engine
=========================
Central, auditable logic for moving points between credits and debits.

Every reward claim, credit note and expiration is a negative PointsTransaction
(a "debit"). This module is the single place that decides which positive
transactions (credits) a debit draws its points from, recording each draw as a
PointAllocation row. The rule is FIFO by soonest-to-expire: points closest to
expiring are spent first, so customers lose as few points to expiry as possible.

Because allocations are explicit rows, a credit's remaining balance is always
derived (never an overwritten counter), and cancelling a debit simply deletes
its allocations to restore the points it had drawn.

Usage:
    from pa_bonus.services.points import allocate_debit, void_debit, expire_credits

    debit = PointsTransaction.objects.create(..., value=-500, ...)
    allocate_debit(debit)
"""
import logging

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from pa_bonus.models import PointsTransaction, PointAllocation

logger = logging.getLogger(__name__)


def _candidate_credits(user, exclude_pk=None):
    """
    Confirmed, positive transactions for a user, ordered soonest-to-expire first.

    Never-expiring credits (expires_at is null) sort last, so points with a
    deadline are always spent before points that keep indefinitely. Ties break by
    grant date then id for a stable, oldest-first order.
    """
    qs = (
        PointsTransaction.objects
        .filter(user=user, status='CONFIRMED', value__gt=0)
        .order_by(F('expires_at').asc(nulls_last=True), 'date', 'id')
    )
    if exclude_pk is not None:
        qs = qs.exclude(pk=exclude_pk)
    return qs


@transaction.atomic
def allocate_debit(debit):
    """
    Allocate a debit against the user's confirmed credits, soonest-to-expire first.

    Any pre-existing allocations on the debit are cleared first, so this is safe to
    call again after the debit's value changes (re-allocation). If the user does not
    have enough available points to cover the debit (e.g. a credit note larger than
    the balance), the debit is left partially allocated on purpose: the shortfall
    surfaces as a negative balance so the discrepancy gets noticed.

    Args:
        debit (PointsTransaction): A negative transaction to allocate. Locked with
            its candidate credits for the duration of the transaction.

    Returns:
        int: The number of points actually allocated (may be less than the debit's
            magnitude if the user ran short).
    """
    if debit.value >= 0:
        raise ValueError("allocate_debit requires a negative (debit) transaction")

    # Clear any prior allocations so re-allocation starts from a clean slate.
    debit.allocations_in.all().delete()

    need = -debit.value
    allocations = []

    # Lock the candidate credits so two concurrent debits can't double-spend a lot.
    credits = _candidate_credits(debit.user, exclude_pk=debit.pk).select_for_update()
    for credit in credits:
        if need <= 0:
            break
        remaining = credit.remaining
        if remaining <= 0:
            continue
        take = min(remaining, need)
        allocations.append(
            PointAllocation(credit=credit, debit=debit, amount=take)
        )
        need -= take

    PointAllocation.objects.bulk_create(allocations)

    allocated = (-debit.value) - need
    if need > 0:
        logger.warning(
            "Debit #%s for user %s under-allocated by %s points "
            "(balance went negative).",
            debit.pk, debit.user_id, need,
        )
    return allocated


@transaction.atomic
def void_debit(debit):
    """
    Cancel a debit and return the points it had drawn back to their credits.

    Deleting the allocations restores each source credit's remaining balance
    automatically. The debit row itself is kept (status CANCELLED) as an audit
    trail of the event.

    Args:
        debit (PointsTransaction): The debit to cancel.
    """
    debit.allocations_in.all().delete()
    if debit.status != 'CANCELLED':
        debit.status = 'CANCELLED'
        debit.save(update_fields=['status'])


@transaction.atomic
def expire_credits(as_of=None, dry_run=False):
    """
    Expire the remaining points of every confirmed credit past its expiry date.

    Each expiring credit gets one EXPIRATION debit for its remaining points, with a
    single allocation linking the two, so an expired point is just as traceable as a
    spent one. Credits with nothing left, or no expiry, are skipped. The operation
    is idempotent: running it twice does not double-expire anything.

    Args:
        as_of (date | None): Treat credits as expired on or before this date.
            Defaults to today.
        dry_run (bool): If True, compute what would expire but write nothing.

    Returns:
        list[tuple[PointsTransaction, int]]: (credit, points_expired) for each
            credit that expired (or would expire, under dry_run).
    """
    as_of = as_of or timezone.now().date()
    expired = []

    credits = (
        PointsTransaction.objects
        .filter(
            status='CONFIRMED', value__gt=0,
            expires_at__isnull=False, expires_at__lte=as_of,
        )
        .select_for_update()
    )
    for credit in credits:
        remaining = credit.remaining
        if remaining <= 0:
            continue
        expired.append((credit, remaining))
        if dry_run:
            continue
        debit = PointsTransaction.objects.create(
            user=credit.user,
            value=-remaining,
            date=credit.expires_at,
            description=f"Points expired (granted {credit.date})",
            type='EXPIRATION',
            status='CONFIRMED',
            brand=credit.brand,
        )
        PointAllocation.objects.create(credit=credit, debit=debit, amount=remaining)

    return expired
