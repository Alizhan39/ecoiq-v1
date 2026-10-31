"""
digital_twin/tests.py — plain django.test.TestCase, module-level helper
functions (matching this repo's convention — see core/tests.py,
waste_to_value_capital_allocation_engine/tests.py). No pytest, no
factory_boy, no mocking of the deterministic services under test: every
test exercises real model rows and real service functions.
"""
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from ai_agent_council.agents import OPERATIONAL_AGENTS, _scan_ai_agents_repo_state
from ai_agent_council.models import CouncilRun
from digital_twin import models as m
from digital_twin.services import baseline as baseline_service
from digital_twin.services import council as council_service
from digital_twin.services import guardrails as guardrails_service
from digital_twin.services import human_approval_gate
from digital_twin.services import loss_detection as loss_detection_service
from digital_twin.services import outcomes as outcomes_service
from digital_twin.services import promotion as promotion_service
from digital_twin.services import scenario_simulation
from digital_twin.services import stewardship as stewardship_service
from digital_twin.services import units as units_service
from waste_to_value_capital_allocation_engine.models import CapitalAllocationDecision, InterventionOption, OperationalLoss
from core.testing_access import SignedIn

User = get_user_model()


def _asset_type(code='manufacturing_facility'):
    return m.AssetType.objects.get(code=code)


def _unit(code):
    return m.Unit.objects.get(code=code)


def _make_asset(**kwargs):
    defaults = {'name': 'Test Factory', 'asset_type': _asset_type()}
    defaults.update(kwargs)
    return m.IndustrialAsset.objects.create(**defaults)


def _make_twin(asset=None, **kwargs):
    asset = asset or _make_asset()
    defaults = {'name': 'Test Twin', 'version': 1}
    defaults.update(kwargs)
    return m.DigitalTwin.objects.create(asset=asset, **defaults)


def _make_component(twin, **kwargs):
    defaults = {'name': 'Test Component', 'component_type': 'machine'}
    defaults.update(kwargs)
    return m.TwinComponent.objects.create(twin=twin, **defaults)


def _make_node(twin, component=None, **kwargs):
    defaults = {'name': 'Test Node', 'node_type': 'treatment'}
    defaults.update(kwargs)
    return m.ProcessNode.objects.create(twin=twin, component=component, **defaults)


def _fully_populated_twin():
    """A twin with all 5 completeness sections populated, for baseline tests."""
    twin = _make_twin()
    component = _make_component(twin)
    node_a = _make_node(twin, component, name='Node A', node_type='heating', confidence=80.0)
    node_b = _make_node(twin, component, name='Node B', node_type='transport', confidence=70.0)
    m.ProcessEdge.objects.create(twin=twin, source_node=node_a, target_node=node_b)
    m.ResourceFlow.objects.create(
        twin=twin, resource_type='energy', quantity=100.0, unit=_unit('kwh'), confidence=75.0,
    )
    definition, _ = m.MetricDefinition.objects.get_or_create(code='test_metric', defaults={'name': 'Test Metric'})
    m.OperationalMetric.objects.create(
        definition=definition, twin=twin, value=10.0, unit=_unit('kwh'), confidence=90.0,
        recorded_at=timezone.now(),
    )
    return twin


def _make_scenario(twin=None, loss=None, **overrides):
    twin = twin or _fully_populated_twin()
    loss = loss or OperationalLoss.objects.create(
        title='Test Loss', loss_type='energy_loss', financial_loss_amount=10000.0, confidence=70.0,
    )
    intervention = InterventionOption.objects.create(
        operational_loss=loss, title='Test Intervention', intervention_type='operational_optimisation',
        capex_estimate=10000.0, opex_change=-500.0, estimated_annual_savings=5000.0,
        estimated_loss_avoided=5000.0,
    )
    defaults = {
        'twin': twin, 'scenario_type': 'low_cost', 'confidence': 70.0,
        'technical_specification': 'A reviewable, supplier-neutral specification.',
        'worker_impact': 'No role changes.', 'community_impact': 'No local effect expected.',
        'evidence_references': ['digital_twin.TestFixture:1'],
        'waste_impact': -10.0, 'energy_impact': -100.0, 'emissions_impact': -50.0,
    }
    defaults.update(overrides)
    return m.ModernisationScenario.objects.create(intervention=intervention, **defaults)


