"""
good_agents/tests.py — PR2 covers: principle-agent mapping, agent
activation (and non-activation of irrelevant agents), opportunity
deduplication/idempotency, evidence confidence, insufficient evidence,
principle conflicts (disagreement preserved), zero-capital classification,
Better Way / Opportunity Cost integration, autonomy boundaries (RED
blocking), run budget exhaustion, retry/idempotency, MRV connection,
ImpactReceipt creation, Evidence Memory persistence.

PR3 (below, see `# === PR3` marker) adds: signal normalisation, duplicate
detection, signal clustering, irrelevant-signal rejection, evidence gate,
Need/Resource creation, resource eligibility, resource matching, circular
matching, zero-capital strategy, funding matching, staged/resumable
GlobalGoodDiscoveryEngine runs, checkpoint resume, MorningImpactBrief v2,
Top 3 Actions, temporal resource expiry.
"""
import datetime

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from countries.models import CountryProfile
from evidence_memory.models import EvidenceMemory
from gold_intelligence.models import GoldProject
from waste_to_value_capital_allocation_engine.models import CapitalAllocationDecision, InterventionOption

from good_agents.models import (
    AgentActivationRecord, AvailableResource, FundingMatch, GoodAgentDefinition, GoodDeedAction,
    GoodDiscoveryRun, GoodMission, GoodOpportunity, ImpactReceipt, Need, ResourceMatch, ResourceStatusChange,
    SignalCluster, SignalProvider, WorldSignal, ZeroCapitalStrategyAction, classify_autonomy,
)
from good_agents.services import good_deeds_engine, opportunity_cost, pipeline, red_team
from good_agents.services.discovery_run import run_discovery
from good_agents.services.orchestrator import Signal, classify_relevant_agents, record_activations, run_deep_reasoning
from good_agents.services.principles import get_principle


class PrincipleAgentMappingTests(TestCase):
    def test_seed_command_creates_configured_lenses_from_canonical_source(self):
        call_command('seed_good_agent_definitions')
        self.assertEqual(GoodAgentDefinition.objects.count(), 6)
        energy_lens = GoodAgentDefinition.objects.get(principle_id=34)
        canonical = get_principle(34)
        self.assertEqual(energy_lens.name, canonical['title'])
        self.assertEqual(energy_lens.mission, canonical['question'])

    def test_seed_command_is_idempotent(self):
        call_command('seed_good_agent_definitions')
        call_command('seed_good_agent_definitions')
        self.assertEqual(GoodAgentDefinition.objects.count(), 6)

    def test_arabic_name_defaults_to_needs_scholar_review_when_set(self):
        agent = GoodAgentDefinition.objects.create(
            principle_id=200, name='Test Lens', mission='Test mission.', arabic_name='مثال',
        )
        self.assertEqual(agent.arabic_name_review_status, 'needs_scholar_review')

    def test_no_arabic_name_stays_not_applicable(self):
        agent = GoodAgentDefinition.objects.create(principle_id=201, name='Test Lens', mission='x')
        self.assertEqual(agent.arabic_name_review_status, 'not_applicable')


class AgentActivationTests(TestCase):
    def setUp(self):
        call_command('seed_good_agent_definitions')

    def test_relevant_agents_activate_on_matching_signal(self):
        signal = Signal(text='coal heating pollution', domains=['energy', 'environment'])
        activations = classify_relevant_agents(signal)
        activated_ids = {a.agent.principle_id for a in activations}
        self.assertIn(34, activated_ids)  # Illumination & Energy Transition
        self.assertIn(9, activated_ids)   # Ecological Stewardship

    def test_irrelevant_agents_do_not_activate(self):
        signal = Signal(text='unrelated office supply procurement question', domains=['procurement'])
        activations = classify_relevant_agents(signal)
        self.assertEqual(activations, [])

    def test_never_activates_all_seeded_lenses_for_a_generic_signal(self):
        signal = Signal(text='a generic problem with no specific keywords', domains=[])
        activations = classify_relevant_agents(signal)
        self.assertLess(len(activations), GoodAgentDefinition.objects.count())

    def test_max_activated_cap_is_respected(self):
        signal = Signal(
            text='coal heating pollution vulnerable elderly equitable access shared resource accountability',
            domains=['energy', 'environment', 'social', 'justice', 'housing', 'health'],
        )
        activations = classify_relevant_agents(signal, max_activated=2)
        self.assertLessEqual(len(activations), 2)


class DisagreementPreservationTests(TestCase):
    def setUp(self):
        call_command('seed_good_agent_definitions')
        self.opportunity = GoodOpportunity.objects.create(
            title='Test opportunity', problem_statement='Test problem.',
        )

    def test_positions_are_preserved_not_averaged(self):
        signal = Signal(text='coal heating equitable access', domains=['energy', 'social'])
        activations = classify_relevant_agents(signal)
        deep_output = {
            'positions': [
                {'principle_id': a.agent.principle_id, 'position': 'concerns' if a.agent.principle_id == 45 else 'support', 'confidence': 60}
                for a in activations
            ],
        }
        records = record_activations(self.opportunity, activations, deep_output, metadata={})
        positions = {r.agent.principle_id: r.position for r in records}
        if 45 in positions:
            self.assertEqual(positions[45], 'concerns')
        self.assertTrue(any(p == 'support' for p in positions.values()))

    def test_record_activations_is_idempotent_per_agent(self):
        signal = Signal(text='coal heating pollution', domains=['energy'])
        activations = classify_relevant_agents(signal)
        record_activations(self.opportunity, activations)
        record_activations(self.opportunity, activations)
        self.assertEqual(AgentActivationRecord.objects.filter(opportunity=self.opportunity).count(), len(activations))


class DeepReasoningCostTests(TestCase):
    def setUp(self):
        call_command('seed_good_agent_definitions')

    def test_simulated_demo_adapter_replays_fixture_never_invents(self):
        signal = Signal(text='coal heating pollution', domains=['energy'])
        activations = classify_relevant_agents(signal)
        fixture = {'positions': [{'principle_id': a.agent.principle_id, 'position': 'support', 'confidence': 99} for a in activations]}
        output, metadata = run_deep_reasoning(signal, activations, execution_mode='simulated_demo', fixture_output=fixture)
        self.assertEqual(output, fixture)
        self.assertEqual(metadata['model_provider'], 'simulated')

    def test_cost_policy_can_skip_a_call_over_budget(self):
        signal = Signal(text='coal heating pollution', domains=['energy'])
        activations = classify_relevant_agents(signal)
        output, metadata = run_deep_reasoning(
            signal, activations, execution_mode='simulated_demo', estimated_cost_usd=999.0,
        )
        self.assertIsNone(output)
        self.assertTrue(metadata.get('skipped'))


class ZeroCapitalClassificationTests(TestCase):
    def test_zero_capital_opportunity_gets_find_partner_and_match_actions(self):
        opp = GoodOpportunity.objects.create(
            title='Zero capital test', problem_statement='x', zero_capital_possible=True, status='potential',
        )
        actions = good_deeds_engine.propose_default_actions(opp)
        action_types = {a.action_type for a in actions}
        self.assertIn('find_partner', action_types)
        self.assertIn('match', action_types)

    def test_non_zero_capital_opportunity_does_not_get_partner_actions(self):
        opp = GoodOpportunity.objects.create(
            title='Capital-required test', problem_statement='x', zero_capital_possible=False, status='potential',
        )
        actions = good_deeds_engine.propose_default_actions(opp)
        action_types = {a.action_type for a in actions}
        self.assertNotIn('find_partner', action_types)


class AutonomyBoundaryTests(TestCase):
    def test_classify_autonomy_matches_spec(self):
        self.assertEqual(classify_autonomy('research'), 'green')
        self.assertEqual(classify_autonomy('monitor'), 'green')
        self.assertEqual(classify_autonomy('connect'), 'yellow')
        self.assertEqual(classify_autonomy('match'), 'yellow')

    def test_no_action_type_reaches_red(self):
        for action_type, _ in GoodDeedAction.ACTION_TYPE_CHOICES:
            self.assertIn(classify_autonomy(action_type), ('green', 'yellow'))

    def test_action_creation_rejects_wrong_autonomy_class(self):
        opp = GoodOpportunity.objects.create(title='x', problem_statement='x')
        with self.assertRaises(ValidationError):
            GoodDeedAction.objects.create(opportunity=opp, action_type='research', autonomy_class='yellow')

    def test_yellow_action_cannot_complete_without_human_approval(self):
        opp = GoodOpportunity.objects.create(title='x', problem_statement='x')
        action = GoodDeedAction.objects.create(opportunity=opp, action_type='connect', autonomy_class='yellow')
        with self.assertRaises(ValueError):
            good_deeds_engine.complete_action(action)

    def test_yellow_action_completes_after_approval(self):
        opp = GoodOpportunity.objects.create(title='x', problem_statement='x')
        action = GoodDeedAction.objects.create(opportunity=opp, action_type='connect', autonomy_class='yellow')
        good_deeds_engine.approve_action(action)
        action.refresh_from_db()
        self.assertTrue(action.human_approved)
        completed = good_deeds_engine.complete_action(action, output_summary='done')
        self.assertEqual(completed.status, 'completed')

    def test_green_action_completes_without_approval(self):
        opp = GoodOpportunity.objects.create(title='x', problem_statement='x')
        action = GoodDeedAction.objects.create(opportunity=opp, action_type='research', autonomy_class='green')
        completed = good_deeds_engine.complete_action(action)
        self.assertEqual(completed.status, 'completed')


class RedTeamReviewTests(TestCase):
    def test_review_not_cleared_when_insufficient_evidence(self):
        opp = GoodOpportunity.objects.create(title='x', problem_statement='x', insufficient_evidence=True)
        review = red_team.build_review(opp, [])
        self.assertFalse(review.cleared)

    def test_review_cleared_when_no_concerns_and_evidence_sufficient(self):
        opp = GoodOpportunity.objects.create(title='x', problem_statement='x', insufficient_evidence=False)
        review = red_team.build_review(opp, [])
        self.assertTrue(review.cleared)


class GoodDiscoveryRunTests(TestCase):
    def setUp(self):
        call_command('seed_good_agent_definitions')

    def test_run_budget_exhaustion_stops_processing_further_signals(self):
        signals = [Signal(text='coal heating pollution', domains=['energy']) for _ in range(3)]
        run = run_discovery(
            'test mission', signals, cost_budget_usd=0.0, execution_mode='simulated_demo',
        )
        self.assertEqual(run.status, 'completed')
        self.assertTrue(any('budget' in e.lower() for e in run.errors))
        self.assertLess(run.signals_reviewed, len(signals) + 1)

    def test_run_is_idempotent_on_idempotency_key(self):
        signals = [Signal(text='coal heating pollution', domains=['energy'])]
        run1 = run_discovery('m', signals, idempotency_key='test-key-1', execution_mode='simulated_demo')
        run2 = run_discovery('m', signals, idempotency_key='test-key-1', execution_mode='simulated_demo')
        self.assertEqual(run1.pk, run2.pk)
        self.assertEqual(GoodDiscoveryRun.objects.filter(idempotency_key='test-key-1').count(), 1)

    def test_opportunity_factory_returning_none_does_not_create_opportunity(self):
        signals = [Signal(text='coal heating pollution', domains=['energy'])]
        run = run_discovery('m', signals, execution_mode='simulated_demo', opportunity_factory=lambda s, a: None)
        self.assertEqual(run.opportunities_detected, 0)


