"""
collaboration_rooms/services/proposals.py — structured next-step
proposals (Phase 11) and mutual consent (Phase 12-13). Consent is NEVER
inferred from silence: a proposal reaches 'accepted' only when every
required RoomConsent row is explicitly 'approved' — checked freshly on
every consent change, never cached as a boolean flag that could drift.
"""
from django.utils import timezone

from collaboration_rooms.models import (
    NEXT_STEP_PROPOSAL_ALLOWED_TRANSITIONS, NextStepProposal, RoomConsent,
)
from collaboration_rooms.permissions import get_active_participant
from collaboration_rooms.services.timeline import record_event


class ProposalNotAllowedError(Exception):
    pass


class IllegalProposalTransitionError(Exception):
    pass


def create_proposal(room, *, proposed_by, proposal_type, description='', required_organisations=None,
                     requires_ecoiq_consent=True, linked_resource_match=None, linked_funding_match=None):
    participant = get_active_participant(room, proposed_by)
    if participant is None or participant.role not in ('coordinator', 'organisation_representative', 'expert'):
        raise ProposalNotAllowedError(f'{proposed_by} may not propose a next step in this room.')
    proposal = NextStepProposal.objects.create(
        room=room, proposed_by=proposed_by, proposing_organisation=participant.organisation,
        proposal_type=proposal_type, description=description, requires_ecoiq_consent=requires_ecoiq_consent,
        linked_resource_match=linked_resource_match, linked_funding_match=linked_funding_match,
    )
    if required_organisations:
        proposal.required_organisations.set(required_organisations)
    return proposal


def _transition(proposal, new_status):
    allowed = NEXT_STEP_PROPOSAL_ALLOWED_TRANSITIONS.get(proposal.status, set())
    if new_status not in allowed:
        raise IllegalProposalTransitionError(f'Cannot move NextStepProposal {proposal.pk} from {proposal.status!r} to {new_status!r}.')
    proposal.status = new_status
    proposal.save(update_fields=['status', 'updated_at'])
    return proposal


def propose(proposal, *, actor):
    """Moves DRAFT -> PROPOSED and materialises one RoomConsent row per required party — the consent matrix (Phase 13)."""
    participant = get_active_participant(proposal.room, actor)
    if participant is None:
        raise ProposalNotAllowedError(f'{actor} is not an active participant of this room.')
    _transition(proposal, 'proposed')
    from collaboration_rooms.services.notify import notify_consent_required, notify_next_step_proposed
    if proposal.requires_ecoiq_consent:
        consent, _ = RoomConsent.objects.get_or_create(proposal=proposal, organisation=None)
        notify_consent_required(consent)
    for organisation in proposal.required_organisations.all():
        consent, _ = RoomConsent.objects.get_or_create(proposal=proposal, organisation=organisation)
        notify_consent_required(consent)
    record_event(
        proposal.room, 'next_step_proposed', actor=actor, organisation=participant.organisation,
        source_object_reference=f'collaboration_rooms.NextStepProposal:{proposal.pk}',
    )
    notify_next_step_proposed(proposal)
    return proposal


def give_consent(proposal, *, actor, organisation=None, notes=''):
    """
    `organisation=None` means the actor is consenting AS EcoIQ (requires
    staff). Otherwise the actor must be an acting participant representing
    exactly that organisation — never consent on another organisation's behalf.
    """
    if organisation is None:
        if actor is None or not getattr(actor, 'is_staff', False):
            raise ProposalNotAllowedError('Consenting on EcoIQ\'s behalf requires a real EcoIQ staff actor.')
    else:
        participant = get_active_participant(proposal.room, actor)
        if participant is None or participant.organisation_id != organisation.pk or participant.role not in (
            'organisation_representative', 'expert',
        ):
            raise ProposalNotAllowedError(f'{actor} may not consent on behalf of {organisation}.')

    consent, _ = RoomConsent.objects.get_or_create(proposal=proposal, organisation=organisation)
    consent.status = 'approved'
    consent.actor = actor
    consent.decided_at = timezone.now()
    consent.notes = notes
    consent.save(update_fields=['status', 'actor', 'decided_at', 'notes'])
    record_event(
        proposal.room, 'consent_given', actor=actor, organisation=organisation,
        source_object_reference=f'collaboration_rooms.RoomConsent:{consent.pk}',
    )
    from collaboration_rooms.services.notify import notify_consent_received
    notify_consent_received(consent)
    return check_and_apply_consensus(proposal)


def reject_consent(proposal, *, actor, organisation=None, notes=''):
    if organisation is None:
        if actor is None or not getattr(actor, 'is_staff', False):
            raise ProposalNotAllowedError('Rejecting on EcoIQ\'s behalf requires a real EcoIQ staff actor.')
    else:
        participant = get_active_participant(proposal.room, actor)
        if participant is None or participant.organisation_id != organisation.pk or participant.role not in (
            'organisation_representative', 'expert',
        ):
            raise ProposalNotAllowedError(f'{actor} may not reject on behalf of {organisation}.')

    consent, _ = RoomConsent.objects.get_or_create(proposal=proposal, organisation=organisation)
    consent.status = 'rejected'
    consent.actor = actor
    consent.decided_at = timezone.now()
    consent.notes = notes
    consent.save(update_fields=['status', 'actor', 'decided_at', 'notes'])
    record_event(
        proposal.room, 'consent_rejected', actor=actor, organisation=organisation,
        source_object_reference=f'collaboration_rooms.RoomConsent:{consent.pk}',
    )
    if proposal.status == 'proposed':
        _transition(proposal, 'rejected')
        from collaboration_rooms.services.notify import notify_next_step_rejected
        notify_next_step_rejected(proposal)
    return proposal


def check_and_apply_consensus(proposal):
    """
    The consent matrix's own read: only 'accepted' when EVERY required
    consent row is 'approved' — a single pending or rejected row means
    not yet ready, full stop. Never inferred from a majority or from silence.
    """
    proposal.refresh_from_db()
    if proposal.status != 'proposed':
        return proposal
    consents = list(proposal.consents.all())
    if not consents:
        return proposal
    if any(c.status == 'rejected' for c in consents):
        return proposal  # reject_consent() already transitions the proposal itself
    if all(c.status == 'approved' for c in consents):
        _transition(proposal, 'accepted')
        record_event(proposal.room, 'next_step_agreed', source_object_reference=f'collaboration_rooms.NextStepProposal:{proposal.pk}')
        from collaboration_rooms.services.notify import notify_project_candidate_ready, notify_ready_for_action
        if proposal.proposal_type == 'project_candidate':
            notify_project_candidate_ready(proposal)
        else:
            notify_ready_for_action(proposal)
    return proposal


def request_modification(proposal, *, actor, notes=''):
    participant = get_active_participant(proposal.room, actor)
    if participant is None:
        raise ProposalNotAllowedError(f'{actor} is not an active participant of this room.')
    _transition(proposal, 'needs_modification')
    record_event(proposal.room, 'room_status_changed', actor=actor, notes=f'Proposal {proposal.pk} needs modification: {notes}')
    return proposal
