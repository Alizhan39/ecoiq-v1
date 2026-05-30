"""
ingest_sec_edgar — Pull US company disclosure data from SEC EDGAR.

Free API, no authentication required.
User-Agent header is required (SEC policy).

Usage:
    python manage.py ingest_sec_edgar
    python manage.py ingest_sec_edgar --slug exxonmobil
"""
import time
import requests
from django.core.management.base import BaseCommand
from companies.models import DataIngestionLog

EDGAR_BASE = 'https://data.sec.gov'
EDGAR_HEADERS = {
    'User-Agent': 'EcoIQ alizhan@ecoiq.uk',
    'Accept-Encoding': 'gzip, deflate',
}

# Slug → SEC CIK (zero-padded to 10 digits)
# Find: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&type=10-K
US_COMPANY_CIKS = {
    'exxonmobil':        '0000034088',
    'chevron':           '0000093410',
    'conocophillips':    '0001163165',
    'freeport-mcmoran':  '0000831259',
    'newmont':           '0001164180',
    'southern-copper':   '0000849869',
    'alcoa':             '0001675149',
    'nucor':             '0000073309',
    'tesla':             '0001318605',
    'amazon':            '0001018724',
    'walmart':           '0000104169',
    'jpmorgan':          '0000019617',
    'blackrock':         '0001364742',
    'coca-cola':         '0000021344',
    'microsoft':         '0000789019',
    'apple':             '0000320193',
    'arcelormittal':     '0001345105',
    'vale':              '0001340175',
    'mosaic':            '0001285785',
}


def _extract_latest_value(concept_data: dict) -> float | None:
    """Return the most recent numeric value from an XBRL concept dict."""
    units = concept_data.get('units', {})
    for unit_key, entries in units.items():
        if not entries:
            continue
        # Sort by end date descending and take annual (10-K) filings first
        annual = [e for e in entries if e.get('form') in ('10-K', '20-F')]
        pool   = annual if annual else entries
        pool   = sorted(pool, key=lambda x: x.get('end', ''), reverse=True)
        if pool:
            return pool[0].get('val')
    return None


class Command(BaseCommand):
    help = 'Ingest US company ESG disclosure data from SEC EDGAR (free)'

    def add_arguments(self, parser):
        parser.add_argument('--slug', type=str, help='Only update this slug')

    def handle(self, *args, **options):
        from league.models import Company
        from companies.models import CompanyProfile

        target = options.get('slug')
        ciks   = {target: US_COMPANY_CIKS[target]} if (target and target in US_COMPANY_CIKS) else US_COMPANY_CIKS
        ok, skip, err = 0, 0, 0

        for slug, cik in ciks.items():
            try:
                company = Company.objects.get(slug=slug)
            except Company.DoesNotExist:
                skip += 1
                continue

            try:
                resp = requests.get(
                    f'{EDGAR_BASE}/api/xbrl/companyfacts/CIK{cik}.json',
                    headers=EDGAR_HEADERS,
                    timeout=20,
                )
            except requests.RequestException as exc:
                self.stdout.write(self.style.ERROR(f'  ✗ {slug}: {exc}'))
                err += 1
                continue

            if resp.status_code == 404:
                self.stdout.write(f'  — {slug} (CIK {cik}): not in EDGAR')
                skip += 1
                continue
            elif resp.status_code != 200:
                self.stdout.write(f'  ✗ {slug}: HTTP {resp.status_code}')
                err += 1
                continue

            facts        = resp.json()
            entity_name  = facts.get('entityName', slug)
            us_gaap      = facts.get('facts', {}).get('us-gaap', {})
            dei          = facts.get('facts', {}).get('dei', {})

            # Extract meaningful financial metrics
            revenue_val   = _extract_latest_value(us_gaap.get('Revenues', {}))
            if revenue_val is None:
                revenue_val = _extract_latest_value(
                    us_gaap.get('RevenueFromContractWithCustomerExcludingAssessedTax', {})
                )
            employees_val = _extract_latest_value(dei.get('EntityNumberOfEmployees', {}))

            has_ghg = bool(
                us_gaap.get('GHGEmissions') or
                us_gaap.get('EmissionsIntensity') or
                facts.get('facts', {}).get('ecd', {})
            )

            extracted = {
                'cik':              cik,
                'entity_name':      entity_name,
                'revenue_usd':      revenue_val,
                'employees':        employees_val,
                'has_ghg_data':     has_ghg,
                'has_revenue':      revenue_val is not None,
                'filing_count':     len(facts.get('filings', {}).get('files', [])),
            }

            fields_updated = []

            # Update Company fields where data is fresher / missing
            if revenue_val and (not company.annual_revenue_usd):
                company.annual_revenue_usd = int(revenue_val)
                fields_updated.append('annual_revenue_usd')

            if not company.description and entity_name:
                company.description = (
                    f'{entity_name} — SEC CIK {cik}. '
                    f'Annual revenue: ${revenue_val/1e9:.1f}B. ' if revenue_val else ''
                )
                fields_updated.append('description')

            # Boost CompanyProfile transparency score for SEC-reporting companies
            # (they have formal disclosure obligations → stronger governance signal)
            try:
                profile = company.profile  # OneToOne reverse from CompanyProfile
                if profile and has_ghg:
                    old_t = float(profile.transparency_anti_corruption_score or 50)
                    profile.transparency_anti_corruption_score = min(95.0, old_t + 3.0)
                    profile.save(update_fields=['transparency_anti_corruption_score'])
                    fields_updated.append('transparency_anti_corruption_score')
            except Exception:
                pass

            if fields_updated:
                company.save()

            DataIngestionLog.objects.create(
                company=company,
                source='sec_edgar',
                raw_data=extracted,
                fields_updated=fields_updated,
                success=True,
            )

            rev_str = f'${revenue_val/1e9:.1f}B' if revenue_val else '—'
            self.stdout.write(
                f'  ✓ {entity_name} (CIK {cik}) '
                f'Rev:{rev_str} GHG:{has_ghg}'
            )
            ok += 1
            time.sleep(0.12)   # SEC asks for ≤10 req/sec

        self.stdout.write(self.style.SUCCESS(
            f'\nSEC EDGAR complete — OK:{ok}  Skipped:{skip}  Errors:{err}'
        ))
