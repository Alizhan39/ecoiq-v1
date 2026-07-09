"""
harvester/services/fetchers.py — the FETCH + VALIDATE layer for the Data
Ingestion Engine (Phase 1). Reuses backend_intelligence_engine.services.
http_client.fetch() for the actual HTTP call (timeout/retry/backoff/user-
agent/structured logging already implemented there) — this module adds only
what's genuinely ingestion-specific on top: max response size, content-type
validation, and robots.txt compliance for HTML sources.

Exactly three real source types, matching the spec's "small number of real
source types" instruction — no plugin framework, no library added that
isn't already a dependency (httpx via the shared client, pandas for CSV,
BeautifulSoup/lxml already present for the existing ingestion app's HTML
handling, urllib.robotparser is Python's own standard library):

  companies_house  — real UK government JSON API (already has a working,
                     proven integration in companies/management/commands/
                     ingest_companies_house.py — reuses its UK_COMPANY_NUMBERS
                     mapping and endpoint rather than re-deriving either)
  csv_dataset      — any CSV endpoint, parsed with pandas (already a
                     dependency; no new library)
  url_recheck      — re-fetches a URL EcoIQ already has on file (an
                     existing harvester.Evidence.url), the safest possible
                     "public HTML page" source since it's a URL EcoIQ chose
                     to record before, not one newly discovered by crawling

Every fetcher returns a FetchOutcome — never raises, never fabricates: a
network/validation failure is a real, honest `error`, not an empty success.
"""
import logging
import urllib.robotparser
from dataclasses import dataclass, field
from urllib.parse import urlparse

import pandas as pd

from backend_intelligence_engine.services.http_client import fetch as http_fetch
from harvester.adapters import EvidenceCandidate, classify_text

logger = logging.getLogger(__name__)

MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB — a bulletin/CSV/API response, never a large file dump
ROBOTS_CACHE = {}  # netloc -> RobotFileParser, per-process cache (Phase 1 scale doesn't need Redis for this)


@dataclass
class FetchOutcome:
    success: bool
    candidates: list = field(default_factory=list)
    content_hash_input: str = ''  # raw text used for change-detection hashing, '' on failure
    error: str = ''
    skipped_reason: str = ''


def _validate_size_and_type(result, expected_content_types):
    if len(result.content) > MAX_RESPONSE_BYTES:
        return f'Response too large ({len(result.content)} bytes, max {MAX_RESPONSE_BYTES})'
    content_type = (result.headers.get('content-type') or '').split(';')[0].strip().lower()
    if expected_content_types and content_type and content_type not in expected_content_types:
        return f'Unexpected content-type "{content_type}", expected one of {expected_content_types}'
    if not result.content:
        return 'Empty response body'
    return None


def _robots_allows(url):
    """Real, honest robots.txt compliance check — a source that disallows
    fetching this path is SKIPPED, never fetched anyway."""
    parsed = urlparse(url)
    netloc = parsed.netloc
    if netloc not in ROBOTS_CACHE:
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(f'{parsed.scheme}://{netloc}/robots.txt')
        try:
            parser.read()
        except Exception:
            # robots.txt unreachable — conservative default: allow (matches
            # urllib.robotparser's own behaviour when it can't fetch the file).
            pass
        ROBOTS_CACHE[netloc] = parser
    try:
        return ROBOTS_CACHE[netloc].can_fetch('EcoIQ-Bot/1.0', url)
    except Exception:
        return True