class ModelConstraintTests(TestCase):
    def test_only_one_active_approved_twin_per_asset(self):
        asset = _make_asset()
        m.DigitalTwin.objects.create(asset=asset, name='v1', version=1, status='active', approved_at=timezone.now())
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                m.DigitalTwin.objects.create(asset=asset, name='v2', version=2, status='active', approved_at=timezone.now())

    def test_active_unapproved_twins_do_not_collide(self):
        # Only ACTIVE + APPROVED collides; an active-but-unapproved twin is
        # fine to coexist (it hasn't cleared human governance yet).
        asset = _make_asset()
        m.DigitalTwin.objects.create(asset=asset, name='v1', version=1, status='active', approved_at=None)
        m.DigitalTwin.objects.create(asset=asset, name='v2', version=2, status='active', approved_at=None)
        self.assertEqual(asset.twins.count(), 2)

    def test_unique_twin_asset_version(self):
        asset = _make_asset()
        m.DigitalTwin.objects.create(asset=asset, name='v1', version=1)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                m.DigitalTwin.objects.create(asset=asset, name='v1 dup', version=1)

    def test_process_edge_unique(self):
        twin = _make_twin()
        a = _make_node(twin, name='A')
        b = _make_node(twin, name='B')
        m.ProcessEdge.objects.create(twin=twin, source_node=a, target_node=b)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                m.ProcessEdge.objects.create(twin=twin, source_node=a, target_node=b)

    def test_measured_outcome_variance_is_always_recomputed(self):
        twin = _fully_populated_twin()
        loss = OperationalLoss.objects.create(title='L', loss_type='energy_loss', financial_loss_amount=1.0)
        scenario = _make_scenario(twin=twin, loss=loss)
        action = m.ImplementationAction.objects.create(scenario=scenario, title='Action')
        outcome = m.MeasuredOutcome.objects.create(action=action, predicted_value=100.0, actual_value=90.0)
        self.assertEqual(outcome.variance, -10.0)
        self.assertEqual(outcome.variance_pct, -10.0)
        outcome.actual_value = 80.0
        outcome.save()
        self.assertEqual(outcome.variance, -20.0)
        self.assertEqual(outcome.variance_pct, -20.0)

    def test_human_decision_derives_human_approved_from_decision(self):
        scenario = _make_scenario()
        approved = m.HumanDecision.objects.create(scenario=scenario, decision='approved')
        self.assertIs(approved.human_approved, True)
        rejected = m.HumanDecision.objects.create(scenario=scenario, decision='rejected')
        self.assertIs(rejected.human_approved, False)
        deferred = m.HumanDecision.objects.create(scenario=scenario, decision='deferred')
        self.assertIsNone(deferred.human_approved)


class UnitConversionTests(TestCase):
    def test_convert_within_category(self):
        value_kwh = units_service.convert(1.0, _unit('mwh'), _unit('kwh'))
        self.assertEqual(value_kwh, 1000.0)

    def test_incompatible_units_raise(self):
        with self.assertRaises(units_service.IncompatibleUnitsError):
            units_service.convert(1.0, _unit('kwh'), _unit('kg'))

    def test_assert_same_category_raises_on_mismatch(self):
        with self.assertRaises(units_service.IncompatibleUnitsError):
            units_service.assert_same_category(_unit('kwh'), _unit('m3'))

    def test_assert_same_category_passes_on_match(self):
        units_service.assert_same_category(_unit('kwh'), _unit('mwh'))  # should not raise


