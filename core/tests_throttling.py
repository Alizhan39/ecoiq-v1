"""
Tests for the trusted throttle identity and the auth-view rate limits.

The property under test is WHO a throttle counts against. A rate limit keyed on
a string the caller controls is not a rate limit, and the failure is silent:
every request looks allowed because every request is a new bucket.
"""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from core.throttling import TrustedAnonRateThrottle, TrustedIdentThrottleMixin

CF = 'CF-Connecting-IP'


class _Req:
    """Minimal request stand-in: only META matters to get_ident."""

    def __init__(self, **meta):
        self.META = meta


class TrustedIdentTests(SimpleTestCase):

    def setUp(self):
        self.throttle = TrustedAnonRateThrottle()

    @override_settings(TRUSTED_CLIENT_IP_HEADER='CF-Connecting-IP', TRUSTED_PROXY_COUNT=2)
    def test_forged_forwarded_entries_do_not_change_the_identity(self):
        """
        The bug this exists to fix. DRF's get_ident returns the whole
        X-Forwarded-For chain when NUM_PROXIES is unset, so prepending junk
        produced a brand-new bucket and no limit at all.
        """
        base = self.throttle.get_ident(_Req(
            HTTP_CF_CONNECTING_IP='203.0.113.5',
            HTTP_X_FORWARDED_FOR='203.0.113.5, 172.16.0.1',
            REMOTE_ADDR='10.0.0.1'))
        forged = self.throttle.get_ident(_Req(
            HTTP_CF_CONNECTING_IP='203.0.113.5',
            HTTP_X_FORWARDED_FOR='1.2.3.4, 5.6.7.8, 203.0.113.5, 172.16.0.1',
            REMOTE_ADDR='10.0.0.1'))
        self.assertEqual(base, forged)
        self.assertEqual(base, '203.0.113.5')

    @override_settings(TRUSTED_CLIENT_IP_HEADER='CF-Connecting-IP', TRUSTED_PROXY_COUNT=2)
    def test_different_real_clients_get_different_identities(self):
        """A limiter that buckets everyone together is also broken."""
        a = self.throttle.get_ident(_Req(HTTP_CF_CONNECTING_IP='203.0.113.5'))
        b = self.throttle.get_ident(_Req(HTTP_CF_CONNECTING_IP='198.51.100.9'))
        self.assertNotEqual(a, b)

    @override_settings(TRUSTED_CLIENT_IP_HEADER='', TRUSTED_PROXY_COUNT=2)
    def test_falls_back_to_counting_from_the_right_of_the_chain(self):
        """Without the Cloudflare header, the trusted hop count is used."""
        ident = self.throttle.get_ident(_Req(
            HTTP_X_FORWARDED_FOR='1.2.3.4, 203.0.113.5, 172.16.0.1',
            REMOTE_ADDR='10.0.0.1'))
        self.assertNotIn('1.2.3.4', ident)

    def test_unresolvable_origin_shares_one_bucket_rather_than_being_waved_through(self):
        ident = self.throttle.get_ident(_Req())
        self.assertEqual(ident, 'unknown')

    def test_mixin_precedes_the_drf_class_in_the_mro(self):
        """
        If the mixin were second, DRF's get_ident would win and every other
        test here would pass while production stayed broken.
        """
        mro = TrustedAnonRateThrottle.__mro__
        self.assertLess(mro.index(TrustedIdentThrottleMixin),
                        mro.index(__import__('rest_framework.throttling',
                                             fromlist=['AnonRateThrottle']).AnonRateThrottle))

    def test_every_ip_keyed_throttle_uses_the_trusted_mixin(self):
        """
        A new throttle added without the mixin is silently unlimited behind
        Cloudflare. This enumerates them so that is caught here, not in prod.
        """
        from ai_gateway.throttles import (AIChatIPThrottle, AIChatUserThrottle,
                                          AICatalogThrottle)
        from api.throttles import APIKeyRateThrottle
        from mobile_auth.throttles import LoginRateThrottle

        for cls in (AIChatIPThrottle, AIChatUserThrottle, AICatalogThrottle,
                    APIKeyRateThrottle, LoginRateThrottle, TrustedAnonRateThrottle):
            self.assertTrue(issubclass(cls, TrustedIdentThrottleMixin),
                            f'{cls.__name__} does not use the trusted identity')

    def test_settings_registers_the_trusted_anon_throttle(self):
        from django.conf import settings

        classes = settings.REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES']
        self.assertIn('core.throttling.TrustedAnonRateThrottle', classes)
        self.assertNotIn('rest_framework.throttling.AnonRateThrottle', classes)


