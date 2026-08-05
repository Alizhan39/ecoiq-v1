"""
Tests for the ecoiq_commerce commercial platform.

SECURE_SSL_REDIRECT is overridden on every test-client class below. settings.py
turns it on whenever DEBUG is False, which is what CI sets — without the
override the test client is 301'd to https before reaching any view, and an
assertion like "an ordinary user gets 404 for someone else's key" would pass
for entirely the wrong reason. Overriding it here means these tests assert real
behaviour under both DEBUG=True (the local convention) and DEBUG=False. No
production setting is changed.
"""
import datetime

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from api.models import APIKey
from ecoiq_commerce.models import (
    CommercialEvent, Entitlement, Feature, Organisation, OrganisationSubscription,
    Plan, PlanFeature, Product, Subscription, UsageLimit,
)
from ecoiq_commerce.services.entitlements import (
    check_and_record_usage, has_entitlement, record_usage,
)
from ecoiq_commerce.services.events import track_event

User = get_user_model()


def _feature(key='test_feature'):
    return Feature.objects.create(key=key, name=key, category='api')


def _plan(feature, *, price=0, public=True, quantity_limit=None, limit_period='unlimited', product_type='lite'):
    product = Product.objects.create(key=f'prod-{feature.key}-{price}', product_type=product_type,
                                      name='Test Product', status='active')
    plan = Plan.objects.create(product=product, key='plan', name='Test Plan',
                                price_amount=price, is_public=public)
    PlanFeature.objects.create(plan=plan, feature=feature, is_included=True,
                                quantity_limit=quantity_limit, limit_period=limit_period)
    return plan


