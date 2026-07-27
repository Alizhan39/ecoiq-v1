"""
digital_twin/services/promotion.py — promotes an approved
ModernisationScenario into the EXISTING
waste_to_value_capital_allocation_engine.CapitalAllocationDecision
workflow.

Follows `capital_guardian.services.capital_decision_bridge.
create_decision_from_better_way()` precedent exactly: scores come from the
real `capital_allocation_scoring.score_intervention_option()` function (never
re-derived here), `verified_impact_score` is deliberately left at
governance.py's own default (0) since nothing has been independently
verified yet, and the whole call goes through the existing
`create_governed_investment_case()` — this module never writes to
CapitalAllocationDecision directly, and never re-approves an
already-decided case.
"""
from waste_to_value_capital_allocation_engine.services.capital_allocation_scoring import score_intervention_option
from waste_to_value_capital_allocation_engine.services.governance import create_governed_investment_case

from digital_twin.services.human_approval_gate import require_human_approval

APPROVAL_STATUS_MAP = {
    'approved': 'approved',
    'approved_with_conditions': 'approved_with_conditions',
}


class ScenarioNotApprovedError(Exception):
    """Raised when promote_scenario is called for a HumanDecision that is
    not an approving decision (approved / approved_with_conditions)."""


def promote_scenario(human_decision):
    """Idempotent: if this HumanDecision has already been promoted, returns
    the existing CapitalAllocationDecision unchanged rather than creating a
    second one or silently resetting its status."""
    if human_decision.capital_allocation_decision_id:
        return human_decision.capital_allocation_decision

    require_human_approval('digital_twin_scenario_promotion', human_decision)

    if human_decision.decision not in APPROVAL_STATUS_MAP:
        raise ScenarioNotApprovedError(
            f"HumanDecision {human_decision.pk} has decision='{human_decision.decision}' — "
            'only approved or approved_with_conditions decisions can be promoted.'
        )

    scenario = human_decision.scenario
    intervention = scenario.intervention
    real_loss = intervention.operational_loss

    # Duplicate-prevention: the same (intervention, council_case) idempotency
    # key create_governed_investment_case() already enforces means a second
    # promotion attempt for the same scenario/council pairing safely returns
    # the same row rather than creating a duplicate.
    ceiling = real_loss.financial_loss_amount or real_loss.projected_future_loss or 0
    sub_scores = score_intervention_option(intervention, capital_at_risk_ceiling=ceiling, inventory_value_ceiling=ceiling)
    scores = {
        'financial_return_score': sub_scores['financial_return'],
        'loss_avoidance_score': sub_scores['loss_avoided'],
        'capital_efficiency_score': sub_scores['capital_efficiency'],
        'risk_score': sub_scores['downside_risk'],
        'maqasid_mizan_score': sub_scores['maqasid_mizan_score'],
        # verified_impact_score deliberately absent — nothing has been
        # independently verified yet (estimated != verified); it is only
        # honestly populated once a MeasuredOutcome exists (services/outcomes.py).
    }

    decision_text = (
        f'Human decision "{human_decision.get_decision_display()}" on scenario "{intervention.title}" '
        f'for twin "{scenario.twin.name}" ({scenario.twin.asset.name}). '
        + (f'Conditions: {"; ".join(human_decision.conditions)}. ' if human_decision.conditions else '')
        + f'Reviewed by {human_decision.reviewer_role or "a human reviewer"}.'
    )

    decision = create_governed_investment_case(
        intervention, council_case=human_decision.council_run, decision_text=decision_text, scores=scores,
        conditions=human_decision.conditions, confidence=scenario.confidence,
        human_approval_required=True, approval_status=APPROVAL_STATUS_MAP[human_decision.decision],
    )
    human_decision.capital_allocation_decision = decision
    human_decision.save(update_fields=['capital_allocation_decision', 'updated_at'])
    return decision
