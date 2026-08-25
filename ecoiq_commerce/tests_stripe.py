"""
Tests for the Stripe billing integration.

No test here touches the network. Outbound calls (`stripe.Customer.create`,
`stripe.checkout.Session.create`, `stripe.billing_portal.Session.create`) are
patched; inbound webhook payloads are signed locally with a test secret using
Stripe's own `WebhookSignature` implementation, so the signature-verification
path under test is the real one rather than a stub of it.

Coverage maps to the integration's actual risks:

* signature verification — valid, missing, tampered, wrong secret, stale
* idempotency — duplicate delivery must not provision twice
* permission and ownership — anonymous, non-member, wrong-role, cross-tenant
* checkout creation — server-side pricing, metadata, Stripe Tax off by default
* subscription lifecycle — created → past_due → recovered → cancelled
* the redirect must not grant access; only the webhook may
"""
import datetime
import json
import time
from unittest.mock import patch

import stripe
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from ecoiq_commerce.models import (
    BillingCustomer, Feature, Invoice, Organisation, OrganisationMembership,
    OrganisationSubscription, PaymentEvent, Plan, PlanFeature, Product,
    StripeCheckoutRecord, StripeDispute, StripeEvent, Subscription,
)
from ecoiq_commerce.services import stripe_gateway, stripe_sync
from ecoiq_commerce.services.entitlements import has_entitlement
from ecoiq_commerce.services.stripe_webhooks import (
    WebhookVerificationError, process_event, verify_event,
)

User = get_user_model()


# ── A fixed test clock ────────────────────────────────────────────────────────
#
# These fixtures used to carry absolute epoch literals: period_start=1785000000
# and period_end=1787678400, the latter being 2026-08-25T17:20:00Z. Every
# entitlement test passed until real time crossed that instant, and then six of
# them failed permanently — on unchanged code, in CI, on main. A subscription
# whose period has ended is correctly denied by
# `entitlements._active_subscription_qs`, which filters
# `current_period_end__gt=now`; the tests were asserting against a date that had
# quietly become the past.
#
# The fix is not a later date. A later date is the same bug with a longer fuse.
# The fixtures are now defined RELATIVE to a frozen clock, and the clock the
# entitlement code reads is frozen to match, so the gap between "now" and
# "period end" is a constant that no amount of calendar time can close.
#
# Chosen deliberately mid-month and mid-day so no test can accidentally depend
# on a month or day boundary.
FROZEN_NOW = datetime.datetime(2026, 1, 15, 12, 0, 0, tzinfo=datetime.timezone.utc)
FROZEN_EPOCH = int(FROZEN_NOW.timestamp())

#: A period that STARTED 30 days before the frozen clock and ENDS 30 days after
#: it. Both are relative, so both stay on the correct side of "now" forever.
PERIOD_BEHIND_SECONDS = 30 * 24 * 3600
PERIOD_AHEAD_SECONDS = 30 * 24 * 3600

DEFAULT_PERIOD_START = FROZEN_EPOCH - PERIOD_BEHIND_SECONDS
DEFAULT_PERIOD_END = FROZEN_EPOCH + PERIOD_AHEAD_SECONDS


def frozen_clock():
    """
    Freeze the clock that entitlement decisions read.

    Patched on `entitlements` specifically rather than on
    `django.utils.timezone` globally: this is the module whose `timezone.now()`
    decides whether a subscription is live, and freezing it there leaves
    `auto_now_add`, webhook signature staleness and everything else running on
    the real clock — which is what those other tests are actually testing.

    `new=` so the decorator injects no argument into every test method.
    """
    return patch('ecoiq_commerce.services.entitlements.timezone.now',
                 new=lambda: FROZEN_NOW)

# Fake credentials for the local test suite. Every value contains the literal
# word "placeholder" so secret scanners (and humans skimming a diff) classify
# them correctly at a glance. None is a real Stripe key, and none has the
# character length of one.
WEBHOOK_SECRET = 'whsec_PLACEHOLDER_not_a_real_webhook_secret'
TEST_SECRET_KEY = 'sk_test_PLACEHOLDER_not_a_real_secret_key'
OTHER_WEBHOOK_SECRET = 'whsec_PLACEHOLDER_a_different_fake_secret'

