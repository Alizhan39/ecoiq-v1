"""
waste_to_value_capital_allocation_engine/services/governance.py — lifecycle
step 10: produce the governed investment case.

Does not make financial decisions automatically — `create_governed_investment_case()`
persists whatever decision/scores/conditions a Council process (real or
simulated, see services/demo_pipeline.py) already reached; it never
computes or asserts an approval on its own.
"""
from waste_to_value_capital_allocation_engine.models import CapitalAllocationDecision


def create_governed_investment_case(intervention, council_case=None, decision_text='', scores=None,
                                     conditions=None, confidence=None, human_approval_required=True,
                                     approval_status='pending'):
    """
    Idempotent via get_or_create on (intervention, council_case). `scores`
    is a dict with any of: financial_return_score, loss_avoidance_score,
    capital_efficiency_score, risk_score, verified_impact_score,
    maqasid_mizan_score (all 0-100).
    """
    scores = scores or {}
    decision, _ = CapitalAllocationDecision.objects.get_or_create(
        intervention=intervention, council_case=council_case, defaults={},
    )
    decision.organisation = intervention.operational_loss.organisation
    decision.project = intervention.operational_loss.project
    decision.decision = decision_text
    decision.financial_return_score = scores.get('financial_return_score', 0)
    decision.loss_avoidance_score = scores.get('loss_avoidance_score', 0)
    decision.capital_efficiency_score = scores.get('capital_efficiency_score', 0)
    decision.risk_score = scores.get('risk_score', 0)
    decision.verified_impact_score = scores.get('verified_impact_score', 0)
    decision.maqasid_mizan_score = scores.get('maqasid_mizan_score', 0)
    decision.confidence = confidence
    decision.conditions = conditions or []
    decision.human_approval_required = human_approval_required
    decision.approval_status = approval_status
    decision.save()
    return decision
