from django.test import TestCase

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class AgentTrainingEvaluationLabPageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        self.assertContains(response, 'EcoIQ Agent Training & Evaluation Lab')

    def test_page_mentions_subtitle(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        self.assertContains(response, 'Train, test and improve EcoIQ AI agents')

    def test_page_mentions_are_all_14_agents_required(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        self.assertContains(response, 'Are all 14 agents required?')

    def test_page_mentions_mvp_agents(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        self.assertContains(response, 'MVP agents')

    def test_page_mentions_github_agents_vs_ecoiq_agents(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        self.assertContains(response, 'GitHub Agents vs EcoIQ Agents')

    def test_page_mentions_golden_test_cases(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        self.assertContains(response, 'Golden Test Cases')

    def test_page_mentions_agent_output_schemas(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        self.assertContains(response, 'Agent Output Schemas')

    def test_page_mentions_no_harm_gate_for_agent_training(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        self.assertContains(response, 'No Harm Gate for Agent Training')

    def test_page_mentions_open_agent_training_lab(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        self.assertContains(response, 'Open Agent Training Lab')

    def test_page_shows_cta_buttons(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        for label in (
            'Open Agent Training Lab', 'View MVP Agents', 'Create Golden Test Case',
            'Run Agent Evaluation', 'Review Failed Output', 'Open Prompt Library',
            'View Human Approval Rules', 'Train Document Reader Agent',
            'Train MRV Agent', 'Train Finance Agent',
        ):
            self.assertContains(response, label)

    def test_page_shows_all_14_agent_cards(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        for name in (
            'Research Agent', 'Document Reader Agent', 'Photo / Visual Evidence Agent',
            'Asset Passport Agent', 'Playbook Matching Agent', 'Finance Modelling Agent',
            'Supplier / Funding Match Agent', 'MRV Agent', 'Governance Agent',
            'Report Generator Agent', 'Customer Success Agent', 'Sales CRM Agent',
            'Analytics Agent', 'Amanah Autopilot Supervisor',
        ):
            self.assertContains(response, name)

    def test_page_has_no_claim_agents_are_fully_autonomous(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        content = response.content.decode()
        self.assertIn('does not claim all agents are fully autonomous production agents yet', content)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/agent-training-evaluation-lab/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class PlatformPageAgentTrainingEvaluationLabTeaserTests(TestCase):
    def test_platform_page_mentions_agent_training_evaluation_lab(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Agent Training & Evaluation Lab')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
