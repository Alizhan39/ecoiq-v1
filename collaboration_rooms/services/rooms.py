"""
collaboration_rooms/services/rooms.py — room creation gate (Phase 2),
participant management (Phase 3-4), status transitions (Phase 19), and
withdrawal (Phase 30). No unsolicited room creation: create_room() only
ever succeeds for a RoutingCandidate already in a real, governed
interested-adjacent state, and only when called by a real staff actor.
"""
import datetime

from django.utils import timezone

from collaboration_rooms.models import (
    ROOM_CREATION_ALLOWED_CANDIDATE_STATUSES, CollaborationRoom, RoomParticipant,
)
from collaboration_rooms.services.timeline import record_event
from partner_participation.models import OrganisationMembership

STALL_GRACE_DAYS_DEFAULT = 10


class RoomCreationNotAllowedError(Exception):
    pass


class RoomAccessError(Exception):
    pass


def create_room(routing_candidate, *, actor, title=''):
    """
    Phase 2's own creation gate: requires a real staff actor AND a
    RoutingCandidate already in 'interested' / 'needs_more_information' /
    'accepted_for_next_step' — never merely because EcoIQ found a match
    (routing_candidate / ready_for_ecoiq_review / approved_to_share /
    shared / no_response / viewed are all explicitly NOT enough). One
    room per candidate — idempotent via the model's own OneToOneField.
    """
    if actor is None or not getattr(actor, 'is_staff', False):
        raise RoomCreationNotAllowedError('Creating a collaboration room requires a real EcoIQ staff actor.')
    if routing_candidate.status not in ROOM_CREATION_ALLOWED_CANDIDATE_STATUSES:
        raise RoomCreationNotAllowedError(
            f'RoutingCandidate {routing_candidate.pk} is {routing_candidate.status!r} — a room may only be '
            f'created once the organisation is interested, needs more information, or accepted a next step.'
        )
    existing = CollaborationRoom.objects.filter(routing_candidate=routing_candidate).first()
    if existing is not None:
        return existing

    room = CollaborationRoom.objects.create(
        routing_candidate=routing_candidate,
        title=title or f'{routing_candidate.opportunity.title} — {routing_candidate.organisation.name}',
        created_by=actor,
    )
    RoomParticipant.objects.create(
        room=room, user=actor, organisation=None, role='coordinator',
        reason='Created this room as the EcoIQ coordinator.', added_by=actor,
    )
    # The anchor organisation's verified members have an inherent reason to
    # access this room — their own organisation is the one that expressed
    # interest. No other organisation/expert is ever auto-added (Phase 3).
    for membership in OrganisationMembership.objects.filter(
        organisation=routing_candidate.organisation, status='verified_member',
    ):
        RoomParticipant.objects.get_or_create(
            room=room, user=membership.user,
            defaults=dict(
                organisation=routing_candidate.organisation, role='organisation_representative',
                reason=f'Verified member of {routing_candidate.organisation.name}, the organisation that responded to this opportunity.',
                added_by=actor,
            ),
        )
    record_event(room, 'room_created', actor=actor, organisation=routing_candidate.organisation)
    return room


def add_participant(room, *, user, organisation, role, reason, actor):
    """Any participant beyond the anchor org's verified members must be explicitly added by staff, with a stated reason."""
    if actor is None or not getattr(actor, 'is_staff', False):
        raise RoomAccessError('Adding a room participant requires a real EcoIQ staff actor.')
    if not reason:
        raise RoomAccessError('A participant may not be added without a stated reason for access.')
    participant, created = RoomParticipant.objects.get_or_create(
        room=room, user=user,
        defaults=dict(organisation=organisation, role=role, reason=reason, added_by=actor),
    )
    if not created and participant.revoked_at is not None:
        participant.role = role
        participant.reason = reason
        participant.added_by = actor
        participant.revoked_at = None
        participant.revoked_by = None
        participant.revoked_reason = ''
        participant.save(update_fields=['role', 'reason', 'added_by', 'revoked_at', 'revoked_by', 'revoked_reason'])
    record_event(room, 'participant_added', actor=actor, organisation=organisation, source_object_reference=f'collaboration_rooms.RoomParticipant:{participant.pk}')
    from collaboration_rooms.services.notify import notify_participant_added
    notify_participant_added(participant)
    return participant


def revoke_participant(participant, *, actor, reason=''):
    if actor is None or not getattr(actor, 'is_staff', False):
        raise RoomAccessError('Revoking a room participant requires a real EcoIQ staff actor.')
    participant.revoked_at = timezone.now()
    participant.revoked_by = actor
    participant.revoked_reason = reason
    participant.save(update_fields=['revoked_at', 'revoked_by', 'revoked_reason'])
    record_event(participant.room, 'participant_revoked', actor=actor, organisation=participant.organisation, notes=reason)
    return participant


def withdraw_organisation(room, organisation, *, actor):
    """
    Phase 30 — an organisation may withdraw. History (messages, evidence,
    consents already given) is preserved untouched; only future access is
    revoked. Any NextStepProposal still awaiting this organisation's
    consent is left PENDING (never silently approved/rejected on its
    behalf) — services.proposals.check_and_apply_consensus() will simply
    never reach consensus for it, which is the honest outcome.
    """
    revoked = []
    for participant in room.participants.filter(organisation=organisation, revoked_at__isnull=True):
        revoked.append(revoke_participant(participant, actor=actor, reason=f'{organisation.name} withdrew from this collaboration.'))
    record_event(room, 'organisation_withdrew', actor=actor, organisation=organisation)
    return revoked


def set_status(room, new_status, *, actor=None, notes=''):
    room.status = new_status
    room.save(update_fields=['status', 'updated_at'])
    record_event(room, 'room_status_changed', actor=actor, notes=f'-> {new_status}. {notes}'.strip())
    return room


def close_room(room, *, actor, reason=''):
    if actor is None or not getattr(actor, 'is_staff', False):
        raise RoomAccessError('Closing a collaboration room requires a real EcoIQ staff actor.')
    room.status = 'closed'
    room.closed_by = actor
    room.closed_at = timezone.now()
    room.close_reason = reason
    room.save(update_fields=['status', 'closed_by', 'closed_at', 'close_reason', 'updated_at'])
    record_event(room, 'room_closed', actor=actor, notes=reason)
    return room


def detect_stalled_rooms(*, grace_days=STALL_GRACE_DAYS_DEFAULT):
    """
    Phase 29 — a honest label, never an auto-close. Returns the rooms
    newly flagged this call (does not re-flag ones already inactive/closed).
    """
    cutoff = timezone.now() - datetime.timedelta(days=grace_days)
    stalled = []
    for room in CollaborationRoom.objects.exclude(status__in=['closed', 'archived', 'promoted_to_action', 'promoted_to_project']):
        if room.last_activity_at >= cutoff:
            continue
        already_flagged = room.activity_events.filter(
            event_type='stall_detected', created_at__gte=room.last_activity_at,
        ).exists()
        if already_flagged:
            continue
        record_event(room, 'stall_detected', notes=f'No activity for {grace_days}+ days.', touch=False)
        stalled.append(room)
    return stalled