STRIPE_TEST_SETTINGS = dict(
    # settings.py enables SECURE_SSL_REDIRECT whenever DEBUG is False, which is
    # what CI sets. Without this the test client is 301'd to https before
    # reaching any view — so a permission assertion such as "a non-member gets
    # 404" would pass for entirely the wrong reason. Disabling it here means
    # these tests assert real behaviour under both DEBUG=True and DEBUG=False.
    # No production setting is changed.
    SECURE_SSL_REDIRECT=False,
    # Stripe is the authoritative provider throughout these tests, which is
    # what services/billing.py:require_provider asserts before any invoice is
    # written. See BillingProviderExclusivityTests for the other half.
    ECOIQ_BILLING_PROVIDER='stripe',
    STRIPE_SECRET_KEY=TEST_SECRET_KEY,
    STRIPE_PUBLISHABLE_KEY='pk_test_PLACEHOLDER_not_a_real_key',
    STRIPE_WEBHOOK_SECRET=WEBHOOK_SECRET,
    STRIPE_PRICE_STARTER_MONTHLY='price_starter_monthly',
    STRIPE_PRICE_STARTER_YEARLY='price_starter_yearly',
    STRIPE_PRICE_PRO_MONTHLY='price_pro_monthly',
    STRIPE_PRICE_PRO_YEARLY='price_pro_yearly',
    STRIPE_AUTOMATIC_TAX_ENABLED=False,
    STRIPE_TAX_ID_COLLECTION_ENABLED=False,
    STRIPE_API_VERSION='',
    STRIPE_BILLING_PORTAL_CONFIGURATION_ID='',
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def sign(payload: dict, secret: str = WEBHOOK_SECRET, timestamp: int = None) -> tuple:
    """
    Produce (body_bytes, Stripe-Signature header) exactly as Stripe would.

    Uses Stripe's own signature generator rather than a hand-rolled HMAC, so
    a change in their scheme would surface here rather than being silently
    accommodated by a matching bug in the test.
    """
    body = json.dumps(payload).encode()
    timestamp = timestamp or int(time.time())
    signature = stripe.WebhookSignature._compute_signature(
        f'{timestamp}.{body.decode()}', secret)
    return body, f't={timestamp},v1={signature}'


def subscription_payload(*, sub_id='sub_test123', customer='cus_test123',
                         status='active', price_id='price_pro_monthly',
                         metadata=None, cancel_at_period_end=False,
                         canceled_at=None, period_start=None,
                         period_end=None):
    """
    A Stripe Subscription in the CURRENT API shape — period boundaries on the
    item, not on the subscription. stripe_sync reads the legacy shape too;
    test_period_dates_read_from_legacy_shape covers that path.

    `period_start`/`period_end` default to a window around FROZEN_NOW rather
    than to fixed epochs, so the subscription is live relative to the frozen
    clock no matter what today's date is. Pass explicit values to test an
    expired or future period.
    """
    if period_start is None:
        period_start = DEFAULT_PERIOD_START
    if period_end is None:
        period_end = DEFAULT_PERIOD_END
    return {
        'id': sub_id,
        'object': 'subscription',
        'customer': customer,
        'status': status,
        'cancel_at_period_end': cancel_at_period_end,
        'canceled_at': canceled_at,
        'trial_end': None,
        'metadata': metadata if metadata is not None else {},
        'items': {'object': 'list', 'data': [{
            'id': 'si_test123',
            'price': {'id': price_id, 'object': 'price'},
            'current_period_start': period_start,
            'current_period_end': period_end,
        }]},
    }


def event(event_type, obj, event_id='evt_test123'):
    return {
        'id': event_id,
        'object': 'event',
        'api_version': '2026-07-29.dahlia',
        'livemode': False,
        'type': event_type,
        'data': {'object': obj},
    }


class StripeBillingTestCase(TestCase):
    """Shared fixtures: a user, an organisation, and priced plans."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='payer', email='payer@example.com', password='pw12345')
        self.other_user = User.objects.create_user(
            username='outsider', email='outsider@example.com', password='pw12345')

        self.organisation = Organisation.objects.create(
            name='Acme Industrial', slug='acme', billing_email='ap@acme.example')
        OrganisationMembership.objects.create(
            organisation=self.organisation, user=self.user, role='owner')

        self.product = Product.objects.create(
            key='ecoiq-pro', product_type='professional', name='EcoIQ Professional',
            status='active')

        self.pro_monthly = Plan.objects.create(
            product=self.product, key='pro-monthly', name='Professional Monthly',
            billing_period='monthly', price_amount=99, currency='GBP',
            stripe_price_id='price_pro_monthly')
        self.starter_monthly = Plan.objects.create(
            product=self.product, key='starter-monthly', name='Starter Monthly',
            billing_period='monthly', price_amount=29, currency='GBP',
            stripe_price_id='price_starter_monthly')
        self.assessment = Plan.objects.create(
            product=self.product, key='assessment', name='Sustainability Assessment',
            billing_period='one_time', price_amount=1500, currency='GBP',
            stripe_price_id='price_assessment_one_time')

        self.feature = Feature.objects.create(
            key='evidence_access', name='Evidence access', category='company_data')
        PlanFeature.objects.create(plan=self.pro_monthly, feature=self.feature,
                                    is_included=True, limit_period='unlimited')

    def post_webhook(self, payload, secret=WEBHOOK_SECRET, body=None, header=None):
        signed_body, signed_header = sign(payload, secret)
        return self.client.post(
            reverse('billing:webhook'),
            data=body if body is not None else signed_body,
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE=header if header is not None else signed_header,
        )


# ── Webhook signature verification ───────────────────────────────────────────

@override_settings(**STRIPE_TEST_SETTINGS)
class WebhookSignatureTests(StripeBillingTestCase):

    def test_valid_signature_is_accepted(self):
        body, header = sign(event('customer.subscription.created',
                                   subscription_payload(metadata={'ecoiq_user_id': str(self.user.pk)})))
        verified = verify_event(body, header)
        self.assertEqual(verified['id'], 'evt_test123')

    def test_missing_signature_header_is_rejected(self):
        body, _header = sign(event('invoice.paid', {'id': 'in_1'}))
        with self.assertRaises(WebhookVerificationError):
            verify_event(body, '')

    def test_wrong_secret_is_rejected(self):
        body, header = sign(event('invoice.paid', {'id': 'in_1'}), secret=OTHER_WEBHOOK_SECRET)
        with self.assertRaises(WebhookVerificationError):
            verify_event(body, header)

    def test_tampered_body_is_rejected(self):
        """The signature covers the exact bytes — a one-character edit breaks it."""
        payload = event('invoice.paid', {'id': 'in_1', 'total': 100})
        body, header = sign(payload)
        tampered = body.replace(b'"total": 100', b'"total": 999')
        self.assertNotEqual(tampered, body)
        with self.assertRaises(WebhookVerificationError):
            verify_event(tampered, header)

    def test_stale_timestamp_is_rejected(self):
        """Replay protection: Stripe's default tolerance is 5 minutes."""
        payload = event('invoice.paid', {'id': 'in_1'})
        body, header = sign(payload, timestamp=int(time.time()) - 86400)
        with self.assertRaises(WebhookVerificationError):
            verify_event(body, header)

    def test_signed_payload_that_is_not_an_event_is_a_400_not_a_500(self):
        """
        Regression: `construct_event` reads `event.object` after verifying,
        and StripeObject raises AttributeError for a missing key instead of
        returning None. A correctly-signed payload missing that key used to
        500 — which makes Stripe retry a request no retry can fix, and leaks
        a traceback under DEBUG. Found by posting to the live dev server;
        the test helper's payloads had always included the key.
        """
        for payload in ({'id': 'evt_x', 'type': 'invoice.paid', 'data': {'object': {}}},
                        {'not': 'an event at all'},
                        []):
            body, header = sign(payload)
            with self.assertRaises(WebhookVerificationError):
                verify_event(body, header)

            response = self.client.post(
                reverse('billing:webhook'), data=body,
                content_type='application/json', HTTP_STRIPE_SIGNATURE=header)
            self.assertEqual(response.status_code, 400, payload)
        self.assertEqual(StripeEvent.objects.count(), 0)

    @override_settings(STRIPE_WEBHOOK_SECRET='')
    def test_unconfigured_secret_refuses_rather_than_trusting(self):
        body, header = sign(event('invoice.paid', {'id': 'in_1'}))
        with self.assertRaises(WebhookVerificationError):
            verify_event(body, header)

    def test_endpoint_returns_400_for_forged_request_and_stores_nothing(self):
        response = self.client.post(
            reverse('billing:webhook'),
            data=json.dumps(event('invoice.paid', {'id': 'in_1'})),
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='t=1,v1=deadbeef')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(StripeEvent.objects.count(), 0)

    def test_endpoint_returns_400_when_signature_header_absent(self):
        response = self.client.post(
            reverse('billing:webhook'),
            data=json.dumps(event('invoice.paid', {'id': 'in_1'})),
            content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_webhook_is_csrf_exempt(self):
        """Stripe has no CSRF token; the signature is the credential."""
        enforcing = self.client_class(enforce_csrf_checks=True)
        body, header = sign(event('customer.subscription.created',
                                   subscription_payload(metadata={'ecoiq_user_id': str(self.user.pk)})))
        response = enforcing.post(
            reverse('billing:webhook'), data=body,
            content_type='application/json', HTTP_STRIPE_SIGNATURE=header)
        self.assertEqual(response.status_code, 200)


# ── Idempotency ──────────────────────────────────────────────────────────────

@override_settings(**STRIPE_TEST_SETTINGS)
class WebhookIdempotencyTests(StripeBillingTestCase):

    def test_duplicate_delivery_does_not_provision_twice(self):
        payload = event('customer.subscription.created',
                        subscription_payload(metadata={'ecoiq_user_id': str(self.user.pk)}))

        first = self.post_webhook(payload)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()['status'], 'processed')
        self.assertEqual(Subscription.objects.count(), 1)

        second = self.post_webhook(payload)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()['status'], 'processed')

        self.assertEqual(Subscription.objects.count(), 1, 'access provisioned twice')
        self.assertEqual(StripeEvent.objects.count(), 1)

    def test_second_delivery_is_not_reprocessed(self):
        payload = event('customer.subscription.created',
                        subscription_payload(metadata={'ecoiq_user_id': str(self.user.pk)}))
        self.post_webhook(payload)

        with patch.object(stripe_sync, 'upsert_subscription') as handler:
            response = self.post_webhook(payload)
        handler.assert_not_called()
        self.assertEqual(response.status_code, 200)

    def test_distinct_event_ids_for_same_object_are_both_processed(self):
        """Idempotency is per event id, not per object — updates must apply."""
        self.post_webhook(event('customer.subscription.created',
                                subscription_payload(metadata={'ecoiq_user_id': str(self.user.pk)}),
                                event_id='evt_one'))
        self.post_webhook(event('customer.subscription.updated',
                                subscription_payload(status='past_due',
                                                     metadata={'ecoiq_user_id': str(self.user.pk)}),
                                event_id='evt_two'))

        self.assertEqual(Subscription.objects.count(), 1)
        self.assertEqual(Subscription.objects.get().status, 'past_due')
        self.assertEqual(StripeEvent.objects.count(), 2)

    def test_unhandled_event_type_is_acknowledged_not_retried(self):
        response = self.post_webhook(event('payment_intent.created', {'id': 'pi_1'}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(StripeEvent.objects.get().status, 'ignored')

    def test_handler_failure_returns_500_so_stripe_retries(self):
        payload = event('customer.subscription.created',
                        subscription_payload(metadata={'ecoiq_user_id': str(self.user.pk)}))
        with patch.object(stripe_sync, 'upsert_subscription',
                          side_effect=RuntimeError('database on fire')):
            response = self.post_webhook(payload)

        self.assertEqual(response.status_code, 500)
        ledger = StripeEvent.objects.get()
        self.assertEqual(ledger.status, 'failed')
        self.assertEqual(Subscription.objects.count(), 0)

    def test_failed_event_is_reprocessed_on_retry(self):
        payload = event('customer.subscription.created',
                        subscription_payload(metadata={'ecoiq_user_id': str(self.user.pk)}))
        with patch.object(stripe_sync, 'upsert_subscription',
                          side_effect=RuntimeError('transient')):
            self.post_webhook(payload)

        response = self.post_webhook(payload)          # Stripe's retry
        self.assertEqual(response.status_code, 200)
        self.assertEqual(StripeEvent.objects.get().status, 'processed')
        self.assertEqual(Subscription.objects.count(), 1)


# ── Subscription lifecycle ───────────────────────────────────────────────────

@override_settings(**STRIPE_TEST_SETTINGS)
@patch('ecoiq_commerce.services.entitlements.timezone.now', new=lambda: FROZEN_NOW)
class SubscriptionLifecycleTests(StripeBillingTestCase):

    def _create(self, **kwargs):
        return self.post_webhook(event(
            'customer.subscription.created',
            subscription_payload(metadata={'ecoiq_user_id': str(self.user.pk)}, **kwargs)))

    def test_created_provisions_a_subscription_with_period_dates(self):
        self._create()
        sub = Subscription.objects.get()
        self.assertEqual(sub.user, self.user)
        self.assertEqual(sub.plan, self.pro_monthly)
        self.assertEqual(sub.status, 'active')
        self.assertEqual(sub.stripe_subscription_id, 'sub_test123')
        self.assertEqual(sub.stripe_price_id, 'price_pro_monthly')
        self.assertIsNotNone(sub.current_period_start)
        self.assertIsNotNone(sub.current_period_end)
        self.assertTrue(sub.is_active)

    def test_created_grants_the_plan_entitlement(self):
        self.assertFalse(has_entitlement(self.user, 'evidence_access').allowed)
        self._create()
        self.assertTrue(has_entitlement(self.user, 'evidence_access').allowed)

    def test_organisation_subscription_is_created_from_metadata(self):
        self.post_webhook(event('customer.subscription.created', subscription_payload(
            metadata={'ecoiq_organisation_id': str(self.organisation.pk)})))
        org_sub = OrganisationSubscription.objects.get()
        self.assertEqual(org_sub.organisation, self.organisation)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_trialing_maps_to_trialing_and_stays_entitled(self):
        self._create(status='trialing')
        self.assertEqual(Subscription.objects.get().status, 'trialing')
        self.assertTrue(has_entitlement(self.user, 'evidence_access').allowed)

    def test_updated_to_past_due_withdraws_entitlement(self):
        self._create()
        self.post_webhook(event('customer.subscription.updated',
                                subscription_payload(status='past_due',
                                                     metadata={'ecoiq_user_id': str(self.user.pk)}),
                                event_id='evt_update'))
        sub = Subscription.objects.get()
        self.assertEqual(sub.status, 'past_due')
        self.assertFalse(sub.is_active)
        self.assertFalse(has_entitlement(self.user, 'evidence_access').allowed)

    def test_cancel_at_period_end_keeps_access_until_the_period_ends(self):
        self._create()
        self.post_webhook(event('customer.subscription.updated',
                                subscription_payload(cancel_at_period_end=True,
                                                     metadata={'ecoiq_user_id': str(self.user.pk)}),
                                event_id='evt_cancel_pending'))
        sub = Subscription.objects.get()
        self.assertTrue(sub.cancel_at_period_end)
        self.assertEqual(sub.status, 'active')
        self.assertTrue(has_entitlement(self.user, 'evidence_access').allowed)

    def test_deleted_cancels_and_withdraws_entitlement(self):
        self._create()
        self.post_webhook(event('customer.subscription.deleted',
                                subscription_payload(status='canceled', canceled_at=DEFAULT_PERIOD_END,
                                                     metadata={'ecoiq_user_id': str(self.user.pk)}),
                                event_id='evt_deleted'))
        sub = Subscription.objects.get()
        self.assertEqual(sub.status, 'cancelled')
        self.assertIsNotNone(sub.canceled_at)
        self.assertFalse(has_entitlement(self.user, 'evidence_access').allowed)

    def test_price_change_moves_the_local_plan(self):
        """An upgrade in the Customer Portal must re-point entitlements."""
        self.post_webhook(event('customer.subscription.created', subscription_payload(
            price_id='price_starter_monthly', metadata={'ecoiq_user_id': str(self.user.pk)})))
        self.assertEqual(Subscription.objects.get().plan, self.starter_monthly)

        self.post_webhook(event('customer.subscription.updated', subscription_payload(
            price_id='price_pro_monthly', metadata={'ecoiq_user_id': str(self.user.pk)}),
            event_id='evt_upgrade'))
        self.assertEqual(Subscription.objects.get().plan, self.pro_monthly)

    def test_unmapped_price_provisions_nothing(self):
        response = self.post_webhook(event('customer.subscription.created', subscription_payload(
            price_id='price_never_configured', metadata={'ecoiq_user_id': str(self.user.pk)})))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(StripeEvent.objects.get().status, 'ignored')
        self.assertEqual(Subscription.objects.count(), 0)

    def test_unattributable_subscription_provisions_nothing(self):
        response = self.post_webhook(event('customer.subscription.created',
                                            subscription_payload(metadata={})))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(StripeEvent.objects.get().status, 'ignored')
        self.assertEqual(Subscription.objects.count(), 0)

    def test_owner_resolves_from_billing_customer_when_metadata_absent(self):
        """Covers subscriptions created directly in the Stripe Dashboard."""
        BillingCustomer.objects.create(user=self.user, provider='stripe',
                                        external_customer_id='cus_dashboard')
        self.post_webhook(event('customer.subscription.created',
                                subscription_payload(customer='cus_dashboard', metadata={})))
        self.assertEqual(Subscription.objects.get().user, self.user)

    def test_period_dates_read_from_legacy_shape(self):
        """Pre-"basil" payloads put the period on the subscription itself."""
        payload = subscription_payload(metadata={'ecoiq_user_id': str(self.user.pk)})
        payload['items']['data'][0].pop('current_period_start')
        payload['items']['data'][0].pop('current_period_end')
        payload['current_period_start'] = DEFAULT_PERIOD_START
        payload['current_period_end'] = DEFAULT_PERIOD_END

        self.post_webhook(event('customer.subscription.created', payload))
        sub = Subscription.objects.get()
        self.assertIsNotNone(sub.current_period_start)
        self.assertIsNotNone(sub.current_period_end)

    def test_unknown_stripe_status_denies_access(self):
        """A status Stripe adds later must fail closed, not fail open."""
        self.assertEqual(stripe_sync.map_subscription_status('some_future_status'), 'expired')
        for stripe_status in ('incomplete', 'incomplete_expired', 'unpaid', 'paused'):
            self.assertNotIn(stripe_sync.map_subscription_status(stripe_status),
                             ('active', 'trialing'), stripe_status)


# ── Invoices ─────────────────────────────────────────────────────────────────

@override_settings(**STRIPE_TEST_SETTINGS)
@patch('ecoiq_commerce.services.entitlements.timezone.now', new=lambda: FROZEN_NOW)
class InvoiceWebhookTests(StripeBillingTestCase):

    def setUp(self):
        super().setUp()
        self.post_webhook(event('customer.subscription.created',
                                subscription_payload(metadata={'ecoiq_user_id': str(self.user.pk)})))

    def _invoice(self, **overrides):
        payload = {
            'id': 'in_test123',
            'object': 'invoice',
            'customer': 'cus_test123',
            'currency': 'gbp',
            'total': 9900,
            'total_taxes': [],
            'description': 'EcoIQ Professional',
            'hosted_invoice_url': 'https://invoice.stripe.com/i/test',
            'status_transitions': {'finalized_at': DEFAULT_PERIOD_START,
                                   'paid_at': DEFAULT_PERIOD_START + 100},
            'parent': {'subscription_details': {'subscription': 'sub_test123'}},
            'payment_intent': 'pi_invoice_test',
            'metadata': {'ecoiq_user_id': str(self.user.pk)},
        }
        payload.update(overrides)
        return payload

    def test_invoice_paid_records_invoice_and_payment_event(self):
        response = self.post_webhook(event('invoice.paid', self._invoice(), event_id='evt_paid'))
        self.assertEqual(response.status_code, 200)

        invoice = Invoice.objects.get()
        self.assertEqual(invoice.external_invoice_id, 'in_test123')
        self.assertEqual(str(invoice.amount_total), '99.00')
        self.assertEqual(invoice.currency, 'GBP')
        self.assertEqual(invoice.status, 'paid')
        self.assertEqual(invoice.subscription, Subscription.objects.get())
        self.assertEqual(PaymentEvent.objects.filter(status='succeeded').count(), 1)

    def test_tax_is_zero_while_stripe_tax_is_disabled(self):
        self.post_webhook(event('invoice.paid', self._invoice(), event_id='evt_paid'))
        self.assertEqual(str(Invoice.objects.get().tax_amount), '0.00')

    def test_tax_totals_are_summed_from_the_list_shape(self):
        self.post_webhook(event('invoice.paid',
                                self._invoice(total_taxes=[{'amount': 1200}, {'amount': 800}]),
                                event_id='evt_taxed'))
        self.assertEqual(str(Invoice.objects.get().tax_amount), '20.00')

    def test_payment_failed_moves_subscription_to_past_due(self):
        self.post_webhook(event('invoice.payment_failed', self._invoice(),
                                event_id='evt_failed'))
        self.assertEqual(Subscription.objects.get().status, 'past_due')
        self.assertEqual(Invoice.objects.get().status, 'open')
        self.assertEqual(PaymentEvent.objects.filter(status='failed').count(), 1)
        self.assertFalse(has_entitlement(self.user, 'evidence_access').allowed)

    def test_paid_after_failure_recovers_the_subscription(self):
        self.post_webhook(event('invoice.payment_failed', self._invoice(), event_id='evt_failed'))
        self.assertEqual(Subscription.objects.get().status, 'past_due')

        self.post_webhook(event('invoice.paid', self._invoice(), event_id='evt_recovered'))
        self.assertEqual(Subscription.objects.get().status, 'active')
        self.assertTrue(has_entitlement(self.user, 'evidence_access').allowed)

    def test_repeat_delivery_of_invoice_paid_creates_one_invoice(self):
        payload = event('invoice.paid', self._invoice(), event_id='evt_paid')
        self.post_webhook(payload)
        self.post_webhook(payload)
        self.assertEqual(Invoice.objects.count(), 1)
        self.assertEqual(PaymentEvent.objects.count(), 1)

    def test_legacy_invoice_subscription_shape_is_understood(self):
        payload = self._invoice()
        payload.pop('parent')
        payload['subscription'] = 'sub_test123'
        self.post_webhook(event('invoice.paid', payload, event_id='evt_legacy'))
        self.assertEqual(Invoice.objects.get().subscription, Subscription.objects.get())


# ── Checkout session creation ────────────────────────────────────────────────

@override_settings(**STRIPE_TEST_SETTINGS)
class CheckoutCreationTests(StripeBillingTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def _patched(self):
        """Patch both outbound Stripe calls a checkout makes."""
        return (
            patch('stripe.Customer.create', return_value={'id': 'cus_test123'}),
            patch('stripe.checkout.Session.create',
                  return_value={'id': 'cs_test123',
                                'url': 'https://checkout.stripe.com/c/pay/cs_test123'}),
        )

    def test_subscription_checkout_redirects_to_stripe_and_records_the_session(self):
        customer_patch, session_patch = self._patched()
        with customer_patch, session_patch as session_create:
            response = self.client.post(reverse('billing:checkout_subscription'),
                                        {'tier': 'pro', 'interval': 'monthly'})

        self.assertEqual(response.status_code, 303)
        self.assertEqual(response['Location'], 'https://checkout.stripe.com/c/pay/cs_test123')

        kwargs = session_create.call_args.kwargs
        self.assertEqual(kwargs['mode'], 'subscription')
        self.assertEqual(kwargs['line_items'], [{'price': 'price_pro_monthly', 'quantity': 1}])
        self.assertEqual(kwargs['client_reference_id'], f'user:{self.user.pk}')
        self.assertEqual(kwargs['metadata']['ecoiq_user_id'], str(self.user.pk))
        self.assertEqual(kwargs['metadata']['ecoiq_plan_id'], str(self.pro_monthly.pk))
        # Copied onto the subscription so later lifecycle events stay attributable.
        self.assertEqual(kwargs['subscription_data']['metadata'], kwargs['metadata'])
        # The secret key travels as a per-call request option, never a global.
        self.assertEqual(kwargs['api_key'], TEST_SECRET_KEY)

        record = StripeCheckoutRecord.objects.get()
        self.assertEqual(record.session_id, 'cs_test123')
        self.assertEqual(record.user, self.user)
        self.assertEqual(record.plan, self.pro_monthly)
        self.assertEqual(record.status, 'created')
        self.assertFalse(record.access_granted)

    def test_automatic_tax_is_absent_by_default(self):
        customer_patch, session_patch = self._patched()
        with customer_patch, session_patch as session_create:
            self.client.post(reverse('billing:checkout_subscription'),
                             {'tier': 'pro', 'interval': 'monthly'})
        self.assertNotIn('automatic_tax', session_create.call_args.kwargs)
        self.assertNotIn('tax_id_collection', session_create.call_args.kwargs)

    @override_settings(STRIPE_AUTOMATIC_TAX_ENABLED=True,
                       STRIPE_TAX_ID_COLLECTION_ENABLED=True)
    def test_automatic_tax_can_be_enabled_by_configuration_alone(self):
        customer_patch, session_patch = self._patched()
        with customer_patch, session_patch as session_create:
            self.client.post(reverse('billing:checkout_subscription'),
                             {'tier': 'pro', 'interval': 'monthly'})
        kwargs = session_create.call_args.kwargs
        self.assertEqual(kwargs['automatic_tax'], {'enabled': True})
        self.assertEqual(kwargs['tax_id_collection'], {'enabled': True})

    def test_one_time_checkout_prices_from_the_catalogue(self):
        customer_patch, session_patch = self._patched()
        with customer_patch, session_patch as session_create:
            response = self.client.post(
                reverse('billing:checkout_one_time', args=[self.assessment.key]))

        self.assertEqual(response.status_code, 303)
        kwargs = session_create.call_args.kwargs
        self.assertEqual(kwargs['mode'], 'payment')
        self.assertEqual(kwargs['line_items'],
                         [{'price': 'price_assessment_one_time', 'quantity': 1}])
        self.assertEqual(kwargs['invoice_creation'], {'enabled': True})
        self.assertEqual(StripeCheckoutRecord.objects.get().mode, 'payment')

    def test_unknown_tier_or_interval_is_rejected(self):
        for payload in ({'tier': 'enterprise', 'interval': 'monthly'},
                        {'tier': 'pro', 'interval': 'weekly'},
                        {}):
            with patch('stripe.checkout.Session.create') as session_create:
                response = self.client.post(reverse('billing:checkout_subscription'), payload)
            self.assertEqual(response.status_code, 400, payload)
            session_create.assert_not_called()

    def test_client_cannot_choose_its_own_price(self):
        """A price id in the request body is ignored — pricing is server-side."""
        customer_patch, session_patch = self._patched()
        with customer_patch, session_patch as session_create:
            self.client.post(reverse('billing:checkout_subscription'), {
                'tier': 'pro', 'interval': 'monthly',
                'price': 'price_one_penny', 'amount': '1', 'price_id': 'price_one_penny',
            })
        self.assertEqual(session_create.call_args.kwargs['line_items'],
                         [{'price': 'price_pro_monthly', 'quantity': 1}])

    @override_settings(STRIPE_PRICE_PRO_MONTHLY='')
    def test_unconfigured_price_fails_cleanly_without_calling_stripe(self):
        with patch('stripe.checkout.Session.create') as session_create:
            response = self.client.post(reverse('billing:checkout_subscription'),
                                        {'tier': 'pro', 'interval': 'monthly'})
        session_create.assert_not_called()
        self.assertRedirects(response, reverse('billing:plans'))

    @override_settings(STRIPE_SECRET_KEY='')
    def test_unconfigured_stripe_fails_cleanly(self):
        with patch('stripe.checkout.Session.create') as session_create:
            response = self.client.post(reverse('billing:checkout_subscription'),
                                        {'tier': 'pro', 'interval': 'monthly'})
        session_create.assert_not_called()
        self.assertRedirects(response, reverse('billing:plans'))

    def test_stripe_error_does_not_leak_into_the_response(self):
        with patch('stripe.Customer.create', return_value={'id': 'cus_test123'}), \
             patch('stripe.checkout.Session.create',
                   side_effect=stripe.InvalidRequestError('secret detail req_abc123', None)):
            response = self.client.post(reverse('billing:checkout_subscription'),
                                        {'tier': 'pro', 'interval': 'monthly'}, follow=True)
        self.assertNotContains(response, 'req_abc123')
        self.assertEqual(StripeCheckoutRecord.objects.count(), 0)

    def test_billing_customer_is_reused_across_checkouts(self):
        customer_patch, session_patch = self._patched()
        with customer_patch as customer_create, session_patch:
            self.client.post(reverse('billing:checkout_subscription'),
                             {'tier': 'pro', 'interval': 'monthly'})
            self.client.post(reverse('billing:checkout_subscription'),
                             {'tier': 'pro', 'interval': 'monthly'})
        self.assertEqual(customer_create.call_count, 1)
        self.assertEqual(BillingCustomer.objects.count(), 1)


# ── Permissions and ownership ────────────────────────────────────────────────

@override_settings(**STRIPE_TEST_SETTINGS)
class BillingPermissionTests(StripeBillingTestCase):

    def test_authenticated_views_require_login(self):
        for name, method in (('billing:manage', 'get'),
                             ('billing:success', 'get'),
                             ('billing:cancelled', 'get'),
                             ('billing:portal', 'post'),
                             ('billing:checkout_subscription', 'post')):
            response = getattr(self.client, method)(reverse(name))
            self.assertEqual(response.status_code, 302, name)
            self.assertIn('/login/', response['Location'], name)

    def test_one_time_checkout_requires_login(self):
        response = self.client.post(
            reverse('billing:checkout_one_time', args=[self.assessment.key]))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_plans_page_is_public(self):
        self.assertEqual(self.client.get(reverse('billing:plans')).status_code, 200)

    def test_non_member_cannot_bill_an_organisation(self):
        self.client.force_login(self.other_user)
        with patch('stripe.checkout.Session.create') as session_create:
            response = self.client.post(reverse('billing:checkout_subscription'), {
                'tier': 'pro', 'interval': 'monthly',
                'organisation_id': str(self.organisation.pk)})
        self.assertEqual(response.status_code, 404)
        session_create.assert_not_called()

    def test_plain_member_cannot_bill_an_organisation(self):
        """'member' may use what was bought; only owner/admin/billing may buy."""
        OrganisationMembership.objects.create(
            organisation=self.organisation, user=self.other_user, role='member')
        self.client.force_login(self.other_user)
        with patch('stripe.checkout.Session.create') as session_create:
            response = self.client.post(reverse('billing:checkout_subscription'), {
                'tier': 'pro', 'interval': 'monthly',
                'organisation_id': str(self.organisation.pk)})
        self.assertEqual(response.status_code, 404)
        session_create.assert_not_called()

    def test_billing_role_may_bill_an_organisation(self):
        OrganisationMembership.objects.create(
            organisation=self.organisation, user=self.other_user, role='billing')
        self.client.force_login(self.other_user)
        with patch('stripe.Customer.create', return_value={'id': 'cus_org'}), \
             patch('stripe.checkout.Session.create',
                   return_value={'id': 'cs_org', 'url': 'https://checkout.stripe.com/c/pay/cs_org'}):
            response = self.client.post(reverse('billing:checkout_subscription'), {
                'tier': 'pro', 'interval': 'monthly',
                'organisation_id': str(self.organisation.pk)})
        self.assertEqual(response.status_code, 303)
        self.assertEqual(StripeCheckoutRecord.objects.get().organisation, self.organisation)

    def test_non_member_cannot_open_an_organisation_portal(self):
        self.client.force_login(self.other_user)
        with patch('stripe.billing_portal.Session.create') as portal_create:
            response = self.client.post(reverse('billing:portal'),
                                        {'organisation_id': str(self.organisation.pk)})
        self.assertEqual(response.status_code, 404)
        portal_create.assert_not_called()

    def test_portal_redirects_the_owner_to_stripe(self):
        self.client.force_login(self.user)
        with patch('stripe.Customer.create', return_value={'id': 'cus_test123'}), \
             patch('stripe.billing_portal.Session.create',
                   return_value={'url': 'https://billing.stripe.com/p/session/test'}) as portal:
            response = self.client.post(reverse('billing:portal'))
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response['Location'], 'https://billing.stripe.com/p/session/test')
        self.assertEqual(portal.call_args.kwargs['api_key'], TEST_SECRET_KEY)

    def test_manage_shows_only_the_callers_own_records(self):
        Subscription.objects.create(user=self.other_user, plan=self.pro_monthly,
                                     stripe_subscription_id='sub_someone_else')
        self.client.force_login(self.user)
        response = self.client.get(reverse('billing:manage'))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.other_user.get_username(), response.content.decode())
        self.assertEqual(list(response.context['personal_subs']), [])

    def test_success_page_cannot_read_another_users_session(self):
        StripeCheckoutRecord.objects.create(
            session_id='cs_someone_else', mode='payment', user=self.other_user,
            plan=self.assessment, access_granted=True)
        self.client.force_login(self.user)
        response = self.client.get(reverse('billing:success'),
                                    {'session_id': 'cs_someone_else'})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['record'])
        self.assertFalse(response.context['confirmed'])

    def test_get_is_rejected_on_state_changing_endpoints(self):
        self.client.force_login(self.user)
        for name in ('billing:checkout_subscription', 'billing:portal', 'billing:webhook'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 405, name)


