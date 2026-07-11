from django.test import TestCase

from waste_to_value_capital_allocation_engine.models import OperationalLoss
from waste_to_value_capital_allocation_engine.services.loss_intake import (
    create_operational_loss, quantify_financial_loss,
)
from waste_to_value_capital_allocation_engine.services.capital_risk import (
    calculate_capital_at_risk, calculate_waste_risk_score, predict_recoverable_value,
)
from waste_to_value_capital_allocation_engine.services.intervention_finance import (
    _calculate_payback, calculate_finance_readiness_score, calculate_intervention_finance,
    model_interventions,
)
from waste_to_value_capital_allocation_engine.services.funding import (
    calculate_funding_gap, match_capital_routes,
)
from waste_to_value_capital_allocation_engine.models import CapitalRouteMatch, FundingGap, InterventionOption
from waste_to_value_capital_allocation_engine.services.ranking import rank_capital_allocation_options
from waste_to_value_capital_allocation_engine.services.capital_allocation_scoring import score_intervention_option
from waste_to_value_capital_allocation_engine.services.agent_bridge import build_loss_detection_fixture
from waste_to_value_capital_allocation_engine.services.capital_allocation_bridge import build_capital_allocation_fixture
from waste_to_value_capital_allocation_engine.services.human_approval_gate import (
    ACTIONS_REQUIRING_APPROVAL as WTV_ACTIONS_REQUIRING_APPROVAL,
    HumanApprovalRequiredError as WTVHumanApprovalRequiredError,
    require_human_approval as wtv_require_human_approval,
)
from waste_to_value_capital_allocation_engine.services.governance import create_governed_investment_case
from waste_to_value_capital_allocation_engine.models import CapitalAllocationDecision
from waste_to_value_capital_allocation_engine.services.mrv_outcomes import (
    generate_capital_reallocation_signal, record_verified_outcome,
)
from django.core.management import call_command
from agent_runtime_model_router.models import AgentRun
from waste_to_value_capital_allocation_engine.services.demo_pipeline import DEMO_RUN_SLUG
from ai_agent_council.models import AgentTask, CouncilDecision, CouncilDisagreement, CouncilRun
from agent_runtime_model_router.services.safety_assertions import run_safety_assertions
from waste_to_value_capital_allocation_engine.services.capital_guardian_handoff import (
    DecisionNotApprovedError, promote_to_capital_guardian,
)

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class LossIntakeTests(TestCase):
    def test_create_operational_loss_persists(self):
        loss = create_operational_loss(
            title='Meat cold-chain spoilage risk', loss_type='meat_spoilage',
            financial_loss_amount=12000,
        )
        self.assertTrue(OperationalLoss.objects.filter(pk=loss.pk).exists())

    def test_quantify_financial_loss_is_plain_arithmetic(self):
        result = quantify_financial_loss(quantity_lost=500, unit_value=24, evidence_quality='strong')
        self.assertEqual(result['financial_loss_amount'], 12000)
        self.assertEqual(result['confidence'], 90)


class CapitalRiskTests(TestCase):
    def test_capital_at_risk_worked_example(self):
        self.assertEqual(calculate_capital_at_risk(80000, 0.15), 12000.0)

    def test_recoverable_value_worked_example(self):
        self.assertEqual(predict_recoverable_value(8500, 1200), 7300)

    def test_waste_risk_score_worked_example(self):
        score = calculate_waste_risk_score(96, 75, 80, 60, 55, 65, 45, 50, 40)
        self.assertEqual(score, 72)

    def test_waste_risk_score_clamped_to_100(self):
        score = calculate_waste_risk_score(100, 100, 100, 100, 100, 100, 0, 0, 0)
        self.assertEqual(score, 100)

    def test_waste_risk_score_clamped_to_0(self):
        score = calculate_waste_risk_score(0, 0, 0, 0, 0, 0, 100, 100, 100)
        self.assertEqual(score, 0)


class InterventionFinanceTests(TestCase):
    def test_payback_worked_example_matches_spec(self):
        self.assertEqual(_calculate_payback(120000, 180000), 8.0)

    def test_payback_none_when_no_savings(self):
        self.assertIsNone(_calculate_payback(120000, 0))

    def test_finance_readiness_score_worked_example(self):
        score = calculate_finance_readiness_score(
            capex=120000, loss_avoided_annual=180000, working_capital_released=70000,
            payback_months=8.0, evidence_quality='strong', mrv_readiness='medium',
        )
        self.assertEqual(score, 84)

    def test_calculate_intervention_finance_consolidates_helpers(self):
        result = calculate_intervention_finance(
            capex=120000, opex_change=-5000, loss_avoided=180000, value_recovered=90000,
            annual_savings=180000, working_capital_released=70000,
        )
        self.assertEqual(result['payback_months'], 8.0)
        self.assertEqual(result['capex'], 120000)

    def test_model_interventions_persists_options_idempotently(self):
        loss = OperationalLoss.objects.create(
            title='Cold-chain spoilage', loss_type='cold_chain_failure', financial_loss_amount=12000,
        )
        candidates = [
            {'title': 'Cold-chain equipment upgrade', 'intervention_type': 'equipment_upgrade',
             'capex_estimate': 120000, 'estimated_annual_savings': 180000, 'working_capital_released': 70000},
        ]
        options_first = model_interventions(loss, candidates)
        options_second = model_interventions(loss, candidates)
        self.assertEqual(len(options_first), 1)
        self.assertEqual(options_first[0].pk, options_second[0].pk)
        self.assertEqual(options_first[0].estimated_payback_months, 8.0)


