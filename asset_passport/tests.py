from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class AssetPassportPageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/asset-passport/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/asset-passport/')
        self.assertContains(response, 'EcoIQ Asset Passport')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/asset-passport/')
        self.assertContains(response, 'Every industrial asset becomes a measurable modernisation project')

    def test_page_mentions_example_asset(self):
        response = self.client.get('/asset-passport/')
        self.assertContains(response, 'Boiler House #3')

    def test_page_mentions_maqasid_score(self):
        response = self.client.get('/asset-passport/')
        self.assertContains(response, 'Maqasid score')

    def test_page_mentions_mizan_score(self):
        response = self.client.get('/asset-passport/')
        self.assertContains(response, 'Mizan score')

    def test_page_mentions_no_harm_gate(self):
        response = self.client.get('/asset-passport/')
        self.assertContains(response, 'No Harm Gate')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/asset-passport/')
        for label in (
            'Create Asset Passport', 'Upload Asset Evidence', 'Run Modernisation Diagnosis',
            'Generate Investor Brief', 'Verify Impact',
        ):
            self.assertContains(response, label)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/asset-passport/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageAssetPassportTeaserTests(TestCase):
    def test_platform_page_mentions_asset_passport(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Asset Passport')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
