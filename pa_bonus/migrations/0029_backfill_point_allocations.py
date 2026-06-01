"""
Data migration: materialise expiry dates on existing credits and reconstruct the
point allocations that historical debits implied.

Before this change points were a single signed ledger with no record of which
credit a reward claim or credit note actually drew from. This migration:

  1. Backfills expires_at on every confirmed positive credit, computed from its
     brand's validity window and the credit's real grant date (per the chosen
     "backfill real expiry" policy).
  2. Reconstructs PointAllocation rows by replaying every confirmed debit, oldest
     first, against confirmed credits using the live rule (soonest-to-expire
     first), so each credit's remaining balance reflects reality and the total
     confirmed balance is unchanged.

It deliberately does NOT expire anything. After this runs, review what would be
removed with `python manage.py expire_points --dry-run` before expiring for real.
"""
from django.db import migrations
from dateutil.relativedelta import relativedelta


def _expiry_for(brand, grant_date):
    """End-of-month expiry, brand.points_validity_months after grant_date."""
    if not brand or not brand.points_validity_months:
        return None
    target = grant_date + relativedelta(months=brand.points_validity_months)
    return target + relativedelta(day=31)


def backfill(apps, schema_editor):
    PointsTransaction = apps.get_model('pa_bonus', 'PointsTransaction')
    PointAllocation = apps.get_model('pa_bonus', 'PointAllocation')

    # 1. Backfill expiry dates on confirmed credits that don't have one yet.
    credits_to_date = (
        PointsTransaction.objects
        .filter(status='CONFIRMED', value__gt=0, expires_at__isnull=True,
                brand__isnull=False)
        .select_related('brand')
    )
    for credit in credits_to_date:
        expiry = _expiry_for(credit.brand, credit.date)
        if expiry is not None:
            credit.expires_at = expiry
            credit.save(update_fields=['expires_at'])

    # 2. Reconstruct allocations per user.
    user_ids = (
        PointsTransaction.objects
        .filter(status='CONFIRMED')
        .values_list('user_id', flat=True)
        .distinct()
    )

    def credit_sort_key(c):
        # soonest-to-expire first; never-expiring (None) last; then oldest grant.
        return (c.expires_at is None, c.expires_at, c.date, c.id)

    for user_id in user_ids:
        credits = list(
            PointsTransaction.objects.filter(
                user_id=user_id, status='CONFIRMED', value__gt=0
            )
        )
        credits.sort(key=credit_sort_key)

        # Track remaining points per credit as we consume them.
        remaining = {c.id: c.value for c in credits}

        debits = list(
            PointsTransaction.objects.filter(
                user_id=user_id, status='CONFIRMED', value__lt=0
            ).order_by('date', 'id')
        )

        new_allocations = []
        for debit in debits:
            need = -debit.value
            for credit in credits:
                if need <= 0:
                    break
                avail = remaining[credit.id]
                if avail <= 0:
                    continue
                take = min(avail, need)
                new_allocations.append(
                    PointAllocation(credit_id=credit.id, debit_id=debit.id, amount=take)
                )
                remaining[credit.id] -= take
                need -= take
            # If need > 0 the user was historically over-drawn; leave it
            # unallocated so the negative balance stays visible.

        PointAllocation.objects.bulk_create(new_allocations)


def unbackfill(apps, schema_editor):
    PointsTransaction = apps.get_model('pa_bonus', 'PointsTransaction')
    PointAllocation = apps.get_model('pa_bonus', 'PointAllocation')
    PointAllocation.objects.all().delete()
    PointsTransaction.objects.filter(expires_at__isnull=False).update(expires_at=None)


class Migration(migrations.Migration):

    dependencies = [
        ('pa_bonus', '0028_brand_points_validity_months_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill, unbackfill),
    ]
