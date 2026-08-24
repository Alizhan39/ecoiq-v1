"""
core/tests_access.py — the experimental surfaces stop answering anonymously,
and the public product keeps answering.

Both halves matter. A gate that catches the public product is worse than no
gate, so the second class here is as long as the first.
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase

from core import access
from core.redirects import PERMANENT


class GatedSurfacesTests(TestCase):
    """Every declared prefix and exact path requires a signed-in user."""

    def setUp(self):
        cache.clear()

    def test_every_declared_prefix_is_gated(self):
        """
        Driven from the declaration, so adding a prefix adds its test and
        removing one fails here rather than silently re-publishing a page.
        """
        for prefix in access.SIGN_IN_PREFIXES:
            with self.subTest(prefix=prefix):
                response = self.client.get(prefix)
                self.assertEqual(response.status_code, 302)
                self.assertIn('/login/', response['Location'])

    def test_every_declared_exact_path_is_gated(self):
        for path in sorted(access.SIGN_IN_EXACT):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertIn('/login/', response['Location'])

    def test_the_gate_carries_the_destination(self):
        """A visitor who signs in should land where they were going."""
        response = self.client.get('/legacy-safe/audit-logs/')
        self.assertIn('next=/legacy-safe/audit-logs/', response['Location'])

    def test_a_signed_in_user_gets_through(self):
        """
        Sign-in, not deletion. Every gated surface keeps working — this is a
        de-publication, and a de-publication that also broke the page would be
        a deletion with extra steps.
        """
        user = get_user_model().objects.create_user(
            username='gate-tester', password='correct-horse-battery')
        client = Client()
        client.force_login(user)

        response = client.get('/legacy-safe/')
        self.assertEqual(response.status_code, 200)

    def test_an_api_path_under_a_gated_prefix_answers_json(self):
        """
        Redirecting an XHR to a login page hands the caller an HTML body and a
        200, which reads as a parse error rather than as "sign in".
        """
        response = self.client.get('/digital-twin/api/assets/')
        self.assertEqual(response.status_code, 403)
        self.assertIn('application/json', response['Content-Type'])

    def test_no_gated_surface_is_in_the_sitemap(self):
        """A sitemap entry behind a login is an instruction to index a 302."""
        import re

        body = self.client.get('/sitemap.xml').content.decode()
        for path in re.findall(r'<loc>https?://[^/]+([^<]*)</loc>', body):
            with self.subTest(path=path):
                self.assertFalse(
                    access.requires_sign_in(path),
                    f'{path} is in the sitemap and requires sign-in.')


class PublicSurfaceIsUntouchedTests(TestCase):
    """
    The gate must not catch the product.

    Listed explicitly rather than derived, because deriving the allowed set
    from the same tuple the gate reads would prove only that the tuple equals
    itself.
    """

    PUBLIC = (
        '/', '/intelligence/', '/projects/', '/tours/', '/about/', '/contact/',
        '/pricing/', '/league/', '/labs/', '/trust/',
        '/companies/', '/countries/', '/press/', '/investors/', '/api-docs/',
        '/gcc-investors/', '/heating/', '/khalifa-tours/',
        '/request-access/enterprise/', '/login/', '/register/',
        '/governance-principles/', '/ethical-governance/',
    )

    def setUp(self):
        cache.clear()

    def test_the_public_surface_still_answers_anonymously(self):
        for path in self.PUBLIC:
            with self.subTest(path=path):
                self.assertFalse(
                    access.requires_sign_in(path),
                    f'{path} is public product and must not require sign-in.')
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_the_company_directory_and_a_company_page_stay_public(self):
        """
        /companies/ shares a prefix with three gated analyst tools. The gate
        uses exact paths there for exactly this reason.
        """
        from companies.testing import unpopulated
        from league.models import Company

        company = Company.objects.create(
            name='Gate Co', slug='gate-co', sector='Energy')
        unpopulated(company, status='public')

        self.assertEqual(self.client.get('/companies/').status_code, 200)
        self.assertEqual(self.client.get('/companies/gate-co/').status_code, 200)

    def test_healthz_and_the_api_are_untouched(self):
        self.assertEqual(self.client.get('/healthz/').status_code, 200)
        self.assertEqual(self.client.get('/api/v2/').status_code, 200)


class PermanentRedirectTests(TestCase):
    """Retired public pages point at the React page that covers them."""

    def setUp(self):
        cache.clear()

    def test_each_old_path_returns_301(self):
        for old, new in PERMANENT.items():
            with self.subTest(old=old):
                response = self.client.get(old)
                self.assertEqual(response.status_code, 301)
                self.assertEqual(response['Location'], new)

    def test_no_redirect_chains(self):
        """
        Every destination is a live page, not another redirect. A chain costs a
        round trip and crawlers give up on long ones.
        """
        for old, new in PERMANENT.items():
            with self.subTest(old=old):
                response = self.client.get(new)
                self.assertEqual(
                    response.status_code, 200,
                    f'{old} redirects to {new}, which is not a 200.')

    def test_every_destination_is_the_react_app(self):
        for old, new in PERMANENT.items():
            with self.subTest(old=old):
                self.assertContains(self.client.get(new), 'id="root"')

    def test_the_url_names_still_reverse(self):
        """
        The names survive the redirect, so `{% url 'methodology' %}` in the
        templates that are still server-rendered keeps resolving.
        """
        from django.urls import reverse

        for name in ('methodology', 'platform', 'stewardship',
                     'value_distribution', 'sample_report'):
            with self.subTest(name=name):
                self.assertTrue(reverse(name))

    def test_no_surviving_template_links_to_a_retired_path(self):
        """
        A link that needs a redirect is a link nobody updated. One hop is not a
        chain, but it is still a page telling a visitor to go somewhere that
        tells them to go somewhere else.
        """
        import pathlib

        offenders = []
        for path in pathlib.Path('templates').rglob('*.html'):
            text = path.read_text(encoding='utf-8', errors='ignore')
            for old in PERMANENT:
                if f'"{old}"' in text or f"'{old}'" in text:
                    offenders.append(f'{path} -> {old}')
        self.assertEqual(offenders, [])


class PerCompanyOrphanPagesTests(TestCase):
    """
    The two per-organisation Django pages the Phase 10 audit found.

    Gated at the slugged path, not just at the bare prefix the declaration
    test walks — /company-intelligence/ has no route of its own, so a gate
    that only covered the prefix would prove nothing about the page anyone
    could actually reach.
    """

    def setUp(self):
        cache.clear()

    def test_the_company_intelligence_page_requires_sign_in(self):
        response = self.client.get('/company-intelligence/abb-turkiye/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_the_why_page_requires_sign_in(self):
        response = self.client.get('/why/company/abb-turkiye/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_the_why_pdf_is_gated_with_its_page(self):
        """
        The PDF carries the same per-organisation content. Exempting it as a
        "server document" would de-publish the page and republish it in
        another format.
        """
        response = self.client.get('/why/company/abb-turkiye/pack.pdf')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])

    def test_a_slug_that_does_not_exist_no_longer_answers_anonymously(self):
        """
        The defect that put these on the list: both rendered a full 200 for a
        slug EcoIQ holds nothing on, in production. A public per-company URL
        that never 404s is an unbounded supply of indexable pages.
        """
        for path in ('/company-intelligence/does-not-exist-xyz/',
                     '/why/company/does-not-exist-xyz/'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 302)

    def test_a_signed_in_user_still_gets_both_pages(self):
        user = get_user_model().objects.create_user(username='why-reader')
        client = Client()
        client.force_login(user)
        for path in ('/company-intelligence/abb-turkiye/',
                     '/why/company/abb-turkiye/'):
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 200)

    def test_the_public_organisation_page_is_untouched(self):
        """
        /companies/<slug>/ is the organisation page and stays public. A gate
        that caught it would be the regression, not the fix.
        """
        response = self.client.get('/companies/abb-turkiye/')
        self.assertIn(response.status_code, (200, 404))
        self.assertNotEqual(response.status_code, 302)


class CompanyLeafPagesTests(TestCase):
    """
    /companies/<slug>/ stays public; three leaves under it do not.

    The slug sits in the middle, so neither a prefix nor an exact path can
    express this — which is why these three outlived every earlier sweep.
    """

    def setUp(self):
        cache.clear()
        from companies.testing import populated
        from league.models import Company

        self.company = Company.objects.create(
            name='Leaf Co', slug='leaf-co', sector='energy', country='GB')
        self.profile = populated(self.company)

    def test_each_leaf_requires_sign_in(self):
        for suffix in access.COMPANY_LEAF_SUFFIXES:
            with self.subTest(suffix=suffix):
                response = self.client.get(f'/companies/leaf-co{suffix}')
                self.assertEqual(response.status_code, 302)
                self.assertIn('/login/', response['Location'])

    def test_the_organisation_page_itself_stays_public(self):
        """The rule this class exists to not break."""
        response = self.client.get('/companies/leaf-co/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(access.requires_sign_in('/companies/leaf-co/'))

    def test_the_directory_stays_public(self):
        self.assertFalse(access.requires_sign_in('/companies/'))
        self.assertEqual(self.client.get('/companies/').status_code, 200)

    def test_a_signed_in_user_still_gets_the_leaves(self):
        user = get_user_model().objects.create_user(username='leaf-reader')
        client = Client()
        client.force_login(user)
        for suffix in access.COMPANY_LEAF_SUFFIXES:
            with self.subTest(suffix=suffix):
                response = client.get(f'/companies/leaf-co{suffix}')
                self.assertEqual(response.status_code, 200)

    def test_the_rule_does_not_reach_outside_companies(self):
        """
        A suffix rule is a blunt instrument. It must not gate a same-named
        path under another app.
        """
        for path in ('/portfolio/leaf-co/stock/', '/labs/explain/',
                     '/companies/leaf-co/deeper/stock/'):
            with self.subTest(path=path):
                self.assertFalse(access.requires_sign_in(path))

    def test_no_gated_leaf_publishes_a_withheld_score(self):
        """
        The charge against these pages is that they are unlinked duplicates,
        NOT that they leak. Asserting the difference keeps the record honest —
        and turns a measurement into a guarantee, so a future edit to any of
        the three templates cannot quietly start publishing the composite.
        """
        from companies.eligibility import decide

        self.profile.ecoiq_total_score = 73.6
        self.profile.save(update_fields=['ecoiq_total_score'])
        self.profile.refresh_from_db()
        self.assertFalse(decide(self.profile).is_published,
                         'Fixture must be unpublishable for this to mean '
                         'anything.')

        user = get_user_model().objects.create_user(username='leaf-auditor')
        client = Client()
        client.force_login(user)
        for suffix in access.COMPANY_LEAF_SUFFIXES:
            with self.subTest(suffix=suffix):
                body = client.get(
                    f'/companies/leaf-co{suffix}').content.decode()
                self.assertNotIn('73.6', body)
