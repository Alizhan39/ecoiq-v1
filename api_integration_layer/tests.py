from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class ApiIntegrationLayerPageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/api-integration-layer/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/api-integration-layer/')
        self.assertContains(response, 'EcoIQ API & Integration Layer')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/api-integration-layer/')
        self.assertContains(response, 'Connect EcoIQ intelligence to Microsoft')

    def test_page_mentions_asset_passport_api(self):
        response = self.client.get('/api-integration-layer/')
        self.assertContains(response, 'Asset Passport API')

    def test_page_mentions_webhook_events(self):
        response = self.client.get('/api-integration-layer/')
        self.assertContains(response, 'Webhook Events')

    def test_page_mentions_microsoft_integration_blueprint(self):
        response = self.client.get('/api-integration-layer/')
        self.assertContains(response, 'Microsoft Integration Blueprint')

    def test_page_mentions_send_approval_to_teams(self):
        response = self.client.get('/api-integration-layer/')
        self.assertContains(response, 'Send Approval to Teams')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/api-integration-layer/')
        for label in (
            'View API Docs', 'Connect Microsoft Teams', 'Export to Power BI',
            'Sync Asset Passport', 'Create Webhook', 'Connect IoT Sensor',
            'Generate Evidence Pack', 'Send Approval to Teams', 'Export MRV Report',
        ):
            self.assertContains(response, label)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/api-integration-layer/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageApiIntegrationLayerTeaserTests(TestCase):
    def test_platform_page_mentions_api_integration_layer(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ API & Integration Layer')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
