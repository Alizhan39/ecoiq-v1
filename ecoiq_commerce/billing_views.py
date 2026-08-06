"""
ecoiq_commerce/billing_views.py — the /billing/ surface.

Mounted from ecoiq/urls.py under the `billing` namespace. Split out from
views.py (which serves /products/) because the trust models are completely
different: every view here either requires an authenticated owner, or is the
unauthenticated webhook whose only credential is a Stripe signature.

Permission conventions follow the rest of the platform (see views.py's
header): @login_required for personal pages, and organisation access checked
through OrganisationMembership with a 404 rather than a 403, so probing an
organisation id never reveals whether it exists.

The one rule worth stating loudly, because it is the difference between a
billing integration and a free-money machine:

    NO VIEW IN THIS FILE GRANTS PAID ACCESS.

`success` is a page a customer's browser lands on. It can be visited
directly, bookmarked, shared, or forged, with or without a payment having
happened. Provisioning happens exclusively in the webhook handler, against a
Stripe-signed payload. `success` only *reports* what the webhook has already
recorded — and says plainly when confirmation has not arrived yet.
"""
import logging

import stripe
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import (
    Http404, HttpResponse, HttpResponseBadRequest, HttpResponseRedirect, JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from ecoiq_commerce.models import (
    Invoice, Organisation, OrganisationMembership, OrganisationSubscription,
    Plan, StripeCheckoutRecord, Subscription,
)
from ecoiq_commerce.services import stripe_gateway
from ecoiq_commerce.services.stripe_gateway import BillingNotConfigured
from ecoiq_commerce.services.stripe_webhooks import (
    WebhookVerificationError, process_event, verify_event,
)

logger = logging.getLogger(__name__)

# Roles permitted to spend an organisation's money or change its subscription.
# A plain 'member' can use what the organisation bought but cannot buy more.
BILLING_ROLES = ('owner', 'admin', 'billing')


class SeeOther(HttpResponseRedirect):
    """
    303 rather than Django's default 302.

    Every redirect to Stripe in this file follows a POST. A 302 permits a
    client to repeat the POST against the new URL; 303 mandates a GET, which
    is what a Stripe-hosted page expects.
    """
    status_code = 303


def _require_organisation(request, organisation_id):
    """
    Resolve an organisation the caller may transact for, or 404.

    404 rather than 403 on a role failure is deliberate and matches the
    existing convention in views.py: a 403 would confirm that the
    organisation exists and that the caller is merely not senior enough,
    which is more than an outsider needs to know.

    Returns None when no organisation was requested — a personal purchase.
    """
    if not organisation_id:
        return None
    organisation = get_object_or_404(Organisation, pk=organisation_id)
    if not OrganisationMembership.objects.filter(
            organisation=organisation, user=request.user, role__in=BILLING_ROLES).exists():
        logger.warning('User %s attempted a billing action for organisation %s '
                       'without a billing role.', request.user.pk, organisation.pk)
        raise Http404('No such organisation for this account.')
    return organisation


def _billing_organisations(user):
    """Organisations this user may manage billing for."""
    return Organisation.objects.filter(
        memberships__user=user, memberships__role__in=BILLING_ROLES).distinct()


# ── Plans ────────────────────────────────────────────────────────────────────

@require_GET
def plans(request):
    """
    GET /billing/plans/ — self-serve subscription tiers and one-time purchases.

    Public. Deliberately separate from /pricing/, which is an enterprise and
    government engagement page that routes every CTA to a sales enquiry and
    collects no payment; this page is the self-serve counterpart.

    Only tiers whose Stripe Price id is actually configured are offered, so
    the page can never show a buy button that would 500 on click.
    """
    configured = stripe_gateway.configured_subscription_prices()

    tiers = []
    for tier in stripe_gateway.TIERS:
        intervals = {}
        for interval in stripe_gateway.INTERVALS:
            price_id = configured.get((tier, interval))
            if not price_id:
                continue
            intervals[interval] = {
                'price_id': price_id,
                'plan': stripe_gateway.plan_for_price_id(price_id),
            }
        if intervals:
            tiers.append({'key': tier, 'label': tier.title(), 'intervals': intervals})

    one_time_plans = (Plan.objects
                      .filter(billing_period='one_time', is_public=True)
                      .exclude(stripe_price_id='')
                      .select_related('product')
                      .order_by('sort_order', 'name'))

    return render(request, 'ecoiq_commerce/billing_plans.html', {
        'tiers': tiers,
        'one_time_plans': one_time_plans,
        'billing_configured': stripe_gateway.is_configured(),
        'organisations': (_billing_organisations(request.user)
                          if request.user.is_authenticated else []),
        # Publishable key only — safe to render, and used by nothing but a
        # future client-side Stripe.js enhancement. The secret key is never
        # placed in a template context anywhere in this codebase.
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    })


# ── Checkout ─────────────────────────────────────────────────────────────────

def _redirect_to_checkout(session):
    """Send the browser to Stripe-hosted Checkout (see SeeOther)."""
    return SeeOther(session['url'])


@login_required
@require_POST
def checkout_subscription(request):
    """
    POST /billing/checkout/subscription/ — start a monthly or annual
    subscription for the caller, or for an organisation they may bill for.

    The price is resolved server-side from (tier, interval); no amount, price
    id or plan id is ever accepted from the request body. A client that could
    name its own price could name a price of zero.
    """
    tier = (request.POST.get('tier') or '').strip().lower()
    interval = (request.POST.get('interval') or '').strip().lower()

    if tier not in stripe_gateway.TIERS or interval not in stripe_gateway.INTERVALS:
        return HttpResponseBadRequest('Unknown plan tier or billing interval.')

    organisation = _require_organisation(request, request.POST.get('organisation_id'))

    try:
        session, _record = stripe_gateway.create_subscription_checkout_session(
            request=request, user=request.user, tier=tier, interval=interval,
            organisation=organisation)
    except BillingNotConfigured as exc:
        messages.error(request, str(exc))
        return redirect('billing:plans')
    except stripe.StripeError as exc:
        # Never surface exc directly: Stripe error messages can include
        # request ids and account details that do not belong in a page.
        logger.exception('Stripe rejected a subscription checkout for user %s', request.user.pk)
        messages.error(request, 'Stripe could not start this checkout. '
                                'Please try again, or contact support if it persists.')
        return redirect('billing:plans')

    return _redirect_to_checkout(session)


@login_required
@require_POST
def checkout_one_time(request, plan_key):
    """
    POST /billing/checkout/one-time/<plan_key>/ — pay for a one-off
    sustainability assessment or consulting engagement.

    `plan_key` selects a catalogue row; the amount comes from the Stripe
    price that row points at. Restricted to public one-time plans so an
    internal or draft catalogue entry cannot be bought by guessing its key.
    """
    plan = get_object_or_404(Plan, key=plan_key, billing_period='one_time', is_public=True)
    organisation = _require_organisation(request, request.POST.get('organisation_id'))

    try:
        session, _record = stripe_gateway.create_one_time_checkout_session(
            request=request, user=request.user, plan=plan, organisation=organisation)
    except BillingNotConfigured as exc:
        messages.error(request, str(exc))
        return redirect('billing:plans')
    except stripe.StripeError:
        logger.exception('Stripe rejected a one-time checkout for user %s', request.user.pk)
        messages.error(request, 'Stripe could not start this checkout. '
                                'Please try again, or contact support if it persists.')
        return redirect('billing:plans')

    return _redirect_to_checkout(session)


# ── Post-checkout landings ───────────────────────────────────────────────────

@login_required
@require_GET
def success(request):
    """
    GET /billing/success/?session_id=cs_… — the Stripe success redirect.

    Grants nothing. Reads the local StripeCheckoutRecord — scoped to
    request.user, so one customer cannot inspect another's session — and
    reports whether the webhook has confirmed the payment yet.

    "Not confirmed yet" is a normal, expected state for a second or two, and
    the template says so rather than implying failure.
    """
    session_id = (request.GET.get('session_id') or '').strip()
    record = None
    if session_id:
        record = StripeCheckoutRecord.objects.filter(
            session_id=session_id, user=request.user).select_related('plan').first()

    return render(request, 'ecoiq_commerce/billing_success.html', {
        'record': record,
        'session_id': session_id,
        # True only when a signature-verified webhook said so.
        'confirmed': bool(record and (record.access_granted
                                      or record.stripe_subscription_id)),
    })


@login_required
@require_GET
def cancelled(request):
    """GET /billing/cancelled/ — the customer backed out of Checkout."""
    return render(request, 'ecoiq_commerce/billing_cancelled.html', {})


# ── Billing management ───────────────────────────────────────────────────────

@login_required
@require_GET
def manage(request):
    """
    GET /billing/manage/ — the customer's billing home.

    Shows their own subscriptions and those of organisations they hold a
    billing role in, recent invoices, and the entry point to the Stripe
    Customer Portal. Every queryset is scoped to the caller.
    """
    organisations = list(_billing_organisations(request.user))

    personal_subs = (Subscription.objects
                     .filter(user=request.user)
                     .select_related('plan', 'plan__product')
                     .order_by('-started_at'))
    org_subs = (OrganisationSubscription.objects
                .filter(organisation__in=organisations)
                .select_related('plan', 'plan__product', 'organisation')
                .order_by('-started_at'))

    invoices = (Invoice.objects
                .filter(billing_customer__user=request.user)
                .order_by('-created_at')[:20])
    org_invoices = (Invoice.objects
                    .filter(billing_customer__organisation__in=organisations)
                    .select_related('billing_customer__organisation')
                    .order_by('-created_at')[:20])

    purchases = (StripeCheckoutRecord.objects
                 .filter(user=request.user, mode='payment')
                 .select_related('plan')
                 .order_by('-created_at')[:20])

    return render(request, 'ecoiq_commerce/billing_manage.html', {
        'personal_subs': personal_subs,
        'org_subs': org_subs,
        'invoices': invoices,
        'org_invoices': org_invoices,
        'purchases': purchases,
        'organisations': organisations,
        'billing_configured': stripe_gateway.is_configured(),
    })


@login_required
@require_POST
def portal(request):
    """
    POST /billing/portal/ — hand the customer to the Stripe Customer Portal.

    The portal is where payment methods are updated, invoices downloaded, and
    subscriptions cancelled or switched. Doing it there rather than in EcoIQ
    means no card details ever touch this application, and every change comes
    back as a signed webhook instead of being trusted from a form post.
    """
    organisation = _require_organisation(request, request.POST.get('organisation_id'))

    try:
        session = stripe_gateway.create_billing_portal_session(
            request=request, user=request.user, organisation=organisation)
    except BillingNotConfigured as exc:
        messages.error(request, str(exc))
        return redirect('billing:manage')
    except stripe.StripeError:
        logger.exception('Stripe rejected a portal session for user %s', request.user.pk)
        messages.error(
            request,
            'The billing portal is unavailable right now. If this persists, '
            'the Customer Portal may still need configuring in Stripe.')
        return redirect('billing:manage')

    return SeeOther(session['url'])


# ── Webhook ──────────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def webhook(request):
    """
    POST /billing/webhook/ — the Stripe webhook endpoint.

    Public and CSRF-exempt by necessity: Stripe's servers have no session and
    no CSRF token. The signature check is the entire authentication story,
    which is why it runs first, against `request.body` — the raw, unmodified
    bytes — and why nothing is parsed before it passes.

    Status codes are chosen for Stripe's retry behaviour, not for a human:
      400  unverifiable — forged, tampered, stale, or wrong secret. Stripe
           does not retry these, and should not: a retry cannot fix a bad
           signature, and retrying would amplify a forgery attempt.
      200  verified. Includes duplicates and deliberately-ignored events —
           the delivery genuinely succeeded, so Stripe must stop retrying.
      500  verified but the handler failed internally. Stripe retries with
           backoff, and the handler is written to be safe to re-run.
    """
    signature_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    try:
        event = verify_event(request.body, signature_header)
    except WebhookVerificationError as exc:
        # Logged without the payload or the supplied signature: an attacker
        # should not be able to write chosen content into our log files.
        logger.warning('Rejected Stripe webhook: %s', exc)
        return HttpResponse(status=400)

    status, note = process_event(event)

    if status == 'failed':
        return JsonResponse({'received': True, 'status': status, 'detail': note}, status=500)
    return JsonResponse({'received': True, 'status': status, 'detail': note}, status=200)
