"""
Translation of Stripe objects into EcoIQ rows.

Called only from stripe_webhooks.py, i.e. only for payloads whose signature
has already been verified. Nothing in this module trusts a browser.

Two things make this messier than it looks, and both are handled explicitly
rather than assumed away:

1. **Stripe moves fields between API versions.** As of the "basil" release,
   `Subscription.current_period_start/end` live on each subscription *item*
   rather than the subscription, and `Invoice.subscription` moved to
   `Invoice.parent.subscription_details.subscription`. The installed SDK
   (stripe 15.4.0, default version 2026-07-29.dahlia) uses the new shapes.
   Every accessor below reads the new shape first and falls back to the old
   one, so an account still pinned to an older version — or a replayed
   historical event — is handled correctly either way.

2. **Status vocabularies differ.** Stripe has eight subscription statuses;
   ecoiq_commerce has five. The mapping is deliberately conservative: any
   Stripe status that does not unambiguously mean "entitled right now" maps
   to a local status outside ('trialing', 'active'), which is what
   Subscription.is_active and services/entitlements.py test. Access is
   withheld on ambiguity rather than granted.
"""
import datetime
import logging
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from ecoiq_commerce.models import (
    BillingCustomer, Invoice, Organisation, OrganisationSubscription,
    PaymentEvent, StripeCheckoutRecord, StripeDispute, Subscription,
)
from ecoiq_commerce.services import stripe_gateway
from ecoiq_commerce.services.billing import require_provider
from ecoiq_commerce.services.events import track_event

logger = logging.getLogger(__name__)
User = get_user_model()


class SyncSkipped(Exception):
    """
    The event was valid and correctly signed, but there is nothing to do —
    an unmapped price, an unknown customer, a subscription EcoIQ did not
    create. The webhook view turns this into a 200 with status='ignored':
    a retry would produce the same outcome, so making Stripe retry would be
    pure noise.
    """


# ── Status mapping ───────────────────────────────────────────────────────────

_STATUS_MAP = {
    'trialing': 'trialing',
    'active': 'active',
    'past_due': 'past_due',
    'unpaid': 'past_due',            # every retry failed, but not yet cancelled
    'incomplete': 'past_due',        # first payment never succeeded — no access
    'incomplete_expired': 'expired',
    'canceled': 'cancelled',         # note the spelling difference (Stripe US, EcoIQ UK)
    'paused': 'expired',             # collection paused — no entitlement either way
}


def map_subscription_status(stripe_status: str) -> str:
    mapped = _STATUS_MAP.get(stripe_status)
    if mapped is None:
        logger.warning('Unknown Stripe subscription status %r — treating as expired '
                       '(no access) until the mapping is updated.', stripe_status)
        return 'expired'
    return mapped


# ── Field accessors (version-tolerant) ───────────────────────────────────────

def _ts(value):
    """Unix timestamp → aware datetime, or None."""
    if not value:
        return None
    return datetime.datetime.fromtimestamp(int(value), tz=datetime.timezone.utc)


def _first_item(subscription: dict) -> dict:
    items = (subscription.get('items') or {}).get('data') or []
    return items[0] if items else {}


def subscription_period(subscription: dict):
    """(current_period_start, current_period_end) across API-version shapes."""
    start = subscription.get('current_period_start')
    end = subscription.get('current_period_end')
    if start is None and end is None:
        item = _first_item(subscription)
        start = item.get('current_period_start')
        end = item.get('current_period_end')
    return _ts(start), _ts(end)


def subscription_price_id(subscription: dict) -> str:
    item = _first_item(subscription)
    price = item.get('price') or {}
    if isinstance(price, dict):
        return price.get('id') or ''
    return str(price or '')


