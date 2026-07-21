"""
refresh_stewardship_universe — feat/stewardship-universe (PR 13): the
batch-refresh management command (Section 12/26). Deliberately conservative
per the brief's own "the goal is NOT maximum scraping" instruction — this
supports refreshing one company, a selected few, only those due per
services/refresh_policy.py, or every actively-tracked company, but never
seeds hundreds of fake companies and never bypasses the refresh
orchestrator's own idempotency/failure-tolerance.

Also doubles as the real-company bootstrap for verification (Section 27):
--company accepts a slug that doesn't have a CompanyProfile yet and will
create one from the same REAL_COMPANY_SEEDS identity dict PR10's
ingest_real_company_evidence.py already uses (reused, not duplicated) —
first refresh implicitly starts tracking (see refresh_orchestrator's own
docstring).
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Refreshes Stewardship Universe company intelligence — one, selected, due-only, or all active companies.'

    def add_arguments(self, parser):
        parser.add_argument('--company', action='append', help='Company slug to refresh (repeatable). Creates the profile from a known real-company seed if it does not exist yet.')
        parser.add_argument('--limit', type=int, default=None, help='Maximum number of companies to refresh this run.')
        parser.add_argument('--due-only', action='store_true', help='Only refresh companies currently due per refresh policy (ignored when --company is given).')
        parser.add_argument('--dry-run', action='store_true', help='Preview only — performs zero database writes.')

    def handle(self, *args, **options):
        from companies.models import CompanyProfile
        from company_intelligence.management.commands.ingest_real_company_evidence import REAL_COMPANY_SEEDS
        from company_intelligence.services import refresh_policy
        from company_intelligence.services.refresh_orchestrator import refresh_company_intelligence
        from league.models import Company

        slugs = options.get('company')
        dry_run = options['dry_run']
        limit = options['limit']

        profiles = []
        if slugs:
            for slug in slugs:
                seed = REAL_COMPANY_SEEDS.get(slug, {'name': slug.title(), 'sector': 'other', 'country': 'Unknown'})
                company, _ = Company.objects.get_or_create(slug=slug, defaults={**seed, 'is_public': True})
                profile, _ = CompanyProfile.objects.get_or_create(company=company, defaults={'status': 'public'})
                profiles.append(profile)
        else:
            profiles = list(CompanyProfile.objects.filter(tracking_status='active').select_related('company'))
            if options['due_only']:
                profiles = [p for p in profiles if refresh_policy.is_company_due_for_refresh(p)]

        if limit is not None:
            profiles = profiles[:limit]

        if not profiles:
            self.stdout.write(self.style.WARNING(
                'No companies to refresh — pass --company to bootstrap one, or ensure some companies '
                'have tracking_status=active (use --due-only only once companies are tracked).'
            ))
            return

        self.stdout.write(f'Refreshing {len(profiles)} companies (dry_run={dry_run})...')
        for profile in profiles:
            slug = profile.company.slug
            result = refresh_company_intelligence(profile, triggered_by='management_command', dry_run=dry_run)

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
            'No periodic scheduler is wired into this repo (see PR13 report §22) — run this command via an '
            'external cron/platform scheduler, e.g.: '
            '0 6 * * * cd /path/to/app && python manage.py refresh_stewardship_universe --due-only'
        )
