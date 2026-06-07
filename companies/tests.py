"""
Tests for the per-IP rate limiting + response caching that protect the heavy
public companies endpoints (PDF report, ML insights, certificate, sector report).

Decorators are tested in isolation against trivial views so the suite stays fast
and does not depend on WeasyPrint / matplotlib / ML models.
"""
from django.test import TestCase, RequestFactory
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.models import User, AnonymousUser

from companies.throttle import (
    rate_limit, cache_response, ANON_PER_MIN, AUTH_PER_MIN,
)


def _ok(request, *a, **k):
    return HttpResponse('ok')


class RateLimitTests(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        cache.clear()
        self.anon = AnonymousUser()
        self.user = User.objects.create_user('u', password='x')
        self.staff = User.objects.create_user('s', password='x', is_staff=True)

    def _req(self, user, ip='1.2.3.4'):
        r = self.rf.get('/companies/acme/report.pdf', REMOTE_ADDR=ip)
        r.user = user
        return r

    def test_anonymous_blocked_after_limit(self):
        view = rate_limit('t_anon')(_ok)
        for i in range(ANON_PER_MIN):
            self.assertEqual(view(self._req(self.anon)).status_code, 200, msg=f'req {i+1}')
        # 11th request → 429
        resp = view(self._req(self.anon))
        self.assertEqual(resp.status_code, 429)
        self.assertIn('Retry-After', resp)

    def test_authenticated_has_higher_limit(self):
        view = rate_limit('t_auth')(_ok)
        # an authenticated user sails past the anon limit
        for _ in range(ANON_PER_MIN + 5):
            self.assertEqual(view(self._req(self.user)).status_code, 200)
        # but is blocked after the auth limit
        for _ in range(AUTH_PER_MIN - (ANON_PER_MIN + 5)):
            view(self._req(self.user))
        self.assertEqual(view(self._req(self.user)).status_code, 429)

    def test_staff_unlimited(self):
        view = rate_limit('t_staff')(_ok)
        for _ in range(AUTH_PER_MIN + 25):
            self.assertEqual(view(self._req(self.staff)).status_code, 200)

    def test_limit_is_per_ip(self):
        view = rate_limit('t_ip')(_ok)
        for _ in range(ANON_PER_MIN + 2):
            view(self._req(self.anon, ip='9.9.9.9'))
        # a different IP is unaffected
        self.assertEqual(view(self._req(self.anon, ip='8.8.8.8')).status_code, 200)

    def test_json_429_body(self):
        view = rate_limit('t_json', json=True)(_ok)
        for _ in range(ANON_PER_MIN):
            view(self._req(self.anon))
        resp = view(self._req(self.anon))
        self.assertEqual(resp.status_code, 429)
        self.assertEqual(resp['Content-Type'], 'application/json')
        self.assertIn('Rate limit', resp.content.decode())


class CacheResponseTests(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        cache.clear()

    def test_second_request_served_from_cache(self):
        calls = {'n': 0}

        @cache_response('t_cache', timeout=60)
        def view(request, *a, **k):
            calls['n'] += 1
            return HttpResponse(f'body-{calls["n"]}', content_type='application/pdf')

        r1 = view(self.rf.get('/companies/acme/report.pdf'))
        r2 = view(self.rf.get('/companies/acme/report.pdf'))
        self.assertEqual(calls['n'], 1)               # generated once
        self.assertEqual(r1.content, r2.content)      # identical bytes
        self.assertEqual(r2['Content-Type'], 'application/pdf')

    def test_different_path_not_cached_together(self):
        calls = {'n': 0}

        @cache_response('t_cache2', timeout=60)
        def view(request, *a, **k):
            calls['n'] += 1
            return HttpResponse('x')

        view(self.rf.get('/companies/acme/report.pdf'))
        view(self.rf.get('/companies/other/report.pdf'))
        self.assertEqual(calls['n'], 2)               # distinct paths → distinct cache keys

    def test_non_get_bypasses_cache(self):
        calls = {'n': 0}

        @cache_response('t_cache3', timeout=60)
        def view(request, *a, **k):
            calls['n'] += 1
            return HttpResponse('x')

        view(self.rf.post('/companies/acme/report.pdf'))
        view(self.rf.post('/companies/acme/report.pdf'))
        self.assertEqual(calls['n'], 2)               # POST never cached
