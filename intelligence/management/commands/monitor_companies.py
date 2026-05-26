"""
Management command: python manage.py monitor_companies

Runs the full autonomous intelligence cycle:
  1. Check MonitorWatch targets for content changes
  2. Trigger ingestion pipeline for changed company websites
  3. Recompute CountryIntelligence aggregates
  4. Sync strategic signals from AIFinding records
  5. Generate IntelligenceAlerts for score anomalies

Schedule via Render/Railway cron or system crontab:
  0 3 * * * /path/to/venv/bin/python manage.py monitor_companies

Options:
  --dry-run         Print what would be done without writing to DB
  --company <slug>  Run only for one company
  --step <name>     Run only one step (monitor|country|signals|alerts|briefing)
"""
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone

log = logging.getLogger('intelligence.monitor')


class Command(BaseCommand):
    help = 'Autonomous environmental intelligence monitoring cycle'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Print actions without writing to DB')
        parser.add_argument('--company', type=str, default='',
                            help='Limit to one company slug')
        parser.add_argument('--step', type=str, default='all',
                            choices=['all','monitor','country','signals','alerts','briefing'],
                            help='Run only a specific step')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        company_slug = options['company']
        step = options['step']

        self.stdout.write(self.style.SUCCESS(
            f'\n[EcoIQ Monitor] Starting cycle — {timezone.now():%Y-%m-%d %H:%M} UTC'
            + (' [DRY RUN]' if dry_run else '')
        ))

        if step in ('all', 'monitor'):
            self._step_monitor(dry_run, company_slug)

        if step in ('all', 'country'):
            self._step_country(dry_run)

        if step in ('all', 'signals'):
            self._step_signals(dry_run)

        if step in ('all', 'alerts'):
            self._step_alerts(dry_run, company_slug)

        if step in ('briefing',):
            self._step_briefings(dry_run, company_slug)

        self.stdout.write(self.style.SUCCESS(
            f'[EcoIQ Monitor] Cycle complete — {timezone.now():%H:%M:%S} UTC\n'
        ))

    def _step_monitor(self, dry_run, company_slug):
        """Check MonitorWatch targets for content changes."""
        from intelligence.models import MonitorWatch
        from intelligence.compute import check_monitor_target

        qs = MonitorWatch.objects.filter(is_active=True).select_related('company')
        if company_slug:
            qs = qs.filter(company__slug=company_slug)

        due = [w for w in qs if w.is_due]
        self.stdout.write(f'  [monitor] {len(due)} targets due for check')

        changes = 0
        ingestions_triggered = 0

        for watch in due:
            self.stdout.write(f'    checking: {watch.company.name} → {watch.url[:60]}')
            if dry_run:
                continue
            changed = check_monitor_target(watch)
            if changed:
                changes += 1
                self.stdout.write(
                    self.style.WARNING(f'    ⚡ Change detected: {watch.company.name}')
                )
                # Trigger ingestion pipeline for the company
                if not MonitorWatch.objects.filter(
                    pk=watch.pk, ingestion_triggered=True
                ).exists():
                    try:
                        from ingestion.models import IngestionJob
                        from ingestion.pipeline import run_pipeline_in_thread
                        job = IngestionJob.objects.create(
                            company_name=watch.company.name
                        )
                        run_pipeline_in_thread(job.pk)
                        MonitorWatch.objects.filter(pk=watch.pk).update(
                            ingestion_triggered=True
                        )
                        ingestions_triggered += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'    → Ingestion job #{job.pk} started')
                        )
                    except Exception as exc:
                        self.stdout.write(
                            self.style.ERROR(f'    ✗ Ingestion failed: {exc}')
                        )

        self.stdout.write(
            f'  [monitor] {changes} changes, {ingestions_triggered} ingestions triggered'
        )

    def _step_country(self, dry_run):
        """Recompute CountryIntelligence aggregates."""
        from intelligence.compute import compute_country_intelligence

        self.stdout.write('  [country] Computing national intelligence…')
        if not dry_run:
            updated = compute_country_intelligence()
            self.stdout.write(
                self.style.SUCCESS(f'  [country] Updated {len(updated)} countries')
            )
        else:
            from league.models import Company
            countries = set(Company.objects.values_list('country', flat=True))
            self.stdout.write(f'  [country] Would update {len(countries)} countries')

    def _step_signals(self, dry_run):
        """Sync strategic signals from AIFinding records."""
        from intelligence.compute import sync_strategic_signals_from_audit

        self.stdout.write('  [signals] Syncing strategic signals from audit findings…')
        if not dry_run:
            count = sync_strategic_signals_from_audit()
            self.stdout.write(
                self.style.SUCCESS(f'  [signals] Created {count} new strategic signals')
            )
        else:
            from audit.models import AIFinding
            count = AIFinding.objects.filter(status='approved').count()
            self.stdout.write(f'  [signals] Would scan {count} approved findings')

    def _step_alerts(self, dry_run, company_slug):
        """Generate intelligence alerts for score anomalies."""
        from league.models import Company, ScoreHistory
        from intelligence.compute import generate_alerts_for_company
        from datetime import date, timedelta

        self.stdout.write('  [alerts] Scanning for score anomalies…')

        qs = Company.objects.all()
        if company_slug:
            qs = qs.filter(slug=company_slug)

        total_alerts = 0
        cutoff = date.today() - timedelta(days=35)

        for company in qs:
            # Compare current score against 30-day snapshot
            old_snap = ScoreHistory.objects.filter(
                company=company, date__lte=cutoff
            ).order_by('-date').first()

            prev_score = float(old_snap.ecoiq_score) if old_snap else None

            if not dry_run:
                alerts = generate_alerts_for_company(company, prev_score)
                total_alerts += len(alerts)
                for a in alerts:
                    self.stdout.write(
                        self.style.WARNING(f'    ⚠ {a.severity.upper()}: {a.title}')
                    )
            else:
                if prev_score and abs(float(company.ecoiq_score) - prev_score) >= 5:
                    self.stdout.write(
                        f'    Would alert: {company.name} '
                        f'({prev_score:.1f} → {company.ecoiq_score})'
                    )

        self.stdout.write(
            self.style.SUCCESS(f'  [alerts] {total_alerts} new alerts generated')
        )

    def _step_briefings(self, dry_run, company_slug):
        """Generate AI executive briefings."""
        from league.models import Company
        from intelligence.compute import generate_executive_briefing
        from django.conf import settings

        if not settings.ANTHROPIC_API_KEY:
            self.stdout.write(self.style.WARNING('  [briefing] No ANTHROPIC_API_KEY — skipping'))
            return

        self.stdout.write('  [briefing] Generating executive briefings…')

        qs = Company.objects.filter(verified=True)
        if company_slug:
            qs = qs.filter(slug=company_slug)

        for company in qs[:10]:  # cap at 10 per run to control API costs
            self.stdout.write(f'    briefing: {company.name}')
            if not dry_run:
                b = generate_executive_briefing(company)
                if b:
                    self.stdout.write(
                        self.style.SUCCESS(f'    ✓ Briefing created: {b.headline[:60]}')
                    )
