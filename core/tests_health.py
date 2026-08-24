"""
Tests for the /healthz/ liveness probe and the Render wiring behind it.

These pin the properties that make the endpoint safe to point a restart
decision at: it answers 200 without authentication, it touches no database, and
it is not redirected away under production security settings. Each of those has
a specific failure mode if it regresses, named in the test.
"""
import re
from pathlib import Path
from unittest import mock

from django.db.utils import OperationalError

from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

REPO_ROOT = Path(__file__).resolve().parent.parent


class HealthzResponseTests(SimpleTestCase):
    """The contract Render reads: status, body, and no auth requirement."""

    def test_returns_200(self):
        self.assertEqual(self.client.get('/healthz/').status_code, 200)

    def test_body_is_ok(self):
        response = self.client.get('/healthz/')
        self.assertEqual(response.content, b'ok')

    def test_content_type_is_plain_text(self):
        response = self.client.get('/healthz/')
        self.assertEqual(response['Content-Type'], 'text/plain; charset=utf-8')

    def test_is_reachable_by_name(self):
        self.assertEqual(reverse('healthz'), '/healthz/')

    def test_requires_no_authentication(self):
        """
        Render probes anonymously. If this ever started redirecting to /login/
        the health check would fail on a completely healthy process.
        """
        anonymous = Client()
        response = anonymous.get('/healthz/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Location', response)

    def test_response_is_not_cacheable(self):
        """
        A cached `ok` replayed by an intermediary would report a dead process as
        healthy — the exact failure the health check exists to catch.
        """
        response = self.client.get('/healthz/')
        self.assertIn('no-cache', response['Cache-Control'])
        self.assertIn('no-store', response['Cache-Control'])


class HealthzDoesNoWorkTests(TestCase):
    """The endpoint must stay cheap enough to be safe under a probe loop."""

    def test_makes_no_database_queries(self):
        """
        The whole point of a liveness probe: it must not fail because the
        database is briefly unavailable. TestCase (not SimpleTestCase) so a
        query would actually be counted rather than raising.
        """
        with self.assertNumQueries(0):
            self.client.get('/healthz/')


