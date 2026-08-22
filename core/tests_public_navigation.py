"""
Regression tests for the simplified public information architecture.

The public header carried 21 links in base.html and 18 in landing.html — mostly
internal engines (Geo/Gold Intelligence, Capital Guardian, AI agents) or
alternative framings of the same material (Rankings, Countries, Methodology,
Stewardship, Framework, Compendium). The footer restated most of them again.

Primary public navigation is now: Intelligence, Eco Tours, Projects, About,
Contact, plus a sign-in.

Nothing was deleted. Every route dropped from the navigation still exists and
still responds; it is simply no longer promoted on every public page.

These tests are written against link destinations rather than whole-page
strings, so restyling the header does not break them.

AFTER THE REACT CUTOVER
-----------------------
`/` and `/about/` are served by the React app now, so they carry no Django
navigation at all. base.html still renders the ~100 pages that were NOT
migrated, and its navigation is still the thing these tests exist to protect —
so they assert against a page that base.html still renders.

The React navigation has its own tests, in frontend/web/src/app/Nav.test.tsx,
asserting the same rule: five primary destinations, and nothing internal
promoted alongside them.
"""
import re

from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse

# The five public items plus the utility sign-in.
EXPECTED_NAV = ['/intelligence/', '/tours/', '/projects/', '/about/', '/contact/']

#: A page base.html still renders, whose <nav> IS base.html's global
#: navigation.
#:
#: `/` and `/about/` are React now, so asserting the Django header against them
#: would assert nothing. /methodology/ used to serve here and is a 301 now.
#: /governance-principles/ and /countries/ render their own in-page nav on top
#: of the global one, which is not what these tests measure.
SERVER_RENDERED = '/heating/'

# Destinations that must no longer appear in the primary public navigation.
# They remain reachable — this asserts placement, not existence.
BANISHED_FROM_NAV = [
    '/companies/', '/countries/', '/league/', '/rankings/',
    '/ai-agents/', '/geo-intelligence/', '/gold-intelligence/',
    '/capital-guardian/', '/methodology/', '/stewardship/',
    '/heating/', '/khalifa-tours/', '/platform/',
    '/heating/', '/ingest/', '/admin/',
]


def nav_links(html):
    """Destinations inside the primary <nav>, whichever template rendered it."""
    match = re.search(r'<nav[^>]*>(.*?)</nav>', html, re.S)
    if not match:
        return []
    return re.findall(r'href="([^"]+)"', match.group(1))


def header_links(html):
    match = re.search(r'<header[^>]*>(.*?)</header>', html, re.S)
    return re.findall(r'href="([^"]+)"', match.group(1)) if match else []


def footer_links(html):
    match = re.search(r'<footer[^>]*>(.*?)</footer>', html, re.S)
    return re.findall(r'href="([^"]+)"', match.group(1)) if match else []


class ReactHomepageTests(TestCase):
    """
    `/` is the React app. It carries no Django navigation at all.

    The React header is asserted in frontend/web/src/app/Nav.test.tsx, against
    the same rule this module protects. Duplicating it here would mean
    asserting on a string in a JavaScript bundle, which passes for as long as
    nobody minifies it differently.
    """

    def setUp(self):
        self.body = self.client.get('/').content.decode()

    def test_the_homepage_is_the_react_shell(self):
        self.assertIn('id="root"', self.body)

    def test_it_carries_no_server_rendered_navigation(self):
        self.assertEqual(nav_links(self.body), [])
        self.assertEqual(header_links(self.body), [])

    def test_it_promotes_no_internal_module(self):
        """
        Still worth asserting: the shell is where a stray marketing link would
        be added if someone wanted one on every page.
        """
        for path in BANISHED_FROM_NAV:
            with self.subTest(path=path):
                self.assertNotIn(f'href="{path}"', self.body)