class BaselineEngineTests(TestCase):
    def test_empty_twin_is_incomplete_with_zero_scores(self):
        twin = _make_twin()
        result = baseline_service.compute_baseline(twin)
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['completeness_score'], 0.0)
        self.assertEqual(result['confidence_score'], 0.0)
        self.assertFalse(result['ready_for_optimisation'])
        self.assertTrue(len(result['warnings']) > 0)

    def test_fully_populated_twin_is_baseline_ready(self):
        twin = _fully_populated_twin()
        result = baseline_service.compute_baseline(twin)
        self.assertEqual(result['completeness_score'], 100.0)
        self.assertEqual(result['status'], 'baseline_ready')
        self.assertTrue(result['ready_for_optimisation'])

    def test_critical_gap_blocks_readiness_even_if_otherwise_complete(self):
        twin = _fully_populated_twin()
        m.TwinDataGap.objects.create(
            twin=twin, affected_area='X', required_data='Y', why_it_matters='Z', severity='critical', status='open',
        )
        result = baseline_service.compute_baseline(twin)
        self.assertFalse(result['ready_for_optimisation'])
        self.assertEqual(len(result['critical_data_gaps']), 1)

    def test_generate_data_gaps_creates_one_per_missing_section_and_is_idempotent(self):
        twin = _make_twin()
        created_first = baseline_service.generate_data_gaps(twin)
        self.assertEqual(len(created_first), len(baseline_service.COMPLETENESS_SECTIONS))
        created_second = baseline_service.generate_data_gaps(twin)
        self.assertEqual(created_second, [])  # no duplicates on a second run
        self.assertEqual(twin.data_gaps.count(), len(baseline_service.COMPLETENESS_SECTIONS))

    def test_apply_baseline_never_sets_active_itself(self):
        twin = _fully_populated_twin()
        baseline_service.apply_baseline(twin)
        twin.refresh_from_db()
        self.assertEqual(twin.status, 'baseline_ready')
        self.assertNotEqual(twin.status, 'active')  # only a human approval can do that
        self.assertIsNotNone(twin.completeness_score)


class LossDetectionTests(TestCase):
    def test_downtime_rule_detects_candidate(self):
        twin = _make_twin()
        node = _make_node(twin, name='Line 1', downtime_hours=150.0, cost_per_unit=10.0, confidence=60.0)
        results = loss_detection_service.detect_loss_candidates(twin)
        loss_types = [c.loss_type for c, _ in results]
        self.assertIn('production_downtime', loss_types)

    def test_no_false_positive_below_threshold(self):
        twin = _make_twin()
        _make_node(twin, name='Line 1', downtime_hours=10.0)
        results = loss_detection_service.detect_loss_candidates(twin)
        self.assertEqual(results, [])

    def test_detection_is_idempotent_across_reruns(self):
        twin = _make_twin()
        _make_node(twin, name='Line 1', downtime_hours=150.0)
        loss_detection_service.detect_loss_candidates(twin)
        loss_detection_service.detect_loss_candidates(twin)
        self.assertEqual(m.LossDetection.objects.filter(twin=twin).count(), 1)

    def test_promotion_requires_approved_status(self):
        twin = _make_twin()
        candidate = m.LossDetection.objects.create(
            twin=twin, loss_type='energy_loss', title='Candidate', status='candidate',
        )
        with self.assertRaises(loss_detection_service.PromotionNotAllowedError):
            loss_detection_service.promote_loss_detection(candidate)

    def test_promotion_creates_real_operational_loss_and_links_back(self):
        twin = _make_twin(asset=_make_asset(name='Linked Asset'))
        candidate = m.LossDetection.objects.create(
            twin=twin, loss_type='energy_loss', title='Candidate', status='approved',
            estimated_annual_impact=1234.0, confidence=80.0,
        )
        real_loss = loss_detection_service.promote_loss_detection(candidate)
        candidate.refresh_from_db()
        self.assertIsInstance(real_loss, OperationalLoss)
        self.assertEqual(candidate.status, 'promoted')
        self.assertEqual(candidate.promoted_loss_id, real_loss.pk)
        self.assertEqual(real_loss.asset, 'Linked Asset')

    def test_promotion_is_idempotent(self):
        twin = _make_twin()
        candidate = m.LossDetection.objects.create(
            twin=twin, loss_type='energy_loss', title='Candidate', status='approved',
        )
        first = loss_detection_service.promote_loss_detection(candidate)
        second = loss_detection_service.promote_loss_detection(candidate)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(OperationalLoss.objects.count(), 1)

    def test_promotion_self_heals_status_if_caller_resets_it_after_promotion(self):
        # Reproduces a real bug found while validating the demo fixture: a
        # caller (e.g. a re-run approval script) sets status back to
        # 'approved' on an already-promoted row before calling promote again.
        twin = _make_twin()
        candidate = m.LossDetection.objects.create(
            twin=twin, loss_type='energy_loss', title='Candidate', status='approved',
        )
        real_loss = loss_detection_service.promote_loss_detection(candidate)
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, 'promoted')

        candidate.status = 'approved'  # caller regresses status
        candidate.save()
        result = loss_detection_service.promote_loss_detection(candidate)
        candidate.refresh_from_db()
        self.assertEqual(result.pk, real_loss.pk)
        self.assertEqual(candidate.status, 'promoted')  # self-healed
        self.assertEqual(OperationalLoss.objects.count(), 1)

    def test_never_auto_approved_by_detection(self):
        twin = _make_twin()
        _make_node(twin, name='Line 1', downtime_hours=999.0)
        results = loss_detection_service.detect_loss_candidates(twin)
        for candidate, _ in results:
            self.assertEqual(candidate.status, 'candidate')
            self.assertIsNone(candidate.human_approved)