class HealthzUnderProductionSecurityTests(SimpleTestCase):
    """
    Render probes over the internal network, where X-Forwarded-Proto is absent,
    so the request is not 'secure'. With SECURE_SSL_REDIRECT on and no
    exemption, SecurityMiddleware answers 301 and Render reads a healthy service
    as unhealthy. These tests pin the exemption and its narrowness.
    """

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_is_not_redirected_when_ssl_redirect_is_on(self):
        response = self.client.get('/healthz/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'ok')

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_other_paths_are_still_redirected(self):
        """
        The exemption must not have widened into a general opt-out of HTTPS.
        """
        response = self.client.get('/')
        self.assertEqual(response.status_code, 301)
        self.assertTrue(response['Location'].startswith('https://'))

    def test_exemption_pattern_is_anchored_to_exactly_one_path(self):
        """
        SecurityMiddleware matches these with .search() against
        request.path.lstrip('/'), so an unanchored pattern would exempt far
        more than intended.
        """
        from django.conf import settings

        patterns = [re.compile(p) for p in settings.SECURE_REDIRECT_EXEMPT]

        def exempt(path):
            return any(p.search(path.lstrip('/')) for p in patterns)

        self.assertTrue(exempt('/healthz/'))
        for path in (
            '/',
            '/healthz',                 # no trailing slash — not the wired route
            '/healthz/../admin/',
            '/not-healthz/',
            '/healthz/extra/',
            '/admin/',
            '/companies/',
        ):
            self.assertFalse(exempt(path), f'unexpectedly exempt: {path}')


class HealthzProxyTrustTests(SimpleTestCase):
    """
    STEP 6 guarantee: adding the health check did not relax origin trust.
    These read the shipped settings, so weakening them fails here.
    """

    def test_trusted_proxy_settings_are_untouched_by_the_exemption(self):
        from django.conf import settings

        # Present and still driven by environment/IS_PRODUCTION, not by the
        # health endpoint. The exemption list must not have leaked into them.
        self.assertIsInstance(settings.TRUSTED_PROXY_COUNT, int)
        self.assertNotIn('healthz', str(settings.TRUSTED_PROXY_COUNT))
        self.assertNotIn('healthz', settings.TRUSTED_CLIENT_IP_HEADER)

    def test_security_response_headers_still_apply_to_healthz(self):
        """
        SECURE_REDIRECT_EXEMPT is read only in process_request. Response
        hardening must still reach this endpoint.
        """
        with self.settings(SECURE_CONTENT_TYPE_NOSNIFF=True):
            response = self.client.get('/healthz/')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')


class HealthzLoggingTests(SimpleTestCase):
    """The request logger already anticipated this path; keep them in step."""

    def test_path_is_in_the_request_logger_quiet_list(self):
        """
        A probe every few seconds should not emit a success line each time.
        A failing probe still logs — see core/logging_middleware.py.
        """
        from core.logging_middleware import QUIET_PATHS

        self.assertIn('/healthz/', QUIET_PATHS)


class RenderBlueprintHealthCheckTests(SimpleTestCase):
    """
    The endpoint is only useful if Render is actually pointed at it, and only
    safe while it stays pointed at the cheap one.
    """

    def setUp(self):
        self.blueprint = (REPO_ROOT / 'render.yaml').read_text()

    def test_blueprint_declares_the_health_check_path(self):
        match = re.search(r'^\s*healthCheckPath:\s*(\S+)\s*$',
                          self.blueprint, re.MULTILINE)
        self.assertIsNotNone(match, 'healthCheckPath not found in render.yaml')
        self.assertEqual(match.group(1), '/healthz/')

    def test_health_check_is_not_pointed_at_the_homepage(self):
        """
        '/' renders the landing page and queries the database. Using it as a
        liveness path makes a slow database look like a dead process.
        """
        for bad in ('healthCheckPath: /', 'healthCheckPath: "/"'):
            self.assertNotIn(f'{bad}\n', self.blueprint)


class ReadyzResponseTests(TestCase):
    """
    The readiness contract. TestCase, not SimpleTestCase: this endpoint is
    SUPPOSED to query the database, so the test needs a real one.
    """

    def test_returns_200_when_dependencies_answer(self):
        self.assertEqual(self.client.get('/readyz/').status_code, 200)

    def test_reports_ready_and_names_each_check(self):
        payload = self.client.get('/readyz/').json()
        self.assertEqual(payload['status'], 'ready')
        self.assertEqual(payload['checks']['database'], 'ok')

    def test_is_reachable_by_name(self):
        self.assertEqual(reverse('readyz'), '/readyz/')

    def test_requires_no_authentication(self):
        """A probe runs anonymously; a redirect to /login/ would read as down."""
        response = Client().get('/readyz/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Location', response)

    def test_response_is_not_cacheable(self):
        """A replayed `ready` would report a disconnected process as serving."""
        response = self.client.get('/readyz/')
        self.assertIn('no-cache', response['Cache-Control'])
        self.assertIn('no-store', response['Cache-Control'])

    def test_redis_is_skipped_when_not_configured(self):
        """
        The production case today: no Redis service is deployed, so readiness
        must not fail over it. REDIS_URL alone must never trigger the check —
        it has a localhost default and is therefore always truthy.
        """
        with self.settings(REDIS_CONFIGURED=False):
            payload = self.client.get('/readyz/').json()
        self.assertEqual(payload['checks']['redis'], 'skipped')
        self.assertEqual(payload['status'], 'ready')


class ReadyzFailureTests(TestCase):
    """What it does when a dependency is down, and what it refuses to say."""

    #: A realistic driver error: these carry host, port and user in the text,
    #: which is exactly what must not reach an anonymous response body.
    DRIVER_ERROR = ('FATAL: password authentication failed for user "ecoiq" '
                    'on host db.internal:5432')

    def _fail_database(self):
        """
        Make `connections['default']` itself raise.

        MagicMock, because `__getitem__` is a magic method and a plain Mock
        does not support configuring one.
        """
        handler = mock.MagicMock()
        handler.__getitem__.side_effect = OperationalError(self.DRIVER_ERROR)
        return mock.patch('core.health.connections', handler)

    def test_returns_503_when_the_database_is_unavailable(self):
        """
        503, not 500: "not ready" is an expected operational state that tells a
        load balancer to retry, not an application crash.
        """
        with self._fail_database():
            response = self.client.get('/readyz/')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()['status'], 'not_ready')
        self.assertEqual(response.json()['checks']['database'], 'unavailable')

    def test_failure_body_leaks_no_connection_detail(self):
        """
        The single most important property here. Driver errors routinely carry
        the host, port and user they failed against, and this endpoint answers
        anonymously. The category is stable; the detail goes to the logs.
        """
        with self._fail_database():
            body = self.client.get('/readyz/').content.decode()
        for secret in ('password', 'ecoiq', 'db.internal', '5432', 'FATAL', 'Traceback'):
            self.assertNotIn(secret, body, f'readiness body leaked {secret!r}')

    def test_redis_failure_alone_makes_the_service_not_ready(self):
        with self.settings(REDIS_CONFIGURED=True):
            with mock.patch('redis.Redis.from_url',
                            side_effect=OSError('connect to redis://:hunter2@cache:6379 failed')):
                response = self.client.get('/readyz/')
        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertEqual(payload['checks']['redis'], 'unavailable')
        self.assertEqual(payload['checks']['database'], 'ok')

    def test_redis_failure_body_leaks_no_credential(self):
        """A broker URL carries a password. It must never reach the response."""
        with self.settings(REDIS_CONFIGURED=True):
            with mock.patch('redis.Redis.from_url',
                            side_effect=OSError('connect to redis://:hunter2@cache:6379 failed')):
                body = self.client.get('/readyz/').content.decode()
        for secret in ('hunter2', 'cache:6379', 'redis://', 'Traceback'):
            self.assertNotIn(secret, body, f'readiness body leaked {secret!r}')


