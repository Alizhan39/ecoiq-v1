from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class FrontendExperienceGoogleStitchDesignSystemPageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/frontend-experience-google-stitch-design-system/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/frontend-experience-google-stitch-design-system/')
        self.assertContains(response, 'EcoIQ Frontend Experience & Google Stitch Design System')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/frontend-experience-google-stitch-design-system/')
        self.assertContains(response, 'A visual, mobile-first, Microsoft-ready interface')

    def test_page_mentions_stitch_prompt_library(self):
        response = self.client.get('/frontend-experience-google-stitch-design-system/')
        self.assertContains(response, 'Google Stitch Prompt Library')

    def test_page_mentions_ui_screens(self):
        response = self.client.get('/frontend-experience-google-stitch-design-system/')
        for title in (
            'Command Centre Dashboard', 'Asset Passport Page', 'Country Transition Atlas',
            'Knowledge Graph', 'Mobile Inspection Mode', 'Public Trust Portal',
        ):
            self.assertContains(response, title)

    def test_page_mentions_microsoft_partner_frontend_pack(self):
        response = self.client.get('/frontend-experience-google-stitch-design-system/')
        self.assertContains(response, 'Microsoft Partner Frontend Pack')

    def test_page_mentions_open_design_system(self):
        response = self.client.get('/frontend-experience-google-stitch-design-system/')
        self.assertContains(response, 'Open Design System')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/frontend-experience-google-stitch-design-system/')
        for label in (
            'Open Design System', 'Copy Google Stitch Prompts', 'View Command Centre Mockup',
            'View Asset Passport UI', 'View Country Atlas UI', 'View Knowledge Graph UI',
            'View Mobile Inspection UI', 'View Public Trust Portal UI',
            'View Microsoft Partner UI Pack', 'Export Component Library',
        ):
            self.assertContains(response, label)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/frontend-experience-google-stitch-design-system/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageFrontendExperienceGoogleStitchDesignSystemTeaserTests(TestCase):
    def test_platform_page_mentions_frontend_experience_google_stitch_design_system(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Frontend Experience & Google Stitch Design System')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
