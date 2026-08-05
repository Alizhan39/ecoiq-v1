"""
Inbound Stripe webhooks: signature verification, idempotency, dispatch.

This module is the trust boundary. `/billing/webhook/` is a public,
unauthenticated, CSRF-exempt endpoint — anyone on the internet can POST to
it. The ONLY thing that makes a request trustworthy is a valid
`Stripe-Signature` header over the exact bytes received, checked against
STRIPE_WEBHOOK_SECRET. Nothing downstream of verify_event() re-checks that,
so nothing may bypass it.

Three properties this module is responsible for:

**Raw body.** Verification runs against `request.body` — the unmodified
bytes. Re-serialising parsed JSON changes whitespace and key order and breaks
the HMAC, so the view must never parse before verifying.

**Idempotency.** Stripe delivers at least once, retries every non-2xx for up
to three days, and can deliver the same event twice concurrently. Every event
id is recorded in StripeEvent under a row lock taken before any work happens,
so a duplicate finds status='processed' and returns without provisioning a
second time.

**Correct status codes.** 400 for anything unverifiable (Stripe will not
retry, and should not — a bad signature is not a transient fault). 200 for
verified events, including ones already processed and ones deliberately
ignored. 500 only for genuine internal failures, where a Stripe retry has a
real chance of succeeding.
"""
import json
import logging

import stripe
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ecoiq_commerce.models import StripeEvent
from ecoiq_commerce.services import stripe_sync
from ecoiq_commerce.services.stripe_sync import SyncSkipped

logger = logging.getLogger(__name__)


class WebhookVerificationError(Exception):
    """Signature missing, malformed, or not matching the signing secret."""


# Every event type this endpoint acts on. Anything else that reaches the
# endpoint is recorded and acknowledged, never treated as an error — Stripe
# endpoints commonly receive types beyond those explicitly subscribed to.
HANDLED_EVENT_TYPES = (
    'checkout.session.completed',
    'invoice.paid',
    'invoice.payment_failed',
    'customer.subscription.created',
    'customer.subscription.updated',
    'customer.subscription.deleted',
)


def verify_event(payload: bytes, signature_header: str) -> dict:
    """
    Verify a webhook and return the event as a plain dict.

    `payload` must be the raw request body. Raises WebhookVerificationError
    for every rejection reason so the view has a single thing to catch, and
    so the reason is logged without echoing the attacker-supplied header
    back into a response.

    The return value is deliberately a plain dict rather than the SDK's
    `stripe.Event`. StripeObject is not a dict subclass and has no `.get()`,
    so every optional-field read against it would have to be a try/except —
    and webhook payloads are full of optional fields that legitimately vary
    by API version. Re-parsing the same bytes that just passed the HMAC check
    costs one json.loads and gives the whole sync layer ordinary dict
    semantics. It weakens nothing: `construct_event` has already proved these
    exact bytes came from Stripe.
    """
    secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
    if not secret:
        # Refusing is the only safe option: without a secret, every payload
        # would have to be either trusted blindly or rejected. Trusting
        # blindly would let anyone POST a forged `invoice.paid` and grant
        # themselves a subscription.
        raise WebhookVerificationError(
            'STRIPE_WEBHOOK_SECRET is not configured — refusing to process '
            'unverifiable webhook traffic.')

    if not signature_header:
        raise WebhookVerificationError('Missing Stripe-Signature header.')

    try:
        stripe.Webhook.construct_event(payload, signature_header, secret)
    except ValueError as exc:                                # unparseable body
        raise WebhookVerificationError(f'Malformed webhook payload: {exc}') from exc
    except stripe.SignatureVerificationError as exc:         # forged / stale / wrong secret
        raise WebhookVerificationError(f'Signature verification failed: {exc}') from exc
    except (AttributeError, KeyError, TypeError) as exc:
        # construct_event inspects `event.object` *after* verifying the
        # signature, to tell v1 events from v2. StripeObject is not a dict and
        # raises AttributeError rather than returning None for a missing key,
        # so a signed payload that is not shaped like an Event crashes there.
        # Without this clause that surfaced as a 500 — which makes Stripe
        # retry a request no retry can fix, and leaks a traceback under DEBUG.
        raise WebhookVerificationError(
            f'Verified payload is not a well-formed Stripe Event: '
            f'{type(exc).__name__}: {exc}') from exc

    event = json.loads(payload)
    if not isinstance(event, dict) or not event.get('id') or not event.get('type'):
        raise WebhookVerificationError('Verified payload is not a Stripe Event.')
    return event


