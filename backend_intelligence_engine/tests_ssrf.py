"""
SSRF tests for the shared HTTP client and the URL validator.

No test here touches the network. DNS is patched at
`company_intelligence.services.url_safety.socket.getaddrinfo` — the same seam
company_intelligence's own tests already use — and HTTP at `httpx.Client`, so
the whole redirect chain is exercised without a socket being opened.

The attack this file exists to prevent, concretely: a staff member registers
`https://attacker.example/report.pdf`, which is public and passes validation at
registration time. The later fetch receives
`302 Location: http://169.254.169.254/latest/meta-data/iam/security-credentials/`
and, before this change, followed it and stored the response as evidence text.
"""
from unittest.mock import patch

from django.test import SimpleTestCase

from backend_intelligence_engine.services import http_client
from company_intelligence.services import url_safety

PUBLIC_IP = '93.184.216.34'


def _dns(mapping, default=None):
    """A fake resolver: hostname -> list of addresses."""
    def _resolve(host, *_a, **_k):
        import socket as _socket
        addrs = mapping.get(host, default)
        if addrs is None:
            raise _socket.gaierror(f'no fixture for {host}')
        return [(2, 1, 6, '', (a, 0)) for a in addrs]
    return _resolve


def _response(status=200, headers=None, content=b'ok', is_redirect=False):
    return type('R', (), {
        'status_code': status,
        'headers': headers or {},
        'content': content,
        'text': content.decode(errors='replace'),
        'is_redirect': is_redirect,
        'json': lambda self: {},
    })()


def _redirect_to(location):
    return _response(status=302, headers={'location': location}, is_redirect=True)


class _ChainClient:
    """
    Stands in for httpx.Client and serves a scripted sequence of responses,
    recording every URL actually requested. What was requested is the real
    assertion — a test that only checks the return value cannot tell the
    difference between "refused to follow" and "followed and then failed".
    """

    requested: list = []
    script: list = []

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def request(self, method, url, **kwargs):
        type(self).requested.append(url)
        if not type(self).script:
            return _response()
        return type(self).script.pop(0)

    @classmethod
    def arm(cls, script):
        cls.requested = []
        cls.script = list(script)


# ── The validator ────────────────────────────────────────────────────────────

