"""
EcoIQ Transition Engine — Global Dataset Ingestion.

Uses Anthropic web search to discover industrial companies from global sources
(Forbes G2000, Fortune 500, stock exchanges, ESG registries) and feeds them
into the existing ingestion pipeline.

Usage:
    python manage.py ingest_global_dataset
    python manage.py ingest_global_dataset --source forbes_g2000
    python manage.py ingest_global_dataset --country Kazakhstan --max 10
    python manage.py ingest_global_dataset --dry-run
"""
import json
import logging
import re
import time
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone

from transition.models import GlobalDatasetSource
from league.models import Company

logger = logging.getLogger(__name__)

# ── Pre-defined source registry entries (seeded if not present) ───────────────

DEFAULT_SOURCES = [
    {
        'name': 'Forbes Global 2000 — Energy & Materials',
        'source_type': 'forbes_g2000',
        'url': 'https://www.forbes.com/lists/global2000/',
        'description': 'Top 2000 global companies by revenue, profit, assets, and market value',
        'focus_sectors': ['energy', 'mining', 'utilities', 'chemicals', 'steel'],
        'focus_countries': [],
        'min_revenue_usd': 1_000_000_000,
        'check_interval_days': 90,
    },
    {
        'name': 'Fortune 500 — Industrial Sector',
        'source_type': 'fortune500',
        'url': 'https://fortune.com/ranking/fortune500/',
        'description': 'Top 500 US companies; covers major industrial and energy firms',
        'focus_sectors': ['energy', 'industrial', 'chemicals', 'utilities'],
        'focus_countries': ['USA'],
        'min_revenue_usd': 5_000_000_000,
        'check_interval_days': 90,
    },
    {
        'name': 'Kazakhstan Stock Exchange — KazMunayGas & Peers',
        'source_type': 'stock_exchange',
        'url': 'https://kase.kz',
        'description': 'KASE listed companies in energy, mining, and industrial sectors',
        'focus_sectors': ['energy', 'mining', 'utilities', 'chemicals'],
        'focus_countries': ['Kazakhstan'],
        'min_revenue_usd': 10_000_000,
        'check_interval_days': 60,
    },
    {
        'name': 'Uzbekistan Industrial Registry',
        'source_type': 'gov_registry',
        'url': 'https://uzprom.uz',
        'description': 'Uzbekistan Ministry of Industry major industrial enterprises',
        'focus_sectors': ['energy', 'mining', 'chemicals', 'steel'],
        'focus_countries': ['Uzbekistan'],
        'min_revenue_usd': 5_000_000,
        'check_interval_days': 60,
    },
    {
        'name': 'CDP Global Corporate Registry',
        'source_type': 'esg_db',
        'url': 'https://www.cdp.net/en/companies',
        'description': 'Companies disclosing climate data via CDP — covers 23,000+ companies',
        'focus_sectors': [],
        'focus_countries': [],
        'min_revenue_usd': 100_000_000,
        'check_interval_days': 365,
    },
]