def _summarise(event) -> dict:
    """
    A small allow-listed set of identifiers for the audit trail.

    The full payload is intentionally NOT stored: it can contain customer
    names, email addresses and billing addresses, and EcoIQ has no need to
    keep a second copy of any of that. The Stripe Dashboard remains the
    system of record, searchable by the event id kept here.
    """
    obj = (event.get('data') or {}).get('object') or {}
    summary = {}
    for key in ('id', 'object', 'status', 'payment_status', 'mode', 'currency'):
        value = obj.get(key)
        if isinstance(value, (str, int, bool)):
            summary[key] = value
    customer = obj.get('customer')
    if isinstance(customer, str):
        summary['customer'] = customer
    return summary


def _dispatch(event) -> str:
    """Route a verified event to its handler. Returns a short outcome note."""
    event_type = event['type']
    obj = event['data']['object']
    event_id = event['id']

    if event_type == 'checkout.session.completed':
        record = stripe_sync.complete_checkout_session(obj)
        return f'checkout {record.session_id} completed (access_granted={record.access_granted})'

    if event_type == 'invoice.paid':
        row = stripe_sync.record_invoice_paid(obj, event_id=event_id)
        return f'invoice {row.external_invoice_id} marked paid'

    if event_type == 'invoice.payment_failed':
        row = stripe_sync.record_invoice_payment_failed(obj, event_id=event_id)
        return f'invoice {row.external_invoice_id} payment failed'

    if event_type in ('customer.subscription.created', 'customer.subscription.updated'):
        sub = stripe_sync.upsert_subscription(obj)
        return f'subscription synced (local status={sub.status})'

    if event_type == 'customer.subscription.deleted':
        sub = stripe_sync.cancel_subscription(obj)
        return f'subscription cancelled (local id={sub.pk})'

    raise SyncSkipped(f'No handler for event type {event_type}.')


def process_event(event) -> tuple:
    """
    Record and handle one verified event exactly once.

    Returns (status, note) where status is a StripeEvent status value. The
    caller maps every one of these to a 2xx: the event was genuinely from
    Stripe, so acknowledging it is correct even when EcoIQ chose not to act.

    The row lock matters. Two concurrent deliveries of the same event would
    otherwise both read "not processed" and both provision. Selecting the
    ledger row FOR UPDATE inside the transaction serialises them, so the
    second sees status='processed' and does nothing.
    """
    event_id = event['id']
    event_type = event['type']

    with transaction.atomic():
        ledger, created = StripeEvent.objects.get_or_create(
            stripe_event_id=event_id,
            defaults={
                'event_type': event_type,
                'api_version': event.get('api_version') or '',
                'livemode': bool(event.get('livemode')),
                'payload_summary': _summarise(event),
            },
        )
        if not created:
            # Lock and re-read: another worker may be mid-flight right now.
            ledger = StripeEvent.objects.select_for_update().get(pk=ledger.pk)
            if ledger.status in ('processed', 'ignored'):
                logger.info('Stripe event %s (%s) already handled — acknowledging '
                            'without reprocessing.', event_id, event_type)
                return ledger.status, 'duplicate delivery — already handled'
        else:
            ledger = StripeEvent.objects.select_for_update().get(pk=ledger.pk)

        if event_type not in HANDLED_EVENT_TYPES:
            ledger.status = 'ignored'
            ledger.error = f'Event type {event_type} is not handled by EcoIQ.'
            ledger.processed_at = timezone.now()
            ledger.save()
            return 'ignored', ledger.error

        try:
            # A savepoint, so that a handler failing undoes only its own
            # partial writes. The ledger row itself must survive to record
            # the failure — if the whole transaction rolled back there would
            # be no trace that the event was ever attempted.
            with transaction.atomic():
                note = _dispatch(event)
        except SyncSkipped as exc:
            # Verified, understood, and deliberately not acted on. A retry
            # would reach the same conclusion, so acknowledge it.
            ledger.status = 'ignored'
            ledger.error = str(exc)[:2000]
            ledger.processed_at = timezone.now()
            ledger.save()
            logger.warning('Stripe event %s (%s) skipped: %s', event_id, event_type, exc)
            return 'ignored', str(exc)
        except Exception as exc:                        # noqa: BLE001 — see below
            # A genuine internal fault (database, bug, Stripe API outage
            # during a follow-up call). Recorded as 'failed', which is NOT
            # one of the statuses process_event() short-circuits on, so
            # Stripe's retry will legitimately re-run the handler. The
            # caller returns 500 to ask for that retry.
            ledger.status = 'failed'
            ledger.error = f'{type(exc).__name__}: {exc}'[:2000]
            ledger.processed_at = None
            ledger.save()
            logger.exception('Stripe event %s (%s) failed — Stripe will retry.',
                             event_id, event_type)
            return 'failed', str(exc)

        ledger.status = 'processed'
        ledger.error = ''
        ledger.processed_at = timezone.now()
        ledger.save()
        logger.info('Stripe event %s (%s) processed: %s', event_id, event_type, note)
        return 'processed', note