class UrlValidatorTests(SimpleTestCase):

    def _assert_blocked(self, url, category=None):
        verdict = url_safety.validate_url(url)
        self.assertFalse(verdict.safe, f'expected {url!r} to be blocked')
        if category:
            self.assertEqual(verdict.category, category)
        return verdict

    @patch('company_intelligence.services.url_safety.socket.getaddrinfo',
           _dns({'public.example': [PUBLIC_IP]}))
    def test_public_https_url_is_allowed(self):
        self.assertTrue(url_safety.validate_url('https://public.example/report.pdf').safe)

    @patch('company_intelligence.services.url_safety.socket.getaddrinfo',
           _dns({'public.example': [PUBLIC_IP]}))
    def test_public_http_url_is_allowed(self):
        self.assertTrue(url_safety.validate_url('http://public.example/report.pdf').safe)

    def test_direct_private_ipv4_blocked(self):
        for addr in ('10.0.0.5', '172.16.0.1', '192.168.1.1', '127.0.0.1', '0.0.0.0'):
            self._assert_blocked(f'http://{addr}/x', url_safety.CATEGORY_PRIVATE_IP)

    def test_carrier_grade_nat_blocked(self):
        """
        100.64.0.0/10 is RFC 6598 shared address space and `is_private` returns
        False for it, so it is checked explicitly. Widely used for internal
        infrastructure — a gap the stdlib flags alone would have left open.
        """
        self._assert_blocked('http://100.64.0.1/x', url_safety.CATEGORY_PRIVATE_IP)

    def test_direct_private_ipv6_blocked(self):
        for addr in ('[::1]', '[fc00::1]', '[fe80::1]'):
            self._assert_blocked(f'http://{addr}/x', url_safety.CATEGORY_PRIVATE_IP)

    def test_ipv4_mapped_ipv6_blocked(self):
        for addr in ('[::ffff:127.0.0.1]', '[::ffff:10.0.0.5]'):
            self._assert_blocked(f'http://{addr}/x', url_safety.CATEGORY_PRIVATE_IP)

    def test_cloud_metadata_address_blocked(self):
        self._assert_blocked('http://169.254.169.254/latest/meta-data/',
                             url_safety.CATEGORY_PRIVATE_IP)

    def test_localhost_names_blocked(self):
        for host in ('localhost', 'foo.localhost', 'db.internal', 'printer.local'):
            self._assert_blocked(f'http://{host}/x', url_safety.CATEGORY_HOSTNAME)

    @patch('company_intelligence.services.url_safety.socket.getaddrinfo',
           _dns({'2130706433': ['127.0.0.1'], '0x7f000001': ['127.0.0.1'], '127.1': ['127.0.0.1']}))
    def test_alternative_ip_representations_blocked(self):
        """
        `2130706433`, `0x7f000001` and `127.1` are not parseable as IP literals,
        so they reach the DNS branch — where the resolver returns 127.0.0.1 and
        the address check rejects them. Resolving before judging is what makes
        this work without enumerating every notation.
        """
        for host in ('2130706433', '0x7f000001', '127.1'):
            self._assert_blocked(f'http://{host}/x', url_safety.CATEGORY_PRIVATE_IP)

    def test_non_http_schemes_blocked(self):
        for url in ('ftp://example.com/f', 'file:///etc/passwd', 'gopher://example.com/',
                    'data:text/plain,hi'):
            self._assert_blocked(url, url_safety.CATEGORY_SCHEME)

    def test_embedded_credentials_blocked(self):
        self._assert_blocked('https://user:pw@public.example/x', url_safety.CATEGORY_CREDENTIALS)

    @patch('company_intelligence.services.url_safety.socket.getaddrinfo',
           _dns({'169.254.169.254': ['169.254.169.254']}))
    def test_credentials_cannot_disguise_the_real_host(self):
        """`https://trusted.example.com@169.254.169.254/` reads as trusted."""
        self._assert_blocked('https://trusted.example.com@169.254.169.254/latest/',
                             url_safety.CATEGORY_CREDENTIALS)

    @patch('company_intelligence.services.url_safety.socket.getaddrinfo',
           _dns({'public.example': [PUBLIC_IP]}))
    def test_non_standard_ports_blocked(self):
        for port in (22, 6379, 5432, 8080, 11211):
            self._assert_blocked(f'http://public.example:{port}/x', url_safety.CATEGORY_PORT)

    @patch('company_intelligence.services.url_safety.socket.getaddrinfo',
           _dns({'public.example': [PUBLIC_IP]}))
    def test_standard_ports_allowed(self):
        for port in (80, 443):
            self.assertTrue(url_safety.validate_url(f'http://public.example:{port}/x').safe)

    def test_malformed_urls_blocked(self):
        for url in ('', 'not a url', 'http://', '://x', None, 12345):
            self.assertFalse(url_safety.validate_url(url).safe)

    @patch('company_intelligence.services.url_safety.socket.getaddrinfo',
           _dns({'sneaky.example': ['10.0.0.5']}))
    def test_dns_resolving_to_private_address_blocked(self):
        self._assert_blocked('https://sneaky.example/x', url_safety.CATEGORY_PRIVATE_IP)

    @patch('company_intelligence.services.url_safety.socket.getaddrinfo',
           _dns({'split.example': [PUBLIC_IP, '10.0.0.5']}))
    def test_mixed_public_and_private_dns_answers_blocked(self):
        """
        One public answer and one internal one must be refused. "The first
        answer was public" is the wrong reading — the connection could use
        either.
        """
        self._assert_blocked('https://split.example/x', url_safety.CATEGORY_PRIVATE_IP)

    @patch('company_intelligence.services.url_safety.socket.getaddrinfo', _dns({}))
    def test_dns_failure_is_blocked_not_a_crash(self):
        self._assert_blocked('https://no-such-host.invalid/x', url_safety.CATEGORY_DNS)

    def test_every_rejection_returns_the_same_public_reason(self):
        """
        A caller must not be able to distinguish a blocked port from a private
        DNS answer. Differing messages turn the registration form into an
        internal network oracle.
        """
        reasons = set()
        for url in ('ftp://example.com/f', 'http://10.0.0.5/x', 'http://localhost/x',
                    'https://u:p@public.example/x', ''):
            reasons.add(url_safety.validate_url(url).public_reason)
        self.assertEqual(reasons, {url_safety.PUBLIC_REJECTION})

    def test_detail_is_kept_out_of_the_public_reason(self):
        verdict = url_safety.validate_url('http://10.0.0.5/x')
        self.assertIn('10.0.0.5', verdict.detail)
        self.assertNotIn('10.0.0.5', verdict.public_reason)