def invoice_payment_intent_id(invoice: dict) -> str:
    """
    The PaymentIntent that settled an invoice, across API-version shapes.

    Pre-"basil" this was a plain `invoice.payment_intent`. Current versions
    move it under `invoice.payments[].payment.payment_intent`. Needed so a
    later chargeback — which carries only a charge and a payment_intent — can
    be traced back to the subscription it paid for.
    """
    pi = invoice.get('payment_intent')
    if isinstance(pi, dict):
        return pi.get('id') or ''
    if pi:
        return pi
    for payment in ((invoice.get('payments') or {}).get('data') or []):
        inner = ((payment or {}).get('payment') or {}).get('payment_intent')
        if isinstance(inner, dict):
            inner = inner.get('id')
        if inner:
            return inner
    return ''


def invoice_subscription_id(invoice: dict) -> str:
    """The subscription an invoice belongs to, across API-version shapes."""
    parent = invoice.get('parent') or {}
    details = parent.get('subscription_details') or {}
    sub = details.get('subscription')
    if not sub:
        sub = invoice.get('subscription')      # pre-basil shape
    if isinstance(sub, dict):
        return sub.get('id') or ''
    return sub or ''


def _amount(value) -> Decimal:
    """Stripe minor units (pence/cents) → a Decimal major-unit amount."""
    if value is None:
        return Decimal('0')
    return (Decimal(int(value)) / Decimal('100')).quantize(Decimal('0.01'))


def invoice_tax_total(invoice: dict) -> Decimal:
    """
    Total tax on an invoice, across API-version shapes.

    Current versions expose `total_taxes` as a *list* of per-rate amounts
    (there is no scalar total), so it has to be summed. Older versions had a
    single `tax` integer. Both yield 0 while Stripe Tax is disabled, which is
    the expected state until Stoke Share Ltd's registrations are confirmed.
    """
    taxes = invoice.get('total_taxes')
    if isinstance(taxes, list):
        return _amount(sum(int((t or {}).get('amount') or 0) for t in taxes))
    return _amount(invoice.get('tax'))


# ── Owner resolution ─────────────────────────────────────────────────────────

def resolve_owner(metadata: dict, customer_id: str = ''):
    """
    Work out which EcoIQ user/organisation a Stripe object belongs to.

    Order matters. Metadata is checked first because EcoIQ set it itself at
    checkout time and it is the most specific signal. The BillingCustomer
    lookup is the fallback that covers subscriptions created directly in the
    Stripe Dashboard, which carry no EcoIQ metadata.

    Returns (user, organisation) with exactly one non-None, or raises
    SyncSkipped when the object cannot be attributed to an EcoIQ account at
    all — provisioning access for a guessed owner would be far worse than
    provisioning none.
    """
    metadata = metadata or {}

    org_id = metadata.get('ecoiq_organisation_id')
    if org_id:
        organisation = Organisation.objects.filter(pk=org_id).first()
        if organisation is not None:
            return None, organisation

    user_id = metadata.get('ecoiq_user_id')
    if user_id:
        user = User.objects.filter(pk=user_id).first()
        if user is not None:
            return user, None

    if customer_id:
        billing_customer = (BillingCustomer.objects
                            .filter(provider='stripe', external_customer_id=customer_id)
                            .select_related('user', 'organisation').first())
        if billing_customer is not None:
            if billing_customer.organisation_id:
                return None, billing_customer.organisation
            return billing_customer.user, None

    raise SyncSkipped(
        f'No EcoIQ user or organisation matches this Stripe object '
        f'(customer={customer_id or "—"}). Nothing provisioned.'
    )


def _billing_customer_for(user, organisation, customer_id: str) -> BillingCustomer:
    """Local BillingCustomer for a Stripe customer id, created if first seen."""
    if customer_id:
        existing = BillingCustomer.objects.filter(
            provider='stripe', external_customer_id=customer_id).first()
        if existing is not None:
            return existing
    existing = BillingCustomer.objects.filter(user=user, organisation=organisation).first()
    if existing is not None:
        if customer_id and existing.external_customer_id != customer_id:
            existing.provider = 'stripe'
            existing.external_customer_id = customer_id
            existing.save(update_fields=['provider', 'external_customer_id'])
        return existing
    return BillingCustomer.objects.create(
        user=user, organisation=organisation,
        provider='stripe', external_customer_id=customer_id)


