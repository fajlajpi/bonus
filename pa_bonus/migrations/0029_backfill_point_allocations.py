"""
Data migration: reconstruct the point allocations that historical debits implied.

Before this change points were a single signed ledger with no record of which
credit a reward claim or credit note actually drew from. This migration replays
every confirmed debit, oldest first, against confirmed credits using the live
rule (soonest-to-expire first), creating one PointAllocation row per draw so each
credit's remaining balance reflects reality. The total confirmed balance is
unchanged.

Expiry dates are NOT set here. Because they depend on each brand's policy (which
you may set or change over time), stamping them lives in the re-runnable
`backfill_point_expiry` management command instead. Run that after setting brand
policies, then review `expire_points --dry-run` before expiring for real.
"""
from django.db import migrations


def reconstruct(apps, schema_editor):
    PointsTransaction = apps.get_model('pa_bonus', 'PointsTransaction')
    PointAllocation = apps.get_model('pa_bonus', 'PointAllocation')

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


def unreconstruct(apps, schema_editor):
    PointAllocation = apps.get_model('pa_bonus', 'PointAllocation')
    PointAllocation.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('pa_bonus', '0028_brand_points_validity_months_and_more'),
    ]

    operations = [
        migrations.RunPython(reconstruct, unreconstruct),
    ]
