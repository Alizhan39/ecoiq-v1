"""
good_agents/services/action_pathway.py — creates the explicit next-step
pathway for an APPROVED opportunity (PR5 Phase 2-3, 12-13). Never forces
every opportunity into a project — the caller picks the pathway type that
actually fits.
"""
from good_agents.models import ActionGate, ActionPathway
from good_agents.services import notify
from good_agents.services.action_gate import get_or_create_gate
from good_agents.services.timeline import record_event

# Pathway types this repo can genuinely support with zero owned capital
# (Phase 3 — zero-capital-first). 'project_candidate' and 'funding_referral'
# are deliberately excluded: a project or a funding application, even a
# zero-capital one, still needs a capital_required assessment made
# explicitly by the caller, not assumed here.
ZERO_CAPITAL_ELIGIBLE_PATHWAY_TYPES = frozenset({
    'information_request', 'introduction', 'resource_connection', 'authority_alert',
    'expert_review', 'data_request', 'zero_capital_action',
})


class PathwayNotAllowedError(Exception):
    """Raised when creating a pathway for an opportunity whose ActionGate isn't in an approved state."""


def create_pathway(opportunity, pathway_type, *, rationale='', capital_required='unknown',
                   zero_capital_path='', owner=None, actor=None):
    gate = get_or_create_gate(opportunity)
    if gate.current_state not in ActionGate.APPROVED_STATES:
        raise PathwayNotAllowedError(
            f'Opportunity {opportunity.pk} is in ActionGate state {gate.current_state!r}, not an approved state. '
            f'Call services.action_gate.transition(...) to approve it first.'
        )

    if capital_required == 'unknown' and pathway_type in ZERO_CAPITAL_ELIGIBLE_PATHWAY_TYPES:
        capital_required = 'no'

    pathway = ActionPathway.objects.create(
        opportunity=opportunity, pathway_type=pathway_type, rationale=rationale,
        capital_required=capital_required, zero_capital_path=zero_capital_path, owner=owner,
    )
    if capital_required == 'no':
        notify.notify_zero_capital_pathway_ready(pathway)
    if owner is not None:
        record_event(
            opportunity, 'owner_assigned', actor=actor,
            source_object_reference=f'good_agents.ActionPathway:{pathway.pk}',
            notes=f'Assigned to {owner}.',
        )
    return pathway


def assign_owner(pathway, owner, *, actor=None):
    pathway.owner = owner
    pathway.touch()
    pathway.save(update_fields=['owner'])
    record_event(
        pathway.opportunity, 'owner_assigned', actor=actor,
        source_object_reference=f'good_agents.ActionPathway:{pathway.pk}', notes=f'Assigned to {owner}.',
    )
    return pathway


def update_status(pathway, status, *, next_step='', blocked_reason=''):
    pathway.status = status
    if next_step:
        pathway.next_step = next_step
    if status == 'blocked':
        pathway.blocked_reason = blocked_reason
    pathway.touch()
    pathway.save(update_fields=['status', 'next_step', 'blocked_reason'])
    return pathway
