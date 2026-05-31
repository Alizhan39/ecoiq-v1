"""
run_ecoiq_maintenance — Consolidated maintenance runner for EcoIQ.

Replaces multiple separate cron jobs with a single idempotent command
that can be scheduled once on Render (or run manually).

Usage:
    python manage.py run_ecoiq_maintenance --daily
    python manage.py run_ecoiq_maintenance --weekly
    python manage.py run_ecoiq_maintenance --ml
    python manage.py run_ecoiq_maintenance --all

Flags:
    --daily   Archive stale profiles, fix placeholder summaries, log counts
    --weekly  Re-run focus_target_markets (top-up + archive non-target),
              re-run seed_score_history (trend chart data)
    --ml      Re-run anomaly detection + cluster labelling (if ML deps present)
    --all     Run all of the above in order

This command is idempotent — safe to run repeatedly.
"""
import time
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Consolidated EcoIQ maintenance runner (daily/weekly/ml tasks).'

    def add_arguments(self, parser):
        parser.add_argument('--daily',  action='store_true', help='Run daily maintenance tasks')
        parser.add_argument('--weekly', action='store_true', help='Run weekly maintenance tasks')
        parser.add_argument('--ml',     action='store_true', help='Re-run ML scoring (anomaly + cluster)')
        parser.add_argument('--all',    action='store_true', help='Run all maintenance tasks')

    def handle(self, *args, **options):
        run_daily  = options['daily']  or options['all']
        run_weekly = options['weekly'] or options['all']
        run_ml     = options['ml']     or options['all']

        if not (run_daily or run_weekly or run_ml):
            self.stdout.write(self.style.WARNING(
                'No flag specified. Use --daily, --weekly, --ml, or --all.'
            ))
            return

        start = time.time()
        self.stdout.write(self.style.MIGRATE_HEADING('=== EcoIQ Maintenance Runner ==='))

        # ── Daily tasks ────────────────────────────────────────────────────────
        if run_daily:
            self.stdout.write(self.style.MIGRATE_HEADING('\n── Daily: placeholder check ──'))
            try:
                call_command('check_public_placeholders', verbosity=1)
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f'  check_public_placeholders skipped: {exc}'))

            self.stdout.write(self.style.MIGRATE_HEADING('\n── Daily: profile counts ──'))
            try:
                from companies.models import CompanyProfile
                from collections import Counter

                dist = Counter(
                    p.company.country
                    for p in CompanyProfile.objects.filter(
                        status__in=('public', 'verified')
                    ).select_related('company')
                )
                self.stdout.write('  Public/Verified distribution:')
                for country, count in sorted(dist.items(), key=lambda x: -x[1])[:10]:
                    self.stdout.write(f'    {country:<32s} {count:>4d}')
                self.stdout.write(
                    self.style.SUCCESS(f'  Total public: {sum(dist.values())}')
                )
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f'  Profile count skipped: {exc}'))

        # ── Weekly tasks ───────────────────────────────────────────────────────
        if run_weekly:
            self.stdout.write(self.style.MIGRATE_HEADING(
                '\n── Weekly: focus_target_markets ──'
            ))
            try:
                call_command('focus_target_markets', verbosity=1)
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f'  focus_target_markets failed: {exc}'))

            self.stdout.write(self.style.MIGRATE_HEADING(
                '\n── Weekly: seed_score_history ──'
            ))
            try:
                call_command('seed_score_history', verbosity=1)
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f'  seed_score_history skipped: {exc}'))

        # ── ML tasks ──────────────────────────────────────────────────────────
        if run_ml:
            self.stdout.write(self.style.MIGRATE_HEADING('\n── ML: anomaly detection ──'))
            try:
                call_command('run_anomaly_detection', verbosity=1)
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f'  run_anomaly_detection skipped: {exc}'))

            self.stdout.write(self.style.MIGRATE_HEADING('\n── ML: cluster labelling ──'))
            try:
                call_command('run_clustering', verbosity=1)
            except Exception as exc:
                self.stdout.write(self.style.WARNING(f'  run_clustering skipped: {exc}'))

        elapsed = round(time.time() - start, 1)
        self.stdout.write(self.style.SUCCESS(
            f'\n=== Maintenance complete in {elapsed}s ==='
        ))