def _existing_subscription(stripe_subscription_id: str):
    """The local row for a Stripe subscription id, personal or organisational."""
    if not stripe_subscription_id:
        return None
    return (Subscription.objects.filter(stripe_subscription_id=stripe_subscription_id).first()
            or OrganisationSubscription.objects
            .filter(stripe_subscription_id=stripe_subscription_id).first())


# ── Subscription lifecycle ───────────────────────────────────────────────────

def upsert_subscription(subscription: dict):
    """
    Create or update the local subscription row for a Stripe Subscription.

    Idempotent by construction: keyed on stripe_subscription_id, and every
    field is assigned from the payload rather than incremented, so replaying
    the same event any number of times converges on the same row.
    """
    stripe_sub_id = subscription.get('id') or ''
    if not stripe_sub_id:
        raise SyncSkipped('Subscription payload carried no id.')

    customer_id = subscription.get('customer') or ''
    if isinstance(customer_id, dict):
        customer_id = customer_id.get('id') or ''

    status = map_subscription_status(subscription.get('status') or '')
    price_id = subscription_price_id(subscription)
    period_start, period_end = subscription_period(subscription)
    trial_end = _ts(subscription.get('trial_end'))
    canceled_at = _ts(subscription.get('canceled_at'))
    cancel_at_period_end = bool(subscription.get('cancel_at_period_end'))

    fields = {
        'status': status,
        'stripe_price_id': price_id,
        'current_period_start': period_start,
        'current_period_end': period_end,
        'trial_end': trial_end,
        'cancel_at_period_end': cancel_at_period_end,
        'canceled_at': canceled_at,
    }

    existing = _existing_subscription(stripe_sub_id)
    if existing is not None:
        # A price change (upgrade/downgrade in the Portal) must move the local
        # plan too, or entitlements would keep resolving against the old tier.
        plan = stripe_gateway.plan_for_price_id(price_id)
        if plan is not None and plan.pk != existing.plan_id:
            existing.plan = plan
        for field, value in fields.items():
            setattr(existing, field, value)
        existing.save()
        return existing

    plan = stripe_gateway.plan_for_price_id(price_id)
    if plan is None:
        # Deliberately not fatal, and deliberately not provisioned: an
        # unmapped price means EcoIQ does not know which features were bought.
        raise SyncSkipped(
            f'Stripe price {price_id or "—"} is not mapped to any EcoIQ Plan, '
            f'so subscription {stripe_sub_id} grants no entitlements. Map it '
            f'with `manage.py sync_stripe_prices` or by setting '
            f'Plan.stripe_price_id, then replay this event from the Dashboard.'
        )

    user, organisation = resolve_owner(subscription.get('metadata'), customer_id)
    _billing_customer_for(user, organisation, customer_id)

    if organisation is not None:
        created = OrganisationSubscription.objects.create(
            organisation=organisation, plan=plan,
            stripe_subscription_id=stripe_sub_id, **fields)
    else:
        created = Subscription.objects.create(
            user=user, plan=plan,
            stripe_subscription_id=stripe_sub_id, **fields)

    track_event('trial_started' if status == 'trialing' else 'subscription_started',
                user=user, organisation=organisation, plan=plan,
                metadata={'plan_key': plan.key})
    logger.info('Provisioned %s from Stripe subscription %s (status=%s)',
                type(created).__name__, stripe_sub_id, status)
    return created


def cancel_subscription(subscription: dict):
    """customer.subscription.deleted — the subscription is over."""
    stripe_sub_id = subscription.get('id') or ''
    existing = _existing_subscription(stripe_sub_id)
    if existing is None:
        raise SyncSkipped(f'No local subscription matches {stripe_sub_id or "—"}.')

    existing.status = 'cancelled'
    existing.canceled_at = _ts(subscription.get('canceled_at')) or timezone.now()
    existing.cancel_at_period_end = False
    existing.save()

    track_event('subscription_cancelled',
                user=getattr(existing, 'user', None),
                organisation=getattr(existing, 'organisation', None),
                plan=existing.plan, metadata={'plan_key': existing.plan.key})
    logger.info('Cancelled local subscription for Stripe %s', stripe_sub_id)
    return existing