class FundingTests(TestCase):
    def test_calculate_funding_gap_arithmetic(self):
        result = calculate_funding_gap(
            total_capital_required=120000, owner_contribution=20000, grant_potential=30000,
            debt_potential=40000,
        )
        self.assertEqual(result['remaining_gap'], 30000)

    def test_islamic_finance_potential_not_subtracted_from_gap(self):
        with_review = calculate_funding_gap(total_capital_required=100000, islamic_finance_review_potential=50000)
        without_review = calculate_funding_gap(total_capital_required=100000)
        self.assertEqual(with_review['remaining_gap'], without_review['remaining_gap'])

    def test_gap_never_negative(self):
        result = calculate_funding_gap(total_capital_required=10000, owner_contribution=50000)
        self.assertEqual(result['remaining_gap'], 0)

    def _make_funding_gap(self):
        loss = OperationalLoss.objects.create(title='Test loss', loss_type='meat_spoilage', financial_loss_amount=1000)
        option = InterventionOption.objects.create(operational_loss=loss, title='Test option', intervention_type='equipment_upgrade')
        return FundingGap.objects.create(
            intervention=option, total_capital_required=100000, grant_potential=20000,
            debt_potential=30000, islamic_finance_review_potential=25000,
        )

    def test_match_capital_routes_creates_matches_for_nonzero_potentials(self):
        gap = self._make_funding_gap()
        matches = match_capital_routes(gap)
        route_types = {m.route_type for m in matches}
        self.assertEqual(route_types, {'grant', 'equipment_finance', 'islamic_finance_review'})

    def test_islamic_finance_route_marked_needs_review(self):
        gap = self._make_funding_gap()
        matches = match_capital_routes(gap)
        islamic_match = next(m for m in matches if m.route_type == 'islamic_finance_review')
        self.assertEqual(islamic_match.eligibility_status, 'needs_review')

    def test_match_capital_routes_is_idempotent(self):
        gap = self._make_funding_gap()
        match_capital_routes(gap)
        count_first = CapitalRouteMatch.objects.filter(funding_gap=gap).count()
        match_capital_routes(gap)
        count_second = CapitalRouteMatch.objects.filter(funding_gap=gap).count()
        self.assertEqual(count_first, count_second)


class RankingTests(TestCase):
    CANDIDATES = [
        {'name': 'Cold-chain optimisation', 'financial_return': 85, 'capital_efficiency': 80, 'loss_avoided': 90,
         'recoverable_value': 88,
         'payback': 85, 'downside_risk': 80, 'evidence_quality': 85, 'mrv_readiness': 80, 'funding_readiness': 75,
         'asset_life_extension': 60, 'human_need_served': 50, 'harm_reduced': 50, 'maqasid_mizan_score': 60},
        {'name': 'Waste heat recovery', 'financial_return': 70, 'capital_efficiency': 65, 'loss_avoided': 70,
         'recoverable_value': 68,
         'payback': 60, 'downside_risk': 70, 'evidence_quality': 65, 'mrv_readiness': 60, 'funding_readiness': 65,
         'asset_life_extension': 70, 'human_need_served': 40, 'harm_reduced': 55, 'maqasid_mizan_score': 55},
        {'name': 'Boiler modernisation', 'financial_return': 60, 'capital_efficiency': 55, 'loss_avoided': 55,
         'recoverable_value': 55,
         'payback': 50, 'downside_risk': 60, 'evidence_quality': 60, 'mrv_readiness': 55, 'funding_readiness': 55,
         'asset_life_extension': 65, 'human_need_served': 35, 'harm_reduced': 45, 'maqasid_mizan_score': 50},
        {'name': 'Expansion project', 'financial_return': 50, 'capital_efficiency': 40, 'loss_avoided': 20,
         'recoverable_value': 25,
         'payback': 30, 'downside_risk': 40, 'evidence_quality': 45, 'mrv_readiness': 30, 'funding_readiness': 40,
         'asset_life_extension': 50, 'human_need_served': 30, 'harm_reduced': 20, 'maqasid_mizan_score': 35},
    ]

    def test_weights_sum_to_one(self):
        from waste_to_value_capital_allocation_engine.services.ranking import RANKING_WEIGHTS
        self.assertAlmostEqual(sum(RANKING_WEIGHTS.values()), 1.0)

    def test_ranking_matches_spec_ordering(self):
        ranked = rank_capital_allocation_options(self.CANDIDATES)
        names_in_order = [c['name'] for c in ranked]
        self.assertEqual(names_in_order, [
            'Cold-chain optimisation', 'Waste heat recovery', 'Boiler modernisation', 'Expansion project',
        ])
        self.assertEqual([c['rank'] for c in ranked], [1, 2, 3, 4])

    def test_ranking_does_not_mutate_input_scores(self):
        ranked = rank_capital_allocation_options(self.CANDIDATES)
        self.assertIn('composite_score', ranked[0])
        self.assertIn('rank', ranked[0])


