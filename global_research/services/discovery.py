"""
global_research/services/discovery.py — turns extracted claims into
TechnologyCandidate / ManufacturerProfile / ProductCandidate rows.

Manufacturers are never a new org directory: every manufacturer resolves
through `capability_graph.services.organisations.get_or_create_organisation()`
— the same dedup-safe function the rest of the platform uses — and gaining
a real `ManufacturerProfile` also writes a real, evidence-backed
`OrganisationCapability(capability='manufacture')` row, which **is** the
Knowledge Graph edge the product spec asks for (see
docs/adr/ADR-global-research-engine.md decision 2). No second graph engine.
"""
# Predicates that describe a candidate's own numeric capability, bucketed
# into the ProductCandidate JSON fields they belong in. Never inferred —
# only predicates a provider explicitly returned are ever mapped.
CAPACITY_PREDICATES = {'rated_thermal_output_kw': 'kwh', 'recoverable_heat_kw': 'kwh'}
OPERATING_LIMIT_PREDICATES = {'max_supply_temperature_c'}
EFFICIENCY_PREDICATES = {'has_seasonal_cop', 'retrofit_efficiency_pct', 'specific_fuel_reduction_pct'}
GEOGRAPHY_PREDICATES = {'offers_local_service_coverage'}
TRL_PREDICATE = 'technology_readiness_level'

READY_STATUS_THRESHOLD = 40.0


def get_or_create_technology_category(name):
    from global_research.models import TechnologyCategory

    category, _ = TechnologyCategory.objects.get_or_create(name=name or 'Uncategorised')
    return category


def _average_confidence(claims):
    scores = [c.confidence for c in claims if c.confidence is not None]
    return round(sum(scores) / len(scores), 2) if scores else None


def create_or_update_technology_candidate(mission, category, name, claims, description=''):
    from global_research.models import TechnologyCandidate

    candidate, _ = TechnologyCandidate.objects.get_or_create(mission=mission, category=category, name=name)
    if description and not candidate.description:
        candidate.description = description
    if claims:
        candidate.source_claims.add(*claims)
    trl_claim = next((c for c in claims if c.predicate == TRL_PREDICATE and c.numeric_value is not None), None)
    if trl_claim:
        candidate.technology_readiness_level = int(trl_claim.numeric_value)
        candidate.commercial_maturity = 'concept' if trl_claim.numeric_value <= 4 else 'pilot' if trl_claim.numeric_value <= 6 else 'early_commercial'
        candidate.save()
    return refresh_technology_candidate_evidence(candidate)


def refresh_technology_candidate_evidence(candidate):
    """Re-aggregates evidence_score/confidence/status from the candidate's
    CURRENT claim confidences. Must be called again after
    evidence_scoring.score_claim() runs for those claims — at discovery
    time (inside the orchestrator's per-source loop) a claim's confidence
    is still None, so the first aggregation is necessarily a placeholder;
    without this second pass, evidence_score would stay stuck at None
    forever even though the underlying claims are fully scored."""
    all_claims = list(candidate.source_claims.all())
    candidate.evidence_score = _average_confidence(all_claims)
    candidate.confidence = candidate.evidence_score
    if candidate.status in ('discovered', 'insufficient_evidence', 'technically_relevant') and candidate.evidence_score is not None:
        candidate.status = (
            'technically_relevant' if candidate.evidence_score >= READY_STATUS_THRESHOLD else 'insufficient_evidence'
        )
    candidate.save()
    return candidate


def create_or_update_manufacturer(name, country, category=None):
    """Returns None (never a fabricated manufacturer) when no name was
    extracted. Creates/reuses the real Organisation via the one sanctioned
    dedup-safe entry point."""
    if not name:
        return None
    from capability_graph.models import OrganisationCapability
    from capability_graph.services.organisations import get_or_create_organisation

    from global_research.models import ManufacturerProfile

    organisation = get_or_create_organisation(name, org_type='company', jurisdiction=country or '')
    profile, _ = ManufacturerProfile.objects.get_or_create(
        organisation=organisation, defaults={'headquarters_country': country or ''},
    )
    if country and not profile.headquarters_country:
        profile.headquarters_country = country
        profile.save(update_fields=['headquarters_country', 'updated_at'])
    if category:
        profile.manufacturer_categories.add(category)

    OrganisationCapability.objects.get_or_create(
        organisation=organisation, capability='manufacture', jurisdiction=country or '',
        topic_domain=category.name if category else '',
        defaults={
            'evidence_source': f'global_research.ManufacturerProfile:{profile.pk}',
            'verification_state': 'unverified',
        },
    )
    return profile


def create_or_update_product(manufacturer_profile, technology_candidate, product_name, claims):
    if not product_name or manufacturer_profile is None:
        return None
    from global_research.models import ProductCandidate

    product, _ = ProductCandidate.objects.get_or_create(
        manufacturer=manufacturer_profile, technology_candidate=technology_candidate, product_name=product_name,
    )
    if claims:
        product.source_claims.add(*claims)

    from digital_twin.models import Unit

    for claim in claims:
        if claim.numeric_value is None:
            continue
        if claim.predicate in CAPACITY_PREDICATES:
            product.capacity_max = claim.numeric_value
            unit_code = CAPACITY_PREDICATES[claim.predicate]
            product.capacity_unit = Unit.objects.filter(code=unit_code).first()
        elif claim.predicate in OPERATING_LIMIT_PREDICATES:
            product.operating_limits[claim.predicate] = claim.numeric_value
        elif claim.predicate in EFFICIENCY_PREDICATES:
            product.efficiency_values[claim.predicate] = claim.numeric_value
    for claim in claims:
        if claim.predicate in GEOGRAPHY_PREDICATES and claim.object_value:
            if claim.object_value not in product.geographical_availability:
                product.geographical_availability.append(claim.object_value)

    if product.status == 'unknown':
        product.status = 'active'
    if product.lifecycle_status == 'unknown':
        product.lifecycle_status = 'established'
    product.save()
    return refresh_product_evidence(product)


def refresh_product_evidence(product):
    """Re-aggregates evidence_score/confidence from the product's CURRENT
    claim confidences — must be called again after
    evidence_scoring.score_claim() runs (see
    refresh_technology_candidate_evidence's docstring for why)."""
    all_claims = list(product.source_claims.all())
    product.evidence_score = _average_confidence(all_claims)
    product.confidence = product.evidence_score
    product.save(update_fields=['evidence_score', 'confidence', 'updated_at'])
    return product
