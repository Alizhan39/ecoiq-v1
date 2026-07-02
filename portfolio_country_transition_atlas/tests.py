from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class PortfolioCountryTransitionAtlasPageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/portfolio-country-transition-atlas/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/portfolio-country-transition-atlas/')
        self.assertContains(response, 'EcoIQ Portfolio & Country Transition Atlas')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/portfolio-country-transition-atlas/')
        self.assertContains(
            response,
            'Map transition risk, finance-ready projects and verified impact',
        )

    def test_page_mentions_kazakhstan(self):
        response = self.client.get('/portfolio-country-transition-atlas/')
        self.assertContains(response, 'Kazakhstan')

    def test_page_mentions_united_kingdom(self):
        response = self.client.get('/portfolio-country-transition-atlas/')
        self.assertContains(response, 'United Kingdom')

    def test_page_mentions_saudi_arabia(self):
        response = self.client.get('/portfolio-country-transition-atlas/')
        self.assertContains(response, 'Saudi Arabia')

    def test_page_mentions_turkiye(self):
        response = self.client.get('/portfolio-country-transition-atlas/')
        self.assertContains(response, 'Türkiye')

    def test_page_mentions_highest_harm_view(self):
        response = self.client.get('/portfolio-country-transition-atlas/')
        self.assertContains(response, 'Highest Harm View')

    def test_page_mentions_highest_impact_view(self):
        response = self.client.get('/portfolio-country-transition-atlas/')
        self.assertContains(response, 'Highest Impact View')

    def test_page_mentions_finance_ready_view(self):
        response = self.client.get('/portfolio-country-transition-atlas/')
        self.assertContains(response, 'Finance-Ready View')

    def test_page_mentions_verified_impact_view(self):
        response = self.client.get('/portfolio-country-transition-atlas/')
        self.assertContains(response, 'Verified Impact View')

    def test_page_mentions_open_transition_atlas(self):
        response = self.client.get('/portfolio-country-transition-atlas/')
        self.assertContains(response, 'Open Transition Atlas')

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/portfolio-country-transition-atlas/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPagePortfolioCountryTransitionAtlasTeaserTests(TestCase):
    def test_platform_page_mentions_portfolio_country_transition_atlas(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Portfolio & Country Transition Atlas')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
