"""
Regression tests for entitlement precedence.

Two bugs are pinned here, both of which grant or deny access incorrectly
without ever looking broken:

1. Resolution used the most recently *started* subscription. A customer who
   upgraded to Pro and then added a cheaper Starter subscription would be
   resolved against Starter, silently losing the entitlement they pay for.

2. Only `status` was checked, never the period. A subscription left at
   'active' with a current_period_end in the past — which is what a missed,
   delayed or never-delivered cancellation webhook leaves behind — kept
   granting access indefinitely, for free.
"""
import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from ecoiq_commerce.models import (
    Feature, Organisation, OrganisationSubscription, Plan, PlanFeature, Product,
    Subscription,
)
from ecoiq_commerce.services.entitlements import has_entitlement

User = get_user_model()


class EntitlementPrecedenceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='multisub', password='pw12345')
        self.organisation = Organisation.objects.create(name='Acme', slug='acme-prec')
        self.product = Product.objects.create(
            key='prec-product', product_type='professional', name='Product', status='active')
        self.feature = Feature.objects.create(
            key='evidence_access', name='Evidence', category='company_data')

        self.starter = self._plan('starter', limit=10, period='monthly')
        self.pro = self._plan('pro', limit=None, period='unlimited')
        self.mid = self._plan('mid', limit=500, period='monthly')
        self.excluded = self._plan('excluded', included=False)

        self.now = timezone.now()
        self.future = self.now + datetime.timedelta(days=15)
        self.past = self.now - datetime.timedelta(days=15)

    def _plan(self, key, *, limit=None, period='unlimited', included=True):
        plan = Plan.objects.create(product=self.product, key=key, name=key.title(),
                                    price_amount=10, is_public=True)
        PlanFeature.objects.create(plan=plan, feature=self.feature, is_included=included,
                                    quantity_limit=limit, limit_period=period)
        return plan

    def _sub(self, plan, *, started_days_ago=0, period_end=None, status='active'):
        sub = Subscription.objects.create(user=self.user, plan=plan, status=status,
                                           current_period_end=period_end or self.future)
        Subscription.objects.filter(pk=sub.pk).update(
            started_at=self.now - datetime.timedelta(days=started_days_ago))
        return Subscription.objects.get(pk=sub.pk)

    def _org_sub(self, plan, *, started_days_ago=0, period_end=None, status='active'):
        sub = OrganisationSubscription.objects.create(
            organisation=self.organisation, plan=plan, status=status,
            current_period_end=period_end or self.future)
        OrganisationSubscription.objects.filter(pk=sub.pk).update(
            started_at=self.now - datetime.timedelta(days=started_days_ago))
        return OrganisationSubscription.objects.get(pk=sub.pk)

    # ── highest entitlement wins, not the newest row ─────────────────────────

    def test_unlimited_plan_wins_over_a_newer_limited_one(self):
        self._sub(self.pro, started_days_ago=30)
        self._sub(self.starter, started_days_ago=1)          # newer, weaker
        check = has_entitlement(self.user, 'evidence_access')
        self.assertTrue(check.allowed)
        self.assertIsNone(check.limit, 'newer Starter masked the Pro entitlement')

    def test_larger_limit_wins_over_a_newer_smaller_one(self):
        self._sub(self.mid, started_days_ago=30)             # 500/month
        self._sub(self.starter, started_days_ago=1)          # 10/month, newer
        self.assertEqual(has_entitlement(self.user, 'evidence_access').limit, 500)

    def test_order_of_creation_does_not_change_the_answer(self):
        self._sub(self.starter, started_days_ago=30)
        self._sub(self.pro, started_days_ago=1)
        self.assertIsNone(has_entitlement(self.user, 'evidence_access').limit)

    def test_included_plan_wins_over_a_newer_excluding_one(self):
        self._sub(self.pro, started_days_ago=30)
        self._sub(self.excluded, started_days_ago=1)
        self.assertTrue(has_entitlement(self.user, 'evidence_access').allowed)

    def test_organisation_with_several_subscriptions_gets_the_highest(self):
        self._org_sub(self.pro, started_days_ago=30)
        self._org_sub(self.starter, started_days_ago=1)
        check = has_entitlement(None, 'evidence_access', organisation=self.organisation)
        self.assertTrue(check.allowed)
        self.assertIsNone(check.limit)

    # ── invalid subscriptions must not grant ─────────────────────────────────

    def test_active_but_expired_period_does_not_grant(self):
        """A missed cancellation webhook must not mean free access forever."""
        self._sub(self.pro, period_end=self.past)
        self.assertFalse(has_entitlement(self.user, 'evidence_access').allowed)

    def test_expired_subscription_cannot_mask_a_valid_weaker_one(self):
        self._sub(self.pro, started_days_ago=1, period_end=self.past)     # expired
        self._sub(self.starter, started_days_ago=30)                       # valid
        check = has_entitlement(self.user, 'evidence_access')
        self.assertTrue(check.allowed)
        self.assertEqual(check.limit, 10, 'expired Pro row still granted unlimited')

    def test_null_period_end_is_still_valid(self):
        """Manually-created and NullBillingProvider subscriptions have no period."""
        Subscription.objects.create(user=self.user, plan=self.pro, status='active',
                                     current_period_end=None)
        self.assertTrue(has_entitlement(self.user, 'evidence_access').allowed)

    def test_non_entitling_statuses_never_grant(self):
        for status in ('past_due', 'cancelled', 'expired'):
            with self.subTest(status=status):
                Subscription.objects.all().delete()
                self._sub(self.pro, status=status)
                self.assertFalse(
                    has_entitlement(self.user, 'evidence_access').allowed,
                    f'status={status} granted access')

    def test_cancelled_alongside_valid_still_grants_via_the_valid_one(self):
        self._sub(self.pro, started_days_ago=1, status='cancelled')
        self._sub(self.starter, started_days_ago=30, status='active')
        check = has_entitlement(self.user, 'evidence_access')
        self.assertTrue(check.allowed)
        self.assertEqual(check.limit, 10)

    def test_all_invalid_means_no_access(self):
        self._sub(self.pro, status='cancelled')
        self._sub(self.starter, status='past_due')
        self.assertFalse(has_entitlement(self.user, 'evidence_access').allowed)
