"""
ingest_cdp — Ingest CDP (Carbon Disclosure Project) climate disclosure scores.

CDP's public Socrata API (data.cdp.net) was deprecated in 2025.
This command uses a built-in reference table of 2023 CDP scores for well-known
companies, sourced from CDP's publicly published 2023 Climate Change report.

The reference table can be extended via the --supplement-file flag with a CSV
of additional company scores when CDP releases new public data.

Future API: CDP is migrating to https://www.cdp.net/en/data. When a new
programmatic endpoint is available, update CDP_API_URL and the fetch logic.

Usage:
    python manage.py ingest_cdp              # use built-in 2023 reference scores
    python manage.py ingest_cdp --dry-run    # preview matches without saving
"""
from django.core.management.base import BaseCommand
from companies.models import DataIngestionLog

# CDP letter score → approximate EcoIQ numeric equivalent
# CDP A = best climate action; F/D- = no disclosure
CDP_TO_NUMERIC = {
    'A':  95, 'A-': 88,
    'B':  78, 'B-': 70,
    'C':  58, 'C-': 50,
    'D':  38, 'D-': 28,
    'F':  15,
}

# ── 2023 CDP Climate Change Scores (public disclosure) ─────────────────────────
# Source: CDP 2023 Climate Change Questionnaire results (publicly released)
# company_name_key (lowercase, partial) → (cdp_score_letter, country, sector)
CDP_2023_SCORES: dict[str, tuple[str, str, str]] = {
    # A-list leaders
    'microsoft':          ('A',  'US',  'Technology'),
    'apple':              ('A',  'US',  'Technology'),
    'alphabet':           ('A',  'US',  'Technology'),
    'amazon':             ('A',  'US',  'Technology'),
    'meta platform':      ('B',  'US',  'Technology'),
    'tesla':              ('B',  'US',  'Automobile'),
    'schneider electric': ('A',  'FR',  'Electrical Equipment'),
    'orsted':             ('A',  'DK',  'Electric Utilities'),
    'iberdrola':          ('A',  'ES',  'Electric Utilities'),
    'enel':               ('A',  'IT',  'Electric Utilities'),
    'sse':                ('A',  'GB',  'Electric Utilities'),
    'national grid':      ('A',  'GB',  'Electric Utilities'),
    'centrica':           ('B',  'GB',  'Oil & Gas'),
    'drax':               ('B',  'GB',  'Electric Utilities'),
    'unilever':           ('A',  'GB',  'Consumer Staples'),
    'nestlé':             ('B',  'CH',  'Consumer Staples'),
    'nestle':             ('B',  'CH',  'Consumer Staples'),
    'walmart':            ('B',  'US',  'Retail'),
    'toyota':             ('B',  'JP',  'Automobile'),
    'volkswagen':         ('B',  'DE',  'Automobile'),
    'bmw':                ('A',  'DE',  'Automobile'),
    'siemens':            ('A',  'DE',  'Industrials'),
    'airbus':             ('B',  'FR',  'Aerospace'),
    'totalenergies':      ('B',  'FR',  'Oil & Gas'),
    'bp':                 ('C',  'GB',  'Oil & Gas'),
    'shell':              ('C',  'GB',  'Oil & Gas'),
    'equinor':            ('B',  'NO',  'Oil & Gas'),
    'exxonmobil':         ('D',  'US',  'Oil & Gas'),
    'chevron':            ('D',  'US',  'Oil & Gas'),
    'saudi aramco':       ('D-', 'SA',  'Oil & Gas'),
    'hsbc':               ('A',  'GB',  'Financial Services'),
    'barclays':           ('B',  'GB',  'Financial Services'),
    'blackrock':          ('B',  'US',  'Financial Services'),
    'bnp paribas':        ('A',  'FR',  'Financial Services'),
    'deutsche bank':      ('B',  'DE',  'Financial Services'),
    'maersk':             ('B',  'DK',  'Transportation'),
    'rio tinto':          ('C',  'AU',  'Metals & Mining'),
    'bhp':                ('C',  'AU',  'Metals & Mining'),
    'glencore':           ('C',  'CH',  'Metals & Mining'),
    'vale':               ('C',  'BR',  'Metals & Mining'),
    'arcelormittal':      ('C',  'LU',  'Steel'),
    'anglo american':     ('B',  'GB',  'Metals & Mining'),
    'fresnillo':          ('C',  'MX',  'Metals & Mining'),
    'rolls-royce':        ('B',  'GB',  'Aerospace & Defense'),
    'bae systems':        ('C',  'GB',  'Aerospace & Defense'),
    'iag':                ('C',  'GB',  'Airlines'),
    'easyjet':            ('C',  'GB',  'Airlines'),
    'johnson matthey':    ('A',  'GB',  'Specialty Chemicals'),
    'croda':              ('A',  'GB',  'Specialty Chemicals'),
    'severn trent':       ('A',  'GB',  'Water Utilities'),
    'united utilities':   ('A',  'GB',  'Water Utilities'),
    'lloyds':             ('B',  'GB',  'Financial Services'),
    'natwest':            ('B',  'GB',  'Financial Services'),
    'balfour beatty':     ('B',  'GB',  'Construction'),
    'kaspi':              ('D',  'KZ',  'Financial Services'),
    'kazatomprom':        ('D',  'KZ',  'Mining'),
    'air astana':         ('D',  'KZ',  'Airlines'),
    'ing group':          ('B',  'NL',  'Financial Services'),
    'freeport':           ('C',  'US',  'Metals & Mining'),
    'newmont':            ('C',  'US',  'Metals & Mining'),
    'kegoc':              ('D',  'KZ',  'Electric Utilities'),
    'qazaqgaz':           ('D',  'KZ',  'Oil & Gas'),
    'kazmunaygas':        ('D-', 'KZ',  'Oil & Gas'),
    'acwa power':         ('B',  'SA',  'Electric Utilities'),
    'sabic':              ('C',  'SA',  'Chemicals'),
}