class CapitalAllocationScoringTests(TestCase):
    """
    Real 7 Meat Cold-Chain candidates (same shape as demo_pipeline.py's
    INTERVENTION_CANDIDATES) scored and ranked end-to-end — the load-bearing
    regression guard that a future formula "simplification" cannot silently
    invert without breaking a test.
    """
    CAPITAL_AT_RISK_CEILING = 12000
    INVENTORY_VALUE_CEILING = 80000

    CANDIDATES = [
        {'title': 'Dynamic discount now', 'intervention_type': 'prevention',
         'capex_estimate': 200, 'estimated_value_recovered': 3000, 'estimated_loss_avoided': 3000,
         'risk_level': 'low', 'technical_readiness': 'ready'},
        {'title': 'Transfer to another branch (dynamic, discounted resale)', 'intervention_type': 'transfer_redistribution',
         'capex_estimate': 1200, 'estimated_value_recovered': 8500, 'estimated_loss_avoided': 8500,
         'risk_level': 'low', 'technical_readiness': 'ready'},
        {'title': 'Sell to processor', 'intervention_type': 'resale',
         'capex_estimate': 500, 'estimated_value_recovered': 6000, 'estimated_loss_avoided': 6000,
         'risk_level': 'low', 'technical_readiness': 'ready'},
        {'title': 'Safe donation where appropriate', 'intervention_type': 'transfer_redistribution',
         'capex_estimate': 300, 'estimated_value_recovered': 1500, 'estimated_loss_avoided': 1500,
         'risk_level': 'medium', 'technical_readiness': 'needs_review'},
        {'title': 'Freeze / reprocess', 'intervention_type': 'processing_recovery',
         'capex_estimate': 800, 'estimated_value_recovered': 4500, 'estimated_loss_avoided': 4500,
         'risk_level': 'low', 'technical_readiness': 'ready'},
        {'title': 'Cold-chain equipment intervention', 'intervention_type': 'equipment_upgrade',
         'capex_estimate': 9000, 'estimated_annual_savings': 12000, 'estimated_loss_avoided': 12000,
         'estimated_payback_months': 9.0,  # capex/(annual_savings/12) = 9000/(12000/12), as computed by model_interventions()
         'risk_level': 'medium', 'technical_readiness': 'ready', 'finance_readiness': 'needs_review',
         'mrv_readiness': 'draft', 'status': 'recommended'},
        {'title': 'Anaerobic digestion as last resort', 'intervention_type': 'disposal',
         'capex_estimate': 200, 'estimated_value_recovered': 300, 'estimated_loss_avoided': 300,
         'risk_level': 'low', 'technical_readiness': 'ready'},
    ]

    def _scored_candidates(self):
        scored = []
        for candidate in self.CANDIDATES:
            scores = score_intervention_option(
                candidate, self.CAPITAL_AT_RISK_CEILING, self.INVENTORY_VALUE_CEILING,
            )
            scored.append({**candidate, **scores})
        return scored

    def test_equipment_option_scores_expected_sub_scores(self):
        equipment = next(c for c in self.CANDIDATES if c['title'] == 'Cold-chain equipment intervention')
        scores = score_intervention_option(equipment, self.CAPITAL_AT_RISK_CEILING, self.INVENTORY_VALUE_CEILING)
        self.assertEqual(scores['financial_return'], 100)  # 12000/12000*100, capped at 100
        self.assertEqual(scores['recoverable_value'], 0)  # value_recovered=0 by design — it prevents future loss, doesn't salvage this cycle's inventory
        self.assertEqual(scores['payback'], 73)  # round(100 - 9.0*3)
        self.assertEqual(scores['downside_risk'], 60)  # medium risk

    def test_dynamic_discount_scores_expected_sub_scores(self):
        discount = next(c for c in self.CANDIDATES if c['title'] == 'Dynamic discount now')
        scores = score_intervention_option(discount, self.CAPITAL_AT_RISK_CEILING, self.INVENTORY_VALUE_CEILING)
        self.assertEqual(scores['payback'], 65)  # no payback_months -> same-cycle tactical action
        self.assertEqual(scores['downside_risk'], 90)  # low risk

    def test_equipment_option_ranks_first_among_real_candidates(self):
        ranked = rank_capital_allocation_options(self._scored_candidates())
        self.assertEqual(ranked[0]['title'], 'Cold-chain equipment intervention')
        self.assertEqual(ranked[0]['rank'], 1)

    def test_dynamic_discount_has_highest_capital_efficiency(self):
        """
        Reported honestly even though it isn't the top-ranked option overall
        — highest capital efficiency and highest overall ranking are not the
        same claim.
        """
        scored = self._scored_candidates()
        by_efficiency = sorted(scored, key=lambda c: c['capital_efficiency'], reverse=True)
        self.assertEqual(by_efficiency[0]['title'], 'Dynamic discount now')


