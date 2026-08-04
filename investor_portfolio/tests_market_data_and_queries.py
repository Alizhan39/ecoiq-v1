"""
Group E hardening tests: market-data integration, query efficiency, and
cross-user isolation proven under CI conditions.

investor_portfolio/tests_permissions.py already covers ownership with two
ordinary users and one staff user. It does NOT disable SECURE_SSL_REDIRECT,
which settings turns on whenever DEBUG is False — the value CI uses. Under
CI those tests get a 301 before reaching a view, so an isolation assertion
would pass without the authorisation code ever running. The isolation tests
here are deliberately duplicated with the redirect disabled so the guarantee
holds in both environments.

Market data is read from league.Company (populated by the ingest_yfinance
command). Nothing here fetches, caches or redistributes market data.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from investor_portfolio.calculations import _holding_value
from investor_portfolio.models import Holding, Portfolio, Watchlist
from league.models import Company

User = get_user_model()


def _company(slug, **kw):
    defaults = dict(
        name=slug.replace('-', ' ').title(), slug=slug,
        sector='energy', country='United Kingdom',
    )
    defaults.update(kw)
    return Company.objects.create(**defaults)


@override_settings(SECURE_SSL_REDIRECT=False)
class MarketDataIntegrationTests(TestCase):
    """
    Missing, stale and current prices must be three distinguishable states.
    A missing price must never be silently valued at zero.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('mduser', password='x')
        cls.portfolio = Portfolio.objects.create(
            owner=cls.user, name='MD Portfolio', base_currency='USD',
        )

    def _holding(self, company, **kw):
        return Holding.objects.create(
            portfolio=self.portfolio, company=company,
            shares=Decimal("10"), **kw,
        )

    def test_current_price_produces_a_value_and_is_not_stale(self):
        co = _company('fresh-co', ticker='FRSH', stock_price=Decimal('20.00'),
                      stock_price_currency='USD',
                      stock_price_updated_at=timezone.now())
        value, currency, missing, stale, updated = _holding_value(self._holding(co))
        self.assertEqual(value, Decimal('200.00'))
        self.assertEqual(currency, 'USD')
        self.assertFalse(missing)
        self.assertFalse(stale)
        self.assertIsNotNone(updated)

    def test_stale_price_still_values_but_is_flagged(self):
        old = timezone.now() - timezone.timedelta(hours=Company.STOCK_STALE_AFTER_HOURS + 5)
        co = _company('stale-co', ticker='STL', stock_price=Decimal('20.00'),
                      stock_price_currency='USD', stock_price_updated_at=old)
        value, _cur, missing, stale, updated = _holding_value(self._holding(co))
        self.assertEqual(value, Decimal('200.00'))
        self.assertFalse(missing)
        self.assertTrue(stale, 'a price older than the trust window must be flagged stale')
        self.assertEqual(updated, old)

    def test_missing_price_is_none_never_zero(self):
        co = _company('no-price-co', ticker='NOP')
        value, currency, missing, stale, updated = _holding_value(self._holding(co))
        self.assertIsNone(value, 'a missing price must never become 0')
        self.assertIsNone(currency)
        self.assertTrue(missing)
        self.assertFalse(stale)
        self.assertIsNone(updated)

    def test_private_company_with_no_ticker_is_missing_not_zero(self):
        co = _company('private-co')
        value, _c, missing, _s, _u = _holding_value(self._holding(co))
        self.assertIsNone(value)
        self.assertTrue(missing)

    def test_manual_value_is_used_only_when_market_data_absent(self):
        co = _company('manual-co')
        h = self._holding(co, manual_current_value=Decimal('500.00'))
        value, currency, missing, _s, _u = _holding_value(h)
        self.assertEqual(value, Decimal('500.00'))
        self.assertEqual(currency, 'USD')
        self.assertFalse(missing)

    def test_market_price_wins_over_manual_value(self):
        co = _company('both-co', ticker='BTH', stock_price=Decimal('20.00'),
                      stock_price_currency='USD',
                      stock_price_updated_at=timezone.now())
        h = self._holding(co, manual_current_value=Decimal('999.00'))
        value, _c, _m, _s, _u = _holding_value(h)
        self.assertEqual(value, Decimal('200.00'))

    def test_pence_quoting_is_normalised_before_arithmetic(self):
        """Yahoo quotes LSE tickers in GBp. 2742p is £27.42, not £2,742."""
        co = _company('pence-co', ticker='PNC.L', stock_price=Decimal('2742.00'),
                      stock_price_currency='GBp',
                      stock_price_updated_at=timezone.now())
        value, currency, _m, _s, _u = _holding_value(self._holding(co))
        self.assertEqual(currency, 'GBP')
        self.assertEqual(value, Decimal('274.20'))

    def test_dashboard_renders_with_a_priceless_holding(self):
        self._holding(_company('dash-nop', ticker='DNP'))
        self.client.force_login(self.user)
        r = self.client.get(reverse('portfolio:portfolio_dashboard', args=[self.portfolio.pk]))
        self.assertEqual(r.status_code, 200)

    def test_empty_portfolio_dashboard_renders(self):
        empty = Portfolio.objects.create(owner=self.user, name='Empty', base_currency='USD')
        self.client.force_login(self.user)
        r = self.client.get(reverse('portfolio:portfolio_dashboard', args=[empty.pk]))
        self.assertEqual(r.status_code, 200)