# ── Redirect must not grant access ───────────────────────────────────────────

@override_settings(**STRIPE_TEST_SETTINGS)
class SuccessRedirectGrantsNothingTests(StripeBillingTestCase):
    """
    The single most important property of this integration: a browser landing
    on the success URL must never be what provisions paid access.
    """

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.record = StripeCheckoutRecord.objects.create(
            session_id='cs_pending', mode='payment', user=self.user,
            plan=self.assessment, stripe_customer_id='cus_test123')

    def _session_payload(self, payment_status='paid', **overrides):
        payload = {
            'id': 'cs_pending',
            'object': 'checkout.session',
            'mode': 'payment',
            'customer': 'cus_test123',
            'payment_status': payment_status,
            'payment_intent': 'pi_test123',
            'amount_total': 150000,
            'currency': 'gbp',
            'client_reference_id': f'user:{self.user.pk}',
            'metadata': {'ecoiq_user_id': str(self.user.pk)},
        }
        payload.update(overrides)
        return payload

    def test_visiting_success_does_not_grant_access(self):
        response = self.client.get(reverse('billing:success'), {'session_id': 'cs_pending'})
        self.assertEqual(response.status_code, 200)
        self.record.refresh_from_db()
        self.assertFalse(self.record.access_granted)
        self.assertEqual(self.record.status, 'created')
        self.assertFalse(response.context['confirmed'])

    def test_repeated_success_visits_never_grant_access(self):
        for _ in range(5):
            self.client.get(reverse('billing:success'), {'session_id': 'cs_pending'})
        self.record.refresh_from_db()
        self.assertFalse(self.record.access_granted)

    def test_webhook_grants_access_and_success_then_reports_it(self):
        response = self.post_webhook(
            event('checkout.session.completed', self._session_payload(), event_id='evt_cs'))
        self.assertEqual(response.status_code, 200)

        self.record.refresh_from_db()
        self.assertTrue(self.record.access_granted)
        self.assertEqual(self.record.status, 'completed')
        self.assertEqual(str(self.record.amount_total), '1500.00')
        self.assertEqual(self.record.currency, 'GBP')
        self.assertEqual(self.record.stripe_payment_intent_id, 'pi_test123')

        page = self.client.get(reverse('billing:success'), {'session_id': 'cs_pending'})
        self.assertTrue(page.context['confirmed'])

    def test_unpaid_session_does_not_grant_access(self):
        self.post_webhook(event('checkout.session.completed',
                                self._session_payload(payment_status='unpaid'),
                                event_id='evt_unpaid'))
        self.record.refresh_from_db()
        self.assertFalse(self.record.access_granted)
        self.assertEqual(self.record.status, 'completed')

    def test_session_not_created_by_ecoiq_provisions_nothing(self):
        response = self.post_webhook(event(
            'checkout.session.completed',
            self._session_payload(id='cs_fabricated_by_an_attacker'),
            event_id='evt_forged_session'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(StripeEvent.objects.get().status, 'ignored')
        self.record.refresh_from_db()
        self.assertFalse(self.record.access_granted)

    def test_owner_mismatch_provisions_nothing(self):
        """Metadata and the local record are two copies of the same claim."""
        response = self.post_webhook(event(
            'checkout.session.completed',
            self._session_payload(metadata={'ecoiq_user_id': str(self.other_user.pk)}),
            event_id='evt_mismatch'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(StripeEvent.objects.get().status, 'ignored')
        self.record.refresh_from_db()
        self.assertFalse(self.record.access_granted)


# ── Configuration and catalogue mapping ──────────────────────────────────────

@override_settings(**STRIPE_TEST_SETTINGS)
class StripeConfigurationTests(StripeBillingTestCase):

    def test_price_lookup_resolves_every_configured_tier(self):
        self.assertEqual(stripe_gateway.price_id_for('pro', 'yearly'), 'price_pro_yearly')
        self.assertEqual(stripe_gateway.price_id_for('starter', 'monthly'),
                         'price_starter_monthly')

    def test_unknown_tier_raises_billing_not_configured(self):
        with self.assertRaises(stripe_gateway.BillingNotConfigured):
            stripe_gateway.price_id_for('enterprise', 'monthly')

    @override_settings(STRIPE_SECRET_KEY='')
    def test_is_configured_is_false_without_a_secret_key(self):
        self.assertFalse(stripe_gateway.is_configured())

    def test_sync_stripe_prices_maps_env_ids_onto_plans(self):
        from django.core.management import call_command
        from io import StringIO

        self.pro_monthly.stripe_price_id = ''
        self.pro_monthly.save(update_fields=['stripe_price_id'])

        out = StringIO()
        call_command('sync_stripe_prices', stdout=out)
        self.pro_monthly.refresh_from_db()
        self.assertEqual(self.pro_monthly.stripe_price_id, 'price_pro_monthly')
        self.assertIn('test mode', out.getvalue())

    def test_sync_stripe_prices_dry_run_writes_nothing(self):
        from django.core.management import call_command
        from io import StringIO

        self.pro_monthly.stripe_price_id = ''
        self.pro_monthly.save(update_fields=['stripe_price_id'])

        call_command('sync_stripe_prices', '--dry-run', stdout=StringIO())
        self.pro_monthly.refresh_from_db()
        self.assertEqual(self.pro_monthly.stripe_price_id, '')

    def test_billing_provider_seam_returns_the_stripe_provider(self):
        from ecoiq_commerce.services.billing import (
            StripeBillingProvider, get_billing_provider,
        )
        with override_settings(ECOIQ_BILLING_PROVIDER='stripe'):
            self.assertIsInstance(get_billing_provider(), StripeBillingProvider)

    def test_stripe_provider_refuses_to_start_a_subscription_locally(self):
        """Provisioning must go through Checkout + webhooks, never a local call."""
        from ecoiq_commerce.services.billing import StripeBillingProvider
        with self.assertRaises(NotImplementedError):
            StripeBillingProvider().start_subscription(plan=self.pro_monthly, user=self.user)
        with self.assertRaises(NotImplementedError):
            StripeBillingProvider().cancel_subscription(None)

    def test_no_secret_key_reaches_a_rendered_page(self):
        self.client.force_login(self.user)
        for name in ('billing:plans', 'billing:manage'):
            body = self.client.get(reverse(name)).content.decode()
            self.assertNotIn(TEST_SECRET_KEY, body, name)
            self.assertNotIn(WEBHOOK_SECRET, body, name)
            self.assertNotIn('sk_test', body, name)
            self.assertNotIn('PLACEHOLDER', body, name)
            self.assertNotIn('whsec_', body, name)


# ── Refunds ──────────────────────────────────────────────────────────────────

@override_settings(**STRIPE_TEST_SETTINGS)
class RefundWebhookTests(StripeBillingTestCase):
    """A full refund withdraws access; a partial refund deliberately does not."""

    def setUp(self):
        super().setUp()
        self.record = StripeCheckoutRecord.objects.create(
            session_id='cs_refundable', mode='payment', user=self.user,
            plan=self.assessment, stripe_customer_id='cus_test123',
            stripe_payment_intent_id='pi_refundable',
            amount_total='1500.00', currency='GBP',
            status='completed', access_granted=True)

    def _charge(self, *, refunded=True, amount_refunded=150000, amount_captured=150000):
        return {
            'id': 'ch_refundable', 'object': 'charge',
            'payment_intent': 'pi_refundable', 'currency': 'gbp',
            'amount': 150000, 'amount_captured': amount_captured,
            'amount_refunded': amount_refunded, 'refunded': refunded,
        }

    def test_full_refund_withdraws_access(self):
        response = self.post_webhook(
            event('charge.refunded', self._charge(), event_id='evt_refund'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(StripeEvent.objects.get().status, 'processed')
        self.record.refresh_from_db()
        self.assertFalse(self.record.access_granted)
        self.assertEqual(self.record.revocation_reason, 'refund')

    def test_partial_refund_leaves_access_in_place(self):
        self.post_webhook(event('charge.refunded',
                                self._charge(refunded=False, amount_refunded=50000),
                                event_id='evt_partial'))
        self.record.refresh_from_db()
        self.assertTrue(self.record.access_granted,
                        'a partial refund must not revoke a purchase outright')
        self.assertEqual(self.record.revocation_reason, '')

    def test_refund_is_idempotent(self):
        payload = event('charge.refunded', self._charge(), event_id='evt_refund')
        self.post_webhook(payload)
        self.post_webhook(payload)
        self.assertEqual(StripeEvent.objects.count(), 1)
        self.record.refresh_from_db()
        self.assertFalse(self.record.access_granted)

    def test_refund_for_an_unknown_charge_is_acknowledged_not_retried(self):
        charge = self._charge(); charge['payment_intent'] = 'pi_not_ours'
        response = self.post_webhook(event('charge.refunded', charge, event_id='evt_unknown'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(StripeEvent.objects.get().status, 'ignored')
        self.record.refresh_from_db()
        self.assertTrue(self.record.access_granted)


# ── Disputes ─────────────────────────────────────────────────────────────────

@override_settings(**STRIPE_TEST_SETTINGS)
class DisputeWebhookTests(StripeBillingTestCase):
    """
    A dispute suspends rather than deletes, and a won dispute restores exactly
    what it suspended — never more.
    """

    def setUp(self):
        super().setUp()
        self.record = StripeCheckoutRecord.objects.create(
            session_id='cs_disputed', mode='payment', user=self.user,
            plan=self.assessment, stripe_customer_id='cus_test123',
            stripe_payment_intent_id='pi_disputed',
            status='completed', access_granted=True)

    def _dispute(self, *, status='needs_response', dispute_id='dp_test'):
        return {
            'id': dispute_id, 'object': 'dispute', 'charge': 'ch_disputed',
            'payment_intent': 'pi_disputed', 'amount': 150000, 'currency': 'gbp',
            'reason': 'fraudulent', 'status': status,
        }

    def _open(self):
        return self.post_webhook(event('charge.dispute.created', self._dispute(),
                                        event_id='evt_dispute_open'))

    def test_dispute_created_suspends_access(self):
        self.assertEqual(self._open().status_code, 200)
        self.record.refresh_from_db()
        self.assertFalse(self.record.access_granted)
        self.assertEqual(self.record.revocation_reason, 'dispute')
        row = StripeDispute.objects.get()
        self.assertEqual(row.status, 'open')
        self.assertTrue(row.access_suspended)
        self.assertEqual(row.reason, 'fraudulent')

    def test_dispute_created_is_idempotent(self):
        self._open(); self._open()
        self.assertEqual(StripeDispute.objects.count(), 1)
        self.assertEqual(StripeEvent.objects.count(), 1)

    def test_dispute_won_restores_access(self):
        self._open()
        self.post_webhook(event('charge.dispute.closed', self._dispute(status='won'),
                                 event_id='evt_dispute_won'))
        self.record.refresh_from_db()
        self.assertTrue(self.record.access_granted)
        self.assertEqual(self.record.revocation_reason, '')
        row = StripeDispute.objects.get()
        self.assertEqual(row.status, 'won')
        self.assertFalse(row.access_suspended)
        self.assertIsNotNone(row.closed_at)

    def test_dispute_lost_keeps_access_withdrawn(self):
        self._open()
        self.post_webhook(event('charge.dispute.closed', self._dispute(status='lost'),
                                 event_id='evt_dispute_lost'))
        self.record.refresh_from_db()
        self.assertFalse(self.record.access_granted)
        self.assertEqual(StripeDispute.objects.get().status, 'lost')

    def test_dispute_closed_is_idempotent(self):
        self._open()
        payload = event('charge.dispute.closed', self._dispute(status='won'),
                        event_id='evt_dispute_won')
        self.post_webhook(payload); self.post_webhook(payload)
        self.assertEqual(StripeEvent.objects.count(), 2)
        self.assertEqual(StripeDispute.objects.get().status, 'won')

    def test_won_dispute_never_resurrects_a_refunded_purchase(self):
        """Restoration is scoped to what THIS dispute revoked."""
        self._open()
        self.record.refresh_from_db()
        self.record.revocation_reason = 'refund'      # refunded while disputed
        self.record.save(update_fields=['revocation_reason'])

        self.post_webhook(event('charge.dispute.closed', self._dispute(status='won'),
                                 event_id='evt_dispute_won'))
        self.record.refresh_from_db()
        self.assertFalse(self.record.access_granted,
                         'a won dispute resurrected a refunded purchase')

    def test_closed_without_a_recorded_open_is_acknowledged_not_retried(self):
        response = self.post_webhook(
            event('charge.dispute.closed', self._dispute(status='won'),
                  event_id='evt_orphan_close'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(StripeEvent.objects.get().status, 'ignored')


@override_settings(**STRIPE_TEST_SETTINGS)
@patch('ecoiq_commerce.services.entitlements.timezone.now', new=lambda: FROZEN_NOW)
class SubscriptionDisputeTests(StripeBillingTestCase):
    """A dispute against a subscription invoice suspends and restores exactly."""

    def setUp(self):
        super().setUp()
        self.post_webhook(event('customer.subscription.created',
                                subscription_payload(metadata={'ecoiq_user_id': str(self.user.pk)}),
                                event_id='evt_sub'))
        self.post_webhook(event('invoice.paid', {
            'id': 'in_disputed', 'object': 'invoice', 'customer': 'cus_test123',
            'currency': 'gbp', 'total': 9900, 'total_taxes': [],
            'payment_intent': 'pi_sub_invoice',
            'status_transitions': {'finalized_at': DEFAULT_PERIOD_START, 'paid_at': DEFAULT_PERIOD_START + 100},
            'parent': {'subscription_details': {'subscription': 'sub_test123'}},
            'metadata': {'ecoiq_user_id': str(self.user.pk)},
        }, event_id='evt_inv'))

    def _dispute(self, status='needs_response'):
        return {'id': 'dp_sub', 'object': 'dispute', 'charge': 'ch_sub',
                'payment_intent': 'pi_sub_invoice', 'amount': 9900,
                'currency': 'gbp', 'reason': 'fraudulent', 'status': status}

    def test_invoice_records_its_payment_intent(self):
        self.assertEqual(Invoice.objects.get().external_payment_intent_id, 'pi_sub_invoice')

    def test_dispute_suspends_the_subscription_and_withdraws_entitlement(self):
        self.assertTrue(has_entitlement(self.user, 'evidence_access').allowed)
        self.post_webhook(event('charge.dispute.created', self._dispute(),
                                 event_id='evt_sub_dispute'))
        self.assertEqual(Subscription.objects.get().status, 'past_due')
        self.assertFalse(has_entitlement(self.user, 'evidence_access').allowed)
        self.assertEqual(StripeDispute.objects.get().previous_subscription_status, 'active')

    def test_won_dispute_restores_the_previous_status(self):
        self.post_webhook(event('charge.dispute.created', self._dispute(),
                                 event_id='evt_sub_dispute'))
        self.post_webhook(event('charge.dispute.closed', self._dispute('won'),
                                 event_id='evt_sub_dispute_won'))
        self.assertEqual(Subscription.objects.get().status, 'active')
        self.assertTrue(has_entitlement(self.user, 'evidence_access').allowed)

    def test_won_dispute_does_not_reactivate_an_independently_cancelled_sub(self):
        """
        The subscription was cancelled for unrelated reasons while the dispute
        was open. Winning the dispute must not resurrect it.
        """
        self.post_webhook(event('charge.dispute.created', self._dispute(),
                                 event_id='evt_sub_dispute'))
        self.post_webhook(event('customer.subscription.deleted',
                                subscription_payload(status='canceled', canceled_at=DEFAULT_PERIOD_END,
                                                     metadata={'ecoiq_user_id': str(self.user.pk)}),
                                event_id='evt_sub_deleted'))
        self.assertEqual(Subscription.objects.get().status, 'cancelled')

        self.post_webhook(event('charge.dispute.closed', self._dispute('won'),
                                 event_id='evt_sub_dispute_won'))
        sub = Subscription.objects.get()
        self.assertEqual(sub.status, 'cancelled',
                         'a won dispute reactivated a cancelled subscription')
        self.assertFalse(has_entitlement(self.user, 'evidence_access').allowed)


# ── One provider, one source of truth ────────────────────────────────────────

@override_settings(**STRIPE_TEST_SETTINGS)
class BillingProviderExclusivityTests(StripeBillingTestCase):
    """Only the configured provider may write billing records."""

    def _invoice(self):
        return {'id': 'in_exclusive', 'object': 'invoice', 'customer': 'cus_test123',
                'currency': 'gbp', 'total': 9900, 'total_taxes': [],
                'status_transitions': {'finalized_at': DEFAULT_PERIOD_START, 'paid_at': DEFAULT_PERIOD_START + 100},
                'metadata': {'ecoiq_user_id': str(self.user.pk)}}

    def test_null_provider_cannot_write_while_stripe_is_configured(self):
        from ecoiq_commerce.services.billing import (
            NullBillingProvider, WrongBillingProvider,
        )
        provider = NullBillingProvider()
        with self.assertRaises(WrongBillingProvider):
            provider.get_or_create_customer(user=self.user)
        with self.assertRaises(WrongBillingProvider):
            provider.start_subscription(plan=self.pro_monthly, user=self.user)
        with self.assertRaises(WrongBillingProvider):
            provider.issue_invoice(billing_customer=None, line_items=[])

    @override_settings(ECOIQ_BILLING_PROVIDER='none')
    def test_stripe_cannot_write_while_null_is_configured(self):
        response = self.post_webhook(event('invoice.paid', self._invoice(),
                                            event_id='evt_wrong_provider'))
        self.assertEqual(response.status_code, 500,
                         'a misconfiguration must fail loudly, not write silently')
        self.assertEqual(Invoice.objects.count(), 0)

    def test_one_charge_produces_exactly_one_invoice(self):
        self.post_webhook(event('invoice.paid', self._invoice(), event_id='evt_a'))
        self.post_webhook(event('invoice.paid', self._invoice(), event_id='evt_b'))
        self.assertEqual(Invoice.objects.filter(external_invoice_id='in_exclusive').count(), 1)

    def test_get_billing_provider_returns_exactly_one(self):
        from ecoiq_commerce.services.billing import (
            NullBillingProvider, StripeBillingProvider, get_billing_provider,
        )
        self.assertIsInstance(get_billing_provider(), StripeBillingProvider)
        with override_settings(ECOIQ_BILLING_PROVIDER='none'):
            self.assertIsInstance(get_billing_provider(), NullBillingProvider)


# ── Discounts: one source of truth per payment flow ──────────────────────────

@override_settings(**STRIPE_TEST_SETTINGS)
class DiscountSourceOfTruthTests(StripeBillingTestCase):
    """Stripe Checkout uses Stripe promotion codes; local Coupons never apply."""

    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_checkout_enables_stripe_promotion_codes(self):
        with patch('stripe.Customer.create', return_value={'id': 'cus_test123'}), \
             patch('stripe.checkout.Session.create',
                   return_value={'id': 'cs_promo', 'url': 'https://x'}) as create:
            self.client.post(reverse('billing:checkout_subscription'),
                             {'tier': 'pro', 'interval': 'monthly'})
        self.assertTrue(create.call_args.kwargs['allow_promotion_codes'])

    def test_a_local_coupon_never_reaches_a_stripe_checkout(self):
        from ecoiq_commerce.models import Coupon
        Coupon.objects.create(code='HALFOFF', discount_type='percent', value=50)
        with patch('stripe.Customer.create', return_value={'id': 'cus_test123'}), \
             patch('stripe.checkout.Session.create',
                   return_value={'id': 'cs_promo', 'url': 'https://x'}) as create:
            self.client.post(reverse('billing:checkout_subscription'),
                             {'tier': 'pro', 'interval': 'monthly', 'coupon': 'HALFOFF'})
        kwargs = create.call_args.kwargs
        self.assertNotIn('discounts', kwargs)
        self.assertNotIn('coupon', kwargs)
        self.assertEqual(kwargs['line_items'], [{'price': 'price_pro_monthly', 'quantity': 1}])

    def test_coupons_are_scoped_to_manual_billing(self):
        from ecoiq_commerce.models import Coupon
        self.assertEqual(Coupon.objects.create(code='X', discount_type='percent',
                                                value=10).scope, 'manual')

    def test_stripe_gateway_does_not_read_the_coupon_table(self):
        import inspect
        from ecoiq_commerce.services import stripe_gateway
        self.assertNotIn('Coupon', inspect.getsource(stripe_gateway))


# ── The fixture clock itself ─────────────────────────────────────────────────

@override_settings(**STRIPE_TEST_SETTINGS)
class FixtureClockTests(StripeBillingTestCase):
    """
    Guards the bug that produced this class.

    Six entitlement tests passed for months and then failed permanently, on
    unchanged code, because `period_end` was an absolute epoch and real time
    crossed it (see the fixed-clock note at the top of this module). These
    assert the property that makes that impossible to repeat: the fixture is
    defined relative to a frozen clock, and the entitlement code reads that
    same frozen clock.
    """

    def _create(self, **kwargs):
        return self.post_webhook(event(
            'customer.subscription.created',
            subscription_payload(metadata={'ecoiq_user_id': str(self.user.pk)}, **kwargs)))

    def test_fixture_period_is_relative_to_the_frozen_clock(self):
        item = subscription_payload()['items']['data'][0]
        self.assertEqual(item['current_period_start'], FROZEN_EPOCH - PERIOD_BEHIND_SECONDS)
        self.assertEqual(item['current_period_end'], FROZEN_EPOCH + PERIOD_AHEAD_SECONDS)

    def test_fixture_straddles_the_frozen_clock(self):
        """Live at 'now': started in the past, ends in the future."""
        item = subscription_payload()['items']['data'][0]
        self.assertLess(item['current_period_start'], FROZEN_EPOCH)
        self.assertGreater(item['current_period_end'], FROZEN_EPOCH)

    def test_no_absolute_epoch_literal_survives_in_the_fixtures(self):
        """
        A hardcoded epoch is a date that will arrive. Comments may mention the
        old values; executable lines may not reintroduce them.
        """
        import re
        from pathlib import Path

        source = Path(__file__).read_text(encoding='utf-8')
        offenders = [
            (n, line) for n, line in enumerate(source.splitlines(), 1)
            if not line.lstrip().startswith('#') and re.search(r'\b1[6-9]\d{8}\b', line)
        ]
        self.assertEqual(offenders, [], f'absolute epoch literal reintroduced: {offenders}')

    @patch('ecoiq_commerce.services.entitlements.timezone.now', new=lambda: FROZEN_NOW)
    def test_active_period_is_allowed_before_the_end(self):
        self._create()
        self.assertTrue(has_entitlement(self.user, 'evidence_access').allowed)

    @patch('ecoiq_commerce.services.entitlements.timezone.now', new=lambda: FROZEN_NOW)
    def test_expired_period_is_denied_after_the_end(self):
        """The real rule, asserted directly rather than inferred."""
        self._create(period_start=FROZEN_EPOCH - 60 * 24 * 3600,
                     period_end=FROZEN_EPOCH - 1)
        self.assertFalse(has_entitlement(self.user, 'evidence_access').allowed)

    @patch('ecoiq_commerce.services.entitlements.timezone.now', new=lambda: FROZEN_NOW)
    def test_boundary_exactly_at_period_end_is_denied(self):
        """
        `entitlements._active_subscription_qs` filters `current_period_end__gt=now`,
        so the instant the period ends is already outside it. Pinned explicitly
        because `gt` versus `gte` here is one character and a day of access.
        """
        self._create(period_start=FROZEN_EPOCH - 30 * 24 * 3600,
                     period_end=FROZEN_EPOCH)
        self.assertFalse(has_entitlement(self.user, 'evidence_access').allowed)

    def test_outcome_does_not_depend_on_the_wall_clock(self):
        """
        The regression test proper: run the same fixture against an entitlement
        clock set a decade apart and confirm the verdict is decided by the
        frozen clock, not by today's date.

        Under the old fixture this was impossible — the verdict flipped the
        moment real time passed a fixed epoch.
        """
        self._create()
        far_future = FROZEN_NOW + datetime.timedelta(days=3650)
        with patch('ecoiq_commerce.services.entitlements.timezone.now', new=lambda: FROZEN_NOW):
            self.assertTrue(has_entitlement(self.user, 'evidence_access').allowed)
        with patch('ecoiq_commerce.services.entitlements.timezone.now', new=lambda: far_future):
            self.assertFalse(has_entitlement(self.user, 'evidence_access').allowed)
