from django.test import TestCase, override_settings

from agent_runtime_model_router.models import AgentRegistryEntry
from agent_runtime_model_router.services.registry import discover_agents, sync_registry
from agent_runtime_model_router.services.training_pack_loader import (
    load_training_pack, validate_training_pack,
)
from agent_runtime_model_router.services.model_adapters import (
    AnthropicCompatibleAdapter, AzureOpenAICompatibleAdapter, DeterministicTestAdapter,
    GeminiCompatibleAdapter, OpenAICompatibleAdapter, SimulatedDemoAdapter,
)
from agent_runtime_model_router.services.model_router import select_model_route
from agent_runtime_model_router.services.safety_assertions import (
    aggregate_safety_status, run_safety_assertions,
)
from agent_runtime_model_router.services.schema_validation import validate_agent_output
from agent_runtime_model_router.services.confidence_calibration import calibrate_confidence
from agent_runtime_model_router.services.cost_policy import (
    HIGH_REASONING_APPROVAL_THRESHOLD_USD, MAX_ESTIMATED_COST_PER_RUN_USD, check_cost_policy,
)
from agent_runtime_model_router.services.human_approval_gate import (
    ACTIONS_REQUIRING_APPROVAL, HumanApprovalRequiredError, require_human_approval,
)
from agent_runtime_model_router.models import AgentRun
from agent_runtime_model_router.services.execution import (
    check_no_evidence_upgrade, create_agent_run, execute_agent, submit_agent_position_to_council,
)
from ai_agent_council.models import (
    AgentTask, CouncilDecision, CouncilDisagreement, CouncilRun, CrossExaminationExchange,
    DecisionMemoryEntry,
)
from django.core.management import call_command
from agent_runtime_model_router.services.demo_pipeline import DEMO_RUN_SLUG

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class RegistryDiscoveryTests(TestCase):
    def test_discovers_twelve_operational_and_four_next_stage(self):
        discovered = discover_agents()
        operational = [d for d in discovered if not d['is_next_stage']]
        next_stage = [d for d in discovered if d['is_next_stage']]
        self.assertEqual(len(operational), 12)
        self.assertEqual(len(next_stage), 4)

    def test_operational_agents_have_real_content_hash(self):
        discovered = discover_agents()
        for d in discovered:
            if not d['is_next_stage']:
                self.assertEqual(len(d['content_hash']), 64, d['agent_name'])

    def test_next_stage_agents_have_no_content_hash_or_path(self):
        discovered = discover_agents()
        for d in discovered:
            if d['is_next_stage']:
                self.assertEqual(d['content_hash'], '')
                self.assertEqual(d['training_pack_path'], '')


class RegistrySyncTests(TestCase):
    def test_sync_creates_sixteen_entries(self):
        sync_registry()
        self.assertEqual(AgentRegistryEntry.objects.count(), 16)

    def test_sync_is_idempotent(self):
        sync_registry()
        first_count = AgentRegistryEntry.objects.count()
        sync_registry()
        self.assertEqual(AgentRegistryEntry.objects.count(), first_count)

    def test_next_stage_agents_never_marked_enabled(self):
        sync_registry()
        for entry in AgentRegistryEntry.objects.filter(is_next_stage=True):
            self.assertFalse(entry.enabled, f'{entry.agent_name} must not be enabled')

    def test_operational_agents_are_enabled(self):
        sync_registry()
        for entry in AgentRegistryEntry.objects.filter(is_next_stage=False):
            self.assertTrue(entry.enabled, f'{entry.agent_name} should be enabled')

    def test_last_evaluation_score_stays_null(self):
        sync_registry()
        for entry in AgentRegistryEntry.objects.all():
            self.assertIsNone(entry.last_evaluation_score)


class TrainingPackLoaderTests(TestCase):
    def test_loads_all_ten_files_for_operational_agent(self):
        pack = load_training_pack('Finance Modelling Agent')
        self.assertEqual(len(pack['files']), 10)

    def test_parses_test_cases_json(self):
        pack = load_training_pack('Finance Modelling Agent')
        self.assertEqual(pack['test_cases_error'], '')
        self.assertIn('realistic_test_cases', pack['test_cases'])
        self.assertIn('failure_cases', pack['test_cases'])

    def test_next_stage_agent_has_no_files(self):
        pack = load_training_pack('Supplier / Funding Match Agent')
        self.assertEqual(pack['files'], {})
        self.assertIsNone(pack['test_cases'])

    def test_validate_operational_agent_is_valid(self):
        result = validate_training_pack('Finance Modelling Agent')
        self.assertTrue(result['valid'])
        self.assertEqual(result['missing_files'], [])
        self.assertTrue(result['agent_identity_consistent'])

    def test_validate_next_stage_agent_is_invalid(self):
        result = validate_training_pack('Supplier / Funding Match Agent')
        self.assertFalse(result['valid'])
        self.assertEqual(len(result['missing_files']), 10)

    def test_validate_all_operational_agents(self):
        from ai_agent_council.agents import OPERATIONAL_AGENT_NAMES
        for name in OPERATIONAL_AGENT_NAMES:
            result = validate_training_pack(name)
            self.assertTrue(result['valid'], f'{name} should have a fully valid training pack')