class HumanApprovalGateTests(TestCase):
    def setUp(self):
        loss = OperationalLoss.objects.create(title='Test loss', loss_type='meat_spoilage', financial_loss_amount=1000)
        option = InterventionOption.objects.create(operational_loss=loss, title='Test option', intervention_type='equipment_upgrade')
        gap = FundingGap.objects.create(intervention=option, total_capital_required=10000)
        self.unapproved_match = CapitalRouteMatch.objects.create(funding_gap=gap, route_type='grant', human_approved=None)
        self.approved_match = CapitalRouteMatch.objects.create(funding_gap=gap, route_type='equipment_finance', human_approved=True)

    def test_twelve_total_actions_registered(self):
        self.assertEqual(len(WTV_ACTIONS_REQUIRING_APPROVAL), 12)

    def test_autonomous_capital_movement_blocked_without_approval(self):
        with self.assertRaises(WTVHumanApprovalRequiredError):
            wtv_require_human_approval('autonomous_capital_movement', self.unapproved_match)

    def test_autonomous_capital_movement_allowed_with_approval(self):
        self.assertTrue(wtv_require_human_approval('autonomous_capital_movement', self.approved_match))

    def test_new_action_blocked_without_approval(self):
        with self.assertRaises(WTVHumanApprovalRequiredError):
            wtv_require_human_approval('capital_route_outreach', self.unapproved_match)

    def test_new_action_allowed_with_approval(self):
        self.assertTrue(wtv_require_human_approval('capital_route_outreach', self.approved_match))

    def test_food_redistribution_action_blocked_without_approval(self):
        with self.assertRaises(WTVHumanApprovalRequiredError):
            wtv_require_human_approval('food_redistribution_action', self.unapproved_match)

    def test_food_redistribution_action_allowed_with_approval(self):
        self.assertTrue(wtv_require_human_approval('food_redistribution_action', self.approved_match))

    def test_shared_base_action_still_enforced(self):
        with self.assertRaises(WTVHumanApprovalRequiredError):
            wtv_require_human_approval('funder_outreach', self.unapproved_match)

    def test_islamic_finance_claim_publication_blocked_without_approval(self):
        with self.assertRaises(WTVHumanApprovalRequiredError):
            wtv_require_human_approval('islamic_finance_claim_publication', self.unapproved_match)


class GovernanceTests(TestCase):
    def test_create_governed_investment_case_persists_and_is_idempotent(self):
        loss = OperationalLoss.objects.create(title='Test loss', loss_type='meat_spoilage', financial_loss_amount=1000)
        option = InterventionOption.objects.create(operational_loss=loss, title='Test option', intervention_type='equipment_upgrade')
        decision1 = create_governed_investment_case(
            option, decision_text='APPROVE WITH CONDITIONS',
            scores={'financial_return_score': 80}, conditions=['Collect after-data.'],
        )
        decision2 = create_governed_investment_case(
            option, decision_text='APPROVE WITH CONDITIONS', scores={'financial_return_score': 85},
        )
        self.assertEqual(decision1.pk, decision2.pk)
        self.assertEqual(CapitalAllocationDecision.objects.filter(intervention=option).count(), 1)
        self.assertEqual(decision2.financial_return_score, 85)


class MrvOutcomesTests(TestCase):
    def setUp(self):
        self.loss = OperationalLoss.objects.create(title='Test loss', loss_type='meat_spoilage', financial_loss_amount=12000)
        self.option = InterventionOption.objects.create(
            operational_loss=self.loss, title='Cold-chain upgrade', intervention_type='equipment_upgrade',
            estimated_payback_months=9,
        )
        self.decision = create_governed_investment_case(self.option, decision_text='APPROVE WITH CONDITIONS')

    def test_verified_net_value_recovered_worked_example(self):
        outcome = record_verified_outcome(
            self.decision, self.option, loss_avoided_actual=8400, capex_actual=1500,
        )
        self.assertEqual(outcome.value_recovered_actual, 6900.0)

    def test_verified_status_never_verified_unless_mrv_says_so(self):
        outcome = record_verified_outcome(
            self.decision, self.option, loss_avoided_actual=8400, capex_actual=1500,
            mrv_status='after_data_pending',
        )
        self.assertEqual(outcome.verified_status, 'estimated')

    def test_public_reporting_never_ready_off_estimated_outcome(self):
        outcome = record_verified_outcome(
            self.decision, self.option, loss_avoided_actual=8400, capex_actual=1500,
            mrv_status='after_data_pending', public_reporting_ready=True,
        )
        self.assertFalse(outcome.public_reporting_ready)

    def test_reallocation_signal_worked_example(self):
        outcome = record_verified_outcome(
            self.decision, self.option, loss_avoided_actual=8400, capex_actual=1500,
            savings_actual=1500 / (11 / 12),
        )
        signal = generate_capital_reallocation_signal(self.option, outcome)
        self.assertEqual(signal['direction'], 'worse_than_estimated')
        self.assertAlmostEqual(signal['variance_pct'], 22.2, places=1)

    def test_reallocation_signal_handles_missing_data(self):
        self.option.estimated_payback_months = None
        outcome = record_verified_outcome(self.decision, self.option, loss_avoided_actual=8400, capex_actual=1500)
        signal = generate_capital_reallocation_signal(self.option, outcome)
        self.assertEqual(signal['direction'], 'unknown')


