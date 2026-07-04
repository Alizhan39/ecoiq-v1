"""
waste_to_value_capital_allocation_engine/services/human_approval_gate.py —
reuses agent_runtime_model_router's gate directly rather than forking it.

The base gate is a pure function that only reads `.human_approved`/`.pk` off
whatever object it's given, so it works unchanged for this app's
`CapitalRouteMatch`/`CapitalAllocationDecision` objects, not just `AgentRun`.
This module only adds 2 new action types not covered by the base 8.
"""
from agent_runtime_model_router.services.human_approval_gate import (
    ACTIONS_REQUIRING_APPROVAL as _BASE_ACTIONS,
    HumanApprovalRequiredError,
    require_human_approval as _base_require_human_approval,
)

ADDITIONAL_ACTIONS_REQUIRING_APPROVAL = frozenset({
    'capital_route_outreach',
    'islamic_finance_claim_publication',
})

ACTIONS_REQUIRING_APPROVAL = _BASE_ACTIONS | ADDITIONAL_ACTIONS_REQUIRING_APPROVAL


def require_human_approval(action_type, approvable):
    """
    Reuses the base gate for the 8 shared actions; handles this app's 2
    additional action types the same way (raise unless human_approved is
    exactly True). `approvable` is typically a CapitalRouteMatch or
    CapitalAllocationDecision, not an AgentRun.
    """
    if action_type in ADDITIONAL_ACTIONS_REQUIRING_APPROVAL:
        if getattr(approvable, 'human_approved', None) is not True:
            raise HumanApprovalRequiredError(
                f"Action '{action_type}' requires human approval before it can proceed "
                f'(id={getattr(approvable, "pk", None)}, human_approved={getattr(approvable, "human_approved", None)!r}).'
            )
        return True
    return _base_require_human_approval(action_type, approvable)
