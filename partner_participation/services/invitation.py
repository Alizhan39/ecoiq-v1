"""
partner_participation/services/invitation.py — real partner onboarding
invitations (PR9 Phase 1-3). Reuses this repo's existing
`django.core.mail.send_mail`/`EMAIL_BACKEND` infrastructure exactly like
PR5's `good_agents.services.outreach.send_outreach()` — no second
communications stack.

Unlike PR5's outreach (which always calls `send_mail()` and marks 'sent'
regardless of which backend is configured), this module explicitly
detects whether a REAL external mail transport is configured. Locally —
and in any environment where `EMAIL_HOST_USER` is unset — Django's
`EMAIL_BACKEND` defaults to the console backend, which always "succeeds"
by printing to stdout. Treating that as a real delivery would be exactly
the "pretend an email was sent" failure mode Phase 3 explicitly forbids.
So: a real SMTP/production backend sends for real and marks
`sent_real_email`; anything else raises `ManualDeliverySendError` without
changing the invitation's status, and the caller must use
`render_invitation_message()` + `mark_manually_sent()` instead — an
honest, deliberate two-step path.
"""
import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils import timezone

from partner_participation.models import PartnerInvitation

# Backends that do NOT deliver to a real external inbox — never claim a
# real send against any of these.
_NON_REAL_BACKENDS = frozenset({
    'django.core.mail.backends.console.EmailBackend',
    'django.core.mail.backends.locmem.EmailBackend',
    'django.core.mail.backends.dummy.EmailBackend',
    'django.core.mail.backends.filebased.EmailBackend',
})


class InvitationNotAllowedError(Exception):
    pass


class ManualDeliveryRequiredError(Exception):
    """Raised by send_invitation() when no real mail transport is configured — use render + mark_manually_sent instead."""


class InvalidInvitationError(Exception):
    pass


def has_real_mail_transport():
    return getattr(settings, 'EMAIL_BACKEND', '') not in _NON_REAL_BACKENDS


def create_invitation(organisation, invitee_email, *, actor, intended_role='viewer', reason='', expires_in_days=14):
    if actor is None or not getattr(actor, 'is_staff', False):
        raise InvitationNotAllowedError('Creating a partner invitation requires a real EcoIQ staff actor.')
    return PartnerInvitation.objects.create(
        organisation=organisation, invitee_email=invitee_email, intended_role=intended_role, reason=reason,
        expires_at=timezone.now() + datetime.timedelta(days=expires_in_days), created_by=actor, status='draft',
    )


def acceptance_url(invitation, request=None):
    path = reverse('partner_participation:accept_invitation', args=[invitation.token])
    if request is not None:
        return request.build_absolute_uri(path)
    return path


def render_invitation_message(invitation, request=None):
    """
    The exact, real message content — grounded, never fabricated. Used
    both for a real send and for manual delivery (Phase 3's own "expose
    the exact message/link for manual sending").
    """
    link = acceptance_url(invitation, request=request)
    subject = f'EcoIQ Partner Network — invitation to join {invitation.organisation.name}'
    body = (
        f'You have been invited to represent {invitation.organisation.name} on the EcoIQ Partner Network '
        f'as {invitation.get_intended_role_display()}.\n\n'
        f'{invitation.reason or ""}\n\n'
        f'To accept, visit: {link}\n\n'
        f'This invitation expires on {invitation.expires_at:%Y-%m-%d %H:%M %Z}. '
        f'Accepting still requires a real EcoIQ staff member to verify your membership before you gain access — '
        f'this invitation does not grant access on its own.'
    )
    return subject, body, link


def send_invitation(invitation, *, actor):
    """
    Attempts a REAL send. Raises ManualDeliveryRequiredError (leaving the
    invitation's status untouched) if no real mail transport is
    configured — the caller must fall back to render_invitation_message()
    + mark_manually_sent().
    """
    if actor is None or not getattr(actor, 'is_staff', False):
        raise InvitationNotAllowedError('Sending a partner invitation requires a real EcoIQ staff actor.')
    if invitation.status != 'draft':
        raise InvalidInvitationError(f'Invitation {invitation.pk} is {invitation.status!r}, not "draft".')
    if not has_real_mail_transport():
        raise ManualDeliveryRequiredError(
            f'No real mail transport is configured (EMAIL_BACKEND={settings.EMAIL_BACKEND!r}) — '
            f'use render_invitation_message() and mark_manually_sent() instead of pretending this was sent.'
        )

    subject, body, _link = render_invitation_message(invitation)
    send_mail(
        subject=subject, message=body, from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        recipient_list=[invitation.invitee_email], fail_silently=False,
    )
    invitation.status = 'sent'
    invitation.send_status = 'sent_real_email'
    invitation.sent_at = timezone.now()
    invitation.save(update_fields=['status', 'send_status', 'sent_at'])

    from partner_participation.services.timeline import record_event
    record_event(
        invitation.organisation, 'invitation_sent', actor=actor,
        source_object_reference=f'partner_participation.PartnerInvitation:{invitation.pk}',
        notes=f'Real email sent to {invitation.invitee_email}.',
    )
    return invitation


