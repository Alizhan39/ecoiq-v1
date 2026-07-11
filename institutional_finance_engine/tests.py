from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class InstitutionalFinanceEnginePageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/institutional-finance-engine/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/institutional-finance-engine/')
        self.assertContains(response, 'EcoIQ Institutional Finance Engine')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/institutional-finance-engine/')
        self.assertContains(response, 'From industrial evidence to investment-ready decisions')

    def test_page_mentions_payback(self):
        response = self.client.get('/institutional-finance-engine/')
        self.assertContains(response, 'Payback')

    def test_page_mentions_irr(self):
        response = self.client.get('/institutional-finance-engine/')
        self.assertContains(response, 'IRR')

    def test_page_mentions_npv(self):
        response = self.client.get('/institutional-finance-engine/')
        self.assertContains(response, 'NPV')

    def test_page_mentions_islamic_finance_fit(self):
        response = self.client.get('/institutional-finance-engine/')
        self.assertContains(response, 'Islamic Finance Fit')

    def test_page_mentions_no_harm_gate_for_finance(self):
        response = self.client.get('/institutional-finance-engine/')
        self.assertContains(response, 'No Harm Gate for Finance')

    def test_page_mentions_institutional_memo_builder(self):
        response = self.client.get('/institutional-finance-engine/')
        self.assertContains(response, 'Institutional Memo Builder')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/institutional-finance-engine/')
        for label in (
            'Run Finance Model', 'Generate Investor Memo', 'Assess Finance Fit',
            'Calculate Payback', 'Prepare Grant Brief', 'Check Islamic Finance Fit',
            'Export to Power BI', 'Start MRV Tracking',
        ):
            self.assertContains(response, label)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/institutional-finance-engine/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageInstitutionalFinanceEngineTeaserTests(TestCase):
    def test_platform_page_no_longer_mentions_institutional_finance_engine(self):
        """
        Phase 1A follow-up: institutional_finance_engine is deprecated in
        favour of financial_intelligence_cloud, and its module card + promo
        section were removed from /platform/. This guards against the
        deprecated module's teaser silently reappearing.
        """
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'EcoIQ Institutional Finance Engine')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
