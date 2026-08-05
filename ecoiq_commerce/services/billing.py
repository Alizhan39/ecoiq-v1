"""
Provider-neutral billing service interface (PART 11 of the spec this was
built against). Inspection confirmed no payment gateway is integrated
anywhere in this repository (only unrelated references to the word "Stripe"
in docstrings/tests of other apps) — so this is a from-scratch, provider-
agnostic layer, built BEFORE any real gateway is wired in, exactly as
instructed.

BillingProvider is the seam: every call site (subscription creation,
cancellation, invoice issuance) goes through get_billing_provider(), never
directly through a vendor SDK. Swapping in Stripe later means writing one
new class here and flipping BILLING_PROVIDER in settings — nothing in
views/entitlements/tests needs to change.

NullBillingProvider is the only implementation today. It does real
bookkeeping (creates Invoice/BillingCustomer rows, moves Subscription
status) but never talks to a payment network and never collects card data —
appropriate for manual/invoiced billing, free tiers, and comp accounts while
a real gateway integration is pending legal/commercial sign-off.
"""
import datetime
from decimal import Decimal

from django.utils import timezone

from ecoiq_commerce.models import (
    BillingCustomer, Invoice, InvoiceLineItem, OrganisationSubscription, Subscription,
)


class BillingProvider:
    """Abstract interface — see NullBillingProvider for the only current implementation."""

    def get_or_create_customer(self, *, user=None, organisation=None) -> BillingCustomer:
        raise NotImplementedError

    def start_subscription(self, *, plan, user=None, organisation=None, trial_days=0):
        raise NotImplementedError

    def cancel_subscription(self, subscription, *, at_period_end=True):
        raise NotImplementedError

    def issue_invoice(self, *, billing_customer, line_items, currency='USD'):
        raise NotImplementedError


class NullBillingProvider(BillingProvider):
    """
    No external gateway. Subscriptions activate immediately (or enter
    trialing) on record; invoices are created in 'open' status for manual
    collection / offline payment tracking. Never stores card data — there is
    no field anywhere in this app for one.
    """

    def get_or_create_customer(self, *, user=None, organisation=None) -> BillingCustomer:
        if bool(user) == bool(organisation):
            raise ValueError('Exactly one of user or organisation is required.')
        existing = BillingCustomer.objects.filter(user=user, organisation=organisation).first()
        if existing:
            return existing
        return BillingCustomer.objects.create(user=user, organisation=organisation, provider='none')

    def start_subscription(self, *, plan, user=None, organisation=None, trial_days=0):
        if bool(user) == bool(organisation):
            raise ValueError('Exactly one of user or organisation is required.')
        now = timezone.now()
        status = 'trialing' if trial_days else 'active'
        trial_end = now + datetime.timedelta(days=trial_days) if trial_days else None
        period_end = trial_end or self._period_end(now, plan.billing_period)

        if organisation is not None:
            return OrganisationSubscription.objects.create(
                organisation=organisation, plan=plan, status=status,
                current_period_start=now, current_period_end=period_end, trial_end=trial_end,
            )
        return Subscription.objects.create(
            user=user, plan=plan, status=status,
            current_period_start=now, current_period_end=period_end, trial_end=trial_end,
        )

    def cancel_subscription(self, subscription, *, at_period_end=True):
        if at_period_end:
            subscription.cancel_at_period_end = True
        else:
            subscription.status = 'cancelled'
            subscription.canceled_at = timezone.now()
        subscription.save()
        return subscription

    def issue_invoice(self, *, billing_customer, line_items, currency='USD'):
        """line_items: list of {description, quantity, unit_price}."""
        total = sum(Decimal(str(li['unit_price'])) * li.get('quantity', 1) for li in line_items)
        invoice = Invoice.objects.create(
            billing_customer=billing_customer, amount_total=total, currency=currency,
            status='open', issued_at=timezone.now(),
        )
        for li in line_items:
            InvoiceLineItem.objects.create(
                invoice=invoice, description=li['description'], quantity=li.get('quantity', 1),
                unit_price=li['unit_price'], amount=Decimal(str(li['unit_price'])) * li.get('quantity', 1),
            )
        return invoice

    @staticmethod
    def _period_end(start, billing_period):
        if billing_period == 'annual':
            return start.replace(year=start.year + 1)
        if billing_period == 'monthly':
            month = start.month % 12 + 1
            year = start.year + (1 if start.month == 12 else 0)
            try:
                return start.replace(year=year, month=month)
            except ValueError:
                return start.replace(year=year, month=month, day=28)
        return None  # one_time / usage / custom — no recurring period


class StripeBillingProvider(BillingProvider):
    """
    The Stripe implementation of the seam described in this module's header.

    Deliberately thin, and deliberately not a mirror of NullBillingProvider.
    Under Stripe, EcoIQ is not the system that decides when a subscription
    starts, what it costs, or when an invoice is paid — Stripe is. So the two
    write methods here do NOT create local rows and return them; they hand
    off to Stripe and let the resulting webhooks create the rows, which is
    the only path that cannot be spoofed by a browser.

    Anything that needs a Checkout or Portal session should call
    services/stripe_gateway.py directly: those need the HttpRequest (for
    absolute success/cancel URLs) that this provider-neutral interface has no
    place carrying.
    """

    def get_or_create_customer(self, *, user=None, organisation=None):
        from ecoiq_commerce.services import stripe_gateway
        return stripe_gateway.get_or_create_billing_customer(
            user=user, organisation=organisation)

    def start_subscription(self, *, plan, user=None, organisation=None, trial_days=0):
        raise NotImplementedError(
            'Stripe subscriptions start from a Checkout Session, not from a '
            'server-side call: the customer must enter payment details on '
            'Stripe-hosted Checkout first. Use '
            'stripe_gateway.create_subscription_checkout_session(), and let '
            'the customer.subscription.created webhook create the local row.'
        )

    def cancel_subscription(self, subscription, *, at_period_end=True):
        raise NotImplementedError(
            'Cancel through the Stripe Customer Portal (billing:portal) or '
            'the Stripe Dashboard. The customer.subscription.updated / '
            '.deleted webhook then updates the local row. Cancelling only '
            'locally would leave Stripe still billing the customer.'
        )

    def issue_invoice(self, *, billing_customer, line_items, currency='USD'):
        raise NotImplementedError(
            'Stripe issues invoices for subscriptions and for Checkout '
            'sessions created with invoice_creation enabled. Local Invoice '
            'rows are written by the invoice.paid / invoice.payment_failed '
            'webhooks — see services/stripe_sync.py.'
        )


def get_billing_provider() -> BillingProvider:
    from django.conf import settings
    provider_key = getattr(settings, 'ECOIQ_BILLING_PROVIDER', 'none')
    if provider_key == 'none':
        return NullBillingProvider()
    if provider_key == 'stripe':
        return StripeBillingProvider()
    raise NotImplementedError(
        f'Billing provider "{provider_key}" is not implemented. '
        'Available: "none" (NullBillingProvider), "stripe" (StripeBillingProvider).'
    )
