"""
Khalifa Heat — admin lead notifications.

Sends a plain-text notification to the heating-leads inbox when a new lead is
submitted. Designed to NEVER break form submission: if email is unconfigured or
sending fails, it logs a warning and returns quietly.
"""
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

logger = logging.getLogger(__name__)


SUBJECTS = {
    'household':  'New Khalifa Heat Household Application',
    'akimat':     'New Khalifa Heat Akimat Partnership Lead',
    'company':    'New Khalifa Heat Company Sponsorship Lead',
    'assessment': 'New Khalifa Heat Home Assessment',
}


def _recipient():
    return (
        getattr(settings, 'HEATING_LEADS_NOTIFY_EMAIL', '')
        or getattr(settings, 'LEAD_NOTIFY_EMAIL', '')
    )


def _admin_url(request, obj):
    """Absolute admin change URL for the object (best-effort)."""
    try:
        path = reverse(
            f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change',
            args=[obj.pk],
        )
        return request.build_absolute_uri(path) if request else path
    except Exception:
        return ''


def _household_body(obj, admin_url):
    pkg = obj.package.name if getattr(obj, 'package', None) else '—'
    return (
        f'Lead type:    {obj.get_lead_type_display()}\n'
        f'Name:         {obj.full_name}\n'
        f'Phone:        {obj.phone or "—"}\n'
        f'Email:        {obj.email or "—"}\n'
        f'Organisation: {obj.organisation or "—"}\n'
        f'Location:     {obj.location or "—"}\n'
        f'Package:      {pkg}\n'
        f'Install type: {obj.get_install_type_display() or "—"}\n'
        f'Message:      {obj.message or "—"}\n\n'
        f'View in admin: {admin_url or "(admin URL unavailable)"}\n'
    )


def _company_body(obj, admin_url):
    return (
        f'Lead type:    Company sponsorship\n'
        f'Company:      {obj.company_name}\n'
        f'Contact:      {obj.contact_name}\n'
        f'Email:        {obj.email or "—"}\n'
        f'Phone:        {obj.phone or "—"}\n'
        f'Package:      {obj.get_package_display() or "—"}\n'
        f'Budget:       {obj.budget_band or "—"}\n'
        f'Message:      {obj.message or "—"}\n\n'
        f'View in admin: {admin_url or "(admin URL unavailable)"}\n'
    )


def _assessment_body(obj, admin_url):
    return (
        f'Lead type:        Home assessment (calculator)\n'
        f'Area:             {obj.area_m2} m²\n'
        f'Insulation:       {obj.get_insulation_display()}\n'
        f'Rooms:            {obj.rooms}\n'
        f'Electricity:      {obj.get_electricity_display()}\n'
        f'Recommended kW:   {obj.recommended_kw}\n'
        f'Selected package: {obj.selected_package or "—"}\n'
        f'Heat-pump ready:  {"Yes" if obj.hp_ready_recommended else "No"}\n\n'
        f'View in admin: {admin_url or "(admin URL unavailable)"}\n'
    )


_BODY_BUILDERS = {
    'household':  _household_body,
    'akimat':     _household_body,
    'company':    _company_body,
    'assessment': _assessment_body,
}


def notify_new_lead(lead_kind, obj, request=None):
    """
    Send an admin notification for a new heating lead.

    lead_kind: one of 'household' | 'akimat' | 'company' | 'assessment'.
    Returns True if an email was sent, False otherwise. Never raises.
    """
    recipient = _recipient()
    if not recipient:
        logger.warning(
            'Khalifa Heat: no HEATING_LEADS_NOTIFY_EMAIL/LEAD_NOTIFY_EMAIL set; '
            'skipping notification for %s lead #%s.', lead_kind, getattr(obj, 'pk', '?')
        )
        return False

    try:
        subject = SUBJECTS.get(lead_kind, 'New Khalifa Heat Lead')
        body = _BODY_BUILDERS.get(lead_kind, _household_body)(obj, _admin_url(request, obj))
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@ecoiq.uk')
        send_mail(subject, body, from_email, [recipient], fail_silently=False)
        return True
    except Exception as exc:  # noqa: BLE001 — must never break form submission
        logger.warning('Khalifa Heat: lead notification failed (%s): %s', lead_kind, exc)
        return False
