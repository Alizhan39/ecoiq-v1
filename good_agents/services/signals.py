"""
good_agents/services/signals.py — signal normalisation, deduplication, and
fact/claim/inference classification (PR3 Phases 2-3).

No live ingestion happens here — `normalise_signal` takes a plain dict
(supplied by a caller: a management command, a future real SignalProvider
adaptor, or a test) and turns it into a persisted `WorldSignal`. This
module never fetches anything from the network itself.
"""
import hashlib
import re

from django.utils import timezone

from good_agents.models import WorldSignal

# A raw signal is only classified 'fact' if it explicitly says so AND comes
# from a high-trust provider type — never inferred from wording alone.
# Everything else defaults to 'claim' (third-party assertion) or
# 'inference' (EcoIQ's own derived read) — Phase 2's explicit ban on
# auto-treating third-party claims as facts.
HIGH_TRUST_PROVIDER_TYPES = frozenset({
    'government_publication', 'regulatory_announcement', 'public_dataset',
    'climate_environmental_dataset', 'energy_data', 'procurement_data',
})


def compute_dedup_key(signal_type, geography_label, sector, title):
    """sha256 of the normalised (type, geography, sector, title) tuple — the anti-duplication key (Phase 27)."""
    normalised_title = re.sub(r'\s+', ' ', (title or '').strip().lower())
    normalised_title = re.sub(r'[^\w\s]', '', normalised_title)
    payload = '|'.join([signal_type or '', (geography_label or '').lower(), (sector or '').lower(), normalised_title])
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def classify_content(raw, provider=None):
    """
    Deterministic fact/claim/inference classification. `raw` may set
    `raw['asserted_as_fact'] = True` (the provider explicitly vouches for
    it) — that alone is not enough; the provider must also be high-trust.
    Anything EcoIQ itself derived (no external provider) is 'inference'.
    """
    if provider is None:
        return 'inference'
    if raw.get('asserted_as_fact') and provider.provider_type in HIGH_TRUST_PROVIDER_TYPES:
        return 'fact'
    return 'claim'


def compute_freshness(published_at):
    """0-100, decaying with age. No published_at at all -> 0 (never assume freshness)."""
    if published_at is None:
        return 0.0
    age_days = max((timezone.now() - published_at).days, 0)
    if age_days <= 7:
        return 100.0
    if age_days >= 365:
        return 0.0
    return round(100.0 * (1 - age_days / 365.0), 1)


def normalise_signal(raw, provider=None):
    """
    raw: a plain dict with (at minimum) signal_type/title; optional summary,
    geography (CountryProfile instance or None), region, sector, entities,
    source_url, publisher, published_at, raw_evidence_ref, confidence,
    severity, potential_affected_population, tags, asserted_as_fact.

    Returns a persisted, but not-yet-clustered, WorldSignal. Idempotent on
    dedup_key + source_url: re-normalising the same raw signal from the same
    URL returns the existing row rather than creating a duplicate at the DB
    level (clustering, separately, also groups near-duplicates that don't
    share an exact dedup_key/URL — see services/clustering.py).
    """
    geography = raw.get('geography')
    geography_label = raw.get('region') or (geography.name if geography else '')
    dedup_key = compute_dedup_key(raw['signal_type'], geography_label, raw.get('sector', ''), raw['title'])

    existing = None
    if raw.get('source_url'):
        existing = WorldSignal.objects.filter(dedup_key=dedup_key, source_url=raw['source_url']).first()
    if existing is not None:
        return existing, False

    signal = WorldSignal.objects.create(
        signal_type=raw['signal_type'],
        title=raw['title'],
        summary=raw.get('summary', ''),
        geography=geography,
        region=raw.get('region', ''),
        sector=raw.get('sector', ''),
        entities=raw.get('entities', []),
        provider=provider,
        source_url=raw.get('source_url', ''),
        publisher=raw.get('publisher', ''),
        published_at=raw.get('published_at'),
        raw_evidence_ref=raw.get('raw_evidence_ref', ''),
        confidence=raw.get('confidence', 0.0),
        freshness=compute_freshness(raw.get('published_at')),
        severity=raw.get('severity', 0.0),
        potential_affected_population=raw.get('potential_affected_population', ''),
        tags=raw.get('tags', []),
        content_classification=classify_content(raw, provider),
        dedup_key=dedup_key,
        status='new',
    )
    return signal, True
