"""
Privacy / object-level permission tests (spec §11): a user must never be
able to view or edit another user's portfolio or holdings, generate a
briefing for another user's portfolio, or reach a private watchlist through
a guessed URL. Anonymous users must be locked out of all portfolio data.
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from investor_portfolio.models import Holding, Portfolio, Watchlist
from league.models import Company


def _make_company(slug='permco', **kwargs):
    defaults = {'name': 'Perm Co', 'sector': 'energy'}
    defaults.update(kwargs)
    return Company.objects.create(slug=slug, **defaults)


class PortfolioPermissionTests(TestCase):

    def setUp(self):
        self.owner = User.objects.create_user('owner', password='x')
        self.other = User.objects.create_user('other', password='x')
        self.staff = User.objects.create_user('staff', password='x', is_staff=True)
        self.portfolio = Portfolio.objects.create(owner=self.owner, name='Private Portfolio', base_currency='USD')
        Holding.objects.create(portfolio=self.portfolio, company=_make_company(), shares=Decimal('5'),
                                avg_acquisition_price=Decimal('10'))

    def test_other_authenticated_user_cannot_view_portfolio(self):
        c = Client(SERVER_NAME='localhost')
        c.force_login(self.other)
        r = c.get(reverse('portfolio:portfolio_dashboard', kwargs={'pk': self.portfolio.pk}))
        self.assertEqual(r.status_code, 404)  # not 403 — existence isn't confirmed either

    def test_other_authenticated_user_cannot_edit_holdings(self):
        holding = self.portfolio.holdings.first()
        c = Client(SERVER_NAME='localhost')
        c.force_login(self.other)
        r = c.post(reverse('portfolio:holding_edit', kwargs={'pk': self.portfolio.pk, 'holding_id': holding.pk}),
                   {'company_slug': holding.company.slug, 'shares': '999', 'include_in_analytics': 'on'})
        self.assertEqual(r.status_code, 404)
        holding.refresh_from_db()
        self.assertEqual(holding.shares, Decimal('5'))  # unchanged

    def test_other_authenticated_user_cannot_delete_holdings(self):
        holding = self.portfolio.holdings.first()
        c = Client(SERVER_NAME='localhost')
        c.force_login(self.other)
        c.post(reverse('portfolio:holding_delete', kwargs={'pk': self.portfolio.pk, 'holding_id': holding.pk}))
        self.assertTrue(Holding.objects.filter(pk=holding.pk).exists())

    def test_other_authenticated_user_cannot_generate_briefing(self):
        c = Client(SERVER_NAME='localhost')
        c.force_login(self.other)
        r = c.post(reverse('portfolio:portfolio_generate_briefing', kwargs={'pk': self.portfolio.pk}))
        self.assertEqual(r.status_code, 404)

    def test_other_authenticated_user_cannot_export_csv(self):
        c = Client(SERVER_NAME='localhost')
        c.force_login(self.other)
        r = c.get(reverse('portfolio:portfolio_export_csv', kwargs={'pk': self.portfolio.pk}))
        self.assertEqual(r.status_code, 404)

    def test_anonymous_user_redirected_not_shown_data(self):
        c = Client(SERVER_NAME='localhost')
        r = c.get(reverse('portfolio:portfolio_dashboard', kwargs={'pk': self.portfolio.pk}))
        self.assertEqual(r.status_code, 302)  # redirected to login, no data leaked
        self.assertIn('/login/', r.url)

    def test_anonymous_user_cannot_list_portfolios(self):
        c = Client(SERVER_NAME='localhost')
        r = c.get(reverse('portfolio:portfolio_list'))
        self.assertEqual(r.status_code, 302)

    def test_anonymous_user_cannot_export_csv(self):
        c = Client(SERVER_NAME='localhost')
        r = c.get(reverse('portfolio:portfolio_export_csv', kwargs={'pk': self.portfolio.pk}))
        self.assertEqual(r.status_code, 302)

    def test_staff_can_view_any_portfolio(self):
        c = Client(SERVER_NAME='localhost')
        c.force_login(self.staff)
        r = c.get(reverse('portfolio:portfolio_dashboard', kwargs={'pk': self.portfolio.pk}))
        self.assertEqual(r.status_code, 200)

    def test_sensitive_fields_never_in_other_users_response(self):
        """Even indirectly — e.g. via a stray API or search page — acquisition price/notes must not leak."""
        holding = self.portfolio.holdings.first()
        holding.notes = 'SECRET_NOTE_MARKER'
        holding.save()
        c = Client(SERVER_NAME='localhost')
        c.force_login(self.other)
        r = c.get(reverse('portfolio:portfolio_dashboard', kwargs={'pk': self.portfolio.pk}))
        self.assertNotContains(r, 'SECRET_NOTE_MARKER', status_code=404)


class WatchlistPermissionTests(TestCase):

    def setUp(self):
        self.owner = User.objects.create_user('wlowner', password='x')
        self.other = User.objects.create_user('wlother', password='x')
        self.private_wl = Watchlist.objects.create(owner=self.owner, name='Private List', is_public=False)
        self.public_wl = Watchlist.objects.create(owner=self.owner, name='Public List', is_public=True)

    def test_private_watchlist_404s_for_other_user(self):
        c = Client(SERVER_NAME='localhost')
        c.force_login(self.other)
        r = c.get(reverse('portfolio:watchlist_detail', kwargs={'pk': self.private_wl.pk}))
        self.assertEqual(r.status_code, 404)

    def test_private_watchlist_404s_for_anonymous_guessed_url(self):
        c = Client(SERVER_NAME='localhost')
        r = c.get(reverse('portfolio:watchlist_detail', kwargs={'pk': self.private_wl.pk}))
        self.assertEqual(r.status_code, 404)  # not a login redirect — existence isn't confirmed

    def test_public_watchlist_viewable_by_anonymous(self):
        c = Client(SERVER_NAME='localhost')
        r = c.get(reverse('portfolio:watchlist_detail', kwargs={'pk': self.public_wl.pk}))
        self.assertEqual(r.status_code, 200)

    def test_public_watchlist_not_editable_by_other_user(self):
        c = Client(SERVER_NAME='localhost')
        c.force_login(self.other)
        r = c.post(reverse('portfolio:watchlist_delete', kwargs={'pk': self.public_wl.pk}))
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Watchlist.objects.filter(pk=self.public_wl.pk).exists())

    def test_other_user_cannot_remove_company_from_someone_elses_watchlist(self):
        co = _make_company()
        from investor_portfolio.models import WatchlistItem
        WatchlistItem.objects.create(watchlist=self.public_wl, company=co)
        c = Client(SERVER_NAME='localhost')
        c.force_login(self.other)
        c.post(reverse('portfolio:watchlist_remove_company', kwargs={'pk': self.public_wl.pk, 'company_slug': co.slug}))
        self.assertTrue(WatchlistItem.objects.filter(watchlist=self.public_wl, company=co).exists())
