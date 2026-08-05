"""
EcoIQ entitlement resolution — the ONE place that decides whether a user or
organisation may use a gated feature. Every view/API permission/template
that needs to gate something calls has_entitlement() (or the convenience
check_and_record_usage() when the feature also consumes a quota) instead of
re-deriving plan logic inline — see the module docstring in models.py for
why this exists (PART 3 of the spec this was built against: "Do not scatter
logic such as `if user.is_pro:` across templates").

Resolution order (first match wins for *inclusion*; quantity limits are then
applied on top of whichever source granted access):
    1. An unexpired manual Entitlement grant (comp access, beta tester, etc.)
    2. The user's (or organisation's) active Subscription -> Plan -> PlanFeature
    3. Any public Plan with price_amount == 0 that includes the feature
       (the "free tier" — available even to a user with no subscription row
       at all, exactly like an anonymous visitor gets free-tier web access)
    4. Not entitled.

Usage limits (PlanFeature.quantity_limit / UsageLimit override) are only
enforced for a known user or organisation — anonymous requests are handled
by the caller's own IP/session-based throttling (e.g. api.throttles), not
by this module, since UsageRecord has no concept of an anonymous identity.
"""
import datetime
from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from ecoiq_commerce.models import (
    Entitlement, OrganisationSubscription, Plan, PlanFeature, Subscription,
    UsageLimit, UsageRecord,
)


@dataclass
class EntitlementCheck:
    allowed: bool
    source: str            # 'manual_grant' | 'plan' | 'free_plan' | 'none' | 'usage_exceeded'
    limit: Optional[int]   # None = unlimited
    used: Optional[int]
    remaining: Optional[int]
    period: str             # 'monthly' | 'annual' | 'unlimited'
    reason: str = ''

    def __bool__(self):
        return self.allowed


_DENIED = EntitlementCheck(False, 'none', None, None, None, 'unlimited', 'No plan or grant includes this feature.')


def _period_bounds(period: str, at: datetime.date = None):
    at = at or timezone.now().date()
    if period == 'monthly':
        start = at.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1) - datetime.timedelta(days=1)
        else:
            end = start.replace(month=start.month + 1) - datetime.timedelta(days=1)
        return start, end
    if period == 'annual':
        start = at.replace(month=1, day=1)
        end = at.replace(month=12, day=31)
        return start, end
    return at, at  # 'unlimited' — period bounds unused when there's no quantity limit


def _active_subscription(user, organisation):
    if organisation is not None:
        return (OrganisationSubscription.objects
                .filter(organisation=organisation, status__in=('trialing', 'active'))
                .select_related('plan').order_by('-started_at').first())
    if user is not None and getattr(user, 'is_authenticated', False):
        return (Subscription.objects
                .filter(user=user, status__in=('trialing', 'active'))
                .select_related('plan').order_by('-started_at').first())
    return None


def _manual_grant(user, organisation, feature_key):
    now = timezone.now()
    qs = Entitlement.objects.filter(
        feature__key=feature_key,
    ).filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
    if organisation is not None:
        return qs.filter(organisation=organisation).first()
    if user is not None and getattr(user, 'is_authenticated', False):
        return qs.filter(user=user).first()
    return None


def _free_plan_feature(feature_key):
    """Any public, zero-price plan that includes this feature — the always-on free tier."""
    return (PlanFeature.objects
            .filter(feature__key=feature_key, is_included=True,
                    plan__is_public=True, plan__price_amount=0)
            .select_related('plan', 'feature').first())


def _usage_limit_override(subscription, organisation_subscription, feature_key):
    qs = UsageLimit.objects.filter(feature__key=feature_key)
    if organisation_subscription is not None:
        return qs.filter(organisation_subscription=organisation_subscription).first()
    if subscription is not None:
        return qs.filter(subscription=subscription).first()
    return None


def _current_usage(user, organisation, feature_key, period, period_start):
    qs = UsageRecord.objects.filter(feature__key=feature_key, period_start=period_start)
    if organisation is not None:
        record = qs.filter(organisation=organisation).first()
    else:
        record = qs.filter(user=user).first()
    return record.used_quantity if record else 0


