"""
Outbound Stripe calls — the only module in EcoIQ that creates Stripe objects.

Everything here goes *out* to Stripe (Checkout Sessions, Billing Portal
sessions, Customers). Inbound traffic is handled by stripe_webhooks.py, and
the translation of Stripe objects into EcoIQ rows by stripe_sync.py.

Design rules this module holds to:

* Credentials come from settings, which reads them from the environment. The
  secret key is passed per-call as an explicit `api_key=` request option
  rather than assigned to the process-global `stripe.api_key`, so nothing
  leaks between requests, tests, or a future Celery worker.
* A missing secret key is a first-class, reported state — `BillingNotConfigured`
  — not an exception from deep inside the SDK. Views turn it into a clear
  message instead of a 500.
* No amount, currency or price is ever hard-coded here. Recurring prices come
  from the STRIPE_PRICE_* environment variables; one-time prices come from
  Plan.stripe_price_id in the database. Stripe is authoritative for what a
  customer is actually charged.
* automatic_tax is attached ONLY when settings.STRIPE_AUTOMATIC_TAX_ENABLED
  is true. It defaults to false and must stay false until Stoke Share Ltd's
  tax registrations are confirmed in the Stripe Dashboard — see settings.py.
"""
import logging

import stripe
from django.conf import settings
from django.urls import reverse

logger = logging.getLogger(__name__)


class BillingNotConfigured(Exception):
    """Raised when Stripe credentials or a required price id are absent."""


# ── Self-serve subscription catalogue ────────────────────────────────────────
# (tier, interval) → the settings attribute holding that Stripe Price id.
# Kept as a name lookup rather than a value lookup so override_settings() in
# tests, and a Render dashboard change in production, both take effect without
# a process restart of this module.

TIERS = ('starter', 'pro')
INTERVALS = ('monthly', 'yearly')

_PRICE_SETTING_NAMES = {
    ('starter', 'monthly'): 'STRIPE_PRICE_STARTER_MONTHLY',
    ('starter', 'yearly'): 'STRIPE_PRICE_STARTER_YEARLY',
    ('pro', 'monthly'): 'STRIPE_PRICE_PRO_MONTHLY',
    ('pro', 'yearly'): 'STRIPE_PRICE_PRO_YEARLY',
}


def is_configured() -> bool:
    """True when outbound Stripe calls are possible at all."""
    return bool(getattr(settings, 'STRIPE_SECRET_KEY', ''))


def _request_options() -> dict:
    """Per-call credentials + API version. Never mutates stripe module globals."""
    if not is_configured():
        raise BillingNotConfigured(
            'Stripe is not configured. Set STRIPE_SECRET_KEY in the '
            'environment to enable checkout and the customer portal.'
        )
    options = {'api_key': settings.STRIPE_SECRET_KEY}
    version = getattr(settings, 'STRIPE_API_VERSION', '')
    if version:
        options['stripe_version'] = version
    return options


def price_id_for(tier: str, interval: str) -> str:
    """
    Resolve a (tier, interval) pair to its configured Stripe Price id.

    Raises BillingNotConfigured — not KeyError — when the price has not been
    set, because "this plan has no price configured yet" is an operational
    state an operator can fix, and the view should say so plainly.
    """
    setting_name = _PRICE_SETTING_NAMES.get((tier, interval))
    if setting_name is None:
        raise BillingNotConfigured(f'Unknown plan tier/interval: {tier}/{interval}.')
    price_id = getattr(settings, setting_name, '')
    if not price_id:
        raise BillingNotConfigured(
            f'{setting_name} is not set, so the {tier} {interval} plan cannot '
            f'be purchased. Create the price in the Stripe Dashboard and set '
            f'the environment variable.'
        )
    return price_id


def configured_subscription_prices() -> dict:
    """{(tier, interval): price_id} for every price actually configured."""
    out = {}
    for key, setting_name in _PRICE_SETTING_NAMES.items():
        price_id = getattr(settings, setting_name, '')
        if price_id:
            out[key] = price_id
    return out


def plan_for_price_id(price_id: str):
    """
    The local Plan a Stripe Price maps to, or None.

    A None result is not fatal: the subscription is still recorded with its
    Stripe ids, it simply grants no plan-derived entitlements until an
    operator maps the price (see `manage.py sync_stripe_prices`). The webhook
    logs a warning rather than failing, so Stripe is not made to retry an
    event that a retry cannot fix.
    """
    from ecoiq_commerce.models import Plan
    if not price_id:
        return None
    return Plan.objects.filter(stripe_price_id=price_id).select_related('product').first()


