"""
Invariants for structured logging.

These are not tests of structlog. They are tests of the promises this codebase
makes about what may reach a log line, written so that breaking a promise fails
CI rather than being discovered in an aggregator months later.

Every secret below is synthetic and marked `.invalid` or `TEST_`.
"""
import io
import json
import logging
import re
import threading

import structlog
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings

from core import events
from core.logging_middleware import (
    INBOUND_ID_RE, RequestContextMiddleware, bind_operation, clear_operation,
    current_context, incoming_request_id,
)
from core.logging_setup import REDACTED, configure_structlog, redact_sensitive

# Synthetic markers. If any of these reaches formatted output, a test fails.
MARKER_EMAIL = 'alice.testing@example.invalid'
MARKER_PASSWORD = 'TOP_SECRET_TEST_PASSWORD_91827'
MARKER_TOKEN = 'TEST_TOKEN_928374'
MARKER_MESSAGE = 'SENSITIVE_TEST_MESSAGE_18273'
MARKER_IPV4 = '203.0.113.77'
MARKER_IPV6 = '2001:db8::dead:beef'
MARKER_COOKIE = 'sessionid=TEST_SESSION_5551212'
MARKER_AUTH = 'Bearer TEST_BEARER_7654321'

ALL_MARKERS = (
    MARKER_EMAIL, MARKER_PASSWORD, MARKER_TOKEN, MARKER_MESSAGE,
    MARKER_IPV4, MARKER_IPV6, MARKER_COOKIE, MARKER_AUTH,
)


class CapturedLogs:
    """Capture formatted output exactly as a log aggregator would receive it."""

    def __init__(self, *, json_logs=True):
        self.json_logs = json_logs
        self.stream = io.StringIO()

    def __enter__(self):
        self._root = logging.getLogger()
        self._saved = list(self._root.handlers)
        self._saved_level = self._root.level
        self.handler = logging.StreamHandler(self.stream)
        self._root.handlers = [self.handler]
        self._root.setLevel(logging.DEBUG)
        configure_structlog(json_logs=self.json_logs)
        return self

    def __exit__(self, *exc):
        self._root.handlers = self._saved
        self._root.setLevel(self._saved_level)
        configure_structlog(json_logs=False)
        return False

    @property
    def text(self):
        return self.stream.getvalue()

    def records(self):
        return [json.loads(line) for line in self.text.splitlines() if line.strip()]


class RedactionTests(SimpleTestCase):
    """The processor itself, independent of transport."""

    def test_sensitive_keys_are_replaced(self):
        event = {
            'event': 'x', 'password': MARKER_PASSWORD, 'api_key': MARKER_TOKEN,
            'authorization': MARKER_AUTH, 'cookie': MARKER_COOKIE,
            'csrf_token': 'abc', 'database_url': 'postgres://u:p@h/db',
            'stripe_secret': 'sk_test_x', 'refresh_token': 'r',
        }
        out = redact_sensitive(None, 'info', event)
        for key in event:
            if key == 'event':
                continue
            with self.subTest(key):
                self.assertEqual(out[key], REDACTED)

    def test_personal_keys_are_replaced(self):
        event = {'email': MARKER_EMAIL, 'contact_name': 'Alice Example',
                 'phone': '+44 7700 900000', 'message': MARKER_MESSAGE,
                 'ip_address': MARKER_IPV4, 'client_ip': MARKER_IPV4}
        out = redact_sensitive(None, 'info', event)
        for key in event:
            with self.subTest(key):
                self.assertEqual(out[key], REDACTED)

    def test_addresses_are_scrubbed_even_under_an_innocent_key(self):
        # The case a key-name list alone would miss: someone hand-builds a
        # string and the address rides along inside it.
        out = redact_sensitive(None, 'info', {'detail': f'failed for {MARKER_IPV4}'})
        self.assertNotIn(MARKER_IPV4, out['detail'])
        out6 = redact_sensitive(None, 'info', {'detail': f'peer {MARKER_IPV6} gone'})
        self.assertNotIn(MARKER_IPV6, out6['detail'])

    def test_nested_structures_are_redacted(self):
        event = {'ctx': {'inner': {'password': MARKER_PASSWORD}},
                 'items': [{'email': MARKER_EMAIL}]}
        out = redact_sensitive(None, 'info', event)
        self.assertEqual(out['ctx']['inner']['password'], REDACTED)
        self.assertEqual(out['items'][0]['email'], REDACTED)

    def test_the_origin_fingerprint_survives(self):
        # It is the one correlation handle we have; redacting it would leave
        # abuse investigation with nothing.
        out = redact_sensitive(None, 'info', {'origin_fingerprint': 'v1:abc123def456'})
        self.assertEqual(out['origin_fingerprint'], 'v1:abc123def456')

    def test_business_objects_are_not_mutated(self):
        original = {'password': MARKER_PASSWORD}
        redact_sensitive(None, 'info', dict(original))
        self.assertEqual(original['password'], MARKER_PASSWORD)

    def test_redaction_does_not_reveal_length_or_prefix(self):
        out = redact_sensitive(None, 'info', {'token': 'abcdefghijklmnop'})
        self.assertEqual(out['token'], REDACTED)
        self.assertNotIn('abcd', out['token'])
        self.assertNotIn('16', out['token'])


