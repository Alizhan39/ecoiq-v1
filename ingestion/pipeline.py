"""
EcoIQ AI Company Ingestion Pipeline.

Architecture
============
Five sequential steps, each isolated in its own method.
Progress is written to the DB after every step so the UI can poll.
All DB writes use .filter(pk=pk).update(...) — safe from any thread.

Step 1 — Search   : Anthropic web_search_20250305 → company facts + report URLs
Step 2 — Download : requests + pypdf → raw text from PDFs and HTML pages
Step 3 — Extract  : Claude structured JSON extraction → projects, KPIs, signals
Step 4 — Score    : Rule-based + AI-suggested pillar scores (0-100)
Step 5 — Save     : Company, Project, Evidence, ScoreHistory, AIAnalysisJob

Entry point: run_pipeline_in_thread(job_pk)  — spawns a daemon thread.
"""

import io
import json
import logging
import re
import threading
import traceback
from datetime import date, datetime
from decimal import Decimal

import requests as http_requests

from django.conf import settings
from django.utils import timezone

log = logging.getLogger('ingestion.pipeline')


# ── Progress buckets (step → % range) ─────────────────────────────────────────

_STEP_RANGES = {
    'search':   (5,  30),
    'download': (30, 50),
    'extract':  (50, 72),
    'score':    (72, 88),
    'save':     (88, 100),
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clamp(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, value))


def _update_job(job_pk: int, **fields):
    """Thread-safe, no-instance DB write."""
    from ingestion.models import IngestionJob
    IngestionJob.objects.filter(pk=job_pk).update(**fields)


def _progress(job_pk: int, pct: int, message: str):
    _update_job(job_pk, progress_pct=pct, progress_message=message)
    log.info('[job %s] %d%% — %s', job_pk, pct, message)


def _interpolate(step: str, fraction: float) -> int:
    lo, hi = _STEP_RANGES[step]
    return _clamp(int(lo + (hi - lo) * fraction), lo, hi)


# ── PDF text extraction ────────────────────────────────────────────────────────

