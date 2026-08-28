"""
The anonymous per-organisation surface, against a profile that is not public.

WHY A ROUTE-DRIVEN TEST
-----------------------
`companies/visibility.py` exists because the rule "only published statuses are
served" had been written out by hand in six places and skipped in two. The way
that happens again is a NEW per-organisation route that simply never asks.

So this suite enumerates the surface rather than asserting view by view: every
anonymous route that takes an organisation slug is listed once, and each must
withhold an archived organisation. A route added to the list and not to the
rule fails here.

WHAT THE AUTHORIZATION PASS FOUND
---------------------------------
Two endpoints were serving a withdrawn organisation to anonymous callers while
/companies/<slug>/ — the page — answered 404 to everybody:

  /companies/<slug>/ml-insights.json   looked the organisation up in
                                       league.Company by slug alone, so no
                                       status was ever consulted. It returned a
                                       cluster label ("Governance Champion")
                                       and an anomaly score for an archived
                                       profile.

  /api/why/company/<slug>/             was public while its own page required
                                       sign-in — recorded as a known gap when
                                       the page was gated — and additionally
                                       never 404'd at all.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.utils import override_settings

from companies.models import CompanyProfile
from harvester.models import RegistryCompany
from league.models import Company

#: Every anonymous route that names one organisation. Add a route here when
#: you add one to the product; the assertions below then apply to it.
PER_ORGANISATION_ROUTES = (
    '/companies/{slug}/',
    '/companies/{slug}/kpis/16/',
    '/companies/{slug}/report.pdf',
    '/companies/{slug}/ml-insights.json',
    '/embed/{slug}/',
    '/embed/{slug}/badge.svg',
    '/embed/{slug}/ethical-badge.svg',
    '/embed/{slug}/islamic-badge.svg',
    '/embed/{slug}/risk-card/',
    '/api/v2/companies/{slug}/',
    '/api/v2/companies/{slug}/principles/',
    '/api/v2/companies/{slug}/kpis/16/',
    '/api/v2/companies/{slug}/assessment/',
)

#: Not "the request failed" — specifically "this organisation is not served
#: here". 404 for withheld, 403 where a gate answers before the lookup.
WITHHELD = (403, 404)


def make_organisation(slug, status):
    company = Company.objects.create(name=slug.replace('-', ' ').title(), slug=slug)
    CompanyProfile.objects.create(company=company, status=status)
    return company


@override_settings(ALLOWED_HOSTS=['*'])
class ArchivedOrganisationTests(TestCase):
    """
    An archived profile keeps its evidence and its history — that is the point
    of archiving rather than deleting. It must not be served as though it were
    current.
    """

    def setUp(self):
        make_organisation('withdrawn-org', 'archived')
        make_organisation('current-org', 'public')

    def test_no_anonymous_route_serves_an_archived_organisation(self):
        for route in PER_ORGANISATION_ROUTES:
            with self.subTest(route=route):
                response = self.client.get(route.format(slug='withdrawn-org'))
                self.assertIn(
                    response.status_code, WITHHELD,
                    f'{route} served an archived organisation '
                    f'({response.status_code}) while /companies/<slug>/ 404s.')

    def test_the_same_routes_do_serve_a_public_organisation(self):
        """
        The other half. Without this, withholding everything would pass the
        test above and the suite would be measuring nothing.
        """
        served = [route for route in PER_ORGANISATION_ROUTES
                  if self.client.get(route.format(slug='current-org')).status_code == 200]
        self.assertGreater(
            len(served), len(PER_ORGANISATION_ROUTES) // 2,
            'Almost nothing answers for a public organisation, so the '
            'archived assertions above prove nothing.')


@override_settings(ALLOWED_HOSTS=['*'])
class MlInsightsTests(TestCase):
    """The endpoint that consulted no status at all."""

    def setUp(self):
        make_organisation('withdrawn-org', 'archived')
        make_organisation('current-org', 'public')

    def url(self, slug):
        return f'/companies/{slug}/ml-insights.json'

    def test_an_archived_organisation_is_withheld(self):
        self.assertEqual(self.client.get(self.url('withdrawn-org')).status_code, 404)

    def test_no_judgement_label_leaks_in_the_body(self):
        """
        A status assertion alone would pass on a 404 page that still rendered
        the cluster label. This is what actually must not reach the reader.
        """
        body = self.client.get(self.url('withdrawn-org')).content
        self.assertNotIn(b'"cluster"', body)
        self.assertNotIn(b'anomaly_score', body)

    def test_a_public_organisation_is_still_served(self):
        self.assertEqual(self.client.get(self.url('current-org')).status_code, 200)

    def test_staff_may_read_the_archived_one(self):
        """
        Withheld from the public is not the same as unreviewable — the whole
        point of companies/visibility.py.
        """
        get_user_model().objects.create_user(
            username='reviewer', password='x', is_staff=True)
        staff = self.client_class()
        staff.login(username='reviewer', password='x')
        self.assertEqual(staff.get(self.url('withdrawn-org')).status_code, 200)

    def test_an_unknown_slug_is_still_a_404(self):
        self.assertEqual(self.client.get(self.url('no-such-org-xyz')).status_code, 404)


@override_settings(ALLOWED_HOSTS=['*'])
class WhyCompanyApiTests(TestCase):
    """
    The JSON behind a page that requires sign-in.
    """

    def setUp(self):
        RegistryCompany.objects.create(
            company_name='Registered Org', slug='registered-org',
            sector='utilities', country='GB')

    def url(self, slug):
        return f'/api/why/company/{slug}/'

    def test_the_api_is_gated_exactly_like_its_page(self):
        """
        /why/company/<slug>/ redirects to sign-in. The JSON serving the same
        payload publicly de-published the page and published it again one path
        away.
        """
        self.assertEqual(self.client.get(self.url('registered-org')).status_code, 403)

    def test_a_signed_in_user_still_gets_the_report(self):
        """Sign-in, not deletion — the endpoint still works."""
        get_user_model().objects.create_user(username='analyst', password='x')
        client = self.client_class()
        client.login(username='analyst', password='x')
        response = client.get(self.url('registered-org'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['reports'])

    def test_the_country_api_is_deliberately_left_public(self):
        """
        Both halves of the country pair are public and consistently so. This
        pins that the company fix did not quietly take the country with it.
        """
        self.assertNotEqual(
            self.client.get('/api/why/country/united-kingdom/').status_code, 403)


@override_settings(ALLOWED_HOSTS=['*'])
class NoOrganisationInventedFromTheUrlTests(TestCase):
    """
    The endpoint answered 200 for ANY slug, with a name title-cased out of the
    path: /api/why/company/no-such-org-xyz/ returned "No Such Org Xyz" and a
    seven-metric report about an organisation EcoIQ had invented from the URL.

    An unbounded supply of documents naming organisations that may not exist is
    the same charge core/access.py already made against /company-intelligence/.
    """

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='analyst', password='x')
        self.client.login(username='analyst', password='x')
        RegistryCompany.objects.create(
            company_name='Registered Org', slug='registered-org',
            sector='utilities', country='GB')

    def test_a_slug_nothing_is_recorded_under_is_a_404(self):
        for slug in ('no-such-org-xyz', 'acme', 'a-competitor-of-yours'):
            with self.subTest(slug=slug):
                self.assertEqual(
                    self.client.get(f'/api/why/company/{slug}/').status_code, 404,
                    f'{slug!r} produced a report about an organisation that is '
                    f'not on record.')

    def test_the_page_and_the_pdf_agree_with_the_api(self):
        """One absent organisation, three formats, one answer."""
        for path in ('/why/company/no-such-org-xyz/',
                     '/why/company/no-such-org-xyz/pack.pdf',
                     '/api/why/company/no-such-org-xyz/'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 404)

    def test_a_registered_but_unharvested_organisation_still_reports(self):
        """
        The honest "not yet defendable" case must survive. It IS on record —
        it simply has no evidence yet, which the report says in full.
        """
        response = self.client.get(self.url_for('registered-org'))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['summary']['metrics_covered'], 0)
        self.assertTrue(all(report['value'] is None
                            for report in payload['reports']))

    def url_for(self, slug):
        return f'/api/why/company/{slug}/'
