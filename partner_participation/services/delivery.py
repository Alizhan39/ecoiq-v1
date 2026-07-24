"""
partner_participation/services/delivery.py — PR9 Phase 12-13: human
approval before any share, then real (or honestly-manual) delivery.
Reuses this repo's existing email infrastructure — no second
communications stack. `RoutingCandidate.status` never reaches 'shared'
without a real `ShareDelivery` row backing it.
"""
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from partner_participation.models import ShareDelivery
from partner_participation.services import routing
from partner_participation.services.invitation import has_real_mail_transport
from partner_participation.services.share_package import render_share_message
from partner_participation.services.timeline import record_event


class ShareApprovalError(Exception):
    pass


class DeliveryError(Exception):
    pass


def approve_share(candidate, *, actor):
    """Staff inspects recipient/route/message/evidence/rationale, then explicitly approves — Phase 12."""
    if actor is None or not getattr(actor, 'is_staff', False):
        raise ShareApprovalError('Approving a share requires a real EcoIQ staff actor.')
    candidate = routing.transition(candidate, 'approved_to_share', actor=actor)
    record_event(
        candidate.organisation, 'approved_to_share', actor=actor,
        source_object_reference=f'partner_participation.RoutingCandidate:{candidate.pk}',
    )
    return candidate


def reject_share(candidate, *, actor, reason=''):
    if actor is None or not getattr(actor, 'is_staff', False):
        raise ShareApprovalError('Declining a share requires a real EcoIQ staff actor.')
    candidate = routing.transition(candidate, 'not_approved', actor=actor, notes=reason)
    record_event(
        candidate.organisation, 'not_approved_to_share', actor=actor,
        source_object_reference=f'partner_participation.RoutingCandidate:{candidate.pk}', notes=reason,
    )
    return candidate


def _find_open_email_route(organisation, capability_ids):
    from capability_graph.models import PublicRoute
    routes = PublicRoute.objects.filter(
        organisation_capability_id__in=capability_ids, is_currently_open=True,
    )
    for route in routes:
        if '@' in route.route_value:
            return route
    return None


def deliver_via_real_email(candidate, *, actor):
    """
    Real send, only when a real mail transport is configured AND the
    organisation has a real, currently-open, email-shaped public route.
    Never fabricates either condition.
    """
    if candidate.status != 'approved_to_share':
        raise DeliveryError(f'RoutingCandidate {candidate.pk} is {candidate.status!r}, not "approved_to_share".')
    if not has_real_mail_transport():
        raise DeliveryError('No real mail transport is configured — use record_manual_delivery() instead.')

    capability_ids = candidate.organisation.capabilities.values_list('pk', flat=True)
    route = _find_open_email_route(candidate.organisation, capability_ids)
    if route is None:
        raise DeliveryError('No currently-open, email-shaped public route exists for this organisation.')

    subject, body = render_share_message(candidate)
    send_mail(
        subject=subject, message=body, from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        recipient_list=[route.route_value], fail_silently=False,
    )
    delivery = ShareDelivery.objects.create(
        candidate=candidate, sender=actor, recipient=route.route_value, subject=subject, body=body,
        delivery_method='real_email', send_status='sent',
    )
    candidate = routing.transition(candidate, 'shared', actor=actor)
    record_event(
        candidate.organisation, 'shared', actor=actor,
        source_object_reference=f'partner_participation.ShareDelivery:{delivery.pk}',
    )
    from partner_participation.services.notify import notify_opportunity_shared
    notify_opportunity_shared(delivery)
    return delivery


def record_manual_delivery(candidate, *, actor, recipient, channel_notes, evidence=''):
    """
    The honest alternative when no real send infrastructure exists (or a
    human simply chose to deliver it another way — phone, in-person,
    referral through a third party). `recipient`/`channel_notes` must be
    real, specific facts a human is asserting responsibility for — never
    optional placeholders.
    """
    if actor is None or not getattr(actor, 'is_staff', False):
        raise DeliveryError('Recording a manual delivery requires a real EcoIQ staff actor.')
    if candidate.status != 'approved_to_share':
        raise DeliveryError(f'RoutingCandidate {candidate.pk} is {candidate.status!r}, not "approved_to_share".')
    if not recipient or not channel_notes:
        raise DeliveryError('recipient and channel_notes are required — a manual delivery is never recorded without them.')

    subject, body = render_share_message(candidate)
    delivery = ShareDelivery.objects.create(
        candidate=candidate, sender=actor, recipient=recipient, subject=subject, body=body,
        delivery_method='manual_recorded', send_status='sent', manual_evidence=f'{channel_notes}\n\n{evidence}'.strip(),
    )
    candidate = routing.transition(candidate, 'shared', actor=actor)
    record_event(
        candidate.organisation, 'shared', actor=actor,
        source_object_reference=f'partner_participation.ShareDelivery:{delivery.pk}',
        notes=f'Manually delivered by {actor}: {channel_notes}',
    )
    from partner_participation.services.notify import notify_opportunity_shared
    notify_opportunity_shared(delivery)
    return delivery