def _extract_pdf_text(content: bytes, max_chars: int = 12_000) -> str:
    """Extract plain text from PDF bytes using pypdf."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or '')
            if sum(len(p) for p in parts) >= max_chars:
                break
        return '\n'.join(parts)[:max_chars]
    except Exception as exc:
        log.warning('PDF extraction failed: %s', exc)
        return ''


def _extract_html_text(content: bytes, max_chars: int = 8_000) -> str:
    """Strip HTML tags, collapse whitespace."""
    try:
        text = content.decode('utf-8', errors='replace')
        text = re.sub(r'<style[^>]*>.*?</style>', ' ', text, flags=re.S | re.I)
        text = re.sub(r'<script[^>]*>.*?</script>', ' ', text, flags=re.S | re.I)
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text[:max_chars]
    except Exception:
        return ''


def _fetch_url(url: str, timeout: int = 20) -> bytes | None:
    """Download URL content with a browser-like UA. Returns raw bytes or None."""
    try:
        headers = {
            'User-Agent': (
                'Mozilla/5.0 (compatible; EcoIQ-Bot/1.0; '
                '+https://ecoiq.uk/about)'
            ),
            'Accept': 'text/html,application/pdf,*/*;q=0.8',
        }
        resp = http_requests.get(url, headers=headers, timeout=timeout,
                                  allow_redirects=True, stream=True)
        if resp.status_code != 200:
            return None
        # Guard against huge files (>8 MB)
        chunks = []
        total = 0
        for chunk in resp.iter_content(chunk_size=65536):
            chunks.append(chunk)
            total += len(chunk)
            if total > 8_000_000:
                break
        return b''.join(chunks)
    except Exception as exc:
        log.warning('Fetch failed for %s: %s', url, exc)
        return None


# ── Anthropic client ──────────────────────────────────────────────────────────

def _anthropic_client():
    import anthropic
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


# ── Main pipeline class ────────────────────────────────────────────────────────

class IngestionPipeline:
    """
    Encapsulates all pipeline state for one IngestionJob.
    Instantiate with the pk; all DB access is via pk to stay thread-safe.
    """

    def __init__(self, job_pk: int):
        self.job_pk       = job_pk
        self.company_name = ''      # filled in run()
        self._search_data: dict  = {}
        self._sources: list[dict]= []   # [{url, source_type, title, snippet, content, confidence}]
        self._extraction: dict   = {}
        self._scores: dict       = {}

    # ── Public entry ──────────────────────────────────────────────────────────

    def run(self):
        from ingestion.models import IngestionJob
        try:
            job = IngestionJob.objects.get(pk=self.job_pk)
            self.company_name = job.company_name
            _update_job(self.job_pk,
                        status=IngestionJob.STATUS_SEARCHING,
                        started_at=timezone.now(),
                        progress_pct=2,
                        progress_message=f'Starting ingestion for "{self.company_name}"…')

            self._step_search()
            self._step_download()
            self._step_extract()
            self._step_score()
            self._step_save()

            _update_job(self.job_pk,
                        status=IngestionJob.STATUS_DONE,
                        progress_pct=100,
                        progress_message='Ingestion complete.',
                        completed_at=timezone.now())

        except Exception as exc:
            tb = traceback.format_exc()
            log.error('[job %s] Pipeline failed: %s\n%s', self.job_pk, exc, tb)
            _update_job(self.job_pk,
                        status=IngestionJob.STATUS_FAILED,
                        progress_pct=0,
                        error_message=f'{exc}\n\n{tb}',
                        completed_at=timezone.now())

    # ── Step 1: Web Search ────────────────────────────────────────────────────

    def _step_search(self):
        from ingestion.models import IngestionJob
        _update_job(self.job_pk,
                    status=IngestionJob.STATUS_SEARCHING,
                    progress_pct=5,
                    progress_message='Searching the internet for company data…')

        prompt = f"""You are an environmental research assistant helping build an ESG database.

Research the company: "{self.company_name}"

Use web search to find:
1. Official company website and basic facts (country, sector, founded year, employee count, revenue)
2. ESG reports, sustainability reports, or annual reports (find direct PDF URLs if possible)
3. Environmental projects, green investments, pollution incidents
4. Government regulatory filings or environmental permits
5. News about environmental performance (positive and negative)

Return a JSON object with this exact structure:
{{
  "canonical_name": "Official company name as it appears in documents",
  "country": "Country name",
  "city": "Headquarters city",
  "sector": "One of: oil_gas | mining | energy | chemical | metallurgy | transport | agriculture | other",
  "website": "https://...",
  "founded_year": 2000,
  "employee_count": 50000,
  "annual_revenue_usd": 5000000000,
  "description": "2-3 sentence company description",
  "report_urls": [
    {{"url": "https://...", "type": "esg_report", "title": "ESG Report 2023", "year": 2023}},
    {{"url": "https://...", "type": "annual_report", "title": "Annual Report 2023", "year": 2023}}
  ],
  "web_sources": [
    {{"url": "https://...", "type": "web", "title": "Page title", "snippet": "Key excerpt (max 200 chars)", "confidence": 0.9}}
  ],
  "environmental_highlights": ["bullet 1", "bullet 2"],
  "environmental_concerns": ["bullet 1", "bullet 2"],
  "data_confidence": 0.8
}}