# ── Customers ────────────────────────────────────────────────────────────────

def get_or_create_billing_customer(*, user=None, organisation=None):
    """
    Return the local BillingCustomer for this holder, creating the Stripe
    Customer on first use.

    Exactly one of user/organisation, matching BillingCustomer.save()'s own
    invariant. Metadata carries the EcoIQ ids so an operator looking at the
    Stripe Dashboard can always trace a customer back to an account, and so
    webhooks that arrive without a checkout record can still resolve an owner.
    """
    from ecoiq_commerce.models import BillingCustomer

    if bool(user) == bool(organisation):
        raise ValueError('Exactly one of user or organisation is required.')

    customer = BillingCustomer.objects.filter(user=user, organisation=organisation).first()
    if customer and customer.provider == 'stripe' and customer.external_customer_id:
        return customer

    email = ''
    name = ''
    metadata = {}
    if organisation is not None:
        email = organisation.billing_email or ''
        name = organisation.name
        metadata['ecoiq_organisation_id'] = str(organisation.pk)
    else:
        email = getattr(user, 'email', '') or ''
        name = user.get_full_name() or user.get_username()
        metadata['ecoiq_user_id'] = str(user.pk)

    stripe_customer = stripe.Customer.create(
        email=email or None,
        name=name or None,
        metadata=metadata,
        **_request_options(),
    )

    if customer is None:
        customer = BillingCustomer(user=user, organisation=organisation)
    customer.provider = 'stripe'
    customer.external_customer_id = stripe_customer['id']
    customer.save()
    return customer


# ── Checkout ─────────────────────────────────────────────────────────────────

def _absolute(request, viewname: str, query: str = '') -> str:
    return request.build_absolute_uri(reverse(viewname)) + query


def _tax_params() -> dict:
    """
    Stripe Tax parameters, or {} while it is disabled.

    Structured as an additive dict rather than an `if` inside every call site
    so that turning tax on later is a configuration change (one env var) and
    not a code change — the requirement is explicitly that automatic_tax stay
    off until registrations are confirmed, but that the code be ready.
    """
    if not getattr(settings, 'STRIPE_AUTOMATIC_TAX_ENABLED', False):
        return {}
    params = {'automatic_tax': {'enabled': True}}
    if getattr(settings, 'STRIPE_TAX_ID_COLLECTION_ENABLED', False):
        params['tax_id_collection'] = {'enabled': True}
    return params


def _ownership_metadata(*, user, organisation, plan=None, kind='') -> dict:
    """Ids EcoIQ needs to attribute an inbound webhook. No PII beyond ids."""
    metadata = {'ecoiq_user_id': str(user.pk)}
    if organisation is not None:
        metadata['ecoiq_organisation_id'] = str(organisation.pk)
    if plan is not None:
        metadata['ecoiq_plan_id'] = str(plan.pk)
        metadata['ecoiq_plan_key'] = plan.key
    if kind:
        metadata['ecoiq_checkout_kind'] = kind
    return metadata


def _client_reference_id(*, user, organisation) -> str:
    """
    A compact, parseable owner reference echoed back on the session.

    Checked against the session metadata on arrival — two independent copies
    of the same claim, both set by EcoIQ, so a mismatch means something is
    wrong and the event should not provision anything.
    """
    if organisation is not None:
        return f'org:{organisation.pk}:user:{user.pk}'
    return f'user:{user.pk}'