class ModelAdapterTests(TestCase):
    """
    This dev environment has a real ANTHROPIC_API_KEY configured for other
    features (core/ai.py etc.) — every live-adapter test below forces the
    relevant credential to '' via override_settings so this suite NEVER
    makes a real network call, regardless of ambient .env state.
    """

    @override_settings(ANTHROPIC_API_KEY='')
    def test_anthropic_adapter_fails_safely_without_credentials(self):
        result = AnthropicCompatibleAdapter().run({'prompt_text': 'hi'})
        self.assertEqual(result.status, 'failed')
        self.assertEqual(result.failure_reason, 'missing_credentials')

    @override_settings(OPENAI_API_KEY='')
    def test_openai_adapter_fails_safely_without_credentials(self):
        result = OpenAICompatibleAdapter().run({'prompt_text': 'hi'})
        self.assertEqual(result.status, 'failed')
        self.assertEqual(result.failure_reason, 'missing_credentials')

    @override_settings(GEMINI_API_KEY='')
    def test_gemini_adapter_fails_safely_without_credentials(self):
        result = GeminiCompatibleAdapter().run({'prompt_text': 'hi'})
        self.assertEqual(result.status, 'failed')
        self.assertEqual(result.failure_reason, 'missing_credentials')

    @override_settings(AZURE_OPENAI_API_KEY='', AZURE_OPENAI_ENDPOINT='')
    def test_azure_openai_adapter_fails_safely_without_credentials(self):
        result = AzureOpenAICompatibleAdapter().run({'prompt_text': 'hi'})
        self.assertEqual(result.status, 'failed')
        self.assertEqual(result.failure_reason, 'missing_credentials')

    def test_deterministic_adapter_replays_golden_case(self):
        pack = load_training_pack('Finance Modelling Agent')
        result = DeterministicTestAdapter().run({'test_cases': pack['test_cases']})
        self.assertEqual(result.status, 'success')
        self.assertEqual(result.model_provider, 'deterministic')
        self.assertEqual(
            result.output,
            pack['test_cases']['realistic_test_cases'][0]['expected_output'],
        )

    def test_deterministic_adapter_fails_safely_with_no_test_cases(self):
        result = DeterministicTestAdapter().run({'test_cases': {}})
        self.assertEqual(result.status, 'failed')
        self.assertEqual(result.failure_reason, 'empty_response')

    def test_simulated_adapter_returns_provided_fixture(self):
        fixture = {'position_summary': 'Financially attractive', 'confidence': 82}
        result = SimulatedDemoAdapter().run({'fixture_output': fixture})
        self.assertEqual(result.status, 'success')
        self.assertEqual(result.output, fixture)

    def test_simulated_adapter_never_invents_output_without_a_fixture(self):
        result = SimulatedDemoAdapter().run({})
        self.assertEqual(result.status, 'failed')
        self.assertEqual(result.failure_reason, 'empty_response')


class ModelRouterTests(TestCase):
    def test_deterministic_test_mode_always_routes_to_deterministic_adapter(self):
        route = select_model_route('Research Agent', 'sector_research', 'deterministic_test',
                                    sensitivity_level='high', requires_vision=True)
        self.assertEqual(route['selected_provider'], 'deterministic')
        self.assertEqual(route['rejected_alternatives'], [])

    def test_simulated_demo_mode_always_routes_to_simulated_adapter(self):
        route = select_model_route('Research Agent', 'sector_research', 'simulated_demo')
        self.assertEqual(route['selected_provider'], 'simulated')

    def test_finance_agent_routes_to_reasoning_capable_route(self):
        route = select_model_route(
            'Finance Modelling Agent', 'capex_opex_modelling', 'live',
            sensitivity_level='medium', requires_reasoning=True,
        )
        self.assertEqual(route['selected_provider'], 'anthropic')
        self.assertIn('reasoning', route['reason'])

    def test_photo_visual_agent_routes_to_vision_capable_route(self):
        route = select_model_route(
            'Photo / Visual Evidence Agent', 'site_photo_review', 'live', requires_vision=True,
        )
        self.assertEqual(route['selected_provider'], 'gemini')
        self.assertIn('vision', route['reason'])

    def test_sensitive_industrial_data_routes_to_enterprise_route(self):
        route = select_model_route(
            'Governance Agent', 'review_routing', 'live', sensitivity_level='high',
        )
        self.assertEqual(route['selected_provider'], 'azure_openai')
        self.assertIn('enterprise', route['reason'])

    def test_rejected_alternatives_cover_every_other_live_provider(self):
        route = select_model_route(
            'Finance Modelling Agent', 'capex_opex_modelling', 'live', requires_reasoning=True,
        )
        rejected_providers = {r['provider'] for r in route['rejected_alternatives']}
        self.assertEqual(rejected_providers, {'openai', 'gemini', 'azure_openai'})
        for r in route['rejected_alternatives']:
            self.assertTrue(r['reason_rejected'])

    def test_default_live_route_has_no_special_requirement(self):
        route = select_model_route('Report Generator Agent', 'board_pack', 'live')
        self.assertEqual(route['selected_provider'], 'openai')


def _has_pattern(findings, pattern_id):
    return any(f['pattern_id'] == pattern_id for f in findings)


