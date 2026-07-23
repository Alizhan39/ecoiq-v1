"""
good_agents/services/provider_adapters.py — real SignalProvider adapters
(PR4 Phases 1-3). Exactly 3, matching the spec's "small number of real,
bounded source types" instruction — no plugin framework, no arbitrary URL
fetching, no global internet scraping:

  usgs-significant-earthquakes   — USGS (US Geological Survey), real-time
                                    significant-earthquakes GeoJSON feed.
                                    ENVIRONMENTAL_RISK signals.
  govuk-search                    — GOV.UK Search API, queried with a small
                                    fixed set of grant/funding/policy terms.
                                    FUNDING_AVAILABLE / POLICY_CHANGE signals.
  uk-ea-flood-monitoring          — UK Environment Agency real-time flood
                                    warnings API. ENVIRONMENTAL_RISK /
                                    INFRASTRUCTURE_OPPORTUNITY signals.
                                    Frequently returns zero active warnings
                                    — that is a real, honest result, not an
                                    error (see docs/GLOBAL_GOOD_DISCOVERY.md).

Provider adapter contract (Phase 2): each adapter is a plain function
`fetch_raw_signals(provider) -> ProviderFetchResult`. It fetches,
normalises into raw signal dicts (the shape
`services.signals.normalise_signal` expects), and validates — but never
creates a `WorldSignal` or `GoodOpportunity` directly; every raw signal it
returns still passes through the full normalise -> dedup -> cluster ->
evidence gate -> discovery engine path, unchanged from PR3.

Every adapter here NEVER raises — a malformed/unexpected response is a
real, honest `ProviderFetchResult(success=False, error=...)`, exactly like
`harvester.services.fetchers.FetchOutcome`'s convention. This is what lets
`services/ingestion.py` isolate one provider's failure from the rest of a
run.
"""
import datetime
import logging

from django.utils import timezone as dj_timezone
from dataclasses import dataclass, field

from good_agents.services.safe_http import safe_fetch

logger = logging.getLogger(__name__)


@dataclass
class ProviderFetchResult:
    success: bool
    raw_signals: list = field(default_factory=list)
    error: str = ''
    items_fetched: int = 0
    items_after_validation: int = 0


def _epoch_ms_to_dt(epoch_ms):
    if not epoch_ms:
        return None
    try:
        return dj_timezone.make_aware(datetime.datetime.utcfromtimestamp(epoch_ms / 1000.0), datetime.timezone.utc)
    except (ValueError, OSError, OverflowError):
        return None


def _parse_iso(value):
    if not value:
        return None
    try:
        dt = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
        return dt if dt.tzinfo else dj_timezone.make_aware(dt, datetime.timezone.utc)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Adapter 1 — USGS Significant Earthquakes
# ---------------------------------------------------------------------------

USGS_URL = 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.geojson'
USGS_ALLOWED_HOSTS = frozenset({'earthquake.usgs.gov'})


def fetch_usgs_significant_earthquakes(provider):
    result = safe_fetch(USGS_URL, allowed_hosts=USGS_ALLOWED_HOSTS)
    if not result.success or result.json_data is None:
        return ProviderFetchResult(success=False, error=result.error or 'USGS: no JSON body returned')

    features = result.json_data.get('features', [])
    raw_signals = []
    for feature in features:
        props = feature.get('properties') or {}
        mag = props.get('mag')
        place = props.get('place') or 'Unknown location'
        if mag is None:
            continue  # insufficient evidence to classify severity — skip rather than guess (Phase 3)
        raw_signals.append({
            'signal_type': 'environmental_risk',
            'title': props.get('title') or f'M {mag} — {place}',
            'summary': f'A magnitude {mag} earthquake was recorded near {place} (USGS significant-earthquakes feed).',
            'region': place,
            'sector': 'seismic hazard',
            'source_url': props.get('url', ''),
            'publisher': 'USGS (US Geological Survey)',
            'published_at': _epoch_ms_to_dt(props.get('time')),
            'raw_evidence_ref': f'usgs:{feature.get("id", "")}',
            'source_excerpt': props.get('title', ''),
            # 'reviewed' means a human seismologist confirmed the automatic
            # detection — the real, documented USGS confidence signal, not
            # an invented one.
            'confidence': 90.0 if props.get('status') == 'reviewed' else 55.0,
            'severity': round(min(100.0, max(5.0, (mag - 4.0) * 22.0)), 1),
            'tags': ['environment', 'environmental_risk'],
            # USGS is an authoritative scientific network reporting a
            # directly measured value (magnitude) — a real fact, not an inference.
            'asserted_as_fact': True,
        })
    return ProviderFetchResult(
        success=True, raw_signals=raw_signals,
        items_fetched=len(features), items_after_validation=len(raw_signals),
    )


# ---------------------------------------------------------------------------
# Adapter 2 — GOV.UK Search API
# ---------------------------------------------------------------------------

GOVUK_SEARCH_URL = 'https://www.gov.uk/api/search.json'
GOVUK_ALLOWED_HOSTS = frozenset({'www.gov.uk'})
# A small, fixed set of queries — never an open/arbitrary search term from
# user input (Phase 1: "do not attempt global internet scraping").
GOVUK_SEARCH_QUERIES = [
    'energy efficiency grant', 'clean heating grant funding', 'flood defence funding',
]
GOVUK_FUNDING_KEYWORDS = ('grant', 'fund', 'funding', 'subsidy')


