"""
good_agents/services/connection_action.py — governed "propose connection"
workflow over an existing ResourceMatch (PR5 Phase 8). Never implies the
resource provider has agreed to anything — `interest_confirmed` can only
be set by a human recording a real, external confirmation.
"""
from django.utils import timezone

from good_agents.models import ConnectionCandidate
from good_agents.services import notify
from good_agents.services.timeline import record_event

TERMINAL_STATES = frozenset({'not_suitable', 'declined', 'expired', 'interest_confirmed'})


def create_candidate(resource_match, *, action_pathway=None, notes=''):
    candidate, created = ConnectionCandidate.objects.get_or_create(
        resource_match=resource_match, defaults=dict(action_pathway=action_pathway, notes=notes),
    )
    if created:
        notify.notify_connection_candidate_ready(candidate)
    return candidate


def approve_for_introduction(candidate, *, actor):
    if candidate.status != 'candidate_match':
        raise ValueError(f'ConnectionCandidate {candidate.pk} is {candidate.status!r}, not "candidate_match".')
    candidate.status = 'approved_for_introduction'
    candidate.approved_by = actor
    candidate.approved_at = timezone.now()
    candidate.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
    opportunity = candidate.resource_match.need.opportunity
    if opportunity is not None:
        record_event(
            opportunity, 'action_approved', actor=actor,
            source_object_reference=f'good_agents.ConnectionCandidate:{candidate.pk}',
            notes=f'Approved for introduction: {candidate.resource_match}',
        )
    return candidate


def mark_introduced(candidate, *, actor=None, notes=''):
    if candidate.status != 'approved_for_introduction':
        raise ValueError(f'ConnectionCandidate {candidate.pk} is {candidate.status!r}, not "approved_for_introduction".')
    candidate.status = 'introduced'
    if notes:
        candidate.notes = f'{candidate.notes}\n\n{notes}'.strip()
    candidate.save(update_fields=['status', 'notes', 'updated_at'])
    opportunity = candidate.resource_match.need.opportunity
    if opportunity is not None:
        record_event(
            opportunity, 'connection_made', actor=actor,
            source_object_reference=f'good_agents.ConnectionCandidate:{candidate.pk}', notes=notes,
        )
    return candidate


def record_outcome(candidate, status, *, notes=''):
    """status: one of 'interest_confirmed' / 'not_suitable' / 'declined' / 'expired' — always a real, human-recorded outcome."""
    if status not in TERMINAL_STATES:
        raise ValueError(f'{status!r} is not a valid connection outcome.')
    candidate.status = status
    if notes:
        candidate.notes = f'{candidate.notes}\n\n{notes}'.strip()
    candidate.save(update_fields=['status', 'notes', 'updated_at'])
    return candidate