def create_subscription_checkout_session(*, request, user, tier: str, interval: str,
                                          organisation=None):
    """
    Create a Stripe Checkout Session in `subscription` mode and record it.

    The local StripeCheckoutRecord is written in the same call, before the
    caller redirects, so the session is already attributable if the webhook
    beats the browser back to us (which it routinely does).
    """
    from ecoiq_commerce.models import StripeCheckoutRecord

    price_id = price_id_for(tier, interval)
    plan = plan_for_price_id(price_id)
    customer = get_or_create_billing_customer(
        user=user if organisation is None else None, organisation=organisation)

    metadata = _ownership_metadata(user=user, organisation=organisation, plan=plan,
                                   kind=f'subscription:{tier}:{interval}')

    session = stripe.checkout.Session.create(
        mode='subscription',
        customer=customer.external_customer_id,
        client_reference_id=_client_reference_id(user=user, organisation=organisation),
        line_items=[{'price': price_id, 'quantity': 1}],
        metadata=metadata,
        # Copied onto the Subscription itself: customer.subscription.updated /
        # .deleted events carry no checkout session, so without this the only
        # way to attribute a later lifecycle event would be the customer id.
        subscription_data={'metadata': metadata},
        success_url=_absolute(request, 'billing:success', '?session_id={CHECKOUT_SESSION_ID}'),
        cancel_url=_absolute(request, 'billing:cancelled'),
        allow_promotion_codes=True,
        **_tax_params(),
        **_request_options(),
    )

    # update_or_create, not create: session_id is unique, and while Stripe
    # mints a fresh id per session, an IntegrityError here would surface to a
    # paying customer as a 500 on the way *to* checkout. Converging on the
    # same row is the harmless outcome.
    record, _created = StripeCheckoutRecord.objects.update_or_create(
        session_id=session['id'],
        defaults={
            'mode': 'subscription',
            'user': user,
            'organisation': organisation,
            'plan': plan,
            'stripe_price_id': price_id,
            'stripe_customer_id': customer.external_customer_id,
        },
    )
    logger.info('Stripe subscription checkout created: session=%s user=%s org=%s',
                record.session_id, user.pk, organisation.pk if organisation else None)
    return session, record


def create_one_time_checkout_session(*, request, user, plan, organisation=None):
    """
    Create a Stripe Checkout Session in `payment` mode for a one-time
    purchase — a sustainability assessment, a consulting engagement, a paid
    report.

    Priced from `plan.stripe_price_id` rather than an amount passed in by the
    caller: a client-supplied amount is a classic tampering vector, and the
    catalogue is already the configured source of truth for pricing
    everywhere else in this app.
    """
    from ecoiq_commerce.models import StripeCheckoutRecord

    if not plan.stripe_price_id:
        raise BillingNotConfigured(
            f'Plan "{plan.key}" has no stripe_price_id, so it cannot be '
            f'purchased. Create a one-time price in the Stripe Dashboard and '
            f'set it on the plan.'
        )

    customer = get_or_create_billing_customer(
        user=user if organisation is None else None, organisation=organisation)

    metadata = _ownership_metadata(user=user, organisation=organisation, plan=plan,
                                   kind='one_time')

    session = stripe.checkout.Session.create(
        mode='payment',
        customer=customer.external_customer_id,
        client_reference_id=_client_reference_id(user=user, organisation=organisation),
        line_items=[{'price': plan.stripe_price_id, 'quantity': 1}],
        metadata=metadata,
        # Ask Stripe to generate a real invoice for one-time payments too, so
        # the customer's Portal invoice history is complete rather than only
        # covering subscriptions.
        invoice_creation={'enabled': True},
        success_url=_absolute(request, 'billing:success', '?session_id={CHECKOUT_SESSION_ID}'),
        cancel_url=_absolute(request, 'billing:cancelled'),
        **_tax_params(),
        **_request_options(),
    )

    record, _created = StripeCheckoutRecord.objects.update_or_create(
        session_id=session['id'],
        defaults={
            'mode': 'payment',
            'user': user,
            'organisation': organisation,
            'plan': plan,
            'stripe_price_id': plan.stripe_price_id,
            'stripe_customer_id': customer.external_customer_id,
        },
    )
    logger.info('Stripe one-time checkout created: session=%s plan=%s user=%s',
                record.session_id, plan.key, user.pk)
    return session, record


# ── Customer Portal ──────────────────────────────────────────────────────────

def create_billing_portal_session(*, request, user, organisation=None, return_view='billing:manage'):
    """
    A Stripe-hosted Customer Portal session: update payment method, view and
    download invoices, switch or cancel a subscription.

    Everything the portal offers is configured in the Stripe Dashboard, not
    here — which is the point. EcoIQ never renders a card form, so it stays
    out of PCI scope entirely, and cancellations made in the portal come back
    as customer.subscription.updated/deleted webhooks like any other change.
    """
    customer = get_or_create_billing_customer(
        user=user if organisation is None else None, organisation=organisation)

    params = {
        'customer': customer.external_customer_id,
        'return_url': request.build_absolute_uri(reverse(return_view)),
    }
    configuration = getattr(settings, 'STRIPE_BILLING_PORTAL_CONFIGURATION_ID', '')
    if configuration:
        params['configuration'] = configuration

    return stripe.billing_portal.Session.create(**params, **_request_options())
