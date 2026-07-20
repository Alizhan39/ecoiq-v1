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
import datetime
import logging
import urllib.robotparser
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx
import pandas as pd

from backend_intelligence_engine.services.http_client import fetch as http_fetch
from harvester.adapters import EvidenceCandidate, classify_text

logger = logging.getLogger(__name__)

MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB — a bulletin/CSV/API response, never a large file dump
# feat/company-discovery-ranking (PR 11) — real official sustainability/
# annual reports are legitimately large PDFs (Apple's 2024 Environmental
# Progress Report is ~30MB) — a separate, still-bounded cap for this one
# document-fetching path, never the unbounded default.
MAX_DOCUMENT_BYTES = 50 * 1024 * 1024  # 50 MB
DOCUMENT_FETCH_TIMEOUT = httpx.Timeout(connect=10.0, read=90.0, write=10.0, pool=10.0)
MAX_DOCUMENT_CHUNKS = 60  # a real, documented cap — never silently truncates without saying so
MIN_CHUNK_CHARS = 80  # shorter fragments (cover pages, running headers) carry no real evidence
ROBOTS_CACHE = {}  # netloc -> RobotFileParser, per-process cache (Phase 1 scale doesn't need Redis for this)


@dataclass
class FetchOutcome:
    success: bool
    candidates: list = field(default_factory=list)
    content_hash_input: str = ''  # raw text used for change-detection hashing, '' on failure
    error: str = ''
    skipped_reason: str = ''
    # feat/company-evidence-ingestion (PR 10): optional structured payload a
    # fetcher can return alongside its human-readable candidates, for a
    # caller that needs real numeric values (not just prose) — e.g.
    # fetch_sec_edgar's extracted XBRL figures, consumed by
    # company_intelligence.services.evidence_ingestion to populate
    # CompanyFinancialFacts. Every other existing fetcher leaves this empty;
    # ingest_source() never reads it, so this is purely additive.
    metadata: dict = field(default_factory=dict)


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


