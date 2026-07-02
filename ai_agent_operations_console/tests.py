from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class AiAgentOperationsConsolePageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/ai-agent-operations-console/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/ai-agent-operations-console/')
        self.assertContains(response, 'EcoIQ AI Agent Operations Console')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/ai-agent-operations-console/')
        self.assertContains(response, 'Monitor agents, tasks, evidence, costs and human approvals')

    def test_page_mentions_human_approval_queue(self):
        response = self.client.get('/ai-agent-operations-console/')
        self.assertContains(response, 'Human Approval Queue')

    def test_page_mentions_evidence_trace(self):
        response = self.client.get('/ai-agent-operations-console/')
        self.assertContains(response, 'Evidence Trace')

    def test_page_mentions_cost_and_model_monitoring(self):
        response = self.client.get('/ai-agent-operations-console/')
        self.assertContains(response, 'Cost & Model Monitoring')

    def test_page_mentions_amanah_autopilot_morning_operations_briefing(self):
        response = self.client.get('/ai-agent-operations-console/')
        self.assertContains(response, 'Amanah Autopilot Morning Operations Briefing')

    def test_page_mentions_no_harm_gate_for_agents(self):
        response = self.client.get('/ai-agent-operations-console/')
        self.assertContains(response, 'No Harm Gate for Agents')

    def test_page_mentions_open_agent_console(self):
        response = self.client.get('/ai-agent-operations-console/')
        self.assertContains(response, 'Open Agent Console')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/ai-agent-operations-console/')
        for label in (
            'Open Agent Console', 'View Running Tasks', 'Review Failed Tasks',
            'Open Human Approval Queue', 'View Evidence Trace', 'Retry Failed Task',
            'Request Missing Evidence', 'Export Agent Logs', 'Send Approval to Teams',
            'Generate Morning Operations Briefing',
        ):
            self.assertContains(response, label)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/ai-agent-operations-console/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageAiAgentOperationsConsoleTeaserTests(TestCase):
    def test_platform_page_mentions_ai_agent_operations_console(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ AI Agent Operations Console')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
