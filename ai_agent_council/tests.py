from django.test import TestCase

from ai_agent_council.views import _scan_ai_agents_repo_state

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% intelligence_block', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class AiAgentCouncilPageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/ai-agent-council/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/ai-agent-council/')
        self.assertContains(response, 'EcoIQ AI Agent Council')

    def test_page_mentions_ten_operationally_trained_agents(self):
        response = self.client.get('/ai-agent-council/')
        self.assertContains(response, 'Ten operationally trained agents')

    def test_page_mentions_four_next_stage_agents(self):
        response = self.client.get('/ai-agent-council/')
        self.assertContains(response, 'Four next-stage agents')

    def test_page_mentions_real_agent_training_file_count(self):
        """
        The training-file count on the page is read live from the repository
        (see views._scan_ai_agents_repo_state) rather than hardcoded, so this
        test computes the real count the same way and checks the page
        reflects it — it stays correct even if the repo structure changes.
        """
        repo_state = _scan_ai_agents_repo_state()
        response = self.client.get('/ai-agent-council/')
        self.assertContains(response, f"{repo_state['total_training_files']} agent training files")

    def test_page_mentions_all_operational_agents(self):
        response = self.client.get('/ai-agent-council/')
        for name in (
            'Research Agent', 'Document Reader Agent', 'Photo / Visual Evidence Agent',
            'Asset Passport Agent', 'Industrial Playbook Matching Agent',
            'Finance Modelling Agent', 'MRV Agent', 'Governance Agent',
            'Report Generator Agent', 'Amanah Autopilot Supervisor',
        ):
            self.assertContains(response, name)

    def test_page_mentions_supplier_funding_match_agent_as_next_stage(self):
        response = self.client.get('/ai-agent-council/')
        content = response.content.decode()
        # "Supplier / Funding Match Agent" also appears as a plain handoff
        # mention on the Playbook Matching Agent's card, so search within the
        # Next-Stage Agents section specifically, not the first occurrence.
        section_start = content.find('id="next-stage-agents"')
        self.assertNotEqual(section_start, -1, 'Next-Stage Agents section not found')
        idx = content.find('Supplier / Funding Match Agent', section_start)
        self.assertNotEqual(idx, -1, 'Supplier / Funding Match Agent not found in Next-Stage Agents section')
        window = content[max(0, idx - 600):idx + 600]
        self.assertIn('Next Training Pack', window)

    def test_page_mentions_human_approval(self):
        response = self.client.get('/ai-agent-council/')
        self.assertContains(response, 'Human Approval')

    def test_page_mentions_agent_council_handoffs(self):
        response = self.client.get('/ai-agent-council/')
        self.assertContains(response, 'Agent Council Handoffs')

    def test_page_mentions_presentation_mode_headline(self):
        response = self.client.get('/ai-agent-council/')
        self.assertContains(response, '10 trained operational agents working as one governed system')

    def test_page_has_no_claim_all_14_have_full_training_packs(self):
        response = self.client.get('/ai-agent-council/')
        content = response.content.decode()
        self.assertNotIn('all 14 agents have full training packs', content)
        self.assertNotIn('fourteen operationally trained agents', content.lower())

    def test_page_has_no_claim_agents_are_fully_autonomous(self):
        response = self.client.get('/ai-agent-council/')
        self.assertContains(response, 'not fully autonomous decision-makers')

    def test_page_has_no_unsupported_microsoft_certification_claim(self):
        response = self.client.get('/ai-agent-council/')
        content = response.content.decode()
        idx = content.find('Microsoft certified')
        while idx != -1:
            context = content[max(0, idx - 60):idx + 40]
            self.assertIn('not', context, 'unsupported "Microsoft certified" claim found without a negation nearby')
            idx = content.find('Microsoft certified', idx + 1)
        self.assertNotIn('official Microsoft partner', content)

    def test_page_has_no_unsupported_fatwa_or_shariah_claim(self):
        response = self.client.get('/ai-agent-council/')
        content = response.content.decode()
        self.assertNotIn('is a fatwa', content)
        self.assertNotIn('Shariah certified', content)
        self.assertNotIn('Shariah certification', content)

    def test_page_has_no_raw_template_tags(self):
        response = self.client.get('/ai-agent-council/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class AiAgentCouncilRepoValidationTests(TestCase):
    """Validates the live repository state the Council page reads from."""

    def test_exactly_ten_operational_agent_folders(self):
        repo_state = _scan_ai_agents_repo_state()
        self.assertEqual(repo_state['operational_folder_count'], 10)

    def test_exactly_one_hundred_agent_training_files(self):
        repo_state = _scan_ai_agents_repo_state()
        self.assertEqual(repo_state['total_training_files'], 100)

    def test_master_index_exists(self):
        repo_state = _scan_ai_agents_repo_state()
        self.assertTrue(repo_state['master_index_exists'])


class PlatformPageAiAgentCouncilTeaserTests(TestCase):
    def test_platform_page_mentions_ai_agent_council(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ AI Agent Council')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')