class SafetyAssertionEngineTests(TestCase):
    def test_clean_output_has_no_findings(self):
        findings = run_safety_assertions(
            {
                'output_summary': 'Draft CAPEX/OPEX model with assumptions listed.',
                'evidence_used': ['fuel_bills_2024'], 'missing_data': [], 'risk_flags': [],
                'human_approval_required': True,
            },
            'Finance Modelling Agent',
        )
        self.assertEqual(findings, [])
        self.assertEqual(aggregate_safety_status(findings), 'pass')

    def test_invented_missing_data_blocked(self):
        findings = run_safety_assertions(
            {'output_summary': 'We are assuming typical values since exact data was not on file.', 'missing_data': []},
            'Finance Modelling Agent',
        )
        self.assertTrue(_has_pattern(findings, 'invented_missing_data'))

    def test_estimated_as_verified_blocked(self):
        findings = run_safety_assertions(
            {'output_summary': 'Impact savings are verified for this period.', 'evidence_used': []},
            'MRV Agent',
        )
        self.assertTrue(_has_pattern(findings, 'estimated_as_verified'))

    def test_guaranteed_savings_blocked(self):
        findings = run_safety_assertions(
            {'output_summary': 'This upgrade will deliver a guaranteed 20% savings on energy costs.'},
            'Finance Modelling Agent',
        )
        self.assertTrue(_has_pattern(findings, 'guaranteed_savings'))

    def test_funding_secured_without_evidence_blocked(self):
        findings = run_safety_assertions(
            {'output_summary': 'The project funding is secured for construction.', 'evidence_used': []},
            'Finance Modelling Agent',
        )
        self.assertTrue(_has_pattern(findings, 'funding_secured_without_evidence'))

    def test_supplier_endorsement_from_quote_only_needs_review(self):
        findings = run_safety_assertions(
            {'output_summary': 'We recommend this supplier based on their quote.', 'evidence_used': ['supplier_quote_boiler3']},
            'Industrial Playbook Matching Agent',
        )
        self.assertTrue(_has_pattern(findings, 'supplier_endorsement_from_quote_only'))

    def test_mrv_verified_without_evidence_blocked(self):
        findings = run_safety_assertions(
            {'output_summary': 'This project has achieved MRV Verified status.', 'missing_data': ['baseline_survey']},
            'MRV Agent',
        )
        self.assertTrue(_has_pattern(findings, 'mrv_verified_without_evidence'))

    def test_visual_hypothesis_as_fact_needs_review(self):
        findings = run_safety_assertions(
            {'output_summary': 'The insulation gap is confirmed.', 'risk_flags': []},
            'Photo / Visual Evidence Agent',
        )
        self.assertTrue(_has_pattern(findings, 'visual_hypothesis_as_fact'))

    def test_external_action_without_permission_blocked(self):
        findings = run_safety_assertions(
            {'next_action': 'send email to supplier with quote request', 'human_approval_required': False},
            'Report Generator Agent',
        )
        self.assertTrue(_has_pattern(findings, 'external_action_without_permission'))

    def test_public_impact_claim_without_approval_blocked(self):
        findings = run_safety_assertions(
            {'output_summary': 'This public impact figure will be shared externally.', 'human_approval_required': False},
            'Report Generator Agent',
        )
        self.assertTrue(_has_pattern(findings, 'public_impact_claim_without_approval'))

    def test_unsupported_microsoft_claim_blocked(self):
        findings = run_safety_assertions(
            {'output_summary': 'EcoIQ is Microsoft certified for this integration.'},
            'Report Generator Agent',
        )
        self.assertTrue(_has_pattern(findings, 'unsupported_microsoft_claim'))

    def test_negated_microsoft_claim_not_blocked(self):
        findings = run_safety_assertions(
            {'output_summary': 'This integration is not Microsoft certified or Microsoft partner.'},
            'Report Generator Agent',
        )
        self.assertFalse(_has_pattern(findings, 'unsupported_microsoft_claim'))

    def test_unsupported_shariah_fatwa_claim_blocked(self):
        findings = run_safety_assertions(
            {'output_summary': 'This structure is Shariah-compliant and approved.'},
            'Finance Modelling Agent',
        )
        self.assertTrue(_has_pattern(findings, 'unsupported_shariah_fatwa_claim'))

    def test_negated_shariah_claim_not_blocked(self):
        findings = run_safety_assertions(
            {'output_summary': 'This is not Shariah-compliant advice; a qualified reviewer must confirm.'},
            'Finance Modelling Agent',
        )
        self.assertFalse(_has_pattern(findings, 'unsupported_shariah_fatwa_claim'))

    def test_aggregate_status_picks_worst_severity(self):
        findings = [{'pattern_id': 'a', 'severity': 'warning'}, {'pattern_id': 'b', 'severity': 'blocking'}]
        self.assertEqual(aggregate_safety_status(findings), 'blocking')


class SchemaValidationTests(TestCase):
    def test_valid_minimal_output_passes(self):
        valid, errors = validate_agent_output({
            'confidence': 82, 'human_approval_required': True, 'status': 'completed',
            'risk_flags': [], 'evidence_used': ['fuel_bills_2024'], 'missing_data': [],
        })
        self.assertTrue(valid)
        self.assertEqual(errors, [])

    def test_missing_required_field_is_invalid(self):
        valid, errors = validate_agent_output({'human_approval_required': True, 'status': 'completed'})
        self.assertFalse(valid)
        self.assertTrue(any('confidence' in e for e in errors))

    def test_confidence_out_of_range_is_invalid(self):
        valid, errors = validate_agent_output({
            'confidence': 150, 'human_approval_required': True, 'status': 'completed',
        })
        self.assertFalse(valid)

    def test_confidence_wrong_type_is_invalid(self):
        valid, errors = validate_agent_output({
            'confidence': 'high', 'human_approval_required': True, 'status': 'completed',
        })
        self.assertFalse(valid)

    def test_wrong_type_for_list_field_is_invalid(self):
        valid, errors = validate_agent_output({
            'confidence': 80, 'human_approval_required': True, 'status': 'completed',
            'risk_flags': 'none',
        })
        self.assertFalse(valid)

    def test_invalid_status_enum_is_invalid(self):
        valid, errors = validate_agent_output({
            'confidence': 80, 'human_approval_required': True, 'status': 'made_up_status',
        })
        self.assertFalse(valid)

    def test_partial_real_golden_case_fails_validation_honestly(self):
        # A real ai_agents/finance_modelling_agent/test_cases.json expected_output
        # shape — deliberately partial, proving the validator is a real gate.
        valid, errors = validate_agent_output({
            'payback_estimate_labelled_estimated': True, 'human_approval_required': True,
        })
        self.assertFalse(valid)