class ScenarioSimulationTests(TestCase):
    def test_downside_expected_upside_ordering(self):
        scenario = _make_scenario()
        result = scenario_simulation.simulate_scenario(scenario)
        downside_capex = result['cases']['downside']['capex']['output']
        expected_capex = result['cases']['expected']['capex']['output']
        upside_capex = result['cases']['upside']['capex']['output']
        self.assertGreater(downside_capex, expected_capex)
        self.assertGreater(expected_capex, upside_capex)

        downside_savings = result['cases']['downside']['annual_savings']['output']
        upside_savings = result['cases']['upside']['annual_savings']['output']
        self.assertLess(downside_savings, upside_savings)

    def test_every_value_exposes_formula_inputs_and_output(self):
        scenario = _make_scenario()
        result = scenario_simulation.simulate_scenario(scenario)
        for case in result['cases'].values():
            for value in case.values():
                self.assertIn('formula', value)
                self.assertIn('inputs', value)
                self.assertIn('assumptions', value)
                self.assertIn('output', value)
                self.assertIn('unit', value)
                self.assertIn('confidence', value)
                self.assertIn('missing_inputs', value)

    def test_zero_capex_zero_savings_scenario_has_no_crash_and_undefined_payback(self):
        loss = OperationalLoss.objects.create(title='L', loss_type='energy_loss', financial_loss_amount=1.0)
        intervention = InterventionOption.objects.create(
            operational_loss=loss, title='Do nothing', intervention_type='do_nothing',
            capex_estimate=0.0, opex_change=0.0, estimated_annual_savings=0.0,
        )
        scenario = m.ModernisationScenario.objects.create(twin=_make_twin(), intervention=intervention, scenario_type='no_change')
        result = scenario_simulation.simulate_scenario(scenario)
        expected = result['cases']['expected']
        self.assertIsNone(expected['simple_payback_months']['output'])
        self.assertIn('annual_savings is 0 — payback undefined', expected['simple_payback_months']['missing_inputs'])

    def test_persist_scenario_cases_writes_intervention_scenarios_and_is_idempotent(self):
        from waste_to_value_capital_allocation_engine.models import InterventionScenario

        scenario = _make_scenario()
        scenario_simulation.persist_scenario_cases(scenario)
        scenario_simulation.persist_scenario_cases(scenario)
        self.assertEqual(InterventionScenario.objects.filter(intervention=scenario.intervention).count(), 3)
        cases = {row.sensitivity_case for row in InterventionScenario.objects.filter(intervention=scenario.intervention)}
        self.assertEqual(cases, {'base', 'upside', 'downside'})