class JsonRenderingTests(SimpleTestCase):
    """Production output has to be parseable, one record per line."""

    def test_output_is_one_valid_json_object_per_line(self):
        with CapturedLogs() as cap:
            log = structlog.get_logger('test')
            log.info('first_event', a=1)
            log.info('second_event', b=2)
        lines = [l for l in cap.text.splitlines() if l.strip()]
        self.assertEqual(len(lines), 2)
        for line in lines:
            with self.subTest(line=line[:40]):
                json.loads(line)

    def test_required_fields_are_present(self):
        with CapturedLogs() as cap:
            structlog.get_logger('test').info('an_event')
        record = cap.records()[0]
        for field in ('event', 'timestamp', 'level', 'service', 'environment'):
            with self.subTest(field):
                self.assertIn(field, record)
        self.assertEqual(record['event'], 'an_event')

    def test_no_ansi_escapes_in_json_output(self):
        with CapturedLogs() as cap:
            structlog.get_logger('test').warning('colourful')
        self.assertNotIn('\x1b[', cap.text)

    def test_field_types_are_stable(self):
        with CapturedLogs() as cap:
            structlog.get_logger('test').info(
                events.REQUEST_COMPLETED, status_code=200, duration_ms=12.5,
                origin_available=True, reason_codes=['a', 'b'])
        r = cap.records()[0]
        self.assertIsInstance(r['status_code'], int)
        self.assertIsInstance(r['duration_ms'], float)
        self.assertIsInstance(r['origin_available'], bool)
        self.assertIsInstance(r['reason_codes'], list)

    def test_stdlib_loggers_are_redacted_too(self):
        # 66 modules still call logging.getLogger(). They must not be a hole.
        with CapturedLogs() as cap:
            logging.getLogger('legacy.module').warning(
                'legacy line for %s', MARKER_IPV4)
        self.assertNotIn(MARKER_IPV4, cap.text)


class RequestIdTests(SimpleTestCase):

    def test_a_generated_id_is_opaque_and_unique(self):
        a = incoming_request_id(RequestFactory().get('/'))
        b = incoming_request_id(RequestFactory().get('/'))
        self.assertNotEqual(a, b)
        self.assertRegex(a, INBOUND_ID_RE)

    def test_a_valid_upstream_id_is_reused(self):
        request = RequestFactory().get('/', HTTP_X_REQUEST_ID='abc123-valid_ID.9')
        self.assertEqual(incoming_request_id(request), 'abc123-valid_ID.9')

    def test_hostile_upstream_ids_are_rejected(self):
        for hostile in (
            'x' * 500,                       # unbounded
            'short',                         # under the minimum
            'has spaces in it here',         # charset
            'newline\ninjected_log_line',    # log injection
            '{"json":"injection_attempt"}',
            '../../etc/passwd',
        ):
            with self.subTest(hostile[:24]):
                request = RequestFactory().get('/', HTTP_X_REQUEST_ID=hostile)
                got = incoming_request_id(request)
                self.assertNotEqual(got, hostile)
                self.assertRegex(got, INBOUND_ID_RE)