Respond ONLY with valid JSON. No markdown, no explanation."""

        client = _anthropic_client()
        model  = getattr(settings, 'ECOIQ_AI_MODEL', 'claude-opus-4-5')

        _progress(self.job_pk, 8, 'Running AI web search…')

        try:
            response = client.messages.create(
                model=model,
                max_tokens=4096,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract the text block from the response
            text_content = ''
            for block in response.content:
                if hasattr(block, 'text'):
                    text_content += block.text

            _progress(self.job_pk, 25, 'Parsing search results…')

            # Parse JSON from response
            search_data = self._parse_json_block(text_content)
            if not search_data:
                # Fallback: minimal structure so later steps can still run
                search_data = {
                    'canonical_name': self.company_name,
                    'country': 'Unknown',
                    'sector': 'other',
                    'report_urls': [],
                    'web_sources': [],
                    'data_confidence': 0.2,
                }

        except Exception as exc:
            log.warning('[job %s] Web search failed (%s), using minimal stub', self.job_pk, exc)
            search_data = {
                'canonical_name': self.company_name,
                'country': 'Unknown',
                'sector': 'other',
                'report_urls': [],
                'web_sources': [],
                'data_confidence': 0.1,
                'error': str(exc),
            }

        self._search_data = search_data

        # Persist raw output
        _update_job(self.job_pk, search_result=search_data)

        # Build internal sources list
        for src in search_data.get('report_urls', []):
            self._sources.append({
                'url': src.get('url', ''),
                'source_type': src.get('type', 'pdf'),
                'title': src.get('title', ''),
                'snippet': '',
                'content': '',
                'confidence': 0.9,
                'downloaded': False,
                'used_in_analysis': False,
                'content_chars': 0,
            })
        for src in search_data.get('web_sources', []):
            self._sources.append({
                'url': src.get('url', ''),
                'source_type': src.get('type', 'web'),
                'title': src.get('title', ''),
                'snippet': src.get('snippet', ''),
                'content': '',
                'confidence': float(src.get('confidence', 0.5)),
                'downloaded': False,
                'used_in_analysis': False,
                'content_chars': 0,
            })

        _progress(self.job_pk, 29, f'Found {len(self._sources)} sources to investigate.')

    # ── Step 2: Download ──────────────────────────────────────────────────────

    def _step_download(self):
        from ingestion.models import IngestionJob
        _update_job(self.job_pk,
                    status=IngestionJob.STATUS_DOWNLOADING,
                    progress_pct=30,
                    progress_message='Downloading ESG reports and documents…')

        # Prioritise report URLs first, then high-confidence web sources
        sorted_sources = sorted(
            self._sources,
            key=lambda s: (
                0 if s['source_type'] in ('esg_report', 'annual_report', 'pdf') else 1,
                -s['confidence'],
            )
        )

        # Cap: download at most 6 sources to keep latency reasonable
        to_download = sorted_sources[:6]
        total = len(to_download)

        for i, src in enumerate(to_download):
            pct = _interpolate('download', (i + 1) / max(total, 1))
            _progress(self.job_pk, pct, f'Downloading: {src["title"] or src["url"][:60]}…')

            content_bytes = _fetch_url(src['url'])
            if not content_bytes:
                continue

            src['downloaded'] = True
            ct = src['url'].lower()

            if ct.endswith('.pdf') or content_bytes[:4] == b'%PDF':
                text = _extract_pdf_text(content_bytes)
                src['source_type'] = 'pdf'
            else:
                text = _extract_html_text(content_bytes)

            src['content']       = text
            src['content_chars'] = len(text)

        _progress(self.job_pk, 49, f'Downloaded {sum(1 for s in self._sources if s["downloaded"])} sources.')

    # ── Step 3: Extract ───────────────────────────────────────────────────────

    def _step_extract(self):
        from ingestion.models import IngestionJob
        _update_job(self.job_pk,
                    status=IngestionJob.STATUS_EXTRACTING,
                    progress_pct=50,
                    progress_message='AI extracting environmental data and projects…')

        # Build a corpus from downloaded sources (cap total chars to keep prompt sane)
        corpus_parts = []
        total_chars  = 0
        MAX_CORPUS   = 28_000

        for src in self._sources:
            if not src['content']:
                continue
            chunk = f'--- SOURCE: {src["title"] or src["url"]} ---\n{src["content"][:6000]}\n'
            if total_chars + len(chunk) > MAX_CORPUS:
                break
            corpus_parts.append(chunk)
            src['used_in_analysis'] = True
            total_chars += len(chunk)

        corpus = '\n'.join(corpus_parts) if corpus_parts else 'No documents downloaded; use web search knowledge only.'

        search_summary = json.dumps({
            k: v for k, v in self._search_data.items()
            if k not in ('report_urls', 'web_sources')
        }, ensure_ascii=False, indent=2)

        _progress(self.job_pk, 55, 'Sending documents to AI for extraction…')

        prompt = f"""You are an expert ESG analyst. Extract structured environmental data for:

Company: {self._search_data.get('canonical_name', self.company_name)}
Country: {self._search_data.get('country', 'Unknown')}
Sector:  {self._search_data.get('sector', 'other')}

Search summary:
{search_summary}

Document corpus:
{corpus}

Return a JSON object:
{{
  "projects": [
    {{
      "name": "Project name",
      "project_type": "One of: coal_stove|gasification|power_modern|renewable|water_cleanup|waste|tree_planting|filters|methane|other",
      "status": "planned|active|completed|cancelled",
      "start_year": 2021,
      "investment_usd": 50000000,
      "co2_reduction_tonnes": 150000,
      "pm25_reduction_kg": 5000,
      "households_helped": 3000,
      "description": "What the project does",
      "location": "City, Region",
      "source_url": "https://..."
    }}
  ],
  "metrics": {{
    "total_co2_tonnes": 2500000,
    "co2_year": 2022,
    "ghg_intensity": 0.45,
    "renewable_pct": 12,
    "investment_env_usd": 80000000,
    "investment_env_year": 2022,
    "environmental_fines_usd": 0,
    "violations_count": 0
  }},
  "esg_signals": {{
    "has_esg_report": true,
    "has_audit": false,
    "has_third_party_verification": false,
    "iso14001_certified": false,
    "targets_set": true,
    "net_zero_target_year": null,
    "community_programs": ["Program 1", "Program 2"],
    "incidents": ["Incident description if any"]
  }},
  "pillar_hints": {{
    "pollution_footprint": {{
      "suggested_score": 45,
      "rationale": "Why this score",
      "data_quality": "high|medium|low"
    }},
    "reduction_progress": {{
      "suggested_score": 55,
      "rationale": "Why",
      "data_quality": "medium"
    }},
    "investment": {{
      "suggested_score": 60,
      "rationale": "Why",
      "data_quality": "high"
    }},
    "transparency": {{
      "suggested_score": 50,
      "rationale": "Why",
      "data_quality": "high"
    }},
    "community_impact": {{
      "suggested_score": 40,
      "rationale": "Why",
      "data_quality": "low"
    }}
  }},
  "greenwashing_signals": ["Any concerns found"],
  "data_gaps": ["What was missing"],
  "overall_confidence": 0.7
}}

