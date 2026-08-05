"""
ecoiq_commerce/views.py — PART 14 (/products/ catalogue page), PART 17
(self-service API key page), PART 12 (commercial admin dashboard).

Permission pattern matches core/investor_portfolio conventions used
elsewhere in the platform: @login_required for personal pages, and
get_object_or_404 scoped to `owner=request.user` for anything key-specific
(unauthorized access 404s rather than 403ing, so it never confirms whether
a given key id belongs to someone else).
"""
import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ecoiq_commerce.models import (
    CommercialEvent, Invoice, Organisation, OrganisationSubscription, Plan, Product, Subscription,
)
from ecoiq_commerce.services.entitlements import has_entitlement
from ecoiq_commerce.services.events import track_event


# ── PART 14: /products/ catalogue ────────────────────────────────────────────

def products(request):
    """
    GET /products/ — public commercial catalogue. Pulls Product/Plan rows
    straight from the DB (PART 2: "configurable, not hard-coded"). Products
    with status='coming_soon' render with a clearly-labelled coming-soon
    state and no functional CTA — never presented as if they were live.
    """
    catalogue = (Product.objects
                 .prefetch_related('plans')
                 .order_by('sort_order', 'name'))
    context = {
        'products': [
            {'product': p, 'plans': [pl for pl in p.plans.all() if pl.is_public]}
            for p in catalogue
        ],
    }
    return render(request, 'ecoiq_commerce/products.html', context)


# ── PART 17: self-service API key management ─────────────────────────────────

def _users_api_plan(user):
    sub = (Subscription.objects
           .filter(user=user, status__in=('trialing', 'active'), plan__product__product_type='data_api')
           .select_related('plan').order_by('-started_at').first())
    return sub.plan if sub else None


@login_required
def api_keys(request):
    """
    GET  /products/api-keys/  — list the caller's own API keys.
    POST /products/api-keys/  — create a new SANDBOX key on their current
                                 Data API plan (or the free Explorer tier).

    Deliberately sandbox-only for self-service — production key issuance
    stays an admin action (see api/admin.py) until a real self-serve
    checkout/verification flow exists; see the final report's "prepared,
    not operational" section.
    """
    from api.models import APIKey

    if request.method == 'POST':
        check = has_entitlement(request.user, 'api_access')
        if not check.allowed:
            messages.error(request, check.reason or 'Your current plan does not include API access.')
            return redirect('commerce:api_keys')

        plan = _users_api_plan(request.user)
        tier = plan.api_tier if (plan and plan.api_tier) else 'explorer'
        _instance, raw_key = APIKey.create_key(
            name=f'{request.user.get_username()} — self-service',
            tier=tier,
            owner=request.user,
            plan=plan,
            environment='sandbox',
        )
        track_event('api_key_created', user=request.user, plan=plan,
                     metadata={'plan_key': plan.key if plan else '', 'api_key_prefix': raw_key[:8]})
        messages.success(
            request,
            f'Sandbox API key created. Copy it now — it will not be shown again: {raw_key}',
        )
        return redirect('commerce:api_keys')

    keys = APIKey.objects.filter(owner=request.user).order_by('-created_at')
    check = has_entitlement(request.user, 'api_access')
    return render(request, 'ecoiq_commerce/api_keys.html', {
        'keys': keys,
        'can_create': check.allowed,
        'entitlement_reason': check.reason,
    })


@login_required
def api_key_rotate(request, pk):
    from api.models import APIKey
    key = get_object_or_404(APIKey, pk=pk, owner=request.user)
    if request.method == 'POST' and key.is_active:
        _new_key, raw_key = key.rotate()
        messages.success(
            request,
            f'Key rotated. Copy the new key now — it will not be shown again: {raw_key}',
        )
    return redirect('commerce:api_keys')


