"""
Watchlist and Portfolio CRUD tests: creation, multiple watchlists, adding/
removing companies, holding creation/editing, duplicate-holding prevention.
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from league.models import Company

from .models import Holding, Portfolio, Watchlist, WatchlistItem


def _make_company(slug='acme', **kwargs):
    defaults = {'name': 'Acme Co', 'sector': 'energy', 'ticker': 'ACME'}
    defaults.update(kwargs)
    return Company.objects.create(slug=slug, **defaults)


class WatchlistModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('alice', password='x')
        self.client = Client(SERVER_NAME='localhost')
        self.client.force_login(self.user)

    def test_create_watchlist(self):
        wl = Watchlist.objects.create(owner=self.user, name='Energy companies')
        self.assertEqual(wl.owner, self.user)
        self.assertFalse(wl.is_public)  # private by default
        self.assertEqual(wl.items.count(), 0)

    def test_user_can_have_multiple_watchlists(self):
        Watchlist.objects.create(owner=self.user, name='Energy companies')
        Watchlist.objects.create(owner=self.user, name='UK portfolio')
        Watchlist.objects.create(owner=self.user, name='Companies to review')
        self.assertEqual(Watchlist.objects.filter(owner=self.user).count(), 3)

    def test_add_company_to_watchlist_via_view(self):
        wl = Watchlist.objects.create(owner=self.user, name='Energy companies')
        co = _make_company()
        r = self.client.post(reverse('portfolio:watchlist_add_company'),
                              {'company_slug': co.slug, 'watchlist_id': wl.pk}, follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(WatchlistItem.objects.filter(watchlist=wl, company=co).exists())

    def test_add_company_creates_new_watchlist_in_one_action(self):
        co = _make_company()
        r = self.client.post(reverse('portfolio:watchlist_add_company'),
                              {'company_slug': co.slug, 'new_watchlist_name': 'Potential investments'}, follow=True)
        self.assertEqual(r.status_code, 200)
        wl = Watchlist.objects.get(owner=self.user, name='Potential investments')
        self.assertTrue(WatchlistItem.objects.filter(watchlist=wl, company=co).exists())

    def test_remove_company_from_watchlist(self):
        wl = Watchlist.objects.create(owner=self.user, name='Energy companies')
        co = _make_company()
        WatchlistItem.objects.create(watchlist=wl, company=co)
        r = self.client.post(
            reverse('portfolio:watchlist_remove_company', kwargs={'pk': wl.pk, 'company_slug': co.slug}),
            follow=True,
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(WatchlistItem.objects.filter(watchlist=wl, company=co).exists())

    def test_anonymous_user_never_sees_watchlist_controls(self):
        """
        The load-bearing half of this test: an anonymous visitor must not get
        watchlist controls on a company page.

        The sign-in prompt it used to assert now sits behind the D1.5 evidence
        gate — an unevidenced company renders the "Evidence assessment pending"
        page, which offers neither controls nor a prompt. That is a stricter
        outcome than before, not a weaker one, so the control assertion is kept
        and the prompt assertion is dropped rather than moved somewhere it
        cannot hold (see the comment below).
        """
        from django.contrib.auth import get_user_model

        from companies.models import CompanyProfile

        co = _make_company()
        CompanyProfile.objects.create(company=co, status='public')
        url = reverse('companies:detail', kwargs={'slug': co.slug})

        anon = Client(SERVER_NAME='localhost')
        self.assertNotContains(anon.get(url), 'name="new_watchlist_name"')

        # The 'Sign in to add to watchlist' prompt is shown only to anonymous
        # visitors, and an anonymous visitor to an unevidenced company now gets
        # the evidence-pending page instead. So the prompt is currently
        # unreachable: signed-in users see real controls, and anonymous users
        # see the gate. It becomes reachable again when a company has evidence
        # (plan step D3+), and is not asserted here rather than asserted
        # against a page it cannot appear on.
        staff_client = Client(SERVER_NAME='localhost')
        staff_client.force_login(get_user_model().objects.create_user(
            username='watchlist-staff', is_staff=True))
        self.assertEqual(staff_client.get(url).status_code, 200)

    def test_watchlist_add_company_requires_login(self):
        co = _make_company()
        anon = Client(SERVER_NAME='localhost')
        r = anon.post(reverse('portfolio:watchlist_add_company'), {'company_slug': co.slug, 'new_watchlist_name': 'x'})
        self.assertNotEqual(r.status_code, 200)  # redirected to login, not processed
        self.assertFalse(Watchlist.objects.filter(name='x').exists())


class PortfolioModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('bob', password='x')
        self.client = Client(SERVER_NAME='localhost')
        self.client.force_login(self.user)

    def test_create_portfolio(self):
        p = Portfolio.objects.create(owner=self.user, name='Core Holdings', base_currency='USD')
        self.assertEqual(p.owner, self.user)
        self.assertEqual(p.holdings.count(), 0)

    def test_add_holding(self):
        p = Portfolio.objects.create(owner=self.user, name='Core Holdings')
        co = _make_company()
        r = self.client.post(reverse('portfolio:holding_create', kwargs={'pk': p.pk}), {
            'company_slug': co.slug, 'shares': '10', 'avg_acquisition_price': '50',
            'acquisition_currency': 'USD', 'include_in_analytics': 'on',
        }, follow=True)
        self.assertEqual(r.status_code, 200)
        holding = Holding.objects.get(portfolio=p, company=co)
        self.assertEqual(holding.shares, Decimal('10'))
        self.assertEqual(holding.avg_acquisition_price, Decimal('50'))

    def test_edit_holding(self):
        p = Portfolio.objects.create(owner=self.user, name='Core Holdings')
        co = _make_company()
        h = Holding.objects.create(portfolio=p, company=co, shares=Decimal('5'))
        r = self.client.post(reverse('portfolio:holding_edit', kwargs={'pk': p.pk, 'holding_id': h.pk}), {
            'company_slug': co.slug, 'shares': '20', 'acquisition_currency': 'USD', 'include_in_analytics': 'on',
        }, follow=True)
        self.assertEqual(r.status_code, 200)
        h.refresh_from_db()
        self.assertEqual(h.shares, Decimal('20'))

    def test_duplicate_holding_prevented_at_view_level(self):
        p = Portfolio.objects.create(owner=self.user, name='Core Holdings')
        co = _make_company()
        Holding.objects.create(portfolio=p, company=co, shares=Decimal('5'))
        r = self.client.post(reverse('portfolio:holding_create', kwargs={'pk': p.pk}), {
            'company_slug': co.slug, 'shares': '10', 'acquisition_currency': 'USD', 'include_in_analytics': 'on',
        })
        self.assertEqual(Holding.objects.filter(portfolio=p, company=co).count(), 1)  # still just one
        self.assertContains(r, 'already a holding')

    def test_duplicate_holding_prevented_at_db_level(self):
        p = Portfolio.objects.create(owner=self.user, name='Core Holdings')
        co = _make_company()
        Holding.objects.create(portfolio=p, company=co, shares=Decimal('5'))
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Holding.objects.create(portfolio=p, company=co, shares=Decimal('1'))

    def test_delete_holding(self):
        p = Portfolio.objects.create(owner=self.user, name='Core Holdings')
        co = _make_company()
        h = Holding.objects.create(portfolio=p, company=co, shares=Decimal('5'))
        r = self.client.post(reverse('portfolio:holding_delete', kwargs={'pk': p.pk, 'holding_id': h.pk}), follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Holding.objects.filter(pk=h.pk).exists())