def fetch_companies_house(company_slug):
    """
    Real Companies House UK API call — reuses the exact mapping and endpoint
    already proven in companies/management/commands/ingest_companies_house.py,
    now wired through the shared retrying httpx client instead of a bare
    `requests.get`, and producing an EvidenceCandidate the existing dedup
    engine can store, instead of writing to DataIngestionLog directly.
    """
    from django.conf import settings

    from companies.management.commands.ingest_companies_house import CH_BASE, UK_COMPANY_NUMBERS

    company_number = UK_COMPANY_NUMBERS.get(company_slug)
    if not company_number:
        return FetchOutcome(success=False, skipped_reason=f'No Companies House number mapped for "{company_slug}"')

    api_key = getattr(settings, 'COMPANIES_HOUSE_API_KEY', '').strip()
    if not api_key:
        return FetchOutcome(success=False, skipped_reason='COMPANIES_HOUSE_API_KEY not configured')

    result = http_fetch(f'{CH_BASE}/company/{company_number}', auth=(api_key, ''))
    if not result.success:
        return FetchOutcome(success=False, error=result.error or f'HTTP {result.status_code}')

    validation_error = _validate_size_and_type(result, {'application/json'})
    if validation_error:
        return FetchOutcome(success=False, error=validation_error)

    data = result.json_data or {}
    company_status = data.get('company_status', '')
    sic_codes = data.get('sic_codes', [])
    registered_name = data.get('company_name', '')
    statement = (
        f'{registered_name} (Companies House {company_number}): status={company_status}, '
        f'SIC codes={", ".join(sic_codes) or "none listed"}, jurisdiction={data.get("jurisdiction", "")}.'
    )
    candidate = EvidenceCandidate(
        company_slug=company_slug, category='governance', statement=statement, source_type='companies_house',
        title=f'Companies House record — {registered_name or company_slug}',
        url=f'https://find-and-update.company-information.service.gov.uk/company/{company_number}',
        source_owner='Companies House',
    )
    return FetchOutcome(success=True, candidates=[candidate], content_hash_input=statement)


def fetch_csv_dataset(source_url, company_slug, category='financial'):
    """
    Generic CSV ingestion — pandas.read_csv over an in-memory buffer (no new
    library). Each row becomes one EvidenceCandidate; the caller decides
    which column holds the fact statement via a simple, honest convention:
    a `statement` column if present, else the first text-like column.
    """
    import io

    result = http_fetch(source_url)
    if not result.success:
        return FetchOutcome(success=False, error=result.error or f'HTTP {result.status_code}')

    validation_error = _validate_size_and_type(result, {'text/csv', 'application/csv', 'text/plain'})
    if validation_error:
        return FetchOutcome(success=False, error=validation_error)

    try:
        df = pd.read_csv(io.BytesIO(result.content))
    except Exception as exc:
        return FetchOutcome(success=False, error=f'CSV parse error: {type(exc).__name__}: {exc}')

    if df.empty:
        return FetchOutcome(success=False, error='CSV contained no rows')

    statement_col = 'statement' if 'statement' in df.columns else df.select_dtypes(include='object').columns[0] if len(df.select_dtypes(include='object').columns) else None
    if statement_col is None:
        return FetchOutcome(success=False, error='CSV has no text column to use as a statement')

    candidates = []
    for _, row in df.iterrows():
        stmt = str(row[statement_col]).strip()
        if not stmt or stmt.lower() == 'nan':
            continue
        candidates.append(EvidenceCandidate(
            company_slug=company_slug, category=category, statement=stmt, source_type='csv_dataset',
            title=stmt[:120], url=source_url, source_owner='CSV dataset',
        ))
    if not candidates:
        return FetchOutcome(success=False, error='No usable rows found in CSV')

    return FetchOutcome(success=True, candidates=candidates, content_hash_input=result.text)


def fetch_url_recheck(source_url, company_slug, category='strategy'):
    """
    Re-fetches a URL EcoIQ already has on file — the safest possible "public
    HTML page" source, since it's a URL EcoIQ itself chose to record earlier
    (an existing harvester.Evidence.url), not a newly-discovered one. Honours
    robots.txt: if disallowed, this is a SKIP, never a fetch.
    """
    if not _robots_allows(source_url):
        return FetchOutcome(success=False, skipped_reason=f'robots.txt disallows fetching {source_url}')

    result = http_fetch(source_url)
    if not result.success:
        return FetchOutcome(success=False, error=result.error or f'HTTP {result.status_code}')

    validation_error = _validate_size_and_type(result, set())  # any content-type accepted, size still checked
    if validation_error:
        return FetchOutcome(success=False, error=validation_error)

    content_type = (result.headers.get('content-type') or '').lower()
    if 'html' in content_type:
        from bs4 import BeautifulSoup
        text = BeautifulSoup(result.text, 'lxml').get_text(separator=' ', strip=True)
    else:
        text = result.text

    text = text[:2000].strip()
    if not text:
        return FetchOutcome(success=False, error='No extractable text content')

    candidate = EvidenceCandidate(
        company_slug=company_slug, category=classify_text(text, default=category), statement=text[:600],
        source_type='press_release', title=text[:120], url=source_url, excerpt=text[:600], full_text=text,
    )
    return FetchOutcome(success=True, candidates=[candidate], content_hash_input=text)
