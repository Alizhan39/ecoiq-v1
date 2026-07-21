"""
expand_stewardship_universe — feat/global-stewardship-universe (PR 15)
Section 19: seeds a CompanyProfile + synced identity (and, optionally,
triggers a first refresh) for every company this app already has a REAL
regulatory identifier for — a SEC EDGAR CIK or a Companies House number —
never a fabricated or search-discovered company list.

This is deliberately NOT a company-discovery command: it only ever
iterates the union of
companies.management.commands.ingest_sec_edgar.US_COMPANY_CIKS and
companies.management.commands.ingest_companies_house.UK_COMPANY_NUMBERS —
the same two real-identity dicts every other real-data command in this
app already reads from (never a second, competing identity source).
company_intelligence.management.commands.ingest_real_company_evidence.
REAL_COMPANY_SEEDS supplies a curated name/sector where known; for the
remainder, name is derived from the slug itself (real, not fabricated —
it's literally the same key every other real-identity dict already uses)
and country is inferred from which identity dict the slug came from (a
US CIK implies 'United States', a UK Companies House number implies
'United Kingdom' — both real facts, never guessed). Sector defaults to
'other' when genuinely unknown — never invented.

Never sets tracking_status directly: exactly like refresh_stewardship_
universe.py's own documented discipline, tracking_status only ever
becomes 'active' as a side effect of a REAL successful refresh
(refresh_orchestrator.py) — this command creates the CompanyProfile and
syncs its identity fields, nothing more, unless --refresh is passed, in
which case it delegates straight to refresh_company_intelligence()
(reused, never duplicated).

Usage:
    python manage.py expand_stewardship_universe --dry-run
    python manage.py expand_stewardship_universe --limit 10
    python manage.py expand_stewardship_universe --refresh
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Expands the Stewardship Universe to every company with a known real regulatory '
        'identifier (SEC EDGAR CIK or Companies House number).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--refresh', action='store_true',
            help='Also trigger a first refresh for each company (delegates to refresh_company_intelligence(), never duplicates its logic).',
        )
        parser.add_argument(
            '--limit', type=int, default=None,
            help='Maximum number of companies to expand into this run (bounded by rate_limiter.DEFAULT_BATCH_SIZE when omitted).',
        )
        parser.add_argument('--dry-run', action='store_true', help='Preview only — performs zero database writes.')

    def handle(self, *args, **options):
        from companies.management.commands.ingest_companies_house import UK_COMPANY_NUMBERS
        from companies.management.commands.ingest_sec_edgar import US_COMPANY_CIKS
        from companies.models import CompanyProfile
        from company_intelligence.management.commands.ingest_real_company_evidence import REAL_COMPANY_SEEDS
        from company_intelligence.services import identity_sync, rate_limiter
        from league.models import Company

        dry_run = options['dry_run']
        limit = options['limit']
        do_refresh = options['refresh']

        us_slugs = set(US_COMPANY_CIKS.keys())
        uk_slugs = set(UK_COMPANY_NUMBERS.keys())
        all_slugs = sorted(us_slugs | uk_slugs)

        bounded_slugs, dropped = rate_limiter.bounded_batch(all_slugs, limit=limit)
        if dropped:
            self.stdout.write(self.style.WARNING(
                f'Universe expansion bounded to {len(bounded_slugs)} of {len(all_slugs)} known real-identity '
                f'companies this run — {dropped} were NOT processed (re-run, or pass --limit to raise the bound).'
            ))

        if dry_run:
            for slug in bounded_slugs:
                exists = CompanyProfile.objects.filter(company__slug=slug).exists()
                identifier = f'CIK {US_COMPANY_CIKS[slug]}' if slug in us_slugs else f'Companies House #{UK_COMPANY_NUMBERS[slug]}'
                self.stdout.write(f'{slug}: DRY RUN — {identifier} — {"profile already exists" if exists else "would create profile"}.')
            self.stdout.write(self.style.SUCCESS(
                f'DRY RUN complete — {len(bounded_slugs)} compan(y/ies) previewed, zero database writes made.'
            ))
            return

        created_count = synced_count = refreshed_count = 0
        for slug in bounded_slugs:
            seed = REAL_COMPANY_SEEDS.get(slug)
            if seed is None:
                country = 'United States' if slug in us_slugs else 'United Kingdom'
                seed = {'name': slug.replace('-', ' ').title(), 'sector': 'other', 'country': country}

            company, company_created = Company.objects.get_or_create(slug=slug, defaults={**seed, 'is_public': True})
            profile, profile_created = CompanyProfile.objects.get_or_create(company=company, defaults={'status': 'public'})
            newly_created = company_created or profile_created
            if newly_created:
                created_count += 1

            listing = identity_sync.sync_company_identity(profile)
            if listing is not None:
                synced_count += 1

            refresh_note = ''
            if do_refresh:
                from company_intelligence.services.refresh_orchestrator import refresh_company_intelligence

                result = refresh_company_intelligence(profile, triggered_by='management_command')
                if isinstance(result, dict) and result.get('error'):
                    refresh_note = f' — refresh skipped: {result["error"]}'
                else:
                    refreshed_count += 1
                    refresh_note = f' — refreshed: {result.get_status_display()}'

            self.stdout.write(
                f'{slug}: {"created" if newly_created else "already existed"}, '
                f'identity {"synced" if listing else "not available"}{refresh_note}'
            )

        summary = f'Universe expansion complete — {created_count} new profile(s), {synced_count} identity sync(s)'
        summary += f', {refreshed_count} refresh(es).' if do_refresh else ' (no refresh triggered — pass --refresh to also fetch real evidence).'
        self.stdout.write(self.style.SUCCESS(summary))
        self.stdout.write(
            'Every company here has a REAL regulatory identifier (SEC EDGAR CIK or Companies House number) — '
            'this command never fabricates coverage or invents a company that has no defensible identity path. '
            'tracking_status stays not_tracked until this company\'s first successful refresh runs.'
        )
