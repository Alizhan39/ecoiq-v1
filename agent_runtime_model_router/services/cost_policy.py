"""
agent_runtime_model_router/services/cost_policy.py — explicit cost controls.

All costs are estimates (token-count-based, provider list pricing) — never
conflated with actual provider-billed cost, which is tracked separately on
`AgentRun.actual_usage` only when a provider returns it.
"""
MAX_ESTIMATED_COST_PER_RUN_USD = 2.00
MAX_ESTIMATED_COST_PER_COUNCIL_CASE_USD = 15.00
HIGH_REASONING_APPROVAL_THRESHOLD_USD = 1.00
LOW_COST_ROUTE_TASK_TYPES = {
    'sector_research', 'site_context_research', 'overnight_portfolio_check',
}


def check_cost_policy(estimated_cost_usd, council_case, cost_class='standard'):
    """
    Returns {allowed, reason, requires_human_approval, budget_exceeded}.
    Never blocks solely because a high-reasoning route is expensive — it
    instead requires human approval before the run proceeds.
    """
    if estimated_cost_usd is None:
        return {
            'allowed': True, 'reason': 'No cost estimate available.',
            'requires_human_approval': False, 'budget_exceeded': False,
        }

    if estimated_cost_usd > MAX_ESTIMATED_COST_PER_RUN_USD:
        return {
            'allowed': False,
            'reason': f'Estimated cost ${estimated_cost_usd:.2f} exceeds the per-run limit (${MAX_ESTIMATED_COST_PER_RUN_USD:.2f}).',
            'requires_human_approval': True, 'budget_exceeded': True,
        }

    case_total = estimated_cost_usd
    if council_case is not None:
        from agent_runtime_model_router.models import AgentRun
        prior_total = AgentRun.objects.filter(council_case=council_case).exclude(
            estimated_cost_usd__isnull=True,
        ).values_list('estimated_cost_usd', flat=True)
        case_total += sum(prior_total)

    if case_total > MAX_ESTIMATED_COST_PER_COUNCIL_CASE_USD:
        return {
            'allowed': False,
            'reason': f'Cumulative estimated cost for this case (${case_total:.2f}) exceeds the per-case limit (${MAX_ESTIMATED_COST_PER_COUNCIL_CASE_USD:.2f}).',
            'requires_human_approval': True, 'budget_exceeded': True,
        }

    if cost_class == 'high_reasoning' and estimated_cost_usd > HIGH_REASONING_APPROVAL_THRESHOLD_USD:
        return {
            'allowed': True,
            'reason': f'High-reasoning route above ${HIGH_REASONING_APPROVAL_THRESHOLD_USD:.2f} requires human approval before proceeding.',
            'requires_human_approval': True, 'budget_exceeded': False,
        }

    return {
        'allowed': True, 'reason': 'Within cost policy.',
        'requires_human_approval': False, 'budget_exceeded': False,
    }
