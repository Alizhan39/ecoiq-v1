from types import SimpleNamespace

from django.core.management import call_command
from django.test import TestCase

from ai_agent_council.models import (
    AgentHandoff, AgentTask, CouncilDecision, CouncilDisagreement, CouncilRun,
    CrossExaminationExchange, DecisionMemoryEntry,
)
from ai_agent_council.services.confidence import build_confidence_breakdown
from ai_agent_council.services.disagreement import classify_conflict
from ai_agent_council.services.maturity import compute_maturity
from ai_agent_council.services.reliability import compute_reliability
from ai_agent_council.services.routing import select_agents_for_task
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

    def test_page_mentions_twelve_operationally_trained_agents(self):
        response = self.client.get('/ai-agent-council/')
        self.assertContains(response, 'Twelve operationally trained agents')

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
            'Report Generator Agent', 'Amanah Autopilot Supervisor', 'Capital Allocation Agent',
        ):
            self.assertContains(response, name)
        # "&" is HTML-escaped by Django's template auto-escaping.
        self.assertContains(response, 'Waste &amp; Leakage Agent')

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
        self.assertContains(response, '12 trained operational agents working as one governed system')

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

    def test_exactly_twelve_operational_agent_folders(self):
        repo_state = _scan_ai_agents_repo_state()
        self.assertEqual(repo_state['operational_folder_count'], 12)

    def test_exactly_one_hundred_and_twenty_agent_training_files(self):
        repo_state = _scan_ai_agents_repo_state()
        self.assertEqual(repo_state['total_training_files'], 120)

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


class CouncilModelTests(TestCase):
    def test_council_run_str_and_defaults(self):
        run = CouncilRun.objects.create(
            slug='test-run', title='Test Run', question='Should we?', task_category='industrial_asset_modernisation',
        )
        self.assertEqual(str(run), 'Test Run')
        self.assertTrue(run.is_simulated)
        self.assertEqual(run.status, 'open')

    def test_agent_task_str(self):
        run = CouncilRun.objects.create(slug='r2', title='R2', question='Q', task_category='industrial_asset_modernisation')
        task = AgentTask.objects.create(run=run, agent_name='Research Agent', collaboration_mode='solo')
        self.assertIn('Research Agent', str(task))
        self.assertIn('R2', str(task))

    def test_council_decision_and_memory_entry_are_one_to_one(self):
        run = CouncilRun.objects.create(slug='r3', title='R3', question='Q', task_category='industrial_asset_modernisation')
        decision = CouncilDecision.objects.create(run=run, summary='Approved.')
        memory_entry = DecisionMemoryEntry.objects.create(
            decision=decision, original_decision_summary='Approved.', reason='Because.',
        )
        self.assertEqual(run.decision, decision)
        self.assertEqual(decision.memory_entry, memory_entry)
        with self.assertRaises(Exception):
            DecisionMemoryEntry.objects.create(decision=decision, original_decision_summary='dup', reason='dup')

    def test_council_disagreement_str(self):
        run = CouncilRun.objects.create(slug='r4', title='R4', question='Q', task_category='industrial_asset_modernisation')
        task_a = AgentTask.objects.create(run=run, agent_name='Finance Modelling Agent', collaboration_mode='council', order=1)
        task_b = AgentTask.objects.create(run=run, agent_name='Governance Agent', collaboration_mode='council', order=2)
        disagreement = CouncilDisagreement.objects.create(
            run=run, position_a=task_a, position_b=task_b,
            conflict_type='risk_tolerance', resolution_method='require_human_review',
        )
        self.assertIn('Finance Modelling Agent', str(disagreement))
        self.assertIn('Governance Agent', str(disagreement))


class ConfidenceServiceTests(TestCase):
    def test_worked_example_matches_spec_exactly(self):
        breakdown = build_confidence_breakdown(90, 86, 82, 9, 7, 3)
        self.assertEqual(breakdown['final'], 79)

    def test_confidence_clamped_to_100(self):
        breakdown = build_confidence_breakdown(100, 100, 100, 0, 0, 50)
        self.assertEqual(breakdown['final'], 100)

    def test_confidence_clamped_to_0(self):
        breakdown = build_confidence_breakdown(10, 10, 10, 50, 50, -50)
        self.assertEqual(breakdown['final'], 0)


class RoutingServiceTests(TestCase):
    def test_known_category_selects_expected_agents_and_explains_exclusions(self):
        results = select_agents_for_task('industrial_asset_modernisation')
        by_name = {r['agent_name']: r for r in results}
        self.assertTrue(by_name['Finance Modelling Agent']['selected'])
        self.assertFalse(by_name['Amanah Autopilot Supervisor']['selected'])
        for entry in results:
            self.assertTrue(entry['reason'])

    def test_unknown_category_selects_nobody(self):
        results = select_agents_for_task('not_a_real_category')
        self.assertTrue(all(not entry['selected'] for entry in results))


