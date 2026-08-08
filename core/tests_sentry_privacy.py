"""
Privacy invariants for outbound Sentry payloads.

The authoritative test in this file is the fake transport. `before_send` in
isolation proves only that `before_send` works; it says nothing about a field
some integration adds afterwards, or a payload shape nobody anticipated. These
tests capture the event at the transport boundary — the last point before bytes
would leave the process — and assert on the complete serialised payload.

No test here reaches the network. The DSN is syntactically valid and points at a
`.invalid` host, and the transport is replaced before `init()`, so nothing is
ever resolved or dialled.

Every secret is synthetic.
"""
import json
import logging
import sys

import sentry_sdk
import structlog
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import path
from sentry_sdk.transport import Transport

from core import sentry_setup

# RFC 2606 reserves .invalid; it can never resolve.
FAKE_DSN = 'https://publickey@o0.ingest.invalid/0'

MARKERS = {
    'password': 'TOP_SECRET_PASSWORD_918271',
    'token': 'TEST_TOKEN_928374',
    'email': 'alice.testing@example.invalid',
    'phone': '+447700900123',
    'ipv4': '203.0.113.42',
    'ipv6': '2001:db8::123',
    'message': 'SENSITIVE_CONTACT_MESSAGE_12873',
    'prompt': 'SECRET_AI_PROMPT_92837',
    'dburl': 'postgresql://testuser:testpassword@example.invalid/test',
}


class CapturingTransport(Transport):
    """Records envelopes instead of sending them. Opens no socket."""

    captured: list = []

    def __init__(self, options=None):
        super().__init__(options)
        CapturingTransport.captured = []

    def capture_envelope(self, envelope):
        for item in envelope.items:
            payload = item.get_event() or item.payload.json
            if payload:
                CapturingTransport.captured.append(payload)

    def flush(self, timeout=None, callback=None):
        return None

    def kill(self):
        return None


class SentryTestCase(TestCase):
    """Initialises a real client whose transport cannot reach the network."""

    traces_rate = 0.0

    def setUp(self):
        options = sentry_setup.sentry_options(
            dsn=FAKE_DSN, environment='test', release='testrelease123')
        options.pop('_sdk_version', None)
        options['transport'] = CapturingTransport
        options['traces_sample_rate'] = self.traces_rate
        sentry_sdk.init(**options)
        CapturingTransport.captured = []
        self.addCleanup(sentry_sdk.init, dsn=None)

    @property
    def events(self):
        sentry_sdk.get_client().flush()
        return [e for e in CapturingTransport.captured if e.get('type') != 'transaction']

    def blob(self):
        sentry_sdk.get_client().flush()
        return json.dumps(CapturingTransport.captured, default=str)


