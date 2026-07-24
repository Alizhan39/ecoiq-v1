"""
collaboration_rooms/services/messaging.py — deliberately minimal
controlled messaging (Phase 10). No anonymous messages (author is always
the real authenticated participant); no silent edits (edit_history keeps
every prior body).
"""
from django.utils import timezone

from collaboration_rooms.models import RoomMessage
from collaboration_rooms.permissions import get_active_participant
from collaboration_rooms.services.timeline import record_event


class MessageNotAllowedError(Exception):
    pass


def post_message(room, *, author, body, visibility='shared_with_room'):
    participant = get_active_participant(room, author)
    if participant is None:
        raise MessageNotAllowedError(f'{author} is not an active participant of this room.')
    if not body:
        raise MessageNotAllowedError('A message requires real body text.')
    message = RoomMessage.objects.create(room=room, author=author, organisation=participant.organisation, body=body, visibility=visibility)
    record_event(
        room, 'message_sent', actor=author, organisation=participant.organisation,
        source_object_reference=f'collaboration_rooms.RoomMessage:{message.pk}',
    )
    return message


def edit_message(message, *, actor, new_body):
    if actor.pk != message.author_id:
        raise MessageNotAllowedError('Only the original author may edit their own message.')
    if not new_body:
        raise MessageNotAllowedError('An edit requires real body text.')
    message.edit_history = message.edit_history + [{'body': message.body, 'edited_at': timezone.now().isoformat()}]
    message.body = new_body
    message.edited_at = timezone.now()
    message.save(update_fields=['body', 'edited_at', 'edit_history'])
    return message
