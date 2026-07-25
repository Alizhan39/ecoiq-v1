"""
outreach_readiness/services/dry_run.py — Phase 17, 19, 26: transport audit
and the safe dry run. NEVER sends anything — every function here only
reads configuration or writes a snapshot row.
"""
from django.conf import settings
from django.utils import timezone

from outreach_readiness.models import OutreachDryRun
from outreach_readiness.services.route import active_route
from partner_participation.services.invitation import has_real_mail_transport


class DryRunNotAllowedError(Exception):
    pass


def transport_audit():
    """
    Phase 19 — reports what is ACTUALLY available, never what's merely
    configured-but-unverified. Reuses PR9's has_real_mail_transport()
    (same EMAIL_BACKEND, same repo) rather than a second transport check.
    """
    real_email = has_real_mail_transport()
    return {
        'real_email_transport': real_email,
        'email_backend': getattr(settings, 'EMAIL_BACKEND', ''),
        'sender_identity_configured': bool(getattr(settings, 'DEFAULT_FROM_EMAIL', '')),
        'message_id_support': real_email,
        'limitations': (
            [] if real_email else
            ['EMAIL_BACKEND is a non-real backend (console/locmem/dummy/filebased) — no real message would leave this environment.']
        ),
        'available_modes': (
            ['real_email_transport', 'manual_email', 'public_contact_form_manual', 'other_verified_public_channel']
            if real_email else ['manual_email', 'public_contact_form_manual', 'other_verified_public_channel', 'no_transport']
        ),
    }


def run_dry_run(message_version, *, actor):
    """
    Snapshots exactly what WOULD be sent — recipient route, subject,
    body, sender identity, transport mode — and validates it, but calls
    no send function of any kind (`django.core.mail.send_mail` is never
    imported here). `validation_result` is 'fail' if any required field
    is missing or the risk review has not fully passed; a dry run can
    exist and still legitimately fail, that IS the point of running it.
    """
    if actor is None:
        raise DryRunNotAllowedError('A dry run requires a real actor.')

    route = active_route(message_version.assessment)
    audit = transport_audit()
    details = []

    if route is None:
        details.append('No active verified contact route recorded.')
    if not message_version.subject:
        details.append('Message has no subject.')
    if not message_version.body_text:
        details.append('Message has no body text.')
    if not message_version.reply_to:
        details.append('No reply-to address recorded.')
    risk_review = getattr(message_version, 'risk_review', None)
    if risk_review is None or not risk_review.all_passed:
        details.append('Risk review has not fully passed.')

    transport_mode = 'real_email_transport' if audit['real_email_transport'] else 'no_transport'
    if route is not None and route.route_type in ('public_contact_form', 'in_person', 'referral_required'):
        transport_mode = 'public_contact_form_manual'
    elif route is not None and not audit['real_email_transport']:
        transport_mode = 'manual_email' if route.route_type == 'email' else 'other_verified_public_channel'

    validation_result = 'fail' if details else 'pass'

    return OutreachDryRun.objects.create(
        message_version=message_version,
        recipient_route_snapshot=(
            f'{route.get_route_type_display()} — {route.contact_page_or_institutional_email}' if route else 'No route.'
        ),
        subject_snapshot=message_version.subject, body_snapshot=message_version.body_text,
        sender_identity_snapshot=f'{message_version.sender_name}, {message_version.sender_role}, {message_version.sender_organisation}',
        reply_to_snapshot=message_version.reply_to,
        links_snapshot=[route.source_reference] if route else [],
        transport_mode=transport_mode, validation_result=validation_result, validation_details=details,
        run_by=actor, run_at=timezone.now(),
    )