class Command(BaseCommand):
    help = 'Discover and ingest industrial companies from global open-source datasets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            default='',
            help='Source type to process (e.g. forbes_g2000, fortune500, stock_exchange). '
                 'Leave empty to process all active sources.',
        )
        parser.add_argument(
            '--country',
            type=str,
            default='',
            help='Filter by country (e.g. Kazakhstan)',
        )
        parser.add_argument(
            '--sector',
            type=str,
            default='',
            help='Filter by sector code (e.g. energy, mining)',
        )
        parser.add_argument(
            '--max',
            type=int,
            default=5,
            help='Maximum number of companies to ingest per source (default 5)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Discover company names but do not create ingestion jobs',
        )
        parser.add_argument(
            '--seed-sources',
            action='store_true',
            help='Seed GlobalDatasetSource records from defaults then exit',
        )

    def handle(self, *args, **options):
        if options['seed_sources']:
            self._seed_sources()
            return

        # Ensure sources exist
        if not GlobalDatasetSource.objects.exists():
            self.stdout.write('No GlobalDatasetSource records found — seeding defaults...')
            self._seed_sources()

        source_type_filter = options['source']
        country_filter     = options['country']
        sector_filter      = options['sector']
        max_companies      = options['max']
        dry_run            = options['dry_run']

        sources = GlobalDatasetSource.objects.filter(is_active=True)
        if source_type_filter:
            sources = sources.filter(source_type=source_type_filter)

        if not sources.exists():
            self.stdout.write(self.style.WARNING('No active sources found.'))
            return

        total_ingested = 0
        for source in sources:
            self.stdout.write(f'\n📡 Processing: {source.name}')
            try:
                companies = self._discover_companies(
                    source, country_filter, sector_filter, max_companies
                )
                self.stdout.write(f'   Found {len(companies)} candidates')
                source.companies_found = len(companies)

                if dry_run:
                    for c in companies:
                        self.stdout.write(f'   [DRY RUN] Would ingest: {c["name"]} ({c.get("country", "?")})')
                else:
                    ingested = self._ingest_companies(companies, source)
                    source.companies_ingested = ingested
                    total_ingested += ingested
                    self.stdout.write(
                        self.style.SUCCESS(f'   ✓ Ingested {ingested} new companies')
                    )

                source.last_fetch_status = 'success'
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'   ✗ Error: {exc}'))
                source.last_fetch_status = 'failed'
                source.error_log = str(exc)[:1000]
                logger.exception('Failed to process source %s', source.name)

            source.last_fetched_at = timezone.now()
            source.save(update_fields=[
                'last_fetched_at', 'last_fetch_status', 'companies_found',
                'companies_ingested', 'error_log',
            ])

        if not dry_run:
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Global dataset ingestion complete: {total_ingested} companies queued'
            ))

    def _seed_sources(self):
        created = 0
        for data in DEFAULT_SOURCES:
            _, is_new = GlobalDatasetSource.objects.update_or_create(
                name=data['name'],
                defaults=data,
            )
            if is_new:
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Seeded {created} GlobalDatasetSource records'))

    def _discover_companies(self, source, country_filter, sector_filter, max_n) -> list:
        """
        Use Claude web search to discover companies from a given source.
        Returns list of dicts: {name, country, sector, revenue_usd, description}.
        """
        api_key = getattr(settings, 'ANTHROPIC_API_KEY', '')
        if not api_key:
            raise RuntimeError('ANTHROPIC_API_KEY not configured')

        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        model  = getattr(settings, 'ECOIQ_AI_MODEL', 'claude-opus-4-5')

        # Build search prompt
        focus_sectors = source.focus_sectors or []
        focus_countries = source.focus_countries or []
        if country_filter:
            focus_countries = [country_filter]
        if sector_filter:
            focus_sectors = [sector_filter]

        sector_str  = ', '.join(focus_sectors) if focus_sectors else 'energy, mining, utilities, industrial, chemicals, steel'
        country_str = ', '.join(focus_countries) if focus_countries else 'any country'
        min_rev     = f'${source.min_revenue_usd / 1_000_000:.0f}M+ revenue' if source.min_revenue_usd else ''

        prompt = f"""Search for major industrial companies from the following source:

Source: {source.name}
URL: {source.url}
Focus sectors: {sector_str}
Focus countries: {country_str}
{f'Minimum size: {min_rev}' if min_rev else ''}

Find the top {max_n} industrial companies (energy producers, miners, steel mills, chemical plants,
utilities, refineries, cement producers) that:
1. Operate in the focus sectors above
2. Are large industrial enterprises with significant emissions
3. Are not already very small or purely financial companies

For each company, return:
- Full legal company name (as used in filings)
- Country of headquarters
- Primary industry sector (one of: energy, mining, utilities, chemicals, steel, industrial, agriculture, water)
- Approximate annual revenue in USD if known
- Brief description (1-2 sentences on what they do)

Return ONLY a valid JSON array:
[
  {{
    "name": "Full Company Name",
    "country": "Country",
    "sector": "energy|mining|utilities|chemicals|steel|industrial|agriculture|water|other",
    "revenue_usd": 1000000000,
    "description": "Brief description"
  }}
]

Focus on companies with significant environmental footprints that would benefit from
EcoIQ's industrial transition analysis.
"""

        try:
            response = client.messages.create(
                model=model,
                max_tokens=2048,
                tools=[{
                    'type': 'web_search_20250305',
                    'name': 'web_search',
                    'max_uses': 3,
                }],
                messages=[{'role': 'user', 'content': prompt}],
            )

            # Extract text content from response
            text_parts = []
            for block in response.content:
                if hasattr(block, 'text'):
                    text_parts.append(block.text)

            full_text = '\n'.join(text_parts)
        except Exception as exc:
            # Fallback: try without web search tool
            logger.warning('Web search failed, trying text-only: %s', exc)
            response = client.messages.create(
                model=model,
                max_tokens=2048,
                messages=[{'role': 'user', 'content': prompt}],
            )
            full_text = response.content[0].text if response.content else ''

        if not full_text.strip():
            return []

        # Parse JSON
        try:
            data = _parse_json_block(full_text)
            if isinstance(data, dict):
                data = [data]
            return data[:max_n]
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning('JSON parse failed: %s', exc)
            return []

    def _ingest_companies(self, companies: list, source: 'GlobalDatasetSource') -> int:
        """Create IngestionJob for each new company and start pipeline."""
        from ingestion.models import IngestionJob
        from ingestion.pipeline import run_pipeline_in_thread

        ingested = 0
        existing_names = {c.name.lower() for c in Company.objects.all()}

        for company_data in companies:
            name = company_data.get('name', '').strip()
            if not name or len(name) < 2:
                continue

            # Skip if already in database (fuzzy match)
            if name.lower() in existing_names:
                self.stdout.write(f'   Skip (exists): {name}')
                continue

            # Create ingestion job
            try:
                job = IngestionJob.objects.create(
                    company_name=name,
                    status='pending',
                    progress_message=f'Queued via global dataset: {source.name}',
                )
                run_pipeline_in_thread(job.pk)
                self.stdout.write(f'   → Queued: {name} (job #{job.pk})')
                ingested += 1
                # Brief pause to avoid hammering the API
                time.sleep(2)
            except Exception as exc:
                logger.error('Failed to queue %s: %s', name, exc)

        return ingested


def _parse_json_block(text: str):
    """Extract outermost JSON object or array from text."""
    text = re.sub(r'```(?:json)?\s*', '', text).strip()
    for opener, closer in [('{', '}'), ('[', ']')]:
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    return json.loads(text[start:i + 1])
    raise ValueError('No JSON block found')