# ── The fetch layer: redirects ───────────────────────────────────────────────

@patch('company_intelligence.services.url_safety.socket.getaddrinfo',
       _dns({'public.example': [PUBLIC_IP], 'evil.example': [PUBLIC_IP],
             'hop2.example': [PUBLIC_IP], 'internal.example': ['10.0.0.5']}))
class RedirectRevalidationTests(SimpleTestCase):

    def _fetch(self, url, script):
        _ChainClient.arm(script)
        with patch('httpx.Client', _ChainClient):
            return http_client.fetch(url, max_retries=0)

    def test_public_url_redirecting_to_metadata_service_is_refused(self):
        """The headline case."""
        result = self._fetch('https://evil.example/report.pdf', [
            _redirect_to('http://169.254.169.254/latest/meta-data/'),
        ])
        self.assertFalse(result.success)
        self.assertEqual(result.error, http_client.BLOCKED_ERROR)
        self.assertNotIn('169.254.169.254', _ChainClient.requested,
                         'the metadata address was actually requested')
        self.assertEqual(_ChainClient.requested, ['https://evil.example/report.pdf'])

    def test_redirect_to_private_ip_is_refused(self):
        result = self._fetch('https://evil.example/x', [_redirect_to('http://10.0.0.5/admin')])
        self.assertFalse(result.success)
        self.assertEqual(len(_ChainClient.requested), 1)

    def test_multi_hop_redirect_ending_at_private_ip_is_refused(self):
        """Two public hops then an internal one — only the last is malicious."""
        result = self._fetch('https://evil.example/a', [
            _redirect_to('https://hop2.example/b'),
            _redirect_to('http://10.0.0.5/c'),
        ])
        self.assertFalse(result.success)
        self.assertEqual(_ChainClient.requested,
                         ['https://evil.example/a', 'https://hop2.example/b'])

    def test_relative_redirect_is_resolved_then_validated(self):
        """A relative Location must not skip validation by carrying no host."""
        result = self._fetch('https://public.example/a', [
            _redirect_to('/b'), _response(content=b'final'),
        ])
        self.assertTrue(result.success)
        self.assertEqual(_ChainClient.requested,
                         ['https://public.example/a', 'https://public.example/b'])

    def test_scheme_relative_redirect_to_private_host_is_refused(self):
        result = self._fetch('https://evil.example/a', [_redirect_to('//internal.example/x')])
        self.assertFalse(result.success)
        self.assertEqual(len(_ChainClient.requested), 1)

    def test_protocol_switch_redirect_to_unsupported_scheme_is_refused(self):
        result = self._fetch('https://evil.example/a', [_redirect_to('file:///etc/passwd')])
        self.assertFalse(result.success)
        self.assertEqual(result.error, http_client.BLOCKED_ERROR)

    def test_redirect_loop_is_bounded(self):
        result = self._fetch('https://public.example/a',
                             [_redirect_to('https://public.example/a')] * 20)
        self.assertFalse(result.success)
        self.assertLessEqual(len(_ChainClient.requested), http_client.MAX_REDIRECTS + 1)

    def test_excessive_redirect_count_is_refused(self):
        script = [_redirect_to(f'https://public.example/{i}')
                  for i in range(http_client.MAX_REDIRECTS + 3)]
        result = self._fetch('https://public.example/start', script)
        self.assertFalse(result.success)
        self.assertEqual(len(_ChainClient.requested), http_client.MAX_REDIRECTS + 1)

    def test_redirect_without_location_is_refused(self):
        result = self._fetch('https://public.example/a',
                             [_response(status=302, is_redirect=True)])
        self.assertFalse(result.success)

    def test_allowed_redirect_chain_still_works(self):
        """The guard must not break a legitimate http->https, bare->www hop."""
        result = self._fetch('http://public.example/a', [
            _redirect_to('https://public.example/a'),
            _response(content=b'report'),
        ])
        self.assertTrue(result.success)
        self.assertEqual(result.final_url, 'https://public.example/a')
        self.assertEqual(result.content, b'report')

    def test_blocked_result_never_leaks_the_internal_address(self):
        result = self._fetch('https://evil.example/x', [_redirect_to('http://10.0.0.5/admin')])
        self.assertNotIn('10.0.0.5', result.error)
        self.assertNotIn('10.0.0.5', repr(result))

    def test_a_refusal_is_not_retried(self):
        """
        A refused destination is a permanent verdict. Retrying it would mean
        three DNS lookups and three log lines for the same answer.
        """
        _ChainClient.arm([_redirect_to('http://10.0.0.5/x')])
        with patch('httpx.Client', _ChainClient), \
             patch('backend_intelligence_engine.services.http_client.time.sleep') as sleep:
            result = http_client.fetch('https://evil.example/x', max_retries=2)
        self.assertFalse(result.success)
        self.assertEqual(result.attempts, 1)
        sleep.assert_not_called()

    def test_initial_url_is_validated_before_any_request(self):
        _ChainClient.arm([_response()])
        with patch('httpx.Client', _ChainClient):
            result = http_client.fetch('http://169.254.169.254/latest/', max_retries=0)
        self.assertFalse(result.success)
        self.assertEqual(_ChainClient.requested, [], 'a request was made to a blocked URL')

    def test_oversize_response_is_refused_not_truncated(self):
        big = b'x' * (http_client.MAX_RESPONSE_BYTES + 1)
        result = self._fetch('https://public.example/a', [_response(content=big)])
        self.assertFalse(result.success)
        self.assertIn('cap', result.error)

    def test_validation_can_be_disabled_only_explicitly(self):
        """The escape hatch exists, but nothing reaches it by accident."""
        _ChainClient.arm([_response(content=b'ok')])
        with patch('httpx.Client', _ChainClient):
            result = http_client.fetch('http://10.0.0.5/x', max_retries=0, validate=False)
        self.assertTrue(result.success)
        self.assertEqual(_ChainClient.requested, ['http://10.0.0.5/x'])


class TimeoutBehaviourTests(SimpleTestCase):

    @patch('company_intelligence.services.url_safety.socket.getaddrinfo',
           _dns({'public.example': [PUBLIC_IP]}))
    def test_timeout_returns_a_safe_error_not_an_exception(self):
        import httpx

        with patch('httpx.Client') as MockClient, \
             patch('backend_intelligence_engine.services.http_client.time.sleep'):
            MockClient.return_value.__enter__.side_effect = httpx.ConnectTimeout('timed out')
            result = http_client.fetch('https://public.example/x', max_retries=1)
        self.assertFalse(result.success)
        self.assertIn('ConnectTimeout', result.error)