# ── Checkout completion ──────────────────────────────────────────────────────

def complete_checkout_session(session: dict):
    """
    checkout.session.completed — the customer finished Stripe Checkout.

    This is the ONLY place a one-time purchase is marked paid. The browser
    success redirect deliberately grants nothing (see billing_views.success):
    a success URL can be visited, bookmarked or shared without any payment
    having taken place, whereas this payload is signed by Stripe.

    Subscriptions are only stamped onto the record here; the authoritative
    status and period dates arrive with customer.subscription.created/updated,
    which Stripe also sends and which upsert_subscription() handles.
    """
    session_id = session.get('id') or ''
    record = StripeCheckoutRecord.objects.filter(session_id=session_id).first()
    if record is None:
        raise SyncSkipped(
            f'Checkout session {session_id or "—"} was not created by EcoIQ '
            f'(no local record), so there is nothing to provision.')

    metadata = session.get('metadata') or {}
    expected_user = str(record.user_id)
    if metadata.get('ecoiq_user_id') and metadata['ecoiq_user_id'] != expected_user:
        # Both copies of the owner claim were written by EcoIQ at checkout
        # creation. A mismatch means the session is not what we think it is.
        raise SyncSkipped(
            f'Owner mismatch on session {session_id}: metadata says user '
            f'{metadata["ecoiq_user_id"]}, local record says {expected_user}. '
            f'Nothing provisioned.')

    customer_id = session.get('customer') or ''
    if isinstance(customer_id, dict):
        customer_id = customer_id.get('id') or ''

    subscription_id = session.get('subscription') or ''
    if isinstance(subscription_id, dict):
        subscription_id = subscription_id.get('id') or ''

    payment_intent = session.get('payment_intent') or ''
    if isinstance(payment_intent, dict):
        payment_intent = payment_intent.get('id') or ''

    record.status = 'completed'
    record.completed_at = timezone.now()
    record.stripe_customer_id = customer_id or record.stripe_customer_id
    record.stripe_subscription_id = subscription_id or record.stripe_subscription_id
    record.stripe_payment_intent_id = payment_intent or record.stripe_payment_intent_id
    record.amount_total = _amount(session.get('amount_total'))
    record.currency = (session.get('currency') or '').upper()

    # `paid` is Stripe's own assertion that funds were captured (or that the
    # subscription's first invoice is settled). `no_payment_required` covers a
    # 100%-off promotion code and a fully-trialing subscription.
    paid = session.get('payment_status') in ('paid', 'no_payment_required')
    if paid and record.mode == 'payment':
        record.access_granted = True
        track_event('report_purchased', user=record.user, organisation=record.organisation,
                    plan=record.plan,
                    metadata={'amount': str(record.amount_total),
                              'plan_key': record.plan.key if record.plan else ''})
    record.save()

    _billing_customer_for(
        record.user if record.organisation is None else None,
        record.organisation, customer_id)

    logger.info('Completed checkout session %s (mode=%s, paid=%s)',
                session_id, record.mode, paid)
    return record


# ── Invoices ─────────────────────────────────────────────────────────────────

