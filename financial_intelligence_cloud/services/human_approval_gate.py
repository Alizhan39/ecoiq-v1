"""
financial_intelligence_cloud/services/human_approval_gate.py — reuses
agent_runtime_model_router's gate directly rather than forking it, exactly
matching waste_to_value_capital_allocation_engine's own wrapper shape.

Adds 1 action not covered by the base 8: `advisory_outreach` — contacting a
client based on this platform's recommendation requires human approval. A
recommended client call is never a guaranteed advisory-revenue outcome.
"""
from agent_runtime_model_router.services.human_approval_gate import (
    ACTIONS_REQUIRING_APPROVAL as _BASE_ACTIONS,
    HumanApprovalRequiredError,
    require_human_approval as _base_require_human_approval,
)

ADDITIONAL_ACTIONS_REQUIRING_APPROVAL = frozenset({
    'advisory_outreach',
})

ACTIONS_REQUIRING_APPROVAL = _BASE_ACTIONS | ADDITIONAL_ACTIONS_REQUIRING_APPROVAL


def require_human_approval(action_type, approvable):
    """
    Reuses the base gate for the 8 shared actions; handles this app's 1
    additional action type the same way (raise unless human_approved is
    exactly True). `approvable` is typically an AdvisoryOpportunity.
    """
    if action_type in ADDITIONAL_ACTIONS_REQUIRING_APPROVAL:
        if getattr(approvable, 'human_approved', None) is not True:
            raise HumanApprovalRequiredError(
                f"Action '{action_type}' requires human approval before it can proceed "
                f'(id={getattr(approvable, "pk", None)}, human_approved={getattr(approvable, "human_approved", None)!r}).'
            )
        return True
    return _base_require_human_approval(action_type, approvable)
