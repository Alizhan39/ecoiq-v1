"""
waste_to_value_capital_allocation_engine/services/mrv_outcomes.py —
lifecycle steps 13-15: MRV verification and the capital reallocation
feedback loop.

Predicted result must never silently become verified result:
`verified_status` is only ever 'verified' when `mrv_status == 'verified'`;
otherwise it stays 'estimated'. `generate_capital_reallocation_signal()` is
purely advisory — it never mutates other InterventionOption rows, matching
the "prepares governed recommendations for human review" principle used
throughout this session.
"""
from waste_to_value_capital_allocation_engine.models import VerifiedCapitalOutcome
from waste_to_value_capital_allocation_engine.services.intervention_finance import _calculate_payback


def record_verified_outcome(decision, intervention, loss_avoided_actual, capex_actual, opex_actual=0,
                             savings_actual=0, mrv_status='verified', evidence_quality='strong',
                             public_reporting_ready=False):
    """
    value_recovered_actual = loss_avoided_actual - capex_actual.
    Reference worked example: loss_avoided_actual=8400, capex_actual=1500
    -> value_recovered_actual = 6900.0 (exact).
    """
    value_recovered_actual = round(loss_avoided_actual - capex_actual, 2)
    payback_actual = _calculate_payback(capex_actual, savings_actual) if savings_actual else None
    verified_status = 'verified' if mrv_status == 'verified' else 'estimated'

    outcome, _ = VerifiedCapitalOutcome.objects.get_or_create(
        decision=decision, defaults={'intervention': intervention},
    )
    outcome.intervention = intervention
    outcome.capex_actual = capex_actual
    outcome.opex_actual = opex_actual
    outcome.loss_avoided_actual = loss_avoided_actual
    outcome.value_recovered_actual = value_recovered_actual
    outcome.savings_actual = savings_actual
    outcome.payback_actual = payback_actual
    outcome.mrv_status = mrv_status
    outcome.evidence_quality = evidence_quality
    outcome.verified_status = verified_status
    # Public reporting can never be marked ready off an estimated outcome.
    outcome.public_reporting_ready = bool(public_reporting_ready) and verified_status == 'verified'
    outcome.save()
    return outcome


def generate_capital_reallocation_signal(intervention, outcome):
    """
    Compares the original estimate to the verified actual and returns a
    structured advisory signal — never auto-adjusts other rows.
    """
    estimated = intervention.estimated_payback_months
    actual = outcome.payback_actual

    if not estimated or not actual:
        return {
            'variance_pct': None, 'direction': 'unknown',
            'recommendation_text': 'Insufficient data to generate a reallocation signal.',
            'confidence_note': 'Missing estimated or actual payback figures.',
        }

    variance_pct = round(((actual - estimated) / estimated) * 100, 1)
    if actual > estimated:
        direction = 'worse_than_estimated'
        recommendation_text = (
            f'Future {intervention.get_intervention_type_display()} projects should lower expected '
            f'savings assumptions and widen the sensitivity range.'
        )
    elif actual < estimated:
        direction = 'better_than_estimated'
        recommendation_text = (
            f'Future {intervention.get_intervention_type_display()} projects could use a slightly '
            f'more optimistic base case, given verified outperformance.'
        )
    else:
        direction = 'as_estimated'
        recommendation_text = 'Original estimate held — no adjustment needed for similar future projects.'

    return {
        'variance_pct': variance_pct,
        'direction': direction,
        'recommendation_text': recommendation_text,
        'confidence_note': 'Higher confidence for future estimates due to real verified evidence.',
    }