class StewardshipTests(TestCase):
    def test_all_seeded_kpis_are_unapproved_by_default(self):
        for kpi in m.StewardshipKPI.objects.all():
            self.assertEqual(kpi.approval_status, 'requires_scholarly_review')
            self.assertFalse(kpi.is_approved_for_use)
        for principle in m.StewardshipPrinciple.objects.all():
            self.assertFalse(principle.is_approved_for_use)
            self.assertEqual(principle.review_status, 'draft_reflection')
        for source in m.SacredSourceReference.objects.all():
            self.assertEqual(source.review_status, 'source_needed')
            self.assertEqual(source.approved_translation, '')

    def test_run_stewardship_assessment_creates_one_row_per_active_kpi(self):
        scenario = _make_scenario()
        assessments = stewardship_service.run_stewardship_assessment(scenario)
        self.assertEqual(len(assessments), m.StewardshipKPI.objects.filter(is_active=True).count())

    def test_harm_keyword_triggers_blocking(self):
        scenario = _make_scenario(worker_impact='Risk of exposure during construction.')
        assessments = stewardship_service.run_stewardship_assessment(scenario)
        harm = next(a for a in assessments if a.kpi.slug == 'worker-community-harm-screen')
        self.assertTrue(harm.blocking)
        self.assertEqual(harm.calculated_score, 0.0)

    def test_no_harm_keyword_does_not_block(self):
        scenario = _make_scenario(worker_impact='Two operators retrained, no other change.')
        assessments = stewardship_service.run_stewardship_assessment(scenario)
        harm = next(a for a in assessments if a.kpi.slug == 'worker-community-harm-screen')
        self.assertFalse(harm.blocking)

    def test_missing_data_produces_warning_not_a_fabricated_score(self):
        scenario = _make_scenario(waste_impact=None)
        assessments = stewardship_service.run_stewardship_assessment(scenario)
        waste_kpi = next(a for a in assessments if a.kpi.slug == 'prevention-of-waste-reduction')
        self.assertIsNone(waste_kpi.calculated_score)
        self.assertTrue(waste_kpi.warning)

    def test_rerunning_assessment_updates_rather_than_duplicates(self):
        scenario = _make_scenario()
        stewardship_service.run_stewardship_assessment(scenario)
        stewardship_service.run_stewardship_assessment(scenario)
        self.assertEqual(
            m.StewardshipAssessment.objects.filter(scenario=scenario).count(),
            m.StewardshipKPI.objects.filter(is_active=True).count(),
        )


class GuardrailTests(TestCase):
    def test_clean_scenario_passes(self):
        # A "clean" scenario must satisfy every KPI's happy path: waste/
        # energy/emissions all reduced, no harm/vulnerability keywords, a
        # backed confidence, a technical spec, a good payback, and a fully
        # populated governance trail (evidence/risks/dependencies/regulatory).
        scenario = _make_scenario(
            technical_risks=['Minor supply-chain lead time'], dependencies=['Vendor confirmation'],
            regulatory_requirements=['Standard permit filing'],
        )
        scenario.intervention.estimated_payback_months = 6.0
        scenario.intervention.save()
        stewardship_service.run_stewardship_assessment(scenario)
        result = guardrails_service.evaluate_guardrails(scenario)
        self.assertEqual(result['verdict'], 'pass')

    def test_worker_harm_blocks(self):
        scenario = _make_scenario(worker_impact='Fatality risk during confined-space work.')
        stewardship_service.run_stewardship_assessment(scenario)
        result = guardrails_service.evaluate_guardrails(scenario)
        self.assertEqual(result['verdict'], 'block')

    def test_undocumented_community_impact_is_a_lesser_severity_than_a_detected_signal(self):
        undocumented = _make_scenario(community_impact='')
        stewardship_service.run_stewardship_assessment(undocumented)
        undocumented_result = guardrails_service.evaluate_guardrails(undocumented)

        flagged = _make_scenario(community_impact='Requires resettlement of a vulnerable community.')
        stewardship_service.run_stewardship_assessment(flagged)
        flagged_result = guardrails_service.evaluate_guardrails(flagged)

        self.assertNotEqual(undocumented_result['verdict'], 'requires_specialist_review')
        self.assertEqual(flagged_result['verdict'], 'requires_specialist_review')

    def test_missing_evidence_requires_evidence(self):
        scenario = _make_scenario(confidence=90.0, evidence_references=[])
        stewardship_service.run_stewardship_assessment(scenario)
        result = guardrails_service.evaluate_guardrails(scenario)
        self.assertIn(result['verdict'], ('requires_evidence', 'block', 'requires_specialist_review'))

    def test_hidden_pollution_transfer_blocks(self):
        scenario = _make_scenario(emissions_impact=500.0, evidence_references=[])
        scenario.intervention.estimated_annual_savings = 10000.0
        scenario.intervention.save()
        stewardship_service.run_stewardship_assessment(scenario)
        result = guardrails_service.evaluate_guardrails(scenario)
        self.assertEqual(result['verdict'], 'block')


