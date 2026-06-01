"""
Management command to (re)stamp expiry dates on existing point credits.

Each confirmed positive credit's expiry is computed from its brand's
points_validity_months and the credit's grant date. This is safe to run as often
as you like:

  * By default it only fills credits that have no expiry yet, so adding a policy
    to a brand and re-running picks up that brand's historical points without
    touching anything already stamped.
  * Use --overwrite to recompute every credit's expiry from the current brand
    policy (e.g. after changing a brand's window). Credits whose brand has no
    policy are cleared back to "never expires".

    python manage.py backfill_point_expiry --dry-run
    python manage.py backfill_point_expiry
    python manage.py backfill_point_expiry --overwrite
"""
from django.core.management.base import BaseCommand

from pa_bonus.models import PointsTransaction


class Command(BaseCommand):
    help = "Compute and store expiry dates on existing point credits from brand policy."

    def add_arguments(self, parser):
        parser.add_argument(
            '--overwrite', action='store_true',
            help="Recompute expiry for every credit, even ones already stamped.",
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Report what would change without writing anything.",
        )

    def handle(self, *args, **options):
        overwrite = options['overwrite']
        dry_run = options['dry_run']

        credits = (
            PointsTransaction.objects
            .filter(status='CONFIRMED', value__gt=0, brand__isnull=False)
            .select_related('brand')
        )
        if not overwrite:
            credits = credits.filter(expires_at__isnull=True)

        changed = 0
        for credit in credits:
            new_expiry = credit.brand.expiry_for(credit.date)
            if new_expiry == credit.expires_at:
                continue
            changed += 1
            if not dry_run:
                credit.expires_at = new_expiry
                credit.save(update_fields=['expires_at'])

        verb = "Would update" if dry_run else "Updated"
        style = self.style.WARNING if dry_run else self.style.SUCCESS
        self.stdout.write(style(
            f"{verb} expiry on {changed} credit(s)"
            + (" (dry run, nothing written)." if dry_run else ".")
        ))
