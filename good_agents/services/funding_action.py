"""
good_agents/services/funding_action.py — governed tracking over an
existing FundingMatch (PR5 Phase 9). Never says "funding secured" until
`status='awarded'`, which only a human recording real, external
confirmation can set. Grant-application automation is explicitly out of
scope for this PR (Phase 9's own instruction).
"""
from good_agents.models import FundingAction

# Statuses that require an explicit, real deadline before being entered —
# stops a caller pretending "application_started" means work is happening
# against a fabricated timeline.
_NO_FABRICATED_DEADLINE_NOTE = 'No real deadline is known for this funding match yet.'


def create_action(funding_match, *, action_pathway=None, deadline=None, notes=''):
    action, created = FundingAction.objects.get_or_create(
        funding_match=funding_match,
        defaults=dict(action_pathway=action_pathway, deadline=deadline, notes=notes or ''),
    )
    if created and deadline is None and not notes:
        action.notes = _NO_FABRICATED_DEADLINE_NOTE
        action.save(update_fields=['notes'])
    return action


def update_status(action, status, *, notes=''):
    if action.funding_match.eligibility_status == 'requires_sharia_review' and status == 'awarded':
        raise ValueError(
            f'FundingAction {action.pk} funder type requires Sharia review before it may be marked awarded — '
            f'see FundingMatch.eligibility_status.'
        )
    action.status = status
    if notes:
        action.notes = f'{action.notes}\n\n{notes}'.strip()
    action.save(update_fields=['status', 'notes', 'updated_at'])
    return action