class ReadinessIsSeparateFromLivenessTests(SimpleTestCase):
    """
    The property that makes this safe to add at all: readiness must never
    become the thing Render restarts on.
    """

    def setUp(self):
        self.blueprint = (REPO_ROOT / 'render.yaml').read_text()

    def test_render_health_check_still_points_at_liveness(self):
        match = re.search(r'^\s*healthCheckPath:\s*(\S+)\s*$',
                          self.blueprint, re.MULTILINE)
        self.assertEqual(match.group(1), '/healthz/')

    def test_render_health_check_is_not_pointed_at_readiness(self):
        """
        Pointing healthCheckPath here would restart the web service every time
        the database blipped — the precise failure /healthz/ exists to avoid.
        """
        self.assertNotIn('healthCheckPath: /readyz/', self.blueprint)

    def test_readiness_path_is_in_the_request_logger_quiet_list(self):
        from core.logging_middleware import QUIET_PATHS

        self.assertIn('/readyz/', QUIET_PATHS)

    def test_readiness_is_exempt_from_the_ssl_redirect(self):
        """
        Probed over the internal network, where X-Forwarded-Proto is absent.
        Without the exemption a healthy service answers 301 to its monitor.
        """
        from django.conf import settings

        patterns = [re.compile(p) for p in settings.SECURE_REDIRECT_EXEMPT]

        def exempt(path):
            return any(p.search(path.lstrip('/')) for p in patterns)

        self.assertTrue(exempt('/readyz/'))
        # The exemption must not have widened while being extended.
        for path in ('/', '/readyz', '/not-readyz/', '/readyz/extra/', '/admin/'):
            self.assertFalse(exempt(path), f'unexpectedly exempt: {path}')
