"""
Regression tests for production settings and deployment-script safety.

These pin behaviour that previously failed open: an insecure SECRET_KEY
fallback, a .env file overriding real environment variables, a silent SQLite
fallback in production, and deploy scripts that swallowed migration failures.
"""
import os
import re
import sys
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

REPO_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = REPO_ROOT / 'ecoiq' / 'settings.py'


def load_settings_module(environ, argv=None):
    """
    Execute settings.py in a fresh namespace under a controlled environment.

    Importing the real module again would return the cached one, so the file is
    exec'd instead. This is the only way to assert on import-time guards.

    sys.argv is replaced as well: settings.py treats `test` in argv as "this is
    the test runner" and relaxes the production guards. Under the real test
    runner that flag is always set, which would make every assertion below
    vacuous, so the default argv here simulates a normal server process.
    """
    source = SETTINGS_PATH.read_text()
    namespace = {'__file__': str(SETTINGS_PATH), '__name__': 'ecoiq.settings_under_test'}
    with mock.patch.dict(os.environ, environ, clear=True):
        # load_dotenv would re-read the developer's real .env and defeat
        # clear=True, so it is neutralised for the duration of the exec.
        with mock.patch('dotenv.load_dotenv', lambda *a, **k: False):
            with mock.patch.object(sys, 'argv', argv or ['manage.py', 'runserver']):
                exec(compile(source, str(SETTINGS_PATH), 'exec'), namespace)
    return namespace


PRODUCTION_ENV = {
    'DEBUG': 'False',
    'DJANGO_SECRET_KEY': 'a-sufficiently-long-test-key-for-settings-exec-only',
    'ALLOWED_HOSTS': 'ecoiq.uk www.ecoiq.uk',
    'DATABASE_URL': 'postgres://user:pw@localhost:5432/ecoiq',
}


def production_env(**overrides):
    merged = {**PRODUCTION_ENV, **overrides}
    return {k: v for k, v in merged.items() if v is not None}


