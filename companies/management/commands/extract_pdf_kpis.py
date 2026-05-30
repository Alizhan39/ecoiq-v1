"""
extract_pdf_kpis — Extract ESG KPIs from annual reports using Claude API.

Accepts a company slug and optionally a PDF URL or raw text.
Uses Claude claude-sonnet-4-5 to extract structured ESG metrics.
Stores results in DataIngestionLog for audit trail.

No fine-tuning needed — Claude handles ESG extraction out of the box.

Usage:
  python manage.py extract_pdf_kpis --slug=schneider-electric
  python manage.py extract_pdf_kpis --slug=bp-plc --pdf-url=https://...
  python manage.py extract_pdf_kpis --slug=shell --text="Shell 2023 Annual Report..."
"""

import json
import requests
from django.core.management.base import BaseCommand
from django.conf import settings


EXTRACT_PROMPT = """\
You are an ESG data specialist. Extract the following KPIs from the text below.
Return ONLY a valid JSON object with EXACTLY these keys. Use null for missing values.
Do not add any explanation or text outside the JSON.

{
  "scope1_emissions_mt":       null,
  "scope2_emissions_mt":       null,
  "scope3_emissions_mt":       null,
  "renewable_energy_pct":      null,
  "water_consumption_m3":      null,
  "waste_recycled_pct":        null,
  "women_in_leadership_pct":   null,
  "employee_count":            null,
  "safety_incidents":          null,
  "carbon_neutral_target_year":null,
  "has_science_based_target":  false,
  "has_tcfd_alignment":        false,
  "third_party_verified":      false,
  "annual_revenue_usd":        null,
  "net_profit_usd":            null
}

Source text:
"""


class Command(BaseCommand):
    help = 'Extract ESG KPIs from annual reports using Claude API'

    def add_arguments(self, parser):
        parser.add_argument('--slug', type=str, required=True,
                            help='Company slug to process')
        parser.add_argument('--pdf-url', type=str, default=None,
                            help='URL of the annual report PDF (text will be fetched)')
        parser.add_argument('--text', type=str, default=None,
                            help='Raw text to analyse (overrides --pdf-url)')
        parser.add_argument('--dry-run', action='store_true',
                            help='Print extracted KPIs without saving to DB')

    def handle(self, *args, **options):
        import anthropic
        from league.models import Company
        from companies.models import DataIngestionLog

        # ── API client ───────────────────────────────────────────────────────
        api_key = getattr(settings, 'ANTHROPIC_API_KEY', '') or ''
        if not api_key:
            self.stdout.write(self.style.ERROR(
                'ANTHROPIC_API_KEY not set. Add it to your .env / Render env vars.'
            ))
            return

        client = anthropic.Anthropic(api_key=api_key)

        # ── Load company ─────────────────────────────────────────────────────
        try:
            company = Company.objects.select_related('profile').get(slug=options['slug'])
        except Company.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Company not found: {options['slug']}"))
            return

        self.stdout.write(f'Extracting KPIs for: {company.name}')

        # ── Build source text ─────────────────────────────────────────────────
        source_text = ''

        if options.get('text'):
            source_text = options['text'][:4000]
            self.stdout.write('  Source: --text argument')

        elif options.get('pdf_url'):
            self.stdout.write(f"  Fetching: {options['pdf_url'][:60]}…")
            try:
                resp = requests.get(options['pdf_url'], timeout=30, stream=True)
                resp.raise_for_status()
                content_type = resp.headers.get('content-type', '')

                if 'pdf' in content_type:
                    # Try pypdf if available
                    try:
                        from pypdf import PdfReader
                        from io import BytesIO
                        reader = PdfReader(BytesIO(resp.content))
                        pages = []
                        for page in reader.pages[:8]:  # first 8 pages
                            pages.append(page.extract_text() or '')
                        source_text = '\n'.join(pages)[:4000]
                        self.stdout.write(f'  PDF parsed: {len(source_text)} chars from {len(pages)} pages')
                    except ImportError:
                        # Fall back to raw bytes (may contain garbage for PDFs)
                        source_text = resp.text[:3000]
                        self.stdout.write('  pypdf not available — using raw text')
                else:
                    source_text = resp.text[:4000]
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  Could not fetch PDF: {e}'))
                source_text = ''

        # Fall back to company description if no external text
        if not source_text:
            profile = getattr(company, 'profile', None)
            source_text = (
                f"Company: {company.name}. "
                f"Sector: {company.sector}. Country: {company.country}. "
                f"Description: {company.description or 'N/A'}. "
                f"EcoIQ Score: {company.ecoiq_score}."
            )
            if profile:
                source_text += (
                    f" Pollution level: {profile.get_pollution_level_display()}."
                    f" Renewable energy share: {profile.renewable_energy_share or 'N/A'}%."
                    f" Estimated emissions: {profile.estimated_emissions or 'N/A'} tCO2."
                )
            self.stdout.write('  Source: company description (fallback)')

        # ── Call Claude ───────────────────────────────────────────────────────
        self.stdout.write('  Calling Claude API…')
        try:
            message = client.messages.create(
                model='claude-sonnet-4-5',
                max_tokens=1000,
                messages=[{
                    'role':    'user',
                    'content': EXTRACT_PROMPT + source_text[:4000],
                }],
            )
            raw_response = message.content[0].text.strip()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  Claude API error: {e}'))
            return

        # ── Parse JSON ────────────────────────────────────────────────────────
        try:
            # Strip markdown code fences if present
            if raw_response.startswith('```'):
                raw_response = raw_response.split('```')[1]
                if raw_response.startswith('json'):
                    raw_response = raw_response[4:]
            kpis = json.loads(raw_response)
        except json.JSONDecodeError as e:
            self.stdout.write(self.style.ERROR(f'  JSON parse error: {e}'))
            self.stdout.write(f'  Raw response: {raw_response[:300]}')
            return

        # ── Display results ───────────────────────────────────────────────────
        self.stdout.write(self.style.SUCCESS('\n  Extracted KPIs:'))
        found = 0
        for k, v in kpis.items():
            if v is not None and v is not False:
                self.stdout.write(f'    {k}: {v}')
                found += 1

        if found == 0:
            self.stdout.write('  No KPIs found — source text may be insufficient.')

        if options['dry_run']:
            self.stdout.write('\n  [dry-run] — not saved to database.')
            return

        # ── Store in DataIngestionLog ─────────────────────────────────────────
        DataIngestionLog.objects.create(
            company=company,
            source='manual',
            raw_data={
                'kpis':          kpis,
                'method':        'claude_kpi_extraction',
                'source_url':    options.get('pdf_url') or 'text_input',
                'chars_analysed':len(source_text),
                'kpis_found':    found,
            },
            fields_updated=['kpis_extracted'],
            success=True,
        )
        self.stdout.write(self.style.SUCCESS(
            f'\n  Saved to DataIngestionLog — {found} KPIs found for {company.name}.'
        ))