class OutboundPrivacyTests(SentryTestCase):
    """The synthetic marker sweep, asserted on the serialised payload."""

    def _saturate_and_raise(self):
        scope = sentry_sdk.get_current_scope()
        scope.set_tag('api_key', MARKERS['token'])
        scope.set_user({'id': '42', 'email': MARKERS['email'],
                        'username': MARKERS['email'], 'ip_address': MARKERS['ipv4']})
        scope.set_context('ai', {'prompt': MARKERS['prompt'],
                                 'completion': MARKERS['message']})
        scope.set_context('db', {'database_url': MARKERS['dburl']})
        scope.set_extra('contact_message', MARKERS['message'])
        scope.set_extra('nested', {'deep': {'password': MARKERS['password'],
                                            'phone': MARKERS['phone']}})
        logging.getLogger('legacy').warning(
            'legacy breadcrumb %s %s', MARKERS['ipv4'], MARKERS['email'])
        structlog.get_logger('ecoiq.app').info(
            'structured_breadcrumb', email=MARKERS['email'], token=MARKERS['token'])
        try:
            raise ValueError(f"{MARKERS['password']} {MARKERS['email']} "
                             f"{MARKERS['token']} {MARKERS['ipv6']}")
        except ValueError:
            sentry_sdk.capture_exception()

    def test_no_synthetic_marker_reaches_the_transport(self):
        self._saturate_and_raise()
        blob = self.blob()
        self.assertTrue(blob and blob != '[]', 'no event was captured')
        for name, value in MARKERS.items():
            with self.subTest(name):
                self.assertNotIn(value, blob)

    def test_useful_diagnostics_survive(self):
        self._saturate_and_raise()
        event = self.events[0]
        self.assertEqual(event['exception']['values'][0]['type'], 'ValueError')
        frames = event['exception']['values'][0]['stacktrace']['frames']
        self.assertTrue(frames)
        self.assertTrue(any(f.get('function') for f in frames))
        self.assertTrue(any(f.get('lineno') for f in frames))
        self.assertEqual(event.get('release'), 'testrelease123')
        self.assertEqual(event.get('environment'), 'test')

    def test_stack_frames_carry_no_local_variables(self):
        self._saturate_and_raise()
        for event in self.events:
            for entry in event.get('exception', {}).get('values', []):
                for frame in entry.get('stacktrace', {}).get('frames', []):
                    with self.subTest(frame.get('function')):
                        self.assertNotIn('vars', frame)

    def test_exception_value_is_redacted_but_type_kept(self):
        self._saturate_and_raise()
        entry = self.events[0]['exception']['values'][0]
        self.assertEqual(entry['type'], 'ValueError')
        self.assertEqual(entry['value'], sentry_setup.REDACTED)

    def test_user_context_keeps_only_an_internal_id(self):
        self._saturate_and_raise()
        user = self.events[0].get('user') or {}
        self.assertEqual(set(user) - {'id'}, set())
        self.assertEqual(user.get('id'), '42')


class ArgvScrubbingTests(SentryTestCase):
    """
    Command-line arguments are an independent leak path.

    `extra['sys.argv']` is attached to every event by the SDK. This repository
    has management commands that take secrets as arguments, and neither the key
    rules (the key is `sys.argv`) nor the value rules (a password has no shape)
    catch them. Verified leaking before scrub_argv existed.
    """

    def test_command_line_secrets_do_not_reach_the_transport(self):
        import sys as _sys
        saved = _sys.argv
        # Assembled at runtime. Sentry captures pre_context/context_line/
        # post_context — the SOURCE around each frame — so a marker written as a
        # literal here would appear in the payload as code, not as leaked data,
        # and the assertion would fail for the wrong reason.
        secret = 'ARGV' + '_SECRET_' + '55123'
        _sys.argv = ['manage.py', 'create_demo_user', '--password',
                     secret, '--email', MARKERS['email']]
        self.addCleanup(setattr, _sys, 'argv', saved)
        try:
            raise RuntimeError('command failed')
        except RuntimeError:
            sentry_sdk.capture_exception()
        blob = self.blob()
        self.assertNotIn(secret, blob)
        self.assertNotIn(MARKERS['email'], blob)

    def test_the_command_name_is_still_identifiable(self):
        # Redaction must not cost us knowing WHICH command failed.
        event = {'extra': {'sys.argv': ['manage.py', 'create_demo_user',
                                        '--password', 'a-secret-value']}}
        sentry_setup.scrub_argv(event)
        self.assertEqual(event['extra']['sys.argv'],
                         ['manage.py', 'create_demo_user', sentry_setup.REDACTED])

    def test_a_short_argv_is_left_alone(self):
        event = {'extra': {'sys.argv': ['manage.py', 'migrate']}}
        sentry_setup.scrub_argv(event)
        self.assertEqual(event['extra']['sys.argv'], ['manage.py', 'migrate'])


