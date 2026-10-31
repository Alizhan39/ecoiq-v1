"""
Regression tests for PR A — internal concept pages removed from the public surface.

Twenty-eight routes were hard-coded architecture/roadmap/CRM/DevOps descriptions
served anonymously at HTTP 200. Together they published roughly 1.1 MB of internal
material as though it were customer-facing product. See
docs/product/PHASE_1_ARCHITECTURE.md §3.

They are gated, not deleted: every app, view, template, model and test is retained.
The only change is who may read the page.

What these tests pin, and the failure each prevents:
  - an anonymous request must not READ the page (content leak),
  - and must not receive its content in the redirect body either,
  - staff access still works (we gated, not broke),
  - customer-facing pages are untouched (over-broad gating),
  - /healthz/, /billing/webhook/ and the auth routes are untouched
    (this PR must not disturb liveness, payments or login),
  - the sitemap still advertises no internal page.
"""
from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase

# The 28 gated routes. Kept as a literal list rather than derived from the
# URLconf: a test that discovers its own subjects would silently stop covering a
# route that someone later unmounted or renamed.
GATED_ROUTES = [
    '/frontend-implementation-roadmap/',
    '/deployment-devops-reliability-centre/',
    '/sales-crm-partner-pipeline/',
    '/revenue-pricing-engine/',
    '/customer-success-renewal-engine/',
    '/product-analytics-kpi-engine/',
    '/security-privacy-compliance-centre/',
    '/knowledge-graph-relationship-map/',
    '/frontend-experience-google-stitch-design-system/',
    '/microsoft-ecosystem-core-stack/',
    '/api-integration-layer/',
    '/data-room-evidence-vault/',
    '/executive-briefing-board-pack-generator/',
    '/governance-expert-review-board/',
    '/institutional-finance-engine/',
    '/industrial-playbook-library/',
    '/supplier-funding-marketplace/',
    '/mobile-inspection-mode/',
    '/impact-mrv-layer/',
    '/asset-passport/',
    '/omnimodal-evidence-panel/',
    '/certification-trust-badge-engine/',
    '/portfolio-country-transition-atlas/',
    '/public-trust-impact-portal/',
    '/ai-agent-operations-console/',
    '/document-reader-agent-training-pack/',
    '/mrv-agent-training-pack/',
    '/agent-training-evaluation-lab/',
]

# Public pages that must keep working. If gating were applied too broadly, or a
# shared decorator leaked, these are what would break first.
PUBLIC_ROUTES = [
    '/',
    '/healthz/',
    '/projects/',
    '/about/',
    '/contact/',
    '/pricing/',
    '/robots.txt',
]


class AnonymousCannotReadInternalPages(TestCase):

    def test_every_gated_route_redirects_anonymous_users(self):
        anonymous = Client()
        for route in GATED_ROUTES:
            with self.subTest(route=route):
                response = anonymous.get(route)
                self.assertEqual(
                    response.status_code, 302,
                    f'{route} did not redirect an anonymous visitor')
                self.assertIn('/login/', response['Location'])

    def test_redirect_body_carries_no_page_content(self):
        """
        A 302 whose body still contained the rendered page would leak exactly
        what this change exists to stop. staff_member_required redirects before
        the view runs, so the body must be empty.
        """
        anonymous = Client()
        for route in GATED_ROUTES:
            with self.subTest(route=route):
                response = anonymous.get(route)
                self.assertEqual(response.content, b'')

    def test_following_the_redirect_reaches_login_not_the_page(self):
        anonymous = Client()
        response = anonymous.get(GATED_ROUTES[0], follow=True)
        final_url = response.redirect_chain[-1][0]
        self.assertIn('/login/', final_url)


class StaffCanStillReadInternalPages(TestCase):
    """We are changing exposure, not destroying the pages."""

    @classmethod
    def setUpTestData(cls):
        cls.staff = get_user_model().objects.create_user(
            username='gating-staff', password='x', is_staff=True)

    def test_staff_get_200_on_every_gated_route(self):
        client = Client()
        client.force_login(self.staff)
        for route in GATED_ROUTES:
            with self.subTest(route=route):
                response = client.get(route)
                self.assertEqual(
                    response.status_code, 200,
                    f'{route} is no longer reachable by staff — the page was '
                    f'meant to be gated, not broken')
                self.assertGreater(len(response.content), 0)

    def test_a_signed_in_non_staff_user_is_still_refused(self):
        """
        staff_member_required, not login_required: any registered account must
        not be enough to read internal architecture material.
        """
        get_user_model().objects.create_user(username='plain', password='x')
        client = Client()
        client.login(username='plain', password='x')
        response = client.get(GATED_ROUTES[0])
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])


class PublicSurfaceIsUnaffected(TestCase):

    def test_customer_facing_pages_still_serve_anonymously(self):
        anonymous = Client()
        for route in PUBLIC_ROUTES:
            with self.subTest(route=route):
                response = anonymous.get(route)
                self.assertEqual(
                    response.status_code, 200,
                    f'{route} broke — gating was applied too broadly')

    def test_healthz_still_returns_ok(self):
        """PR #234's liveness endpoint must be untouched by this change."""
        response = Client().get('/healthz/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'ok')


class UntouchedCriticalRoutingTests(SimpleTestCase):
    """
    Stripe and authentication routing must be byte-identical after this PR.
    Asserted by URL resolution rather than by reading the diff.
    """

    def test_stripe_webhook_path_is_unchanged(self):
        from django.urls import resolve, reverse

        self.assertEqual(reverse('billing:webhook'), '/billing/webhook/')
        self.assertEqual(resolve('/billing/webhook/').view_name, 'billing:webhook')

    def test_auth_routes_are_unchanged(self):
        from django.urls import reverse

        self.assertEqual(reverse('login'), '/login/')
        self.assertEqual(reverse('logout'), '/logout/')

    def test_gated_route_names_still_reverse(self):
        """
        The apps are retained, so every URL name must still resolve. A template
        elsewhere doing {% url 'impact_mrv_layer:overview' %} must not raise.
        """
        from django.urls import reverse

        for namespace in ('impact_mrv_layer', 'asset_passport',
                          'industrial_playbook_library', 'revenue_pricing_engine'):
            with self.subTest(namespace=namespace):
                self.assertTrue(reverse(f'{namespace}:overview').startswith('/'))


class SitemapExcludesInternalPagesTests(TestCase):
    """
    The sitemap never listed these pages, and must not start listing them.
    Asserted rather than assumed, because StaticSitemap._pages is edited by hand.
    """

    def test_sitemap_advertises_no_gated_route(self):
        body = self.client.get('/sitemap.xml').content.decode()
        for route in GATED_ROUTES:
            with self.subTest(route=route):
                self.assertNotIn(route, body)

    def test_sitemap_still_serves(self):
        self.assertEqual(self.client.get('/sitemap.xml').status_code, 200)
