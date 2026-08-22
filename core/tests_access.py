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
