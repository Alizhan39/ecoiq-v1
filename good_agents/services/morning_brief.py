"""
good_agents/services/morning_brief.py — MorningImpactBrief (PR3 Phase 16)
+ Top 3 Actions / AttentionPriority (Phase 17-18).

Everything in the returned dict is read straight from stored rows on
`run` and its related opportunities — no number is computed ad hoc or
invented for display. This is a plain function returning a dict, not a
persisted model: the brief is a view over data that already has its own
persistence (GoodDiscoveryRun, GoodOpportunity, ResourceMatch, etc.),
regenerating it fresh avoids a second, potentially-stale copy of the truth.
"""
from good_agents.services.prioritisation import prioritise

ACTION_LABEL_BY_KIND = {
    'review_evidence': 'Review evidence',
    'approve_decision': 'Approve capital decision',
    'approve_action': 'Approve outreach/introduction',
    'request_data': 'Request missing dataset',
    'discuss_pilot': 'Discuss pilot',
    'monitor': 'Monitor — no action needed today',
}


def _next_safe_step(opportunity):
    if opportunity.insufficient_evidence:
        return ACTION_LABEL_BY_KIND['request_data'], 'request_data'
    pending_yellow = opportunity.actions.filter(autonomy_class='yellow', status='proposed').exists()
    if pending_yellow:
        return ACTION_LABEL_BY_KIND['approve_action'], 'approve_action'
    if opportunity.status == 'qualified':
        return ACTION_LABEL_BY_KIND['discuss_pilot'], 'discuss_pilot'
    return ACTION_LABEL_BY_KIND['review_evidence'], 'review_evidence'


def _opportunity_summary(opportunity):
    result = prioritise(opportunity)
    matched_resources = []
    for need in opportunity.needs.all():
        matched_resources.extend(m.resource.title for m in need.matches.select_related('resource').all())
    label, action_kind = _next_safe_step(opportunity)

    return {
        'id': opportunity.pk,
        'title': opportunity.title,
        'problem': opportunity.problem_statement,
        'location': opportunity.region or (opportunity.geography.name if opportunity.geography_id else ''),
        'affected_population': opportunity.affected_population,
        'evidence_refs': opportunity.evidence_refs,
        'insufficient_evidence': opportunity.insufficient_evidence,
        'relevant_principles': [
            {'principle_id': a.agent.principle_id, 'name': a.agent.name, 'position': a.position}
            for a in opportunity.agent_activations.select_related('agent').all()
        ],
        'resources_matched': matched_resources,
        'better_way_summary': getattr(opportunity, 'opportunity_cost_assessment', None) and opportunity.opportunity_cost_assessment.preferred_option,
        'potential_impact': opportunity.potential_benefit,
        'confidence': opportunity.confidence,
        'urgency': opportunity.urgency,
        'labels': result.labels,
        'next_safe_step': label,
        'next_action_kind': action_kind,
        'zero_capital_possible': opportunity.zero_capital_possible,
        'capital_required_usd': opportunity.capital_required_usd,
    }


def top_3_actions(opportunities):
    """
    AttentionPriority (Phase 18): which 3 decisions deserve human attention
    today. Ranked urgent-first, then evidence-gap (needs a human to unblock
    it), then everything else — never shows all opportunities as equally
    important.
    """
    scored = []
    for opportunity in opportunities:
        result = prioritise(opportunity)
        weight = (
            (3 if 'URGENT' in result.labels else 0)
            + (2 if 'EVIDENCE_GAP' in result.labels else 0)
            + (1 if 'HIGH_LEVERAGE' in result.labels else 0)
        )
        if weight > 0 or opportunity.actions.filter(autonomy_class='yellow', status='proposed').exists():
            scored.append((weight, opportunity))

    scored.sort(key=lambda pair: -pair[0])
    top = scored[:3]
    actions = []
    for _, opportunity in top:
        label, action_kind = _next_safe_step(opportunity)
        actions.append({'opportunity_id': opportunity.pk, 'title': opportunity.title, 'action': label, 'action_kind': action_kind})
    return actions


def build_brief(run):
    """Assembled entirely from `run` and its related, already-persisted rows."""
    opportunities = list(run.opportunities.all())
    qualified = [o for o in opportunities if o.status == 'qualified']
    zero_capital = [o for o in opportunities if o.zero_capital_possible]
    needing_approval = [o for o in opportunities if o.actions.filter(autonomy_class='yellow', status='proposed').exists()]
    capital_required = [o for o in opportunities if o.capital_required_usd]
    watch_list = [o for o in opportunities if o.insufficient_evidence]

    ranked_top = sorted(opportunities, key=lambda o: (-o.urgency, -o.confidence))[:5]

    return {
        'run_id': run.pk,
        'mission': run.mission,
        'status': run.status,
        'completed_at': run.completed_at.isoformat() if run.completed_at else None,
        'signals_reviewed': run.signals_reviewed,
        'duplicates_removed': run.duplicates_removed,
        'agents_activated': run.agents_activated,
        'opportunities_detected': run.opportunities_detected,
        'qualified_opportunities': run.qualified_opportunities,
        'rejected_opportunities': run.rejected_opportunities,
        'insufficient_evidence_count': run.insufficient_evidence_count,
        'zero_capital_opportunities': run.zero_capital_opportunities,
        'estimated_run_cost_usd': run.estimated_run_cost_usd,
        'cost_budget_usd': run.cost_budget_usd,
        'what_changed_overnight': f'{run.signals_reviewed} signals reviewed, {run.duplicates_removed} duplicates removed, {len(opportunities)} opportunities detected.',
        'problems_detected': [_opportunity_summary(o) for o in opportunities],
        'qualified': [_opportunity_summary(o) for o in qualified],
        'zero_capital_available': [_opportunity_summary(o) for o in zero_capital],
        'requires_human_approval': [_opportunity_summary(o) for o in needing_approval],
        'requires_capital': [_opportunity_summary(o) for o in capital_required],
        'watch_list': [_opportunity_summary(o) for o in watch_list],
        'top_opportunities': [_opportunity_summary(o) for o in ranked_top],
        'top_3_actions_today': top_3_actions(opportunities),
    }
