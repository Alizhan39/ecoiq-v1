from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class SupplierFundingMarketplacePageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/supplier-funding-marketplace/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/supplier-funding-marketplace/')
        self.assertContains(response, 'EcoIQ Supplier & Funding Marketplace')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/supplier-funding-marketplace/')
        self.assertContains(response, 'From recommended action to funded implementation')

    def test_page_mentions_supplier_fit_score(self):
        response = self.client.get('/supplier-funding-marketplace/')
        self.assertContains(response, 'Supplier Fit Score')

    def test_page_mentions_funding_fit_score(self):
        response = self.client.get('/supplier-funding-marketplace/')
        self.assertContains(response, 'Funding Fit Score')

    def test_page_mentions_boiler_house_example(self):
        response = self.client.get('/supplier-funding-marketplace/')
        self.assertContains(response, 'Boiler House #3 Modernisation')

    def test_page_mentions_no_harm_gate_for_marketplace(self):
        response = self.client.get('/supplier-funding-marketplace/')
        self.assertContains(response, 'No Harm Gate for Marketplace')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/supplier-funding-marketplace/')
        for label in (
            'Find Suppliers', 'Match Funding', 'Generate Supplier Brief',
            'Prepare Funding Memo', 'Create Outreach Email', 'Start Implementation',
            'Verify Impact',
        ):
            self.assertContains(response, label)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/supplier-funding-marketplace/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageSupplierFundingMarketplaceTeaserTests(TestCase):
    def test_platform_page_mentions_supplier_funding_marketplace(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Supplier & Funding Marketplace')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