class BaseTemplateNavigationTests(TestCase):
    """base.html still renders the pages that were not migrated to React."""

    def setUp(self):
        self.body = self.client.get(SERVER_RENDERED).content.decode()

    def test_nav_contains_exactly_the_approved_public_items(self):
        links = [link for link in nav_links(self.body) if link != '/login/']
        self.assertEqual(links, EXPECTED_NAV)

    def test_no_internal_module_appears_in_the_header(self):
        links = nav_links(self.body)
        for path in BANISHED_FROM_NAV:
            with self.subTest(path=path):
                self.assertNotIn(path, links)

    def test_staff_links_are_not_in_the_public_header(self):
        """Command Centre / Ingest / Admin moved out of the public header."""
        links = nav_links(self.body)
        self.assertNotIn('/ingest/', links)
        self.assertNotIn('/admin/', links)


# HeadersMatchTests is gone. It compared landing.html's header with
# base.html's, because the homepage defined its own and could silently drift.
# `/` is React now, so there is exactly one server-rendered header left and
# nothing for it to drift from.


class FooterTests(TestCase):
    """A simplified header is pointless if the footer restates the old tree."""

    def test_footer_is_small(self):
        for path in (SERVER_RENDERED, '/khalifa-tours/'):
            with self.subTest(path=path):
                links = footer_links(self.client.get(path).content.decode())
                self.assertLessEqual(
                    len(links), 14,
                    'the footer is growing back into a second navigation tree')

    def test_footer_drops_technical_module_links(self):
        for path in (SERVER_RENDERED, '/khalifa-tours/'):
            body = self.client.get(path).content.decode()
            links = footer_links(body)
            for gone in ('/platform/', '/ethical-governance/', '/governance-principles/',
                         '/countries/', '/league/', '/stewardship/', '/heating/',
                         '/value-distribution/', '/khalifa-impact/', '/kazakhstan-map/'):
                with self.subTest(path=path, gone=gone):
                    self.assertNotIn(gone, links)

    def test_footer_keeps_the_gcc_seo_entry_point(self):
        """
        /gcc-investors/ fronts eight sitemap-registered pages and the footer is
        their only internal link; dropping it would orphan all eight.

        It used to be linked from the server-rendered homepage and from
        /pricing/. Both are React now, so the React footer carries it too —
        asserted in frontend/web/src/app/App.test.tsx.
        """
        body = self.client.get(SERVER_RENDERED).content.decode()
        self.assertIn('/gcc-investors/', footer_links(body))

    def test_footer_invents_no_legal_pages(self):
        """EcoIQ has no privacy/terms/cookie pages; we must not link to them."""
        links = footer_links(self.client.get(SERVER_RENDERED).content.decode())
        for absent in ('/privacy/', '/terms/', '/cookies/'):
            with self.subTest(absent=absent):
                self.assertNotIn(absent, links)