@override_settings(SECURE_SSL_REDIRECT=False)
class CrossUserIsolationUnderCISettingsTests(TestCase):
    """
    Ownership isolation, re-asserted with the SSL redirect disabled so the
    authorisation code actually runs. Two ordinary users, one staff user.
    """

    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user('e-alice', password='x')
        cls.bob = User.objects.create_user('e-bob', password='x')
        cls.sam = User.objects.create_user('e-sam', password='x', is_staff=True)
        cls.alice_pf = Portfolio.objects.create(
            owner=cls.alice, name='Alice Holdings', base_currency='USD')
        cls.bob_pf = Portfolio.objects.create(
            owner=cls.bob, name='Bob Holdings', base_currency='USD')
        cls.alice_wl = Watchlist.objects.create(
            owner=cls.alice, name='Alice Private', is_public=False)

    def test_owner_reaches_own_portfolio(self):
        self.client.force_login(self.alice)
        r = self.client.get(reverse('portfolio:portfolio_dashboard', args=[self.alice_pf.pk]))
        self.assertEqual(r.status_code, 200)

    def test_other_user_cannot_reach_portfolio(self):
        self.client.force_login(self.bob)
        r = self.client.get(reverse('portfolio:portfolio_dashboard', args=[self.alice_pf.pk]))
        self.assertEqual(r.status_code, 404)

    def test_list_shows_only_own_portfolios(self):
        self.client.force_login(self.alice)
        r = self.client.get(reverse('portfolio:portfolio_list'))
        self.assertContains(r, 'Alice Holdings')
        self.assertNotContains(r, 'Bob Holdings')

    def test_other_user_cannot_delete_or_recalculate(self):
        self.client.force_login(self.bob)
        for name in ('portfolio:portfolio_delete', 'portfolio:portfolio_recalculate'):
            with self.subTest(action=name):
                r = self.client.post(reverse(name, args=[self.alice_pf.pk]))
                self.assertEqual(r.status_code, 404)
        self.assertTrue(Portfolio.objects.filter(pk=self.alice_pf.pk).exists())

    def test_private_watchlist_404s_for_other_user(self):
        self.client.force_login(self.bob)
        r = self.client.get(reverse('portfolio:watchlist_detail', args=[self.alice_wl.pk]))
        self.assertEqual(r.status_code, 404)

    def test_private_watchlist_404s_for_anonymous(self):
        r = self.client.get(reverse('portfolio:watchlist_detail', args=[self.alice_wl.pk]))
        self.assertEqual(r.status_code, 404)

    def test_id_enumeration_reveals_only_own_portfolios(self):
        self.client.force_login(self.alice)
        for pk in Portfolio.objects.values_list('pk', flat=True):
            r = self.client.get(reverse('portfolio:portfolio_dashboard', args=[pk]))
            expected = 200 if pk == self.alice_pf.pk else 404
            self.assertEqual(r.status_code, expected, f'portfolio pk={pk}')

    def test_staff_may_view_any_portfolio(self):
        self.client.force_login(self.sam)
        for pk in (self.alice_pf.pk, self.bob_pf.pk):
            self.assertEqual(
                self.client.get(
                    reverse('portfolio:portfolio_dashboard', args=[pk])).status_code,
                200)

    def test_anonymous_is_redirected_to_login_not_shown_data(self):
        r = self.client.get(reverse('portfolio:portfolio_dashboard', args=[self.alice_pf.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login', r['Location'])
        self.assertNotIn('Alice Holdings', r.content.decode(errors='ignore'))


@override_settings(SECURE_SSL_REDIRECT=False)
class PortfolioQueryEfficiencyTests(TestCase):
    """Adding holdings must not add a query per holding."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('q-user', password='x')
        cls.portfolio = Portfolio.objects.create(
            owner=cls.user, name='Query Portfolio', base_currency='USD')

    def setUp(self):
        self.client.force_login(self.user)

    def _add_holdings(self, n, prefix):
        for i in range(n):
            co = _company(f'{prefix}-{i}', ticker=f'{prefix.upper()}{i}',
                          stock_price=Decimal('10.00'), stock_price_currency='USD',
                          stock_price_updated_at=timezone.now())
            Holding.objects.create(portfolio=self.portfolio, company=co,
                                   shares=Decimal("5"))

    def _count(self, url):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(url)
        return len(ctx.captured_queries)

    def test_dashboard_query_count_does_not_grow_per_holding(self):
        url = reverse('portfolio:portfolio_dashboard', args=[self.portfolio.pk])
        self._add_holdings(3, 'qa')
        few = self._count(url)
        self._add_holdings(9, 'qb')
        many = self._count(url)
        self.assertEqual(
            few, many,
            f'dashboard grew {few} -> {many} queries when holdings went from 3 '
            'to 12 — holdings are not being prefetched',
        )

    def test_portfolio_list_query_count_does_not_grow_per_portfolio(self):
        url = reverse('portfolio:portfolio_list')
        first = self._count(url)
        for i in range(6):
            Portfolio.objects.create(owner=self.user, name=f'Extra {i}',
                                     base_currency='USD')
        second = self._count(url)
        self.assertEqual(
            first, second,
            f'portfolio list grew {first} -> {second} queries as portfolios '
            'were added',
        )