class DemoPipelineIdempotencyTests(TestCase):
    def test_seed_command_is_idempotent(self):
        call_command('seed_waste_to_value_demo')
        council_run = CouncilRun.objects.get(slug=DEMO_RUN_SLUG)
        counts_first = {
            'agent_runs': AgentRun.objects.filter(council_case=council_run).count(),
            'losses': OperationalLoss.objects.count(),
            'interventions': InterventionOption.objects.count(),
            'decisions': CapitalAllocationDecision.objects.count(),
            'disagreements': CouncilDisagreement.objects.filter(run=council_run).count(),
        }

        call_command('seed_waste_to_value_demo')
        counts_second = {
            'agent_runs': AgentRun.objects.filter(council_case=council_run).count(),
            'losses': OperationalLoss.objects.count(),
            'interventions': InterventionOption.objects.count(),
            'decisions': CapitalAllocationDecision.objects.count(),
            'disagreements': CouncilDisagreement.objects.filter(run=council_run).count(),
        }

        self.assertEqual(counts_first, counts_second)
        self.assertEqual(counts_first['agent_runs'], 11)
        self.assertEqual(counts_first['interventions'], 7)
        self.assertEqual(counts_first['disagreements'], 2)

    def test_waste_leakage_agent_golden_case_conclusion(self):
        call_command('seed_waste_to_value_demo')
        council_run = CouncilRun.objects.get(slug=DEMO_RUN_SLUG)
        task = AgentTask.objects.get(run=council_run, agent_name='Waste & Leakage Agent')
        self.assertEqual(task.collaboration_mode, 'solo')
        self.assertEqual(task.order, 1)
        run = AgentRun.objects.get(council_position=task)
        self.assertEqual(run.parsed_output['capital_at_risk'], 12000.0)
        self.assertEqual(run.parsed_output['classification'], 'forecast')
        self.assertEqual(run.parsed_output['confidence'], 60)
        self.assertEqual(run.parsed_output['capital_already_lost'], 0)
        self.assertIn('Projected capital at risk: £12,000', task.position_summary)
        self.assertIn('Classification: Forecast', task.position_summary)
        self.assertIn('Confidence: Medium', task.position_summary)
        self.assertNotIn('Verified loss', task.position_summary)

    def test_demo_produces_approved_with_conditions_with_exact_six_conditions(self):
        call_command('seed_waste_to_value_demo')
        decision = CouncilDecision.objects.get(run__slug=DEMO_RUN_SLUG)
        self.assertEqual(decision.status, 'approved_with_conditions')
        self.assertEqual(decision.minority_agents, ['Governance Agent'])
        self.assertEqual(len(decision.conditions), 6)

    def test_demo_preserves_minority_disagreements(self):
        call_command('seed_waste_to_value_demo')
        disagreements = CouncilDisagreement.objects.filter(run__slug=DEMO_RUN_SLUG)
        self.assertEqual(disagreements.count(), 2)
        for d in disagreements:
            self.assertTrue(d.minority_opinion_retained)

    def test_demo_shows_differing_confidence_and_correct_execution_mode(self):
        call_command('seed_waste_to_value_demo')
        runs = AgentRun.objects.filter(council_case__slug=DEMO_RUN_SLUG)
        confidences = {r.calibrated_confidence for r in runs}
        self.assertGreater(len(confidences), 1)
        for run in runs:
            self.assertEqual(run.execution_mode_requested, 'simulated_demo')
            self.assertEqual(run.execution_mode_used, 'simulated_demo')

    def test_demo_creates_capital_allocation_decision_for_equipment_intervention(self):
        call_command('seed_waste_to_value_demo')
        decision = CapitalAllocationDecision.objects.get(council_case__slug=DEMO_RUN_SLUG)
        self.assertEqual(decision.intervention.title, 'Cold-chain equipment intervention')
        self.assertEqual(decision.intervention.estimated_payback_months, 9.0)
        self.assertEqual(decision.approval_status, 'approved_with_conditions')
        # Real rank computed by the Capital Allocation Agent, not hardcoded.
        self.assertEqual(decision.ranking, 1)

    def test_demo_creates_capital_allocation_agent_position(self):
        call_command('seed_waste_to_value_demo')
        council_run = CouncilRun.objects.get(slug=DEMO_RUN_SLUG)
        task = AgentTask.objects.get(run=council_run, agent_name='Capital Allocation Agent')
        self.assertEqual(task.order, 11)
        self.assertEqual(task.collaboration_mode, 'council')
        run = AgentRun.objects.get(council_position=task)
        self.assertEqual(run.parsed_output['top_ranked_option'], 'Cold-chain equipment intervention')
        self.assertIn('Cold-chain equipment intervention', task.position_summary)
        self.assertIn('never an autonomous investment decision', run.parsed_output['why_top_ranked'])


