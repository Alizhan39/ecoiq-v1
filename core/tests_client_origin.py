"""
Tests for trusted client-origin resolution.

The property under test throughout: a client cannot choose the address it is
recorded and rate-limited as, no matter what it puts in X-Forwarded-For.
"""
from django.test import RequestFactory, SimpleTestCase, override_settings

from core import client_origin as CO

SPOOFED = '203.0.113.9'          # what an attacker claims (TEST-NET-3)
REAL = '198.51.100.7'            # what our proxy actually saw (TEST-NET-2)
PROXY = '10.0.0.1'               # our own load balancer


def req(xff=None, remote=PROXY):
    extra = {'REMOTE_ADDR': remote}
    if xff is not None:
        extra['HTTP_X_FORWARDED_FOR'] = xff
    return RequestFactory().post('/contact/submit/', **extra)


class TrustedProxyParsingTests(SimpleTestCase):
    """1–4: the header is parsed from the right, and only as far as we trust it."""

    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_client_cannot_spoof_its_address_by_prepending_entries(self):
        # The client wrote SPOOFED; our proxy appended REAL after it.
        request = req(f'{SPOOFED}, {REAL}')
        self.assertEqual(CO.client_ip(request), REAL)

    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_a_long_forged_chain_still_resolves_to_the_real_client(self):
        forged = ', '.join(['198.18.0.%d' % i for i in range(1, 12)])
        request = req(f'{forged}, {REAL}')
        self.assertEqual(CO.client_ip(request), REAL)

    @override_settings(TRUSTED_PROXY_COUNT=0)
    def test_with_no_trusted_proxy_the_header_is_ignored_entirely(self):
        request = req(f'{SPOOFED}, {REAL}', remote=REAL)
        self.assertEqual(CO.client_ip(request), REAL)

    @override_settings(TRUSTED_PROXY_COUNT=2)
    def test_a_chain_shorter_than_expected_fails_closed(self):
        # Changed deliberately in the proxy-topology fix. This used to fall back
        # to REMOTE_ADDR, but behind Render that is a private address identical
        # for every visitor, so the fallback merged all traffic into one bucket
        # while looking like a successful resolution. Now it resolves to
        # nothing, and the caller uses its bounded "unknown" bucket.
        request = req(SPOOFED, remote=PROXY)
        self.assertEqual(CO.client_ip(request), '')
        self.assertNotEqual(CO.client_ip(request), PROXY)


class AddressFamilyTests(SimpleTestCase):
    """5–6: IPv4 and IPv6, including the spellings that would otherwise differ."""

    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_ipv6_is_resolved_and_normalised(self):
        for spelling in ('2001:db8::1', '2001:DB8:0:0:0:0:0:1',
                         '[2001:db8::1]:443', '2001:db8::1%eth0'):
            with self.subTest(spelling):
                request = req(f'{SPOOFED}, {spelling}')
                self.assertEqual(CO.client_ip(request), '2001:db8::1')

    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_malformed_entries_are_discarded_not_passed_through(self):
        for junk in ('not-an-address', '999.999.999.999', '', '<script>', '::gg'):
            with self.subTest(junk):
                request = req(f'{SPOOFED}, {junk}')
                # The junk entry is dropped, so the chain is [SPOOFED] and one
                # trusted hop resolves to it — which is still not the junk, and
                # never an unvalidated string.
                resolved = CO.client_ip(request)
                self.assertNotEqual(resolved, junk)
                self.assertTrue(resolved == '' or CO.normalise_ip(resolved) == resolved)


