from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class SalesCrmPartnerPipelinePageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/sales-crm-partner-pipeline/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/sales-crm-partner-pipeline/')
        self.assertContains(response, 'EcoIQ Sales CRM & Partner Pipeline')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/sales-crm-partner-pipeline/')
        self.assertContains(response, 'Track customers, partners, pilots and funding relationships')

    def test_page_mentions_lead_fit_score(self):
        response = self.client.get('/sales-crm-partner-pipeline/')
        self.assertContains(response, 'Lead Fit Score')

    def test_page_mentions_partner_fit_score(self):
        response = self.client.get('/sales-crm-partner-pipeline/')
        self.assertContains(response, 'Partner Fit Score')

    def test_page_mentions_funding_fit_score(self):
        response = self.client.get('/sales-crm-partner-pipeline/')
        self.assertContains(response, 'Funding Fit Score')

    def test_page_mentions_amanah_autopilot_for_crm(self):
        response = self.client.get('/sales-crm-partner-pipeline/')
        self.assertContains(response, 'Amanah Autopilot for CRM')

    def test_page_mentions_no_harm_gate_for_sales(self):
        response = self.client.get('/sales-crm-partner-pipeline/')
        self.assertContains(response, 'No Harm Gate for Sales')

    def test_page_mentions_open_sales_pipeline(self):
        response = self.client.get('/sales-crm-partner-pipeline/')
        self.assertContains(response, 'Open Sales Pipeline')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/sales-crm-partner-pipeline/')
        for label in (
            'Open Sales Pipeline', 'Add New Lead', 'Create Opportunity',
            'Generate Proposal', 'Prepare Investor Outreach', 'Prepare Akimat Brief',
            'Send Follow-Up to Teams', 'Create Sponsor Pack', 'Link Data Room',
            'Update Deal Stage',
        ):
            self.assertContains(response, label)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/sales-crm-partner-pipeline/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageSalesCrmPartnerPipelineTeaserTests(TestCase):
    def test_platform_page_mentions_sales_crm_partner_pipeline(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Sales CRM & Partner Pipeline')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
