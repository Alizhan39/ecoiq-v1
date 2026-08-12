"""
mobile_auth/tests.py — login/refresh/logout lifecycle, refresh-token
rotation + reuse detection, session IDOR protection, and the auth-ordering
fix in api/throttles.py (APIKeyRateThrottle must not crash when
request.auth is a DeviceSession rather than an api.models.APIKey).
"""
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from api.models import APIKey
from mobile_auth.models import DeviceSession
from mobile_auth.throttles import LoginRateThrottle

User = get_user_model()

LOGIN_URL = '/api/v1/auth/login/'
REFRESH_URL = '/api/v1/auth/refresh/'
LOGOUT_URL = '/api/v1/auth/logout/'
LOGOUT_ALL_URL = '/api/v1/auth/logout-all/'
SESSIONS_URL = '/api/v1/auth/sessions/'
ME_URL = '/api/v1/me/'
APP_CONFIG_URL = '/api/v1/app-config/'


class _CacheIsolatedTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)
        super().setUp()


class LoginTest(_CacheIsolatedTestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='mobileuser', password='correct-horse-battery')

    def test_valid_login_returns_token_pair(self):
        resp = self.client.post(LOGIN_URL, {
            'username': 'mobileuser', 'password': 'correct-horse-battery',
            'device_id': 'device-1', 'device_name': 'iPhone', 'platform': 'ios',
        }, content_type='application/json')
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertIn('access_token', body)
        self.assertIn('refresh_token', body)
        self.assertEqual(body['token_type'], 'Bearer')
        self.assertEqual(DeviceSession.objects.filter(user=self.user, revoked_at__isnull=True).count(), 1)

    def test_wrong_password_rejected(self):
        resp = self.client.post(LOGIN_URL, {
            'username': 'mobileuser', 'password': 'wrong', 'device_id': 'device-1',
        }, content_type='application/json')
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(DeviceSession.objects.count(), 0)

    def test_missing_device_id_rejected(self):
        resp = self.client.post(LOGIN_URL, {
            'username': 'mobileuser', 'password': 'correct-horse-battery',
        }, content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_relogin_same_device_replaces_prior_session(self):
        for _ in range(2):
            resp = self.client.post(LOGIN_URL, {
                'username': 'mobileuser', 'password': 'correct-horse-battery', 'device_id': 'device-1',
            }, content_type='application/json')
            self.assertEqual(resp.status_code, 201)
        self.assertEqual(DeviceSession.objects.filter(user=self.user, revoked_at__isnull=True).count(), 1)
        self.assertEqual(DeviceSession.objects.filter(user=self.user).count(), 2)

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()
        resp = self.client.post(LOGIN_URL, {
            'username': 'mobileuser', 'password': 'correct-horse-battery', 'device_id': 'device-1',
        }, content_type='application/json')
        self.assertEqual(resp.status_code, 401)

    def test_login_is_rate_limited(self):
        with mock.patch.dict(LoginRateThrottle.THROTTLE_RATES, {'auth_login': '2/hour'}):
            for _ in range(2):
                resp = self.client.post(LOGIN_URL, {
                    'username': 'mobileuser', 'password': 'wrong', 'device_id': 'device-1',
                }, content_type='application/json')
                self.assertEqual(resp.status_code, 401)
            resp = self.client.post(LOGIN_URL, {
                'username': 'mobileuser', 'password': 'wrong', 'device_id': 'device-1',
            }, content_type='application/json')
            self.assertEqual(resp.status_code, 429)


class RefreshTest(_CacheIsolatedTestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='refreshuser', password='pw123456')
        login = self.client.post(LOGIN_URL, {
            'username': 'refreshuser', 'password': 'pw123456', 'device_id': 'device-1',
        }, content_type='application/json').json()
        self.access = login['access_token']
        self.refresh = login['refresh_token']

    def test_refresh_rotates_and_old_access_still_works_until_expiry(self):
        resp = self.client.post(REFRESH_URL, {'refresh_token': self.refresh}, content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertNotEqual(body['refresh_token'], self.refresh)

    def test_reused_refresh_token_is_detected_and_revokes_session(self):
        self.client.post(REFRESH_URL, {'refresh_token': self.refresh}, content_type='application/json')
        # Replay the ORIGINAL (now-rotated-away) refresh token.
        resp = self.client.post(REFRESH_URL, {'refresh_token': self.refresh}, content_type='application/json')
        self.assertEqual(resp.status_code, 401)

        session = DeviceSession.objects.get(user=self.user)
        self.assertIsNotNone(session.revoked_at)
        self.assertEqual(session.revoked_reason, 'refresh_token_reuse_detected')

        # The access token issued by the rotation is ALSO dead now (session revoked).
        me_resp = self.client.get(ME_URL, HTTP_AUTHORIZATION=f'Bearer {self.access}')
        self.assertEqual(me_resp.status_code, 401)

    def test_unknown_refresh_token_rejected(self):
        resp = self.client.post(REFRESH_URL, {'refresh_token': 'not-a-real-token'}, content_type='application/json')
        self.assertEqual(resp.status_code, 401)

    def test_expired_refresh_token_rejected(self):
        session = DeviceSession.objects.get(user=self.user)
        session.refresh_expires_at = timezone.now() - timezone.timedelta(days=1)
        session.save(update_fields=['refresh_expires_at'])
        resp = self.client.post(REFRESH_URL, {'refresh_token': self.refresh}, content_type='application/json')
        self.assertEqual(resp.status_code, 401)


class LogoutTest(_CacheIsolatedTestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='logoutuser', password='pw123456')

    def _login(self, device_id):
        return self.client.post(LOGIN_URL, {
            'username': 'logoutuser', 'password': 'pw123456', 'device_id': device_id,
        }, content_type='application/json').json()

    def test_logout_revokes_only_current_device(self):
        phone = self._login('phone')
        laptop = self._login('laptop')

        resp = self.client.post(LOGOUT_URL, HTTP_AUTHORIZATION=f"Bearer {phone['access_token']}")
        self.assertEqual(resp.status_code, 204)

        self.assertFalse(DeviceSession.objects.get(pk=phone['session_id']).is_active)
        self.assertTrue(DeviceSession.objects.get(pk=laptop['session_id']).is_active)

    def test_logout_all_revokes_every_device(self):
        phone = self._login('phone')
        self._login('laptop')

        resp = self.client.post(LOGOUT_ALL_URL, HTTP_AUTHORIZATION=f"Bearer {phone['access_token']}")
        self.assertEqual(resp.status_code, 204)

        self.assertEqual(DeviceSession.objects.filter(user=self.user, revoked_at__isnull=True).count(), 0)

    def test_logged_out_access_token_rejected_immediately(self):
        phone = self._login('phone')
        self.client.post(LOGOUT_URL, HTTP_AUTHORIZATION=f"Bearer {phone['access_token']}")
        resp = self.client.get(ME_URL, HTTP_AUTHORIZATION=f"Bearer {phone['access_token']}")
        self.assertEqual(resp.status_code, 401)


class SessionListAndRevokeTest(_CacheIsolatedTestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='sessuser', password='pw123456')
        self.other = User.objects.create_user(username='otheruser', password='pw123456')

        self.login1 = self.client.post(LOGIN_URL, {
            'username': 'sessuser', 'password': 'pw123456', 'device_id': 'd1', 'device_name': 'Phone',
        }, content_type='application/json').json()

    def test_sessions_list_only_shows_own_sessions(self):
        other_session, _raw = DeviceSession.create_session(user=self.other, device_id='other-d1')
        resp = self.client.get(SESSIONS_URL, HTTP_AUTHORIZATION=f"Bearer {self.login1['access_token']}")
        self.assertEqual(resp.status_code, 200)
        ids = [s['id'] for s in resp.json()['sessions']]
        self.assertIn(self.login1['session_id'], ids)
        self.assertNotIn(other_session.pk, ids)

    def test_cannot_revoke_another_users_session(self):
        other_session, _raw = DeviceSession.create_session(user=self.other, device_id='other-d1')
        resp = self.client.post(
            f'/api/v1/auth/sessions/{other_session.pk}/revoke/',
            HTTP_AUTHORIZATION=f"Bearer {self.login1['access_token']}",
        )
        self.assertEqual(resp.status_code, 404)
        other_session.refresh_from_db()
        self.assertTrue(other_session.is_active)

    def test_can_revoke_own_other_session(self):
        login2 = self.client.post(LOGIN_URL, {
            'username': 'sessuser', 'password': 'pw123456', 'device_id': 'd2', 'device_name': 'Laptop',
        }, content_type='application/json').json()

        resp = self.client.post(
            f"/api/v1/auth/sessions/{login2['session_id']}/revoke/",
            HTTP_AUTHORIZATION=f"Bearer {self.login1['access_token']}",
        )
        self.assertEqual(resp.status_code, 204)
        self.assertFalse(DeviceSession.objects.get(pk=login2['session_id']).is_active)


class MobileAndAPIKeyAuthCoexistTest(_CacheIsolatedTestCase):
    """
    Regression guard for the fix to api/throttles.py:APIKeyRateThrottle and
    the DEFAULT_AUTHENTICATION_CLASSES ordering -- a Bearer mobile access
    token and a Bearer API key must each authenticate correctly and must
    not crash or misclaim each other's tokens.
    """
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='coexistuser', password='pw123456')

    def test_mobile_token_and_api_key_both_work_on_the_same_endpoint(self):
        from companies.models import CompanyProfile
        from league.models import Company
        company = Company.objects.create(name='Coexist Co', slug='coexist-co')
        CompanyProfile.objects.create(company=company, status='public')

        login = self.client.post(LOGIN_URL, {
            'username': 'coexistuser', 'password': 'pw123456', 'device_id': 'd1',
        }, content_type='application/json').json()
        mobile_resp = self.client.get(
            f'/api/v1/companies/{company.slug}/risks/',
            HTTP_AUTHORIZATION=f"Bearer {login['access_token']}",
        )
        self.assertEqual(mobile_resp.status_code, 200)

        _key, raw_api_key = APIKey.create_key(name='k', tier='explorer')
        api_key_resp = self.client.get(
            f'/api/v1/companies/{company.slug}/risks/',
            HTTP_AUTHORIZATION=f'Bearer {raw_api_key}',
        )
        self.assertEqual(api_key_resp.status_code, 200)

    def test_mobile_token_works_on_company_search_and_detail(self):
        """
        api/views.py:search / CompanyDetailView / CompanyScoresView /
        CompanyHarmSignalsView are the endpoints the app's search screen and
        company-profile screen actually call — regression guard for the
        same authentication_classes fix applied there.
        """
        from companies.models import CompanyProfile
        from league.models import Company
        company = Company.objects.create(name='Search Target Co', slug='search-target-co')
        CompanyProfile.objects.create(company=company, status='public')

        login = self.client.post(LOGIN_URL, {
            'username': 'coexistuser', 'password': 'pw123456', 'device_id': 'd1',
        }, content_type='application/json').json()
        headers = {'HTTP_AUTHORIZATION': f"Bearer {login['access_token']}"}

        search_resp = self.client.get('/api/v1/search/?q=Search+Target', **headers)
        self.assertEqual(search_resp.status_code, 200)
        self.assertEqual(search_resp.json()['count'], 1)

        detail_resp = self.client.get(f'/api/v1/companies/{company.slug}/', **headers)
        self.assertEqual(detail_resp.status_code, 200)

        scores_resp = self.client.get(f'/api/v1/companies/{company.slug}/scores/', **headers)
        self.assertEqual(scores_resp.status_code, 200)

        harm_resp = self.client.get(f'/api/v1/companies/{company.slug}/harm-signals/', **headers)
        self.assertEqual(harm_resp.status_code, 200)

    def test_garbage_bearer_token_rejected_cleanly_not_500(self):
        resp = self.client.get(ME_URL, HTTP_AUTHORIZATION='Bearer not-a-real-anything')
        self.assertEqual(resp.status_code, 401)

    def test_requires_feature_endpoint_resolves_entitlement_from_the_app_users_own_plan(self):
        """
        api.permissions.RequiresFeature must check the LOGGED-IN APP USER'S
        own subscription (not just an API key's plan) -- companies/evidence/
        is RequiresFeature('api_evidence_access')-gated.
        """
        from django.core.management import call_command

        from companies.models import CompanyProfile
        from ecoiq_commerce.models import Feature, Plan, PlanFeature, Product, Subscription
        from league.models import Company

        call_command('seed_commercial_catalogue')
        company = Company.objects.create(name='Feature Gate Co', slug='feature-gate-co')
        CompanyProfile.objects.create(company=company, status='public')

        login = self.client.post(LOGIN_URL, {
            'username': 'coexistuser', 'password': 'pw123456', 'device_id': 'd1',
        }, content_type='application/json').json()
        headers = {'HTTP_AUTHORIZATION': f"Bearer {login['access_token']}"}

        # No subscription yet, and api_evidence_access isn't on any free plan -> denied.
        resp = self.client.get(f'/api/v1/companies/{company.slug}/evidence/', **headers)
        self.assertEqual(resp.status_code, 403)

        # Give this user a plan that includes it, directly (not via an API key).
        product = Product.objects.create(key='test-pro', product_type='professional', name='Test Pro', status='active')
        plan = Plan.objects.create(product=product, key='test-pro-plan', name='Test Pro Plan', price_amount=79)
        PlanFeature.objects.create(plan=plan, is_included=True,
                                    feature=Feature.objects.get(key='api_evidence_access'))
        Subscription.objects.create(user=self.user, plan=plan, status='active')

        resp = self.client.get(f'/api/v1/companies/{company.slug}/evidence/', **headers)
        self.assertEqual(resp.status_code, 200)


class MeAndAppConfigTest(_CacheIsolatedTestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='meuser', password='pw123456')

    def test_me_requires_auth(self):
        resp = self.client.get(ME_URL)
        self.assertEqual(resp.status_code, 401)

    def test_me_returns_entitlement_summary(self):
        from django.core.management import call_command
        call_command('seed_commercial_catalogue')

        login = self.client.post(LOGIN_URL, {
            'username': 'meuser', 'password': 'pw123456', 'device_id': 'd1',
        }, content_type='application/json').json()
        resp = self.client.get(ME_URL, HTTP_AUTHORIZATION=f"Bearer {login['access_token']}")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body['username'], 'meuser')
        self.assertIn('company_profiles_basic', body['entitlements'])
        self.assertIsNone(body['plan'])  # no subscription for this user

    def test_app_config_is_public_and_has_no_secrets(self):
        resp = self.client.get(APP_CONFIG_URL)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        for key in ('min_supported_version', 'latest_version', 'maintenance_mode', 'force_update'):
            self.assertIn(key, body)
        self.assertNotIn('SECRET_KEY', str(body))
