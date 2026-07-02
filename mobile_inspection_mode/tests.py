from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class MobileInspectionModePageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/mobile-inspection-mode/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/mobile-inspection-mode/')
        self.assertContains(response, 'EcoIQ Mobile / iPad Inspection Mode')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/mobile-inspection-mode/')
        self.assertContains(response, 'Capture evidence on site')

    def test_page_mentions_start_mobile_inspection(self):
        response = self.client.get('/mobile-inspection-mode/')
        self.assertContains(response, 'Start Mobile Inspection')

    def test_page_mentions_boiler_house_example(self):
        response = self.client.get('/mobile-inspection-mode/')
        self.assertContains(response, 'Boiler House #3')

    def test_page_mentions_offline_mode(self):
        response = self.client.get('/mobile-inspection-mode/')
        self.assertContains(response, 'Offline / Low-Connectivity Mode')

    def test_page_mentions_field_inspection_checklist(self):
        response = self.client.get('/mobile-inspection-mode/')
        self.assertContains(response, 'Field Inspection Checklist')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/mobile-inspection-mode/')
        for label in (
            'Start Mobile Inspection', 'Take Asset Photo', 'Create Asset Passport',
            'Run Photo Diagnosis', 'Generate Field Report', 'Send to Teams',
            'Start MRV Baseline', 'Request Manager Approval',
        ):
            self.assertContains(response, label)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/mobile-inspection-mode/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageMobileInspectionModeTeaserTests(TestCase):
    def test_platform_page_mentions_mobile_inspection_mode(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Mobile / iPad Inspection Mode')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
