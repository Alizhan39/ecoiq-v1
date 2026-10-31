"""
Regression tests for the measured Render proxy topology.

The chain reproduced here is the one measured against production on 2026-08-07
by classifying hops rather than recording addresses:

    [ client-supplied entries ... , real client , Cloudflare edge ]

The infrastructure appends exactly two entries, so the client is at index -2.
Every "forged" address below is RFC 5737 TEST-NET-3, which never appears in real
traffic.
"""
import logging

from django.core.cache import cache
from django.test import RequestFactory, SimpleTestCase, override_settings

from core import client_origin as CO

FORGED = '203.0.113.9'            # what an attacker claims (TEST-NET-3)
CLIENT = '198.51.100.7'           # what Cloudflare observed (TEST-NET-2)
CF_EDGE = '104.16.0.1'            # Cloudflare edge, appended by Render
RENDER_INTERNAL = '10.201.3.4'    # REMOTE_ADDR behind Render

# Production shape: two trusted hops, no trusted header unless a test names one.
PROD = dict(TRUSTED_PROXY_COUNT=2, TRUSTED_CLIENT_IP_HEADER='',
            REQUEST_ORIGIN_HMAC_KEY='unit-test-origin-key',
            REQUEST_ORIGIN_HMAC_KEY_VERSION='v1')


def req(xff=None, remote=RENDER_INTERNAL, **headers):
    extra = {'REMOTE_ADDR': remote}
    if xff is not None:
        extra['HTTP_X_FORWARDED_FOR'] = xff
    extra.update(headers)
    return RequestFactory().get('/', **extra)


@override_settings(**PROD)
class MeasuredChainTests(SimpleTestCase):
    """1–5: the chain as production actually presents it."""

    def test_the_measured_production_chain_resolves_to_the_client(self):
        request = req(f'{CLIENT}, {CF_EDGE}')
        self.assertEqual(CO.client_ip(request), CLIENT)

    def test_a_normal_request_does_not_resolve_to_the_cloudflare_edge(self):
        # The old TRUSTED_PROXY_COUNT=1 picked CF_EDGE. That is the bug.
        self.assertNotEqual(CO.client_ip(req(f'{CLIENT}, {CF_EDGE}')), CF_EDGE)

    def test_one_forged_leftmost_entry_is_ignored(self):
        request = req(f'{FORGED}, {CLIENT}, {CF_EDGE}')
        self.assertEqual(CO.client_ip(request), CLIENT)

    def test_many_forged_entries_are_ignored(self):
        forged = ', '.join(f'203.0.113.{i}' for i in range(1, 25))
        request = req(f'{forged}, {CLIENT}, {CF_EDGE}')
        self.assertEqual(CO.client_ip(request), CLIENT)

    def test_a_chain_shorter_than_expected_fails_closed(self):
        # Not the topology we believe in: trust nothing, do not fall back to
        # REMOTE_ADDR (which is the same private address for every visitor).
        with self.assertLogs('core.client_origin', level='WARNING'):
            ip, status = CO.resolve_origin(req(FORGED))
        self.assertEqual(ip, '')
        self.assertEqual(status, CO.RESOLVED_CHAIN_TOO_SHORT)
        self.assertNotEqual(ip, RENDER_INTERNAL)


@override_settings(**PROD)
class HeaderAndFormatTests(SimpleTestCase):
    """6–12: headers, families, spellings, malformed input."""

    def test_missing_forwarded_header_yields_no_origin(self):
        ip, status = CO.resolve_origin(req())
        self.assertEqual(ip, '')
        self.assertEqual(status, CO.RESOLVED_CHAIN_TOO_SHORT)

    def test_malformed_entries_are_discarded_not_returned(self):
        for junk in ('not-an-address', '999.999.999.999', '<script>', '::gg'):
            with self.subTest(junk):
                request = req(f'{junk}, {CLIENT}, {CF_EDGE}')
                self.assertEqual(CO.client_ip(request), CLIENT)

    def test_ipv4_and_ipv6_clients_both_resolve(self):
        self.assertEqual(CO.client_ip(req(f'{CLIENT}, {CF_EDGE}')), CLIENT)
        self.assertEqual(CO.client_ip(req(f'2001:db8::1, {CF_EDGE}')), '2001:db8::1')

    def test_equivalent_ipv6_spellings_normalise_identically(self):
        for spelling in ('2001:db8::1', '2001:DB8:0:0:0:0:0:1',
                         '[2001:db8::1]:443', '2001:db8::1%eth0'):
            with self.subTest(spelling):
                self.assertEqual(CO.client_ip(req(f'{spelling}, {CF_EDGE}')),
                                 '2001:db8::1')

    def test_private_hops_are_classified_correctly(self):
        for private in ('10.0.0.1', '192.168.1.1', '172.16.0.1', '127.0.0.1',
                        '::1', 'fe80::1'):
            with self.subTest(private):
                self.assertTrue(CO.is_private(private))
        for public in ('8.8.8.8', '1.1.1.1', '2606:4700:4700::1111'):
            with self.subTest(public):
                self.assertFalse(CO.is_private(public))

    @override_settings(TRUSTED_CLIENT_IP_HEADER='CF-Connecting-IP')
    def test_a_trusted_header_wins_and_ignores_the_chain_entirely(self):
        # Cloudflare rejects client-supplied CF-Connecting-IP with HTTP 403
        # error 1000, so a value arriving here was set by the edge.
        request = req(f'{FORGED}, {CLIENT}, {CF_EDGE}', HTTP_CF_CONNECTING_IP=CLIENT)
        ip, status = CO.resolve_origin(request)
        self.assertEqual(ip, CLIENT)
        self.assertEqual(status, CO.RESOLVED_TRUSTED_HEADER)

    @override_settings(TRUSTED_CLIENT_IP_HEADER='')
    def test_an_unnamed_header_is_not_trusted_even_when_present(self):
        # Adding a CDN must be a configuration change, never implicit.
        request = req(f'{CLIENT}, {CF_EDGE}', HTTP_CF_CONNECTING_IP=FORGED)
        self.assertEqual(CO.client_ip(request), CLIENT)


