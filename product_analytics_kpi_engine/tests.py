from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class ProductAnalyticsKpiEnginePageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/product-analytics-kpi-engine/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/product-analytics-kpi-engine/')
        self.assertContains(response, 'EcoIQ Product Analytics & KPI Engine')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/product-analytics-kpi-engine/')
        self.assertContains(
            response,
            'Track usage, conversion, revenue, impact and product performance',
        )

    def test_page_mentions_product_usage_analytics(self):
        response = self.client.get('/product-analytics-kpi-engine/')
        self.assertContains(response, 'Product Usage Analytics')

    def test_page_mentions_conversion_analytics(self):
        response = self.client.get('/product-analytics-kpi-engine/')
        self.assertContains(response, 'Conversion Analytics')

    def test_page_mentions_revenue_analytics(self):
        response = self.client.get('/product-analytics-kpi-engine/')
        self.assertContains(response, 'Revenue Analytics')

    def test_page_mentions_impact_analytics(self):
        response = self.client.get('/product-analytics-kpi-engine/')
        self.assertContains(response, 'Impact Analytics')

    def test_page_mentions_amanah_autopilot_for_analytics(self):
        response = self.client.get('/product-analytics-kpi-engine/')
        self.assertContains(response, 'Amanah Autopilot for Analytics')

    def test_page_mentions_no_harm_gate_for_analytics(self):
        response = self.client.get('/product-analytics-kpi-engine/')
        self.assertContains(response, 'No Harm Gate for Analytics')

    def test_page_mentions_open_kpi_dashboard(self):
        response = self.client.get('/product-analytics-kpi-engine/')
        self.assertContains(response, 'Open KPI Dashboard')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/product-analytics-kpi-engine/')
        for label in (
            'Open KPI Dashboard', 'View Product Funnel', 'Track Revenue Metrics',
            'View MRV Completion', 'Show Country Pipeline', 'Analyse Module Adoption',
            'Export Power BI Report', 'Generate Weekly KPI Brief', 'Flag Drop-Offs',
            'Send KPI Briefing to Teams',
        ):
            self.assertContains(response, label)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/product-analytics-kpi-engine/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageProductAnalyticsKpiEngineTeaserTests(TestCase):
    def test_platform_page_mentions_product_analytics_kpi_engine(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Product Analytics & KPI Engine')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