class AgentCouncilIntegrationTests(TestCase):
    def test_registry_includes_new_digital_twin_personas(self):
        names = {a['name'] for a in OPERATIONAL_AGENTS}
        for expected in ('Digital Twin Agent', 'Engineering Agent', 'Energy and Resources Agent',
                         'Worker Safety Agent', 'Community Impact Agent', 'Evidence Agent', 'Stewardship Agent'):
            self.assertIn(expected, names)

    def test_every_new_persona_has_a_complete_training_pack(self):
        state = _scan_ai_agents_repo_state()
        for folder in ('digital_twin_agent', 'engineering_agent', 'energy_resources_agent', 'worker_safety_agent',
                       'community_impact_agent', 'evidence_agent', 'stewardship_agent'):
            self.assertIn(folder, state['operational_folder_names'])
            self.assertEqual(len(state['per_folder_files'][folder]), 10)

    def test_convene_council_creates_one_task_per_agent_with_valid_schema(self):
        scenario = _make_scenario()
        stewardship_service.run_stewardship_assessment(scenario)
        result = council_service.convene_council(scenario)
        self.assertEqual(len(result['tasks']), len(council_service.COUNCIL_AGENT_ORDER))
        for task in result['tasks']:
            self.assertTrue(0 <= task.confidence <= 100)
            self.assertIsInstance(task.evidence_refs, list)
            self.assertIsInstance(task.missing_data, list)
            self.assertIsInstance(task.risk_flags, list)
            self.assertTrue(task.position_summary)

    def test_council_run_is_simulated(self):
        scenario = _make_scenario()
        stewardship_service.run_stewardship_assessment(scenario)
        result = council_service.convene_council(scenario)
        self.assertTrue(result['run'].is_simulated)

    def test_blocked_scenario_produces_rejected_decision_and_disagreement(self):
        scenario = _make_scenario(worker_impact='Injury risk unless mitigated.')
        stewardship_service.run_stewardship_assessment(scenario)
        result = council_service.convene_council(scenario)
        self.assertEqual(result['decision'].status, 'rejected')
        worker_safety_task = next(t for t in result['tasks'] if t.agent_name == 'Worker Safety Agent')
        self.assertIn('worker_harm_signal', worker_safety_task.risk_flags)

    def test_get_council_run_finds_review_with_no_human_decision_yet(self):
        # Reproduces a real view bug: Council review happens BEFORE a human
        # decision exists, so lookup must not depend on one.
        scenario = _make_scenario()
        stewardship_service.run_stewardship_assessment(scenario)
        result = council_service.convene_council(scenario)
        self.assertFalse(m.HumanDecision.objects.filter(scenario=scenario).exists())
        found = council_service.get_council_run(scenario)
        self.assertEqual(found.pk, result['run'].pk)

    def test_convene_council_is_rerunnable_without_duplicating_the_run(self):
        scenario = _make_scenario()
        stewardship_service.run_stewardship_assessment(scenario)
        council_service.convene_council(scenario)
        council_service.convene_council(scenario)
        self.assertEqual(CouncilRun.objects.filter(task_category=council_service.TASK_CATEGORY).count(), 1)