Rules:
- Only include projects with evidence from the documents or web search
- Set data_quality based on how well-evidenced the score hint is
- If data is missing, estimate from sector/country norms but lower data_quality
- Return valid JSON only. No markdown.
"""

        client = _anthropic_client()
        model  = getattr(settings, 'ECOIQ_AI_MODEL', 'claude-opus-4-5')

        try:
            response = client.messages.create(
                model=model,
                max_tokens=6000,
                messages=[{"role": "user", "content": prompt}],
            )
            text_content = response.content[0].text if response.content else ''
            _progress(self.job_pk, 68, 'Parsing AI extraction output…')
            extraction = self._parse_json_block(text_content)
        except Exception as exc:
            log.warning('[job %s] Extraction failed: %s', self.job_pk, exc)
            extraction = {'projects': [], 'metrics': {}, 'esg_signals': {},
                          'pillar_hints': {}, 'greenwashing_signals': [], 'data_gaps': [],
                          'overall_confidence': 0.1}

        self._extraction = extraction
        _update_job(self.job_pk, extraction_result=extraction)
        _progress(self.job_pk, 71,
                  f'Extracted {len(extraction.get("projects", []))} projects, '
                  f'{len(extraction.get("esg_signals", {}).get("community_programs", []))} community programs.')

    # ── Step 4: Score ─────────────────────────────────────────────────────────

    def _step_score(self):
        from ingestion.models import IngestionJob
        _update_job(self.job_pk,
                    status=IngestionJob.STATUS_SCORING,
                    progress_pct=72,
                    progress_message='Computing EcoIQ pillar scores…')

        hints   = self._extraction.get('pillar_hints', {})
        metrics = self._extraction.get('metrics', {})
        signals = self._extraction.get('esg_signals', {})

        def _hint(pillar: str, fallback: int) -> tuple[int, float]:
            h = hints.get(pillar, {})
            score = h.get('suggested_score', fallback)
            dq = h.get('data_quality', 'low')
            conf = {'high': 0.85, 'medium': 0.6, 'low': 0.35}.get(dq, 0.35)
            return _clamp(int(score), 0, 100), conf

        _progress(self.job_pk, 76, 'Scoring Pollution Footprint…')
        poll_score, poll_conf = _hint('pollution_footprint', 30)

        _progress(self.job_pk, 79, 'Scoring Reduction Progress…')
        red_score, red_conf = _hint('reduction_progress', 30)

        _progress(self.job_pk, 81, 'Scoring Investment…')
        inv_score, inv_conf = _hint('investment', 30)

        # Transparency: boost if we actually found a report
        _progress(self.job_pk, 83, 'Scoring Transparency…')
        trans_score, trans_conf = _hint('transparency', 25)
        if signals.get('has_esg_report'):
            trans_score = _clamp(trans_score + 10, 0, 100)
        if signals.get('has_third_party_verification'):
            trans_score = _clamp(trans_score + 8, 0, 100)

        _progress(self.job_pk, 85, 'Scoring Community Impact…')
        comm_score, comm_conf = _hint('community_impact', 25)
        # Boost if community programs found
        programs = len(signals.get('community_programs', []))
        if programs > 0:
            comm_score = _clamp(comm_score + min(programs * 3, 12), 0, 100)

        # Greenwashing penalty
        gw_signals = self._extraction.get('greenwashing_signals', [])
        if len(gw_signals) >= 2:
            trans_score = _clamp(trans_score - 10, 0, 100)

        # Composite
        composite = round(
            poll_score * 0.35 +
            red_score  * 0.25 +
            inv_score  * 0.20 +
            trans_score* 0.10 +
            comm_score * 0.10,
            1
        )
        overall_conf = round(
            (poll_conf * 0.35 + red_conf * 0.25 + inv_conf * 0.20 +
             trans_conf * 0.10 + comm_conf * 0.10),
            3
        )

        # Store confidences as 0-100 integers for easy template rendering
        def _pct(f): return round(f * 100)

        self._scores = {
            'pollution_footprint': poll_score,
            'reduction_progress':  red_score,
            'investment':          inv_score,
            'transparency':        trans_score,
            'community_impact':    comm_score,
            'ecoiq_score':         composite,
            'overall_confidence':  _pct(overall_conf),
            'pillar_confidence': {
                'pollution':    _pct(poll_conf),
                'reduction':    _pct(red_conf),
                'investment':   _pct(inv_conf),
                'transparency': _pct(trans_conf),
                'community':    _pct(comm_conf),
            },
            'reasoning': {k: hints.get(k, {}).get('rationale', '') for k in
                          ('pollution_footprint', 'reduction_progress', 'investment',
                           'transparency', 'community_impact')},
        }
        _update_job(self.job_pk, score_result=self._scores)
        _progress(self.job_pk, 87, f'Computed EcoIQ score: {composite} (confidence {overall_conf:.0%})')

    # ── Step 5: Save ──────────────────────────────────────────────────────────

    def _step_save(self):
        from ingestion.models import IngestionJob, IngestionSource
        from league.models import Company, EnvironmentalProject, Evidence, ScoreHistory, SECTOR_CHOICES
        from league.scoring import rerank_all

        _update_job(self.job_pk,
                    status=IngestionJob.STATUS_SAVING,
                    progress_pct=88,
                    progress_message='Saving company and all data to database…')

        sd      = self._search_data
        ex      = self._extraction
        sc      = self._scores
        signals = ex.get('esg_signals', {})
        metrics = ex.get('metrics', {})

        # ── Company ──────────────────────────────────────────────────────────
        canonical_name = sd.get('canonical_name') or self.company_name
        sector_code    = sd.get('sector', 'other')
        valid_sectors  = {code for code, _ in SECTOR_CHOICES}
        if sector_code not in valid_sectors:
            sector_code = 'other'

        revenue = sd.get('annual_revenue_usd') or None
        if revenue is not None:
            try:
                revenue = int(revenue)
            except (ValueError, TypeError):
                revenue = None

        emp_count = sd.get('employee_count') or None
        if emp_count is not None:
            try:
                emp_count = int(emp_count)
            except (ValueError, TypeError):
                emp_count = None

        founded = sd.get('founded_year') or None
        if founded is not None:
            try:
                founded = int(founded)
                if not (1800 <= founded <= date.today().year):
                    founded = None
            except (ValueError, TypeError):
                founded = None

        company, created = Company.objects.get_or_create(
            slug=self._slug(canonical_name),
            defaults={
                'name':               canonical_name,
                'sector':             sector_code,
                'country':            sd.get('country', 'Unknown'),
                'city':               sd.get('city', ''),
                'founded_year':       founded,
                'description':        sd.get('description', ''),
                'website':            sd.get('website', ''),
                'employee_count':     emp_count,
                'annual_revenue_usd': revenue,
                'score_pollution_footprint': sc['pollution_footprint'],
                'score_reduction_progress':  sc['reduction_progress'],
                'score_investment':          sc['investment'],
                'score_transparency':        sc['transparency'],
                'score_community_impact':    sc['community_impact'],
            },
        )

        if not created:
            # Update scores & metadata on existing record
            Company.objects.filter(pk=company.pk).update(
                sector=sector_code,
                country=sd.get('country', company.country),
                city=sd.get('city', company.city) or company.city,
                description=sd.get('description', '') or company.description,
                website=sd.get('website', '') or company.website,
                score_pollution_footprint=sc['pollution_footprint'],
                score_reduction_progress=sc['reduction_progress'],
                score_investment=sc['investment'],
                score_transparency=sc['transparency'],
                score_community_impact=sc['community_impact'],
            )
            company.refresh_from_db()

        # Recompute & save ecoiq_score
        company.ecoiq_score = company.compute_score()
        company.save(update_fields=['ecoiq_score'])

        _progress(self.job_pk, 90, f'{"Created" if created else "Updated"} company: {company.name}')

        # ── Projects ─────────────────────────────────────────────────────────
        from league.models import PROJECT_TYPE_CHOICES
        valid_pt = {code for code, _ in PROJECT_TYPE_CHOICES}

        projects_saved = 0
        for p in ex.get('projects', []):
            pt = p.get('project_type', 'other')
            if pt not in valid_pt:
                pt = 'other'

            status = p.get('status', 'planned')
            if status not in ('planned', 'active', 'completed', 'cancelled'):
                status = 'planned'

            start_y = p.get('start_year')
            start_d = date(int(start_y), 1, 1) if start_y else None

            inv = self._safe_int(p.get('investment_usd'))
            co2 = self._safe_int(p.get('co2_reduction_tonnes'))
            pm25= self._safe_int(p.get('pm25_reduction_kg'))
            hh  = self._safe_int(p.get('households_helped'))

            proj, _ = EnvironmentalProject.objects.get_or_create(
                company=company,
                name=p.get('name', 'Unknown Project')[:255],
                defaults={
                    'project_type':       pt,
                    'status':             status,
                    'start_date':         start_d,
                    'investment_usd':     inv,
                    'co2_reduction_tonnes': co2,
                    'pm25_reduction_kg':  pm25,
                    'households_helped':  hh,
                    'description':        p.get('description', ''),
                    'location':           p.get('location', '')[:255],
                    'verified':           False,
                },
            )

            # Evidence for the project source URL
            src_url = p.get('source_url', '')
            if src_url:
                Evidence.objects.get_or_create(
                    company=company,
                    project=proj,
                    url=src_url[:2000],
                    defaults={
                        'doc_type':   'press_release',
                        'title':      f'Source: {p.get("name", "Project")}',
                        'verification_status': 'pending',
                    },
                )
            projects_saved += 1

        _progress(self.job_pk, 93, f'Saved {projects_saved} projects.')

        # ── Evidence from report URLs ─────────────────────────────────────────
        for src in self._sources:
            if not src.get('url') or not src.get('downloaded'):
                continue
            doc_map = {
                'esg_report':    'audit_report',
                'annual_report': 'audit_report',
                'pdf':           'other',
                'government':    'government_report',
                'news':          'press_release',
                'web':           'press_release',
            }
            doc_type = doc_map.get(src['source_type'], 'other')
            Evidence.objects.get_or_create(
                company=company,
                url=src['url'][:2000],
                defaults={
                    'doc_type':   doc_type,
                    'title':      src['title'][:255] or src['url'][:255],
                    'notes':      src['snippet'][:1000] if src.get('snippet') else '',
                    'verification_status': 'pending',
                },
            )

        # ── ScoreHistory ──────────────────────────────────────────────────────
        today = date.today()
        ScoreHistory.objects.update_or_create(
            company=company,
            date=today,
            defaults={
                'ecoiq_score':               Decimal(str(sc['ecoiq_score'])),
                'score_pollution_footprint': sc['pollution_footprint'],
                'score_reduction_progress':  sc['reduction_progress'],
                'score_investment':          sc['investment'],
                'score_transparency':        sc['transparency'],
                'score_community_impact':    sc['community_impact'],
            },
        )

        # ── AIAnalysisJob + findings + score estimate ─────────────────────────
        try:
            from audit.models import AIAnalysisJob, AIFinding, AIScoreEstimate

            # pdf_file is required by model but we have no PDF — pass empty str
            # (FileField stores a string path; ORM-level create accepts '' safely)
            ai_job = AIAnalysisJob.objects.create(
                company=company,
                pdf_file='',
                original_filename=f'ingestion:{company.name}'[:255],
                status='completed',
                model_used=getattr(settings, 'ECOIQ_AI_MODEL', ''),
                raw_response=ex or {},
                detected_company_name=company.name,
                detected_doc_type='ingestion',
                executive_summary=(
                    sd.get('description', '') or
                    f'Auto-ingested via EcoIQ AI pipeline on {date.today()}'
                )[:2000],
            )

            # Save pillar findings as AIFinding records
            reasoning = sc.get('reasoning', {})
            pillar_finding_map = {
                'pollution_footprint': 'co2_metric',
                'reduction_progress':  'co2_metric',
                'investment':          'investment',
                'transparency':        'transparency',
                'community_impact':    'other',
            }
            for pillar_key, ft in pillar_finding_map.items():
                rationale = reasoning.get(pillar_key, '')
                if not rationale:
                    continue
                conf = sc['pillar_confidence'].get(
                    pillar_key.replace('_footprint','').replace('_progress','')
                             .replace('_impact',''),
                    50,
                ) / 100.0  # pillar_confidence is now 0-100 pct; AIFinding needs 0-1
                pillar_label = pillar_key.replace('_', ' ').title()
                AIFinding.objects.create(
                    job=ai_job,
                    finding_type=ft,
                    title=f'{pillar_label} — AI Ingestion Finding'[:255],
                    description=rationale[:2000],
                    confidence_score=conf,
                    status='pending',
                )

            # ESG signals as findings
            for incident in signals.get('incidents', []):
                AIFinding.objects.create(
                    job=ai_job,
                    finding_type='other',
                    title='Environmental Incident'[:255],
                    description=str(incident)[:2000],
                    confidence_score=0.6,
                    status='pending',
                )

            for gw in ex.get('greenwashing_signals', []):
                AIFinding.objects.create(
                    job=ai_job,
                    finding_type='greenwashing',
                    title='Greenwashing Signal'[:255],
                    description=str(gw)[:2000],
                    confidence_score=0.5,
                    status='pending',
                )

            # Score estimate
            AIScoreEstimate.objects.create(
                job=ai_job,
                est_pollution=sc['pollution_footprint'],
                est_reduction=sc['reduction_progress'],
                est_investment=sc['investment'],
                est_transparency=sc['transparency'],
                est_community=sc['community_impact'],
                est_ecoiq=float(sc['ecoiq_score']),
                reasoning=json.dumps(reasoning, ensure_ascii=False)[:5000],
                data_gaps=ex.get('data_gaps', []),
                greenwashing_signals=ex.get('greenwashing_signals', []),
                confidence=sc['overall_confidence'] / 100.0,  # AIScoreEstimate expects 0-1
            )

        except Exception as exc:
            log.warning('[job %s] AIAnalysisJob save failed (non-fatal): %s', self.job_pk, exc)

        # ── IngestionSource records ───────────────────────────────────────────
        from ingestion.models import IngestionSource
        for src in self._sources:
            if not src.get('url'):
                continue
            IngestionSource.objects.create(
                job_id=self.job_pk,
                url=src['url'][:2000],
                source_type=src.get('source_type', 'other'),
                title=src.get('title', '')[:500],
                snippet=src.get('snippet', '')[:1000],
                downloaded=src.get('downloaded', False),
                content_chars=src.get('content_chars', 0),
                used_in_analysis=src.get('used_in_analysis', False),
                confidence=src.get('confidence', 0.0),
            )

        # ── Rerank all companies ──────────────────────────────────────────────
        try:
            rerank_all()
        except Exception as exc:
            log.warning('[job %s] rerank_all failed (non-fatal): %s', self.job_pk, exc)

        # ── Link company to job ───────────────────────────────────────────────
        _update_job(self.job_pk, result_company_id=company.pk)
        _progress(self.job_pk, 99, f'All data saved. Company: {company.name} (rank #{company.rank})')

    # ── Utilities ─────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_json_block(text: str) -> dict:
        """Extract and parse the first JSON object from a text response."""
        if not text:
            return {}
        # Strip markdown code fences
        text = re.sub(r'```(?:json)?\s*', '', text)
        text = text.strip()
        # Find the outermost { … }
        start = text.find('{')
        if start == -1:
            return {}
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        return {}
        return {}

    @staticmethod
    def _slug(name: str) -> str:
        from django.utils.text import slugify
        return slugify(name)[:255] or 'company'

    @staticmethod
    def _safe_int(value) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None


# ── Thread entry point ────────────────────────────────────────────────────────

def run_pipeline_in_thread(job_pk: int):
    """
    Start the ingestion pipeline in a daemon thread.
    Call this from the view immediately after creating the IngestionJob.
    """
    def _target():
        # Django DB connections are per-thread; close the inherited one first
        from django.db import connection
        connection.close()
        IngestionPipeline(job_pk).run()

    t = threading.Thread(target=_target, name=f'ingestion-{job_pk}', daemon=True)
    t.start()
    return t