@override_settings(**PROD)
class FingerprintTests(SimpleTestCase):
    """13–17: keyed correlation, never the address."""

    def test_fingerprint_is_stable_and_opaque(self):
        fp = CO.origin_fingerprint(CLIENT)
        self.assertTrue(fp)
        self.assertEqual(fp, CO.origin_fingerprint(CLIENT))
        # The address must not be recoverable from, or embedded in, the value.
        # Checking individual octets is meaningless — a hex digest contains
        # every digit — so assert on the address itself and on the shape.
        self.assertNotIn(CLIENT, fp)
        digest = fp.split(':', 1)[1]
        self.assertNotIn('.', digest)
        self.assertRegex(digest, r'^[0-9a-f]{16}$')
        # And it must be keyed: an unkeyed SHA-256 of the address is trivially
        # reversible by enumerating the address space.
        import hashlib
        self.assertNotIn(hashlib.sha256(CLIENT.encode()).hexdigest()[:16], fp)

    def test_different_origins_produce_different_fingerprints(self):
        self.assertNotEqual(CO.origin_fingerprint(CLIENT),
                            CO.origin_fingerprint('198.51.100.8'))

    def test_equivalent_ipv6_spellings_share_one_fingerprint(self):
        self.assertEqual(CO.origin_fingerprint('2001:db8::1'),
                         CO.origin_fingerprint('[2001:DB8:0:0:0:0:0:1]:443'))

    def test_rotating_the_key_or_version_changes_the_fingerprint(self):
        base = CO.origin_fingerprint(CLIENT)
        with override_settings(REQUEST_ORIGIN_HMAC_KEY='a-different-key'):
            self.assertNotEqual(CO.origin_fingerprint(CLIENT), base)
        with override_settings(REQUEST_ORIGIN_HMAC_KEY_VERSION='v2'):
            rotated = CO.origin_fingerprint(CLIENT)
        self.assertNotEqual(rotated, base)
        self.assertTrue(rotated.startswith('v2:'))

    @override_settings(REQUEST_ORIGIN_HMAC_KEY='', IS_PRODUCTION=True)
    def test_production_without_a_key_disables_fingerprinting_rather_than_using_a_literal(self):
        self.assertFalse(CO.fingerprinting_available())
        self.assertEqual(CO.origin_fingerprint(CLIENT), '')

    def test_unknown_origin_has_no_fingerprint(self):
        self.assertEqual(CO.origin_fingerprint(''), '')


