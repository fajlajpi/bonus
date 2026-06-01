"""
Management command to expire points whose validity window has passed.

Run with --dry-run first (especially the very first time, after backfilling
expiry dates onto historical points) to review exactly what would expire before
any balances are touched:

    python manage.py expire_points --dry-run

Then run for real:

    python manage.py expire_points
"""
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.utils import timezone

from pa_bonus.services.points import expire_credits


class Command(BaseCommand):
    help = "Expire the remaining points of credits past their expiry date."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Report what would expire without writing anything.",
        )
        parser.add_argument(
            '--as-of', type=str, default=None,
            help="Expire points due on or before this date (YYYY-MM-DD). "
                 "Defaults to today.",
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        as_of = options['as_of']
        if as_of:
            as_of = timezone.datetime.strptime(as_of, '%Y-%m-%d').date()

        expired = expire_credits(as_of=as_of, dry_run=dry_run)

        if not expired:
            self.stdout.write(self.style.SUCCESS("Nothing to expire."))
            return

        # Summarise per user so the dry-run report is easy to scan.
        per_user = defaultdict(lambda: [0, 0])  # user -> [credit_count, points]
        for credit, points in expired:
            bucket = per_user[credit.user]
            bucket[0] += 1
            bucket[1] += points

        total_points = sum(points for _, points in expired)
        verb = "Would expire" if dry_run else "Expired"

        self.stdout.write(
            f"{verb} {total_points} points across {len(expired)} credits "
            f"for {len(per_user)} users:"
        )
        for user, (count, points) in sorted(
            per_user.items(), key=lambda kv: kv[1][1], reverse=True
        ):
            self.stdout.write(
                f"  {user.user_number or user.username}: "
                f"{points} points from {count} credit(s)"
            )

        style = self.style.WARNING if dry_run else self.style.SUCCESS
        self.stdout.write(style(
            f"{verb} {total_points} points."
            + (" (dry run, nothing written)" if dry_run else "")
        ))