class RequestScrubbingTests(SentryTestCase):

    def test_request_section_drops_body_cookies_and_credentials(self):
        request = {
            'method': 'POST',
            'url': 'https://ecoiq.uk/contact/?token=' + MARKERS['token'],
            'query_string': 'token=' + MARKERS['token'],
            'data': {'message': MARKERS['message'], 'email': MARKERS['email']},
            'cookies': {'sessionid': MARKERS['token']},
            'env': {'REMOTE_ADDR': MARKERS['ipv4']},
            'headers': {
                'Authorization': 'Bearer ' + MARKERS['token'],
                'Cookie': 'sessionid=' + MARKERS['token'],
                'X-Forwarded-For': MARKERS['ipv4'],
                'CF-Connecting-IP': MARKERS['ipv4'],
                'X-CSRFToken': MARKERS['token'],
                'User-Agent': 'probe/1.0',
            },
        }
        out = sentry_setup.scrub_request(dict(request))
        for key in ('data', 'cookies', 'env'):
            with self.subTest(key):
                self.assertNotIn(key, out)
        for header in ('Authorization', 'Cookie', 'X-Forwarded-For',
                       'CF-Connecting-IP', 'X-CSRFToken'):
            with self.subTest(header):
                self.assertEqual(out['headers'][header], sentry_setup.REDACTED)
        self.assertEqual(out['query_string'], sentry_setup.REDACTED)
        self.assertNotIn('?', out['url'])
        # Kept, because they are what make an event findable.
        self.assertEqual(out['method'], 'POST')
        self.assertEqual(out['headers']['User-Agent'], 'probe/1.0')


def _boom(request):
    raise ValueError(f"{MARKERS['password']} {MARKERS['email']}")


def _fine(request):
    from django.http import HttpResponse
    return HttpResponse('ok')


class RequestCorrelationTests(SentryTestCase):
    """HTTP header, log line and Sentry event must carry one id."""

    def setUp(self):
        super().setUp()
        module = type(sys)('sentry_urlconf')
        module.urlpatterns = [path('boom/', _boom), path('fine/', _fine)]
        sys.modules['sentry_urlconf'] = module
        self.addCleanup(sys.modules.pop, 'sentry_urlconf', None)

    def test_request_id_matches_across_http_log_and_sentry(self):
        import io
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        root = logging.getLogger()
        saved = list(root.handlers)
        root.handlers = [handler] + saved
        self.addCleanup(setattr, root, 'handlers', saved)

        with override_settings(ROOT_URLCONF='sentry_urlconf', DEBUG=False,
                               ALLOWED_HOSTS=['testserver']):
            response = Client(raise_request_exception=False).get('/boom/', secure=True)

        http_id = response['X-Request-ID']
        self.assertTrue(http_id)
        self.assertIn(http_id, stream.getvalue())
        errors = self.events
        self.assertTrue(errors, 'no Sentry event captured for the 500')
        self.assertEqual(errors[0]['tags']['request_id'], http_id)
        self.assertEqual(errors[0]['contexts']['ecoiq']['request_id'], http_id)

    def test_one_unhandled_exception_produces_exactly_one_event(self):
        with override_settings(ROOT_URLCONF='sentry_urlconf', DEBUG=False,
                               ALLOWED_HOSTS=['testserver']):
            Client(raise_request_exception=False).get('/boom/', secure=True)
        # DjangoIntegration and LoggingIntegration both see this fault; if
        # event_level were below ERROR-with-exc_info they would both file it.
        self.assertEqual(len(self.events), 1, f'{len(self.events)} events for one fault')

    def test_a_real_request_leaks_nothing(self):
        with override_settings(ROOT_URLCONF='sentry_urlconf', DEBUG=False,
                               ALLOWED_HOSTS=['testserver']):
            Client(raise_request_exception=False).post(
                f"/boom/?token={MARKERS['token']}",
                data={'message': MARKERS['message'], 'email': MARKERS['email']},
                secure=True,
                HTTP_AUTHORIZATION=f"Bearer {MARKERS['token']}",
                HTTP_COOKIE=f"sessionid={MARKERS['token']}",
                HTTP_X_FORWARDED_FOR=MARKERS['ipv4'])
        blob = self.blob()
        for name, value in MARKERS.items():
            with self.subTest(name):
                self.assertNotIn(value, blob)

    def test_expected_404_does_not_become_an_event(self):
        with override_settings(ROOT_URLCONF='sentry_urlconf', DEBUG=False,
                               ALLOWED_HOSTS=['testserver']):
            response = Client().get('/no-such-path/', secure=True)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.events, [])

    def test_a_successful_request_produces_no_error_event(self):
        with override_settings(ROOT_URLCONF='sentry_urlconf', DEBUG=False,
                               ALLOWED_HOSTS=['testserver']):
            response = Client().get('/fine/', secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.events, [])


