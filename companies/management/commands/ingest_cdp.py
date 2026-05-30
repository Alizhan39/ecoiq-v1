"""
ingest_cdp — Ingest CDP (Carbon Disclosure Project) public scores.

CDP publishes open scores for 18,000+ companies via Socrata API.
No auth required for basic access.

Data portal: https://data.cdp.net/
Score endpoint: https://data.cdp.net/resource/ri3x-i2ph.json

Usage:
    python manage.py ingest_cdp
    python manage.py ingest_cdp --year 2023
"""
import requests
from django.core.management.base import BaseCommand
from companies.models import DataIngestionLog

CDP_SCORES_URL = 'https://data.cdp.net/resource/ri3x-i2ph.json'

# CDP letter score → approximate EcoIQ numeric equivalent
# CDP A = best disclosure; F = no response
CDP_TO_NUMERIC = {
    'A':  95, 'A-': 88,
    'B':  78, 'B-': 70,
    'C':  58, 'C-': 50,
    'D':  38, 'D-': 28,
    'F':  15,
}


class Command(BaseCommand):
    help = 'Ingest CDP climate disclosure scores (public data, no auth)'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=str, default='2023',
                            help='CDP disclosure year (default: 2023)')

    def handle(self, *args, **options):
        from league.models import Company
        from companies.models import CompanyProfile

        year = options['year']
        self.stdout.write(f'Fetching CDP scores for year={year}…')

        try:
            resp = requests.get(
                CDP_SCORES_URL,
                params={
                    '$limit':  10000,
                    '$select': 'organization_name,country,score,year,sector',
                    '$order':  'year DESC',
                    '$where':  f"year='{year}'",
                },
                timeout=30,
            )
        except requests.RequestException as exc:
            self.stdout.write(self.style.ERROR(f'Network error: {exc}'))
            return

        if resp.status_code != 200:
            self.stdout.write(self.style.ERROR(f'CDP API error: {resp.status_code}'))
            return

        records = resp.json()
        if not records:
            self.stdout.write('CDP returned 0 records — API may have changed endpoint.')
            return

        self.stdout.write(f'  Fetched {len(records):,} CDP records')

        # Build lookup: lowercase name prefix → record list
        cdp_index: dict[str, list] = {}
        for rec in records:
            org = (rec.get('organization_name') or '').lower().strip()
            if org:
                key = org[:15]
                cdp_index.setdefault(key, []).append(rec)

        matched, skip = 0, 0

        for company in Company.objects.order_by('name'):
            name_lower  = company.name.lower().strip()
            prefix      = name_lower[:15]
            candidates  = cdp_index.get(prefix, [])

            # Fall back to word-by-word matching for shorter company names
            if not candidates:
                first_word = name_lower.split()[0]
                if len(first_word) >= 4:
                    candidates = [
                        r for r in records
                        if first_word in (r.get('organization_name') or '').lower()
                    ]

            if not candidates:
                skip += 1
                continue

            best      = candidates[0]
            cdp_score = (best.get('score') or '').strip()
            numeric   = CDP_TO_NUMERIC.get(cdp_score)

            if not numeric:
                skip += 1
                continue

            log_data = {
                'cdp_name':    best.get('organization_name'),
                'cdp_score':   cdp_score,
                'cdp_numeric': numeric,
                'year':        best.get('year'),
                'sector':      best.get('sector'),
                'country':     best.get('country'),
            }

            DataIngestionLog.objects.create(
                company=company,
                source='cdp',
                raw_data=log_data,
                fields_updated=[],
                success=True,
            )

            self.stdout.write(
                f'  ✓ {company.name} → CDP {cdp_score} ({numeric}) [{year}]'
            )
            matched += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nCDP ingestion complete — Matched:{matched}  Skipped/unmatched:{skip}'
        ))
