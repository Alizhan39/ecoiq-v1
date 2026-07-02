from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class CommandCentrePageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/command-centre/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/command-centre/')
        self.assertContains(response, 'EcoIQ Command Centre')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/command-centre/')
        self.assertContains(
            response,
            'One dashboard for industrial modernisation, finance and verified impact',
        )

    def test_page_mentions_project_pipeline(self):
        response = self.client.get('/command-centre/')
        self.assertContains(response, 'Project Pipeline')

    def test_page_mentions_morning_command_briefing(self):
        response = self.client.get('/command-centre/')
        self.assertContains(response, 'Morning Command Briefing')

    def test_page_mentions_no_harm_gate_alerts(self):
        response = self.client.get('/command-centre/')
        self.assertContains(response, 'No Harm Gate Alerts')

    def test_page_mentions_finance_ready(self):
        response = self.client.get('/command-centre/')
        self.assertContains(response, 'Finance Ready')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/command-centre/')
        for label in (
            'Open Command Centre', 'View Project Pipeline', 'Filter Finance-Ready Projects',
            'Show High-Harm Assets', 'Generate Morning Briefing', 'Export Power BI Dashboard',
            'Assign Next Action', 'Verify Impact',
        ):
            self.assertContains(response, label)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/command-centre/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageCommandCentreTeaserTests(TestCase):
    def test_platform_page_mentions_command_centre(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Command Centre')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