class ConfidenceCalibrationTests(TestCase):
    def test_worked_example_clean_strong_case(self):
        breakdown = calibrate_confidence(
            evidence_quality_score=90, num_supporting_sources=2, missing_data=['x'],
            schema_valid=True, unresolved_disagreements=1, contradiction_severity='low',
            maturity_stage=6, reviewer_status='human_reviewed', safety_findings=[{'severity': 'warning'}],
        )
        self.assertEqual(breakdown['final'], 90)

    def test_worked_example_finance_case_diverges_from_raw_confidence(self):
        breakdown = calibrate_confidence(
            evidence_quality_score=70, num_supporting_sources=1, missing_data=[],
            schema_valid=True, unresolved_disagreements=2, contradiction_severity='medium',
            maturity_stage=6, reviewer_status='pending', safety_findings=[{'severity': 'needs_review'}],
        )
        self.assertEqual(breakdown['final'], 58)

    def test_worked_example_degenerate_case_floors_at_zero(self):
        breakdown = calibrate_confidence(
            evidence_quality_score=10, num_supporting_sources=0, missing_data=['a', 'b', 'c'],
            schema_valid=False, unresolved_disagreements=3, contradiction_severity='high',
            maturity_stage=1, reviewer_status='rejected', safety_findings=[{'severity': 'blocking'}],
        )
        self.assertEqual(breakdown['final'], 0)

    def test_returns_canonical_breakdown_shape(self):
        breakdown = calibrate_confidence(
            evidence_quality_score=80, num_supporting_sources=1, missing_data=[],
            schema_valid=True, unresolved_disagreements=0, contradiction_severity='none',
            maturity_stage=6, reviewer_status='human_reviewed', safety_findings=[],
        )
        for key in (
            'evidence_coverage', 'source_quality', 'consistency', 'missing_data_penalty',
            'contradiction_penalty', 'historical_reliability_adjustment', 'final', 'explanation',
        ):
            self.assertIn(key, breakdown)


class CostPolicyTests(TestCase):
    def test_no_estimate_is_allowed(self):
        result = check_cost_policy(None, council_case=None)
        self.assertTrue(result['allowed'])
        self.assertFalse(result['requires_human_approval'])

    def test_within_policy_is_allowed(self):
        result = check_cost_policy(0.05, council_case=None)
        self.assertTrue(result['allowed'])
        self.assertFalse(result['requires_human_approval'])
        self.assertFalse(result['budget_exceeded'])

    def test_exceeds_per_run_limit_is_blocked(self):
        result = check_cost_policy(MAX_ESTIMATED_COST_PER_RUN_USD + 1, council_case=None)
        self.assertFalse(result['allowed'])
        self.assertTrue(result['budget_exceeded'])
        self.assertTrue(result['requires_human_approval'])

    def test_high_reasoning_above_threshold_requires_approval_but_is_allowed(self):
        result = check_cost_policy(
            HIGH_REASONING_APPROVAL_THRESHOLD_USD + 0.10, council_case=None, cost_class='high_reasoning',
        )
        self.assertTrue(result['allowed'])
        self.assertTrue(result['requires_human_approval'])
        self.assertFalse(result['budget_exceeded'])


class HumanApprovalGateTests(TestCase):
    """
    One blocked + one allowed test per one of the 8 actions in
    ACTIONS_REQUIRING_APPROVAL (16 tests total) — proves the gate is
    enforced in the service layer, not just displayed as UI text.
    """

    def setUp(self):
        self.registry_entry = AgentRegistryEntry.objects.create(
            agent_id='test-agent', agent_name='Test Agent',
        )
        self.unapproved_run = AgentRun.objects.create(
            agent=self.registry_entry, task_type='demo', execution_mode_requested='simulated_demo',
            human_approved=None,
        )
        self.approved_run = AgentRun.objects.create(
            agent=self.registry_entry, task_type='demo', execution_mode_requested='simulated_demo',
            human_approved=True,
        )
        self.rejected_run = AgentRun.objects.create(
            agent=self.registry_entry, task_type='demo', execution_mode_requested='simulated_demo',
            human_approved=False,
        )

    def test_all_eight_actions_are_registered(self):
        self.assertEqual(len(ACTIONS_REQUIRING_APPROVAL), 8)

    def test_unrecognised_action_is_not_gated(self):
        self.assertTrue(require_human_approval('not_a_real_action', self.unapproved_run))

    def test_explicitly_rejected_run_is_also_blocked(self):
        with self.assertRaises(HumanApprovalRequiredError):
            require_human_approval('supplier_outreach', self.rejected_run)


def _make_gate_test(action_type, expect_blocked):
    if expect_blocked:
        def test(self):
            with self.assertRaises(HumanApprovalRequiredError):
                require_human_approval(action_type, self.unapproved_run)
        return test

    def test(self):
        self.assertTrue(require_human_approval(action_type, self.approved_run))
    return test


for _action in ACTIONS_REQUIRING_APPROVAL:
    setattr(
        HumanApprovalGateTests, f'test_{_action}_blocked_without_approval',
        _make_gate_test(_action, expect_blocked=True),
    )
    setattr(
        HumanApprovalGateTests, f'test_{_action}_allowed_with_approval',
        _make_gate_test(_action, expect_blocked=False),
    )


COMPLETE_FIXTURE = {
    'confidence': 82, 'human_approval_required': True, 'status': 'completed',
    'risk_flags': [], 'evidence_used': ['fuel_bills_2024'], 'missing_data': [],
    'output_summary': 'Financially attractive: estimated payback of 3.2 years.',
}

NO_CREDENTIALS = dict(
    ANTHROPIC_API_KEY='', OPENAI_API_KEY='', GEMINI_API_KEY='',
    AZURE_OPENAI_API_KEY='', AZURE_OPENAI_ENDPOINT='',
)


class ExecutionServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sync_registry()

    def setUp(self):
        self.council_run = CouncilRun.objects.create(
            slug='execution-test-run', title='Execution Test', question='?',
            task_category='industrial_asset_modernisation',
        )

    def test_deterministic_run_replays_golden_case_honestly(self):
        run = create_agent_run(
            'Finance Modelling Agent', 'capex_opex_modelling', council_case=self.council_run,
            execution_mode='deterministic_test', input_summary='test',
        )
        run = execute_agent(run)
        self.assertEqual(run.execution_mode_used, 'deterministic_test')
        self.assertEqual(run.model_provider, 'deterministic')

    def test_simulated_run_with_complete_fixture_succeeds(self):
        run = create_agent_run(
            'Finance Modelling Agent', 'capex_opex_modelling', council_case=self.council_run,
            execution_mode='simulated_demo', input_summary='test',
        )
        run = execute_agent(run, fixture_output=COMPLETE_FIXTURE, evidence_quality_score=85)
        self.assertEqual(run.status, 'completed')
        self.assertTrue(run.schema_valid)
        self.assertEqual(run.safety_status, 'pass')
        self.assertIsNotNone(run.calibrated_confidence)

    def test_complete_run_can_be_submitted_to_council(self):
        run = create_agent_run(
            'Finance Modelling Agent', 'capex_opex_modelling', council_case=self.council_run,
            execution_mode='simulated_demo', input_summary='test',
        )
        run = execute_agent(run, fixture_output=COMPLETE_FIXTURE, evidence_quality_score=85)
        task = submit_agent_position_to_council(run)
        self.assertEqual(task.agent_name, 'Finance Modelling Agent')
        run.refresh_from_db()
        self.assertEqual(run.council_position_id, task.id)

    def test_safety_blocking_output_cannot_be_submitted(self):
        run = create_agent_run(
            'Finance Modelling Agent', 'capex_opex_modelling', council_case=self.council_run,
            execution_mode='simulated_demo', input_summary='test',
        )
        unsafe_fixture = dict(COMPLETE_FIXTURE, output_summary='This will deliver a guaranteed 20% savings.')
        run = execute_agent(run, fixture_output=unsafe_fixture)
        self.assertEqual(run.safety_status, 'blocking')
        self.assertEqual(run.status, 'blocked')
        with self.assertRaises(ValueError):
            submit_agent_position_to_council(run)

    def test_invalid_schema_output_cannot_be_submitted(self):
        run = create_agent_run(
            'Finance Modelling Agent', 'capex_opex_modelling', council_case=self.council_run,
            execution_mode='deterministic_test', input_summary='test',
        )
        run = execute_agent(run)
        self.assertFalse(run.schema_valid)
        with self.assertRaises(ValueError):
            submit_agent_position_to_council(run)

    def test_idempotency_returns_existing_completed_run(self):
        run1 = create_agent_run(
            'Finance Modelling Agent', 'capex_opex_modelling', council_case=self.council_run,
            execution_mode='simulated_demo', input_summary='same input',
        )
        run1 = execute_agent(run1, fixture_output=COMPLETE_FIXTURE)
        run2 = create_agent_run(
            'Finance Modelling Agent', 'capex_opex_modelling', council_case=self.council_run,
            execution_mode='simulated_demo', input_summary='same input',
        )
        self.assertEqual(run1.pk, run2.pk)

    def test_explicit_rerun_creates_new_linked_run(self):
        run1 = create_agent_run(
            'Finance Modelling Agent', 'capex_opex_modelling', council_case=self.council_run,
            execution_mode='simulated_demo', input_summary='same input',
        )
        run1 = execute_agent(run1, fixture_output=COMPLETE_FIXTURE)
        run2 = create_agent_run(
            'Finance Modelling Agent', 'capex_opex_modelling', council_case=self.council_run,
            execution_mode='simulated_demo', input_summary='same input', rerun_reason='new evidence',
        )
        self.assertNotEqual(run1.pk, run2.pk)
        self.assertEqual(run2.rerun_of_id, run1.pk)
        self.assertEqual(run2.rerun_reason, 'new evidence')

    @override_settings(**NO_CREDENTIALS)
    def test_live_failure_never_becomes_simulated(self):
        run = create_agent_run(
            'Finance Modelling Agent', 'capex_opex_modelling', council_case=self.council_run,
            execution_mode='live', input_summary='test',
        )
        run = execute_agent(run, requires_reasoning=True)
        self.assertEqual(run.execution_mode_requested, 'live')
        self.assertNotEqual(run.execution_mode_used, 'simulated_demo')
        self.assertEqual(run.execution_mode_used, 'live')
        self.assertEqual(run.status, 'needs_human_review')
        self.assertTrue(run.human_approval_required)
        self.assertTrue(len(run.fallback_chain) >= 2)

    @override_settings(**NO_CREDENTIALS)
    def test_deterministic_fallback_only_when_explicitly_allowed(self):
        run_not_allowed = create_agent_run(
            'Finance Modelling Agent', 'capex_opex_modelling', council_case=self.council_run,
            execution_mode='live', input_summary='a',
        )
        run_not_allowed = execute_agent(run_not_allowed, requires_reasoning=True, allow_deterministic_fallback=False)
        self.assertEqual(run_not_allowed.execution_mode_used, 'live')
        self.assertEqual(run_not_allowed.status, 'needs_human_review')

        run_allowed = create_agent_run(
            'Finance Modelling Agent', 'capex_opex_modelling', council_case=self.council_run,
            execution_mode='live', input_summary='b',
        )
        run_allowed = execute_agent(run_allowed, requires_reasoning=True, allow_deterministic_fallback=True)
        self.assertEqual(run_allowed.execution_mode_used, 'deterministic_test')
        self.assertTrue(run_allowed.fallback_reason)

    def test_evidence_upgrade_from_estimated_to_verified_is_blocked(self):
        prior = {'evidence_id': 'baseline_1', 'source_document': 'doc.pdf', 'source_ref': 'p1', 'quality': 'estimated'}
        new = {'evidence_id': 'baseline_1', 'source_document': 'doc.pdf', 'source_ref': 'p1', 'quality': 'verified'}
        violations = check_no_evidence_upgrade([new], {'baseline_1': prior})
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]['pattern_id'], 'evidence_upgrade_violation')

    def test_evidence_upgrade_with_new_source_is_allowed(self):
        prior = {'evidence_id': 'baseline_1', 'source_document': 'doc.pdf', 'source_ref': 'p1', 'quality': 'estimated'}
        new = {'evidence_id': 'baseline_1', 'source_document': 'new_survey.pdf', 'source_ref': 'p3', 'quality': 'verified'}
        violations = check_no_evidence_upgrade([new], {'baseline_1': prior})
        self.assertEqual(violations, [])

    def test_gated_action_requires_approval_before_council_submission(self):
        run = create_agent_run(
            'Finance Modelling Agent', 'capex_opex_modelling', council_case=self.council_run,
            execution_mode='simulated_demo', input_summary='test',
        )
        run = execute_agent(run, fixture_output=COMPLETE_FIXTURE)
        self.assertIsNone(run.human_approved)
        with self.assertRaises(HumanApprovalRequiredError):
            submit_agent_position_to_council(run, action_type='investor_memo_delivery')


