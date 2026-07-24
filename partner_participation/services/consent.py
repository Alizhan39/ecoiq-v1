"""
partner_participation/services/consent.py — explicit participation
consent (PR9 Phase 4). Never inferred from account creation or from a
membership merely existing — a verified member with no consent record is
NOT routing-ready (see services/onboarding.py).
"""
from django.utils import timezone

from partner_participation.models import CURRENT_CONSENT_TERMS_VERSION, ParticipationConsent


class ConsentNotAllowedError(Exception):
    pass


def record_consent(membership, *, actor, terms_version=CURRENT_CONSENT_TERMS_VERSION):
    """
    Requires the REAL person consenting — never staff-on-their-behalf,
    and only the membership's own real user.
    """
    if actor is None:
        raise ConsentNotAllowedError('Consent requires a real actor.')
    if actor.pk != membership.user_id:
        raise ConsentNotAllowedError('Only the membership holder themselves can record their own consent.')
    if membership.status != 'verified_member':
        raise ConsentNotAllowedError('Consent can only be recorded for a verified membership.')

    consent, created = ParticipationConsent.objects.get_or_create(
        membership=membership, defaults=dict(actor=actor, terms_version=terms_version),
    )
    if not created and consent.status == 'withdrawn':
        consent.status = 'active'
        consent.actor = actor
        consent.terms_version = terms_version
        consent.consented_at = timezone.now()
        consent.withdrawn_at = None
        consent.save(update_fields=['status', 'actor', 'terms_version', 'consented_at', 'withdrawn_at'])

    from partner_participation.services.timeline import record_event
    record_event(
        membership.organisation, 'consent_recorded', actor=actor,
        source_object_reference=f'partner_participation.ParticipationConsent:{consent.pk}',
    )
    _check_and_notify_routing_ready(membership.organisation)
    return consent


def _check_and_notify_routing_ready(organisation):
    from partner_participation.services.notify import notify_organisation_routing_ready
    from partner_participation.services.onboarding import is_routing_ready
    ready, _reasons = is_routing_ready(organisation)
    if ready:
        notify_organisation_routing_ready(organisation)


def withdraw_consent(consent, *, actor):
    if actor is None or actor.pk != consent.membership.user_id:
        raise ConsentNotAllowedError('Only the membership holder themselves can withdraw their own consent.')
    consent.status = 'withdrawn'
    consent.withdrawn_at = timezone.now()
    consent.save(update_fields=['status', 'withdrawn_at'])

    from partner_participation.services.timeline import record_event
    record_event(consent.membership.organisation, 'consent_withdrawn', actor=actor)
    return consent


def has_active_consent(membership):
    return ParticipationConsent.objects.filter(membership=membership, status='active').exists()
