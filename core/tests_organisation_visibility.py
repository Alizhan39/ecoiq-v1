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


@override_settings(ALLOWED_HOSTS=['*'])
class CompanyListTests(TestCase):
    """
    The directory, against the entries it links to.

    /api/v2/companies/ started from `Company.objects` with no status filter at
    all, so it listed every organisation the detail endpoint and the page both
    withheld. A list that names what its own entries refuse to open is not a
    smaller leak than the entry leaking; it is the index to it.
    """

    def setUp(self):
        Company.objects.create(name='Orphan Org', slug='orphan-org')  # no profile
        make_organisation('withdrawn-org', 'archived')
        make_organisation('demo-org', 'public_demo')
        make_organisation('draft-org', 'draft')
        make_organisation('current-org', 'public')

    def listed(self, client=None):
        client = client or self.client
        return {row['slug'] for row in client.get('/api/v2/companies/').json()['results']}

    def test_an_archived_organisation_is_not_listed(self):
        self.assertNotIn('withdrawn-org', self.listed())

    def test_an_organisation_with_no_profile_is_not_listed(self):
        """
        It has no status, so nothing has decided it may be shown. The detail
        endpoint and the page both 404 it.
        """
        self.assertNotIn('orphan-org', self.listed())

    def test_the_published_statuses_are_listed(self):
        self.assertEqual(self.listed(),
                         {'demo-org', 'draft-org', 'current-org'})

    def test_search_cannot_reach_what_the_list_withholds(self):
        """Filtering narrows the visible set; it never widens it."""
        results = self.client.get('/api/v2/companies/?q=Withdrawn').json()['results']
        self.assertEqual(results, [])

    def test_staff_see_the_archived_one(self):
        get_user_model().objects.create_user(
            username='reviewer', password='x', is_staff=True)
        staff = self.client_class()
        staff.login(username='reviewer', password='x')
        self.assertIn('withdrawn-org', self.listed(staff))

    def test_the_list_and_the_detail_endpoint_agree(self):
        """
        The property that was actually broken, asserted directly: anything the
        directory names must open, and anything it withholds must not.
        """
        listed = self.listed()
        for slug in ('orphan-org', 'withdrawn-org', 'demo-org',
                     'draft-org', 'current-org'):
            with self.subTest(slug=slug):
                opens = self.client.get(
                    f'/api/v2/companies/{slug}/').status_code == 200
                self.assertEqual(
                    slug in listed, opens,
                    f'{slug}: listed={slug in listed} but detail opens={opens}')


@override_settings(ALLOWED_HOSTS=['*'])
class DemonstrationProfileTests(TestCase):
    """
    `public_demo` was added so Apple x 114 could be reachable as a labelled
    worked example. The literal in api/v2_views.py predated it and was never
    updated, so the demonstration profile 404'd on its own API while the page
    served it — a page and its data source disagreeing about whether the
    organisation is reachable at all.
    """

    def setUp(self):
        make_organisation('demo-org', 'public_demo')

    def test_the_page_and_its_api_agree(self):
        self.assertEqual(self.client.get('/companies/demo-org/').status_code, 200)
        self.assertEqual(
            self.client.get('/api/v2/companies/demo-org/').status_code, 200)

    def test_visibility_is_not_a_publication_claim(self):
        """
        Reachable is not published. companies/eligibility.decide() never reads
        status, and this pins that making the profile visible did not quietly
        start publishing it.
        """
        from companies.eligibility import decide
        from companies.models import CompanyProfile

        profile = CompanyProfile.objects.get(company__slug='demo-org')
        self.assertFalse(decide(profile).is_published)


@override_settings(ALLOWED_HOSTS=['*'])
class StaffSeeTheSameThingEverywhereTests(TestCase):
    """
    A staff reviewer opening an archived organisation must get the same answer
    from every surface that serves it.

    They did not. /api/v2/companies/<slug>/kpis/<id>/ is a plain Django view,
    so it read the session and let a reviewer in; its own parent resource,
    /api/v2/companies/<slug>/, is a DRF view whose `authentication_classes`
    override dropped SessionAuthentication — a pure subtraction from the
    default chain, which already contained the API key class it re-declared.
    Same person, same browser, same organisation, two answers.
    """

    def setUp(self):
        make_organisation('withdrawn-org', 'archived')
        get_user_model().objects.create_user(
            username='reviewer', password='x', is_staff=True)
        self.staff = self.client_class()
        self.staff.login(username='reviewer', password='x')

    def test_staff_open_the_archived_organisation_on_every_surface(self):
        for path in ('/api/v2/companies/withdrawn-org/',
                     '/api/v2/companies/withdrawn-org/principles/',
                     '/api/v2/companies/withdrawn-org/kpis/16/',
                     '/companies/withdrawn-org/ml-insights.json'):
            with self.subTest(path=path):
                self.assertEqual(self.staff.get(path).status_code, 200, path)

    def test_an_ordinary_account_opens_none_of_them(self):
        """Signed in is not staff, and staff is what the rule names."""
        get_user_model().objects.create_user(username='ordinary', password='x')
        client = self.client_class()
        client.login(username='ordinary', password='x')
        for path in ('/api/v2/companies/withdrawn-org/',
                     '/api/v2/companies/withdrawn-org/principles/',
                     '/companies/withdrawn-org/ml-insights.json'):
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 404, path)


class NoHandWrittenCopiesOfTheRuleTests(TestCase):
    """
    companies/visibility.py exists because this list had been written out by
    hand in six places, and the copies drifted: every one of them still said
    ('public', 'verified', 'draft') long after `public_demo` was added, so a
    demonstration organisation's page served while its own API and its own PDF
    answered 404.

    A rule you have to remember to copy is not one rule. This fails if a copy
    comes back.
    """

    #: The scoring and analytics queries select on ('public', 'verified') and
    #: are deliberately NOT this list — they must keep excluding demonstration
    #: profiles without being told the status exists. See visibility.py.
    LITERAL = "'public', 'verified', 'draft'"

    def test_the_visibility_list_is_written_once(self):
        import pathlib

        from django.conf import settings

        root = pathlib.Path(settings.BASE_DIR)
        skip = {'.venv', 'node_modules', '.git', '__pycache__', 'static'}
        offenders = []
        for path in root.rglob('*.py'):
            if any(part in skip or part.startswith('.') for part in path.parts):
                continue
            if path.name == 'visibility.py' or path.name.startswith('tests'):
                continue
            if self.LITERAL in path.read_text(encoding='utf-8', errors='replace'):
                offenders.append(str(path.relative_to(root)))
        self.assertEqual(
            offenders, [],
            f'The visibility list is written out by hand in {offenders}. '
            f'Import PUBLICLY_VISIBLE_STATUSES from companies.visibility — '
            f'every previous copy of this literal went stale.')

    def test_the_guard_would_notice(self):
        """
        Non-vacuous: the literal it searches for must be the one that actually
        appears in the module it comes from.
        """
        from companies.visibility import PUBLICLY_VISIBLE_STATUSES

        for status in ('public', 'verified', 'draft'):
            self.assertIn(status, PUBLICLY_VISIBLE_STATUSES)
        self.assertIn('public_demo', PUBLICLY_VISIBLE_STATUSES,
                      'the status every hand-written copy was missing')