def _upsert_invoice(invoice: dict, *, status: str) -> Invoice:
    # Symmetric to NullBillingProvider's guard: Stripe may only write invoices
    # when Stripe is the configured provider. Without both halves, flipping
    # ECOIQ_BILLING_PROVIDER while webhooks are still arriving would let two
    # systems create invoices for the same money.
    require_provider('stripe')
    invoice_id = invoice.get('id') or ''
    customer_id = invoice.get('customer') or ''
    if isinstance(customer_id, dict):
        customer_id = customer_id.get('id') or ''

    user, organisation = resolve_owner(invoice.get('metadata'), customer_id)
    billing_customer = _billing_customer_for(user, organisation, customer_id)

    stripe_sub_id = invoice_subscription_id(invoice)
    local_sub = _existing_subscription(stripe_sub_id)

    defaults = {
        'billing_customer': billing_customer,
        'description': invoice.get('description') or '',
        'amount_total': _amount(invoice.get('total')),
        'tax_amount': invoice_tax_total(invoice),
        'currency': (invoice.get('currency') or '').upper() or 'USD',
        'status': status,
        'hosted_invoice_url': invoice.get('hosted_invoice_url') or '',
        'external_payment_intent_id': invoice_payment_intent_id(invoice),
        'issued_at': _ts((invoice.get('status_transitions') or {}).get('finalized_at')),
        'paid_at': _ts((invoice.get('status_transitions') or {}).get('paid_at')),
        'due_at': _ts(invoice.get('due_date')),
        'subscription': local_sub if isinstance(local_sub, Subscription) else None,
        'organisation_subscription': (
            local_sub if isinstance(local_sub, OrganisationSubscription) else None),
    }

    row, created = Invoice.objects.update_or_create(
        external_invoice_id=invoice_id, defaults=defaults)
    logger.info('%s local Invoice for Stripe %s (status=%s)',
                'Created' if created else 'Updated', invoice_id, status)
    return row


def record_invoice_paid(invoice: dict, *, event_id: str = ''):
    """
    invoice.paid — a subscription renewal (or a one-time invoice) settled.

    Also re-activates a subscription that had gone past_due, which is what
    recovers a customer whose card failed once and then succeeded on retry.

    `event_id` keys the PaymentEvent row. Using the Stripe event id rather
    than the invoice id keeps the payment history honest: one invoice can
    genuinely fail several times before it succeeds, and each of those is a
    distinct event that should appear separately — while a *replay* of the
    same event still collapses onto the same row.
    """
    row = _upsert_invoice(invoice, status='paid')
    if row.paid_at is None:
        row.paid_at = timezone.now()
        row.save(update_fields=['paid_at'])

    PaymentEvent.objects.get_or_create(
        invoice=row, status='succeeded',
        provider_reference=event_id or invoice.get('id') or '')

    local_sub = row.subscription or row.organisation_subscription
    if local_sub is not None and local_sub.status == 'past_due':
        local_sub.status = 'active'
        local_sub.save(update_fields=['status', 'updated_at'])
        logger.info('Subscription %s recovered from past_due after invoice.paid',
                    local_sub.stripe_subscription_id)
    return row


def record_invoice_payment_failed(invoice: dict, *, event_id: str = ''):
    """
    invoice.payment_failed — leaves the invoice open and moves the
    subscription to past_due, which is outside is_active and therefore
    immediately withholds entitlements without deleting anything.
    """
    row = _upsert_invoice(invoice, status='open')

    failure_reason = ''
    charge = invoice.get('last_finalization_error') or {}
    if isinstance(charge, dict):
        failure_reason = charge.get('message') or ''

    PaymentEvent.objects.get_or_create(
        invoice=row, status='failed',
        provider_reference=event_id or invoice.get('id') or '',
        defaults={'failure_reason': failure_reason[:250]})

    local_sub = row.subscription or row.organisation_subscription
    if local_sub is not None and local_sub.status in ('active', 'trialing'):
        local_sub.status = 'past_due'
        local_sub.save(update_fields=['status', 'updated_at'])
        logger.warning('Subscription %s moved to past_due after invoice.payment_failed',
                       local_sub.stripe_subscription_id)
    return row