def has_entitlement(user, feature_key: str, organisation=None, quantity: int = 1, plan: Plan = None) -> EntitlementCheck:
    """
    The single source of truth for "can this user/organisation use this
    feature right now". Returns an EntitlementCheck (truthy iff allowed).

    `plan` is an explicit override for callers that already know which Plan
    governs the request without a Subscription row backing it — e.g. an
    api.APIKey carries its own `plan` FK directly (an API-only customer may
    never have a Subscription/OrganisationSubscription at all). When given,
    it's used as the effective plan instead of looking one up; usage is
    still tracked against `user`/`organisation` as normal.
    """
    subscription = None
    organisation_subscription = None
    if plan is None:
        if organisation is not None:
            organisation_subscription = _active_subscription(None, organisation)
        else:
            subscription = _active_subscription(user, None)

    # 1. Manual grant
    grant = _manual_grant(user, organisation, feature_key)
    if grant is not None:
        if grant.granted_quantity is None:
            return EntitlementCheck(True, 'manual_grant', None, None, None, 'unlimited')
        used = _current_usage(user, organisation, feature_key, 'monthly', _period_bounds('monthly')[0])
        remaining = max(0, grant.granted_quantity - used)
        return EntitlementCheck(remaining >= quantity, 'manual_grant', grant.granted_quantity,
                                 used, remaining, 'monthly',
                                 '' if remaining >= quantity else 'Manual grant quota exhausted for this period.')

    # 2. Active plan (explicit override, or subscription / organisation subscription)
    active_sub = organisation_subscription or subscription
    effective_plan = plan or (active_sub.plan if active_sub else None)
    plan_feature = None
    if effective_plan is not None:
        plan_feature = PlanFeature.objects.filter(plan=effective_plan, feature__key=feature_key).select_related('feature').first()

    source = 'plan'
    if plan_feature is None or not plan_feature.is_included:
        # 3. Free tier fallback
        plan_feature = _free_plan_feature(feature_key)
        source = 'free_plan'
        active_sub = None  # free tier usage is tracked per-user/org, not per-subscription-scoped limit override

    if plan_feature is None or not plan_feature.is_included:
        return _DENIED

    if plan_feature.limit_period == 'unlimited' or plan_feature.quantity_limit is None:
        return EntitlementCheck(True, source, None, None, None, 'unlimited')

    # Quantity-limited — check for a custom override first, then the plan default.
    override = _usage_limit_override(subscription, organisation_subscription, feature_key) if active_sub else None
    limit_value = override.limit_value if override else plan_feature.quantity_limit
    period = override.period if override else plan_feature.limit_period

    if limit_value is None:
        return EntitlementCheck(True, source, None, None, None, period)

    if user is None and organisation is None:
        # No identity to track usage against — allow inclusion, can't enforce quota.
        return EntitlementCheck(True, source, limit_value, None, None, period,
                                 'Usage limit not enforceable for an anonymous caller.')

    period_start, _period_end = _period_bounds(period)
    used = _current_usage(user, organisation, feature_key, period, period_start)
    remaining = max(0, limit_value - used)
    allowed = remaining >= quantity
    return EntitlementCheck(allowed, source, limit_value, used, remaining, period,
                             '' if allowed else f'{period.title()} usage limit reached ({used}/{limit_value}).')


def record_usage(user, feature_key: str, organisation=None, amount: int = 1):
    """
    Increments the usage counter for the current period. Does NOT check
    entitlement first — call has_entitlement() (or check_and_record_usage())
    before doing the gated work.
    """
    from ecoiq_commerce.models import Feature
    feature = Feature.objects.get(key=feature_key)

    # Use the plan's configured period where possible so the counter resets
    # on the same cadence the limit is defined against; default to monthly.
    period = 'monthly'
    active_sub = _active_subscription(None, organisation) if organisation else _active_subscription(user, None)
    if active_sub:
        pf = PlanFeature.objects.filter(plan=active_sub.plan, feature=feature).first()
        if pf:
            period = pf.limit_period if pf.limit_period != 'unlimited' else 'monthly'

    period_start, period_end = _period_bounds(period)
    with transaction.atomic():
        record, _created = UsageRecord.objects.get_or_create(
            user=user if organisation is None else None,
            organisation=organisation,
            feature=feature,
            period_start=period_start,
            defaults={'period_end': period_end, 'used_quantity': 0},
        )
        UsageRecord.objects.filter(pk=record.pk).update(used_quantity=F('used_quantity') + amount)
    return record


def check_and_record_usage(user, feature_key: str, organisation=None, amount: int = 1) -> EntitlementCheck:
    """Convenience wrapper: check entitlement, and if allowed, record the usage."""
    check = has_entitlement(user, feature_key, organisation=organisation, quantity=amount)
    if check.allowed:
        record_usage(user, feature_key, organisation=organisation, amount=amount)
    return check