class SecretKeyTests(SimpleTestCase):

    def test_production_without_secret_key_refuses_to_start(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            load_settings_module(production_env(DJANGO_SECRET_KEY=None))
        self.assertIn('DJANGO_SECRET_KEY', str(ctx.exception))

    def test_production_with_blank_secret_key_refuses_to_start(self):
        with self.assertRaises(ImproperlyConfigured):
            load_settings_module(production_env(DJANGO_SECRET_KEY=''))

    def test_debug_defaults_to_false_when_unset(self):
        """An unset DEBUG must never mean 'development'."""
        with self.assertRaises(ImproperlyConfigured):
            # No DEBUG and no DJANGO_SECRET_KEY: if DEBUG defaulted to True the
            # production guard would be skipped and this would not raise.
            load_settings_module({})

    def test_debug_is_only_true_for_the_exact_string(self):
        for value in ('true', '1', 'yes', 'False', ''):
            with self.subTest(DEBUG=value):
                ns = load_settings_module(production_env(DEBUG=value))
                self.assertFalse(ns['DEBUG'], f'DEBUG={value!r} must not enable debug')

    def test_development_still_gets_a_working_fallback_key(self):
        ns = load_settings_module({'DEBUG': 'True'})
        self.assertTrue(ns['SECRET_KEY'])
        self.assertTrue(ns['DEBUG'])

    def test_no_insecure_fallback_key_literal_remains_in_settings(self):
        source = SETTINGS_PATH.read_text()
        self.assertNotIn('django-insecure-dev-only-CHANGE-IN-PRODUCTION', source)

    def test_secret_key_is_never_printed_at_startup(self):
        source = SETTINGS_PATH.read_text()
        for line in source.splitlines():
            if line.strip().startswith('print(') or 'file=sys.stderr' in line:
                self.assertNotIn('SECRET_KEY', line)


class AllowedHostsTests(SimpleTestCase):

    def test_wildcard_is_rejected_in_production(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            load_settings_module(production_env(ALLOWED_HOSTS='*'))
        self.assertIn('ALLOWED_HOSTS', str(ctx.exception))

    def test_empty_is_rejected_in_production(self):
        with self.assertRaises(ImproperlyConfigured):
            load_settings_module(production_env(ALLOWED_HOSTS=''))

    def test_explicit_hosts_are_accepted(self):
        ns = load_settings_module(production_env())
        self.assertEqual(ns['ALLOWED_HOSTS'], ['ecoiq.uk', 'www.ecoiq.uk'])

    def test_wildcard_still_allowed_in_local_development(self):
        ns = load_settings_module({'DEBUG': 'True', 'ALLOWED_HOSTS': '*'})
        self.assertEqual(ns['ALLOWED_HOSTS'], ['*'])

    def test_render_blueprint_does_not_ship_a_wildcard(self):
        blueprint = (REPO_ROOT / 'render.yaml').read_text()
        match = re.search(r'key:\s*ALLOWED_HOSTS\s*\n\s*value:\s*"([^"]*)"', blueprint)
        self.assertIsNotNone(match, 'ALLOWED_HOSTS not found in render.yaml')
        self.assertNotIn('*', match.group(1))


class DatabaseConfigurationTests(SimpleTestCase):

    def test_production_without_database_url_refuses_to_start(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            load_settings_module(production_env(DATABASE_URL=None))
        self.assertIn('DATABASE_URL', str(ctx.exception))

    def test_development_falls_back_to_sqlite(self):
        ns = load_settings_module({'DEBUG': 'True'})
        self.assertIn('sqlite', ns['DATABASES']['default']['ENGINE'])


class DotenvPrecedenceTests(SimpleTestCase):
    """A real environment variable must always beat a .env file."""

    def test_settings_loads_dotenv_without_override(self):
        source = SETTINGS_PATH.read_text()
        self.assertIn('load_dotenv(override=False)', source)
        self.assertNotIn('load_dotenv(override=True)', source)


class SecurityHardeningTests(SimpleTestCase):

    def test_production_enables_secure_cookies_and_hsts(self):
        ns = load_settings_module(production_env())
        self.assertTrue(ns['SESSION_COOKIE_SECURE'])
        self.assertTrue(ns['CSRF_COOKIE_SECURE'])
        self.assertTrue(ns['SECURE_SSL_REDIRECT'])
        self.assertGreater(ns['SECURE_HSTS_SECONDS'], 0)
        self.assertTrue(ns['SECURE_CONTENT_TYPE_NOSNIFF'])

    def test_proxy_ssl_header_matches_render(self):
        ns = load_settings_module(production_env())
        self.assertEqual(
            ns['SECURE_PROXY_SSL_HEADER'], ('HTTP_X_FORWARDED_PROTO', 'https'))

    def test_logging_is_configured(self):
        self.assertIn('django.request', settings.LOGGING['loggers'])


class DeploymentScriptTests(SimpleTestCase):
    """The deploy scripts must fail the deploy instead of hiding failures."""

    def _read(self, name):
        return (REPO_ROOT / name).read_text()

    def _code_lines(self, name):
        return [
            line for line in self._read(name).splitlines()
            if line.strip() and not line.strip().startswith('#')
        ]

    def test_predeploy_uses_strict_mode(self):
        self.assertIn('set -euo pipefail', self._read('predeploy.sh'))
        self.assertNotIn('set +e', self._read('predeploy.sh'))

    def test_predeploy_aborts_when_migrations_fail(self):
        script = self._read('predeploy.sh')
        self.assertIn('exit 1', script)
        # The old script exited 0 after giving up on migrations.
        self.assertNotIn('exit 0', script)

    def test_predeploy_does_not_swallow_failures(self):
        for line in self._code_lines('predeploy.sh'):
            self.assertNotIn('|| true', line)
            self.assertNotIn('2>/dev/null', line)

    def test_predeploy_runs_deployment_checks(self):
        self.assertIn('check --deploy', self._read('predeploy.sh'))

    def test_predeploy_does_not_seed_on_every_deploy(self):
        seed_commands = (
            'seed_countries', 'seed_global_companies', 'seed_phase2_companies',
            'add_400_companies', 'seed_score_history', 'focus_target_markets',
            'seed_legacy_safe',
        )
        for line in self._code_lines('predeploy.sh'):
            for command in seed_commands:
                self.assertNotIn(
                    command, line,
                    f'{command} must be an explicit operator action, not a deploy step')

    def test_start_does_not_migrate(self):
        for line in self._code_lines('start.sh'):
            self.assertNotIn('manage.py migrate', line)

    def test_start_still_launches_gunicorn(self):
        self.assertIn('gunicorn', self._read('start.sh'))

    def test_build_does_not_reinstall_requirements(self):
        for line in self._code_lines('build.sh'):
            self.assertNotIn('pip install', line)

    def test_build_still_collects_static(self):
        self.assertIn('collectstatic', self._read('build.sh'))

    def test_failed_collectstatic_stops_the_build(self):
        """collectstatic must not be guarded — under `set -e` it aborts."""
        for line in self._code_lines('build.sh'):
            if 'collectstatic' in line:
                self.assertNotIn('|| true', line)
                self.assertNotIn('|| echo', line)
                self.assertNotIn('2>/dev/null', line)
                break
        else:
            self.fail('collectstatic not found in build.sh')

    def test_failed_deployment_check_stops_the_release(self):
        """check --deploy must not be guarded either."""
        for line in self._code_lines('predeploy.sh'):
            if 'check --deploy' in line:
                self.assertNotIn('|| true', line)
                self.assertNotIn('|| echo', line)
                break
        else:
            self.fail('check --deploy not found in predeploy.sh')

    def test_build_uses_strict_mode(self):
        self.assertIn('set -euo pipefail', self._read('build.sh'))


# ═══════════════════════════════════════════════════════════════════════════
# Production security must apply to production processes only.
#
# The block was gated on `not DEBUG`. The test runner imports settings with
# whatever DEBUG the environment carries, and CI sets DEBUG=False so its
# `check` steps are production-like — which switched SECURE_SSL_REDIRECT on
# for the test process, made every test-client request answer 301, and failed
# ~1400 tests. It went unnoticed because the CI test step also carried
# continue-on-error.
#
# These tests run real settings imports in a subprocess: the in-process
# `django.conf.settings` is already loaded and cannot show import-time
# behaviour, and load_settings_module() above cannot reproduce a genuine
# `manage.py` argv.
# ═══════════════════════════════════════════════════════════════════════════

# Settings the block turns on that Django leaves off/0 by default, so their
# value proves whether the block ran.
PRODUCTION_ONLY_SECURITY_SETTINGS = (
    'SECURE_SSL_REDIRECT',
    'SESSION_COOKIE_SECURE',
    'CSRF_COOKIE_SECURE',
    'SECURE_HSTS_SECONDS',
    'SECURE_HSTS_INCLUDE_SUBDOMAINS',
    'SECURE_HSTS_PRELOAD',
)

# Also set by the block, but True in django.conf.global_settings anyway, so it
# stays on everywhere and cannot indicate whether the block ran.
ALWAYS_ON_SECURITY_SETTINGS = ('SECURE_CONTENT_TYPE_NOSNIFF',)

PRODUCTION_SECURITY_SETTINGS = (
    PRODUCTION_ONLY_SECURITY_SETTINGS + ALWAYS_ON_SECURITY_SETTINGS
)

# Import settings under a chosen argv and report the values as JSON. argv is
# what distinguishes a test process from a production one, so it is set
# explicitly rather than inherited.
_PROBE = """
import json, sys
sys.argv = {argv!r}
import django
django.setup()
from django.conf import settings
print('@@' + json.dumps({{
    'DEBUG': settings.DEBUG,
    'RUNNING_TESTS': settings.RUNNING_TESTS,
    'IS_PRODUCTION': settings.IS_PRODUCTION,
    **{{name: getattr(settings, name, None) for name in {names!r}}},
}}))
"""

# Test-process value only; not a credential for any real environment.
PROBE_SECRET = 'subprocess-probe-key-not-a-real-secret-value'


def probe_settings(argv, **env_overrides):
    """
    Import ecoiq.settings in a fresh interpreter under a controlled
    environment and argv, and return the resulting values.
    """
    import json
    import subprocess

    env = {
        'PATH': os.environ.get('PATH', ''),
        'HOME': os.environ.get('HOME', ''),
        'DJANGO_SETTINGS_MODULE': 'ecoiq.settings',
        'DJANGO_SECRET_KEY': PROBE_SECRET,
        'ALLOWED_HOSTS': 'localhost 127.0.0.1',
        'DATABASE_URL': 'sqlite:///probe-not-created.sqlite3',
        # Neutralise any developer .env so the probe sees only what it is given.
        'DOTENV_PATH': '/nonexistent',
    }
    env.update({k: v for k, v in env_overrides.items() if v is not None})

    script = _PROBE.format(argv=argv, names=list(PRODUCTION_SECURITY_SETTINGS))
    result = subprocess.run(
        [sys.executable, '-c', script],
        cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise AssertionError(
            f'settings import failed (exit {result.returncode}) for argv={argv} '
            f'env={ {k: v for k, v in env_overrides.items()} }\n'
            f'--- stderr ---\n{result.stdout[-2000:]}\n{result.stderr[-2000:]}'
        )
    line = next((l for l in result.stdout.splitlines() if l.startswith('@@')), None)
    if line is None:
        raise AssertionError(f'probe produced no result. stdout:\n{result.stdout[-2000:]}')
    return json.loads(line[2:])


class ProductionSecurityAppliesOnlyToProductionTests(SimpleTestCase):

    # ── The defect ────────────────────────────────────────────────────────

    def test_debug_false_under_the_test_runner_does_not_enable_ssl_redirect(self):
        values = probe_settings(['manage.py', 'test'], DEBUG='False')
        self.assertFalse(
            values['SECURE_SSL_REDIRECT'],
            'SECURE_SSL_REDIRECT during tests makes every test-client request 301')

    def test_debug_false_under_the_test_runner_enables_no_production_security(self):
        values = probe_settings(['manage.py', 'test'], DEBUG='False')
        for name in PRODUCTION_ONLY_SECURITY_SETTINGS:
            with self.subTest(setting=name):
                self.assertFalse(
                    values[name],
                    f'{name} must not be enabled solely because the environment '
                    f'carries DEBUG=False while running tests')
        # Django's own default, on in every environment — asserted so a future
        # change that turns it off is still caught.
        for name in ALWAYS_ON_SECURITY_SETTINGS:
            with self.subTest(setting=name):
                self.assertTrue(values[name])

    def test_is_production_is_false_during_tests_even_with_debug_false(self):
        values = probe_settings(['manage.py', 'test'], DEBUG='False')
        self.assertFalse(values['DEBUG'])
        self.assertTrue(values['RUNNING_TESTS'])
        self.assertFalse(values['IS_PRODUCTION'])

    # ── Production must be unaffected ─────────────────────────────────────

    def test_real_production_import_enables_every_security_setting(self):
        values = probe_settings(['manage.py', 'runserver'], DEBUG='False')
        self.assertTrue(values['IS_PRODUCTION'])
        self.assertFalse(values['RUNNING_TESTS'])
        for name in PRODUCTION_SECURITY_SETTINGS:
            with self.subTest(setting=name):
                self.assertTrue(values[name], f'{name} must stay on in production')
        self.assertEqual(values['SECURE_HSTS_SECONDS'], 31536000)

    def test_check_deploy_is_treated_as_production_not_as_a_test(self):
        values = probe_settings(['manage.py', 'check', '--deploy'], DEBUG='False')
        self.assertTrue(values['IS_PRODUCTION'])
        self.assertFalse(values['RUNNING_TESTS'])
        self.assertTrue(values['SECURE_SSL_REDIRECT'])
        self.assertTrue(values['SESSION_COOKIE_SECURE'])
        self.assertTrue(values['CSRF_COOKIE_SECURE'])

    def test_gunicorn_style_process_is_production(self):
        values = probe_settings(['gunicorn', 'ecoiq.wsgi:application'], DEBUG='False')
        self.assertTrue(values['IS_PRODUCTION'])
        self.assertTrue(values['SECURE_SSL_REDIRECT'])

    # ── Development ───────────────────────────────────────────────────────

    def test_development_enables_no_production_security(self):
        values = probe_settings(['manage.py', 'runserver'], DEBUG='True')
        self.assertTrue(values['DEBUG'])
        self.assertFalse(values['IS_PRODUCTION'])
        for name in PRODUCTION_ONLY_SECURITY_SETTINGS:
            with self.subTest(setting=name):
                self.assertFalse(values[name])

    # ── The gate itself ───────────────────────────────────────────────────

    def test_security_block_is_gated_on_is_production(self):
        source = SETTINGS_PATH.read_text()
        block = source[source.index('SECURE_PROXY_SSL_HEADER'):]
        gate = next(
            line.strip() for line in block.splitlines()
            if line.startswith('if ') and 'SECURE' not in line
        )
        self.assertEqual(gate, 'if IS_PRODUCTION:')

    def test_proxy_ssl_header_stays_unconditional(self):
        """Render terminates TLS; this must apply in every environment."""
        for argv, debug in ((['manage.py', 'test'], 'False'),
                            (['manage.py', 'runserver'], 'True'),
                            (['manage.py', 'runserver'], 'False')):
            with self.subTest(argv=argv, DEBUG=debug):
                self.assertEqual(
                    load_settings_module(
                        production_env(DEBUG=debug), argv=argv,
                    )['SECURE_PROXY_SSL_HEADER'],
                    ('HTTP_X_FORWARDED_PROTO', 'https'))
