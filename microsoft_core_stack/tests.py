from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class MicrosoftCoreStackPageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/microsoft-ecosystem-core-stack/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/microsoft-ecosystem-core-stack/')
        self.assertContains(response, 'EcoIQ Microsoft Ecosystem Core Stack')

    def test_page_mentions_several_repositories(self):
        response = self.client.get('/microsoft-ecosystem-core-stack/')
        for repo in (
            'microsoft/agent-framework', 'microsoft/semantic-kernel', 'microsoft/graphrag',
            'Azure/Industrial-IoT', 'Azure-Samples/azure-digital-twins-samples',
            'microsoft/fabric-samples', 'microsoft/responsible-ai-toolbox',
            'Green-Software-Foundation/carbon-aware-sdk',
        ):
            self.assertContains(response, repo)

    def test_page_mentions_microsoft_ecosystem_ready(self):
        response = self.client.get('/microsoft-ecosystem-core-stack/')
        self.assertContains(response, 'Microsoft ecosystem-ready')

    def test_page_mentions_maqasid_mizan_ethical_scoring(self):
        response = self.client.get('/microsoft-ecosystem-core-stack/')
        self.assertContains(response, 'Maqasid/Mizan ethical scoring')

    def test_page_shows_safety_copy(self):
        response = self.client.get('/microsoft-ecosystem-core-stack/')
        self.assertContains(response, 'not a religious ruling')
        self.assertContains(response, 'human expert approval')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/microsoft-ecosystem-core-stack/')
        for label in (
            'Explore Microsoft Stack', 'Generate Industrial Modernisation Roadmap',
            'Request EcoIQ Review', 'View Digital Twin Example',
        ):
            self.assertContains(response, label)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/microsoft-ecosystem-core-stack/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageMicrosoftStackTeaserTests(TestCase):
    def test_platform_page_mentions_microsoft_core_stack(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Microsoft Ecosystem Core Stack')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
