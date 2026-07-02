from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class CustomerSuccessRenewalEnginePageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/customer-success-renewal-engine/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/customer-success-renewal-engine/')
        self.assertContains(response, 'EcoIQ Customer Success & Renewal Engine')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/customer-success-renewal-engine/')
        self.assertContains(response, 'Turn pilots into renewals')

    def test_page_mentions_health_score(self):
        response = self.client.get('/customer-success-renewal-engine/')
        self.assertContains(response, 'Health Score')

    def test_page_mentions_renewal_risk(self):
        response = self.client.get('/customer-success-renewal-engine/')
        self.assertContains(response, 'Renewal Risk')

    def test_page_mentions_expansion_ready(self):
        response = self.client.get('/customer-success-renewal-engine/')
        self.assertContains(response, 'Expansion Ready')

    def test_page_mentions_amanah_autopilot_for_customer_success(self):
        response = self.client.get('/customer-success-renewal-engine/')
        self.assertContains(response, 'Amanah Autopilot for Customer Success')

    def test_page_mentions_no_harm_gate_for_customer_success(self):
        response = self.client.get('/customer-success-renewal-engine/')
        self.assertContains(response, 'No Harm Gate for Customer Success')

    def test_page_mentions_open_customer_success_dashboard(self):
        response = self.client.get('/customer-success-renewal-engine/')
        self.assertContains(response, 'Open Customer Success Dashboard')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/customer-success-renewal-engine/')
        for label in (
            'Open Customer Success Dashboard', 'Onboard New Customer',
            'Generate Value Review', 'Check Renewal Risk', 'Prepare Renewal Proposal',
            'Identify Expansion Opportunity', 'Generate Sponsor Update',
            'Request Missing Evidence', 'Send Follow-Up to Teams',
            'Create Customer Health Report',
        ):
            self.assertContains(response, label)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/customer-success-renewal-engine/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageCustomerSuccessRenewalEngineTeaserTests(TestCase):
    def test_platform_page_mentions_customer_success_renewal_engine(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Customer Success & Renewal Engine')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
