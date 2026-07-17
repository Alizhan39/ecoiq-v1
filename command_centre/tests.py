"""
command_centre/tests.py — updated for feat/project-command-centre-primary-surface.

The old CommandCentrePageTests below asserted the static mockup page's
content directly (title, subtitle, CTA button labels). That page no longer
renders at this URL — command_centre.views.overview() now redirects to the
real project directory (see that view's docstring for why). These tests
are deliberately rewritten to verify the redirect, not deleted or silently
left to fail: the old assertions would all fail today, which is the
intended, documented behavior change for this PR, not a regression to hide.
"""
from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class CommandCentreLegacyRedirectTests(TestCase):
    """The deprecated static /command-centre/ route now redirects to the
    real project directory rather than rendering its old mockup content."""

    def test_legacy_route_redirects_to_project_directory(self):
        response = self.client.get('/command-centre/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/capital-guardian/')

    def test_legacy_route_redirect_followed_reaches_real_page(self):
        response = self.client.get('/command-centre/', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Investor Transparency')

    def test_legacy_redirect_does_not_require_authentication(self):
        """The redirect itself must not become an access-control gate — the
        directory it points to is, and always was, public/read-only."""
        response = self.client.get('/command-centre/')
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('/login', response['Location'])

    def test_named_url_still_resolves(self):
        """templates/platform.html, governance_expert_review_board/views.py,
        and frontend_implementation_roadmap/views.py all reference
        {% url 'command_centre:overview' %} — the URL name must keep
        resolving even though the view's behavior changed."""
        from django.urls import reverse
        self.assertEqual(reverse('command_centre:overview'), '/command-centre/')


class PlatformPageCommandCentreTeaserTests(TestCase):
    def test_platform_page_mentions_command_centre(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Command Centre')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