@override_settings(ALLOWED_HOSTS=['testserver'])
class MiddlewareTests(TestCase):

    def _run(self, view, **kwargs):
        return RequestContextMiddleware(view)(RequestFactory().get('/', **kwargs))

    def test_response_carries_the_request_id(self):
        from django.http import HttpResponse
        response = self._run(lambda r: HttpResponse('ok'))
        self.assertTrue(response['X-Request-ID'])
        self.assertRegex(response['X-Request-ID'], INBOUND_ID_RE)

    def test_lifecycle_events_are_emitted_with_stable_names(self):
        from django.http import HttpResponse
        with CapturedLogs() as cap:
            self._run(lambda r: HttpResponse('ok'))
        names = [r['event'] for r in cap.records()]
        self.assertIn(events.REQUEST_STARTED, names)
        self.assertIn(events.REQUEST_COMPLETED, names)

    def test_completion_reports_status_and_duration(self):
        from django.http import HttpResponse
        with CapturedLogs() as cap:
            self._run(lambda r: HttpResponse('ok', status=201))
        done = [r for r in cap.records() if r['event'] == events.REQUEST_COMPLETED][0]
        self.assertEqual(done['status_code'], 201)
        self.assertIsInstance(done['duration_ms'], float)

    def test_an_exception_logs_request_failed_and_still_propagates(self):
        def boom(request):
            raise ValueError('exploded')
        with CapturedLogs() as cap:
            with self.assertRaises(ValueError):
                self._run(boom)
        failed = [r for r in cap.records() if r['event'] == events.REQUEST_FAILED]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]['exception_type'], 'ValueError')

    def test_context_is_cleared_even_when_the_view_raises(self):
        def boom(request):
            raise ValueError('exploded')
        with self.assertRaises(ValueError):
            self._run(boom)
        self.assertEqual(current_context(), {})

    def test_context_does_not_leak_between_sequential_requests(self):
        from django.http import HttpResponse
        seen = []

        def view(request):
            seen.append(current_context()['request_id'])
            return HttpResponse('ok')

        mw = RequestContextMiddleware(view)
        mw(RequestFactory().get('/'))
        mw(RequestFactory().get('/'))
        self.assertEqual(len(set(seen)), 2, 'the second request reused the first id')
        self.assertEqual(current_context(), {})

    def test_context_does_not_leak_between_threads(self):
        from django.http import HttpResponse
        captured: dict[str, str] = {}
        barrier = threading.Barrier(2)

        def view(request):
            name = threading.current_thread().name
            # Hold both requests open simultaneously, so a shared (rather than
            # per-context) binding would be observable.
            barrier.wait(timeout=5)
            captured[name] = current_context()['request_id']
            return HttpResponse('ok')

        mw = RequestContextMiddleware(view)
        threads = [threading.Thread(target=lambda: mw(RequestFactory().get('/')),
                                    name=f't{i}') for i in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        self.assertEqual(len(captured), 2)
        self.assertEqual(len(set(captured.values())), 2, 'request ids bled across threads')

    def test_the_query_string_is_never_logged(self):
        from django.http import HttpResponse
        with CapturedLogs() as cap:
            RequestContextMiddleware(lambda r: HttpResponse('ok'))(
                RequestFactory().get(f'/?token={MARKER_TOKEN}&email={MARKER_EMAIL}'))
        self.assertNotIn(MARKER_TOKEN, cap.text)
        self.assertNotIn(MARKER_EMAIL, cap.text)

    def test_no_request_marker_of_any_kind_reaches_the_log(self):
        from django.http import HttpResponse
        with CapturedLogs() as cap:
            RequestContextMiddleware(lambda r: HttpResponse('ok'))(
                RequestFactory().post(
                    f'/?q={MARKER_MESSAGE}',
                    data={'email': MARKER_EMAIL, 'message': MARKER_MESSAGE},
                    HTTP_X_FORWARDED_FOR=f'{MARKER_IPV4}, 198.51.100.1, 104.16.0.1',
                    HTTP_AUTHORIZATION=MARKER_AUTH,
                    HTTP_COOKIE=MARKER_COOKIE,
                    HTTP_CF_TURNSTILE_RESPONSE=MARKER_TOKEN))
        for marker in ALL_MARKERS:
            with self.subTest(marker[:24]):
                self.assertNotIn(marker, cap.text)

    def test_no_address_shaped_string_appears_at_all(self):
        from django.http import HttpResponse
        with CapturedLogs() as cap:
            RequestContextMiddleware(lambda r: HttpResponse('ok'))(
                RequestFactory().get(
                    '/', HTTP_X_FORWARDED_FOR='203.0.113.5, 198.51.100.9, 104.16.0.1',
                    REMOTE_ADDR='10.201.3.4'))
        # Timestamps contain colons, so check the JSON values, not the raw text.
        for record in cap.records():
            for key, value in record.items():
                if key in ('timestamp',) or not isinstance(value, str):
                    continue
                with self.subTest(key):
                    self.assertIsNone(re.search(r'\b\d{1,3}(\.\d{1,3}){3}\b', value))

    def test_safe_origin_context_fields_are_present(self):
        from django.http import HttpResponse
        with CapturedLogs() as cap:
            RequestContextMiddleware(lambda r: HttpResponse('ok'))(RequestFactory().get('/'))
        record = cap.records()[0]
        for field in ('origin_available', 'origin_resolution_status',
                      'forwarded_hop_count', 'trusted_proxy_count'):
            with self.subTest(field):
                self.assertIn(field, record)


class OperationContextTests(SimpleTestCase):
    """Correlation for code with no HTTP request."""

    def test_bind_operation_is_distinct_from_request_id(self):
        try:
            op = bind_operation('classify_notification_spam')
            ctx = current_context()
            self.assertEqual(ctx['operation_id'], op)
            self.assertNotIn('request_id', ctx)
        finally:
            clear_operation()

    def test_clear_operation_removes_context(self):
        bind_operation('anything')
        clear_operation()
        self.assertEqual(current_context(), {})

    def test_logging_without_any_context_is_safe(self):
        clear_operation()
        with CapturedLogs() as cap:
            structlog.get_logger('test').info('no_context_event')
        self.assertEqual(cap.records()[0]['event'], 'no_context_event')


class RawIpLoggingRegressionTests(SimpleTestCase):
    """The specific defect this PR fixes, and a repo-wide guard against its return."""

    def test_throttle_logs_no_raw_address(self):
        from django.http import HttpResponse

        from companies import throttle

        @throttle.rate_limit('unit_test_limit')
        def view(request):
            return HttpResponse('ok')

        from django.core.cache import cache
        cache.clear()
        self.addCleanup(cache.clear)

        with CapturedLogs() as cap:
            for _ in range(throttle.ANON_PER_MIN + 2):
                request = RequestFactory().get(
                    '/', HTTP_X_FORWARDED_FOR=f'{MARKER_IPV4}, 198.51.100.9, 104.16.0.1')
                request.user = None
                view(request)

        self.assertIn(events.RATE_LIMIT_APPLIED, cap.text)
        self.assertNotIn(MARKER_IPV4, cap.text)
        self.assertNotIn('198.51.100.9', cap.text)

    def test_only_the_origin_resolver_reads_forwarding_headers(self):
        import pathlib

        root = pathlib.Path(__file__).resolve().parent.parent
        allowed = {'core/client_origin.py'}
        pattern = re.compile(r'HTTP_X_FORWARDED_FOR|REMOTE_ADDR')
        offenders = []
        for path in root.rglob('*.py'):
            rel = path.relative_to(root).as_posix()
            if rel in allowed or '/tests' in rel or 'test' in path.name:
                continue
            if 'migrations/' in rel:
                continue
            if pattern.search(path.read_text(encoding='utf-8', errors='ignore')):
                offenders.append(rel)
        self.assertEqual(offenders, [], f'forwarding headers parsed outside the resolver: {offenders}')