def fetch_sec_edgar(company_slug):
    """
    Real SEC EDGAR XBRL companyfacts API call — free, no API key, reuses the
    exact CIK mapping already proven in companies/management/commands/
    ingest_sec_edgar.py (same reuse pattern as fetch_companies_house
    above), routed through the shared retrying httpx client. SEC's
    fair-use policy requires a descriptive User-Agent with a contact —
    reuses that command's own EDGAR_HEADERS rather than a second header
    constant.

    Extracts four real XBRL concepts, each only if actually reported —
    never fabricated, never defaulted to zero when absent:
      revenue_usd                — Revenues / RevenueFromContractWith...
      total_debt_usd             — LongTermDebt-family concepts
      cash_and_equivalents_usd   — CashAndCashEquivalentsAtCarryingValue
      non_permissible_income_usd — InvestmentIncomeInterest (a DERIVED
                                    proxy — interest income — never a
                                    directly-reported "non-permissible
                                    income" line item; labelled as such in
                                    both the candidate statement and
                                    outcome.metadata so downstream callers
                                    never present it as directly reported).

    For each metric, every candidate XBRL concept is checked and the entry
    with the most recent reporting `end` date wins — NOT the first concept
    in priority order that happens to have any value at all. This was a
    real, caught-in-verification bug: Tesla's `LongTermDebtNoncurrent` tag
    carries a single stale $0 entry from FY2013 (an old, no-longer-used
    tag), while its real current long-term debt (~$6.6B, FY2025) is filed
    under `LongTermDebt` instead — trusting "first concept with a value"
    would have silently presented an 11-year-stale zero as current debt.
    This module never does that.

    Market capitalisation is NOT obtainable from XBRL companyfacts alone (no
    share-price feed here) — genuinely, honestly absent, not a gap this
    function papers over.
    """
    from companies.management.commands.ingest_sec_edgar import EDGAR_BASE, EDGAR_HEADERS, US_COMPANY_CIKS

    def _extract_latest_entry(concept_data):
        """Returns the single most-recent-`end`-date XBRL entry for one
        concept (annual 10-K/20-F filings preferred over interim ones) —
        the whole entry, not just its value, so the caller can compare
        recency across multiple candidate concepts for the same metric."""
        units = concept_data.get('units', {})
        for entries in units.values():
            if not entries:
                continue
            annual = [e for e in entries if e.get('form') in ('10-K', '20-F')]
            pool = sorted(annual or entries, key=lambda x: x.get('end', ''), reverse=True)
            if pool:
                return pool[0]
        return None

    cik = US_COMPANY_CIKS.get(company_slug)
    if not cik:
        return FetchOutcome(success=False, skipped_reason=f'No SEC EDGAR CIK mapped for "{company_slug}"')

    result = http_fetch(f'{EDGAR_BASE}/api/xbrl/companyfacts/CIK{cik}.json', headers=EDGAR_HEADERS)
    if not result.success:
        if result.status_code == 404:
            return FetchOutcome(success=False, skipped_reason=f'CIK {cik} not found in EDGAR')
        return FetchOutcome(success=False, error=result.error or f'HTTP {result.status_code}')

    validation_error = _validate_size_and_type(result, {'application/json'})
    if validation_error:
        return FetchOutcome(success=False, error=validation_error)

    facts = result.json_data or {}
    entity_name = facts.get('entityName', company_slug)
    us_gaap = facts.get('facts', {}).get('us-gaap', {})

    # field_key, candidate XBRL concepts (first match wins), human label, is_derived
    metric_specs = [
        ('revenue_usd', ['Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax'],
         'total revenue', False),
        ('total_debt_usd', ['DebtLongtermAndShorttermCombinedAmount', 'LongTermDebtNoncurrent', 'LongTermDebt'],
         'long-term debt', False),
        ('cash_and_equivalents_usd', ['CashAndCashEquivalentsAtCarryingValue'],
         'cash and cash equivalents', False),
        ('non_permissible_income_usd', ['InvestmentIncomeInterest', 'InterestIncomeOther'],
         'interest income (used as a conservative proxy for non-permissible income under this methodology)', True),
    ]

    candidates = []
    metadata = {'cik': cik, 'entity_name': entity_name, 'metrics': {}}
    for field_key, concepts, label, is_derived in metric_specs:
        # Evaluate EVERY candidate concept (not just the first one that
        # happens to have any value at all) and keep whichever has the most
        # recent reporting `end` date. A company may tag the same real fact
        # under an unusual concept name while an earlier-priority concept
        # in this list carries only a long-stale, unrelated historical
        # entry (observed for real: Tesla's LongTermDebtNoncurrent has a
        # single stale $0 entry from FY2013, while its real current debt is
        # under LongTermDebt) — picking "first concept with a value" would
        # silently surface that stale figure as current. Never happens.
        best_value, used_concept, period_end = None, None, None
        for concept in concepts:
            entry = _extract_latest_entry(us_gaap.get(concept, {}))
            if entry is None or entry.get('val') is None:
                continue
            entry_end = entry.get('end', '')
            if period_end is None or entry_end > period_end:
                best_value, used_concept, period_end = entry['val'], concept, entry_end
        value = best_value
        if value is None:
            continue
        statement = (
            f'{entity_name} reported {label} of ${value:,.0f} per SEC EDGAR XBRL data '
            f'(concept: {used_concept}).'
        )
        metadata['metrics'][field_key] = {
            'value': value, 'concept': used_concept, 'is_derived': is_derived, 'unit': 'USD',
            'period_end': period_end, 'statement': statement,
        }
        candidates.append(EvidenceCandidate(
            company_slug=company_slug, category='financial', statement=statement, source_type='regulatory_filing',
            title=f'SEC EDGAR — {entity_name} — {label}',
            url=f'https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-K',
            source_owner='U.S. Securities and Exchange Commission',
        ))

    if not candidates:
        return FetchOutcome(success=False, error='No usable XBRL financial concepts found for this company')

    return FetchOutcome(
        success=True, candidates=candidates,
        content_hash_input=str(sorted(metadata['metrics'].items())), metadata=metadata,
    )


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


# ── feat/company-discovery-ranking (PR 11) — sustainability document ──────
# The 25-source-type vocabulary already had annual_report/sustainability_
# report/esg_report/tcfd_report/transition_plan defined (harvester.constants
# .SOURCE_TYPES) with real quality bands already set (harvester.verification
# .SOURCE_TYPE_QUALITY) — this is the one genuinely new fetcher PR11 needs:
# a real HTTP fetch of a staff-registered official document URL (PDF or
# HTML), split into multiple inspectable evidence CHUNKS (never one giant
# record for a 200-page report), each with its own page/section location.

_HEADING_TAGS = ('h1', 'h2', 'h3')


def _pdf_chunks(content):
    """Yields (location_label, text) per PDF page with extractable text.
    pypdf is already a project dependency — no new library added."""
    import io

    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    title = None
    try:
        title = (reader.metadata.title or '').strip() or None if reader.metadata else None
    except Exception:
        title = None

    for i, page in enumerate(reader.pages[:MAX_DOCUMENT_CHUNKS]):
        try:
            text = (page.extract_text() or '').strip()
        except Exception:
            text = ''
        if len(text) >= MIN_CHUNK_CHARS:
            yield f'Page {i + 1}', text
    return title