class BreadcrumbTests(SentryTestCase):

    def test_lifecycle_events_are_not_breadcrumbs(self):
        # They are the highest-volume thing the app logs; as breadcrumbs they
        # would evict everything useful from the trail.
        for name in ('request_started', 'request_completed'):
            with self.subTest(name):
                self.assertIsNone(
                    sentry_setup.before_breadcrumb({'message': name}, None))

    def test_breadcrumbs_are_scrubbed(self):
        crumb = sentry_setup.before_breadcrumb(
            {'message': 'op', 'data': {'email': MARKERS['email'],
                                       'api_key': MARKERS['token']}}, None)
        self.assertEqual(crumb['data']['email'], sentry_setup.REDACTED)
        self.assertEqual(crumb['data']['api_key'], sentry_setup.REDACTED)


class IntegrationSurfaceTests(SentryTestCase):
    """
    Only reviewed integrations may run.

    A captured event once listed celery, fastapi, flask, httpx, langchain,
    langgraph, redis, sqlalchemy and starlette — auto-enabled by the SDK because
    the packages are installed. langchain's whole purpose is recording prompts
    and completions.
    """

    def test_only_django_and_logging_are_active(self):
        try:
            raise RuntimeError('probe')
        except RuntimeError:
            sentry_sdk.capture_exception()
        active = set(self.events[0]['sdk']['integrations'])
        for unwanted in ('langchain', 'langgraph', 'httpx', 'redis', 'celery',
                         'sqlalchemy', 'flask', 'fastapi', 'starlette'):
            with self.subTest(unwanted):
                self.assertNotIn(unwanted, active)
        self.assertIn('django', active)
        self.assertIn('logging', active)

    def test_auto_enabling_is_disabled_in_options(self):
        options = sentry_setup.sentry_options(
            dsn=FAKE_DSN, environment='test', release='r')
        self.assertIs(options['auto_enabling_integrations'], False)


class BreadcrumbUsefulnessTests(SentryTestCase):
    """
    Redaction must not destroy the trail it is protecting.

    `message` is in PERSONAL_KEY_PARTS so that `contact_message` is caught. Applied
    to Sentry's own top-level `message` field it turned every breadcrumb into
    "[REDACTED]" — a trail that says nothing, which is the failure mode the brief
    warned about.
    """

    def test_a_controlled_event_name_survives(self):
        crumb = sentry_setup.before_breadcrumb({'message': 'rate_limit_applied'}, None)
        self.assertEqual(crumb['message'], 'rate_limit_applied')

    def test_but_addresses_inside_a_message_are_still_scrubbed(self):
        crumb = sentry_setup.before_breadcrumb(
            {'message': f"failed for {MARKERS['ipv4']} and {MARKERS['email']}"}, None)
        self.assertNotIn(MARKERS['ipv4'], crumb['message'])
        self.assertNotIn(MARKERS['email'], crumb['message'])

    def test_a_prefixed_message_key_is_still_redacted(self):
        # The exemption is the exact key only.
        crumb = sentry_setup.before_breadcrumb(
            {'message': 'ok', 'data': {'contact_message': MARKERS['message']}}, None)
        self.assertEqual(crumb['data']['contact_message'], sentry_setup.REDACTED)


