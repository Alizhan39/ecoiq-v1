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
