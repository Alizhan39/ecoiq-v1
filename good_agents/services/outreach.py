"""
good_agents/services/outreach.py — AI may draft; a human must approve
before anything external is sent (PR5 Phase 6-7, 26). Real sending
infrastructure already exists in this repo (Django's configured
EMAIL_BACKEND, used by core/views.py, leads/views.py, heating/emails.py) —
reused here directly rather than building a second one, but gated behind
an explicit human approval step immediately before send, per Phase 26.

`send_outreach` is the ONLY function in this app that can set
`OutreachDraft.status='sent'`, and it refuses to run unless the draft is
already `'approved'` — there is no code path from `'draft'` straight to `'sent'`.
"""
import logging

from django.core.mail import send_mail
from django.utils import timezone

from good_agents.models import OutreachDraft
from good_agents.services import notify
from good_agents.services.timeline import record_event

logger = logging.getLogger(__name__)


class OutreachNotApprovedError(Exception):
    """Raised by send_outreach when the draft has not been through human approval."""


class NoContactChannelError(Exception):
    """Raised by send_outreach when the draft has no usable, real contact channel to send to."""


def create_draft(action_pathway, draft_type, *, subject='', body='', contact=None, associated_evidence=None):
    return OutreachDraft.objects.create(
        action_pathway=action_pathway, draft_type=draft_type, subject=subject, body=body,
        contact=contact, associated_evidence=associated_evidence or [], status='draft',
    )


def mark_ready_for_review(draft):
    draft.status = 'ready_for_review'
    draft.save(update_fields=['status', 'updated_at'])
    record_event(
        draft.action_pathway.opportunity, 'outreach_drafted',
        source_object_reference=f'good_agents.OutreachDraft:{draft.pk}', notes=draft.subject,
    )
    notify.notify_outreach_awaiting_approval(draft)
    return draft


def approve(draft, *, actor):
    """The only way an OutreachDraft can reach 'approved' — always requires a real actor."""
    if actor is None:
        raise OutreachNotApprovedError('Outreach approval requires a real actor — automated approval is never permitted.')
    draft.status = 'approved'
    draft.approved_by = actor
    draft.approved_at = timezone.now()
    draft.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
    record_event(
        draft.action_pathway.opportunity, 'outreach_approved', actor=actor,
        source_object_reference=f'good_agents.OutreachDraft:{draft.pk}', notes=f'Approved by {actor}.',
    )
    return draft


def send_outreach(draft, *, actor):
    """
    Sends a REAL email via this repo's existing, configured EMAIL_BACKEND.
    Refuses unless `draft.status == 'approved'` (set only by `approve()`,
    which itself requires a real actor) and unless a real, email-shaped
    contact channel exists. Never fakes a 'sent' status — if this raises,
    the draft's status is untouched.
    """
    if draft.status != 'approved':
        raise OutreachNotApprovedError(
            f'OutreachDraft {draft.pk} is {draft.status!r}, not "approved" — cannot send. '
            f'Call services.outreach.approve(draft, actor=...) first.'
        )
    if draft.contact is None or not draft.contact.public_contact_channel or '@' not in draft.contact.public_contact_channel:
        raise NoContactChannelError(
            f'OutreachDraft {draft.pk} has no real, email-shaped public contact channel to send to.'
        )

    from django.conf import settings
    send_mail(
        subject=draft.subject, message=draft.body, from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        recipient_list=[draft.contact.public_contact_channel], fail_silently=False,
    )

    draft.status = 'sent'
    draft.sent_at = timezone.now()
    draft.sent_channel = draft.contact.public_contact_channel
    draft.save(update_fields=['status', 'sent_at', 'sent_channel', 'updated_at'])
    record_event(
        draft.action_pathway.opportunity, 'sent', actor=actor,
        source_object_reference=f'good_agents.OutreachDraft:{draft.pk}',
        notes=f'Sent to {draft.sent_channel} via {draft.draft_type}.',
    )
    return draft


def record_reply(draft, *, replied=True, notes=''):
    draft.status = 'replied' if replied else 'no_response'
    draft.save(update_fields=['status', 'updated_at'])
    if replied:
        record_event(
            draft.action_pathway.opportunity, 'reply_received',
            source_object_reference=f'good_agents.OutreachDraft:{draft.pk}', notes=notes,
        )
        notify.notify_outreach_reply_received(draft)
    return draft
