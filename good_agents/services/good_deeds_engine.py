"""
good_agents/services/good_deeds_engine.py — GoodDeedsEngine (Phase 4):
converts a GoodOpportunity into concrete next actions, each tagged with an
autonomy class. RED actions are structurally unreachable through this
action-type enum — see good_agents.models.classify_autonomy's docstring.
"""
from good_agents.models import GoodDeedAction, classify_autonomy

DEFAULT_ACTIONS_BY_STATUS = {
    'potential': ['research', 'verify', 'analyse'],
    'qualified': ['compare', 'find_resource', 'find_funding'],
}


def propose_actions(opportunity, action_types):
    """
    Create (or return existing) GoodDeedAction rows for `action_types`.
    Idempotent per (opportunity, action_type) — re-running discovery for the
    same opportunity never duplicates an action.
    """
    created = []
    for action_type in action_types:
        action, _ = GoodDeedAction.objects.get_or_create(
            opportunity=opportunity, action_type=action_type,
            defaults={'autonomy_class': classify_autonomy(action_type), 'status': 'proposed'},
        )
        created.append(action)
    return created


def propose_default_actions(opportunity):
    """Convenience wrapper: pick a sensible action set from the opportunity's current status."""
    action_types = list(DEFAULT_ACTIONS_BY_STATUS.get(opportunity.status, ['research']))
    if opportunity.zero_capital_possible:
        action_types += ['find_partner', 'match']
    return propose_actions(opportunity, action_types)


def approve_action(action):
    """
    The only place an action may move past 'proposed'/'awaiting_approval'.
    GREEN actions need no human gate. YELLOW actions require explicit
    human_approved=True. RED actions are rejected outright — this system has
    no execution capability for them (Phase 0 audit, area 11: Execution is a
    confirmed dead end).
    """
    if action.autonomy_class == 'red':
        action.status = 'blocked'
        action.blocked_reason = 'RED actions cannot be executed by this system — a human must act outside EcoIQ.'
        action.save(update_fields=['status', 'blocked_reason', 'updated_at'])
        return action
    if action.autonomy_class == 'yellow':
        action.human_approved = True
        action.status = 'approved'
        action.save(update_fields=['human_approved', 'status', 'updated_at'])
        return action
    action.status = 'approved'
    action.save(update_fields=['status', 'updated_at'])
    return action


def complete_action(action, output_summary=''):
    if action.autonomy_class == 'red':
        raise ValueError('RED actions can never be completed by this system.')
    if action.autonomy_class == 'yellow' and not action.human_approved:
        raise ValueError('YELLOW action must be human-approved before completion.')
    action.status = 'completed'
    action.output_summary = output_summary
    action.save(update_fields=['status', 'output_summary', 'updated_at'])
    return action