# ── Refunds and disputes ─────────────────────────────────────────────────────
# A refund and a chargeback are different events and get different treatment.
#
# A refund is final and voluntary: EcoIQ (or Stripe) gave the money back, so
# access for a one-time purchase goes away and stays away.
#
# A dispute is neither. The cardholder's bank has pulled the funds pending an
# investigation that can run for weeks and can be resolved either way, so the
# right response is to SUSPEND access and record exactly what was suspended —
# then restore precisely that if the dispute is won, and leave it withdrawn if
# it is lost.
#
# Neither event cancels a subscription by itself. If a subscription is actually
# cancelled, Stripe sends customer.subscription.deleted separately and
# cancel_subscription() handles it.

def _payment_intent_of(obj: dict) -> str:
    pi = obj.get('payment_intent')
    if isinstance(pi, dict):
        return pi.get('id') or ''
    return pi or ''


def _checkout_record_for(payment_intent_id: str, charge_id: str = ''):
    if payment_intent_id:
        rec = StripeCheckoutRecord.objects.filter(
            stripe_payment_intent_id=payment_intent_id).first()
        if rec is not None:
            return rec
    return None


def _subscription_for_payment_intent(payment_intent_id: str):
    """Chargeback -> PaymentIntent -> Invoice -> the subscription it paid for."""
    if not payment_intent_id:
        return None
    invoice = Invoice.objects.filter(
        external_payment_intent_id=payment_intent_id).first()
    if invoice is None:
        return None
    return invoice.subscription or invoice.organisation_subscription


def record_charge_refunded(charge: dict, *, event_id: str = ''):
    """
    charge.refunded — money returned to the customer.

    A FULL refund withdraws access to a one-time purchase. A PARTIAL refund
    does not: the customer still paid for something, and silently revoking on
    a partial refund would take away access someone had legitimately bought.
    The partial case is recorded and logged for a human instead of guessed at.
    """
    payment_intent_id = _payment_intent_of(charge)
    captured = int(charge.get('amount_captured') or charge.get('amount') or 0)
    refunded_amount = int(charge.get('amount_refunded') or 0)
    fully_refunded = bool(charge.get('refunded')) or (
        captured > 0 and refunded_amount >= captured)

    record = _checkout_record_for(payment_intent_id, charge.get('id') or '')
    invoice = Invoice.objects.filter(
        external_payment_intent_id=payment_intent_id).first() if payment_intent_id else None

    if record is None and invoice is None:
        raise SyncSkipped(
            f'Refunded charge {charge.get("id") or "—"} matches no EcoIQ '
            f'purchase or invoice. Nothing to withdraw.')

    if invoice is not None:
        PaymentEvent.objects.get_or_create(
            invoice=invoice, status='refunded',
            provider_reference=event_id or charge.get('id') or '',
            defaults={'failure_reason': ''})
        if fully_refunded:
            invoice.status = 'void'
            invoice.save(update_fields=['status'])

    if record is not None and fully_refunded and record.access_granted:
        record.access_granted = False
        record.revocation_reason = 'refund'
        record.save(update_fields=['access_granted', 'revocation_reason'])
        logger.info('Access withdrawn for %s after full refund', record.session_id)
        return f'access withdrawn for {record.session_id} (full refund)'

    if not fully_refunded:
        logger.warning(
            'Partial refund on charge %s (%s of %s minor units). Access left '
            'in place deliberately — review manually if it should be withdrawn.',
            charge.get('id'), refunded_amount, captured)
        return 'partial refund recorded; access deliberately unchanged'

    return 'refund recorded; no access was outstanding to withdraw'


