"""
partner_participation/services/notify.py — meaningful notifications only
(Phase 27's own instruction: "Do not spam on every profile edit"). Reuses
notifications.create_notification (PR4's own precedent) — no second
notification system.
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
        title, source_type='partner_participation', message=message, instance=instance,
        priority=priority, metadata={'reason': reason}, admin_url=admin_url,
    )


def notify_membership_claim_requires_review(membership):
    return _notify_once(
        membership, 'membership_claim_requires_review',
        title=f'Organisation claim awaiting review: {membership.organisation.name}',
        message=f'{membership.user} has requested {membership.get_role_display()} access to {membership.organisation.name}.',
        priority='high', admin_url=reverse('partner_participation:membership_review_queue'),
    )


def notify_capability_declaration_requires_review(edge):
    return _notify_once(
        edge, 'capability_declaration_requires_review',
        title=f'Capability declaration awaiting review: {edge.organisation.name}',
        message=f'{edge.organisation.name} declared "{edge.get_capability_display()}" — needs EcoIQ review.',
        admin_url=reverse('partner_participation:declaration_review_queue'),
    )


def notify_new_resource_available(resource):
    return _notify_once(
        resource, 'new_resource_available',
        title=f'New resource declared: {resource.title}',
        message=f'{resource.organisation.name if resource.organisation_id else "An organisation"} declared a new {resource.get_resource_type_display()} resource.',
    )


def notify_funding_programme_declared(declaration):
    return _notify_once(
        declaration, 'funding_programme_declared',
        title=f'Funding programme declared: {declaration.programme_name}',
        message=f'{declaration.organisation.name} declared a new funding programme — needs EcoIQ review.',
    )


def notify_funding_programme_deadline_approaching(declaration, *, days_threshold=14):
    from django.utils import timezone
    if not declaration.deadline:
        return None
    days_left = (declaration.deadline - timezone.now().date()).days
    if days_left < 0 or days_left > days_threshold:
        return None
    return _notify_once(
        declaration, 'funding_programme_deadline_approaching',
        title=f'Funding programme deadline approaching: {declaration.programme_name}',
        message=f'{days_left} day(s) left until the deadline.',
        priority='high',
    )


def notify_opportunity_routed_for_review(candidate):
    return _notify_once(
        candidate, 'opportunity_routed_for_review',
        title=f'Routing candidate ready for review: {candidate.organisation.name}',
        message=f'{candidate.opportunity.title} may suit {candidate.organisation.name} — needs EcoIQ approval before sharing.',
        admin_url=reverse('partner_participation:network_overview'),
    )


def notify_organisation_interested(candidate):
    return _notify_once(
        candidate, 'organisation_interested',
        title=f'{candidate.organisation.name} expressed interest',
        message=f'{candidate.organisation.name} marked interest in "{candidate.opportunity.title}".',
        priority='high',
    )


def notify_route_became_stale(edge):
    return _notify_once(
        edge, 'route_became_stale',
        title=f'Route needs reconfirmation: {edge.organisation.name}',
        message=f'"{edge.get_capability_display()}" for {edge.organisation.name} is past its reconfirmation date.',
    )
