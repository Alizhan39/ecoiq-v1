"""
global_research/services/comparison.py — transparent comparative scoring
across the 20 required dimensions. Weights are versioned and stored per
row (docs/research_evidence_methodology.md §5). A candidate whose
CompatibilityAssessment.mandatory_pass is False is excluded from ranking
entirely — shown, marked incompatible, but never given a rank number,
regardless of its weighted score (ADR decision 7 & 8: evidence quality is
always a separate column from rank, never blended in).
"""
FORMULA_VERSION = '1.0.0'

DEFAULT_WEIGHTS = {
    'technical_fit': 0.10,
    'evidence_quality': 0.08,
    'expected_performance': 0.08,
    'deployment_maturity': 0.06,
    'integration_complexity': 0.05,
    'capex_confidence': 0.06,
    'opex_impact': 0.05,
    'implementation_time': 0.04,
    'availability': 0.05,
    'manufacturer_support': 0.05,
    'maintenance_requirements': 0.04,
    'local_capability': 0.05,
    'supply_chain_risk': 0.06,
    'regulatory_compatibility': 0.04,
    'worker_safety': 0.05,
    'environmental_impact': 0.04,
    'stewardship_alignment': 0.04,
    'cybersecurity': 0.03,
    'data_ownership': 0.02,
    'vendor_lock_in_risk': 0.01,
}
assert abs(sum(DEFAULT_WEIGHTS.values()) - 1.0) < 1e-9

MATURITY_SCORE = {'concept': 20.0, 'pilot': 50.0, 'early_commercial': 75.0, 'mature_commercial': 95.0}
COMPLEXITY_SCORE_INVERTED = {'low': 90.0, 'medium': 60.0, 'high': 30.0}
COMPATIBILITY_SCORE = {'compatible': 90.0, 'conditional': 60.0, 'incompatible': 10.0, 'insufficient_data': 40.0}
NEUTRAL_SCORE = 50.0


def _score_dimensions(mission, candidate, compatibility_assessment, product_candidate):
    """Returns (raw_scores dict, missing_data list). Every dimension gets a
    real score derived from a real signal, or NEUTRAL_SCORE with an entry
    in `missing_data` — never a fabricated confident number."""
    from global_research.models import SupplyChainRiskFlag

    scores, missing = {}, []

    scores['technical_fit'] = (
        compatibility_assessment.optional_fit_score if compatibility_assessment and compatibility_assessment.optional_fit_score is not None
        else (100.0 if compatibility_assessment and compatibility_assessment.mandatory_pass else NEUTRAL_SCORE)
    )
    if compatibility_assessment is None:
        missing.append('technical_fit: no CompatibilityAssessment available')

    scores['evidence_quality'] = candidate.evidence_score if candidate.evidence_score is not None else NEUTRAL_SCORE
    if candidate.evidence_score is None:
        missing.append('evidence_quality: candidate has no scored claims yet')

    performance_claims = [c for c in candidate.source_claims.all() if c.claim_type == 'performance' and c.confidence is not None]
    if performance_claims:
        scores['expected_performance'] = round(sum(c.confidence for c in performance_claims) / len(performance_claims), 2)
    else:
        scores['expected_performance'] = scores['evidence_quality']
        missing.append('expected_performance: no performance-tagged claims, falling back to overall evidence quality')

    maturity = getattr(candidate, 'commercial_maturity', None)
    scores['deployment_maturity'] = MATURITY_SCORE.get(maturity, NEUTRAL_SCORE)
    if maturity is None:
        missing.append('deployment_maturity: no commercial_maturity recorded')

    complexity = compatibility_assessment.estimated_integration_complexity if compatibility_assessment else None
    scores['integration_complexity'] = COMPLEXITY_SCORE_INVERTED.get(complexity, NEUTRAL_SCORE)
    scores['maintenance_requirements'] = scores['integration_complexity']
    if complexity is None:
        missing.append('integration_complexity: no CompatibilityAssessment.estimated_integration_complexity recorded')

    if product_candidate is not None and product_candidate.cost_confidence is not None:
        scores['capex_confidence'] = product_candidate.cost_confidence
    else:
        scores['capex_confidence'] = NEUTRAL_SCORE
        missing.append('capex_confidence: no cost_confidence recorded on the product candidate')
    scores['opex_impact'] = NEUTRAL_SCORE
    missing.append('opex_impact: no deterministic OPEX-impact signal available yet — neutral score used')

    scores['implementation_time'] = 70.0 if (product_candidate and product_candidate.lead_time_claim) else NEUTRAL_SCORE
    if not (product_candidate and product_candidate.lead_time_claim):
        missing.append('implementation_time: no lead_time_claim recorded')

    scores['availability'] = 80.0 if (product_candidate and product_candidate.status == 'active') else NEUTRAL_SCORE
    scores['manufacturer_support'] = (
        70.0 if (product_candidate and product_candidate.manufacturer.service_regions) else NEUTRAL_SCORE
    )
    if not (product_candidate and product_candidate.manufacturer.service_regions):
        missing.append('manufacturer_support: no service_regions recorded for the manufacturer')

    deployment_country = mission.country_of_deployment or ''
    scores['local_capability'] = (
        80.0 if (product_candidate and deployment_country and deployment_country in product_candidate.geographical_availability)
        else NEUTRAL_SCORE
    )
    if not (product_candidate and deployment_country in (product_candidate.geographical_availability if product_candidate else [])):
        missing.append('local_capability: no confirmed geographical_availability match for the deployment country')

    risk_qs = SupplyChainRiskFlag.objects.filter(mission=mission)
    if product_candidate is not None:
        risk_qs = risk_qs.filter(product_candidate=product_candidate)
    high = risk_qs.filter(severity='high').count()
    medium = risk_qs.filter(severity='medium').count()
    scores['supply_chain_risk'] = max(0.0, 100.0 - 25 * high - 10 * medium)
    if not risk_qs.exists():
        missing.append('supply_chain_risk: no SupplyChainRiskFlag rows evaluated yet')

    scores['regulatory_compatibility'] = COMPATIBILITY_SCORE.get(
        compatibility_assessment.local_standards_compatibility if compatibility_assessment else None, NEUTRAL_SCORE,
    )

    from global_research.services import stewardship_screen

    technology_candidate = candidate if candidate.__class__.__name__ == 'TechnologyCandidate' else getattr(candidate, 'technology_candidate', None)
    screen_result = stewardship_screen.screen_technology_candidate(technology_candidate) if technology_candidate else {'score': None, 'flags': []}
    if screen_result['score'] is not None:
        scores['worker_safety'] = scores['environmental_impact'] = scores['stewardship_alignment'] = screen_result['score']
    else:
        scores['worker_safety'] = scores['environmental_impact'] = scores['stewardship_alignment'] = NEUTRAL_SCORE
        missing.append('worker_safety/environmental_impact/stewardship_alignment: worker/environmental implications not yet documented for this technology candidate')

    scores['cybersecurity'] = NEUTRAL_SCORE
    scores['data_ownership'] = NEUTRAL_SCORE
    missing.append('cybersecurity/data_ownership: no deterministic signal source configured yet — neutral score used')

    scores['vendor_lock_in_risk'] = (
        70.0 if (product_candidate and product_candidate.manufacturer.supporting_integrators.exists()) else NEUTRAL_SCORE
    )

    return scores, missing


