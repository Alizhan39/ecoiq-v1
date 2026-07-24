"""
collaboration_rooms/services/notify.py — meaningful room events only
(Phase 24). Reuses notifications.create_notification — no second
notification system. Deduped exactly like partner_participation.services.notify.
"""
from django.urls import reverse

from notifications.models import AdminNotification, create_notification


def _already_notified(instance, reason):
    return AdminNotification.objects.filter(
        source_model=f'{instance._meta.app_label}.{instance._meta.model_name}',
        source_object_id=str(instance.pk),
        metadata__reason=reason,
    ).exists()


def _notify_once(instance, reason, *, title, message, priority='normal', admin_url=''):
    if _already_notified(instance, reason):
        return None
    return create_notification(
        title, source_type='collaboration_rooms', message=message, instance=instance,
        priority=priority, metadata={'reason': reason}, admin_url=admin_url,
    )


def notify_participant_added(participant):
    return _notify_once(
        participant, 'participant_added',
        title=f'Added to collaboration room: {participant.room.title}',
        message=f'{participant.user} was added as {participant.get_role_display()}.',
        admin_url=reverse('collaboration_rooms:room_detail', args=[participant.room_id]),
    )


def notify_information_request(request):
    return _notify_once(
        request, 'information_request_created',
        title=f'New information request in {request.room.title}',
        message=request.question_text[:200],
        admin_url=reverse('collaboration_rooms:room_detail', args=[request.room_id]),
    )


def notify_response_required(request):
    """A response is needed — deliberately separate reason from creation so both can fire independently if ever staged."""
    return _notify_once(
        request, 'response_required',
        title=f'Response needed: {request.room.title}',
        message=request.question_text[:200], priority='high',
        admin_url=reverse('collaboration_rooms:room_detail', args=[request.room_id]),
    )


def notify_next_step_proposed(proposal):
    return _notify_once(
        proposal, 'next_step_proposed',
        title=f'Next step proposed in {proposal.room.title}',
        message=f'{proposal.get_proposal_type_display()}: {proposal.description[:150]}',
        admin_url=reverse('collaboration_rooms:room_detail', args=[proposal.room_id]),
    )


def notify_consent_required(consent):
    party = consent.organisation.name if consent.organisation_id else 'EcoIQ'
    return _notify_once(
        consent, 'consent_required',
        title=f'Consent required from {party}: {consent.proposal.room.title}',
        message=consent.proposal.get_proposal_type_display(), priority='high',
        admin_url=reverse('collaboration_rooms:room_detail', args=[consent.proposal.room_id]),
    )


def notify_consent_received(consent):
    party = consent.organisation.name if consent.organisation_id else 'EcoIQ'
    return _notify_once(
        consent, 'consent_received',
        title=f'{party} consented: {consent.proposal.room.title}',
        message=consent.proposal.get_proposal_type_display(),
        admin_url=reverse('collaboration_rooms:room_detail', args=[consent.proposal.room_id]),
    )


def notify_next_step_rejected(proposal):
    return _notify_once(
        proposal, 'next_step_rejected',
        title=f'Next step rejected: {proposal.room.title}',
        message=proposal.get_proposal_type_display(),
        admin_url=reverse('collaboration_rooms:room_detail', args=[proposal.room_id]),
    )


def notify_ready_for_action(proposal):
    return _notify_once(
        proposal, 'ready_for_action',
        title=f'Ready to promote to action: {proposal.room.title}',
        message=f'All required parties consented to: {proposal.get_proposal_type_display()}.', priority='high',
        admin_url=reverse('collaboration_rooms:room_detail', args=[proposal.room_id]),
    )


def notify_project_candidate_ready(proposal):
    return _notify_once(
        proposal, 'project_candidate_ready',
        title=f'Ready to promote to project candidate: {proposal.room.title}',
        message='All required parties consented to creating a project candidate.', priority='high',
        admin_url=reverse('collaboration_rooms:room_detail', args=[proposal.room_id]),
    )


def send_room_email_notification(room, recipient_email, action_required, *, request=None):
    """
    Phase 25 — minimal, safe email: room title, what's required, and a
    secure deep link only. Never includes evidence/message/proposal
    content, and never mutates anything from an email link itself (the
    link only opens the room; every real action still requires a real
    authenticated click inside it). Uses the SAME real-vs-non-real
    transport honesty check PR9's invitation service established — never
    claims a send that didn't really happen.
    """
    from partner_participation.services.invitation import has_real_mail_transport
    if not has_real_mail_transport():
        return False
    from django.conf import settings
    from django.core.mail import send_mail
    path = reverse('collaboration_rooms:room_detail', args=[room.pk])
    link = request.build_absolute_uri(path) if request is not None else path
    send_mail(
        subject=f'EcoIQ Collaboration Room — action required: {room.title}',
        message=f'{action_required}\n\nOpen the room: {link}',
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None), recipient_list=[recipient_email], fail_silently=False,
    )
    return True