class DisagreementServiceTests(TestCase):
    def _task(self, **overrides):
        defaults = dict(agent_name='Agent A', evidence_refs=[], risk_flags=[], confidence=80)
        defaults.update(overrides)
        return SimpleNamespace(**defaults)

    def test_timing_conflict(self):
        a = self._task(risk_flags=['schedule'])
        b = self._task(agent_name='Agent B')
        self.assertEqual(classify_conflict(a, b), ('timing', 'resolve_automatically'))

    def test_disjoint_evidence_is_evidence_conflict(self):
        a = self._task(evidence_refs=['doc_1'])
        b = self._task(agent_name='Agent B', evidence_refs=['doc_2'])
        self.assertEqual(classify_conflict(a, b), ('evidence', 'request_more_evidence'))

    def test_differing_risk_flags_is_risk_tolerance(self):
        a = self._task(evidence_refs=['doc_1'], risk_flags=[])
        b = self._task(agent_name='Agent B', evidence_refs=['doc_1'], risk_flags=['procurement_gap'])
        self.assertEqual(classify_conflict(a, b), ('risk_tolerance', 'require_human_review'))

    def test_large_confidence_gap_on_shared_evidence_is_assumption(self):
        a = self._task(evidence_refs=['doc_1'], confidence=90)
        b = self._task(agent_name='Agent A', evidence_refs=['doc_1'], confidence=70)
        self.assertEqual(classify_conflict(a, b), ('assumption', 'ask_another_agent'))

    def test_shared_evidence_different_agents_similar_confidence_is_domain(self):
        a = self._task(agent_name='Finance Modelling Agent', evidence_refs=['doc_1'], confidence=85)
        b = self._task(agent_name='Governance Agent', evidence_refs=['doc_1'], confidence=87)
        self.assertEqual(classify_conflict(a, b), ('domain', 'preserve_minority_opinion'))


class MaturityServiceTests(TestCase):
    def test_operational_agent_never_reaches_stage_7(self):
        repo_state = _scan_ai_agents_repo_state()
        result = compute_maturity('Finance Modelling Agent', repo_state)
        self.assertLess(result['stage'], 7)
        self.assertEqual(result['gates'][7]['passed'], False)

    def test_next_stage_agent_blocked_early(self):
        repo_state = _scan_ai_agents_repo_state()
        result = compute_maturity('Supplier / Funding Match Agent', repo_state)
        self.assertEqual(result['stage'], 0)


class ReliabilityServiceTests(TestCase):
    def test_reliability_counts_match_seeded_fixtures(self):
        run = CouncilRun.objects.create(slug='rel-1', title='Rel', question='Q', task_category='industrial_asset_modernisation')
        AgentTask.objects.create(run=run, agent_name='Finance Modelling Agent', collaboration_mode='council', confidence=80, order=1)
        AgentTask.objects.create(run=run, agent_name='Finance Modelling Agent', collaboration_mode='council', confidence=90, order=2)
        result = compute_reliability('Finance Modelling Agent')
        self.assertEqual(result['agent_task_count'], 2)
        self.assertEqual(result['average_confidence'], 85.0)


class SeedDemoIdempotencyTests(TestCase):
    def test_seed_command_is_idempotent_and_covers_all_collaboration_modes(self):
        call_command('seed_council_demo_run')
        counts_after_first = {
            'runs': CouncilRun.objects.count(),
            'tasks': AgentTask.objects.count(),
            'handoffs': AgentHandoff.objects.count(),
            'disagreements': CouncilDisagreement.objects.count(),
            'exchanges': CrossExaminationExchange.objects.count(),
            'decisions': CouncilDecision.objects.count(),
        }

        call_command('seed_council_demo_run')
        counts_after_second = {
            'runs': CouncilRun.objects.count(),
            'tasks': AgentTask.objects.count(),
            'handoffs': AgentHandoff.objects.count(),
            'disagreements': CouncilDisagreement.objects.count(),
            'exchanges': CrossExaminationExchange.objects.count(),
            'decisions': CouncilDecision.objects.count(),
        }

        self.assertEqual(counts_after_first, counts_after_second)
        self.assertTrue(CouncilRun.objects.filter(slug='boiler-house-3-modernisation').exists())
        self.assertTrue(CouncilRun.objects.filter(slug='grid-capacity-evidence-review').exists())

        modes = set(AgentTask.objects.values_list('collaboration_mode', flat=True))
        self.assertEqual(modes, {'solo', 'parallel', 'handoff', 'council', 'escalation'})


class CouncilRuntimeRouteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_council_demo_run')

    def test_run_detail_returns_200_and_shows_key_content(self):
        response = self.client.get('/ai-agent-council/run/boiler-house-3-modernisation/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Boiler House #3 Modernisation', content)
        self.assertIn('Governance Agent', content)
        self.assertIn('Minority opinion retained', content)
        self.assertIn('Approved with Conditions', content)

    def test_run_detail_404_for_unseeded_slug(self):
        response = self.client.get('/ai-agent-council/run/does-not-exist/')
        self.assertEqual(response.status_code, 404)

    def test_training_page_returns_200_and_labels_heuristic(self):
        response = self.client.get('/ai-agent-council/training/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'heuristic')

    def test_reliability_page_returns_200_and_captions_simulated_data(self):
        response = self.client.get('/ai-agent-council/reliability/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'not production telemetry')

    def test_memory_page_returns_200_and_shows_reopened_decision(self):
        response = self.client.get('/ai-agent-council/memory/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Grid Capacity Evidence Review', content)
        self.assertIn('Reopened', content)

    def test_new_routes_have_no_raw_template_tags(self):
        for url in (
            '/ai-agent-council/run/boiler-house-3-modernisation/',
            '/ai-agent-council/training/',
            '/ai-agent-council/reliability/',
            '/ai-agent-council/memory/',
        ):
            response = self.client.get(url)
            content = response.content.decode()
            for token in RAW_TEMPLATE_TOKENS:
                self.assertNotIn(token, content, f'raw template token "{token}" leaked into {url}')

    def test_overview_page_shows_control_room_and_still_no_raw_tags(self):
        response = self.client.get('/ai-agent-council/')
        content = response.content.decode()
        self.assertIn('Council Control Room', content)
        self.assertIn('Boiler House #3 Modernisation', content)
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into overview page')
