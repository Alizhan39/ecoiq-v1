"""
khalifa_stewardship_tour_operating_system/services/capital_allocation_link.py
— "Which tour/intervention deserves the next £1?" Thin adapter: calls the
REAL waste_to_value_capital_allocation_engine scoring/ranking services
directly (a third consumer, after WTV's own use and Financial Intelligence
Cloud's Atlas Value Partners) — no forked ranking logic, no new scoring
mechanism. Maps StewardshipIntervention fields into the same 13-dimension
shape score_intervention_option() already expects.
"""
from waste_to_value_capital_allocation_engine.services.capital_allocation_scoring import score_intervention_option
from waste_to_value_capital_allocation_engine.services.intervention_finance import _calculate_payback
from waste_to_value_capital_allocation_engine.services.ranking import rank_capital_allocation_options

# StewardshipIntervention.intervention_type -> the WTV scoring module's
# intervention_type vocabulary, only where a genuine conceptual match exists
# (e.g. a clean-heating/insulation package really is a physical equipment
# upgrade that extends the home's heating system life). Unmapped types fall
# through to score_intervention_option()'s own DEFAULT_TYPE_SCORES.
INTERVENTION_TYPE_TO_SCORING_TYPE = {
    'clean_heating_upgrade': 'equipment_upgrade',
    'insulation_support': 'equipment_upgrade',
    'boiler_heat_pump_assessment': 'equipment_upgrade',
    'habitat_restoration': 'equipment_upgrade',
    'safe_redistribution': 'transfer_redistribution',
    'community_kitchen_support': 'transfer_redistribution',
}

# implementation_complexity -> risk_level / technical_readiness (higher
# complexity genuinely means higher execution risk and lower readiness).
COMPLEXITY_TO_RISK_LEVEL = {'low': 'low', 'medium': 'medium', 'high': 'high'}
COMPLEXITY_TO_TECHNICAL_READINESS = {'low': 'ready', 'medium': 'needs_review', 'high': 'draft'}


def _intervention_to_scoring_input(intervention, annual_savings):
    payback_months = _calculate_payback(intervention.capex_estimate, annual_savings) if annual_savings else None
    return {
        'title': intervention.title,
        'description': intervention.description,
        'capex_estimate': intervention.capex_estimate,
        'estimated_loss_avoided': annual_savings,
        'estimated_value_recovered': 0,
        'estimated_annual_savings': annual_savings,
        'estimated_payback_months': payback_months,
        'risk_level': COMPLEXITY_TO_RISK_LEVEL.get(intervention.implementation_complexity, 'medium'),
        'technical_readiness': COMPLEXITY_TO_TECHNICAL_READINESS.get(intervention.implementation_complexity, 'needs_review'),
        'finance_readiness': 'needs_review' if intervention.capex_estimate > 1000 else 'ready',
        'mrv_readiness': 'draft',
        'intervention_type': INTERVENTION_TYPE_TO_SCORING_TYPE.get(intervention.intervention_type, intervention.intervention_type),
    }


def rank_stewardship_interventions(problem, capital_at_risk_ceiling, inventory_value_ceiling):
    """
    Scores and ranks every StewardshipIntervention under `problem` using the
    real score_intervention_option()/rank_capital_allocation_options()
    services. Returns the ranked list, each dict annotated with
    composite_score/rank and the original StewardshipIntervention under
    'intervention'.
    """
    candidates = []
    for intervention in problem.interventions.all():
        annual_savings = intervention.estimated_benefit or 0
        scoring_input = _intervention_to_scoring_input(intervention, annual_savings)
        scores = score_intervention_option(scoring_input, capital_at_risk_ceiling, inventory_value_ceiling)
        candidates.append({'intervention': intervention, 'title': intervention.title, **scores})

    return rank_capital_allocation_options(candidates)
