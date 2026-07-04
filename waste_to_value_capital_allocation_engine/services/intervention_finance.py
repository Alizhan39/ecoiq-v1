"""
waste_to_value_capital_allocation_engine/services/intervention_finance.py —
lifecycle steps 4-7: compare interventions, calculate CAPEX/OPEX, payback,
and the Finance Readiness Score.

Required distinctions, enforced by callers of this module:
estimated_savings != verified_savings; finance_ready_recommended !=
finance_ready_approved. Every number here is a recommendation for human
review, never an executed financial decision.
"""
from waste_to_value_capital_allocation_engine.models import InterventionOption

EVIDENCE_QUALITY_SCORE = {'strong': 90, 'medium': 60, 'weak': 30, 'missing': 10}

FINANCE_READINESS_WEIGHTS = {
    'capex_efficiency': 0.25,
    'working_capital':  0.10,
    'payback':          0.35,
    'evidence_quality':  0.20,
    'mrv_readiness':     0.10,
}


def _calculate_capex(capex):
    return round(capex, 2)


def _calculate_opex_change(opex_change):
    return round(opex_change, 2)


def _calculate_loss_avoided(loss_avoided):
    return round(loss_avoided, 2)


def _calculate_value_recovered(value_recovered):
    return round(value_recovered, 2)


def _calculate_working_capital_released(working_capital_released):
    return round(working_capital_released, 2)


def _calculate_payback(capex, annual_savings):
    """
    payback_months = capex / (annual_savings / 12).
    Reference worked example: capex=120000, annual_savings=180000
    -> payback_months = 8.0 (exact — matches the spec's own cold-chain example).
    """
    if not annual_savings:
        return None
    return round(capex / (annual_savings / 12), 1)


def calculate_intervention_finance(capex, opex_change, loss_avoided, value_recovered,
                                    annual_savings, working_capital_released=0):
    """Composes the section-6 helpers into one consolidated finance dict for an intervention."""
    return {
        'capex':                    _calculate_capex(capex),
        'opex_change':               _calculate_opex_change(opex_change),
        'loss_avoided':              _calculate_loss_avoided(loss_avoided),
        'value_recovered':           _calculate_value_recovered(value_recovered),
        'working_capital_released':   _calculate_working_capital_released(working_capital_released),
        'annual_savings':            round(annual_savings, 2),
        'payback_months':            _calculate_payback(capex, annual_savings),
    }


def model_interventions(operational_loss, candidates):
    """
    candidates: list of dicts, each with at least {title, intervention_type},
    plus whatever calculate_intervention_finance() needs. Idempotent via
    get_or_create keyed on (operational_loss, title).
    """
    options = []
    for candidate in candidates:
        finance = calculate_intervention_finance(
            capex=candidate.get('capex_estimate', 0),
            opex_change=candidate.get('opex_change', 0),
            loss_avoided=candidate.get('estimated_loss_avoided', 0),
            value_recovered=candidate.get('estimated_value_recovered', 0),
            annual_savings=candidate.get('estimated_annual_savings', 0),
            working_capital_released=candidate.get('working_capital_released', 0),
        )
        option, _ = InterventionOption.objects.get_or_create(
            operational_loss=operational_loss, title=candidate['title'],
            defaults={'intervention_type': candidate['intervention_type']},
        )
        option.intervention_type = candidate['intervention_type']
        option.description = candidate.get('description', '')
        option.capex_estimate = finance['capex']
        option.opex_change = finance['opex_change']
        option.estimated_loss_avoided = finance['loss_avoided']
        option.estimated_value_recovered = finance['value_recovered']
        option.estimated_annual_savings = finance['annual_savings']
        option.estimated_payback_months = finance['payback_months']
        option.implementation_time = candidate.get('implementation_time', '')
        option.technical_readiness = candidate.get('technical_readiness', 'not_ready')
        option.finance_readiness = candidate.get('finance_readiness', 'not_ready')
        option.mrv_readiness = candidate.get('mrv_readiness', 'not_ready')
        option.risk_level = candidate.get('risk_level', 'medium')
        option.status = candidate.get('status', 'modelled')
        option.save()
        options.append(option)
    return options


def calculate_finance_readiness_score(capex, loss_avoided_annual, working_capital_released,
                                       payback_months, evidence_quality, mrv_readiness):
    """
    Weighted 0-100 score. Sub-scores: CAPEX efficiency (loss-avoided:CAPEX
    ratio), working-capital released (as a share of CAPEX), payback speed,
    evidence quality, MRV readiness.

    Reference worked example (verified against this implementation):
    capex=120000, loss_avoided_annual=180000, working_capital_released=70000,
    payback_months=8.0, evidence_quality='strong', mrv_readiness='medium'
    -> finance_readiness_score = 84.
    """
    capex_efficiency_score = min(100, (loss_avoided_annual / capex) * 100 * 0.6) if capex else 0
    working_capital_score = min(100, (working_capital_released / capex) * 100) if capex else 0
    payback_score = max(0, 100 - (payback_months or 0) * 1.19)
    # mrv_readiness here uses the same strong/medium/weak vocabulary as
    # evidence_quality (matching the spec's own worked example), not the
    # not_ready/draft/needs_review/ready choices used on the model fields —
    # callers passing a model field value should map it accordingly.
    evidence_quality_score = EVIDENCE_QUALITY_SCORE.get(evidence_quality, 50)
    mrv_readiness_score = EVIDENCE_QUALITY_SCORE.get(mrv_readiness, 50)

    raw = (
        FINANCE_READINESS_WEIGHTS['capex_efficiency'] * capex_efficiency_score
        + FINANCE_READINESS_WEIGHTS['working_capital'] * working_capital_score
        + FINANCE_READINESS_WEIGHTS['payback'] * payback_score
        + FINANCE_READINESS_WEIGHTS['evidence_quality'] * evidence_quality_score
        + FINANCE_READINESS_WEIGHTS['mrv_readiness'] * mrv_readiness_score
    )
    return max(0, min(100, round(raw)))
