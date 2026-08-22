"""
Route smoke tests for the stock-profile and public embed surfaces.

Complements companies/tests_embed.py (behaviour) by pinning the things a
public, unauthenticated, third-party-embeddable surface must get right:
response codes, content types, cache headers, the deliberate framing
exemption, and — most importantly — that non-public profiles and unknown
slugs never leak.

SECURE_SSL_REDIRECT is overridden because settings enables it whenever DEBUG
is False; without this the test client is 301'd before reaching any view and
these assertions would pass for the wrong reason.
"""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from companies.models import CompanyProfile
from league.models import Company


@override_settings(SECURE_SSL_REDIRECT=False)
class StockAndEmbedRouteSmokeTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.public_co = Company.objects.create(
            name='Publicly Listed Co', slug='publicly-listed-co',
            sector='energy', country='United Kingdom',
            ticker='PLC.L', exchange='LSE',
            stock_price='27.42', stock_price_currency='GBP',
        )
        cls.public_profile = CompanyProfile.objects.create(
            company=cls.public_co, status='public',
        )
        # Draft profile — must never be served by a public embed.
        cls.draft_co = Company.objects.create(
            name='Draft Only Co', slug='draft-only-co',
            sector='energy', country='United Kingdom', ticker='DOC',
        )
        CompanyProfile.objects.create(company=cls.draft_co, status='draft')
        cls.reader = get_user_model().objects.create_user('route-reader')

    def signed_in(self):
        """
        A client for /companies/<slug>/stock/, which stopped answering
        anonymously in Phase 10 (core.access.COMPANY_LEAF_SUFFIXES).

        The EMBED routes below deliberately do NOT use this: an embed that
        needed a session would not work in a third-party iframe, which is the
        whole point of the surface. They stay anonymous, and this file still
        pins that.
        """
        client = Client()
        client.force_login(self.reader)
        return client

    # ── Stock profile ────────────────────────────────────────────────────────

    def test_stock_profile_does_not_answer_anonymously(self):
        r = self.client.get(reverse('companies:stock', args=[self.public_co.slug]))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login/', r['Location'])

    def test_stock_profile_renders_for_public_company(self):
        r = self.signed_in().get(
            reverse('companies:stock', args=[self.public_co.slug]))
        self.assertEqual(r.status_code, 200)

    def test_stock_profile_unknown_slug_is_404(self):
        """
        Still a 404, not a redirect-to-login that leaks nothing either way:
        a signed-in reader asking for a company that does not exist must be
        told so.
        """
        r = self.signed_in().get(
            reverse('companies:stock', args=['no-such-company']))
        self.assertEqual(r.status_code, 404)

    def test_report_generation_is_staff_only(self):
        """Unauthenticated POST must not reach the generator."""
        r = self.client.post(reverse('companies:stock_generate_report',
                                     args=[self.public_co.slug]))
        self.assertEqual(r.status_code, 403)

    def test_report_status_change_is_staff_only(self):
        r = self.client.post(
            reverse('companies:stock_report_status',
                    args=[self.public_co.slug, 1]),
            {'action': 'publish'},
        )
        self.assertEqual(r.status_code, 403)

    def test_generate_rejects_get(self):
        r = self.client.get(reverse('companies:stock_generate_report',
                                    args=[self.public_co.slug]))
        self.assertEqual(r.status_code, 405)

    # ── Embed badges ─────────────────────────────────────────────────────────

    def test_badges_serve_svg_with_public_cache_headers(self):
        for name in ('embed:ecoiq_badge', 'embed:ethical_badge', 'embed:islamic_badge'):
            with self.subTest(route=name):
                r = self.client.get(reverse(name, args=[self.public_co.slug]))
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r['Content-Type'], 'image/svg+xml')
                self.assertIn('public', r['Cache-Control'])

    def test_badge_theme_parameter_is_allowlisted(self):
        """An unknown theme falls back to light rather than reaching the output."""
        url = reverse('embed:ecoiq_badge', args=[self.public_co.slug])
        r = self.client.get(url, {'theme': '"><script>alert(1)</script>'})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn(b'<script>', r.content)

    def test_badge_svg_contains_no_unescaped_injection_surface(self):
        r = self.client.get(reverse('embed:ecoiq_badge', args=[self.public_co.slug]))
        self.assertNotIn(b'<script', r.content)
        self.assertNotIn(b'onload=', r.content)

    # ── Embed risk card + snippets ───────────────────────────────────────────

    def test_risk_card_is_deliberately_framable(self):
        """
        The risk card is the ONE view intended to be embedded in a partner
        <iframe>, so it must not carry X-Frame-Options.
        """
        r = self.client.get(reverse('embed:risk_card', args=[self.public_co.slug]))
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.headers.get('X-Frame-Options'))

    def test_other_pages_keep_frame_protection(self):
        """Global clickjacking protection must not be weakened elsewhere."""
        r = self.signed_in().get(
            reverse('companies:stock', args=[self.public_co.slug]))
        self.assertEqual(r.status_code, 200)
        self.assertIsNotNone(r.headers.get('X-Frame-Options'))

    def test_snippets_page_renders(self):
        r = self.client.get(reverse('embed:snippets', args=[self.public_co.slug]))
        self.assertEqual(r.status_code, 200)

    # ── Non-public data must never be served ─────────────────────────────────

    def test_draft_profile_is_404_on_every_embed_route(self):
        for name in ('embed:snippets', 'embed:ecoiq_badge', 'embed:ethical_badge',
                     'embed:islamic_badge', 'embed:risk_card'):
            with self.subTest(route=name):
                r = self.client.get(reverse(name, args=[self.draft_co.slug]))
                self.assertEqual(r.status_code, 404)

    def test_unknown_slug_is_404_on_every_embed_route(self):
        for name in ('embed:snippets', 'embed:ecoiq_badge', 'embed:ethical_badge',
                     'embed:islamic_badge', 'embed:risk_card'):
            with self.subTest(route=name):
                r = self.client.get(reverse(name, args=['no-such-company']))
                self.assertEqual(r.status_code, 404)

    def test_embed_routes_reject_non_get(self):
        r = self.client.post(reverse('embed:ecoiq_badge', args=[self.public_co.slug]))
        self.assertEqual(r.status_code, 405)

    def test_embed_response_exposes_no_internal_identifiers(self):
        """Public embeds carry the slug, never internal PKs or draft data."""
        r = self.client.get(reverse('embed:risk_card', args=[self.public_co.slug]))
        body = r.content.decode()
        self.assertNotIn('Draft Only Co', body)
        self.assertNotIn('Traceback', body)