def open_dispute(dispute: dict, *, event_id: str = ''):
    """
    charge.dispute.created — funds withheld pending the bank's investigation.

    Suspends access and stores the pre-suspension subscription status, which is
    what lets close_dispute() restore the exact prior state rather than assume
    'active'. Idempotent: keyed on the dispute id, so a duplicate delivery
    finds the existing row and re-suspends nothing.
    """
    dispute_id = dispute.get('id') or ''
    if not dispute_id:
        raise SyncSkipped('Dispute payload carried no id.')

    payment_intent_id = _payment_intent_of(dispute)
    charge_id = dispute.get('charge') or ''
    if isinstance(charge_id, dict):
        charge_id = charge_id.get('id') or ''

    record = _checkout_record_for(payment_intent_id, charge_id)
    local_sub = _subscription_for_payment_intent(payment_intent_id)

    if record is None and local_sub is None:
        raise SyncSkipped(
            f'Dispute {dispute_id} matches no EcoIQ purchase or subscription. '
            f'Recorded in Stripe only; nothing suspended.')

    row, created = StripeDispute.objects.get_or_create(
        dispute_id=dispute_id,
        defaults={
            'charge_id': charge_id,
            'payment_intent_id': payment_intent_id,
            'status': 'open',
            'reason': (dispute.get('reason') or '')[:80],
            'amount': _amount(dispute.get('amount')),
            'currency': (dispute.get('currency') or '').upper(),
            'checkout_record': record,
            'subscription': local_sub if isinstance(local_sub, Subscription) else None,
            'organisation_subscription': (
                local_sub if isinstance(local_sub, OrganisationSubscription) else None),
        },
    )
    if not created and row.access_suspended:
        return f'dispute {dispute_id} already open; nothing re-suspended'

    if record is not None and record.access_granted:
        record.access_granted = False
        record.revocation_reason = 'dispute'
        record.save(update_fields=['access_granted', 'revocation_reason'])

    if local_sub is not None:
        row.previous_subscription_status = local_sub.status
        if local_sub.status in ('active', 'trialing'):
            local_sub.status = 'past_due'
            row.suspended_to_status = 'past_due'
            local_sub.save(update_fields=['status', 'updated_at'])

    row.access_suspended = True
    row.save()
    logger.warning('Dispute %s opened (%s) — access suspended', dispute_id, row.reason)
    return f'dispute {dispute_id} opened; access suspended'


def close_dispute(dispute: dict, *, event_id: str = ''):
    """
    charge.dispute.closed — the bank decided.

    won  -> restore exactly what this dispute suspended, and only that. A
            subscription goes back to its recorded previous status, so a
            subscription that was independently cancelled or went past_due for
            an unrelated failed payment is not silently reactivated. A purchase
            is restored only if this dispute is what revoked it — never one
            that was refunded.
    lost -> the money is gone. Access stays withdrawn.
    """
    dispute_id = dispute.get('id') or ''
    row = StripeDispute.objects.filter(dispute_id=dispute_id).first()
    if row is None:
        raise SyncSkipped(
            f'Dispute {dispute_id or "—"} was never recorded as opened by '
            f'EcoIQ, so there is nothing to restore.')

    outcome = dispute.get('status') or ''
    won = outcome in ('won', 'warning_closed')

    if row.status in ('won', 'lost'):
        return f'dispute {dispute_id} already closed as {row.status}'

    row.status = 'won' if won else 'lost'
    row.closed_at = timezone.now()

    if won:
        record = row.checkout_record
        if record is not None and record.revocation_reason == 'dispute':
            record.access_granted = True
            record.revocation_reason = ''
            record.save(update_fields=['access_granted', 'revocation_reason'])

        local_sub = row.subscription or row.organisation_subscription
        if (local_sub is not None
                and row.suspended_to_status
                and local_sub.status == row.suspended_to_status):
            # Still exactly where this dispute left it, so nothing else has
            # had an opinion since and it is safe to put back. If the status
            # has moved on — cancelled outright, or past_due from an unrelated
            # failed payment — that newer fact wins and is left alone.
            local_sub.status = row.previous_subscription_status
            local_sub.save(update_fields=['status', 'updated_at'])
        elif local_sub is not None:
            logger.info(
                'Dispute %s won, but subscription status moved to %r since '
                'suspension — leaving it alone rather than reactivating.',
                dispute_id, local_sub.status)
        row.access_suspended = False
        logger.info('Dispute %s won — suspended access restored', dispute_id)
    else:
        logger.warning('Dispute %s lost — access remains withdrawn', dispute_id)

    row.save()
    return f'dispute {dispute_id} closed as {row.status}'
