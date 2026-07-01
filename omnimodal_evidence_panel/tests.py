from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% for', '{% if',
]


class OmnimodalEvidencePanelPageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/omnimodal-evidence-panel/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/omnimodal-evidence-panel/')
        self.assertContains(response, 'Omnimodal Evidence Panel')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/omnimodal-evidence-panel/')
        self.assertContains(response, 'When AI reads, the interface shows what it sees.')

    def test_page_shows_key_workflow_text(self):
        response = self.client.get('/omnimodal-evidence-panel/')
        for step in ('Omnimodal intake', 'Sensitivity check', 'Model router', 'Monitoring/MRV'):
            self.assertContains(response, step)

    def test_page_shows_model_cards(self):
        response = self.client.get('/omnimodal-evidence-panel/')
        for model in ('Gemini Live', 'Azure OpenAI', 'Claude', 'Kimi', 'DeepSeek'):
            self.assertContains(response, model)

    def test_page_shows_safety_copy(self):
        response = self.client.get('/omnimodal-evidence-panel/')
        self.assertContains(response, 'not final engineering certification')
        self.assertContains(response, 'not a fatwa or religious ruling')
        self.assertContains(response, 'Needs verification')

    def test_page_shows_industrial_examples(self):
        response = self.client.get('/omnimodal-evidence-panel/')
        self.assertContains(response, 'Boiler House Photo')
        self.assertContains(response, 'Factory Production Line')
        self.assertContains(response, 'Annual Report / ESG Claim')

    def test_page_links_to_amanah_autopilot(self):
        response = self.client.get('/omnimodal-evidence-panel/')
        self.assertContains(response, 'Good Deeds Overnight Report')

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/omnimodal-evidence-panel/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageOmnimodalTeaserTests(TestCase):
    def test_platform_page_mentions_omnimodal_evidence_panel(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Omnimodal Evidence Panel')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