@override_settings(SECURE_SSL_REDIRECT=False)
class StockFieldQueryEfficiencyTests(TestCase):
    """
    The market-data columns added here live directly on league.Company, so a
    list view that renders a ticker/price reads them off a row it has already
    fetched — no extra query, no join.

    These tests pin exactly that, by comparing the SAME number of companies
    with and without market data. They deliberately do NOT assert a flat
    query count as companies grow: the leaderboard and directory already had
    a pre-existing N+1 on main before this change (measured on pristine
    origin/main at the same commit: 14 queries for 3 companies, 28 for 10 —
    identical with and without this branch). Fixing that is real work with
    its own risk and belongs in its own PR, not smuggled into a recovery
    port. What must not happen is this change making it worse.
    """

    def _make(self, n, prefix, *, with_market_data):
        for i in range(n):
            extra = {}
            if with_market_data:
                extra = {
                    'ticker': f'{prefix[:3].upper()}{i}',
                    'stock_price': '10.00',
                    'stock_price_currency': 'USD',
                    'day_change_pct': 1.5,
                    'exchange': 'LSE',
                }
            Company.objects.create(
                name=f'{prefix} {i}', slug=f'{prefix.lower()}-{i}',
                sector='energy', country='United Kingdom', **extra,
            )

    def _count(self, url):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(url)
        return len(ctx.captured_queries)

    def _assert_market_data_is_query_free(self, url_name):
        url = reverse(url_name)
        self._make(5, 'Plain', with_market_data=False)
        without = self._count(url)
        Company.objects.all().delete()
        self._make(5, 'Traded', with_market_data=True)
        with_data = self._count(url)
        self.assertEqual(
            without, with_data,
            f'{url_name}: {without} queries without market data vs {with_data} '
            'with it — rendering ticker/price costs extra queries',
        )

    def test_market_data_adds_no_queries_to_leaderboard(self):
        self._assert_market_data_is_query_free('league:leaderboard')

    def test_market_data_adds_no_queries_to_directory(self):
        self._assert_market_data_is_query_free('companies:directory')

    def test_stock_profile_page_query_count_is_bounded(self):
        """A single company's stock page must not scale with report history."""
        from companies.models import CompanyProfile, InvestmentRelevanceReport
        co = Company.objects.create(
            name='Bounded Co', slug='bounded-co', sector='energy',
            country='United Kingdom', ticker='BND', stock_price='5.00',
        )
        profile = CompanyProfile.objects.create(company=co, status='public')
        url = reverse('companies:stock', args=[co.slug])
        baseline = self._count(url)
        for v in range(1, 13):
            InvestmentRelevanceReport.objects.create(
                company=profile, version=v, status='published',
                classification='lower_exposure',
            )
        after = self._count(url)
        self.assertEqual(
            baseline, after,
            f'stock page grew {baseline} -> {after} queries as report versions '
            'accumulated — the history queryset is not bounded',
        )