@override_settings(**PROD)
class LoggingContextTests(SimpleTestCase):
    """18–20: what may be logged, and what may never be."""

    SENSITIVE = {
        'HTTP_COOKIE': 'sessionid=abc123secret; csrftoken=def456secret',
        'HTTP_AUTHORIZATION': 'Bearer supersecrettokenvalue',
        'HTTP_USER_AGENT': 'Mozilla/5.0 (identifying-string)',
        'HTTP_REFERER': 'https://example.com/private-page',
        'HTTP_CF_TURNSTILE_RESPONSE': 'turnstile-token-value',
    }

    def test_context_is_a_closed_key_set_and_leaks_nothing(self):
        request = req(f'{FORGED}, {CLIENT}, {CF_EDGE}')
        request.META.update(self.SENSITIVE)
        context = CO.safe_origin_context(request)

        self.assertEqual(set(context), {
            'origin_available', 'origin_fingerprint', 'origin_resolution_status',
            'origin_private', 'origin_family', 'forwarded_hop_count',
            'trusted_proxy_count', 'trusted_header_configured'})

        blob = repr(context)
        for value in list(self.SENSITIVE.values()) + [CLIENT, FORGED, CF_EDGE,
                                                      RENDER_INTERNAL,
                                                      'unit-test-origin-key']:
            self.assertNotIn(value, blob)

    def test_context_reports_the_structure_needed_to_spot_a_topology_change(self):
        context = CO.safe_origin_context(req(f'{FORGED}, {CLIENT}, {CF_EDGE}'))
        self.assertEqual(context['forwarded_hop_count'], 3)
        self.assertEqual(context['trusted_proxy_count'], 2)
        self.assertEqual(context['origin_resolution_status'],
                         CO.RESOLVED_FORWARDED_CHAIN)
        self.assertTrue(context['origin_available'])

    def test_the_chain_too_short_warning_carries_no_address(self):
        with self.assertLogs('core.client_origin', level='WARNING') as captured:
            CO.resolve_origin(req(FORGED))
        blob = '\n'.join(captured.output)
        for value in (FORGED, RENDER_INTERNAL, CLIENT):
            self.assertNotIn(value, blob)


@override_settings(**PROD)
class RateLimitIdentityTests(SimpleTestCase):
    """21–24: the property the whole change exists for."""

    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def test_forged_headers_cannot_mint_new_rate_limit_identities(self):
        from notifications.antispam import ratelimit
        from notifications.antispam.fingerprint import hashed_ip

        limit, _window = ratelimit.DEFAULTS['ip']
        exceeded = []
        # 25 different forged leftmost entries, one real client behind them.
        for i in range(limit + 15):
            request = req(f'203.0.113.{i}, {CLIENT}, {CF_EDGE}')
            resolved = CO.client_ip(request)
            self.assertEqual(resolved, CLIENT)      # never the forged value
            exceeded = ratelimit.check(ip=resolved, form='contact')
        self.assertIn('ip', exceeded)

        # All of them landed in one bucket, keyed on the real client.
        self.assertEqual(hashed_ip(CLIENT), hashed_ip(CO.client_ip(
            req(f'203.0.113.999-junk, {CLIENT}, {CF_EDGE}'))))

    def test_an_unknown_origin_still_consumes_a_bounded_shared_quota(self):
        from notifications.antispam import ratelimit

        limit, _window = ratelimit.DEFAULTS['ip']
        exceeded = []
        for _ in range(limit + 2):
            exceeded = ratelimit.check(ip='', form='contact')
        self.assertIn('ip', exceeded)

    def test_distinct_real_clients_keep_separate_quotas(self):
        from notifications.antispam import ratelimit

        limit, _window = ratelimit.DEFAULTS['ip']
        for _ in range(limit + 2):
            ratelimit.check(ip=CLIENT, form='contact')
        # A different genuine client must not be throttled by the first one.
        self.assertNotIn('ip', ratelimit.check(ip='198.51.100.200', form='contact'))

    def test_companies_throttle_uses_the_shared_resolver(self):
        from companies import throttle
        request = req(f'{FORGED}, {CLIENT}, {CF_EDGE}')
        self.assertEqual(throttle._client_ip(request), CLIENT)
        self.assertEqual(throttle._client_ip(req()), 'unknown')


class ResolverOwnershipTests(SimpleTestCase):
    """No application code may parse forwarding headers on its own."""

    def test_only_the_shared_resolver_and_diagnostics_read_forwarding_headers(self):
        import pathlib
        import re

        root = pathlib.Path(__file__).resolve().parent.parent
        allowed = {'core/client_origin.py'}
        pattern = re.compile(r'HTTP_X_FORWARDED_FOR|REMOTE_ADDR')
        offenders = []
        for path in root.rglob('*.py'):
            rel = path.relative_to(root).as_posix()
            # Only EcoIQ source is in scope. An in-tree virtualenv is the
            # documented dev setup (.claude/launch.json activates .venv), and
            # site-packages is full of legitimate WSGI/ASGI adapters that read
            # these headers — so without this the guard fails for every
            # developer and gets ignored, which is how a guard stops working.
            if rel.startswith('.') or 'site-packages/' in rel or 'node_modules/' in rel:
                continue
            if rel in allowed or '/tests' in rel or rel.startswith('tests'):
                continue
            if 'test' in path.name or 'migrations/' in rel:
                continue
            if pattern.search(path.read_text(encoding='utf-8', errors='ignore')):
                offenders.append(rel)
        self.assertEqual(offenders, [], f'forwarding headers parsed outside the resolver: {offenders}')


logging.getLogger('core.client_origin').addHandler(logging.NullHandler())