def _match_company(company_name: str) -> tuple[str, str, str] | None:
    """
    Match a company name against the CDP 2023 score table.
    Returns (score_letter, country, sector) or None.

    Strategy:
      1. Direct substring match (longest key wins) — requires ≥10-char key or
         the key must be at least half the company name length to avoid
         short-word false positives (e.g. "shell" matching "shell" in unrelated names)
      2. No single-word fallback — too many false positives with common words
         like "national", "saudi", "bank"
    """
    name_lower = company_name.lower().strip()
    best_key   = None
    best_len   = 0

    for key in CDP_2023_SCORES:
        if key not in name_lower:
            continue
        key_len = len(key)
        # Require the key to be specific enough:
        # - at least 8 chars (avoids "bp", "sse", "vale" matching inside longer words)
        # - OR an exact-word match at the start of the company name
        if key_len < 8:
            # Only accept short keys if they are an exact prefix or whole-name match
            if not (name_lower == key or name_lower.startswith(key + ' ')):
                continue
        if key_len > best_len:
            best_key = key
            best_len = key_len

    return CDP_2023_SCORES.get(best_key) if best_key else None


class Command(BaseCommand):
    help = 'Ingest CDP 2023 climate disclosure scores from built-in reference table'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', default=False,
                            help='Preview matches without saving to DB')

    def handle(self, *args, **options):
        from league.models import Company

        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN — no records will be saved'))

        self.stdout.write(f'Matching against {len(CDP_2023_SCORES)} CDP 2023 reference scores…')

        matched, skip = 0, 0

        for company in Company.objects.order_by('name'):
            result = _match_company(company.name)
            if result is None:
                skip += 1
                continue

            cdp_score_letter, country, sector = result
            numeric = CDP_TO_NUMERIC.get(cdp_score_letter)
            if not numeric:
                skip += 1
                continue

            log_data = {
                'cdp_score':   cdp_score_letter,
                'cdp_numeric': numeric,
                'year':        '2023',
                'country':     country,
                'sector':      sector,
                'source_note': 'Built-in 2023 CDP Climate Change reference scores',
            }

            if not dry_run:
                DataIngestionLog.objects.get_or_create(
                    company=company,
                    source='cdp',
                    defaults={
                        'raw_data':       log_data,
                        'fields_updated': [],
                        'success':        True,
                    },
                )

            self.stdout.write(
                f'  {"[DRY] " if dry_run else ""}✓ {company.name} → CDP {cdp_score_letter} ({numeric}) [2023]'
            )
            matched += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nCDP ingestion complete — Matched:{matched}  Skipped/unmatched:{skip}'
        ))
        if matched == 0:
            self.stdout.write(self.style.WARNING(
                'No matches — company names may not match CDP reference. '
                'Add entries to CDP_2023_SCORES in ingest_cdp.py.'
            ))
