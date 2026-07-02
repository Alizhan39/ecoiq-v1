from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class RevenuePricingEnginePageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/revenue-pricing-engine/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/revenue-pricing-engine/')
        self.assertContains(response, 'EcoIQ Revenue & Pricing Engine')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/revenue-pricing-engine/')
        self.assertContains(response, 'Turn industrial intelligence into paid products')

    def test_page_mentions_free_ecoiq_scan(self):
        response = self.client.get('/revenue-pricing-engine/')
        self.assertContains(response, 'Free EcoIQ Scan')

    def test_page_mentions_asset_passport(self):
        response = self.client.get('/revenue-pricing-engine/')
        self.assertContains(response, 'Asset Passport')

    def test_page_mentions_mrv_verification_pack(self):
        response = self.client.get('/revenue-pricing-engine/')
        self.assertContains(response, 'MRV Verification Pack')

    def test_page_mentions_investor_readiness_memo(self):
        response = self.client.get('/revenue-pricing-engine/')
        self.assertContains(response, 'Investor Readiness Memo')

    def test_page_mentions_enterprise_subscription(self):
        response = self.client.get('/revenue-pricing-engine/')
        self.assertContains(response, 'Enterprise Subscription')

    def test_page_mentions_no_harm_gate_for_revenue(self):
        response = self.client.get('/revenue-pricing-engine/')
        self.assertContains(response, 'No Harm Gate for Revenue')

    def test_page_mentions_request_enterprise_pilot(self):
        response = self.client.get('/revenue-pricing-engine/')
        self.assertContains(response, 'Request Enterprise Pilot')

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/revenue-pricing-engine/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageRevenuePricingEngineTeaserTests(TestCase):
    def test_platform_page_mentions_revenue_pricing_engine(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Revenue & Pricing Engine')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