class FingerprintTests(SimpleTestCase):
    """7: what gets logged is a keyed hash, not an address."""

    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_fingerprint_is_stable_opaque_and_never_contains_the_address(self):
        request = req(f'{SPOOFED}, {REAL}')
        fp = CO.origin_fingerprint(request)

        self.assertTrue(fp)
        self.assertEqual(fp, CO.origin_fingerprint(request))          # stable
        self.assertEqual(fp, CO.origin_fingerprint(REAL))             # same origin
        self.assertNotEqual(fp, CO.origin_fingerprint('198.51.100.8'))  # different origin

        # Version-prefixed since the fingerprint rework ("v1:<digest>"), so a
        # colon is expected; the digest itself must still be opaque hex.
        self.assertNotIn(REAL, fp)
        self.assertNotIn(SPOOFED, fp)
        digest = fp.split(':', 1)[1]
        self.assertNotIn('.', digest)
        self.assertRegex(digest, r'^[0-9a-f]{16}$')

        # Equal IPv6 spellings must not produce different fingerprints, or an
        # IPv6 client evades every per-origin limit by varying the spelling.
        self.assertEqual(CO.origin_fingerprint('2001:db8::1'),
                         CO.origin_fingerprint('[2001:DB8:0:0:0:0:0:1]:443'))


class SafeContextTests(SimpleTestCase):
    """8: the logging context cannot leak credentials or identifiers."""

    FORBIDDEN_META = {
        'HTTP_COOKIE': 'sessionid=abc123secret; csrftoken=def456secret',
        'HTTP_AUTHORIZATION': 'Bearer supersecrettokenvalue',
        'HTTP_USER_AGENT': 'Mozilla/5.0 (identifying-string)',
        'HTTP_REFERER': 'https://example.com/private-page',
        'HTTP_CF_TURNSTILE_RESPONSE': 'turnstile-token-value',
    }

    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_context_has_a_closed_key_set_and_leaks_nothing(self):
        request = req(f'{SPOOFED}, {REAL}')
        request.META.update(self.FORBIDDEN_META)

        context = CO.safe_origin_context(request)

        self.assertEqual(set(context), {
            'origin_available', 'origin_fingerprint', 'origin_resolution_status',
            'origin_private', 'origin_family', 'forwarded_hop_count',
            'trusted_proxy_count', 'trusted_header_configured'})

        blob = repr(context)
        for value in self.FORBIDDEN_META.values():
            self.assertNotIn(value, blob)
        for secret in ('abc123secret', 'def456secret', 'supersecrettokenvalue',
                       'turnstile-token-value', REAL, SPOOFED):
            self.assertNotIn(secret, blob)

        self.assertEqual(context['origin_family'], 'ipv4')
        self.assertTrue(context['origin_available'])

    def test_private_ranges_are_flagged_and_public_ones_are_not(self):
        for private in ('10.0.0.1', '192.168.1.1', '172.16.0.1',
                        '127.0.0.1', '::1', 'fe80::1'):
            with self.subTest(private):
                self.assertTrue(CO.is_private(private))
        for public in ('8.8.8.8', '1.1.1.1', '2606:4700:4700::1111'):
            with self.subTest(public):
                self.assertFalse(CO.is_private(public))

    def test_an_unknown_origin_is_still_rate_limited_not_waved_through(self):
        from django.core.cache import cache

        from notifications.antispam import ratelimit

        cache.clear()
        limit, _window = ratelimit.DEFAULTS['ip']
        # An origin we cannot resolve must still consume a quota. Previously
        # this branch was skipped entirely and an unknown origin was unlimited.
        exceeded = []
        for _ in range(limit + 2):
            exceeded = ratelimit.check(ip='', email='', message='', form='contact')
        self.assertIn('ip', exceeded)
        cache.clear()

    @override_settings(TRUSTED_PROXY_COUNT=1)
    def test_unknown_origin_is_reported_as_unknown_not_guessed(self):
        request = RequestFactory().post('/contact/submit/')
        request.META.pop('REMOTE_ADDR', None)
        context = CO.safe_origin_context(request)
        self.assertFalse(context['origin_available'])
        self.assertEqual(context['origin_fingerprint'], '')
        self.assertEqual(context['origin_family'], 'none')