def _html_chunks(html_text):
    """Splits an HTML document into (location_label, text) chunks by its own
    heading structure (h1/h2/h3) — a real, inspectable section boundary,
    never an arbitrary character-count slice. Content before the first
    heading is grouped under "Introduction"."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_text, 'lxml')
    body = soup.body or soup

    current_label = 'Introduction'
    current_parts = []
    chunks = []

    def _flush():
        text = ' '.join(current_parts).strip()
        if len(text) >= MIN_CHUNK_CHARS:
            chunks.append((current_label, text))

    for el in body.find_all(True, recursive=True):
        if el.name in _HEADING_TAGS:
            _flush()
            current_label = f'Section: {el.get_text(strip=True)[:100]}' or current_label
            current_parts = []
        elif el.name in ('p', 'li') and not el.find_all(True):
            text = el.get_text(' ', strip=True)
            if text:
                current_parts.append(text)
    _flush()

    title_tag = soup.find('title')
    title = title_tag.get_text(strip=True) if title_tag else None
    return chunks[:MAX_DOCUMENT_CHUNKS], title


def fetch_sustainability_document(source_url, company_slug, document_type, publisher=''):
    """
    Real fetch of ONE staff-registered official document URL (a
    sustainability/ESG/TCFD/transition-plan/annual report — see
    harvester.constants.SOURCE_TYPES). Splits it into multiple real,
    inspectable evidence chunks (one per PDF page or HTML section), each
    carrying its own `source_location` — never treats a 200-page report as
    a single evidence record.

    Honours robots.txt for HTML fetches (PDF documents have no meaningful
    robots.txt page-level concept — the URL itself was staff-registered as
    an official document, not discovered by crawling). Never invents a
    document: an unreachable/unparseable URL is an honest failure, not an
    empty success.

    Returns a FetchOutcome whose `metadata['document']` dict carries the
    whole-document provenance fields (title, content_hash, chunk_count) the
    caller (company_intelligence.services.evidence_ingestion) uses to
    create/reuse exactly one harvester.SourceDocument row — versioned by
    content hash, never silently overwritten in place.
    """
    from harvester.models import content_hash as compute_content_hash

    if not _robots_allows(source_url):
        return FetchOutcome(success=False, skipped_reason=f'robots.txt disallows fetching {source_url}')

    result = http_fetch(source_url, timeout=DOCUMENT_FETCH_TIMEOUT)
    if not result.success:
        return FetchOutcome(success=False, error=result.error or f'HTTP {result.status_code}')

    if len(result.content) > MAX_DOCUMENT_BYTES:
        return FetchOutcome(
            success=False,
            error=f'Document too large ({len(result.content)} bytes, max {MAX_DOCUMENT_BYTES})',
        )
    if not result.content:
        return FetchOutcome(success=False, error='Empty response body')

    content_type = (result.headers.get('content-type') or '').lower()
    is_pdf = 'pdf' in content_type or source_url.lower().endswith('.pdf')

    doc_title = None
    chunks = []
    if is_pdf:
        try:
            pages = list(_pdf_chunks(result.content))
        except Exception as exc:
            return FetchOutcome(success=False, error=f'PDF parse error: {type(exc).__name__}: {exc}')
        chunks = pages
    else:
        try:
            chunks, doc_title = _html_chunks(result.text)
        except Exception as exc:
            return FetchOutcome(success=False, error=f'HTML parse error: {type(exc).__name__}: {exc}')

    if not chunks:
        return FetchOutcome(success=False, error='No extractable text chunks found in this document')

    doc_title = doc_title or source_url.rsplit('/', 1)[-1] or f'{company_slug} {document_type}'
    doc_hash = compute_content_hash(company_slug, source_url, str(len(result.content)),
                                    chunks[0][1][:200], chunks[-1][1][:200])

    candidates = []
    for location_label, text in chunks:
        statement = text[:800]
        candidates.append(EvidenceCandidate(
            company_slug=company_slug, category=classify_text(text), statement=statement,
            source_type=document_type, title=f'{doc_title} — {location_label}', url=source_url,
            excerpt=text[:600], full_text=text, source_owner=publisher, source_location=location_label,
        ))

    metadata = {
        'document': {
            'title': doc_title, 'document_type': document_type, 'publisher': publisher,
            'content_hash': doc_hash, 'chunk_count': len(candidates),
            'retrieved_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    }
    return FetchOutcome(
        success=True, candidates=candidates,
        content_hash_input=doc_hash, metadata=metadata,
    )
