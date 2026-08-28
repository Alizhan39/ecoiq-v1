"""
The anonymous rate limit has to permit reading the site.

20/day was a DATA-API quota, set when /api/ was something a third party called
deliberately. The frontend migration made API v2 the way the WEBSITE renders,
so every visitor began spending a developer quota to read pages — and after
roughly five to seven page views /companies/ showed "Could not load this
section" for the rest of the day.

Observed in production before the fix: Retry-After 22248 seconds.
"""
from django.test import TestCase
from rest_framework.settings import api_settings

#: What the SPA fetches while a person reads the site. Every one is a DRF view
#: and therefore spends the anonymous allowance.
SPA_ENDPOINTS = (
    '/api/v2/platform/',
    '/api/v2/companies/',
    '/api/v2/projects/',
    '/api/v2/leaderboard/',
)


class AnonThrottleRateTests(TestCase):

    def _rate(self):
        return api_settings.DEFAULT_THROTTLE_RATES['anon']

    def test_the_anonymous_rate_is_not_a_daily_quota(self):
        """
        A daily bucket means a visitor who exhausts it sees a broken site until
        midnight, and recovers no faster by waiting sensibly.
        """
        self.assertFalse(self._rate().endswith('/day'),
                         f'anon rate {self._rate()!r} is a daily quota again')

    def test_a_reading_session_fits_well_inside_the_allowance(self):
        """
        Two to four calls per page view. A person reading thirty pages must not
        be throttled, and a shared address carries several such people.
        """
        count, _, period = self._rate().partition('/')
        self.assertGreaterEqual(
            int(count), 120,
            f'anon rate {self._rate()!r} is too small for ordinary browsing')
        self.assertEqual(period, 'hour')

    def test_api_key_tiers_are_untouched(self):
        """
        The real data-API quotas live on the keyed tiers. Loosening the
        browsing rate must not loosen those.
        """
        rates = api_settings.DEFAULT_THROTTLE_RATES
        self.assertEqual(rates['explorer'], '100/day')
        self.assertEqual(rates['professional'], '2000/day')
        self.assertEqual(rates['enterprise'], '50000/day')


class ThrottleStillEngagesTests(TestCase):
    """
    Loosening the number must not disable the control. Asserted against the
    throttle class itself rather than by hammering a view: DRF caches parsed
    rates at import, so override_settings does not reliably reach it, and a
    test that silently stopped exercising the throttle would be worse than none.
    """

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def test_the_anonymous_throttle_is_installed(self):
        from rest_framework.settings import api_settings
        names = [c.__name__ for c in api_settings.DEFAULT_THROTTLE_CLASSES]
        self.assertIn('TrustedAnonRateThrottle', names)

    def test_the_throttle_refuses_once_its_allowance_is_spent(self):
        from core.throttling import TrustedAnonRateThrottle

        class Tiny(TrustedAnonRateThrottle):
            rate = '3/hour'

        throttle = Tiny()
        request = type('R', (), {
            'META': {'REMOTE_ADDR': '203.0.113.7'}, 'user': None, 'auth': None,
        })()
        allowed = [throttle.allow_request(request, None) for _ in range(5)]
        self.assertEqual(allowed[:3], [True, True, True])
        self.assertIn(False, allowed, 'the throttle never refused')

    def test_a_throttled_api_path_answers_json(self):
        """
        A JSON client handed HTML reports a parse failure, which sends whoever
        is debugging it looking for a serialiser bug instead of a rate limit.
        """
        response = self.client.get('/api/v2/typo/')
        self.assertEqual(response['Content-Type'], 'application/json')
