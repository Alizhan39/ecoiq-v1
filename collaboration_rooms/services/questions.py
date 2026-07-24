"""
collaboration_rooms/services/questions.py — structured questions /
information requests (Phase 8-9). Deliberately NOT free-text chat.
Answering never auto-closes a request — only an explicit status change
does (record_response() leaves status untouched by design).
"""
from collaboration_rooms.models import InformationRequest, InformationRequestResponse
from collaboration_rooms.permissions import get_active_participant
from collaboration_rooms.services.timeline import record_event


class QuestionNotAllowedError(Exception):
    pass


def create_request(room, *, requested_by, question_text, request_type='other', directed_to_organisation=None):
    participant = get_active_participant(room, requested_by)
    if participant is None:
        raise QuestionNotAllowedError(f'{requested_by} is not an active participant of this room.')
    if not question_text:
        raise QuestionNotAllowedError('An information request requires real question text.')
    request = InformationRequest.objects.create(
        room=room, requested_by=requested_by, requesting_organisation=participant.organisation,
        directed_to_organisation=directed_to_organisation, request_type=request_type, question_text=question_text,
    )
    record_event(
        room, 'question_asked', actor=requested_by, organisation=participant.organisation,
        source_object_reference=f'collaboration_rooms.InformationRequest:{request.pk}',
    )
    from collaboration_rooms.services.notify import notify_information_request, notify_response_required
    notify_information_request(request)
    if directed_to_organisation is not None:
        notify_response_required(request)
    return request


def record_response(request, *, responded_by, answer_text, evidence_item=None):
    participant = get_active_participant(request.room, responded_by)
    if participant is None:
        raise QuestionNotAllowedError(f'{responded_by} is not an active participant of this room.')
    if not answer_text:
        raise QuestionNotAllowedError('A response requires real answer text.')
    response = InformationRequestResponse.objects.create(
        request=request, responded_by=responded_by, responding_organisation=participant.organisation,
        answer_text=answer_text, evidence_item=evidence_item,
    )
    record_event(
        request.room, 'answer_provided', actor=responded_by, organisation=participant.organisation,
        source_object_reference=f'collaboration_rooms.InformationRequestResponse:{response.pk}',
    )
    return response


def set_status(request, new_status, *, actor):
    """
    An explicit, real decision — Phase 9's own "do not mark request
    complete merely because a text response exists". Any active
    participant may make this call (the requester deciding their
    question was answered, or a coordinator triaging).
    """
    participant = get_active_participant(request.room, actor)
    if participant is None:
        raise QuestionNotAllowedError(f'{actor} is not an active participant of this room.')
    request.status = new_status
    if new_status == 'closed':
        request.closed_by = actor
        from django.utils import timezone
        request.closed_at = timezone.now()
        request.save(update_fields=['status', 'closed_by', 'closed_at'])
    else:
        request.save(update_fields=['status'])
    record_event(
        request.room, 'request_status_changed', actor=actor, organisation=participant.organisation,
        source_object_reference=f'collaboration_rooms.InformationRequest:{request.pk}', notes=f'-> {new_status}',
    )
    return request
