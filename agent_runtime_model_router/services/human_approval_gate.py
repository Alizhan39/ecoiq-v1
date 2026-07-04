"""
agent_runtime_model_router/services/human_approval_gate.py — human approval
enforced in code, not only shown as UI text.

`require_human_approval` is called by the service layer (never just a
template) before any of the 8 listed external/high-impact actions is
honoured. It raises rather than silently no-opping, so a caller that
forgets to check the return value still can't proceed.
"""
ACTIONS_REQUIRING_APPROVAL = frozenset({
    'supplier_outreach',
    'funder_outreach',
    'investor_memo_delivery',
    'public_summary_publishing',
    'mrv_verified_publication',
    'major_industrial_recommendation',
    'islamic_finance_claim',
    'public_impact_claim',
})


class HumanApprovalRequiredError(Exception):
    """Raised when an action in ACTIONS_REQUIRING_APPROVAL is attempted without human_approved=True."""


def require_human_approval(action_type, agent_run):
    """
    Returns True if the action is permitted. Raises HumanApprovalRequiredError
    if `action_type` requires approval and `agent_run.human_approved` is not
    exactly True (covers both False and None/not-yet-reviewed).
    """
    if action_type in ACTIONS_REQUIRING_APPROVAL and agent_run.human_approved is not True:
        raise HumanApprovalRequiredError(
            f"Action '{action_type}' requires human approval before it can proceed "
            f'(agent_run id={agent_run.pk}, human_approved={agent_run.human_approved!r}).'
        )
    return True