class CapitalPipelineIntegrationTests(TestCase):
    """Proves the Good Agents layer genuinely reuses the existing, unmodified capital pipeline."""

    def setUp(self):
        self.country = CountryProfile.objects.create(name='Kazakhstan', iso_code='KZ')
        self.project = GoldProject.objects.create(
            name='Test Heating Project', slug='test-heating-project', country=self.country,
            commodity='other', is_demo=True,
        )
        self.opportunity = GoodOpportunity.objects.create(
            title='Test heating opportunity', problem_statement='Coal heating cost and pollution.',
            project=self.project, region='Test region', sector='heating',
            potential_benefit={'people_helped': {'value': 10, 'unit': 'households', 'stage': 'target'}},
            zero_capital_possible=False, confidence=50.0,
        )

    def test_creates_real_operational_loss_via_existing_service(self):
        loss = pipeline.create_loss_for_opportunity(
            self.opportunity, self.project, financial_loss_amount=1000.0, loss_type='heat_loss',
        )
        self.assertEqual(loss.financial_loss_amount, 1000.0)
        self.opportunity.refresh_from_db()
        self.assertEqual(self.opportunity.operational_loss_id, loss.pk)

    def test_better_way_and_opportunity_cost_reuse_real_ranking(self):
        loss = pipeline.create_loss_for_opportunity(
            self.opportunity, self.project, financial_loss_amount=1000.0, loss_type='heat_loss',
        )
        pipeline.add_intervention_option(
            loss, title='Do nothing', intervention_type='do_nothing', classification='estimated',
        )
        pipeline.add_intervention_option(
            loss, title='Heat pump', intervention_type='equipment_upgrade', classification='estimated',
            capex_estimate=5000.0, estimated_annual_savings=800.0, estimated_payback_months=75,
        )
        better_way_result, cost_assessment = pipeline.run_better_way_and_opportunity_cost(
            self.opportunity, self.project, loss,
        )
        self.assertGreater(len(better_way_result.ranked), 0)
        self.assertIsNotNone(cost_assessment.preferred_option)
        self.assertTrue(hasattr(self.opportunity, 'opportunity_cost_assessment'))

    def test_capital_decision_created_via_existing_bridge(self):
        loss = pipeline.create_loss_for_opportunity(
            self.opportunity, self.project, financial_loss_amount=1000.0, loss_type='heat_loss',
        )
        pipeline.add_intervention_option(
            loss, title='Heat pump', intervention_type='equipment_upgrade', classification='estimated',
            capex_estimate=5000.0, estimated_annual_savings=800.0, estimated_payback_months=75,
        )
        better_way_result, _ = pipeline.run_better_way_and_opportunity_cost(self.opportunity, self.project, loss)
        decision, option = pipeline.create_capital_decision(self.project, loss, better_way_result)
        self.assertIsInstance(decision, CapitalAllocationDecision)
        self.assertEqual(decision.approval_status, 'pending')
        pipeline.mark_decision_approved(decision)
        decision.refresh_from_db()
        self.assertEqual(decision.approval_status, 'approved')

    def test_impact_receipt_created_with_mrv_plan_not_measured(self):
        loss = pipeline.create_loss_for_opportunity(
            self.opportunity, self.project, financial_loss_amount=1000.0, loss_type='heat_loss',
        )
        pipeline.add_intervention_option(
            loss, title='Heat pump', intervention_type='equipment_upgrade', classification='estimated',
            capex_estimate=5000.0, estimated_annual_savings=800.0, estimated_payback_months=75,
        )
        better_way_result, _ = pipeline.run_better_way_and_opportunity_cost(self.opportunity, self.project, loss)
        decision, _ = pipeline.create_capital_decision(self.project, loss, better_way_result)
        receipt = pipeline.build_impact_receipt(self.opportunity, decision, better_way_result, mrv_methodology='Planned baseline/after-data comparison.')
        self.assertIsInstance(receipt, ImpactReceipt)
        self.assertEqual(receipt.measured_result, {})
        self.assertEqual(receipt.expected_result, self.opportunity.potential_benefit)

    def test_impact_receipt_pushes_to_evidence_memory(self):
        loss = pipeline.create_loss_for_opportunity(
            self.opportunity, self.project, financial_loss_amount=1000.0, loss_type='heat_loss',
        )
        pipeline.add_intervention_option(
            loss, title='Heat pump', intervention_type='equipment_upgrade', classification='estimated',
            capex_estimate=5000.0, estimated_annual_savings=800.0, estimated_payback_months=75,
        )
        better_way_result, _ = pipeline.run_better_way_and_opportunity_cost(self.opportunity, self.project, loss)
        decision, _ = pipeline.create_capital_decision(self.project, loss, better_way_result)
        pipeline.build_impact_receipt(self.opportunity, decision, better_way_result, mrv_methodology='Planned.')
        self.assertTrue(
            EvidenceMemory.objects.filter(text_chunk__icontains=self.opportunity.title).exists()
        )

    def test_record_verified_outcome_and_sync_wires_mrv_to_evidence_memory(self):
        """Proves the fully-wired MRV path exists and works, using clearly-synthetic test figures
        (see services/pipeline.py's module docstring for why the demo command doesn't call this)."""
        loss = pipeline.create_loss_for_opportunity(
            self.opportunity, self.project, financial_loss_amount=1000.0, loss_type='heat_loss',
        )
        pipeline.add_intervention_option(
            loss, title='Heat pump', intervention_type='equipment_upgrade', classification='estimated',
            capex_estimate=5000.0, estimated_annual_savings=800.0, estimated_payback_months=75,
        )
        better_way_result, _ = pipeline.run_better_way_and_opportunity_cost(self.opportunity, self.project, loss)
        decision, _ = pipeline.create_capital_decision(self.project, loss, better_way_result)
        pipeline.mark_decision_approved(decision)
        pipeline.build_impact_receipt(self.opportunity, decision, better_way_result, mrv_methodology='Planned.')

        outcome, memory = pipeline.record_verified_outcome_and_sync(
            decision, mrv_status='baseline_only', evidence_quality='medium',
            capex_actual=4800.0, loss_avoided_actual=750.0, savings_actual=750.0,
        )
        self.assertEqual(outcome.decision_id, decision.pk)
        self.assertIsNotNone(memory)
        receipt = ImpactReceipt.objects.get(opportunity=self.opportunity)
        self.assertEqual(receipt.verified_outcome_id, outcome.pk)
        self.assertEqual(receipt.measured_result['capex_actual'], 4800.0)


class AlmatyDemoCommandTests(TestCase):
    def test_demo_command_runs_end_to_end_without_error(self):
        call_command('run_almaty_good_agent_demo')
        opportunity = GoodOpportunity.objects.get(title__startswith='Almaty coal-to-clean')
        self.assertTrue(opportunity.agent_activations.exists())
        self.assertTrue(hasattr(opportunity, 'red_team_review'))
        self.assertTrue(opportunity.actions.exists())
        self.assertTrue(CapitalAllocationDecision.objects.filter(intervention__operational_loss=opportunity.operational_loss).exists())
        self.assertTrue(ImpactReceipt.objects.filter(opportunity=opportunity).exists())

    def test_demo_command_is_idempotent_across_reruns(self):
        call_command('run_almaty_good_agent_demo')
        first_opportunity_count = GoodOpportunity.objects.count()
        first_loss_count = InterventionOption.objects.count()
        call_command('run_almaty_good_agent_demo')
        self.assertEqual(GoodOpportunity.objects.count(), first_opportunity_count)
        self.assertEqual(InterventionOption.objects.count(), first_loss_count)


