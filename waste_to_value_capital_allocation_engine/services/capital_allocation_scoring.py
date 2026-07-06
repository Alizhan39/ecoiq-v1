"""
waste_to_value_capital_allocation_engine/services/capital_allocation_scoring.py
— derives the 13 sub-scores `ranking.py::rank_capital_allocation_options()`
expects from a real `InterventionOption`'s own fields. Never invents a
second finance number — every score traces back to capex_estimate,
estimated_loss_avoided, estimated_value_recovered, estimated_annual_savings,
estimated_payback_months, risk_level, technical/finance/mrv_readiness, and
intervention_type.

Load-bearing design point: `financial_return`, `loss_avoided` and
`recoverable_value` are scaled against the CASE's own materiality ceilings
(capital_at_risk, inventory_value) rather than as ratios to each option's own
capex. A pure ratio approach structurally rewards tiny-capex tactical
actions and would wrongly rank a small resale option above a recurring-risk
equipment upgrade whose value_recovered is 0 by design (it prevents future
loss via annual_savings, it doesn't salvage this cycle's inventory).
`capital_efficiency` stays a genuine capex ratio, capped at a 10x-capex-back
reference ("excellent"), so it doesn't collapse into the same signal as
`financial_return`.

Reference worked example (Meat Cold-Chain golden case, 7 real options,
capital_at_risk_ceiling=12000, inventory_value_ceiling=80000): Cold-chain
equipment intervention scores highest on the weighted composite in
ranking.py, ahead of Transfer to another branch (the strongest tactical
option) — see waste_to_value_capital_allocation_engine/tests.py for the
exact regression assertion.
"""
READINESS_SCORE = {'not_ready': 10, 'draft': 40, 'needs_review': 60, 'ready': 90}
RISK_SCORE_INVERTED = {'low': 90, 'medium': 60, 'high': 25}
TECHNICAL_READINESS_AS_EVIDENCE_QUALITY = {'not_ready': 30, 'draft': 60, 'needs_review': 60, 'ready': 90}

# intervention_type -> (asset_life_extension, harm_reduced, maqasid_mizan_score).
# human_need_served is scored separately (see _score_human_need_served) since
# it depends on whether a transfer_redistribution option is donation-flavoured
# specifically, not on intervention_type alone.
TYPE_QUALITATIVE_SCORES = {
    'equipment_upgrade':        {'asset_life_extension': 80, 'harm_reduced': 50, 'maqasid_mizan_score': 65},
    'transfer_redistribution':  {'asset_life_extension': 10, 'harm_reduced': 55, 'maqasid_mizan_score': 75},
    'resale':                   {'asset_life_extension': 10, 'harm_reduced': 30, 'maqasid_mizan_score': 45},
    'prevention':               {'asset_life_extension': 10, 'harm_reduced': 30, 'maqasid_mizan_score': 45},
    'processing_recovery':      {'asset_life_extension': 10, 'harm_reduced': 30, 'maqasid_mizan_score': 45},
    'disposal':                 {'asset_life_extension': 10, 'harm_reduced': 60, 'maqasid_mizan_score': 50},
}
DEFAULT_TYPE_SCORES = {'asset_life_extension': 10, 'harm_reduced': 30, 'maqasid_mizan_score': 45}

DONATION_KEYWORDS = ('donat', 'redistribut', 'food bank', 'charity')


def _score_human_need_served(intervention_type, title, description):
    text = f'{title} {description}'.lower()
    if intervention_type == 'transfer_redistribution' and any(k in text for k in DONATION_KEYWORDS):
        return 70
    return 20


def _score_financial_return(annual_savings, loss_avoided, capital_at_risk_ceiling):
    if not capital_at_risk_ceiling:
        return 0
    annualised_value = annual_savings or loss_avoided
    return min(100, round(annualised_value / capital_at_risk_ceiling * 100))


def _score_capital_efficiency(loss_avoided, value_recovered, annual_savings, capex):
    if not capex:
        return 0
    value_generated = loss_avoided + value_recovered + annual_savings
    return min(100, round(value_generated / capex / 10.0 * 100))


def _score_loss_avoided(loss_avoided, capital_at_risk_ceiling):
    if not capital_at_risk_ceiling:
        return 0
    return min(100, round(loss_avoided / capital_at_risk_ceiling * 100))


def _score_recoverable_value(value_recovered, inventory_value_ceiling):
    if not inventory_value_ceiling:
        return 0
    return min(100, round(value_recovered / inventory_value_ceiling * 100 * 5))


def _score_payback(payback_months):
    if payback_months is None:
        # No multi-month payback usually means a same-window tactical action
        # realises its value within this cycle — not "bad" (which would argue
        # for 0) and not "provenly instant" (which would overstate certainty
        # and argue for 100). 65 sits above the moderate midpoint without
        # claiming a stronger evidentiary basis than exists.
        return 65
    return max(0, round(100 - payback_months * 3))


def score_intervention_option(option, capital_at_risk_ceiling, inventory_value_ceiling):
    """
    `option` is a dict (or any object supporting the same attribute names)
    with: title, description, capex_estimate, estimated_loss_avoided,
    estimated_value_recovered, estimated_annual_savings,
    estimated_payback_months, risk_level, technical_readiness,
    finance_readiness, mrv_readiness, intervention_type. Returns the 13
    sub-scores (0-100 each) `rank_capital_allocation_options()` expects,
    already normalized/inverted so higher is always better.
    """
    def get(field, default=None):
        if isinstance(option, dict):
            return option.get(field, default)
        return getattr(option, field, default)

    title = get('title', '') or ''
    description = get('description', '') or ''
    capex = get('capex_estimate', 0) or 0
    loss_avoided = get('estimated_loss_avoided', 0) or 0
    value_recovered = get('estimated_value_recovered', 0) or 0
    annual_savings = get('estimated_annual_savings', 0) or 0
    payback_months = get('estimated_payback_months', None)
    risk_level = get('risk_level', 'medium')
    technical_readiness = get('technical_readiness', 'not_ready')
    finance_readiness = get('finance_readiness', 'not_ready')
    mrv_readiness = get('mrv_readiness', 'not_ready')
    intervention_type = get('intervention_type', '')

    type_scores = TYPE_QUALITATIVE_SCORES.get(intervention_type, DEFAULT_TYPE_SCORES)

    return {
        'financial_return': _score_financial_return(annual_savings, loss_avoided, capital_at_risk_ceiling),
        'capital_efficiency': _score_capital_efficiency(loss_avoided, value_recovered, annual_savings, capex),
        'loss_avoided': _score_loss_avoided(loss_avoided, capital_at_risk_ceiling),
        'recoverable_value': _score_recoverable_value(value_recovered, inventory_value_ceiling),
        'payback': _score_payback(payback_months),
        'downside_risk': RISK_SCORE_INVERTED.get(risk_level, 60),
        'evidence_quality': TECHNICAL_READINESS_AS_EVIDENCE_QUALITY.get(technical_readiness, 50),
        'mrv_readiness': READINESS_SCORE.get(mrv_readiness, 10),
        'funding_readiness': READINESS_SCORE.get(finance_readiness, 10),
        'asset_life_extension': type_scores['asset_life_extension'],
        'human_need_served': _score_human_need_served(intervention_type, title, description),
        'harm_reduced': type_scores['harm_reduced'],
        'maqasid_mizan_score': type_scores['maqasid_mizan_score'],
    }
