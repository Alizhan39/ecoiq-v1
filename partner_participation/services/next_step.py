"""
partner_participation/services/next_step.py — PR9 Phase 16: governed
next-step creation once an organisation expresses interest. Never
automatically creates an active project — `create_project_candidate`
here only ever calls the real, existing, human-approval-gated PR5
`good_agents.services.project_bridge.propose_candidate()`, which itself
requires a further explicit approval + separate creation step before any
real GoldProject exists. The other "reuse an existing mechanism" types
similarly only ever create a soft-pointer record of what already exists,
never a duplicate of it.
"""
from partner_participation.models import NextStepAction
from partner_participation.services.timeline import record_event


class NextStepNotAllowedError(Exception):
    pass


def _require_interest(candidate):
    if candidate.status not in ('interested', 'accepted_for_next_step'):
        raise NextStepNotAllowedError(
            f'RoutingCandidate {candidate.pk} is {candidate.status!r} — a next step requires the organisation '
            f'to have expressed interest first.'
        )


def create_connection_action(candidate, *, actor, resource_match, notes=''):
    """Links to PR3/5's real ConnectionCandidate mechanism rather than duplicating it."""
    _require_interest(candidate)
    from good_agents.services import connection_action
    connection = connection_action.create_candidate(resource_match, notes=notes)
    return _record_next_step(candidate, 'connection_action', actor, f'good_agents.ConnectionCandidate:{connection.pk}', notes)


def create_data_exchange_request(candidate, *, actor, notes):
    """Genuinely new — no existing model covers a data request between EcoIQ and a partner."""
    _require_interest(candidate)
    if not notes:
        raise NextStepNotAllowedError('A data exchange request requires real notes describing what data is being requested.')
    return _record_next_step(candidate, 'data_exchange_request', actor, '', notes)


def create_meeting_request(candidate, *, actor, notes):
    _require_interest(candidate)
    if not notes:
        raise NextStepNotAllowedError('A meeting request requires real notes (proposed topic/time).')
    return _record_next_step(candidate, 'meeting_request', actor, '', notes)


def propose_project_candidate(candidate, *, actor, rationale=''):
    """
    Reuses good_agents.services.project_bridge.propose_candidate() — the
    SAME human-approval-gated mechanism PR5 built. This function never
    creates a real GoldProject; propose_candidate() only ever creates a
    'proposed' ProjectCandidate that still needs its own separate
    approve_candidate()/create_project_from_candidate() calls.
    """
    _require_interest(candidate)
    from good_agents.services import project_bridge
    project_candidate = project_bridge.propose_candidate(candidate.opportunity, rationale=rationale)
    next_step = _record_next_step(
        candidate, 'project_candidate', actor, f'good_agents.ProjectCandidate:{project_candidate.pk}', rationale,
    )
    record_event(
        candidate.organisation, 'project_candidate_created', actor=actor,
        source_object_reference=f'good_agents.ProjectCandidate:{project_candidate.pk}',
    )
    return next_step


def create_resource_match_followup(candidate, *, actor, resource_match, notes=''):
    _require_interest(candidate)
    return _record_next_step(
        candidate, 'resource_match_followup', actor, f'good_agents.ResourceMatch:{resource_match.pk}', notes,
    )


def create_funding_eligibility_review(candidate, *, actor, funding_match, notes=''):
    _require_interest(candidate)
    return _record_next_step(
        candidate, 'funding_eligibility_review', actor, f'good_agents.FundingMatch:{funding_match.pk}', notes,
    )


def _record_next_step(candidate, action_type, actor, linked_object_reference, notes):
    next_step = NextStepAction.objects.create(
        candidate=candidate, action_type=action_type, linked_object_reference=linked_object_reference,
        notes=notes, created_by=actor,
    )
    record_event(
        candidate.organisation, 'next_action_created', actor=actor,
        source_object_reference=f'partner_participation.NextStepAction:{next_step.pk}',
    )
    from partner_participation.services.notify import notify_next_step_required
    notify_next_step_required(next_step)
    return next_step