class PublicPagesStillWorkTests(TestCase):

    def test_approved_public_destinations_all_respond(self):
        for path in EXPECTED_NAV:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_healthz_unaffected(self):
        response = self.client.get('/healthz/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'ok')

    def test_demoted_pages_are_still_reachable(self):
        """
        Demoted from navigation, NOT removed. A 404 here would mean a public
        surface was quietly deleted.
        """
        for path in ('/companies/', '/countries/', '/league/', '/pricing/',
                     '/heating/', '/khalifa-tours/'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_retired_pages_redirect_rather_than_disappear(self):
        """
        /methodology/, /platform/ and /stewardship/ were retired, not deleted
        from the web: each 301s to the React page that covers its subject, so
        an old link still lands somewhere true. See core/redirects.py.
        """
        from core.redirects import PERMANENT

        for path in ('/methodology/', '/platform/', '/stewardship/'):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 301)
                self.assertEqual(response['Location'], PERMANENT[path])


class IntelligenceRouteTests(TestCase):
    """
    /intelligence/ now serves the public page; the staff-only Environmental
    Intelligence OS moved to /intelligence-os/ with its namespace unchanged.
    """

    def test_public_intelligence_page_is_anonymous_and_renders(self):
        """
        The placeholder this used to assert on is gone: /intelligence/ is the
        React assessment flow now. What still matters is that it is public, it
        responds, and it is the app rather than a stray Django page.
        """
        response = self.client.get('/intelligence/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="root"')
        self.assertContains(response, '<title>Intelligence — EcoIQ</title>')

    def test_public_page_makes_no_capability_claims_with_numbers(self):
        """
        It is a placeholder. It must not grow fabricated metrics before the real
        Intelligence experience exists.
        """
        body = self.client.get('/intelligence/').content.decode()
        self.assertNotIn('tCO2', body)
        self.assertNotIn('verified impact', body.lower())

    def test_internal_os_moved_and_is_still_staff_only(self):
        self.assertEqual(reverse('intelligence:hub'), '/intelligence-os/')
        response = Client().get('/intelligence-os/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_internal_os_still_reachable_by_staff(self):
        staff = get_user_model().objects.create_user(
            username='nav-staff', is_staff=True)
        client = Client()
        client.force_login(staff)
        self.assertEqual(client.get('/intelligence-os/').status_code, 200)


class AmanahAutopilotTests(TestCase):
    """
    Gated once the GCC investor pages stopped linking to it. Its implementation,
    template and tests are retained — only public exposure changed.
    """

    def test_is_no_longer_anonymously_readable(self):
        response = Client().get('/amanah-autopilot/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])
        self.assertEqual(response.content, b'')

    def test_staff_can_still_read_it(self):
        staff = get_user_model().objects.create_user(
            username='amanah-staff', is_staff=True)
        client = Client()
        client.force_login(staff)
        self.assertEqual(client.get('/amanah-autopilot/').status_code, 200)

    def test_homepage_no_longer_links_to_it(self):
        self.assertNotIn('/amanah-autopilot/', self.client.get('/').content.decode())


class GccInvestorPageTests(TestCase):
    """
    Both language variants pointed investors at the Amanah Autopilot concept
    page. They now point at /about/, so gating that page cannot strand a
    visitor arriving from an indexed SEO page.
    """

    def test_english_page_links_to_about_not_amanah(self):
        body = self.client.get(reverse('gcc_investors:hub_en')).content.decode()
        self.assertNotIn('/amanah-autopilot/', body)
        self.assertIn('href="/about/"', body)

    def test_arabic_page_links_to_about_not_amanah(self):
        body = self.client.get(reverse('gcc_investors:hub_ar')).content.decode()
        self.assertNotIn('/amanah-autopilot/', body)
        self.assertIn('href="/about/"', body)

    def test_arabic_page_uses_the_repository_translation_for_about(self):
        """
        locale/ar renders "About" as عن المنصة. The link text should follow the
        catalogue rather than introduce a competing rendering.
        """
        body = self.client.get(reverse('gcc_investors:hub_ar')).content.decode()
        self.assertIn('عن المنصة', body)


class UntouchedCriticalRoutingTests(SimpleTestCase):
    """Navigation work must not disturb payments or authentication."""

    def test_stripe_webhook_unchanged(self):
        self.assertEqual(reverse('billing:webhook'), '/billing/webhook/')

    def test_auth_routes_unchanged(self):
        self.assertEqual(reverse('login'), '/login/')
        self.assertEqual(reverse('logout'), '/logout/')


class PreviouslyGatedPagesStayGatedTests(TestCase):
    """PR #235's gating must survive this change."""

    def test_a_sample_of_gated_modules_still_redirect(self):
        anonymous = Client()
        for path in ('/impact-mrv-layer/', '/sales-crm-partner-pipeline/',
                     '/deployment-devops-reliability-centre/',
                     '/frontend-implementation-roadmap/'):
            with self.subTest(path=path):
                response = anonymous.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertIn('/login/', response['Location'])
