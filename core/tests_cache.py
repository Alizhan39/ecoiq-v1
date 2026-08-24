"""
Tests for the cache backend selection in ecoiq/settings.py.

WHY THESE SHELL OUT
-------------------
`CACHES` is derived at settings-import time from the environment, and a
`@override_settings` test would only prove that a dict can be overridden — not
that the derivation produces it. So each scenario imports settings in a fresh
interpreter with a controlled environment and reports what it got. That is
slower than an in-process test and it is the only version that tests the thing
this file claims to test.

No test here needs a Redis server: nothing connects. Selecting the backend and
opening a connection are separate steps, and only the first is under test.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase, TestCase

REPO_ROOT = Path(__file__).resolve().parent.parent

#: Minimum environment for settings to import with DEBUG=False. These are
#: fixture values for a subprocess, not credentials — no real secret appears.
_PRODUCTION_ENV = {
    'DEBUG': 'False',
    'DJANGO_SECRET_KEY': 'test-only-not-a-real-key',
    'ALLOWED_HOSTS': 'localhost',
    'DATABASE_URL': 'postgres://u:p@db.invalid:5432/ecoiq',
}

_PROBE = r'''
import json, os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecoiq.settings")
django.setup()
from django.conf import settings as s
c = s.CACHES["default"]
print("@@" + json.dumps({
    "backend": c["BACKEND"],
    "location": c["LOCATION"],
    "key_prefix": c["KEY_PREFIX"],
    "timeout": c["TIMEOUT"],
    "options": c.get("OPTIONS", {}),
    "uses_redis": s.CACHE_USES_REDIS,
    "redis_configured": s.REDIS_CONFIGURED,
}))
'''


def _resolve_settings(**env):
    """Import settings in a clean interpreter and return (config, stderr)."""
    child = {k: v for k, v in os.environ.items()
             if k not in ('REDIS_URL', 'DEBUG', 'ECOIQ_CACHE_ENVIRONMENT')}
    child.update({k: v for k, v in env.items() if v is not None})
    proc = subprocess.run(
        [sys.executable, '-c', _PROBE],
        cwd=REPO_ROOT, env=child, capture_output=True, text=True, timeout=120,
    )
    line = next((ln[2:] for ln in proc.stdout.splitlines() if ln.startswith('@@')), None)
    if line is None:
        raise AssertionError(f'probe failed\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}')
    return json.loads(line), proc.stderr


class CacheBackendSelectionTests(SimpleTestCase):

    def test_locmem_is_used_when_redis_is_not_configured(self):
        cfg, _ = _resolve_settings(DEBUG='True')
        self.assertTrue(cfg['backend'].endswith('locmem.LocMemCache'))
        self.assertFalse(cfg['uses_redis'])

    def test_locmem_location_is_explicit_and_named(self):
        """
        Two LocMem caches sharing a LOCATION share one dict. Naming it means a
        future second alias cannot silently collide with the default one.
        """
        cfg, _ = _resolve_settings(DEBUG='True')
        self.assertEqual(cfg['location'], 'ecoiq-locmem-default')

    def test_redis_is_used_when_explicitly_configured(self):
        cfg, _ = _resolve_settings(DEBUG='True', REDIS_URL='redis://localhost:6379/0')
        self.assertTrue(cfg['backend'].endswith('redis.RedisCache'))
        self.assertTrue(cfg['uses_redis'])

    def test_localhost_default_alone_does_not_select_redis(self):
        """
        The truthiness bug this design exists to avoid. REDIS_URL always has a
        value because of its localhost default, so `if REDIS_URL:` would select
        Redis on production — where none is deployed — and every cache read
        would fail against a healthy service.
        """
        cfg, _ = _resolve_settings(DEBUG='True')
        self.assertFalse(cfg['redis_configured'])
        self.assertFalse(cfg['uses_redis'])
        self.assertTrue(cfg['backend'].endswith('locmem.LocMemCache'))

    def test_production_with_redis_configured_uses_redis(self):
        cfg, _ = _resolve_settings(REDIS_URL='redis://cache.invalid:6379/0', **_PRODUCTION_ENV)
        self.assertTrue(cfg['backend'].endswith('redis.RedisCache'))
        self.assertEqual(cfg['key_prefix'], 'ecoiq:production')

    def test_production_without_redis_warns_loudly_and_does_not_crash(self):
        """
        Production runs this way today. It must start — refusing would be a
        self-inflicted outage — but it must not be silent, because per-process
        throttle counters are invisible from the outside.
        """
        cfg, stderr = _resolve_settings(**_PRODUCTION_ENV)
        self.assertTrue(cfg['backend'].endswith('locmem.LocMemCache'))
        self.assertIn('REDIS_URL is not set', stderr)
        self.assertIn('NOT shared between processes', stderr)

    def test_no_warning_when_redis_is_configured(self):
        _, stderr = _resolve_settings(REDIS_URL='redis://cache.invalid:6379/0', **_PRODUCTION_ENV)
        self.assertNotIn('REDIS_URL is not set', stderr)


class CacheConnectionOptionsTests(SimpleTestCase):

    def _redis_cfg(self, url='redis://cache.invalid:6379/0'):
        cfg, _ = _resolve_settings(DEBUG='True', REDIS_URL=url)
        return cfg

    def test_socket_timeouts_are_bounded(self):
        """A stalled Redis must not hold a web thread open indefinitely."""
        opts = self._redis_cfg()['options']
        for key in ('socket_connect_timeout', 'socket_timeout'):
            self.assertIn(key, opts)
            self.assertGreater(opts[key], 0)
            self.assertLessEqual(opts[key], 5)

    def test_connection_pool_is_bounded(self):
        opts = self._redis_cfg()['options']
        self.assertIn('max_connections', opts)
        self.assertGreaterEqual(opts['max_connections'], 8)
        self.assertLessEqual(opts['max_connections'], 100)

    def test_tls_url_requires_certificate_verification(self):
        opts = self._redis_cfg('rediss://cache.invalid:6379/0')['options']
        self.assertEqual(opts.get('ssl_cert_reqs'), 'required')

    def test_plain_url_does_not_claim_tls(self):
        self.assertNotIn('ssl_cert_reqs', self._redis_cfg()['options'])

    def test_default_timeout_is_stated_not_inherited(self):
        self.assertEqual(self._redis_cfg()['timeout'], 300)


class CacheNamespaceTests(SimpleTestCase):

    def test_environment_appears_in_the_key_prefix(self):
        """
        A staging service pointed at the same Redis instance must not be able to
        read or overwrite production's entries.
        """
        dev, _ = _resolve_settings(DEBUG='True', REDIS_URL='redis://cache.invalid:6379/0')
        prod, _ = _resolve_settings(REDIS_URL='redis://cache.invalid:6379/0', **_PRODUCTION_ENV)
        self.assertEqual(dev['key_prefix'], 'ecoiq:development')
        self.assertEqual(prod['key_prefix'], 'ecoiq:production')
        self.assertNotEqual(dev['key_prefix'], prod['key_prefix'])

    def test_environment_namespace_is_overridable(self):
        cfg, _ = _resolve_settings(DEBUG='True', ECOIQ_CACHE_ENVIRONMENT='staging')
        self.assertEqual(cfg['key_prefix'], 'ecoiq:staging')

    def test_release_is_deliberately_absent_from_the_prefix(self):
        """
        Release-scoping the prefix would invalidate the whole cache on every
        deploy — including every throttle counter, which is the exact fragility
        this package exists to remove. Version-sensitive values carry their
        version in their own key instead.
        """
        cfg, _ = _resolve_settings(DEBUG='True', RENDER_GIT_COMMIT='abc123def456')
        self.assertEqual(cfg['key_prefix'], 'ecoiq:development')
        self.assertNotIn('abc123', cfg['key_prefix'])


class CacheSecretExposureTests(TestCase):
    # TestCase, not SimpleTestCase: the readiness test below must exercise the
    # REAL ready response. Under SimpleTestCase the database is forbidden, the
    # probe reports "unavailable", and the test would pass against the 503 body
    # while never checking the one it claims to.

    def test_startup_output_never_contains_the_redis_url(self):
        """
        The connection string carries a password. It belongs in LOCATION, which
        Django needs, and nowhere that is written out.
        """
        url = 'rediss://redisuser:SuperSecret123@cache.internal:6379/0'
        cfg, stderr = _resolve_settings(REDIS_URL=url, **_PRODUCTION_ENV)
        for fragment in ('SuperSecret123', 'redisuser', 'cache.internal', url):
            self.assertNotIn(fragment, stderr,
                             f'startup output leaked {fragment!r}')

    def test_readiness_response_never_contains_redis_details(self):
        """Readiness answers anonymously — see core/health.py."""
        with self.settings(REDIS_CONFIGURED=False):
            response = self.client.get('/readyz/')
        self.assertEqual(response.status_code, 200, 'expected the ready path')
        body = response.content.decode()
        self.assertIn('"status": "ready"', body)
        for fragment in ('redis://', 'rediss://', '6379', 'localhost'):
            self.assertNotIn(fragment, body, f'readiness leaked {fragment!r}')


class CacheAndReadinessAgreeTests(TestCase):
    """
    The cache and the readiness probe must key off the SAME signal. If they
    diverge, readiness can report a dependency the cache is not using, or stay
    green while every cache read fails.
    """

    def test_both_read_redis_configured(self):
        from django.conf import settings

        import core.health as health

        self.assertIs(settings.CACHE_USES_REDIS,
                      settings.REDIS_CONFIGURED and not settings.RUNNING_TESTS)
        # health.readyz consults settings.REDIS_CONFIGURED, not REDIS_URL.
        source = (REPO_ROOT / 'core' / 'health.py').read_text()
        self.assertIn('REDIS_CONFIGURED', source)
        self.assertNotIn('REDIS_URL)', source.split('def readyz')[1])
        self.assertTrue(hasattr(health, 'readyz'))

    def test_tests_never_use_redis_even_if_the_developer_has_it_exported(self):
        """
        A test run must not depend on an external service, and must never read
        or write another process's cache.
        """
        from django.conf import settings

        self.assertTrue(settings.RUNNING_TESTS)
        self.assertFalse(settings.CACHE_USES_REDIS)

    def test_the_configured_cache_actually_works(self):
        from django.core.cache import cache

        cache.set('ecoiq-cache-selftest', 'value', 5)
        self.assertEqual(cache.get('ecoiq-cache-selftest'), 'value')
        cache.delete('ecoiq-cache-selftest')
        self.assertIsNone(cache.get('ecoiq-cache-selftest'))


class CacheSystemCheckTests(SimpleTestCase):

    def test_django_system_checks_pass_with_this_cache_configuration(self):
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command('check', stdout=out, stderr=out)
        self.assertIn('no issues', out.getvalue())
