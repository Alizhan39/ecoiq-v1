"""
global_research/services/claim_extraction.py — deterministic,
schema-validated claim extraction.

Per docs/adr/ADR-global-research-engine.md decision 4: extraction in this
phase operates over the STRUCTURED fields a provider already returns
(`SourceCandidateResult.structured_fields['claims']` — a list of
already-labelled {predicate, object_value, numeric_value, unit_code,
conditions} dicts) — never by feeding raw document prose into a live LLM
prompt. A claim missing a required field, or with a non-numeric
`numeric_value`, is discarded and logged, never coerced or defaulted (see
docs/research_evidence_methodology.md §2).
"""
import logging

from global_research.constants import DEFAULT_EVIDENCE_TIER, EVIDENCE_TIER_BY_SOURCE_TYPE, VENDOR_OWNER_TYPES
from global_research.services import content_safety

logger = logging.getLogger('global_research.claim_extraction')

REQUIRED_CLAIM_KEYS = ('predicate', 'object_value')


def validate_claim_schema(raw_claim):
    """Returns a list of error strings — empty means valid. Never raises."""
    if not isinstance(raw_claim, dict):
        return ['claim is not a dict']
    errors = []
    for key in REQUIRED_CLAIM_KEYS:
        if not raw_claim.get(key) and raw_claim.get(key) != 0:
            errors.append(f'missing required field: {key}')
    numeric_value = raw_claim.get('numeric_value')
    if numeric_value is not None and not isinstance(numeric_value, (int, float)):
        errors.append('numeric_value must be numeric or null')
    conditions = raw_claim.get('conditions')
    if conditions is not None and not isinstance(conditions, dict):
        errors.append('conditions must be a dict')
    return errors


def evidence_tier_for_candidate(candidate):
    tier = EVIDENCE_TIER_BY_SOURCE_TYPE.get(candidate.source_type, DEFAULT_EVIDENCE_TIER)
    # A peer-reviewed paper is upgraded from its default B ceiling to A only
    # when independently reproduced — never assumed from source_type alone.
    if candidate.source_type == 'peer_reviewed_paper' and candidate.independently_reproduced:
        tier = 'A'
    return tier


def persist_source(mission, normalised):
    """Idempotent: get_or_create keyed on (mission, dedup_key) — re-running
    a search never creates a duplicate ResearchSource. Flags the source for
    a suspicious-content check exactly once, at creation."""
    from global_research.models import ResearchSource, compute_source_dedup_key

    candidate = normalised.candidate
    dedup_key = compute_source_dedup_key(candidate.url, candidate.title, candidate.publisher)
    source, created = ResearchSource.objects.get_or_create(
        mission=mission, dedup_key=dedup_key,
        defaults=dict(
            title=candidate.title, source_type=candidate.source_type, publisher=candidate.publisher,
            author=candidate.author, publication_date=candidate.publication_date, jurisdiction=candidate.jurisdiction,
            language=candidate.language, url=candidate.url, document_reference=candidate.document_reference,
            licence_or_usage_note=candidate.licence_or_usage_note, source_owner_type=candidate.source_owner_type,
            vendor_affiliation=candidate.vendor_affiliation, evidence_tier=evidence_tier_for_candidate(candidate),
            permitted_extract=normalised.permitted_extract, independently_reproduced=candidate.independently_reproduced,
            status='accepted', provider_name=candidate.provider_name,
        ),
    )
    if created:
        content_safety.flag_source_if_suspicious(source)
    return source, created


def _resolve_unit(unit_code):
    if not unit_code:
        return None
    from digital_twin.models import Unit
    return Unit.objects.filter(code=unit_code).first()


def extract_claims(mission, source, structured_fields):
    """Persists ResearchClaim rows from a source's structured_fields.
    Idempotent (update_or_create keyed on subject/predicate/source).
    Returns (created_or_updated_claims, rejected_with_errors)."""
    from global_research.models import ResearchClaim

    subject = structured_fields.get('product_name') or structured_fields.get('manufacturer_name') or source.title
    vendor_provided = source.source_owner_type in VENDOR_OWNER_TYPES
    created_claims = []
    rejected = []

    for raw_claim in structured_fields.get('claims', []):
        errors = validate_claim_schema(raw_claim)
        if errors:
            logger.info('Discarding malformed claim from source %s: %s (errors: %s)', source.pk, raw_claim, errors)
            rejected.append({'raw_claim': raw_claim, 'errors': errors})
            continue

        claim, _ = ResearchClaim.objects.update_or_create(
            source=source, mission=mission, subject=subject, predicate=raw_claim['predicate'],
            defaults=dict(
                object_value=str(raw_claim['object_value']),
                numeric_value=raw_claim.get('numeric_value'),
                unit=_resolve_unit(raw_claim.get('unit_code')),
                conditions=raw_claim.get('conditions') or {},
                quoted_extract=(source.permitted_extract or '')[:500],
                extraction_method='provider_structured_field',
                vendor_provided=vendor_provided,
                verified=False,
            ),
        )
        created_claims.append(claim)

    return created_claims, rejected