def mark_manually_sent(invitation, *, actor, evidence=''):
    """
    The honest alternative to send_invitation() when no real mail
    transport exists: a real staff member personally delivered the
    invitation (e.g. copied the link into their own email client) and
    confirms it here. Never automatic — always a real, explicit action.
    """
    if actor is None or not getattr(actor, 'is_staff', False):
        raise InvitationNotAllowedError('Confirming manual delivery requires a real EcoIQ staff actor.')
    if invitation.status != 'draft':
        raise InvalidInvitationError(f'Invitation {invitation.pk} is {invitation.status!r}, not "draft".')
    invitation.status = 'sent'
    invitation.send_status = 'manual_delivery_required'
    invitation.sent_at = timezone.now()
    invitation.save(update_fields=['status', 'send_status', 'sent_at'])

    from partner_participation.services.timeline import record_event
    record_event(
        invitation.organisation, 'invitation_sent', actor=actor,
        source_object_reference=f'partner_participation.PartnerInvitation:{invitation.pk}',
        notes=f'Manually delivered to {invitation.invitee_email} by {actor}.' + (f' Evidence: {evidence}' if evidence else ''),
    )
    return invitation


def accept_invitation(token, *, user):
    """
    Token-gated, single-use. Still only ever creates a
    `claim_requested` OrganisationMembership — Phase 1's own "do not
    auto-verify from domain alone" instruction applies even to an
    invited person; a real EcoIQ staff review is still required before
    'verified_member'.
    """
    try:
        invitation = PartnerInvitation.objects.get(token=token)
    except PartnerInvitation.DoesNotExist:
        raise InvalidInvitationError('This invitation link is not valid.')
    if invitation.status == 'accepted':
        raise InvalidInvitationError('This invitation has already been accepted.')
    if invitation.status == 'revoked':
        raise InvalidInvitationError('This invitation has been revoked.')
    if invitation.status != 'sent':
        raise InvalidInvitationError('This invitation has not been sent yet.')
    if invitation.is_expired():
        invitation.status = 'expired'
        invitation.save(update_fields=['status'])
        raise InvalidInvitationError('This invitation has expired.')

    from partner_participation.services.membership import AlreadyMemberError, request_membership
    try:
        membership = request_membership(
            invitation.organisation, user, role=invitation.intended_role,
            justification=f'Accepted invitation {invitation.pk} ({invitation.reason or "no reason given"}).',
        )
    except AlreadyMemberError:
        membership = invitation.organisation.memberships.get(user=user)

    invitation.status = 'accepted'
    invitation.accepted_at = timezone.now()
    invitation.accepted_by = user
    invitation.save(update_fields=['status', 'accepted_at', 'accepted_by'])

    from partner_participation.services.timeline import record_event
    record_event(
        invitation.organisation, 'invitation_accepted', actor=user,
        source_object_reference=f'partner_participation.OrganisationMembership:{membership.pk}',
    )
    from partner_participation.services.notify import notify_invitation_accepted
    notify_invitation_accepted(invitation)
    return membership


def revoke_invitation(invitation, *, actor):
    if actor is None or not getattr(actor, 'is_staff', False):
        raise InvitationNotAllowedError('Revoking an invitation requires a real EcoIQ staff actor.')
    if invitation.status in ('accepted', 'revoked'):
        raise InvalidInvitationError(f'Invitation {invitation.pk} is {invitation.status!r} and cannot be revoked.')
    invitation.status = 'revoked'
    invitation.revoked_at = timezone.now()
    invitation.revoked_by = actor
    invitation.save(update_fields=['status', 'revoked_at', 'revoked_by'])
    return invitation


def sweep_expire_invitations():
    """Time-based, meant to run periodically — mirrors staleness.sweep_expire_stale()'s own precedent."""
    stale = PartnerInvitation.objects.filter(status='sent', expires_at__lt=timezone.now())
    return stale.update(status='expired')
