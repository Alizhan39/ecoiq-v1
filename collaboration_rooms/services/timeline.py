"""collaboration_rooms/services/timeline.py — append-only room timeline (Phase 20)."""
from collaboration_rooms.models import RoomActivityEvent


def record_event(room, event_type, *, actor=None, organisation=None, source_object_reference='', notes='', touch=True):
    if touch:
        room.touch()
    return RoomActivityEvent.objects.create(
        room=room, event_type=event_type, actor=actor, organisation=organisation,
        source_object_reference=source_object_reference, notes=notes,
    )
