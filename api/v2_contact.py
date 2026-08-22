"""
api/v2_contact.py — the contact enquiry flow, for the React frontend.

THE SAME SCREENING, NOT A SECOND DOOR
-------------------------------------
`core.views.contact_submit` produced 100% of the 937 admin notifications in the
June–August abuse incident, because it had no captcha, no rate limit, no
honeypot and no email validation while the leads/ forms had all four. That was
fixed by putting `notifications.antispam.evaluate` in front of it.

Adding a JSON endpoint for the same form is an opportunity to reintroduce
exactly that hole — a new door into the same room, with the lock left off. So
this endpoint calls the same `evaluate()`, with the same arguments, in the same
order, and takes the same three branches. The screening runs BEFORE anything is
created: a rejected submission writes no notification, sends no email and makes
no external call.

WHY A REJECTED SUBMISSION IS TOLD IT SUCCEEDED
----------------------------------------------
Identical wording to the accepted path, deliberately. A bot that can tell it
was caught can iterate until it isn't; a person misclassified sees a normal
outcome and their message sits in review rather than vanishing. The one
exception is the rate limit, which returns 429 — that is a condition the sender
can actually act on, and telling someone "received" when they have been
throttled would be a lie with no security value.
"""
from __future__ import annotations

from django.conf import settings
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core import events
from notifications.antispam import Decision, evaluate
from notifications.antispam import timing as _timing
from notifications.antispam.telemetry import log_submission

#: Mirrors the server-rendered form's own limits. Truncation rather than
#: rejection: a message one character over the limit is a real enquiry, and
#: bouncing it teaches the sender nothing.
_LIMITS = {
    'name': 120, 'email': 254, 'subject': 200, 'company': 120, 'message': 4000,
}

MIN_MESSAGE_LENGTH = 20

ACCEPTED_DETAIL = "Message received — we'll reply within one business day."


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@throttle_classes([])
def contact(request):
    """
    GET  /api/v2/contact/  → the anti-abuse context the form needs.
    POST /api/v2/contact/  → submit an enquiry.

    The GET issues a fresh signed render timestamp per request rather than
    embedding one in the page shell. A token baked into the served document
    would be the same age for every visitor who received that copy of it,
    which is precisely the signal it exists to measure.

    Rate limiting is `notifications.antispam`'s own, not DRF's — it is keyed on
    the submission fingerprint and the client address rather than on the API
    scope, and running both would give the same request two unrelated budgets.
    """
    if request.method == 'GET':
        return Response({
            'form_token': _timing.issue(),
            'turnstile_site_key': getattr(settings, 'TURNSTILE_SITE_KEY', ''),
        })

    data = request.data if isinstance(request.data, dict) else {}
    fields = {
        name: str(data.get(name, '') or '').strip()[:limit]
        for name, limit in _LIMITS.items()
    }

    errors = _validate(fields)
    if errors:
        return Response({'errors': errors}, status=400)

    verdict = evaluate(
        request=request,
        form='contact',
        name=fields['name'], email=fields['email'],
        subject=fields['subject'], message=fields['message'],
        honeypot=str(data.get('website', '') or ''),
        form_token=str(data.get('form_token', '') or ''),
        turnstile_token=str(data.get('turnstile_token', '') or ''),
    )

    if verdict.decision is Decision.REJECT:
        # Recorded BEFORE the early return. monitoring.record() drives the
        # rejection-spike and fingerprint-flood alerts, and an endpoint that
        # screens without recording turns those alerts off without failing
        # anything — which is how the first version of this endpoint shipped.
        log_submission(events.CONTACT_SUBMISSION_REJECTED, verdict, request)
        if verdict.http_status == 429:
            return Response(
                {'errors': {'detail': 'Too many submissions from this '
                                      'connection. Please try again later.'}},
                status=429)
        # Same wording as success. A bot must not learn that it was caught.
        return Response({'status': 'received', 'detail': ACCEPTED_DETAIL})

    quarantined = verdict.decision is Decision.REVIEW
    log_submission(
        events.CONTACT_SUBMISSION_REVIEWED if quarantined
        else events.CONTACT_SUBMISSION_ACCEPTED,
        verdict, request)

    _deliver(fields, quarantined=quarantined, verdict=verdict)
    return Response({'status': 'received', 'detail': ACCEPTED_DETAIL})


def _validate(fields: dict) -> dict:
    """
    Field-level messages, so the form can point at what is wrong.

    The server-rendered form returns one combined sentence for all of these.
    A JSON client can do better, and "please fill in all required fields" on a
    form with five of them is an unhelpful thing to say.
    """
    errors = {}
    if not fields['name']:
        errors['name'] = 'Please tell us your name.'
    if not fields['email'] or '@' not in fields['email']:
        errors['email'] = 'A valid email address is required so we can reply.'
    if not fields['subject']:
        errors['subject'] = 'Please choose a topic.'
    if len(fields['message']) < MIN_MESSAGE_LENGTH:
        errors['message'] = (
            f'Please write at least {MIN_MESSAGE_LENGTH} characters so we can '
            'route your enquiry.')
    return errors


def _deliver(fields: dict, *, quarantined: bool, verdict) -> None:
    """
    Notify, and record.

    Both halves are best-effort and independently guarded: email infrastructure
    is not configured in every environment, and losing the notification record
    because SMTP was down would turn a delivery problem into lost correspondence.
    A quarantined submission is recorded but never alerts the commercial team —
    that is the whole point of the review tier.
    """
    body = (
        'New EcoIQ contact enquiry (API)\n'
        f'{"─" * 45}\n'
        f'Name:     {fields["name"]}\n'
        f'Email:    {fields["email"]}\n'
        f'Company:  {fields["company"] or "—"}\n'
        f'Topic:    {fields["subject"]}\n'
        f'{"─" * 45}\n\n'
        f'{fields["message"]}\n'
    )

    if not quarantined:
        from django.core.mail import send_mail
        try:
            send_mail(
                subject=f'[EcoIQ Contact] {fields["subject"]} — {fields["name"]}',
                message=body,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL',
                                   'EcoIQ <noreply@ecoiq.uk>'),
                recipient_list=[getattr(settings, 'LEAD_NOTIFY_EMAIL',
                                        'alizhan@ecoiq.uk')],
                fail_silently=False,
            )
        except Exception:
            pass

    try:
        from notifications.models import create_notification
        create_notification(
            f'Contact enquiry — {fields["subject"]} ({fields["name"]})',
            source_type='contact',
            priority='low' if quarantined else 'normal',
            message=fields['message'][:500],
            contact_name=fields['name'], contact_email=fields['email'],
            metadata={'company': fields['company'],
                      'subject': fields['subject']},
            spam_status='review' if quarantined else 'accepted',
            risk_reasons=verdict.reason_codes,
            source_endpoint='api_v2_contact',
            fingerprint=verdict.fingerprint,
        )
    except Exception:
        pass