def fetch_govuk_search(provider, queries=None):
    queries = queries or GOVUK_SEARCH_QUERIES
    raw_signals = []
    items_fetched = 0
    last_error = ''
    any_success = False

    for query in queries:
        result = safe_fetch(GOVUK_SEARCH_URL, allowed_hosts=GOVUK_ALLOWED_HOSTS, params={'q': query, 'count': 5})
        if not result.success or result.json_data is None:
            last_error = result.error or f'GOV.UK search: no JSON body for query {query!r}'
            continue
        any_success = True
        results = result.json_data.get('results', [])
        items_fetched += len(results)
        for item in results:
            title = item.get('title', '')
            description = item.get('description') or ''
            link = item.get('link', '')
            if not title or not link:
                continue
            is_funding = any(kw in (title + ' ' + description).lower() for kw in GOVUK_FUNDING_KEYWORDS)
            raw_signals.append({
                'signal_type': 'funding_available' if is_funding else 'policy_change',
                'title': title,
                'summary': description or title,
                'sector': item.get('format', ''),
                'source_url': f'https://www.gov.uk{link}' if link.startswith('/') else link,
                'publisher': 'GOV.UK',
                'published_at': _parse_iso(item.get('public_timestamp')),
                'raw_evidence_ref': f'govuk-search:{link}',
                'source_excerpt': description,
                # Search snippets are a real, authoritative government
                # publisher's own listing, but a truncated automated search
                # result — not classified as a directly-asserted fact.
                'confidence': 55.0,
                'severity': 20.0,
                'tags': ['policy', 'funding' if is_funding else 'policy_change', f'query:{query}'],
                'asserted_as_fact': False,
            })

    if not any_success:
        return ProviderFetchResult(success=False, error=last_error or 'GOV.UK search: all queries failed')
    return ProviderFetchResult(
        success=True, raw_signals=raw_signals, items_fetched=items_fetched, items_after_validation=len(raw_signals),
    )


# ---------------------------------------------------------------------------
# Adapter 3 — UK Environment Agency real-time flood monitoring
# ---------------------------------------------------------------------------

EA_FLOODS_URL = 'https://environment.data.gov.uk/flood-monitoring/id/floods'
EA_ALLOWED_HOSTS = frozenset({'environment.data.gov.uk'})
# severityLevel: 1=Severe Flood Warning, 2=Flood Warning, 3=Flood Alert,
# 4=Warning No Longer In Force (documented at
# environment.data.gov.uk/flood-monitoring/doc/reference).
EA_SEVERITY_TO_SCORE = {1: 95.0, 2: 75.0, 3: 45.0, 4: 5.0}


def fetch_uk_ea_flood_monitoring(provider, min_severity=3):
    result = safe_fetch(EA_FLOODS_URL, allowed_hosts=EA_ALLOWED_HOSTS, params={'min-severity': min_severity})
    if not result.success or result.json_data is None:
        return ProviderFetchResult(success=False, error=result.error or 'EA flood monitoring: no JSON body returned')

    items = result.json_data.get('items', [])
    raw_signals = []
    for item in items:
        severity_level = item.get('severityLevel')
        description = item.get('description') or ''
        area_name = item.get('eaAreaName') or item.get('eaRegionName') or 'Unknown area (UK)'
        if severity_level is None or not description:
            continue  # insufficient evidence — skip rather than guess a severity (Phase 3)
        raw_signals.append({
            'signal_type': 'environmental_risk',
            'title': f'{item.get("severity", "Flood warning")} — {area_name}',
            'summary': description,
            'region': area_name,
            'sector': 'flood risk / infrastructure',
            'source_url': item.get('@id', ''),
            'publisher': 'UK Environment Agency',
            'published_at': _parse_iso(item.get('timeRaised')),
            'raw_evidence_ref': f'ea-flood:{item.get("floodAreaID", "")}',
            'source_excerpt': description,
            # A live, official government regulator's own real-time
            # instrument-derived warning level — a measured fact, not an inference.
            'confidence': 85.0,
            'severity': EA_SEVERITY_TO_SCORE.get(severity_level, 30.0),
            'tags': ['environment', 'flood', f'severity_level:{severity_level}'],
            'asserted_as_fact': True,
        })
    return ProviderFetchResult(
        success=True, raw_signals=raw_signals, items_fetched=len(items), items_after_validation=len(raw_signals),
    )


# ---------------------------------------------------------------------------
# Registry — one adapter function per SignalProvider.slug
# ---------------------------------------------------------------------------

PROVIDER_ADAPTERS = {
    'usgs-significant-earthquakes': fetch_usgs_significant_earthquakes,
    'govuk-search': fetch_govuk_search,
    'uk-ea-flood-monitoring': fetch_uk_ea_flood_monitoring,
}


def fetch_from_provider(provider):
    """
    One provider, isolated: never raises. An unknown/unregistered provider
    slug is a real, honest failure, not a silent no-op.
    """
    adapter = PROVIDER_ADAPTERS.get(provider.slug)
    if adapter is None:
        return ProviderFetchResult(success=False, error=f'No registered adapter for provider slug {provider.slug!r}')
    try:
        return adapter(provider)
    except Exception as exc:  # noqa: BLE001 — a provider's own bug must never crash the run
        logger.exception('good_agents.provider_adapters: adapter for %s raised', provider.slug)
        return ProviderFetchResult(success=False, error=f'{type(exc).__name__}: {exc}')
