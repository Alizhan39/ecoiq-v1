"""
global_research/services/risk.py — deterministic supply-chain/geopolitical
risk rules, modeled on `capital_guardian.services.red_flag_engine`'s
threshold-comparison, idempotent-upsert style. Every rule compares a real
stored value against an explicit constant — never an LLM judgement.
"""
FORMULA_VERSION = '1.0.0'

SINGLE_COUNTRY_CONCENTRATION_THRESHOLD = 1  # fewer than this many distinct manufacturer countries for a category
IMMATURE_TRL_THRESHOLD = 5


def evaluate_manufacturer_risks(mission, manufacturer):
    """Returns the list of SupplyChainRiskFlag rows created/updated for one
    manufacturer within a mission. Idempotent — get_or_create keyed on
    (mission, manufacturer, risk_type)."""
    from global_research.models import SupplyChainRiskFlag

    flags = []

    if manufacturer.sanctions_screening_status in ('unresolved_concern', 'confirmed_concern', 'blocked'):
        severity = 'high' if manufacturer.sanctions_screening_status in ('confirmed_concern', 'blocked') else 'medium'
        flag, _ = SupplyChainRiskFlag.objects.update_or_create(
            mission=mission, manufacturer=manufacturer, risk_type='sanctions',
            defaults=dict(
                severity=severity,
                description=f'{manufacturer.organisation.name} sanctions screening status: {manufacturer.get_sanctions_screening_status_display()}.',
                evidence_references=manufacturer.evidence_references,
            ),
        )
        flags.append(flag)

    if not manufacturer.service_regions:
        flag, _ = SupplyChainRiskFlag.objects.update_or_create(
            mission=mission, manufacturer=manufacturer, risk_type='spare_parts_risk',
            defaults=dict(
                severity='medium',
                description=f'{manufacturer.organisation.name} has no recorded service regions — spare-parts and maintenance coverage unconfirmed.',
                evidence_references=[],
            ),
        )
        flags.append(flag)

    return flags


def evaluate_technology_category_risks(mission, technology_category):
    """Single-country-dependency check: how many distinct manufacturer
    countries exist for this category, mission-wide."""
    from global_research.models import ManufacturerProfile, SupplyChainRiskFlag

    manufacturers = ManufacturerProfile.objects.filter(manufacturer_categories=technology_category)
    countries = {m.headquarters_country for m in manufacturers if m.headquarters_country}
    flags = []
    if len(countries) <= SINGLE_COUNTRY_CONCENTRATION_THRESHOLD:
        for manufacturer in manufacturers:
            flag, _ = SupplyChainRiskFlag.objects.update_or_create(
                mission=mission, manufacturer=manufacturer, risk_type='single_country_dependency',
                defaults=dict(
                    severity='medium',
                    description=f'Only {len(countries)} manufacturer country found for "{technology_category.name}" — single-source dependency risk.',
                    evidence_references=[],
                ),
            )
            flags.append(flag)
    return flags


def evaluate_product_risks(mission, product_candidate):
    from global_research.models import SupplyChainRiskFlag

    flags = []
    trl = product_candidate.technology_candidate.technology_readiness_level
    if trl is not None and trl <= IMMATURE_TRL_THRESHOLD:
        flag, _ = SupplyChainRiskFlag.objects.update_or_create(
            mission=mission, product_candidate=product_candidate, risk_type='immature_technology',
            defaults=dict(
                severity='medium',
                description=f'{product_candidate.product_name}: technology readiness level {trl} — below commercial maturity threshold.',
                evidence_references=[],
            ),
        )
        flags.append(flag)

    if product_candidate.indicative_cost_type == 'unavailable':
        flag, _ = SupplyChainRiskFlag.objects.update_or_create(
            mission=mission, product_candidate=product_candidate, risk_type='warranty_enforceability',
            defaults=dict(
                severity='low',
                description=f'{product_candidate.product_name}: no commercial terms on file yet — warranty enforceability cannot be assessed.',
                evidence_references=[],
            ),
        )
        flags.append(flag)

    return flags


def evaluate_all_risks(mission):
    """Runs every rule above for every manufacturer/category/product
    touched by this mission. Called once per orchestrator run, and again
    on demand from the UI/API."""
    from global_research.models import ManufacturerProfile, ProductCandidate, TechnologyCategory

    flags = []
    manufacturer_ids = ProductCandidate.objects.filter(technology_candidate__mission=mission).values_list('manufacturer_id', flat=True).distinct()
    for manufacturer in ManufacturerProfile.objects.filter(pk__in=manufacturer_ids):
        flags += evaluate_manufacturer_risks(mission, manufacturer)

    category_ids = mission.technology_candidates.values_list('category_id', flat=True).distinct()
    for category in TechnologyCategory.objects.filter(pk__in=category_ids):
        flags += evaluate_technology_category_risks(mission, category)

    for product in ProductCandidate.objects.filter(technology_candidate__mission=mission):
        flags += evaluate_product_risks(mission, product)

    return flags