class ConfigurationTests(SimpleTestCase):

    def test_disabled_without_a_dsn(self):
        with self.settings():
            import os
            saved = os.environ.pop('SENTRY_DSN', None)
            try:
                self.assertFalse(sentry_setup.is_enabled())
                self.assertFalse(sentry_setup.initialise(
                    environment='test', release='r'))
            finally:
                if saved is not None:
                    os.environ['SENTRY_DSN'] = saved

    def test_explicit_disable_overrides_a_present_dsn(self):
        import os
        os.environ['SENTRY_DSN'] = FAKE_DSN
        os.environ['SENTRY_ENABLED'] = 'false'
        self.addCleanup(os.environ.pop, 'SENTRY_DSN', None)
        self.addCleanup(os.environ.pop, 'SENTRY_ENABLED', None)
        self.assertFalse(sentry_setup.is_enabled())

    def test_malformed_sample_rate_fails_loudly(self):
        import os
        for bad in ('abc', '1.5', '-0.1', '100'):
            with self.subTest(bad):
                os.environ['SENTRY_TRACES_SAMPLE_RATE'] = bad
                self.addCleanup(os.environ.pop, 'SENTRY_TRACES_SAMPLE_RATE', None)
                with self.assertRaises(sentry_setup.SentryConfigurationError):
                    sentry_setup._sample_rate('SENTRY_TRACES_SAMPLE_RATE')

    def test_absent_sample_rate_is_zero_not_one(self):
        import os
        os.environ.pop('SENTRY_TRACES_SAMPLE_RATE', None)
        self.assertEqual(sentry_setup._sample_rate('SENTRY_TRACES_SAMPLE_RATE'), 0.0)


class ConfigurationSafeguardTests(SimpleTestCase):
    """
    Structural guards. Each of these, if quietly reversed, would send data we
    have promised not to send — and nothing else would fail.
    """

    def options(self):
        return sentry_setup.sentry_options(
            dsn=FAKE_DSN, environment='test', release='r')

    def test_pii_and_locals_stay_off_and_bodies_are_never_sent(self):
        options = self.options()
        self.assertIs(options['send_default_pii'], False)
        self.assertIs(options['include_local_variables'], False)
        self.assertEqual(options['max_request_body_size'], 'never')

    def test_profiling_is_off(self):
        self.assertEqual(self.options()['profiles_sample_rate'], 0.0)

    def test_tracing_defaults_to_zero(self):
        import os
        os.environ.pop('SENTRY_TRACES_SAMPLE_RATE', None)
        self.assertEqual(self.options()['traces_sample_rate'], 0.0)

    def test_the_privacy_hooks_are_installed(self):
        options = self.options()
        self.assertIs(options['before_send'], sentry_setup.before_send)
        self.assertIs(options['before_breadcrumb'], sentry_setup.before_breadcrumb)
        self.assertIsNotNone(options['event_scrubber'])

    def test_debug_mode_is_off(self):
        self.assertIs(self.options()['debug'], False)

    def test_transaction_names_use_the_route_not_the_url(self):
        integration = self.options()['integrations'][0]
        self.assertEqual(integration.transaction_style, 'url')

    def test_no_dsn_is_committed_to_the_repository(self):
        import pathlib
        import re
        root = pathlib.Path(__file__).resolve().parent.parent
        # A real DSN is https://<key>@<org>.ingest.sentry.io/<project>.
        pattern = re.compile(r'https://[0-9a-f]{16,}@[\w.-]*ingest[\w.-]*sentry\.io')
        offenders = []
        for path_ in list(root.rglob('*.py')) + list(root.rglob('*.yml')) + \
                list(root.rglob('*.toml')) + list(root.rglob('*.txt')):
            rel = path_.relative_to(root).as_posix()
            if any(part in rel for part in ('node_modules/', '.venv/', 'staticfiles/')):
                continue
            if pattern.search(path_.read_text(encoding='utf-8', errors='ignore')):
                offenders.append(rel)
        self.assertEqual(offenders, [], f'a Sentry DSN appears committed: {offenders}')