class HumanApprovalGateTests(TestCase):
    def test_promotion_action_requires_approval(self):
        scenario = _make_scenario()
        decision = m.HumanDecision.objects.create(scenario=scenario, decision='deferred')
        with self.assertRaises(human_approval_gate.HumanApprovalRequiredError):
            human_approval_gate.require_human_approval('digital_twin_scenario_promotion', decision)

    def test_approved_decision_passes_gate(self):
        scenario = _make_scenario()
        decision = m.HumanDecision.objects.create(scenario=scenario, decision='approved')
        self.assertTrue(human_approval_gate.require_human_approval('digital_twin_scenario_promotion', decision))

    def test_base_actions_still_enforced(self):
        # Proves this app's gate is a real union, not a fork — the 8 base
        # actions from agent_runtime_model_router still require .human_approved
        # even though this module never mentions them explicitly.
        class Dummy:
            human_approved = None
            pk = 1
        with self.assertRaises(human_approval_gate.HumanApprovalRequiredError):
            human_approval_gate.require_human_approval('supplier_outreach', Dummy())


class PromotionTests(TestCase):
    def test_promotion_requires_approving_decision(self):
        scenario = _make_scenario()
        decision = m.HumanDecision.objects.create(scenario=scenario, decision='rejected')
        with self.assertRaises(human_approval_gate.HumanApprovalRequiredError):
            promotion_service.promote_scenario(decision)

    def test_promotion_creates_capital_allocation_decision(self):
        scenario = _make_scenario()
        decision = m.HumanDecision.objects.create(scenario=scenario, decision='approved_with_conditions', conditions=['x'])
        result = promotion_service.promote_scenario(decision)
        self.assertIsInstance(result, CapitalAllocationDecision)
        self.assertEqual(result.approval_status, 'approved_with_conditions')
        self.assertEqual(result.intervention_id, scenario.intervention_id)

    def test_duplicate_promotion_is_prevented(self):
        scenario = _make_scenario()
        decision = m.HumanDecision.objects.create(scenario=scenario, decision='approved')
        first = promotion_service.promote_scenario(decision)
        second = promotion_service.promote_scenario(decision)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(CapitalAllocationDecision.objects.filter(intervention=scenario.intervention).count(), 1)

    def test_promotion_preserves_audit_trail_link(self):
        scenario = _make_scenario()
        decision = m.HumanDecision.objects.create(
            scenario=scenario, decision='approved', reviewer_role='Founder', comments='Looks good.',
        )
        cad = promotion_service.promote_scenario(decision)
        decision.refresh_from_db()
        self.assertEqual(decision.capital_allocation_decision_id, cad.pk)
        self.assertIn('Founder', cad.decision)


class OutcomesTests(TestCase):
    def test_record_outcome_updates_twin_last_observed_at(self):
        scenario = _make_scenario()
        twin = scenario.twin
        twin.last_observed_at = None
        twin.save()
        action = m.ImplementationAction.objects.create(scenario=scenario, title='Do the thing')
        outcomes_service.record_measured_outcome(action, predicted_value=100.0, actual_value=95.0)
        twin.refresh_from_db()
        self.assertIsNotNone(twin.last_observed_at)

    def test_placeholder_outcome_with_no_actual_value_has_no_variance(self):
        scenario = _make_scenario()
        action = m.ImplementationAction.objects.create(scenario=scenario, title='Pending measurement')
        outcome = outcomes_service.record_measured_outcome(action, predicted_value=100.0, actual_value=None)
        self.assertIsNone(outcome.variance)
        self.assertIsNone(outcome.variance_pct)

    def test_verified_impact_score_updates_after_promotion_and_measurement(self):
        scenario = _make_scenario()
        decision = m.HumanDecision.objects.create(scenario=scenario, decision='approved')
        cad = promotion_service.promote_scenario(decision)
        self.assertEqual(cad.verified_impact_score, 0.0)
        action = m.ImplementationAction.objects.create(scenario=scenario, title='Do the thing')
        outcomes_service.record_measured_outcome(action, predicted_value=100.0, actual_value=95.0)
        cad.refresh_from_db()
        self.assertEqual(cad.verified_impact_score, 95.0)  # 100 - |5%| variance


