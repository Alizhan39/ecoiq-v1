from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class MrvAgentTrainingPackPageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/mrv-agent-training-pack/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/mrv-agent-training-pack/')
        self.assertContains(response, 'EcoIQ MRV Agent Training Pack')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/mrv-agent-training-pack/')
        self.assertContains(
            response,
            'Train the agent that separates estimated impact from verified impact',
        )

    def test_page_mentions_estimated_vs_verified(self):
        response = self.client.get('/mrv-agent-training-pack/')
        self.assertContains(response, 'Estimated vs Verified')

    def test_page_mentions_mrv_verified(self):
        response = self.client.get('/mrv-agent-training-pack/')
        self.assertContains(response, 'MRV Verified')

    def test_page_mentions_baseline_captured(self):
        response = self.client.get('/mrv-agent-training-pack/')
        self.assertContains(response, 'Baseline Captured')

    def test_page_mentions_after_data_pending(self):
        response = self.client.get('/mrv-agent-training-pack/')
        self.assertContains(response, 'After-Data Pending')

    def test_page_mentions_mrv_golden_test_cases(self):
        response = self.client.get('/mrv-agent-training-pack/')
        self.assertContains(response, 'MRV Golden Test Cases')

    def test_page_mentions_no_harm_gate_for_mrv(self):
        response = self.client.get('/mrv-agent-training-pack/')
        self.assertContains(response, 'No Harm Gate for MRV')

    def test_page_mentions_open_mrv_agent_training_pack(self):
        response = self.client.get('/mrv-agent-training-pack/')
        self.assertContains(response, 'Open MRV Agent Training Pack')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/mrv-agent-training-pack/')
        for label in (
            'Open MRV Agent Training Pack', 'Create MRV Golden Test',
            'Review Baseline Evidence', 'Review After-Data', 'Check Estimated vs Verified',
            'Send MRV to Human Review', 'Recommend MRV Badge',
            'Open Public Reporting Readiness', 'Run MRV Evaluation', 'Generate MRV Briefing',
        ):
            self.assertContains(response, label)

    def test_page_has_no_claim_mrv_agent_independently_certifies(self):
        response = self.client.get('/mrv-agent-training-pack/')
        self.assertContains(response, 'MRV Agent checks evidence readiness; it does not independently certify impact.')

    def test_page_has_no_claim_estimated_equals_verified(self):
        response = self.client.get('/mrv-agent-training-pack/')
        self.assertContains(response, 'Estimated impact must not be presented as verified impact.')

    def test_page_has_no_unsupported_microsoft_certification_claim(self):
        response = self.client.get('/mrv-agent-training-pack/')
        content = response.content.decode()
        self.assertNotIn('Microsoft certified', content)
        self.assertNotIn('official partner', content)

    def test_page_has_no_unsupported_fatwa_or_shariah_claim(self):
        response = self.client.get('/mrv-agent-training-pack/')
        content = response.content.decode()
        self.assertNotIn('is a fatwa', content)
        self.assertNotIn('Shariah certified', content)
        self.assertNotIn('Shariah certification', content)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/mrv-agent-training-pack/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageMrvAgentTrainingPackTeaserTests(TestCase):
    def test_platform_page_mentions_mrv_agent_training_pack(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ MRV Agent Training Pack')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