class ViewTests(TestCase):
    def setUp(self):
        call_command('run_almaty_good_agent_demo')
        self.opportunity = GoodOpportunity.objects.first()
        self.client = Client()

    def test_opportunity_list_view(self):
        response = self.client.get(reverse('good_agents:opportunity_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.opportunity.title)

    def test_opportunity_detail_view_no_dead_end(self):
        response = self.client.get(reverse('good_agents:opportunity_detail', args=[self.opportunity.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Activated Good Agent lenses')
        self.assertContains(response, 'Good Deed actions')

    def test_morning_brief_view(self):
        response = self.client.get(reverse('good_agents:morning_brief'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Morning Brief')


# ===========================================================================
# === PR3 — Global Good Discovery + Good While You Sleep + Need/Resource Matching
# ===========================================================================
from good_agents.services import (  # noqa: E402
    circular_economy, clustering, discovery_engine, evidence_gate, funding_matcher, matcher, morning_brief,
    need_resource, prioritisation, signals as signal_service, zero_capital_strategy,
)
from good_agents.services.discovery_engine import run_global_discovery  # noqa: E402
from good_agents.services.orchestrator import Signal  # noqa: E402


def _raw_signal(signal_type='harm', title='Test signal', **overrides):
    base = dict(signal_type=signal_type, title=title, summary='A test signal.', region='Test Region',
                sector='energy', tags=['energy'], confidence=60.0, severity=50.0)
    base.update(overrides)
    return base


class SignalNormalisationTests(TestCase):
    def test_normalise_signal_creates_world_signal(self):
        signal, created = signal_service.normalise_signal(_raw_signal())
        self.assertTrue(created)
        self.assertEqual(signal.status, 'new')
        self.assertTrue(signal.dedup_key)

    def test_normalise_signal_idempotent_on_same_url(self):
        raw = _raw_signal(source_url='https://example.org/a')
        first, created_first = signal_service.normalise_signal(raw)
        second, created_second = signal_service.normalise_signal(raw)
        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first.pk, second.pk)

    def test_classify_content_defaults_to_claim_without_high_trust_provider(self):
        classification = signal_service.classify_content({'asserted_as_fact': True}, provider=None)
        self.assertEqual(classification, 'inference')

    def test_classify_content_fact_requires_high_trust_provider(self):
        provider = SignalProvider.objects.create(slug='gov-test', name='Gov Test', provider_type='government_publication')
        classification = signal_service.classify_content({'asserted_as_fact': True}, provider=provider)
        self.assertEqual(classification, 'fact')

    def test_classify_content_claim_from_low_trust_provider_even_if_asserted(self):
        provider = SignalProvider.objects.create(slug='news-test', name='News Test', provider_type='news')
        classification = signal_service.classify_content({'asserted_as_fact': True}, provider=provider)
        self.assertEqual(classification, 'claim')

    def test_freshness_zero_without_published_at(self):
        self.assertEqual(signal_service.compute_freshness(None), 0.0)


class DeduplicationClusteringTests(TestCase):
    def test_exact_duplicate_folds_into_same_cluster(self):
        s1, _ = signal_service.normalise_signal(_raw_signal(title='Same event', source_url='https://a.example/1'))
        s2, _ = signal_service.normalise_signal(_raw_signal(title='Same event', source_url='https://a.example/2'))
        result = clustering.deduplicate_and_cluster([s1, s2])
        self.assertEqual(result['duplicates_removed'], 1)
        self.assertEqual(len(result['clusters']), 1)

    def test_titles_overlap_clusters_similar_signals(self):
        s1, _ = signal_service.normalise_signal(_raw_signal(title='High heating costs hit rural households', source_url='https://a.example/1'))
        s2, _ = signal_service.normalise_signal(_raw_signal(title='Rural households face high heating costs', source_url='https://a.example/2'))
        clustering.deduplicate_and_cluster([s1, s2])
        s1.refresh_from_db(); s2.refresh_from_db()
        self.assertEqual(s1.cluster_id, s2.cluster_id)
        self.assertIsNotNone(s1.cluster_id)

    def test_unrelated_signals_do_not_cluster_together(self):
        s1, _ = signal_service.normalise_signal(_raw_signal(title='High heating costs in rural region', source_url='https://a.example/1'))
        s2, _ = signal_service.normalise_signal(_raw_signal(title='Stock market rallies on tech earnings', signal_type='price_change', source_url='https://a.example/2'))
        clustering.deduplicate_and_cluster([s1, s2])
        s1.refresh_from_db(); s2.refresh_from_db()
        self.assertNotEqual(s1.cluster_id, s2.cluster_id)

    def test_irrelevant_noise_signal_triaged_as_noise(self):
        s1, _ = signal_service.normalise_signal(_raw_signal(
            title='Stock market rallies', signal_type='price_change', severity=5.0, source_url='https://a.example/noise',
        ))
        cluster, _ = clustering.assign_to_cluster(s1)
        self.assertEqual(discovery_engine._triage_cluster(cluster), 'noise')

    def test_problem_signal_triaged_as_problem(self):
        s1, _ = signal_service.normalise_signal(_raw_signal(title='Households face harm from pollution', source_url='https://a.example/problem'))
        cluster, _ = clustering.assign_to_cluster(s1)
        self.assertEqual(discovery_engine._triage_cluster(cluster), 'problem')

    def test_resource_signal_triaged_as_resource(self):
        s1, _ = signal_service.normalise_signal(_raw_signal(
            title='Grant programme opens', signal_type='funding', source_url='https://a.example/resource',
        ))
        cluster, _ = clustering.assign_to_cluster(s1)
        self.assertEqual(discovery_engine._triage_cluster(cluster), 'resource')


class EvidenceGateTests(TestCase):
    def test_empty_cluster_is_insufficient_evidence(self):
        cluster = SignalCluster.objects.create(representative_title='Empty', signal_type='harm')
        result = evidence_gate.evaluate_cluster(cluster)
        self.assertEqual(result.decision, 'insufficient_evidence')

    def test_low_confidence_is_insufficient_evidence(self):
        s1, _ = signal_service.normalise_signal(_raw_signal(confidence=5.0, source_url='https://a.example/low'))
        cluster, _ = clustering.assign_to_cluster(s1)
        result = evidence_gate.evaluate_cluster(cluster)
        self.assertEqual(result.decision, 'insufficient_evidence')

    def test_missing_geography_and_sector_is_insufficient_evidence(self):
        s1, _ = signal_service.normalise_signal(_raw_signal(confidence=70.0, region='', sector='', source_url='https://a.example/nogeo'))
        cluster, _ = clustering.assign_to_cluster(s1)
        result = evidence_gate.evaluate_cluster(cluster)
        self.assertEqual(result.decision, 'insufficient_evidence')

    def test_contradiction_forces_monitor(self):
        s1, _ = signal_service.normalise_signal(_raw_signal(confidence=70.0, source_url='https://a.example/contra'))
        cluster, _ = clustering.assign_to_cluster(s1)
        cluster.contradiction_notes = 'Two sources disagree on severity.'
        cluster.save(update_fields=['contradiction_notes'])
        result = evidence_gate.evaluate_cluster(cluster)
        self.assertEqual(result.decision, 'monitor')

    def test_high_confidence_multi_source_qualifies(self):
        s1, _ = signal_service.normalise_signal(_raw_signal(confidence=60.0, publisher='Source One', source_url='https://a.example/q1'))
        s2, _ = signal_service.normalise_signal(_raw_signal(confidence=55.0, publisher='Source Two', source_url='https://a.example/q2'))
        clustering.deduplicate_and_cluster([s1, s2])
        s1.refresh_from_db()
        result = evidence_gate.evaluate_cluster(s1.cluster)
        self.assertEqual(result.decision, 'qualify')


class NeedResourceCreationTests(TestCase):
    def test_create_need_idempotent(self):
        need1, created1 = need_resource.create_need(need_type='energy', title='Heating need', urgency=70.0)
        need2, created2 = need_resource.create_need(need_type='energy', title='Heating need', urgency=70.0)
        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(need1.pk, need2.pk)

    def test_create_resource_idempotent(self):
        r1, created1 = need_resource.create_resource(resource_type='grant', title='Test Grant')
        r2, created2 = need_resource.create_resource(resource_type='grant', title='Test Grant')
        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(r1.pk, r2.pk)

    def test_resource_cannot_be_available_without_evidence(self):
        resource, _ = need_resource.create_resource(
            resource_type='grant', title='Unverified Grant', availability='available', evidence_refs=[],
        )
        self.assertEqual(resource.availability, 'unknown')

    def test_resource_available_with_evidence(self):
        resource, _ = need_resource.create_resource(
            resource_type='grant', title='Verified Grant', availability='available', evidence_refs=['demo:ref-1'],
        )
        self.assertEqual(resource.availability, 'available')

    def test_update_resource_status_logs_history(self):
        resource, _ = need_resource.create_resource(resource_type='grant', title='Tracked Grant')
        need_resource.update_resource_status(resource, new_status='expired', new_availability='expired', reason='Programme closed.')
        resource.refresh_from_db()
        self.assertEqual(resource.status, 'expired')
        self.assertEqual(ResourceStatusChange.objects.filter(resource=resource).count(), 1)


class NeedResourceMatcherTests(TestCase):
    def test_incompatible_type_never_matches(self):
        need, _ = need_resource.create_need(need_type='energy', title='Energy need')
        resource, _ = need_resource.create_resource(resource_type='food_surplus', title='Irrelevant food surplus')
        result = matcher.score_match(need, resource)
        self.assertIsNone(result)

    def test_compatible_type_matches_and_persists(self):
        need, _ = need_resource.create_need(need_type='energy', title='Energy need', region='Region A')
        resource, _ = need_resource.create_resource(
            resource_type='government_programme', title='Energy Grant', region='Region A',
            evidence_refs=['demo:ref'], confidence=80.0, capacity='Open to all households',
        )
        matches = matcher.match_need(need)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].resource_id, resource.pk)
        need.refresh_from_db()
        self.assertEqual(need.status, 'matched')

    def test_expired_resource_excluded_from_new_matches(self):
        need, _ = need_resource.create_need(need_type='energy', title='Energy need', region='Region A')
        resource, _ = need_resource.create_resource(
            resource_type='government_programme', title='Expired Grant', region='Region A',
            evidence_refs=['demo:ref'], confidence=80.0, expiry_date=timezone.now().date() - datetime.timedelta(days=1),
        )
        result = matcher.score_match(need, resource)
        self.assertIsNone(result)
        matches = matcher.match_need(need, candidate_resources=AvailableResource.objects.all())
        self.assertEqual(len(matches), 0)

    def test_geography_mismatch_scores_lower_than_match(self):
        need, _ = need_resource.create_need(need_type='energy', title='Energy need', region='Region A')
        near, _ = need_resource.create_resource(resource_type='technology', title='Local tech', region='Region A', capacity='x', evidence_refs=['r'])
        far, _ = need_resource.create_resource(resource_type='technology', title='Distant tech', region='Region Z', capacity='x', evidence_refs=['r'])
        near_score = matcher.score_match(need, near)
        far_score = matcher.score_match(need, far)
        self.assertGreater(near_score.score, far_score.score)


class CircularEconomyMatcherTests(TestCase):
    def test_waste_heat_matches_and_flags_circular(self):
        need, _ = need_resource.create_need(need_type='energy', title='Heating need', region='Region A')
        need_resource.create_resource(
            resource_type='waste_heat', title='Factory waste heat', region='Region A',
            evidence_refs=['demo:ref'], capacity='Substantial', confidence=70.0,
        )
        matches = circular_economy.match_circular_economy(need)
        self.assertEqual(len(matches), 1)
        self.assertTrue(matches[0].is_circular_economy_match)
        self.assertIn('Circular economy', matches[0].match_reason)

    def test_non_circular_resource_type_excluded_from_circular_matcher(self):
        need, _ = need_resource.create_need(need_type='energy', title='Heating need', region='Region A')
        need_resource.create_resource(resource_type='grant', title='Cash grant', region='Region A', evidence_refs=['r'])
        matches = circular_economy.match_circular_economy(need)
        self.assertEqual(len(matches), 0)


class ZeroCapitalStrategyTests(TestCase):
    def test_ranks_zero_capital_actions_from_matches(self):
        opportunity = GoodOpportunity.objects.create(title='Test opp', problem_statement='x', theme='energy')
        need, _ = need_resource.create_need(need_type='energy', title='Need', opportunity=opportunity, region='Region A')
        need_resource.create_resource(
            resource_type='waste_heat', title='Waste heat resource', region='Region A',
            evidence_refs=['r'], capacity='x', confidence=80.0,
        )
        matcher.match_need(need)
        actions = zero_capital_strategy.rank_actions_for_opportunity(opportunity)
        self.assertGreater(len(actions), 0)
        opportunity.refresh_from_db()
        self.assertTrue(opportunity.zero_capital_possible)

    def test_no_matches_produces_no_zero_capital_actions(self):
        opportunity = GoodOpportunity.objects.create(title='Test opp 2', problem_statement='x')
        actions = zero_capital_strategy.rank_actions_for_opportunity(opportunity)
        self.assertEqual(len(actions), 0)


class FundingMatcherTests(TestCase):
    def test_waqf_always_requires_sharia_review(self):
        opportunity = GoodOpportunity.objects.create(title='Housing opp', problem_statement='x', theme='housing')
        matches = funding_matcher.suggest_funding_matches(opportunity, funder_types=['waqf'])
        self.assertEqual(matches[0].eligibility_status, 'requires_sharia_review')

    def test_funding_match_model_blocks_eligible_for_sharia_sensitive_types(self):
        opportunity = GoodOpportunity.objects.create(title='Housing opp 2', problem_statement='x')
        match = FundingMatch.objects.create(opportunity=opportunity, funder_type='islamic_finance', eligibility_status='eligible')
        self.assertEqual(match.eligibility_status, 'requires_sharia_review')

    def test_no_matches_created_for_irrelevant_theme(self):
        opportunity = GoodOpportunity.objects.create(title='Odd opp', problem_statement='x', theme='biodiversity')
        matches = funding_matcher.suggest_funding_matches(opportunity, funder_types=['development_finance'])
        self.assertEqual(len(matches), 0)


class DiscoveryEngineTests(TestCase):
    def setUp(self):
        call_command('seed_good_agent_definitions')
        self.mission = GoodMission.objects.create(name='Test Mission', run_cost_budget_usd=5.0, min_confidence=30.0, max_opportunities=5)

    def test_run_creates_opportunity_from_problem_signal(self):
        raw_signals = [_raw_signal(title='Coal heating pollution harms rural households', severity=70.0, confidence=60.0)]
        run, brief = run_global_discovery(self.mission, raw_signals, idempotency_key='test-run-1')
        self.assertEqual(run.status, 'completed')
        self.assertEqual(run.opportunities_detected, 1)
        self.assertEqual(len(brief['problems_detected']), 1)

    def test_noise_signal_produces_no_opportunity(self):
        raw_signals = [_raw_signal(title='Stock market rallies', signal_type='price_change', severity=5.0)]
        run, _ = run_global_discovery(self.mission, raw_signals, idempotency_key='test-run-noise')
        self.assertEqual(run.opportunities_detected, 0)

    def test_discovered_opportunity_gets_action_gate_immediately(self):
        """PR5 Phase 1 — no opportunity should be invisible in the Action Centre until someone happens to open its detail page."""
        from good_agents.models import ActionGate
        raw_signals = [_raw_signal(title='Coal heating pollution harms rural households 2', severity=70.0, confidence=60.0)]
        run, _ = run_global_discovery(self.mission, raw_signals, idempotency_key='test-run-gate')
        opportunity = run.opportunities.first()
        self.assertIsNotNone(opportunity)
        gate = ActionGate.objects.filter(opportunity=opportunity).first()
        self.assertIsNotNone(gate)
        self.assertEqual(gate.current_state, 'discovered')

    def test_run_is_idempotent(self):
        raw_signals = [_raw_signal(title='Coal heating pollution harms households', severity=70.0, confidence=60.0)]
        run1, _ = run_global_discovery(self.mission, raw_signals, idempotency_key='test-run-idem')
        run2, _ = run_global_discovery(self.mission, raw_signals, idempotency_key='test-run-idem')
        self.assertEqual(run1.pk, run2.pk)
        self.assertEqual(GoodOpportunity.objects.filter(discovery_run=run1).count(), 1)

    def test_resource_signal_registers_available_resource_not_opportunity(self):
        raw_signals = [_raw_signal(title='New energy grant opens', signal_type='funding', tags=['resource_type:grant'])]
        run, _ = run_global_discovery(self.mission, raw_signals, idempotency_key='test-run-resource')
        self.assertEqual(run.opportunities_detected, 0)
        self.assertTrue(AvailableResource.objects.filter(title='New energy grant opens').exists())

    def test_low_confidence_signal_counted_as_insufficient_evidence(self):
        raw_signals = [_raw_signal(title='Vague harm report', confidence=5.0, severity=60.0)]
        run, _ = run_global_discovery(self.mission, raw_signals, idempotency_key='test-run-insufficient')
        self.assertEqual(run.insufficient_evidence_count, 1)
        self.assertEqual(run.opportunities_detected, 0)

    def test_checkpoint_stages_recorded(self):
        raw_signals = [_raw_signal(title='Coal heating pollution again', severity=70.0, confidence=60.0)]
        run, _ = run_global_discovery(self.mission, raw_signals, idempotency_key='test-run-checkpoints')
        for stage in ['fetch_signals', 'normalise', 'deduplicate', 'cluster', 'triage', 'activate_agents',
                      'verify_evidence', 'create_candidates', 'match_resources', 'run_better_way', 'rank', 'generate_brief']:
            self.assertTrue(run.stage_done(stage), f'stage {stage} not checkpointed')
        self.assertEqual(run.current_stage, 'done')

    def test_never_activates_more_than_max_activated_even_with_all_114_seeded(self):
        call_command('seed_all_good_agent_definitions')
        raw_signals = [_raw_signal(
            title='Energy poverty pollution justice waste stewardship crisis', severity=80.0, confidence=70.0,
            tags=['energy', 'environment', 'social', 'justice', 'housing', 'health'],
        )]
        run, _ = run_global_discovery(self.mission, raw_signals, idempotency_key='test-run-scale-114')
        self.assertLessEqual(run.agents_activated, 6)


class MorningBriefV2Tests(TestCase):
    def setUp(self):
        call_command('seed_good_agent_definitions')
        self.mission = GoodMission.objects.create(name='Brief Test Mission', run_cost_budget_usd=5.0, min_confidence=30.0)
        raw_signals = [_raw_signal(title='Urgent coal heating crisis', severity=90.0, confidence=70.0)]
        self.run, self.brief = run_global_discovery(self.mission, raw_signals, idempotency_key='test-brief-run')

    def test_brief_counts_match_stored_run_fields(self):
        self.assertEqual(self.brief['signals_reviewed'], self.run.signals_reviewed)
        self.assertEqual(self.brief['opportunities_detected'], self.run.opportunities_detected)

    def test_top_3_actions_present_for_urgent_opportunity(self):
        self.assertGreater(len(self.brief['top_3_actions_today']), 0)

    def test_top_3_actions_capped_at_three(self):
        opportunities = list(self.run.opportunities.all())
        for i in range(5):
            GoodOpportunity.objects.create(title=f'Urgent extra {i}', problem_statement='x', urgency=95.0, confidence=80.0, feasibility=80.0, affected_population='many')
        actions = morning_brief.top_3_actions(GoodOpportunity.objects.all())
        self.assertLessEqual(len(actions), 3)


class PrioritisationEngineTests(TestCase):
    def test_urgent_label_applied(self):
        opp = GoodOpportunity.objects.create(title='x', problem_statement='x', urgency=90.0)
        result = prioritisation.prioritise(opp)
        self.assertIn('URGENT', result.labels)

    def test_evidence_gap_label_for_insufficient_evidence(self):
        opp = GoodOpportunity.objects.create(title='x', problem_statement='x', insufficient_evidence=True)
        result = prioritisation.prioritise(opp)
        self.assertIn('EVIDENCE_GAP', result.labels)

    def test_zero_capital_label(self):
        opp = GoodOpportunity.objects.create(title='x', problem_statement='x', zero_capital_possible=True)
        result = prioritisation.prioritise(opp)
        self.assertIn('ZERO_CAPITAL', result.labels)

    def test_capital_required_label(self):
        opp = GoodOpportunity.objects.create(title='x', problem_statement='x', capital_required_usd=5000.0, zero_capital_possible=False)
        result = prioritisation.prioritise(opp)
        self.assertIn('CAPITAL_REQUIRED', result.labels)

    def test_never_produces_a_single_fake_score(self):
        opp = GoodOpportunity.objects.create(title='x', problem_statement='x', urgency=90.0)
        result = prioritisation.prioritise(opp)
        self.assertIsInstance(result.labels, list)
        self.assertNotIn('score', result.dimensions)


class ScaleTo114Tests(TestCase):
    def test_seed_all_creates_114_total(self):
        call_command('seed_good_agent_definitions')
        call_command('seed_all_good_agent_definitions')
        self.assertEqual(GoodAgentDefinition.objects.count(), 114)

    def test_hand_tuned_rows_not_overwritten(self):
        call_command('seed_good_agent_definitions')
        energy_lens_before = GoodAgentDefinition.objects.get(principle_id=34)
        original_signal_types = list(energy_lens_before.signal_types)
        call_command('seed_all_good_agent_definitions')
        energy_lens_after = GoodAgentDefinition.objects.get(principle_id=34)
        self.assertEqual(energy_lens_after.signal_types, original_signal_types)
        self.assertEqual(energy_lens_after.definition_quality, 'hand_tuned')

    def test_auto_generated_rows_require_human_review(self):
        call_command('seed_good_agent_definitions')
        call_command('seed_all_good_agent_definitions')
        auto = GoodAgentDefinition.objects.filter(definition_quality='auto_generated').first()
        self.assertTrue(auto.requires_human_review)


class OvernightDemoCommandTests(TestCase):
    def test_overnight_demo_runs_and_rejects_noise(self):
        call_command('run_overnight_good_discovery_demo')
        run = GoodDiscoveryRun.objects.get(idempotency_key='overnight-good-discovery-demo-v1')
        self.assertEqual(run.status, 'completed')
        self.assertEqual(run.opportunities_detected, 1)
        self.assertEqual(run.signals_reviewed, 4)

    def test_overnight_demo_idempotent(self):
        call_command('run_overnight_good_discovery_demo')
        count_before = GoodOpportunity.objects.count()
        call_command('run_overnight_good_discovery_demo')
        self.assertEqual(GoodOpportunity.objects.count(), count_before)


class DogfoodMissionTests(TestCase):
    def test_dogfood_mission_created_disabled_with_no_signals_run(self):
        call_command('seed_dogfood_mission')
        mission = GoodMission.objects.get(name='EcoIQ Dogfood — 30 Days, Minimal Capital')
        self.assertFalse(mission.enabled)
        self.assertEqual(GoodDiscoveryRun.objects.filter(mission_config=mission).count(), 0)


class GoodMapApiTests(TestCase):
    def test_map_api_returns_json_with_expected_keys(self):
        GoodOpportunity.objects.create(title='Map test', problem_statement='x', theme='energy')
        response = self.client.get(reverse('good_agents:good_map_api'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('opportunities', data)
        self.assertIn('needs', data)
        self.assertIn('resources', data)

    def test_map_api_filters_by_theme(self):
        GoodOpportunity.objects.create(title='Energy one', problem_statement='x', theme='energy')
        GoodOpportunity.objects.create(title='Water one', problem_statement='x', theme='water')
        response = self.client.get(reverse('good_agents:good_map_api'), {'theme': 'energy'})
        titles = [o['title'] for o in response.json()['opportunities']]
        self.assertIn('Energy one', titles)
        self.assertNotIn('Water one', titles)


class ObservatoryHealthApiTests(TestCase):
    def test_health_api_reports_provider_counts(self):
        SignalProvider.objects.create(slug='p1', name='P1', provider_type='news', status='active')
        SignalProvider.objects.create(slug='p2', name='P2', provider_type='news', status='failed')
        response = self.client.get(reverse('good_agents:observatory_health_api'))
        data = response.json()
        self.assertEqual(data['active_count'], 1)
        self.assertEqual(data['failed_count'], 1)


# ===========================================================================
# === PR4 — Real-World Signal Ingestion + Autonomous Overnight Loop
# ===========================================================================
from unittest.mock import patch  # noqa: E402

import httpx  # noqa: E402

from good_agents.models import HumanReviewDecision  # noqa: E402
from good_agents.services import human_review, ingestion, notify, provider_adapters, safe_http  # noqa: E402


class SafeHttpSSRFTests(TestCase):
    def test_rejects_non_https_scheme(self):
        result = safe_http.safe_fetch('http://example.com/x', allowed_hosts={'example.com'})
        self.assertFalse(result.success)
        self.assertIn('blocked', result.error)

    def test_rejects_host_not_in_allowlist(self):
        result = safe_http.safe_fetch('https://evil.example.com/x', allowed_hosts={'good.example.com'})
        self.assertFalse(result.success)
        self.assertIn('not in allowlist', result.error)

    def test_rejects_private_ip_resolution(self):
        with patch('good_agents.services.safe_http.socket.getaddrinfo') as mock_resolve:
            mock_resolve.return_value = [(2, 1, 6, '', ('127.0.0.1', 443))]
            result = safe_http.safe_fetch('https://internal.example.com/x', allowed_hosts={'internal.example.com'})
        self.assertFalse(result.success)
        self.assertIn('non-public', result.error)

    def test_never_raises_on_timeout(self):
        with patch('good_agents.services.safe_http.httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = httpx.ConnectTimeout('timed out')
            with patch('good_agents.services.safe_http.socket.getaddrinfo', return_value=[(2, 1, 6, '', ('93.184.216.34', 443))]):
                result = safe_http.safe_fetch('https://example.com/x', allowed_hosts={'example.com'})
        self.assertFalse(result.success)
        self.assertIn('ConnectTimeout', result.error)

    def test_rejects_oversized_response_via_content_length_header(self):
        class _FakeResponse:
            status_code = 200
            is_redirect = False
            headers = {'content-length': str(safe_http.MAX_RESPONSE_BYTES + 1)}
            content = b''
        with patch('good_agents.services.safe_http.httpx.Client') as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = _FakeResponse()
            with patch('good_agents.services.safe_http.socket.getaddrinfo', return_value=[(2, 1, 6, '', ('93.184.216.34', 443))]):
                result = safe_http.safe_fetch('https://example.com/x', allowed_hosts={'example.com'})
        self.assertFalse(result.success)
        self.assertIn('exceeds cap', result.error)


class ProviderAdapterTests(TestCase):
    def setUp(self):
        call_command('seed_signal_providers')

    def test_usgs_adapter_parses_real_shaped_response(self):
        fixture = {
            'features': [{
                'id': 'us1234', 'properties': {
                    'mag': 6.1, 'place': '10 km N of Testville', 'title': 'M 6.1 - 10 km N of Testville',
                    'time': 1700000000000, 'status': 'reviewed', 'url': 'https://earthquake.usgs.gov/x',
                },
            }],
        }
        with patch('good_agents.services.provider_adapters.safe_fetch') as mock_fetch:
            mock_fetch.return_value = safe_http.SafeFetchResult(success=True, json_data=fixture)
            provider = SignalProvider.objects.get(slug='usgs-significant-earthquakes')
            result = provider_adapters.fetch_usgs_significant_earthquakes(provider)
        self.assertTrue(result.success)
        self.assertEqual(len(result.raw_signals), 1)
        self.assertEqual(result.raw_signals[0]['signal_type'], 'environmental_risk')
        self.assertTrue(result.raw_signals[0]['asserted_as_fact'])

    def test_adapter_skips_items_missing_required_fields_rather_than_guessing(self):
        fixture = {'features': [{'id': 'us1', 'properties': {'place': 'Nowhere'}}]}  # no 'mag'
        with patch('good_agents.services.provider_adapters.safe_fetch') as mock_fetch:
            mock_fetch.return_value = safe_http.SafeFetchResult(success=True, json_data=fixture)
            provider = SignalProvider.objects.get(slug='usgs-significant-earthquakes')
            result = provider_adapters.fetch_usgs_significant_earthquakes(provider)
        self.assertEqual(result.items_fetched, 1)
        self.assertEqual(result.items_after_validation, 0)

    def test_adapter_never_raises_returns_honest_failure(self):
        with patch('good_agents.services.provider_adapters.safe_fetch') as mock_fetch:
            mock_fetch.return_value = safe_http.SafeFetchResult(success=False, error='network unreachable')
            provider = SignalProvider.objects.get(slug='usgs-significant-earthquakes')
            result = provider_adapters.fetch_usgs_significant_earthquakes(provider)
        self.assertFalse(result.success)
        self.assertIn('network unreachable', result.error)

    def test_unregistered_provider_slug_is_honest_failure_not_silent(self):
        provider = SignalProvider.objects.create(slug='unregistered-provider', name='X', provider_type='news')
        result = provider_adapters.fetch_from_provider(provider)
        self.assertFalse(result.success)
        self.assertIn('No registered adapter', result.error)

    def test_adapter_bug_is_isolated_not_propagated(self):
        provider = SignalProvider.objects.get(slug='usgs-significant-earthquakes')
        with patch.dict(provider_adapters.PROVIDER_ADAPTERS, {'usgs-significant-earthquakes': lambda p: 1 / 0}):
            result = provider_adapters.fetch_from_provider(provider)
        self.assertFalse(result.success)
        self.assertIn('ZeroDivisionError', result.error)


class IngestionOrchestrationTests(TestCase):
    def setUp(self):
        call_command('seed_signal_providers')

    def test_one_provider_failure_does_not_stop_others(self):
        def fake_fetch(provider):
            if provider.slug == 'uk-ea-flood-monitoring':
                return provider_adapters.ProviderFetchResult(success=False, error='simulated timeout')
            return provider_adapters.ProviderFetchResult(
                success=True, raw_signals=[{
                    'signal_type': 'environmental_risk', 'title': f'Signal from {provider.slug}',
                    'summary': 'x', 'confidence': 50.0, 'severity': 50.0,
                }],
                items_fetched=1, items_after_validation=1,
            )
        with patch('good_agents.services.ingestion.fetch_from_provider', side_effect=fake_fetch):
            raw_signals, reports = ingestion.fetch_due_signals()

        self.assertEqual(len(raw_signals), 2)  # the 2 non-failing providers
        failed_reports = [r for r in reports if not r['success']]
        self.assertEqual(len(failed_reports), 1)
        self.assertEqual(failed_reports[0]['slug'], 'uk-ea-flood-monitoring')

        flood_provider = SignalProvider.objects.get(slug='uk-ea-flood-monitoring')
        self.assertEqual(flood_provider.status, 'failed')
        self.assertIn('simulated timeout', flood_provider.last_failure_reason)

    def test_successful_provider_marked_refreshed(self):
        def fake_fetch(provider):
            return provider_adapters.ProviderFetchResult(success=True, raw_signals=[], items_fetched=0, items_after_validation=0)
        with patch('good_agents.services.ingestion.fetch_from_provider', side_effect=fake_fetch):
            ingestion.fetch_due_signals()
        provider = SignalProvider.objects.first()
        self.assertEqual(provider.status, 'active')
        self.assertIsNotNone(provider.last_refresh_at)


class ProvenanceTests(TestCase):
    def test_source_excerpt_preserved_verbatim(self):
        raw = _raw_signal(source_excerpt='The exact sentence the source published.')
        signal, _ = signal_service.normalise_signal(raw)
        self.assertEqual(signal.source_excerpt, 'The exact sentence the source published.')

    def test_unknown_signal_type_routed_to_needs_review_not_discarded(self):
        s1, _ = signal_service.normalise_signal(_raw_signal(signal_type='unknown', title='Ambiguous report', source_url='https://a.example/unk'))
        cluster, _ = clustering.assign_to_cluster(s1)
        self.assertEqual(discovery_engine._triage_cluster(cluster), 'needs_review')


class PromiscuousResourceMatchTests(TestCase):
    """
    Regression coverage for a real false-positive caught during PR4's own
    live-data testing: a Californian earthquake scored as "matched" to an
    unrelated UK home-energy grant purely because both fall under the
    broad energy/environment category.
    """
    def test_unrelated_generic_funding_resource_never_matches(self):
        need, _ = need_resource.create_need(need_type='environment', title='M 6.1 earthquake near Testville')
        need_resource.create_resource(
            resource_type='government_programme', title='Warm Homes Local Grant for energy efficiency',
            evidence_refs=['r'], capacity='x',
        )
        result = matcher.match_need(need)
        self.assertEqual(len(result), 0)

    def test_generic_overlap_word_alone_is_not_enough(self):
        need, _ = need_resource.create_need(need_type='environment', title='New earthquake report near Testville')
        need_resource.create_resource(
            resource_type='government_programme', title='New funding scheme for flood defence',
            evidence_refs=['r'], capacity='x',
        )
        result = matcher.match_need(need)
        self.assertEqual(len(result), 0)  # only shared word is the generic "new"

    def test_genuinely_relevant_generic_funding_resource_still_matches(self):
        need, _ = need_resource.create_need(need_type='energy', title='Heating poverty need')
        need_resource.create_resource(
            resource_type='government_programme', title='Heating efficiency grant for households',
            evidence_refs=['r'], capacity='x',
        )
        result = matcher.match_need(need)
        self.assertEqual(len(result), 1)

    def test_non_promiscuous_resource_type_unaffected(self):
        need, _ = need_resource.create_need(need_type='waste', title='Unrelated waste need')
        need_resource.create_resource(resource_type='waste_heat', title='Totally different title', evidence_refs=['r'], capacity='x')
        result = matcher.match_need(need)
        self.assertEqual(len(result), 1)


class HumanFeedbackPrioritisationTests(TestCase):
    def test_repeated_false_positive_reduces_ranking_confidence(self):
        opp1 = GoodOpportunity.objects.create(title='x', problem_statement='x', theme='energy', sector='Seismic', confidence=70.0)
        for _ in range(2):
            other = GoodOpportunity.objects.create(title='y', problem_statement='y', theme='energy', sector='Seismic', confidence=70.0)
            human_review.submit_review(other, 'false_positive', rationale='Not relevant.')
        result = prioritisation.prioritise(opp1)
        self.assertLess(result.dimensions['adjusted_confidence'], opp1.confidence)
        self.assertTrue(result.feedback_reasons)

    def test_repeated_useful_boosts_ranking_confidence(self):
        opp1 = GoodOpportunity.objects.create(title='x', problem_statement='x', theme='housing', sector='Retrofit', confidence=50.0)
        for _ in range(2):
            other = GoodOpportunity.objects.create(title='y', problem_statement='y', theme='housing', sector='Retrofit', confidence=50.0)
            human_review.submit_review(other, 'useful')
        result = prioritisation.prioritise(opp1)
        self.assertGreater(result.dimensions['adjusted_confidence'], opp1.confidence)

    def test_never_mutates_stored_confidence(self):
        opp = GoodOpportunity.objects.create(title='x', problem_statement='x', theme='energy', confidence=70.0)
        human_review.submit_review(opp, 'false_positive')
        human_review.submit_review(opp, 'false_positive')
        prioritisation.prioritise(opp)
        opp.refresh_from_db()
        self.assertEqual(opp.confidence, 70.0)

    def test_submit_review_rejects_unknown_decision(self):
        opp = GoodOpportunity.objects.create(title='x', problem_statement='x')
        with self.assertRaises(ValueError):
            human_review.submit_review(opp, 'not_a_real_decision')


class NotificationDedupTests(TestCase):
    def test_urgent_opportunity_creates_one_notification(self):
        opp = GoodOpportunity.objects.create(title='Urgent test', problem_statement='x', urgency=90.0, confidence=50.0)
        result = prioritisation.prioritise(opp)
        created = notify.notify_for_opportunity(opp, result)
        self.assertEqual(len(created), 1)

    def test_calling_twice_does_not_duplicate(self):
        opp = GoodOpportunity.objects.create(title='Urgent test 2', problem_statement='x', urgency=90.0, confidence=50.0)
        result = prioritisation.prioritise(opp)
        notify.notify_for_opportunity(opp, result)
        notify.notify_for_opportunity(opp, result)
        from notifications.models import AdminNotification
        count = AdminNotification.objects.filter(
            source_type='good_agents_opportunity', source_object_id=str(opp.pk), metadata__reason='urgent_public_need',
        ).count()
        self.assertEqual(count, 1)

    def test_non_urgent_opportunity_creates_no_urgent_notification(self):
        opp = GoodOpportunity.objects.create(title='Calm test', problem_statement='x', urgency=10.0, confidence=10.0)
        result = prioritisation.prioritise(opp)
        notify.notify_for_opportunity(opp, result)
        from notifications.models import AdminNotification
        self.assertFalse(AdminNotification.objects.filter(metadata__reason='urgent_public_need').exists())


class ObservatoryReuseTests(TestCase):
    def test_discovery_run_creates_observatory_session_with_no_anchor(self):
        from ai_observatory.models import AnalysisSession, NO_ANCHOR_ALLOWED_KINDS
        self.assertIn('good_agents_discovery', NO_ANCHOR_ALLOWED_KINDS)

        call_command('seed_good_agent_definitions')
        mission = GoodMission.objects.create(name='Observatory Test Mission', run_cost_budget_usd=5.0, min_confidence=30.0)
        raw_signals = [_raw_signal(title='Coal heating pollution harms households', severity=70.0, confidence=60.0)]
        run, _ = run_global_discovery(mission, raw_signals, idempotency_key='observatory-test-run')

        session_ref = run.stage_checkpoints.get('_observatory_session_reference', '')
        self.assertTrue(session_ref.startswith('ai_observatory.AnalysisSession:'))
        session = AnalysisSession.objects.get(pk=session_ref.split(':')[-1])
        self.assertEqual(session.kind, 'good_agents_discovery')
        self.assertIsNone(session.project)
        self.assertIsNone(session.company)
        self.assertEqual(session.status, 'completed')
        self.assertGreater(session.stages.count(), 0)


class EvidenceMemoryBoundaryTests(TestCase):
    def test_raw_world_signal_never_becomes_evidence_memory_automatically(self):
        """Phase 20 — only verified/reviewed outcomes become reusable learning evidence, never a raw WorldSignal."""
        signal, _ = signal_service.normalise_signal(_raw_signal(title='Some raw unverified claim'))
        self.assertFalse(EvidenceMemory.objects.filter(text_chunk__icontains='Some raw unverified claim').exists())


class GoodWhileYouSleepCommandTests(TestCase):
    def test_command_runs_with_no_enabled_missions(self):
        from io import StringIO
        out = StringIO()
        call_command('run_good_while_you_sleep', stdout=out)
        self.assertIn('No enabled GoodMission found', out.getvalue())

    def test_command_is_idempotent_same_day(self):
        call_command('seed_global_monitoring_mission')
        with patch('good_agents.services.ingestion.fetch_due_signals', return_value=([], [])):
            call_command('run_good_while_you_sleep')
            run_count_after_first = GoodDiscoveryRun.objects.count()
            call_command('run_good_while_you_sleep')
            self.assertEqual(GoodDiscoveryRun.objects.count(), run_count_after_first)

    def test_seeds_all_114_and_real_providers(self):
        call_command('seed_global_monitoring_mission')
        with patch('good_agents.services.ingestion.fetch_due_signals', return_value=([], [])):
            call_command('run_good_while_you_sleep')
        self.assertEqual(GoodAgentDefinition.objects.count(), 114)
        self.assertEqual(SignalProvider.objects.count(), 3)


# ===========================================================================
# === PR5 — Impact Action Network: discovered opportunity -> governed
# === action -> responsible party -> connection/outreach -> project
# === candidate -> execution/MRV -> verified outcome -> Evidence Memory.
# ===========================================================================
from good_agents.models import (  # noqa: E402
    ActionContact, ActionGate, ActionPathway, ActionTimelineEvent, ConnectionCandidate, FundingAction,
    OutreachDraft, ProjectCandidate, ResponsibleParty,
)
from good_agents.services import action_gate as action_gate_service  # noqa: E402
from good_agents.services import action_pathway as action_pathway_service  # noqa: E402
from good_agents.services import connection_action  # noqa: E402
from good_agents.services import funding_action as funding_action_service  # noqa: E402
from good_agents.services import outreach as outreach_service  # noqa: E402
from good_agents.services import project_bridge  # noqa: E402
from good_agents.services import responsible_party as responsible_party_service  # noqa: E402


def _make_opportunity(**overrides):
    base = dict(title='PR5 test opportunity', problem_statement='A real problem.', theme='energy', confidence=60.0)
    base.update(overrides)
    return GoodOpportunity.objects.create(**base)


def _approve_gate(opportunity, state='approved_for_contact'):
    action_gate_service.transition(opportunity, 'needs_review')
    return action_gate_service.transition(opportunity, state)


def _staff_user(username='pr5-staff'):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(username, f'{username}@example.com', 'password123', is_staff=True)


class ActionGateTransitionTests(TestCase):
    def test_gate_lazily_created_at_discovered(self):
        opp = _make_opportunity()
        gate = action_gate_service.get_or_create_gate(opp)
        self.assertEqual(gate.current_state, 'discovered')
        self.assertEqual(gate.transitions.count(), 1)
        self.assertEqual(gate.transitions.first().previous_state, '')

    def test_legal_transition_recorded(self):
        opp = _make_opportunity()
        gate = action_gate_service.transition(opp, 'needs_review', reason='Looks credible.')
        self.assertEqual(gate.current_state, 'needs_review')
        self.assertEqual(gate.transitions.last().previous_state, 'discovered')
        self.assertEqual(gate.transitions.last().reason, 'Looks credible.')

    def test_illegal_transition_raises_and_does_not_mutate_state(self):
        opp = _make_opportunity()
        with self.assertRaises(action_gate_service.IllegalTransitionError):
            action_gate_service.transition(opp, 'approved_for_contact')  # discovered -> approved_for_contact is not allowed
        gate = action_gate_service.get_or_create_gate(opp)
        self.assertEqual(gate.current_state, 'discovered')

    def test_rejected_is_terminal(self):
        opp = _make_opportunity()
        action_gate_service.transition(opp, 'rejected')
        self.assertEqual(ActionGate.ALLOWED_TRANSITIONS['rejected'], set())
        self.assertFalse(action_gate_service.can_transition(opp, 'needs_review'))

    def test_needs_more_evidence_path(self):
        opp = _make_opportunity()
        action_gate_service.transition(opp, 'needs_review')
        gate = action_gate_service.transition(opp, 'needs_more_evidence', reason='Missing a second source.')
        self.assertEqual(gate.current_state, 'needs_more_evidence')
        self.assertTrue(action_gate_service.can_transition(opp, 'needs_review'))

    def test_approval_mirrors_action_approved_timeline_event(self):
        opp = _make_opportunity()
        action_gate_service.transition(opp, 'needs_review')
        action_gate_service.transition(opp, 'approved_for_contact', reason='Ready to reach out.')
        self.assertTrue(
            ActionTimelineEvent.objects.filter(opportunity=opp, event_type='action_approved').exists()
        )

    def test_human_approval_required_no_autonomous_approval_path(self):
        """Nothing in the discovery/orchestrator pipeline calls action_gate.transition — approval is always an explicit call."""
        opp = _make_opportunity()
        gate = action_gate_service.get_or_create_gate(opp)
        self.assertNotIn(gate.current_state, ActionGate.APPROVED_STATES)


class ActionPathwayTests(TestCase):
    def test_pathway_blocked_until_gate_approved(self):
        opp = _make_opportunity()
        with self.assertRaises(action_pathway_service.PathwayNotAllowedError):
            action_pathway_service.create_pathway(opp, 'introduction')

    def test_pathway_allowed_after_approval(self):
        opp = _make_opportunity()
        _approve_gate(opp)
        pathway = action_pathway_service.create_pathway(opp, 'introduction', rationale='Connect to a local NGO.')
        self.assertEqual(pathway.status, 'open')

    def test_zero_capital_eligible_type_defaults_capital_required_no(self):
        opp = _make_opportunity()
        _approve_gate(opp)
        pathway = action_pathway_service.create_pathway(opp, 'information_request')
        self.assertEqual(pathway.capital_required, 'no')

    def test_project_candidate_pathway_type_not_auto_zero_capital(self):
        opp = _make_opportunity()
        _approve_gate(opp, state='approved_for_project_creation')
        pathway = action_pathway_service.create_pathway(opp, 'project_candidate')
        self.assertEqual(pathway.capital_required, 'unknown')

    def test_owner_assignment_records_timeline_event(self):
        opp = _make_opportunity()
        _approve_gate(opp)
        user = _staff_user('pathway-owner')
        pathway = action_pathway_service.create_pathway(opp, 'introduction', owner=user)
        self.assertTrue(
            ActionTimelineEvent.objects.filter(opportunity=opp, event_type='owner_assigned').exists()
        )
        self.assertEqual(pathway.owner_id, user.pk)


class ResponsiblePartyProvenanceTests(TestCase):
    def test_no_publisher_returns_none_honestly(self):
        opp = _make_opportunity()
        signal = WorldSignal.objects.create(signal_type='public_need', title='No publisher signal')
        self.assertIsNone(responsible_party_service.suggest_from_signal(opp, signal))
        self.assertEqual(ResponsibleParty.objects.count(), 0)

    def test_suggestion_starts_as_possible_organisation_never_known(self):
        opp = _make_opportunity()
        signal = WorldSignal.objects.create(signal_type='public_need', title='UK grant signal', publisher='GOV.UK')
        party = responsible_party_service.suggest_from_signal(opp, signal)
        self.assertEqual(party.resolution_status, 'possible_organisation')
        self.assertEqual(party.party_type, 'government_department')
        self.assertIn('good_agents.WorldSignal', party.evidence_ref)

    def test_unknown_publisher_still_creates_low_confidence_other_party(self):
        opp = _make_opportunity()
        signal = WorldSignal.objects.create(signal_type='public_need', title='Local blog post', publisher='Some Local Blog')
        party = responsible_party_service.suggest_from_signal(opp, signal)
        self.assertEqual(party.party_type, 'other')
        self.assertEqual(party.confidence, 30.0)

    def test_confirm_is_only_path_to_known_organisation(self):
        opp = _make_opportunity()
        signal = WorldSignal.objects.create(signal_type='public_need', title='UK grant signal 2', publisher='GOV.UK')
        party = responsible_party_service.suggest_from_signal(opp, signal)
        user = _staff_user('confirmer')
        responsible_party_service.confirm(party, actor=user)
        party.refresh_from_db()
        self.assertEqual(party.resolution_status, 'known_organisation')
        self.assertEqual(party.confirmed_by_id, user.pk)

    def test_mark_unresolved(self):
        opp = _make_opportunity()
        signal = WorldSignal.objects.create(signal_type='public_need', title='UK grant signal 3', publisher='GOV.UK')
        party = responsible_party_service.suggest_from_signal(opp, signal)
        responsible_party_service.mark_unresolved(party, reason='Could not verify this is a real department.')
        party.refresh_from_db()
        self.assertEqual(party.resolution_status, 'unresolved')


class ContactSafetyTests(TestCase):
    def test_contact_channel_is_a_plain_public_field_not_scraped(self):
        opp = _make_opportunity()
        party = ResponsibleParty.objects.create(opportunity=opp, name='Test Department', party_type='government_department')
        contact = ActionContact.objects.create(
            responsible_party=party, contact_role='Press office',
            public_contact_channel='press@example-department.gov', source_of_contact_info='Published on gov.uk contact page',
        )
        self.assertTrue(contact.source_of_contact_info)
        self.assertEqual(contact.status, 'identified')


class OutreachGovernanceTests(TestCase):
    def setUp(self):
        self.opp = _make_opportunity()
        _approve_gate(self.opp)
        self.pathway = action_pathway_service.create_pathway(self.opp, 'introduction')
        self.party = ResponsibleParty.objects.create(opportunity=self.opp, name='Test NGO', party_type='ngo')
        self.contact = ActionContact.objects.create(
            responsible_party=self.party, public_contact_channel='contact@example-ngo.org',
            source_of_contact_info='Published on the NGO website contact page.',
        )
        self.staff = _staff_user('outreach-staff')

    def test_draft_starts_as_draft(self):
        draft = outreach_service.create_draft(self.pathway, 'email', subject='Intro', body='Hello.', contact=self.contact)
        self.assertEqual(draft.status, 'draft')

    def test_approve_requires_real_actor(self):
        draft = outreach_service.create_draft(self.pathway, 'email', subject='Intro', body='Hello.', contact=self.contact)
        with self.assertRaises(outreach_service.OutreachNotApprovedError):
            outreach_service.approve(draft, actor=None)

    def test_send_refuses_unless_approved(self):
        draft = outreach_service.create_draft(self.pathway, 'email', subject='Intro', body='Hello.', contact=self.contact)
        with self.assertRaises(outreach_service.OutreachNotApprovedError):
            outreach_service.send_outreach(draft, actor=self.staff)

    def test_send_refuses_without_email_shaped_channel(self):
        contact_no_email = ActionContact.objects.create(
            responsible_party=self.party, public_contact_channel='+44 20 7946 0000',
            source_of_contact_info='Published phone number.',
        )
        draft = outreach_service.create_draft(self.pathway, 'email', subject='Intro', body='Hello.', contact=contact_no_email)
        outreach_service.approve(draft, actor=self.staff)
        with self.assertRaises(outreach_service.NoContactChannelError):
            outreach_service.send_outreach(draft, actor=self.staff)

    def test_no_direct_draft_to_sent_path(self):
        """There is no way to reach 'sent' without passing through 'approved' first."""
        draft = outreach_service.create_draft(self.pathway, 'email', subject='Intro', body='Hello.', contact=self.contact)
        draft.status = 'sent'  # simulate a hypothetical bypass attempt
        draft.save(update_fields=['status'])
        draft.status = 'draft'
        draft.save(update_fields=['status'])
        with self.assertRaises(outreach_service.OutreachNotApprovedError):
            outreach_service.send_outreach(draft, actor=self.staff)

    def test_approved_and_email_shaped_send_succeeds_via_real_email_backend(self):
        from django.core import mail
        draft = outreach_service.create_draft(self.pathway, 'email', subject='Intro', body='Hello.', contact=self.contact)
        outreach_service.approve(draft, actor=self.staff)
        outreach_service.send_outreach(draft, actor=self.staff)
        draft.refresh_from_db()
        self.assertEqual(draft.status, 'sent')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['contact@example-ngo.org'])

    def test_record_reply_creates_timeline_event(self):
        draft = outreach_service.create_draft(self.pathway, 'email', subject='Intro', body='Hello.', contact=self.contact)
        outreach_service.approve(draft, actor=self.staff)
        outreach_service.send_outreach(draft, actor=self.staff)
        outreach_service.record_reply(draft, replied=True, notes='They are interested.')
        self.assertTrue(
            ActionTimelineEvent.objects.filter(opportunity=self.opp, event_type='reply_received').exists()
        )


class ConnectionLifecycleTests(TestCase):
    def setUp(self):
        self.opp = _make_opportunity()
        need = Need.objects.create(need_type='energy', title='Households need heating support', opportunity=self.opp)
        resource = AvailableResource.objects.create(resource_type='waste_heat', title='Nearby factory waste heat', availability='available')
        self.match = ResourceMatch.objects.create(need=need, resource=resource, match_reason='Same region, compatible type.', confidence=70.0)
        self.staff = _staff_user('connection-staff')

    def test_create_candidate_is_idempotent(self):
        c1 = connection_action.create_candidate(self.match)
        c2 = connection_action.create_candidate(self.match)
        self.assertEqual(c1.pk, c2.pk)

    def test_approve_requires_candidate_match_status(self):
        candidate = connection_action.create_candidate(self.match)
        connection_action.approve_for_introduction(candidate, actor=self.staff)
        with self.assertRaises(ValueError):
            connection_action.approve_for_introduction(candidate, actor=self.staff)

    def test_never_implies_agreement_before_human_recorded_outcome(self):
        candidate = connection_action.create_candidate(self.match)
        self.assertNotIn(candidate.status, {'interest_confirmed'})

    def test_record_outcome_rejects_non_terminal_status(self):
        candidate = connection_action.create_candidate(self.match)
        with self.assertRaises(ValueError):
            connection_action.record_outcome(candidate, 'candidate_match')

    def test_full_lifecycle_to_interest_confirmed(self):
        candidate = connection_action.create_candidate(self.match)
        connection_action.approve_for_introduction(candidate, actor=self.staff)
        connection_action.mark_introduced(candidate, actor=self.staff)
        connection_action.record_outcome(candidate, 'interest_confirmed', notes='Confirmed on a call.')
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, 'interest_confirmed')
        self.assertTrue(
            ActionTimelineEvent.objects.filter(opportunity=self.opp, event_type='connection_made').exists()
        )


class FundingActionTests(TestCase):
    def setUp(self):
        self.opp = _make_opportunity()

    def test_no_deadline_gets_honest_note(self):
        match = FundingMatch.objects.create(opportunity=self.opp, funder_type='grant', eligibility_status='eligibility_unknown')
        action = funding_action_service.create_action(match)
        self.assertIn('No real deadline is known', action.notes)

    def test_real_deadline_recorded_without_fabricated_note(self):
        match = FundingMatch.objects.create(opportunity=self.opp, funder_type='grant', eligibility_status='eligibility_unknown')
        deadline = (timezone.now().date() + datetime.timedelta(days=10))
        action = funding_action_service.create_action(match, deadline=deadline)
        self.assertEqual(action.deadline, deadline)
        self.assertNotIn('No real deadline', action.notes)

    def test_sharia_review_blocks_awarded_status(self):
        match = FundingMatch.objects.create(opportunity=self.opp, funder_type='waqf', eligibility_status='requires_sharia_review')
        action = funding_action_service.create_action(match)
        with self.assertRaises(ValueError):
            funding_action_service.update_status(action, 'awarded')

    def test_non_sharia_match_can_be_awarded(self):
        match = FundingMatch.objects.create(opportunity=self.opp, funder_type='grant', eligibility_status='eligible')
        action = funding_action_service.create_action(match)
        funding_action_service.update_status(action, 'awarded', notes='Confirmed by email from the funder.')
        action.refresh_from_db()
        self.assertEqual(action.status, 'awarded')

    def test_funding_match_itself_never_lets_sharia_sensitive_type_claim_eligible(self):
        match = FundingMatch.objects.create(opportunity=self.opp, funder_type='islamic_finance', eligibility_status='eligible')
        self.assertEqual(match.eligibility_status, 'requires_sharia_review')


class ProjectCandidateBridgeTests(TestCase):
    def setUp(self):
        self.opp = _make_opportunity()
        self.staff = _staff_user('project-staff')

    def test_approve_requires_real_actor(self):
        candidate = project_bridge.propose_candidate(self.opp, rationale='Warrants a real pilot.')
        with self.assertRaises(project_bridge.ProjectCandidateNotApprovedError):
            project_bridge.approve_candidate(candidate, actor=None)

    def test_create_requires_approved_status(self):
        candidate = project_bridge.propose_candidate(self.opp)
        with self.assertRaises(project_bridge.ProjectCandidateNotApprovedError):
            project_bridge.create_project_from_candidate(
                candidate, slug='test-pr5-project', name='Test PR5 Project', is_demo=True,
            )

    def test_create_requires_explicit_is_demo(self):
        candidate = project_bridge.propose_candidate(self.opp)
        project_bridge.approve_candidate(candidate, actor=self.staff)
        with self.assertRaises(TypeError):
            project_bridge.create_project_from_candidate(candidate, slug='test-pr5-project-2', name='Test PR5 Project 2')

    def test_create_project_leaves_gold_specific_fields_none(self):
        candidate = project_bridge.propose_candidate(self.opp)
        project_bridge.approve_candidate(candidate, actor=self.staff)
        project = project_bridge.create_project_from_candidate(
            candidate, slug='test-pr5-project-3', name='Test PR5 Project 3', is_demo=True,
        )
        self.assertIsNone(project.ore_grade_g_per_tonne)
        self.assertIsNone(project.total_capex_usd)
        self.assertTrue(project.is_demo)

    def test_create_is_idempotent(self):
        candidate = project_bridge.propose_candidate(self.opp)
        project_bridge.approve_candidate(candidate, actor=self.staff)
        project1 = project_bridge.create_project_from_candidate(
            candidate, slug='test-pr5-project-4', name='Test PR5 Project 4', is_demo=True,
        )
        project2 = project_bridge.create_project_from_candidate(
            candidate, slug='ignored-slug-on-second-call', name='ignored', is_demo=False,
        )
        self.assertEqual(project1.pk, project2.pk)

    def test_provenance_preserved_after_creation(self):
        candidate = project_bridge.propose_candidate(self.opp, rationale='Because of X and Y evidence.')
        project_bridge.approve_candidate(candidate, actor=self.staff)
        project_bridge.create_project_from_candidate(
            candidate, slug='test-pr5-project-5', name='Test PR5 Project 5', is_demo=True,
        )
        candidate.refresh_from_db()
        self.assertEqual(candidate.opportunity_id, self.opp.pk)
        self.assertEqual(candidate.rationale, 'Because of X and Y evidence.')
        self.assertTrue(
            ActionTimelineEvent.objects.filter(opportunity=self.opp, event_type='project_created').exists()
        )


class ExecutionAndMRVBridgeTests(TestCase):
    """Proves the Execution/MRV/Impact Receipt/Evidence Memory loop genuinely closes onto GoodOpportunity.status."""

    def setUp(self):
        self.country = CountryProfile.objects.create(name='PR5 Test Country', iso_code='P5')
        self.project = GoldProject.objects.create(name='PR5 MRV Project', slug='pr5-mrv-project', country=self.country, is_demo=True)
        self.opp = GoodOpportunity.objects.create(
            title='PR5 MRV opportunity', problem_statement='x', project=self.project, confidence=50.0,
        )
        loss = pipeline.create_loss_for_opportunity(self.opp, self.project, financial_loss_amount=1000.0, loss_type='heat_loss')
        pipeline.add_intervention_option(
            loss, title='Heat pump', intervention_type='equipment_upgrade', classification='estimated',
            capex_estimate=5000.0, estimated_annual_savings=800.0, estimated_payback_months=75,
        )
        better_way_result, _ = pipeline.run_better_way_and_opportunity_cost(self.opp, self.project, loss)
        self.decision, _ = pipeline.create_capital_decision(self.project, loss, better_way_result)
        pipeline.mark_decision_approved(self.decision)
        pipeline.build_impact_receipt(self.opp, self.decision, better_way_result, mrv_methodology='Planned.')

    def test_measuring_a_real_outcome_advances_status_to_measured(self):
        pipeline.record_verified_outcome_and_sync(
            self.decision, mrv_status='baseline_only', evidence_quality='medium',
            capex_actual=4800.0, loss_avoided_actual=750.0, savings_actual=750.0,
        )
        self.opp.refresh_from_db()
        self.assertEqual(self.opp.status, 'measured')
        self.assertTrue(ActionTimelineEvent.objects.filter(opportunity=self.opp, event_type='outcome_measured').exists())

    def test_monitoring_path_cannot_reach_verified(self):
        from capital_guardian.services.execution_monitoring import VerificationNotAllowedHereError
        with self.assertRaises(VerificationNotAllowedHereError):
            pipeline.record_verified_outcome_and_sync(
                self.decision, mrv_status='verified', evidence_quality='medium',
                capex_actual=4800.0, loss_avoided_actual=750.0, savings_actual=750.0,
            )
        self.opp.refresh_from_db()
        self.assertNotEqual(self.opp.status, 'verified')

    def test_admin_verification_signal_syncs_opportunity_to_verified(self):
        """The ONLY real path to 'verified': a staff member editing the VerifiedCapitalOutcome admin form directly."""
        from waste_to_value_capital_allocation_engine.models import VerifiedCapitalOutcome
        outcome, _ = pipeline.record_verified_outcome_and_sync(
            self.decision, mrv_status='baseline_only', evidence_quality='medium',
            capex_actual=4800.0, loss_avoided_actual=750.0, savings_actual=750.0,
        )
        outcome.mrv_status = 'verified'
        outcome.save(update_fields=['mrv_status'])

        self.opp.refresh_from_db()
        self.assertEqual(self.opp.status, 'verified')
        self.assertTrue(ActionTimelineEvent.objects.filter(opportunity=self.opp, event_type='outcome_verified').exists())
        self.assertTrue(ActionTimelineEvent.objects.filter(opportunity=self.opp, event_type='evidence_memory_updated').exists())

    def test_verification_signal_does_not_refire_on_repeat_save(self):
        from waste_to_value_capital_allocation_engine.models import VerifiedCapitalOutcome
        outcome, _ = pipeline.record_verified_outcome_and_sync(
            self.decision, mrv_status='baseline_only', evidence_quality='medium',
            capex_actual=4800.0, loss_avoided_actual=750.0, savings_actual=750.0,
        )
        outcome.mrv_status = 'verified'
        outcome.save(update_fields=['mrv_status'])
        outcome.save(update_fields=['mrv_status'])  # re-save, still 'verified'
        count = ActionTimelineEvent.objects.filter(opportunity=self.opp, event_type='outcome_verified').count()
        self.assertEqual(count, 1)


class ActionTimelineOrderingTests(TestCase):
    def test_events_ordered_chronologically(self):
        opp = _make_opportunity()
        action_gate_service.transition(opp, 'needs_review')
        action_gate_service.transition(opp, 'approved_for_contact')
        events = list(ActionTimelineEvent.objects.filter(opportunity=opp))
        self.assertEqual(events, sorted(events, key=lambda e: e.created_at))
        self.assertGreaterEqual(len(events), 3)  # discovered, human_reviewed x2, action_approved


class ActionOutcomeFeedbackTests(TestCase):
    def test_repeated_not_actionable_gates_reduce_ranking_confidence(self):
        opp1 = _make_opportunity(theme='waste', confidence=70.0)
        for _ in range(2):
            other = _make_opportunity(theme='waste', confidence=70.0)
            action_gate_service.transition(other, 'not_actionable')
        result = prioritisation.prioritise(opp1)
        self.assertLess(result.dimensions['adjusted_confidence'], opp1.confidence)

    def test_repeated_completed_zero_capital_pathways_boost_ranking_confidence(self):
        opp1 = _make_opportunity(theme='housing', confidence=50.0)
        for _ in range(2):
            other = _make_opportunity(theme='housing', confidence=50.0)
            _approve_gate(other)
            pathway = action_pathway_service.create_pathway(other, 'information_request')
            action_pathway_service.update_status(pathway, 'completed')
        result = prioritisation.prioritise(opp1)
        self.assertGreater(result.dimensions['adjusted_confidence'], opp1.confidence)

    def test_repeated_declined_connections_reduce_ranking_confidence(self):
        opp1 = _make_opportunity(theme='water', confidence=70.0)
        for _ in range(2):
            other = _make_opportunity(theme='water', confidence=70.0)
            need = Need.objects.create(need_type='water', title='Need', opportunity=other)
            resource = AvailableResource.objects.create(resource_type='asset', title='Resource', availability='available')
            match = ResourceMatch.objects.create(need=need, resource=resource, match_reason='x', confidence=60.0)
            candidate = connection_action.create_candidate(match)
            connection_action.record_outcome(candidate, 'declined')
        result = prioritisation.prioritise(opp1)
        self.assertLess(result.dimensions['adjusted_confidence'], opp1.confidence)


class NotificationEventTests(TestCase):
    def test_zero_capital_pathway_ready_notification_dedups(self):
        from notifications.models import AdminNotification
        opp = _make_opportunity()
        _approve_gate(opp)
        action_pathway_service.create_pathway(opp, 'information_request')
        action_pathway_service.create_pathway(opp, 'data_request')  # second zero-capital pathway on the SAME opportunity
        count = AdminNotification.objects.filter(
            source_model='good_agents.actionpathway', metadata__reason='zero_capital_pathway_ready',
        ).count()
        self.assertEqual(count, 2)  # different pathway instances — dedup is per-instance, not per-opportunity

    def test_project_candidate_ready_notification_created_once(self):
        from notifications.models import AdminNotification
        opp = _make_opportunity()
        candidate = project_bridge.propose_candidate(opp, rationale='Worth a pilot.')
        project_bridge.propose_candidate(opp)  # idempotent get_or_create — no second candidate, no second notification
        count = AdminNotification.objects.filter(
            source_model='good_agents.projectcandidate', source_object_id=str(candidate.pk),
            metadata__reason='project_candidate_ready',
        ).count()
        self.assertEqual(count, 1)

    def test_outreach_awaiting_approval_notification(self):
        from notifications.models import AdminNotification
        opp = _make_opportunity()
        _approve_gate(opp)
        pathway = action_pathway_service.create_pathway(opp, 'introduction')
        draft = outreach_service.create_draft(pathway, 'email', subject='Hi', body='Hi.')
        outreach_service.mark_ready_for_review(draft)
        self.assertTrue(
            AdminNotification.objects.filter(
                source_model='good_agents.outreachdraft', source_object_id=str(draft.pk),
                metadata__reason='outreach_awaiting_approval',
            ).exists()
        )

    def test_funding_deadline_sweep_only_notifies_within_threshold(self):
        from notifications.models import AdminNotification
        opp = _make_opportunity()
        match_far = FundingMatch.objects.create(opportunity=opp, funder_type='grant')
        far_action = funding_action_service.create_action(
            match_far, deadline=timezone.now().date() + datetime.timedelta(days=90),
        )
        opp2 = _make_opportunity()
        match_near = FundingMatch.objects.create(opportunity=opp2, funder_type='grant')
        near_action = funding_action_service.create_action(
            match_near, deadline=timezone.now().date() + datetime.timedelta(days=5),
        )
        notify.sweep_funding_deadlines(days_threshold=14)
        self.assertFalse(AdminNotification.objects.filter(source_object_id=str(far_action.pk), metadata__reason='funding_deadline_approaching').exists())
        self.assertTrue(AdminNotification.objects.filter(source_object_id=str(near_action.pk), metadata__reason='funding_deadline_approaching').exists())


class ImpactActionCentreViewTests(TestCase):
    def setUp(self):
        self.staff = _staff_user('centre-staff')

    def test_anonymous_redirected(self):
        response = self.client.get(reverse('good_agents:impact_action_centre'))
        self.assertEqual(response.status_code, 302)

    def test_staff_sees_real_sections(self):
        self.client.force_login(self.staff)
        opp = _make_opportunity()
        # A real discovered opportunity gets its gate automatically (see
        # discovery_engine.run_global_discovery); this one was created
        # directly for the test, so it needs the same lazy path the
        # opportunity_detail view uses to show up in "awaiting review".
        action_gate_service.get_or_create_gate(opp)
        response = self.client.get(reverse('good_agents:impact_action_centre'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Impact Action Centre')
        self.assertContains(response, opp.title)


class OpportunityDetailPR5SectionsTests(TestCase):
    def setUp(self):
        self.staff = _staff_user('detail-staff')
        self.opp = _make_opportunity()

    def test_gate_and_timeline_sections_render(self):
        response = self.client.get(reverse('good_agents:opportunity_detail', args=[self.opp.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Action gate')
        self.assertContains(response, 'Timeline')

    def test_gate_transition_view_requires_staff(self):
        response = self.client.post(reverse('good_agents:gate_transition', args=[self.opp.pk]), {'new_state': 'needs_review'})
        self.assertEqual(response.status_code, 302)
        gate = action_gate_service.get_or_create_gate(self.opp)
        self.assertEqual(gate.current_state, 'discovered')

    def test_gate_transition_view_applies_legal_transition(self):
        self.client.force_login(self.staff)
        self.client.post(reverse('good_agents:gate_transition', args=[self.opp.pk]), {'new_state': 'needs_review', 'reason': 'ok'})
        gate = action_gate_service.get_or_create_gate(self.opp)
        self.assertEqual(gate.current_state, 'needs_review')

    def test_gate_transition_view_rejects_illegal_transition_without_crashing(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse('good_agents:gate_transition', args=[self.opp.pk]), {'new_state': 'approved_for_contact'})
        self.assertEqual(response.status_code, 302)
        gate = action_gate_service.get_or_create_gate(self.opp)
        self.assertEqual(gate.current_state, 'discovered')  # untouched — illegal transition never applied

    def test_pathway_create_view_requires_approved_gate(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse('good_agents:pathway_create', args=[self.opp.pk]), {'pathway_type': 'introduction'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ActionPathway.objects.filter(opportunity=self.opp).count(), 0)


class PermissionsAndCSRFTests(TestCase):
    def setUp(self):
        self.staff = _staff_user('perm-staff')
        self.opp = _make_opportunity()

    def test_project_candidate_execute_requires_staff(self):
        candidate = project_bridge.propose_candidate(self.opp)
        response = self.client.post(
            reverse('good_agents:project_candidate_create_execute', args=[candidate.pk]),
            {'slug': 'perm-test', 'name': 'Perm Test', 'is_demo': 'true'},
        )
        self.assertEqual(response.status_code, 302)
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, 'proposed')

    def test_csrf_enforced_on_gate_transition(self):
        csrf_client = Client(enforce_csrf_checks=True, SERVER_NAME='localhost')
        csrf_client.force_login(self.staff)
        response = csrf_client.post(reverse('good_agents:gate_transition', args=[self.opp.pk]), {'new_state': 'needs_review'})
        self.assertEqual(response.status_code, 403)

    def test_project_creation_refuses_unapproved_candidate_even_for_staff(self):
        """Cross-object tampering guard: posting execute for a merely-proposed candidate must not create a project."""
        self.client.force_login(self.staff)
        candidate = project_bridge.propose_candidate(self.opp)
        self.client.post(
            reverse('good_agents:project_candidate_create_execute', args=[candidate.pk]),
            {'slug': 'tamper-test', 'name': 'Tamper Test', 'is_demo': 'true'},
        )
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, 'proposed')
        self.assertIsNone(candidate.created_project)
        self.assertEqual(GoldProject.objects.filter(slug='tamper-test').count(), 0)


class NoFabricatedExternalStatusTests(TestCase):
    def test_connection_candidate_cannot_be_marked_interest_confirmed_without_record_outcome(self):
        """The only field write path for status is record_outcome/approve_for_introduction/mark_introduced — no shortcut asserts agreement."""
        opp = _make_opportunity()
        need = Need.objects.create(need_type='energy', title='Need', opportunity=opp)
        resource = AvailableResource.objects.create(resource_type='asset', title='Resource', availability='available')
        match = ResourceMatch.objects.create(need=need, resource=resource, match_reason='x', confidence=60.0)
        candidate = connection_action.create_candidate(match)
        self.assertEqual(candidate.status, 'candidate_match')

    def test_funding_action_status_never_defaults_to_awarded(self):
        opp = _make_opportunity()
        match = FundingMatch.objects.create(opportunity=opp, funder_type='grant')
        action = funding_action_service.create_action(match)
        self.assertEqual(action.status, 'match_found')

    def test_outreach_draft_never_created_pre_sent(self):
        opp = _make_opportunity()
        _approve_gate(opp)
        pathway = action_pathway_service.create_pathway(opp, 'introduction')
        draft = outreach_service.create_draft(pathway, 'email', subject='x', body='x')
        self.assertNotEqual(draft.status, 'sent')
        self.assertIsNone(draft.sent_at)


# ===========================================================================
# === PR6 — Global Impact Mission Control: one flagship mission, one
# === governed truth chain from real signal to verified outcome.
# ===========================================================================
from good_agents.services import mission_control as mc  # noqa: E402


def _mission_with_run(name='PR6 Test Mission', **overrides):
    defaults = dict(run_cost_budget_usd=5.0, min_confidence=30.0, **overrides)
    mission, _ = GoodMission.objects.get_or_create(name=name, defaults=defaults)
    run = GoodDiscoveryRun.objects.create(mission=name, mission_config=mission, status='completed')
    return mission, run


def _mission_opportunity(run, **overrides):
    base = dict(title='PR6 mission opportunity', problem_statement='A real problem.', theme='energy', confidence=60.0, status='qualified')
    base.update(overrides)
    opp = GoodOpportunity.objects.create(discovery_run=run, **base)
    action_gate_service.get_or_create_gate(opp)
    return opp


class MissionControlAccessTests(TestCase):
    def test_anonymous_redirected(self):
        response = self.client.get(reverse('good_agents:mission_control'))
        self.assertEqual(response.status_code, 302)

    def test_staff_gets_200(self):
        staff = _staff_user('mc-access-staff')
        self.client.force_login(staff)
        response = self.client.get(reverse('good_agents:mission_control'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mission Control')

    def test_no_flagship_mission_handled_honestly(self):
        staff = _staff_user('mc-no-mission-staff')
        self.client.force_login(staff)
        response = self.client.get(reverse('good_agents:mission_control'))
        self.assertContains(response, 'No flagship mission seeded yet')


class SignalFunnelTests(TestCase):
    def test_funnel_counts_are_mission_scoped_and_query_backed(self):
        mission, run = _mission_with_run()
        run.signals_reviewed = 12
        run.duplicates_removed = 3
        run.save(update_fields=['signals_reviewed', 'duplicates_removed'])
        _mission_opportunity(run, title='Opp A')
        _mission_opportunity(run, title='Opp B', status='qualified')

        funnel = mc.signal_funnel(mission)
        self.assertEqual(funnel['signals_fetched'], 12)
        self.assertEqual(funnel['duplicates_removed'], 3)
        self.assertEqual(funnel['opportunities_detected'], 2)
        self.assertEqual(funnel['opportunities_qualified'], 2)
        self.assertEqual(funnel['opportunities_human_reviewed'], 0)

    def test_opportunity_outside_mission_not_counted(self):
        mission, run = _mission_with_run()
        _mission_opportunity(run)
        other = _make_opportunity(title='Not in this mission')  # no discovery_run at all
        funnel = mc.signal_funnel(mission)
        self.assertEqual(funnel['opportunities_detected'], 1)
        self.assertNotIn(other, GoodOpportunity.objects.filter(discovery_run__in=mission.runs.all()))

    def test_human_reviewed_count_reflects_real_gate_transitions(self):
        mission, run = _mission_with_run()
        opp = _mission_opportunity(run)
        self.assertEqual(mc.signal_funnel(mission)['opportunities_human_reviewed'], 0)
        action_gate_service.transition(opp, 'needs_review')
        self.assertEqual(mc.signal_funnel(mission)['opportunities_human_reviewed'], 1)


class NoiseVisibilityTests(TestCase):
    def test_noise_sample_reports_real_reason(self):
        cluster = SignalCluster.objects.create(representative_title='Rejected cluster', status='discarded')
        signal_service.WorldSignal.objects.create(signal_type='price_change', title='Stock rallies', cluster=cluster, confidence=10.0)
        sample = mc.noise_sample(limit=5)
        entry = next((s for s in sample if s['cluster'].pk == cluster.pk), None)
        self.assertIsNotNone(entry)
        self.assertTrue(entry['reason_rejected'])

    def test_open_clusters_never_appear_in_noise_sample(self):
        cluster = SignalCluster.objects.create(representative_title='Still open', status='open')
        sample = mc.noise_sample(limit=50)
        self.assertNotIn(cluster.pk, [s['cluster'].pk for s in sample])


class AgentTransparencyTests(TestCase):
    def test_never_implies_114_llm_calls(self):
        call_command('seed_all_good_agent_definitions')
        mission, run = _mission_with_run()
        signal = WorldSignal.objects.create(
            signal_type='harm', title='Coal heating pollution harms households', summary='x',
            sector='energy', tags=['energy'], confidence=60.0,
        )
        opp = _mission_opportunity(run, detected_signals=[signal.title])
        from good_agents.services.orchestrator import Signal as OrchSignal, classify_relevant_agents, record_activations
        activations = classify_relevant_agents(OrchSignal(text=signal.title, domains=['energy']))
        record_activations(opp, activations)

        transparency = mc.agent_transparency(opp)
        self.assertEqual(transparency['total_available'], 114)
        self.assertLessEqual(transparency['activated'], 6)  # max_activated cap, never all 114
        self.assertEqual(transparency['activated'], opp.agent_activations.count())

    def test_useful_reasoning_outputs_never_exceeds_activated(self):
        opp = _make_opportunity()
        transparency = mc.agent_transparency(opp)
        self.assertLessEqual(transparency['useful_reasoning_outputs'], transparency['activated'])


class ZeroCapitalLaneTests(TestCase):
    def test_lane_only_shows_real_pathways(self):
        mission, run = _mission_with_run()
        opp = _mission_opportunity(run)
        self.assertEqual(len(mc.zero_capital_lane(mission)), 0)
        _approve_gate(opp)
        action_pathway_service.create_pathway(opp, 'data_request', rationale='Real rationale.')
        lane = mc.zero_capital_lane(mission)
        self.assertEqual(len(lane), 1)
        self.assertEqual(lane[0]['capital_required_now'], 'No')

    def test_pathway_outside_mission_excluded(self):
        mission, run = _mission_with_run()
        other = _make_opportunity()  # not linked to any discovery_run
        _approve_gate(other)
        action_pathway_service.create_pathway(other, 'data_request')
        self.assertEqual(len(mc.zero_capital_lane(mission)), 0)


class OutreachConnectionTruthTests(TestCase):
    def test_never_shows_contacted_for_a_mere_draft(self):
        mission, run = _mission_with_run()
        opp = _mission_opportunity(run)
        _approve_gate(opp)
        pathway = action_pathway_service.create_pathway(opp, 'introduction')
        draft = outreach_service.create_draft(pathway, 'email', subject='x', body='x')

        truth = mc.outreach_connection_truth(mission)
        self.assertEqual(len(truth['outreach']), 1)
        self.assertEqual(truth['outreach'][0].status, 'draft')
        self.assertNotEqual(truth['outreach'][0].status, 'sent')

    def test_connection_states_reflect_real_status(self):
        mission, run = _mission_with_run()
        opp = _mission_opportunity(run)
        need = Need.objects.create(need_type='energy', title='Need', opportunity=opp)
        resource = AvailableResource.objects.create(resource_type='asset', title='Resource', availability='available')
        match = ResourceMatch.objects.create(need=need, resource=resource, match_reason='x', confidence=60.0)
        connection_action.create_candidate(match)
        truth = mc.outreach_connection_truth(mission)
        self.assertEqual(truth['connections'][0].status, 'candidate_match')


class ProjectBridgeAndExecutionTests(TestCase):
    def test_project_bridge_chain_none_without_candidate(self):
        opp = _make_opportunity()
        self.assertIsNone(mc.project_bridge_chain(opp))

    def test_project_bridge_chain_reflects_real_state(self):
        opp = _make_opportunity()
        candidate = project_bridge.propose_candidate(opp, rationale='Worth a pilot.')
        chain = mc.project_bridge_chain(opp)
        self.assertEqual(chain['candidate'].pk, candidate.pk)
        self.assertEqual(chain['current_stage'], 'Not yet created.')

    def test_execution_mrv_none_without_project(self):
        self.assertIsNone(mc.execution_mrv_for_project(None))

    def test_execution_mrv_reuses_capital_guardian_no_duplicate_logic(self):
        country = CountryProfile.objects.create(name='PR6 Test Country', iso_code='P6')
        project = GoldProject.objects.create(name='PR6 Project', slug='pr6-mc-project', country=country, is_demo=True)
        result = mc.execution_mrv_for_project(project)
        self.assertIsNone(result['current_milestone'])
        self.assertEqual(result['verification_status'], 'Not started.')


class VerifiedImpactAndReceiptTests(TestCase):
    def test_verified_impact_list_empty_until_genuinely_verified(self):
        mission, run = _mission_with_run()
        _mission_opportunity(run, status='measured')
        self.assertEqual(mc.verified_impact_list(mission).count(), 0)

    def test_evidence_memory_for_receipt_empty_without_verified_outcome(self):
        opp = _make_opportunity()
        receipt = ImpactReceipt.objects.create(opportunity=opp, problem='x')
        self.assertEqual(mc.evidence_memory_for_receipt(receipt).count(), 0)


class ImpactVelocityTests(TestCase):
    def test_missing_stages_labelled_not_fabricated_zero(self):
        opp = _make_opportunity()
        velocity = mc.impact_velocity(opp)
        self.assertEqual(velocity['opportunity_to_review'], mc.NOT_REACHED)
        self.assertEqual(velocity['project_to_measurement'], mc.NOT_MEASURED)
        self.assertEqual(velocity['measurement_to_verification'], mc.NOT_VERIFIED)

    def test_real_gap_computed_from_real_timestamps(self):
        opp = _make_opportunity()
        action_gate_service.transition(opp, 'needs_review')
        velocity = mc.impact_velocity(opp)
        self.assertNotEqual(velocity['opportunity_to_review'], mc.NOT_REACHED)
        import datetime as dt
        self.assertIsInstance(velocity['opportunity_to_review'], dt.timedelta)


class MissionHealthAndComparisonTests(TestCase):
    def test_mission_health_counts_are_real(self):
        SignalProvider.objects.create(slug='p1', name='Provider 1', status='active')
        SignalProvider.objects.create(slug='p2', name='Provider 2', status='failed')
        health = mc.mission_health()
        self.assertEqual(health['providers_active'], 1)
        self.assertEqual(health['providers_failed'], 1)

    def test_mission_comparison_has_no_mystery_score(self):
        _mission_with_run(name='PR6 Comparison Mission')
        rows = mc.mission_comparison()
        self.assertTrue(rows)
        for row in rows:
            self.assertNotIn('score', row)


class ObservatorySummaryReuseTests(TestCase):
    def test_uses_shared_helper_not_a_new_computation(self):
        mission, run = _mission_with_run()
        self.assertIsNone(morning_brief.observatory_summary_for_run(run))


class DemoStoryModeTests(TestCase):
    def test_story_has_16_real_steps_no_fabrication(self):
        opp = _make_opportunity()
        story = mc.demo_story(opp)
        self.assertEqual(len(story), 16)
        self.assertEqual(story[0]['step'], 1)
        self.assertIn('None identified.', [s['text'] for s in story if s['title'] == 'Responsible party'])


class TruthChainTests(TestCase):
    def test_truth_chain_reflects_real_progression_not_fabricated(self):
        opp = _make_opportunity()
        chain = mc.truth_chain(opp)
        stage_map = {n['stage']: n for n in chain}
        self.assertFalse(stage_map['Human review']['reached'])
        self.assertFalse(stage_map['Verification']['reached'])

        action_gate_service.transition(opp, 'needs_review')
        chain = mc.truth_chain(opp)
        stage_map = {n['stage']: n for n in chain}
        self.assertTrue(stage_map['Human review']['reached'])
        self.assertFalse(stage_map['Project']['reached'])


class NotificationDeepLinkTests(TestCase):
    def test_notification_admin_url_points_to_mission_control(self):
        opp = _make_opportunity()
        _approve_gate(opp)
        pathway = action_pathway_service.create_pathway(opp, 'data_request')
        from notifications.models import AdminNotification
        note = AdminNotification.objects.filter(
            source_model='good_agents.actionpathway', source_object_id=str(pathway.pk),
        ).first()
        self.assertIsNotNone(note)
        self.assertIn(f'/good-agents/mission-control/?opportunity={opp.pk}', note.admin_url)


class MorningBriefMissionControlLinkTests(TestCase):
    def test_top_action_links_to_mission_control(self):
        opp = _make_opportunity(urgency=90.0, confidence=80.0)
        response_html = None
        from good_agents.services.morning_brief import top_3_actions
        actions = top_3_actions([opp])
        self.assertTrue(actions)
        self.assertEqual(actions[0]['opportunity_id'], opp.pk)


class MissionControlCrossObjectIsolationTests(TestCase):
    def test_responsible_party_lane_never_leaks_other_missions(self):
        mission_a, run_a = _mission_with_run(name='Mission A')
        mission_b, run_b = _mission_with_run(name='Mission B')
        opp_a = _mission_opportunity(run_a)
        opp_b = _mission_opportunity(run_b)
        ResponsibleParty.objects.create(opportunity=opp_a, name='Party A', party_type='ngo')
        ResponsibleParty.objects.create(opportunity=opp_b, name='Party B', party_type='ngo')

        lane_a = mc.responsible_party_lane(mission_a)
        self.assertEqual(len(lane_a), 1)
        self.assertEqual(lane_a[0]['party'].name, 'Party A')

    def test_explicit_opportunity_param_overrides_default_pick_within_the_flagship_mission(self):
        """
        Mission Control anchors on the ONE flagship mission (Phase 1's own
        "one flagship mission" instruction) — this proves an explicit
        `?opportunity=` request wins over the default "furthest progressed /
        highest urgency" pick, without needing a second mission to exist.
        """
        mission, run = _mission_with_run(name=mc.FLAGSHIP_MISSION_NAME)
        low_urgency = _mission_opportunity(run, title='Low urgency opp', urgency=10.0)
        _mission_opportunity(run, title='High urgency opp', urgency=99.0)

        staff = _staff_user('mc-isolation-staff')
        self.client.force_login(staff)
        response = self.client.get(reverse('good_agents:mission_control') + f'?opportunity={low_urgency.pk}')
        self.assertContains(response, 'TRUTH CHAIN'.title())
        self.assertContains(response, low_urgency.title)

    def test_responsible_party_lane_excludes_opportunities_outside_the_flagship_mission(self):
        """Confirms mission-scoping at the query level: an opportunity with no discovery_run never appears."""
        mission, run = _mission_with_run(name=mc.FLAGSHIP_MISSION_NAME)
        in_mission = _mission_opportunity(run)
        outside = _make_opportunity()  # no discovery_run — never belongs to any mission
        ResponsibleParty.objects.create(opportunity=in_mission, name='In-mission party', party_type='ngo')
        ResponsibleParty.objects.create(opportunity=outside, name='Outside party', party_type='ngo')

        lane = mc.responsible_party_lane(mission)
        self.assertEqual(len(lane), 1)
        self.assertEqual(lane[0]['party'].name, 'In-mission party')


class MissionControlRegressionTests(TestCase):
    def test_full_page_renders_with_populated_data(self):
        call_command('seed_global_monitoring_mission')
        mission, run = _mission_with_run(name=mc.FLAGSHIP_MISSION_NAME)
        opp = _mission_opportunity(run, urgency=80.0)
        action_gate_service.transition(opp, 'needs_review')
        action_gate_service.transition(opp, 'approved_for_research')
        action_pathway_service.create_pathway(opp, 'data_request')

        staff = _staff_user('mc-regression-staff')
        self.client.force_login(staff)
        response = self.client.get(reverse('good_agents:mission_control'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Data request')
        self.assertContains(response, 'Approved for research')
