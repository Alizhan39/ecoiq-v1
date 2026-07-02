from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class PublicTrustImpactPortalPageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/public-trust-impact-portal/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/public-trust-impact-portal/')
        self.assertContains(response, 'EcoIQ Public Trust & Impact Portal')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/public-trust-impact-portal/')
        self.assertContains(
            response,
            'Show verified impact publicly without exposing sensitive evidence',
        )

    def test_page_mentions_verified_impact_map(self):
        response = self.client.get('/public-trust-impact-portal/')
        self.assertContains(response, 'Verified Impact Map')

    def test_page_mentions_public_mrv_registry(self):
        response = self.client.get('/public-trust-impact-portal/')
        self.assertContains(response, 'Public MRV Registry')

    def test_page_mentions_public_summary_approved(self):
        response = self.client.get('/public-trust-impact-portal/')
        self.assertContains(response, 'Public Summary Approved')

    def test_page_mentions_no_harm_gate_for_public_reporting(self):
        response = self.client.get('/public-trust-impact-portal/')
        self.assertContains(response, 'No Harm Gate for Public Reporting')

    def test_page_mentions_open_public_impact_portal(self):
        response = self.client.get('/public-trust-impact-portal/')
        self.assertContains(response, 'Open Public Impact Portal')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/public-trust-impact-portal/')
        for label in (
            'Open Public Impact Portal', 'Publish Verified Impact Story',
            'Generate Public Summary', 'Review Public MRV Registry',
            'Create Sponsor Impact Page', 'Update Country Progress',
            'Export Public Impact Report', 'Send for Approval', 'Redact Sensitive Data',
            'View Verified Impact Map',
        ):
            self.assertContains(response, label)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/public-trust-impact-portal/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPagePublicTrustImpactPortalTeaserTests(TestCase):
    def test_platform_page_mentions_public_trust_impact_portal(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Public Trust & Impact Portal')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