class DemoPipelineIdempotencyTests(TestCase):
    def test_seed_command_is_idempotent(self):
        call_command('seed_agent_runtime_demo')
        council_run = CouncilRun.objects.get(slug=DEMO_RUN_SLUG)
        counts_first = {
            'agent_runs': AgentRun.objects.filter(council_case=council_run).count(),
            'agent_tasks': AgentTask.objects.filter(run=council_run).count(),
            'disagreements': CouncilDisagreement.objects.filter(run=council_run).count(),
            'exchanges': CrossExaminationExchange.objects.filter(run=council_run).count(),
        }

        call_command('seed_agent_runtime_demo')
        counts_second = {
            'agent_runs': AgentRun.objects.filter(council_case=council_run).count(),
            'agent_tasks': AgentTask.objects.filter(run=council_run).count(),
            'disagreements': CouncilDisagreement.objects.filter(run=council_run).count(),
            'exchanges': CrossExaminationExchange.objects.filter(run=council_run).count(),
        }

        self.assertEqual(counts_first, counts_second)
        self.assertEqual(counts_first['agent_runs'], 8)
        self.assertEqual(counts_first['agent_tasks'], 8)
        self.assertEqual(counts_first['disagreements'], 2)

    def test_demo_shows_differing_confidence_values_and_execution_mode(self):
        call_command('seed_agent_runtime_demo')
        runs = AgentRun.objects.filter(council_case__slug=DEMO_RUN_SLUG)
        confidences = {r.calibrated_confidence for r in runs}
        self.assertGreater(len(confidences), 1, 'Demo should show differing confidence values across agents')
        for run in runs:
            self.assertEqual(run.execution_mode_requested, 'simulated_demo')
            self.assertEqual(run.execution_mode_used, 'simulated_demo')

    def test_demo_produces_approved_with_conditions_decision(self):
        call_command('seed_agent_runtime_demo')
        decision = CouncilDecision.objects.get(run__slug=DEMO_RUN_SLUG)
        self.assertEqual(decision.status, 'approved_with_conditions')
        self.assertEqual(decision.minority_agents, ['Governance Agent'])
        self.assertEqual(len(decision.conditions), 4)
        self.assertTrue(decision.human_approval_required)

    def test_demo_preserves_minority_disagreement(self):
        call_command('seed_agent_runtime_demo')
        disagreements = CouncilDisagreement.objects.filter(run__slug=DEMO_RUN_SLUG)
        self.assertEqual(disagreements.count(), 2)
        for d in disagreements:
            self.assertTrue(d.minority_opinion_retained)


REQUIRED_TEXT = [
    'EcoIQ Agent Runtime & Model Router', 'From trained agent to governed decision',
    'Model Router', 'Structured Output Validation', 'Safety Assertion Engine',
    'Execution Mode', 'Human Approval', 'Why this decision happened',
]


class RuntimeRouteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_agent_runtime_demo')

    def test_overview_returns_200(self):
        response = self.client.get('/agent-runtime-model-router/')
        self.assertEqual(response.status_code, 200)

    def test_case_trace_returns_200_and_shows_why_panel(self):
        response = self.client.get(f'/agent-runtime-model-router/case/{DEMO_RUN_SLUG}/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Why this decision happened', content)
        self.assertIn('Governance Agent', content)
        self.assertIn('minority opinion retained', content.lower() + content)

    def test_case_trace_404_for_unseeded_slug(self):
        response = self.client.get('/agent-runtime-model-router/case/does-not-exist/')
        self.assertEqual(response.status_code, 404)

    def test_run_detail_returns_200(self):
        run = AgentRun.objects.filter(council_case__slug=DEMO_RUN_SLUG).first()
        response = self.client.get(f'/agent-runtime-model-router/run/{run.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, run.agent.agent_name)

    def test_run_detail_404_for_unknown_id(self):
        response = self.client.get('/agent-runtime-model-router/run/999999/')
        self.assertEqual(response.status_code, 404)

    def test_required_text_appears_somewhere_across_module_pages(self):
        run = AgentRun.objects.filter(council_case__slug=DEMO_RUN_SLUG).first()
        combined = ''
        for url in (
            '/agent-runtime-model-router/',
            f'/agent-runtime-model-router/run/{run.id}/',
            f'/agent-runtime-model-router/case/{DEMO_RUN_SLUG}/',
        ):
            combined += self.client.get(url).content.decode()
        for text in REQUIRED_TEXT:
            self.assertIn(text, combined, f'Required text {text!r} missing across module pages')

    def test_no_raw_template_tags(self):
        run = AgentRun.objects.filter(council_case__slug=DEMO_RUN_SLUG).first()
        for url in (
            '/agent-runtime-model-router/',
            f'/agent-runtime-model-router/run/{run.id}/',
            f'/agent-runtime-model-router/case/{DEMO_RUN_SLUG}/',
        ):
            content = self.client.get(url).content.decode()
            for token in RAW_TEMPLATE_TOKENS:
                self.assertNotIn(token, content, f'raw template token "{token}" leaked into {url}')

    def test_no_fully_autonomous_or_unsupported_claims(self):
        run = AgentRun.objects.filter(council_case__slug=DEMO_RUN_SLUG).first()
        for url in (
            '/agent-runtime-model-router/',
            f'/agent-runtime-model-router/run/{run.id}/',
            f'/agent-runtime-model-router/case/{DEMO_RUN_SLUG}/',
        ):
            content = self.client.get(url).content.decode()
            self.assertNotIn('fully autonomous', content.lower())
            idx = content.find('Microsoft certified')
            while idx != -1:
                context = content[max(0, idx - 60):idx + 40]
                self.assertIn('not', context)
                idx = content.find('Microsoft certified', idx + 1)
            self.assertNotIn('Shariah certified', content)
            self.assertNotIn('is a fatwa', content)


class PlatformPageTeaserTests(TestCase):
    def test_platform_page_mentions_agent_runtime_model_router(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Agent Runtime & Model Router')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class FallbackModelSelectionTests(TestCase):
    """
    fix/router-fallback-model — the cross-provider fallback must ask the
    fallback provider to run ITS OWN configured model, never the primary
    provider's model string. Regression coverage for the defect surfaced by
    the AI Observatory (a real Anthropic request for "gpt-4o" failing).
    """

    @classmethod
    def setUpTestData(cls):
        sync_registry()

    def setUp(self):
        from ai_agent_council.models import CouncilRun
        self.council_run = CouncilRun.objects.create(
            slug='fallback-model-test-run', title='Fallback Model Test', question='?',
            task_category='industrial_asset_modernisation',
        )

    def _live_run(self, suffix=''):
        from agent_runtime_model_router.services.execution import create_agent_run
        return create_agent_run(
            'Finance Modelling Agent', 'capex_opex_modelling', council_case=self.council_run,
            execution_mode='live', input_summary=f'fallback model test {suffix}',
            rerun_reason=suffix or '',
        )

    @staticmethod
    def _scripted_adapter(provider, results, calls_log):
        """Adapter double that logs every instruction it receives."""
        from agent_runtime_model_router.services.model_adapters import AdapterResult

        class _Fake:
            def __init__(self):
                self.provider = provider

            def run(self, instruction):
                calls_log.append({'provider': provider, 'model_name': instruction.get('model_name')})
                if results:
                    return results.pop(0)
                return AdapterResult(status='failed', failure_reason='timeout', model_provider=provider)
        return _Fake()

    @staticmethod
    def _ok(provider, model):
        from agent_runtime_model_router.services.model_adapters import AdapterResult
        return AdapterResult(
            status='success',
            output={'output_summary': 'ok', 'confidence': 80, 'evidence_used': [],
                    'missing_data': [], 'risk_flags': []},
            raw_text='ok', model_provider=provider, model_name=model,
            actual_usage={'input_tokens': 10, 'output_tokens': 5},
        )

    @staticmethod
    def _fail(provider):
        from agent_runtime_model_router.services.model_adapters import AdapterResult
        return AdapterResult(status='failed', failure_reason='timeout', model_provider=provider)

    def _execute(self, run, adapters, **kwargs):
        from unittest import mock
        from agent_runtime_model_router.services import execution
        with mock.patch.object(execution, 'get_adapter', side_effect=lambda p: adapters[p]):
            return execution.execute_agent(run, **kwargs)

    def test_primary_success_never_touches_fallback(self):
        calls = []
        run = self._live_run('primary-ok')
        adapters = {
            'openai': self._scripted_adapter('openai', [self._ok('openai', 'gpt-4o')], calls),
            'anthropic': self._scripted_adapter('anthropic', [], calls),
        }
        run = self._execute(run, adapters)
        self.assertEqual([c['provider'] for c in calls], ['openai'])
        self.assertEqual(run.fallback_chain, [])
        self.assertEqual(run.model_provider, 'openai')

    def test_openai_to_anthropic_fallback_uses_anthropic_model(self):
        """The core regression: primary openai (gpt-4o) fails twice; the
        anthropic fallback must be asked for anthropic's OWN configured
        model, not 'gpt-4o'."""
        from agent_runtime_model_router.services.model_router import DEFAULT_MODEL_BY_PROVIDER
        calls = []
        run = self._live_run('openai-to-anthropic')
        anthropic_model = DEFAULT_MODEL_BY_PROVIDER['anthropic']
        adapters = {
            'openai': self._scripted_adapter('openai', [self._fail('openai'), self._fail('openai')], calls),
            'anthropic': self._scripted_adapter('anthropic', [self._ok('anthropic', anthropic_model)], calls),
        }
        run = self._execute(run, adapters)
        self.assertEqual(run.status in ('completed', 'needs_human_review'), True)
        self.assertEqual(run.model_provider, 'anthropic')
        # The primary attempts carried openai's model; the fallback attempt
        # carried anthropic's own configured model.
        self.assertEqual(calls[0], {'provider': 'openai', 'model_name': 'gpt-4o'})
        self.assertEqual(calls[1], {'provider': 'openai', 'model_name': 'gpt-4o'})
        self.assertEqual(calls[2], {'provider': 'anthropic', 'model_name': anthropic_model})
        self.assertNotEqual(calls[2]['model_name'], 'gpt-4o')
        # fallback_chain records the real provider/model pairs.
        self.assertEqual(run.fallback_chain[-1]['provider'], 'anthropic')
        self.assertEqual(run.fallback_chain[-1]['model'], anthropic_model)
        self.assertEqual(run.fallback_chain[-1]['outcome'], 'success')

    def test_anthropic_to_openai_fallback_uses_openai_model(self):
        """Reverse direction: requires_reasoning routes primary to
        anthropic; its fallback (openai) must receive gpt-4o, not claude."""
        calls = []
        run = self._live_run('anthropic-to-openai')
        adapters = {
            'anthropic': self._scripted_adapter('anthropic', [self._fail('anthropic'), self._fail('anthropic')], calls),
            'openai': self._scripted_adapter('openai', [self._ok('openai', 'gpt-4o')], calls),
        }
        run = self._execute(run, adapters, requires_reasoning=True)
        self.assertEqual(calls[0]['provider'], 'anthropic')
        self.assertEqual(calls[0]['model_name'], 'claude-opus-4-5')
        self.assertEqual(calls[2], {'provider': 'openai', 'model_name': 'gpt-4o'})
        self.assertEqual(run.model_provider, 'openai')

    def test_missing_fallback_model_config_fails_clearly_without_attempt(self):
        from unittest import mock
        from agent_runtime_model_router.services import model_router
        calls = []
        run = self._live_run('missing-fallback-config')
        adapters = {
            'openai': self._scripted_adapter('openai', [self._fail('openai'), self._fail('openai')], calls),
            'anthropic': self._scripted_adapter('anthropic', [self._ok('anthropic', 'claude-opus-4-5')], calls),
        }
        # Remove the fallback provider's configured model: the fallback must
        # be SKIPPED with an explicit reason, never attempted.
        with mock.patch.object(model_router, 'default_model_for', side_effect=lambda p: None if p == 'anthropic' else model_router.DEFAULT_MODEL_BY_PROVIDER.get(p)):
            run = self._execute(run, adapters)
        self.assertEqual([c['provider'] for c in calls], ['openai', 'openai'])
        self.assertEqual(run.status, 'needs_human_review')
        skipped = run.fallback_chain[-1]
        self.assertEqual(skipped['outcome'], 'skipped')
        self.assertEqual(skipped['reason'], 'no_fallback_model_configured')

    def test_all_routes_fail_is_honest_and_bounded(self):
        """Primary twice + fallback once = exactly three live attempts, no
        fallback-of-fallback, no loop."""
        calls = []
        run = self._live_run('all-fail')
        adapters = {
            'openai': self._scripted_adapter('openai', [self._fail('openai'), self._fail('openai')], calls),
            'anthropic': self._scripted_adapter('anthropic', [self._fail('anthropic')], calls),
        }
        run = self._execute(run, adapters)
        self.assertEqual(len(calls), 3)
        self.assertEqual(run.status, 'needs_human_review')
        self.assertEqual([f['outcome'] for f in run.fallback_chain], ['failed', 'failed_retry', 'failed'])

    def test_skipped_fallback_still_allows_explicit_deterministic_fallback(self):
        from unittest import mock
        from agent_runtime_model_router.services import model_router
        from agent_runtime_model_router.services.model_adapters import DeterministicTestAdapter
        calls = []
        run = self._live_run('skip-then-deterministic')
        adapters = {
            'openai': self._scripted_adapter('openai', [self._fail('openai'), self._fail('openai')], calls),
            'deterministic': DeterministicTestAdapter(),
        }
        with mock.patch.object(model_router, 'default_model_for', side_effect=lambda p: None if p == 'anthropic' else model_router.DEFAULT_MODEL_BY_PROVIDER.get(p)):
            run = self._execute(run, adapters, allow_deterministic_fallback=True)
        self.assertEqual(run.execution_mode_used, 'deterministic_test')
        self.assertEqual(run.fallback_chain[-1]['provider'], 'deterministic')

    def test_telemetry_failure_does_not_break_fallback_routing(self):
        from unittest import mock
        calls = []
        run = self._live_run('telemetry-fail')
        adapters = {
            'openai': self._scripted_adapter('openai', [self._fail('openai'), self._fail('openai')], calls),
            'anthropic': self._scripted_adapter('anthropic', [self._ok('anthropic', 'claude-opus-4-5')], calls),
        }
        with mock.patch('ai_observatory.services.recorder.record_model_invocation',
                        side_effect=RuntimeError('telemetry boom')):
            run = self._execute(run, adapters)
        self.assertEqual(run.model_provider, 'anthropic')
        self.assertEqual(calls[2]['model_name'], 'claude-opus-4-5')

    def test_observatory_attribution_correct_provider_model_pairs(self):
        """One row per physical request, each with the provider/model pair
        that was actually attempted — no double counting."""
        from ai_observatory.models import ModelInvocation
        calls = []
        run = self._live_run('observatory-attribution')
        adapters = {
            'openai': self._scripted_adapter('openai', [self._fail('openai'), self._fail('openai')], calls),
            'anthropic': self._scripted_adapter('anthropic', [self._ok('anthropic', 'claude-opus-4-5')], calls),
        }
        self._execute(run, adapters)
        rows = list(ModelInvocation.objects.order_by('created_at'))
        self.assertEqual(len(rows), 3)
        self.assertEqual(
            [(r.provider, r.succeeded, r.retry_count) for r in rows],
            [('openai', False, 0), ('openai', False, 1), ('anthropic', True, 0)],
        )
        self.assertEqual(rows[2].model_name, 'claude-opus-4-5')
        self.assertEqual(rows[2].input_tokens, 10)
        self.assertEqual(rows[2].output_tokens, 5)