@login_required
def api_key_revoke(request, pk):
    from api.models import APIKey
    key = get_object_or_404(APIKey, pk=pk, owner=request.user)
    if request.method == 'POST' and key.is_active:
        key.revoke()
        track_event('api_key_revoked', user=request.user, plan=key.plan,
                     metadata={'api_key_prefix': key.prefix})
        messages.success(request, f'Key {key.prefix}… revoked.')
    return redirect('commerce:api_keys')


# ── PART 12: commercial admin dashboard ──────────────────────────────────────

def _monthly_equivalent(plan: Plan):
    if plan is None or plan.price_amount is None:
        return None
    if plan.billing_period == 'monthly':
        return plan.price_amount
    if plan.billing_period == 'annual':
        return plan.price_amount / 12
    return None  # one_time / usage / custom — not a recurring-revenue figure


def _mrr():
    """
    Sum of monthly-equivalent price across active/trialing Subscriptions and
    OrganisationSubscriptions on monthly or annual plans. Excludes one_time,
    usage-based, and custom/contact-sales plans — those aren't recurring
    revenue in the accounting sense, so folding them in would overstate MRR.
    This is a commercial-analytics estimate, NOT a statutory revenue
    recognition figure (see PART 12: keep the two separate).
    """
    total = 0
    for sub in Subscription.objects.filter(status__in=('trialing', 'active')).select_related('plan'):
        amount = _monthly_equivalent(sub.plan)
        if amount:
            total += amount
    for osub in OrganisationSubscription.objects.filter(status__in=('trialing', 'active')).select_related('plan'):
        amount = _monthly_equivalent(osub.plan)
        if amount:
            total += amount
    return total


@staff_member_required(login_url='/login/')
def dashboard(request):
    """
    GET /products/dashboard/ — staff-only commercial metrics view.

    Every figure is explicitly labelled with what it counts and as-of when
    it was computed — this is a live commercial-analytics snapshot, not a
    statutory accounting report (PART 12: "do not fabricate accounting
    recognition rules; keep commercial analytics separate from statutory
    accounting").
    """
    now = timezone.now()
    mrr = _mrr()

    active_individual_subs = Subscription.objects.filter(status__in=('trialing', 'active')).count()
    active_org_subs = OrganisationSubscription.objects.filter(status__in=('trialing', 'active')).count()

    from api.models import APIKey, APIRequestLog
    active_api_keys = APIKey.objects.filter(is_active=True).count()
    api_requests_30d = APIRequestLog.objects.filter(
        created_at__gte=now - datetime.timedelta(days=30)
    ).count()

    signups_30d = CommercialEvent.objects.filter(
        event_type='subscription_started', occurred_at__gte=now - datetime.timedelta(days=30)
    ).count()
    trials_30d = CommercialEvent.objects.filter(
        event_type='trial_started', occurred_at__gte=now - datetime.timedelta(days=30)
    ).count()

    plan_breakdown = []
    for plan in Plan.objects.select_related('product').filter(is_public=True):
        n = (Subscription.objects.filter(plan=plan, status__in=('trialing', 'active')).count()
             + OrganisationSubscription.objects.filter(plan=plan, status__in=('trialing', 'active')).count())
        if n:
            plan_breakdown.append({'plan': plan, 'count': n})

    unpaid_invoices = Invoice.objects.filter(status__in=('open', 'past_due')).count()
    orgs_total = Organisation.objects.count()

    context = {
        'generated_at': now,
        'mrr': mrr,
        'arr': mrr * 12 if mrr else 0,
        'active_individual_subs': active_individual_subs,
        'active_org_subs': active_org_subs,
        'active_api_keys': active_api_keys,
        'api_requests_30d': api_requests_30d,
        'signups_30d': signups_30d,
        'trials_30d': trials_30d,
        'plan_breakdown': plan_breakdown,
        'unpaid_invoices': unpaid_invoices,
        'orgs_total': orgs_total,
        'billing_provider': settings.ECOIQ_BILLING_PROVIDER,
    }
    return render(request, 'ecoiq_commerce/dashboard.html', context)
