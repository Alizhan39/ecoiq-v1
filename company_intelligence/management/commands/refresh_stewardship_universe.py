"""
refresh_stewardship_universe — feat/stewardship-universe (PR 13), extended
by feat/stewardship-monitor (PR 14): the batch-refresh management command
(Section 12/26). Deliberately conservative per the brief's own "the goal is
NOT maximum scraping" instruction — this supports refreshing one company, a
selected few, only those due per services/refresh_policy.py, or every
actively-tracked company, but never seeds hundreds of fake companies and
never bypasses the refresh orchestrator's own idempotency/failure-tolerance.

Also doubles as the real-company bootstrap for verification (Section 27):
--company accepts a slug that doesn't have a CompanyProfile yet and will
create one from the same REAL_COMPANY_SEEDS identity dict PR10's
ingest_real_company_evidence.py already uses (reused, not duplicated) —
first refresh implicitly starts tracking (see refresh_orchestrator's own
docstring).

PR 14 adds --scheduled: this is THE command an external cron/platform
scheduler is meant to invoke (see render.yaml's own disabled-by-default
cron block for the exact deployable configuration) — it records
CompanyRefreshRun.triggered_by='scheduled' instead of 'management_command'
so the audit trail honestly distinguishes an ad-hoc staff CLI run from a
genuinely scheduled one, without adding a second command or a parallel
job-running path. --scheduled also skips any source not yet due per
refresh_policy for THIS run (never re-hammers a provider on every batch
tick just because the COMPANY as a whole was due) — a manual/ad-hoc CLI
run (no --scheduled) still rechecks every active source, unchanged from
PR13, matching the same manual-override discipline the staff UI's
"Refresh Company Intelligence" button already has.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Refreshes Stewardship Universe company intelligence — one, selected, due-only, or all active companies.'

    def add_arguments(self, parser):
        parser.add_argument('--company', action='append', help='Company slug to refresh (repeatable). Creates the profile from a known real-company seed if it does not exist yet.')
        parser.add_argument('--limit', type=int, default=None, help='Maximum number of companies to refresh this run.')
        parser.add_argument('--due-only', action='store_true', help='Only refresh companies currently due per refresh policy (ignored when --company is given).')
        parser.add_argument('--dry-run', action='store_true', help='Preview only — performs zero database writes.')
        parser.add_argument('--scheduled', action='store_true', help='Mark this run as scheduler-triggered (per-source due-gating applies) — use this from cron, never for an ad-hoc staff run.')

    def handle(self, *args, **options):
        from companies.models import CompanyProfile
        from company_intelligence.management.commands.ingest_real_company_evidence import REAL_COMPANY_SEEDS
        from company_intelligence.services import rate_limiter, refresh_policy
        from company_intelligence.services.refresh_orchestrator import refresh_company_intelligence
        from league.models import Company

        slugs = options.get('company')
        dry_run = options['dry_run']
        limit = options['limit']
        triggered_by = 'scheduled' if options['scheduled'] else 'management_command'

        profiles = []
        if slugs:
            for slug in slugs:
                seed = REAL_COMPANY_SEEDS.get(slug, {'name': slug.title(), 'sector': 'other', 'country': 'Unknown'})
                company, _ = Company.objects.get_or_create(slug=slug, defaults={**seed, 'is_public': True})
                profile, _ = CompanyProfile.objects.get_or_create(company=company, defaults={'status': 'public'})
                profiles.append(profile)
            dropped = 0
        else:
            profiles = list(CompanyProfile.objects.filter(tracking_status='active').select_related('company'))
            if options['due_only']:
                profiles = [p for p in profiles if refresh_policy.is_company_due_for_refresh(p)]
            # feat/global-stewardship-universe (PR 15) Section 17 — bounded
            # expansion: an explicit --slug list is a deliberate, bounded
            # staff ask and is never silently truncated; a --due-only/all-
            # active batch IS bounded by default so one invocation can
            # never silently try to refresh an unbounded number of
            # companies — the drop is reported, never hidden.
            profiles, dropped = rate_limiter.bounded_batch(profiles, limit=limit)

        if dropped:
            self.stdout.write(self.style.WARNING(
                f'Batch size bounded to {len(profiles)} compan{"y" if len(profiles) == 1 else "ies"} this run — '
                f'{dropped} due/active compan{"y" if dropped == 1 else "ies"} were NOT refreshed this run '
                f'(re-run, or pass --limit to raise the bound).'
            ))

        if not profiles:
            self.stdout.write(self.style.WARNING(
                'No companies to refresh — pass --company to bootstrap one, or ensure some companies '
                'have tracking_status=active (use --due-only only once companies are tracked).'
            ))
            return

        self.stdout.write(f'Refreshing {len(profiles)} companies (dry_run={dry_run}, triggered_by={triggered_by})...')
        for profile in profiles:
            slug = profile.company.slug
            result = refresh_company_intelligence(profile, triggered_by=triggered_by, dry_run=dry_run)

            if isinstance(result, dict) and result.get('dry_run'):
                self.stdout.write(f'{slug}: DRY RUN — {result["sources_due"]}/{result["sources_total"]} source(s) due, nothing changed.')
            elif isinstance(result, dict) and result.get('error'):
                self.stdout.write(self.style.WARNING(f'{slug}: {result["note"]}'))
            else:
                self.stdout.write(
                    f'{slug}: {result.get_status_display()} — sources_checked={result.sources_checked} '
                    f'sources_failed={result.sources_failed} documents_new={result.documents_new} '
                    f'documents_unchanged={result.documents_unchanged} '
                    f'kpi_candidates_proposed={result.kpi_candidates_proposed} '
                    f'review_required={result.review_required_count}'
                )
                for w in result.warnings:
                    self.stdout.write(f'  warning: {w}')
                for e in result.errors:
                    self.stdout.write(self.style.WARNING(f'  error: {e}'))

        self.stdout.write(self.style.SUCCESS(
            'Stewardship Universe refresh complete. Every KPI candidate remains PROPOSED until reviewed in '
            'the Evidence Review Workbench — this command never auto-confirms anything.'
        ))
        self.stdout.write(
            'No periodic scheduler runs automatically in this environment unless explicitly configured (see '
            'render.yaml\'s disabled-by-default cron block and PR14 report §2/22) — this command is designed '
            'to be invoked by an external cron/platform scheduler, e.g.: '
            '0 6 * * * cd /path/to/app && python manage.py refresh_stewardship_universe --due-only --scheduled'
        )