@override_settings(TRUSTED_CLIENT_IP_HEADER='CF-Connecting-IP', TRUSTED_PROXY_COUNT=2)
class AuthViewRateLimitTests(TestCase):
    """The sign-in and registration forms were previously unlimited."""

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _post_login(self, ip='203.0.113.5'):
        return self.client.post(reverse('login'),
                                {'username': 'nobody', 'password': 'wrong'},
                                **{'HTTP_CF_CONNECTING_IP': ip})

    @override_settings(LOGIN_RATE_PER_MIN=3)
    def test_login_is_rate_limited(self):
        codes = [self._post_login().status_code for _ in range(5)]
        self.assertEqual(codes[-1], 429, f'login never throttled: {codes}')

    @override_settings(LOGIN_RATE_PER_MIN=3)
    def test_login_429_carries_retry_after(self):
        for _ in range(5):
            response = self._post_login()
        self.assertEqual(response.status_code, 429)
        self.assertIn('Retry-After', response)
        self.assertGreater(int(response['Retry-After']), 0)

    @override_settings(LOGIN_RATE_PER_MIN=3)
    def test_login_limit_is_per_address_not_shared_globally(self):
        """
        One person hitting their limit must not lock out everyone else — and
        because this throttles an ADDRESS, never an account, an attacker cannot
        lock a named user out by attacking them.
        """
        for _ in range(5):
            self._post_login(ip='203.0.113.5')
        other = self._post_login(ip='198.51.100.9')
        self.assertNotEqual(other.status_code, 429)

    @override_settings(LOGIN_RATE_PER_MIN=3)
    def test_forged_forwarded_header_does_not_reset_the_login_limit(self):
        for _ in range(5):
            self._post_login(ip='203.0.113.5')
        evaded = self.client.post(
            reverse('login'), {'username': 'nobody', 'password': 'wrong'},
            HTTP_CF_CONNECTING_IP='203.0.113.5',
            HTTP_X_FORWARDED_FOR='9.9.9.9, 8.8.8.8, 203.0.113.5, 172.16.0.1')
        self.assertEqual(evaded.status_code, 429)

    @override_settings(LOGIN_RATE_PER_MIN=3)
    def test_staff_are_not_exempt_from_the_login_limit(self):
        """
        Exempting staff from a PDF throttle is sensible. Exempting them here
        would be meaningless — the attacker is not signed in as anybody.
        """
        User = get_user_model()
        User.objects.create_superuser('rlstaff', 'rlstaff@example.invalid', 'pw-not-real-123')
        c = Client()
        c.login(username='rlstaff', password='pw-not-real-123')
        codes = [c.post(reverse('login'), {'username': 'x', 'password': 'y'},
                        HTTP_CF_CONNECTING_IP='203.0.113.7').status_code
                 for _ in range(5)]
        self.assertIn(429, codes)

    @override_settings(REGISTER_RATE_PER_MIN=2)
    def test_registration_is_rate_limited(self):
        codes = [self.client.get(reverse('register'),
                                 HTTP_CF_CONNECTING_IP='203.0.113.8').status_code
                 for _ in range(4)]
        self.assertEqual(codes[-1], 429, f'registration never throttled: {codes}')

    def test_a_normal_sign_in_attempt_is_not_throttled(self):
        """Ordinary pilot use must not trip these."""
        self.assertNotEqual(self._post_login().status_code, 429)


class RateLimitLoggingTests(TestCase):
    """A throttled request must be logged without the raw address."""

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    @override_settings(LOGIN_RATE_PER_MIN=1, TRUSTED_CLIENT_IP_HEADER='CF-Connecting-IP',
                       TRUSTED_PROXY_COUNT=2)
    def test_throttle_event_does_not_log_the_raw_client_address(self):
        with patch('companies.throttle.logger') as log:
            for _ in range(3):
                self.client.post(reverse('login'), {'username': 'a', 'password': 'b'},
                                 HTTP_CF_CONNECTING_IP='203.0.113.55')
        emitted = ' '.join(str(c) for c in log.info.call_args_list)
        self.assertNotIn('203.0.113.55', emitted)
        self.assertTrue(log.info.called, 'a throttled request emitted no event')