class PermissionBoundaryTests(SignedIn, TestCase):
    """
    digital_twin.council is EXPERIMENTAL, so the whole prefix requires sign-in
    (core/access.py). The write actions keep their own stricter checks on top;
    this asserts the floor and the ceiling separately.
    """

    def test_approve_view_requires_login(self):
        scenario = _make_scenario()
        response = Client().get(
            reverse('digital_twin:scenario_approve', args=[scenario.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_promote_view_requires_login(self):
        scenario = _make_scenario()
        response = Client().get(
            reverse('digital_twin:scenario_promote', args=[scenario.pk]))
        self.assertEqual(response.status_code, 302)

    def test_read_only_views_are_no_longer_public(self):
        """
        They were. A scenario baseline is model output from an experimental
        module, and it answered anonymously.
        """
        scenario = _make_scenario()
        response = Client().get(
            reverse('digital_twin:twin_baseline', args=[scenario.twin.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_a_signed_in_user_can_still_read_them(self):
        scenario = _make_scenario()
        response = self.client.get(
            reverse('digital_twin:twin_baseline', args=[scenario.twin.pk]))
        self.assertEqual(response.status_code, 200)


class DemoWorkflowEndToEndTests(TestCase):
    def test_seed_digital_twin_demo_end_to_end(self):
        call_command('seed_digital_twin_demo')

        asset = m.IndustrialAsset.objects.get(name='Riverside District Heating Plant')
        twin = asset.twins.get(version=1)
        self.assertEqual(twin.status, 'active')
        self.assertIsNotNone(twin.approved_at)

        self.assertGreaterEqual(m.LossDetection.objects.filter(twin=twin).count(), 2)
        promoted = m.LossDetection.objects.filter(twin=twin, status='promoted')
        self.assertGreaterEqual(promoted.count(), 2)
        for candidate in promoted:
            self.assertIsNotNone(candidate.promoted_loss_id)

        scenarios = m.ModernisationScenario.objects.filter(twin=twin)
        self.assertEqual(scenarios.count(), 3)
        self.assertEqual({s.scenario_type for s in scenarios}, {'no_change', 'low_cost', 'strategic'})

        for scenario in scenarios:
            self.assertTrue(scenario.stewardship_assessments.exists())

        strategic = scenarios.get(scenario_type='strategic')
        strategic_run = council_service.get_council_run(strategic)
        self.assertEqual(strategic_run.decision.status, 'rejected')

        low_cost = scenarios.get(scenario_type='low_cost')
        decision = m.HumanDecision.objects.get(scenario=low_cost)
        self.assertEqual(decision.decision, 'approved_with_conditions')
        self.assertIsNotNone(decision.capital_allocation_decision_id)
        self.assertEqual(decision.rejected_alternatives.count(), 2)

        action = m.ImplementationAction.objects.get(scenario=low_cost)
        outcome = action.measured_outcomes.get()
        self.assertIsNone(outcome.actual_value)  # honest placeholder, not fabricated

    def test_demo_is_idempotent(self):
        call_command('seed_digital_twin_demo')
        call_command('seed_digital_twin_demo')
        self.assertEqual(m.IndustrialAsset.objects.filter(name='Riverside District Heating Plant').count(), 1)
        self.assertEqual(m.ModernisationScenario.objects.count(), 3)
        self.assertEqual(CapitalAllocationDecision.objects.count(), 1)
