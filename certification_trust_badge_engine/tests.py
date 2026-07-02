from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class CertificationTrustBadgeEnginePageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/certification-trust-badge-engine/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/certification-trust-badge-engine/')
        self.assertContains(response, 'EcoIQ Certification & Trust Badge Engine')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/certification-trust-badge-engine/')
        self.assertContains(response, 'Show readiness, verification and trust status through clear badges')

    def test_page_mentions_mrv_verified(self):
        response = self.client.get('/certification-trust-badge-engine/')
        self.assertContains(response, 'MRV Verified')

    def test_page_mentions_finance_ready(self):
        response = self.client.get('/certification-trust-badge-engine/')
        self.assertContains(response, 'Finance Ready')

    def test_page_mentions_data_room_complete(self):
        response = self.client.get('/certification-trust-badge-engine/')
        self.assertContains(response, 'Data Room Complete')

    def test_page_mentions_no_harm_gate_passed(self):
        response = self.client.get('/certification-trust-badge-engine/')
        self.assertContains(response, 'No Harm Gate Passed')

    def test_page_mentions_badge_revocation_rules(self):
        response = self.client.get('/certification-trust-badge-engine/')
        self.assertContains(response, 'Badge Revocation Rules')

    def test_page_mentions_knowledge_graph_integration(self):
        response = self.client.get('/certification-trust-badge-engine/')
        self.assertContains(response, 'Knowledge Graph Integration')

    def test_page_mentions_frontend_integration(self):
        response = self.client.get('/certification-trust-badge-engine/')
        self.assertContains(response, 'Frontend Integration')

    def test_page_mentions_no_harm_gate_for_badges(self):
        response = self.client.get('/certification-trust-badge-engine/')
        self.assertContains(response, 'No Harm Gate for Badges')

    def test_page_mentions_open_trust_badge_engine(self):
        response = self.client.get('/certification-trust-badge-engine/')
        self.assertContains(response, 'Open Trust Badge Engine')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/certification-trust-badge-engine/')
        for label in (
            'Open Trust Badge Engine', 'Issue Badge', 'Review Badge Evidence',
            'Approve Public Badge', 'Revoke Badge', 'Check Badge Requirements',
            'Export Badge Report', 'Send Badge Review to Teams',
            'Show Finance Ready Projects', 'Show MRV Verified Projects',
        ):
            self.assertContains(response, label)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/certification-trust-badge-engine/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageCertificationTrustBadgeEngineTeaserTests(TestCase):
    def test_platform_page_mentions_certification_trust_badge_engine(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Certification & Trust Badge Engine')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
