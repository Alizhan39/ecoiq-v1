"""
digital_twin/services/human_approval_gate.py — reuses
agent_runtime_model_router's gate directly, exactly like
waste_to_value_capital_allocation_engine/services/human_approval_gate.py
does, rather than forking it.
"""
from agent_runtime_model_router.services.human_approval_gate import (
    ACTIONS_REQUIRING_APPROVAL as _BASE_ACTIONS,
    HumanApprovalRequiredError,
    require_human_approval as _base_require_human_approval,
)

ADDITIONAL_ACTIONS_REQUIRING_APPROVAL = frozenset({
    'digital_twin_scenario_promotion',
    'digital_twin_baseline_approval',
    'digital_twin_loss_promotion',
})

ACTIONS_REQUIRING_APPROVAL = _BASE_ACTIONS | ADDITIONAL_ACTIONS_REQUIRING_APPROVAL


def require_human_approval(action_type, approvable):
    """`approvable` is typically a digital_twin.HumanDecision or
    digital_twin.LossDetection — anything with a `.human_approved`/`.pk`."""
    if action_type in ADDITIONAL_ACTIONS_REQUIRING_APPROVAL:
        if getattr(approvable, 'human_approved', None) is not True:
            raise HumanApprovalRequiredError(
                f"Action '{action_type}' requires human approval before it can proceed "
                f'(id={getattr(approvable, "pk", None)}, human_approved={getattr(approvable, "human_approved", None)!r}).'
            )
        return True
    return _base_require_human_approval(action_type, approvable)