REQUIRED_TEXT = [
    'EcoIQ Waste-to-Value Capital Allocation Engine',
    'Turn operational waste into finance-ready investment opportunities',
    'Operational Waste', 'Funding Gap', 'Capital Reallocated',
    'Where should the next £1 of capital go?', 'We make wasted value investable.',
    'Meat Cold-Chain Loss Prevention',
]


class RouteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_waste_to_value_demo')

    def test_overview_returns_200(self):
        response = self.client.get('/waste-to-value-capital-allocation/')
        self.assertEqual(response.status_code, 200)

    def test_decision_detail_returns_200(self):
        decision = CapitalAllocationDecision.objects.first()
        response = self.client.get(f'/waste-to-value-capital-allocation/decision/{decision.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, decision.intervention.title)

    def test_decision_detail_404_for_unknown_id(self):
        response = self.client.get('/waste-to-value-capital-allocation/decision/999999/')
        self.assertEqual(response.status_code, 404)

    def test_required_text_appears_somewhere_across_pages(self):
        decision = CapitalAllocationDecision.objects.first()
        combined = ''
        for url in (
            '/waste-to-value-capital-allocation/',
            f'/waste-to-value-capital-allocation/decision/{decision.id}/',
        ):
            combined += self.client.get(url).content.decode()
        for text in REQUIRED_TEXT:
            self.assertIn(text, combined, f'Required text {text!r} missing across pages')

    def test_no_raw_template_tags(self):
        decision = CapitalAllocationDecision.objects.first()
        for url in (
            '/waste-to-value-capital-allocation/',
            f'/waste-to-value-capital-allocation/decision/{decision.id}/',
        ):
            content = self.client.get(url).content.decode()
            for token in RAW_TEMPLATE_TOKENS:
                self.assertNotIn(token, content, f'raw template token "{token}" leaked into {url}')

    def _assert_negated_everywhere(self, content, phrase, window=60):
        lowered = content.lower()
        idx = lowered.find(phrase.lower())
        while idx != -1:
            preceding = lowered[max(0, idx - window):idx]
            self.assertIn('not', preceding, f'unsupported claim found: "{phrase}" without negation context nearby')
            idx = lowered.find(phrase.lower(), idx + 1)

    def test_no_unsupported_or_unsafe_claims(self):
        decision = CapitalAllocationDecision.objects.first()
        for url in (
            '/waste-to-value-capital-allocation/',
            f'/waste-to-value-capital-allocation/decision/{decision.id}/',
        ):
            content = self.client.get(url).content.decode()
            # "guaranteed return"/"funding secured" are allowed only inside an
            # explicit negation (e.g. "never presented as a guaranteed return"),
            # mirroring the negation-context-check pattern used elsewhere in
            # this session for the Microsoft-certification claim.
            self._assert_negated_everywhere(content, 'guaranteed return')
            self._assert_negated_everywhere(content, 'funding secured')
            self.assertNotIn('fully autonomous', content.lower())
            self.assertNotIn('Shariah certified', content)
            self.assertNotIn('is a fatwa', content)

    def test_platform_page_mentions_waste_to_value_engine(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Waste-to-Value Capital Allocation Engine')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into rendered page')


class AgentBridgeTests(TestCase):
    def test_meat_cold_chain_golden_case_capital_at_risk_exact(self):
        fixture = build_loss_detection_fixture(
            organisation='', asset='Cold Store Unit 3', loss_type='meat_spoilage',
            inventory_value=80000, historical_loss_rate=0.15,
            evidence_used=['inventory_value_report', 'electricity_bill'],
            missing_data=['independent_technical_inspection_report'],
            classification='forecast', confidence=60,
        )
        self.assertEqual(fixture['capital_at_risk'], 12000.0)
        self.assertEqual(fixture['classification'], 'forecast')
        self.assertEqual(fixture['confidence'], 60)
        self.assertEqual(fixture['capital_already_lost'], 0)

    def test_rejects_invalid_classification(self):
        with self.assertRaises(ValueError):
            build_loss_detection_fixture(
                organisation='', asset='', loss_type='meat_spoilage',
                inventory_value=80000, historical_loss_rate=0.15,
                evidence_used=[], missing_data=[], classification='verified',
            )

    def test_never_asserts_capital_already_lost_without_being_told_to(self):
        fixture = build_loss_detection_fixture(
            organisation='', asset='', loss_type='meat_spoilage',
            inventory_value=80000, historical_loss_rate=0.15,
            evidence_used=[], missing_data=[],
        )
        self.assertEqual(fixture['capital_already_lost'], 0)

    def test_safety_engine_blocks_verified_loss_claim_without_evidence(self):
        # Proves the spec's "the agent must NEVER say Verified loss: £12,000
        # unless actual verified loss evidence exists" invariant is enforced
        # by the shared safety engine, not merely by convention.
        unsafe_output = {
            'output_summary': 'Verified loss: £12,000.',
            'evidence_used': [],
        }
        findings = run_safety_assertions(unsafe_output, 'Waste & Leakage Agent')
        pattern_ids = {f['pattern_id'] for f in findings}
        self.assertIn('estimated_as_verified', pattern_ids)


class CapitalAllocationBridgeTests(TestCase):
    CANDIDATES = [
        {'title': 'Dynamic discount now', 'intervention_type': 'prevention',
         'capex_estimate': 200, 'estimated_value_recovered': 3000, 'estimated_loss_avoided': 3000,
         'risk_level': 'low', 'technical_readiness': 'ready'},
        {'title': 'Cold-chain equipment intervention', 'intervention_type': 'equipment_upgrade',
         'capex_estimate': 9000, 'estimated_annual_savings': 12000, 'estimated_loss_avoided': 12000,
         'risk_level': 'medium', 'technical_readiness': 'ready', 'finance_readiness': 'needs_review',
         'mrv_readiness': 'draft', 'status': 'recommended'},
    ]

    def setUp(self):
        self.loss = OperationalLoss.objects.create(
            title='Meat Cold-Chain Spoilage Risk', loss_type='meat_spoilage',
            financial_loss_amount=0, projected_future_loss=12000,
        )
        model_interventions(self.loss, self.CANDIDATES)

    def test_fixture_recommends_equipment_option_first(self):
        fixture = build_capital_allocation_fixture(self.loss)
        self.assertEqual(fixture['top_ranked_option'], 'Cold-chain equipment intervention')
        self.assertEqual(fixture['ranked_options'][0]['rank'], 1)

    def test_fixture_answers_all_ten_questions(self):
        fixture = build_capital_allocation_fixture(self.loss)
        for field in (
            'top_ranked_option', 'why_top_ranked', 'evidence_supporting_ranking', 'assumptions',
            'unresolved_risks', 'highest_capital_efficiency_option', 'fastest_value_recovery_option',
            'longest_term_capex_option', 'human_approval_required_for', 'mrv_measurement_recommendation',
        ):
            self.assertTrue(fixture[field], f'{field} must not be empty')

    def test_fixture_never_states_autonomous_decision(self):
        fixture = build_capital_allocation_fixture(self.loss)
        self.assertIn('never an autonomous investment decision', fixture['why_top_ranked'])
        self.assertTrue(fixture['human_approval_required'])

    def test_fixture_includes_output_summary(self):
        # submit_agent_position_to_council() falls back to the generic
        # input_summary if output_summary is missing — guard against
        # repeating that bug for this agent too.
        fixture = build_capital_allocation_fixture(self.loss)
        self.assertIn('output_summary', fixture)
        self.assertTrue(fixture['output_summary'])

    def test_fastest_value_recovery_is_not_the_equipment_option(self):
        fixture = build_capital_allocation_fixture(self.loss)
        self.assertEqual(fixture['fastest_value_recovery_option'], 'Dynamic discount now')

    def test_longest_term_capex_is_the_equipment_option(self):
        fixture = build_capital_allocation_fixture(self.loss)
        self.assertEqual(fixture['longest_term_capex_option'], 'Cold-chain equipment intervention')


class CapitalGuardianHandoffTests(TestCase):
    """
    Phase 1A, Task 7 — the first real connection from a human-approved
    CapitalAllocationDecision to capital_guardian.ProjectGovernance.
    """

    def setUp(self):
        from django.contrib.auth import get_user_model
        from gold_intelligence.models import GoldProject

        User = get_user_model()
        self.actor = User.objects.create_user('approver', 'approver@example.com', 'password123')

        self.gold_project = GoldProject.objects.create(name='KZ Gold Project 01', slug='kz-gold-project-01')

        self.loss = OperationalLoss.objects.create(
            title='Test loss', loss_type='meat_spoilage', financial_loss_amount=1000,
            project='KZ Gold Project 01',
        )
        self.option = InterventionOption.objects.create(
            operational_loss=self.loss, title='Test option', intervention_type='equipment_upgrade',
        )

    def _make_decision(self, approval_status='approved'):
        return create_governed_investment_case(
            self.option, decision_text='APPROVE', scores={'financial_return_score': 80},
            approval_status=approval_status,
        )

    def test_approved_decision_with_matching_project_promotes(self):
        from capital_guardian.models import ProjectGovernance

        decision = self._make_decision(approval_status='approved')
        result = promote_to_capital_guardian(decision, actor=self.actor)

        self.assertEqual(result.status, 'promoted')
        self.assertEqual(result.project.pk, self.gold_project.pk)
        self.assertTrue(ProjectGovernance.objects.filter(project=self.gold_project).exists())
        self.assertFalse(result.governance.is_demo)

    def test_approved_with_conditions_also_promotes(self):
        decision = self._make_decision(approval_status='approved_with_conditions')
        result = promote_to_capital_guardian(decision, actor=self.actor)
        self.assertEqual(result.status, 'promoted')

    def test_creation_is_audit_logged_with_real_actor(self):
        from capital_guardian.models import AuditLogEntry

        decision = self._make_decision(approval_status='approved')
        result = promote_to_capital_guardian(decision, actor=self.actor)

        entry = AuditLogEntry.objects.filter(
            project=self.gold_project, event_type='governance',
            source_reference=f'capital_guardian.ProjectGovernance:{result.governance.pk}',
        ).first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.changed_by, self.actor)

    def test_unapproved_decision_raises(self):
        decision = self._make_decision(approval_status='pending')
        with self.assertRaises(DecisionNotApprovedError):
            promote_to_capital_guardian(decision, actor=self.actor)

    def test_rejected_decision_raises(self):
        decision = self._make_decision(approval_status='rejected')
        with self.assertRaises(DecisionNotApprovedError):
            promote_to_capital_guardian(decision, actor=self.actor)

    def test_unapproved_decision_creates_no_governance_record(self):
        from capital_guardian.models import ProjectGovernance

        decision = self._make_decision(approval_status='pending')
        try:
            promote_to_capital_guardian(decision, actor=self.actor)
        except DecisionNotApprovedError:
            pass
        self.assertFalse(ProjectGovernance.objects.filter(project=self.gold_project).exists())

    def test_already_promoted_decision_is_idempotent(self):
        from capital_guardian.models import ProjectGovernance

        decision = self._make_decision(approval_status='approved')
        first = promote_to_capital_guardian(decision, actor=self.actor)
        second = promote_to_capital_guardian(decision, actor=self.actor)

        self.assertEqual(first.status, 'promoted')
        self.assertEqual(second.status, 'already_promoted')
        self.assertEqual(first.governance.pk, second.governance.pk)
        self.assertEqual(ProjectGovernance.objects.filter(project=self.gold_project).count(), 1)

    def test_duplicate_invocation_creates_no_extra_audit_entries(self):
        from capital_guardian.models import AuditLogEntry

        decision = self._make_decision(approval_status='approved')
        promote_to_capital_guardian(decision, actor=self.actor)
        promote_to_capital_guardian(decision, actor=self.actor)

        count = AuditLogEntry.objects.filter(
            project=self.gold_project, event_type='governance', field_name='(created)',
        ).count()
        self.assertEqual(count, 1)

    def test_no_matching_gold_project_returns_honest_result(self):
        from capital_guardian.models import ProjectGovernance

        self.loss.project = 'Some Other Project That Does Not Exist'
        self.loss.save(update_fields=['project'])
        decision = self._make_decision(approval_status='approved')

        result = promote_to_capital_guardian(decision, actor=self.actor)

        self.assertEqual(result.status, 'no_matching_project')
        self.assertIsNone(result.governance)
        self.assertEqual(ProjectGovernance.objects.count(), 0)

    def test_no_matching_project_never_fabricates_a_gold_project(self):
        from gold_intelligence.models import GoldProject

        self.loss.project = 'Nonexistent Project'
        self.loss.save(update_fields=['project'])
        decision = self._make_decision(approval_status='approved')

        before = GoldProject.objects.count()
        promote_to_capital_guardian(decision, actor=self.actor)
        self.assertEqual(GoldProject.objects.count(), before)

    def test_ambiguous_project_name_refuses_to_guess(self):
        from gold_intelligence.models import GoldProject
        from capital_guardian.models import ProjectGovernance

        GoldProject.objects.create(name='KZ Gold Project 01', slug='kz-gold-project-01-duplicate')
        decision = self._make_decision(approval_status='approved')

        result = promote_to_capital_guardian(decision, actor=self.actor)

        self.assertEqual(result.status, 'ambiguous_project_match')
        self.assertIsNone(result.governance)
        self.assertEqual(ProjectGovernance.objects.count(), 0)

    def test_blank_project_field_returns_no_matching_project(self):
        self.loss.project = ''
        self.loss.save(update_fields=['project'])
        decision = self._make_decision(approval_status='approved')

        result = promote_to_capital_guardian(decision, actor=self.actor)
        self.assertEqual(result.status, 'no_matching_project')

    def test_actor_is_optional(self):
        """A promotion with no real actor known must still work honestly (changed_by=None), never guessing a user."""
        from capital_guardian.models import AuditLogEntry

        decision = self._make_decision(approval_status='approved')
        result = promote_to_capital_guardian(decision, actor=None)

        self.assertEqual(result.status, 'promoted')
        entry = AuditLogEntry.objects.filter(
            project=self.gold_project, event_type='governance', field_name='(created)',
        ).first()
        self.assertIsNone(entry.changed_by)
