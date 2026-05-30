"""
ingest_companies_house — Pull UK company data from Companies House API.

Free API (600 req/min).  Register at:
https://developer.companieshouse.gov.uk/developer/applications

Set COMPANIES_HOUSE_API_KEY in your .env / Render environment.

Usage:
    python manage.py ingest_companies_house
    python manage.py ingest_companies_house --slug national-grid
    python manage.py ingest_companies_house --dry-run
"""
import time
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from companies.models import DataIngestionLog

CH_BASE = 'https://api.companieshouse.gov.uk'

# Slug → Companies House registered number
# Find numbers: https://find-and-update.company-information.service.gov.uk/
UK_COMPANY_NUMBERS = {
    'national-grid':        '04031152',
    'sse':                  'SC117119',
    'centrica':             '03033654',
    'rolls-royce':          '01526258',
    'bae-systems':          '01470151',
    'croda-international':  '00313950',
    'johnson-matthey':      '00033228',
    'balfour-beatty':       '00395826',
    'severn-trent':         '02366619',
    'united-utilities':     '02366588',
    'thames-water':         '02366435',
    'anglo-american':       '03564138',
    'fresnillo':            '06802996',
    'tata-steel-uk':        '02280000',
    'hsbc':                 '00014259',
    'barclays':             '00048839',
    'lloyds-banking-group': '00095000',
    'natwest-group':        '00929027',
    'iag-british-airways':  '04067241',
    'easyjet':              '03959649',
    'biffa':                '11285665',
    'renewi':               '00216174',
    'drax-group':           '04883593',
    'stoke-share-ltd':      '16007341',   # EcoIQ parent entity
}


class Command(BaseCommand):
    help = 'Ingest UK company data from Companies House API (free)'

    def add_arguments(self, parser):
        parser.add_argument('--slug',    type=str,  help='Only update this slug')
        parser.add_argument('--dry-run', action='store_true', help='Fetch but do not save')

    def handle(self, *args, **options):
        from league.models import Company

        api_key  = getattr(settings, 'COMPANIES_HOUSE_API_KEY', '').strip()
        dry_run  = options['dry_run']
        target   = options.get('slug')

        if not api_key:
            self.stdout.write(self.style.WARNING(
                'COMPANIES_HOUSE_API_KEY not set — requests will likely return 401.\n'
                'Get a free key at developer.companieshouse.gov.uk'
            ))

        slugs = [target] if target else list(UK_COMPANY_NUMBERS.keys())
        ok, skip, err = 0, 0, 0

        for slug in slugs:
            company_number = UK_COMPANY_NUMBERS.get(slug)
            if not company_number:
                skip += 1
                continue

            try:
                company = Company.objects.get(slug=slug)
            except Company.DoesNotExist:
                self.stdout.write(f'  — {slug}: not in DB, skip')
                skip += 1
                continue

            try:
                resp = requests.get(
                    f'{CH_BASE}/company/{company_number}',
                    auth=(api_key, ''),
                    timeout=10,
                )
            except requests.RequestException as exc:
                self.stdout.write(self.style.ERROR(f'  ✗ {slug}: network error — {exc}'))
                err += 1
                continue

            if resp.status_code == 401:
                self.stdout.write(self.style.ERROR('  Invalid API key — aborting.'))
                break
            elif resp.status_code == 404:
                self.stdout.write(f'  — {slug} ({company_number}): not found on CH')
                skip += 1
                continue
            elif resp.status_code != 200:
                self.stdout.write(f'  ✗ {slug}: HTTP {resp.status_code}')
                err += 1
                continue

            data             = resp.json()
            company_status   = data.get('company_status', '')
            sic_codes        = data.get('sic_codes', [])
            registered_name  = data.get('company_name', '')

            extracted = {
                'ch_number':     company_number,
                'ch_name':       registered_name,
                'status':        company_status,
                'sic_codes':     sic_codes,
                'jurisdiction':  data.get('jurisdiction', ''),
                'date_created':  data.get('date_of_creation', ''),
            }
            fields_updated = []

            if not dry_run:
                # Update description if currently empty
                if not company.description and registered_name:
                    company.description = (
                        f'{registered_name} (Companies House: {company_number}). '
                        f'SIC: {", ".join(sic_codes)}. Status: {company_status}.'
                    )
                    fields_updated.append('description')
                    company.save()

                DataIngestionLog.objects.create(
                    company=company,
                    source='companies_house',
                    raw_data=extracted,
                    fields_updated=fields_updated,
                    success=True,
                )

            status_str = '✓' if company_status == 'active' else '⚠'
            self.stdout.write(
                f'  {status_str} {company.name} ({company_number}) '
                f'— {company_status}'
                + (' [DRY RUN]' if dry_run else '')
            )
            ok += 1
            time.sleep(0.12)   # stay within 600 req/min rate limit

        self.stdout.write(self.style.SUCCESS(
            f'\nCompanies House complete — OK:{ok}  Skipped:{skip}  Errors:{err}'
        ))