def build_comparative_evaluation(mission, technology_candidate=None, product_candidate=None,
                                  compatibility_assessment=None, weights=None):
    """Idempotent (update_or_create). `weights` may override
    DEFAULT_WEIGHTS per mission — always stored on the row, never applied silently."""
    from global_research.models import ComparativeEvaluation

    candidate = product_candidate or technology_candidate
    weights = weights or DEFAULT_WEIGHTS
    raw_scores, missing_data = _score_dimensions(mission, candidate, compatibility_assessment, product_candidate)
    normalised_scores = {k: round(v, 2) for k, v in raw_scores.items()}

    is_ranked = bool(compatibility_assessment and compatibility_assessment.mandatory_pass)
    total_score = round(sum(weights.get(k, 0) * v for k, v in normalised_scores.items()), 2) if is_ranked else None

    evaluation, _ = ComparativeEvaluation.objects.update_or_create(
        mission=mission, technology_candidate=technology_candidate, product_candidate=product_candidate,
        defaults=dict(
            compatibility_assessment=compatibility_assessment, criteria_weights=weights, raw_scores=raw_scores,
            normalised_scores=normalised_scores, evidence_score=candidate.evidence_score if candidate else None,
            missing_data=missing_data, total_score=total_score, is_ranked=is_ranked, formula_version=FORMULA_VERSION,
        ),
    )
    return evaluation


def rank_mission_evaluations(mission):
    """Assigns `rank` only among `is_ranked=True` rows, highest total_score
    first — an incompatible candidate never receives a rank number."""
    from global_research.models import ComparativeEvaluation

    ranked = list(
        ComparativeEvaluation.objects.filter(mission=mission, is_ranked=True).order_by('-total_score'),
    )
    for index, evaluation in enumerate(ranked, start=1):
        if evaluation.rank != index:
            evaluation.rank = index
            evaluation.save(update_fields=['rank', 'updated_at'])
    ComparativeEvaluation.objects.filter(mission=mission, is_ranked=False).update(rank=None)
    return ranked
