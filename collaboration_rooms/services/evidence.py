"""
collaboration_rooms/services/evidence.py — governed evidence sharing and
the claim/evidence separation (Phase 6-7). A statement never becomes
'ecoiq_verified' by itself; only verify_item() with a real staff actor
can move it up the ladder, mirroring capability_graph's own verification
discipline (self_reported -> ... -> independently_verified).
"""
from django.utils import timezone

from collaboration_rooms.models import RoomEvidenceItem
from collaboration_rooms.permissions import get_active_participant
from collaboration_rooms.services.timeline import record_event


class EvidenceNotAllowedError(Exception):
    pass


def share_evidence(room, *, shared_by, title, evidence_type='other', description='', source_url='',
                    source_reference='', visibility='shared_with_room'):
    participant = get_active_participant(room, shared_by)
    if participant is None:
        raise EvidenceNotAllowedError(f'{shared_by} is not an active participant of this room.')
    item = RoomEvidenceItem.objects.create(
        room=room, shared_by=shared_by, organisation=participant.organisation,
        evidence_type=evidence_type, description=description, source_url=source_url,
        source_reference=source_reference, visibility=visibility, title=title,
        # A source_reference pointing at a real existing row starts one rung up the
        # ladder ('linked_evidence'); a bare declaration with nothing behind it stays
        # a 'declared_claim' until a human independently verifies it.
        verification_state='linked_evidence' if (source_url or source_reference) else 'declared_claim',
    )
    record_event(
        room, 'evidence_shared', actor=shared_by, organisation=participant.organisation,
        source_object_reference=f'collaboration_rooms.RoomEvidenceItem:{item.pk}',
    )
    return item


def verify_item(item, *, actor):
    if actor is None or not getattr(actor, 'is_staff', False):
        raise EvidenceNotAllowedError('Verifying evidence requires a real EcoIQ staff actor.')
    item.verification_state = 'ecoiq_verified'
    item.verified_by = actor
    item.verified_at = timezone.now()
    item.save(update_fields=['verification_state', 'verified_by', 'verified_at'])
    record_event(
        item.room, 'evidence_verified', actor=actor, organisation=item.organisation,
        source_object_reference=f'collaboration_rooms.RoomEvidenceItem:{item.pk}',
    )
    return item