@override_settings(SECURE_SSL_REDIRECT=False)
class SelfServiceAPIKeyTest(TestCase):
    def setUp(self):
        call_command('seed_commercial_catalogue')
        self.user = User.objects.create_user(username='keyuser', password='pw12345')
        self.client.force_login(self.user)

    def test_create_list_rotate_revoke_flow(self):
        resp = self.client.post('/products/api-keys/', follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(APIKey.objects.filter(owner=self.user).count(), 1)

        key = APIKey.objects.get(owner=self.user)
        self.assertEqual(key.environment, 'sandbox')
        self.assertTrue(key.is_active)

        resp = self.client.get('/products/api-keys/')
        self.assertContains(resp, key.prefix)

        resp = self.client.post(f'/products/api-keys/{key.pk}/rotate/', follow=True)
        self.assertEqual(resp.status_code, 200)
        key.refresh_from_db()
        self.assertFalse(key.is_active)
        new_key = APIKey.objects.get(rotated_from=key)
        self.assertTrue(new_key.is_active)

        resp = self.client.post(f'/products/api-keys/{new_key.pk}/revoke/', follow=True)
        self.assertEqual(resp.status_code, 200)
        new_key.refresh_from_db()
        self.assertFalse(new_key.is_active)
        self.assertIsNotNone(new_key.revoked_at)

    def test_cannot_rotate_or_revoke_someone_elses_key(self):
        other = User.objects.create_user(username='other', password='pw12345')
        other_key, _raw = APIKey.create_key(name='other key', owner=other, environment='sandbox')

        resp = self.client.post(f'/products/api-keys/{other_key.pk}/revoke/')
        self.assertEqual(resp.status_code, 404)
        other_key.refresh_from_db()
        self.assertTrue(other_key.is_active)

    def test_page_is_noindexed(self):
        resp = self.client.get('/products/api-keys/')
        self.assertContains(resp, 'noindex')


@override_settings(SECURE_SSL_REDIRECT=False)
class ProductsPageTest(TestCase):
    def test_products_page_renders_all_catalogue_products(self):
        call_command('seed_commercial_catalogue')
        resp = self.client.get('/products/')
        self.assertEqual(resp.status_code, 200)
        for product in Product.objects.all():
            self.assertContains(resp, product.name)


@override_settings(SECURE_SSL_REDIRECT=False)
class DashboardTest(TestCase):
    def test_staff_only(self):
        user = User.objects.create_user(username='regular', password='pw12345')
        self.client.force_login(user)
        resp = self.client.get('/products/dashboard/')
        self.assertNotEqual(resp.status_code, 200)

    def test_staff_can_view(self):
        staff = User.objects.create_user(username='staffer', password='pw12345', is_staff=True)
        self.client.force_login(staff)
        resp = self.client.get('/products/dashboard/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Commercial Dashboard')
        self.assertContains(resp, 'noindex')


@override_settings(SECURE_SSL_REDIRECT=False)
class EntitlementServiceTest(TestCase):
    """Unit tests for the single entitlement resolver -- ecoiq_commerce.services.entitlements.has_entitlement()."""

    def setUp(self):
        self.user = User.objects.create_user(username='entuser', password='pw12345')
        self.other_user = User.objects.create_user(username='otheruser', password='pw12345')

    def test_denied_when_nothing_matches(self):
        _feature(key='nope')
        check = has_entitlement(self.user, 'nope')
        self.assertFalse(check)
        self.assertEqual(check.source, 'none')

    def test_manual_grant_unlimited(self):
        feature = _feature()
        Entitlement.objects.create(user=self.user, feature=feature, granted_quantity=None)
        check = has_entitlement(self.user, feature.key)
        self.assertTrue(check)
        self.assertEqual(check.source, 'manual_grant')
        self.assertIsNone(check.limit)

    def test_manual_grant_quota_enforced(self):
        feature = _feature()
        Entitlement.objects.create(user=self.user, feature=feature, granted_quantity=2)
        self.assertTrue(has_entitlement(self.user, feature.key))
        record_usage(self.user, feature.key, amount=2)
        check = has_entitlement(self.user, feature.key)
        self.assertFalse(check)
        self.assertEqual(check.source, 'manual_grant')
        self.assertEqual(check.remaining, 0)

    def test_expired_manual_grant_not_used(self):
        feature = _feature()
        Entitlement.objects.create(
            user=self.user, feature=feature, granted_quantity=None,
            expires_at=timezone.now() - datetime.timedelta(days=1),
        )
        check = has_entitlement(self.user, feature.key)
        self.assertFalse(check)

    def test_active_subscription_grants_plan_feature(self):
        feature = _feature()
        plan = _plan(feature, price=15)
        Subscription.objects.create(user=self.user, plan=plan, status='active')
        check = has_entitlement(self.user, feature.key)
        self.assertTrue(check)
        self.assertEqual(check.source, 'plan')

    def test_canceled_subscription_denied_unless_free_tier_covers_it(self):
        feature = _feature()
        plan = _plan(feature, price=15)
        Subscription.objects.create(user=self.user, plan=plan, status='canceled')
        check = has_entitlement(self.user, feature.key)
        self.assertFalse(check)

    def test_free_public_plan_is_always_on_fallback(self):
        feature = _feature()
        _plan(feature, price=0)  # public, $0 -- the always-on free tier
        # No subscription row at all for this user.
        check = has_entitlement(self.user, feature.key)
        self.assertTrue(check)
        self.assertEqual(check.source, 'free_plan')

    def test_plan_override_bypasses_subscription_lookup(self):
        # Mirrors api.APIKey.plan: an explicit plan with no backing Subscription row.
        feature = _feature()
        plan = _plan(feature, price=499)
        check = has_entitlement(None, feature.key, plan=plan)
        self.assertTrue(check)
        self.assertEqual(check.source, 'plan')

    def test_monthly_usage_limit_enforced_and_resets_conceptually_per_period(self):
        feature = _feature()
        plan = _plan(feature, price=15, quantity_limit=2, limit_period='monthly')
        Subscription.objects.create(user=self.user, plan=plan, status='active')

        self.assertTrue(check_and_record_usage(self.user, feature.key))
        self.assertTrue(check_and_record_usage(self.user, feature.key))
        check = check_and_record_usage(self.user, feature.key)
        self.assertFalse(check)
        self.assertEqual(check.used, 2)
        self.assertEqual(check.remaining, 0)

    def test_usage_limit_override_takes_precedence_over_plan_default(self):
        feature = _feature()
        plan = _plan(feature, price=15, quantity_limit=2, limit_period='monthly')
        sub = Subscription.objects.create(user=self.user, plan=plan, status='active')
        UsageLimit.objects.create(subscription=sub, feature=feature, limit_value=5, period='monthly')

        check = has_entitlement(self.user, feature.key)
        self.assertEqual(check.limit, 5)

    def test_org_subscription_does_not_leak_to_other_org(self):
        feature = _feature()
        plan = _plan(feature, price=299, product_type='professional')
        org_a = Organisation.objects.create(name='Org A', slug='org-a')
        org_b = Organisation.objects.create(name='Org B', slug='org-b')
        OrganisationSubscription.objects.create(organisation=org_a, plan=plan, status='active')

        self.assertTrue(has_entitlement(None, feature.key, organisation=org_a))
        # Org B has no subscription of its own and the plan isn't a public
        # free plan, so no entitlement should leak across organisations.
        self.assertFalse(has_entitlement(None, feature.key, organisation=org_b))

    def test_usage_is_tracked_separately_per_user(self):
        feature = _feature()
        plan = _plan(feature, price=15, quantity_limit=1, limit_period='monthly')
        Subscription.objects.create(user=self.user, plan=plan, status='active')
        Subscription.objects.create(user=self.other_user, plan=plan, status='active')

        self.assertTrue(check_and_record_usage(self.user, feature.key))
        self.assertFalse(check_and_record_usage(self.user, feature.key))
        # other_user's own quota is untouched by self.user's usage.
        self.assertTrue(check_and_record_usage(self.other_user, feature.key))


@override_settings(SECURE_SSL_REDIRECT=False)
class TrackEventTest(TestCase):
    def test_unknown_event_type_rejected(self):
        with self.assertRaises(ValueError):
            track_event('not_a_real_event_type')

    def test_creates_row_with_known_event_type(self):
        event = track_event('trial_started')
        self.assertIsInstance(event, CommercialEvent)
        self.assertEqual(CommercialEvent.objects.count(), 1)

    def test_metadata_allowlist_drops_unknown_keys_and_never_raises(self):
        event = track_event('report_viewed', metadata={
            'plan_key': 'lite',
            'raw_report_body': 'this must never be stored',
            'portfolio_holdings': ['AAPL', 'MSFT'],
        })
        self.assertEqual(event.metadata, {'plan_key': 'lite'})
        self.assertNotIn('raw_report_body', event.metadata)
        self.assertNotIn('portfolio_holdings', event.metadata)
