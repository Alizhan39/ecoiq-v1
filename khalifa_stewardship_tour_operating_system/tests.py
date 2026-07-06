from django.test import TestCase

from khalifa_stewardship_tour_operating_system.services.tours import (
    add_local_partner, add_participant_role, create_funding_plan, create_mrv_plan,
    create_stewardship_intervention, create_stewardship_problem, create_stewardship_tour,
)
from khalifa_stewardship_tour_operating_system.services.capital_allocation_link import rank_stewardship_interventions
from khalifa_stewardship_tour_operating_system.services.agent_bridge import (
    build_finance_modelling_fixture, build_waste_leakage_fixture,
)
from khalifa_stewardship_tour_operating_system.services.demo_flagship_pipeline import (
    DEMO_RUN_SLUG, build_kazakhstan_clean_heat_demo,
)
from agent_runtime_model_router.services.registry import sync_registry
from agent_runtime_model_router.models import AgentRun
from ai_agent_council.models import AgentTask, CouncilDecision, CouncilRun
from khalifa_stewardship_tour_operating_system.services.human_approval_gate import (
    ACTIONS_REQUIRING_APPROVAL, HumanApprovalRequiredError, require_human_approval,
)
from khalifa_stewardship_tour_operating_system.models import StewardshipTour

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class ToursServiceTests(TestCase):
    def test_create_stewardship_tour_is_idempotent(self):
        create_stewardship_tour('kazakhstan-clean-heat', 'Kazakhstan Clean Heat Stewardship Tour', 'clean_heat')
        create_stewardship_tour('kazakhstan-clean-heat', 'Kazakhstan Clean Heat Stewardship Tour', 'clean_heat')
        from khalifa_stewardship_tour_operating_system.models import StewardshipTour
        self.assertEqual(StewardshipTour.objects.filter(slug='kazakhstan-clean-heat').count(), 1)

    def test_create_stewardship_problem_is_idempotent(self):
        tour = create_stewardship_tour('kazakhstan-clean-heat', 'Kazakhstan Clean Heat Stewardship Tour', 'clean_heat')
        create_stewardship_problem(tour, 'inefficient_heating', 'Household uses inefficient coal heating')
        create_stewardship_problem(tour, 'inefficient_heating', 'Household uses inefficient coal heating')
        self.assertEqual(tour.problems.count(), 1)

    def test_create_stewardship_intervention_is_idempotent(self):
        tour = create_stewardship_tour('kazakhstan-clean-heat', 'Kazakhstan Clean Heat Stewardship Tour', 'clean_heat')
        problem = create_stewardship_problem(tour, 'inefficient_heating', 'Household uses inefficient coal heating')
        create_stewardship_intervention(problem, 'Clean heating + insulation package', 'clean_heating_upgrade')
        create_stewardship_intervention(problem, 'Clean heating + insulation package', 'clean_heating_upgrade')
        self.assertEqual(problem.interventions.count(), 1)

    def test_funding_plan_computes_gap_not_asserted(self):
        tour = create_stewardship_tour('kazakhstan-clean-heat', 'Kazakhstan Clean Heat Stewardship Tour', 'clean_heat')
        plan = create_funding_plan(
            tour, total_required=3200, participant_contribution=600, sponsor_contribution=900,
            grant_contribution=500, local_partner_contribution=200,
        )
        self.assertEqual(plan.funding_gap, 1000)

    def test_funding_plan_gap_never_negative(self):
        tour = create_stewardship_tour('kazakhstan-clean-heat', 'Kazakhstan Clean Heat Stewardship Tour', 'clean_heat')
        plan = create_funding_plan(tour, total_required=100, participant_contribution=500)
        self.assertEqual(plan.funding_gap, 0)

    def test_add_participant_role_is_idempotent(self):
        tour = create_stewardship_tour('kazakhstan-clean-heat', 'Kazakhstan Clean Heat Stewardship Tour', 'clean_heat')
        add_participant_role(tour, 'Participant', allowed_actions=['observe'], blocked_actions=['electrical_work'])
        add_participant_role(tour, 'Participant', allowed_actions=['observe'], blocked_actions=['electrical_work'])
        self.assertEqual(tour.participant_roles.count(), 1)

    def test_add_local_partner_is_idempotent(self):
        tour = create_stewardship_tour('kazakhstan-clean-heat', 'Kazakhstan Clean Heat Stewardship Tour', 'clean_heat')
        add_local_partner(tour, 'Almaty Region Community Cooperative', partner_type='cooperative')
        add_local_partner(tour, 'Almaty Region Community Cooperative', partner_type='cooperative')
        self.assertEqual(tour.local_partners.count(), 1)

    def test_create_mrv_plan_is_idempotent(self):
        tour = create_stewardship_tour('kazakhstan-clean-heat', 'Kazakhstan Clean Heat Stewardship Tour', 'clean_heat')
        create_mrv_plan(tour, methodology='Before/after heating cost and comfort survey.')
        create_mrv_plan(tour, methodology='Before/after heating cost and comfort survey.')
        from khalifa_stewardship_tour_operating_system.models import TourMRVPlan
        self.assertEqual(TourMRVPlan.objects.filter(tour=tour).count(), 1)

    def test_participant_role_blocks_electrical_work(self):
        tour = create_stewardship_tour('kazakhstan-clean-heat', 'Kazakhstan Clean Heat Stewardship Tour', 'clean_heat')
        role = add_participant_role(
            tour, 'Participant', allowed_actions=['observe', 'community_cleanup'],
            blocked_actions=['electrical_work', 'heating_installation', 'technical_repairs'],
        )
        self.assertIn('electrical_work', role.blocked_actions)
        self.assertNotIn('electrical_work', role.allowed_actions)

    def test_legacy_record_never_auto_created_for_a_tour(self):
        tour = create_stewardship_tour('kazakhstan-clean-heat', 'Kazakhstan Clean Heat Stewardship Tour', 'clean_heat')
        self.assertFalse(hasattr(tour, 'legacy_record') and tour.legacy_record)
        with self.assertRaises(Exception):
            tour.legacy_record  # RelatedObjectDoesNotExist


class CapitalAllocationLinkTests(TestCase):
    def setUp(self):
        self.tour = create_stewardship_tour('kazakhstan-clean-heat', 'Kazakhstan Clean Heat Stewardship Tour', 'clean_heat')
        self.problem = create_stewardship_problem(
            self.tour, 'inefficient_heating', 'Household uses inefficient coal heating and loses heat through poor insulation',
        )
        create_stewardship_intervention(
            self.problem, 'Clean heating + insulation package', 'clean_heating_upgrade',
            capex_estimate=1400, estimated_benefit=700, implementation_complexity='medium',
        )
        create_stewardship_intervention(
            self.problem, 'Insulation only', 'insulation_support',
            capex_estimate=600, estimated_benefit=250, implementation_complexity='low',
        )
        create_stewardship_intervention(
            self.problem, 'Smart controls only', 'smart_controls',
            capex_estimate=250, estimated_benefit=80, implementation_complexity='low',
        )

    def test_full_package_ranks_first(self):
        ranked = rank_stewardship_interventions(self.problem, capital_at_risk_ceiling=420, inventory_value_ceiling=1200)
        self.assertEqual(ranked[0]['title'], 'Clean heating + insulation package')
        self.assertEqual(ranked[0]['rank'], 1)

    def test_ranking_returns_all_three_candidates(self):
        ranked = rank_stewardship_interventions(self.problem, capital_at_risk_ceiling=420, inventory_value_ceiling=1200)
        self.assertEqual(len(ranked), 3)


class AgentBridgeTests(TestCase):
    def test_waste_leakage_fixture_exact_capital_at_risk(self):
        fixture = build_waste_leakage_fixture(
            inventory_value=1200, historical_loss_rate=0.35,
            evidence_used=['heating_bill', 'household_baseline_checklist'],
            missing_data=['independent_technical_inspection_report'],
        )
        self.assertEqual(fixture['capital_at_risk'], 420.0)
        self.assertEqual(fixture['classification'], 'forecast')
        self.assertEqual(fixture['capital_already_lost'], 0)

    def test_finance_modelling_fixture_exact_recoverable_value(self):
        fixture = build_finance_modelling_fixture(
            expected_value_recovered=650, intervention_cost=150,
            evidence_used=['heating_bill', 'supplier_quote'],
        )
        self.assertEqual(fixture['potential_recoverable_value'], 500)
        self.assertIn('never presented as a guaranteed return', fixture['output_summary'])


class FlagshipPipelineTests(TestCase):
    def setUp(self):
        sync_registry()

    def test_all_twelve_agents_create_council_positions(self):
        build_kazakhstan_clean_heat_demo()
        council_run = CouncilRun.objects.get(slug=DEMO_RUN_SLUG)
        self.assertEqual(AgentTask.objects.filter(run=council_run).count(), 12)

    def test_decision_is_approved_with_conditions_and_exact_six_conditions(self):
        build_kazakhstan_clean_heat_demo()
        decision = CouncilDecision.objects.get(run__slug=DEMO_RUN_SLUG)
        self.assertEqual(decision.status, 'approved_with_conditions')
        self.assertEqual(len(decision.conditions), 6)

    def test_capital_allocation_agent_recommends_full_package(self):
        build_kazakhstan_clean_heat_demo()
        council_run = CouncilRun.objects.get(slug=DEMO_RUN_SLUG)
        task = AgentTask.objects.get(run=council_run, agent_name='Capital Allocation Agent')
        self.assertIn('Clean heating + insulation package', task.position_summary)
        self.assertIn('never an autonomous investment decision', task.position_summary)

    def test_waste_leakage_agent_golden_case_conclusion(self):
        build_kazakhstan_clean_heat_demo()
        council_run = CouncilRun.objects.get(slug=DEMO_RUN_SLUG)
        task = AgentTask.objects.get(run=council_run, agent_name='Waste & Leakage Agent')
        run = AgentRun.objects.get(council_position=task)
        self.assertEqual(run.parsed_output['capital_at_risk'], 420.0)

    def test_finance_modelling_agent_golden_case_conclusion(self):
        build_kazakhstan_clean_heat_demo()
        council_run = CouncilRun.objects.get(slug=DEMO_RUN_SLUG)
        task = AgentTask.objects.get(run=council_run, agent_name='Finance Modelling Agent')
        run = AgentRun.objects.get(council_position=task)
        self.assertEqual(run.parsed_output['potential_recoverable_value'], 500)

    def test_funding_plan_participant_roles_and_local_partner_created(self):
        from khalifa_stewardship_tour_operating_system.models import StewardshipTour
        build_kazakhstan_clean_heat_demo()
        tour = StewardshipTour.objects.get(slug='kazakhstan-clean-heat')
        self.assertTrue(hasattr(tour, 'funding_plan'))
        self.assertEqual(tour.participant_roles.count(), 2)
        self.assertEqual(tour.local_partners.count(), 1)
        self.assertTrue(hasattr(tour, 'mrv_plan'))

    def test_no_legacy_record_created_for_demo_tour(self):
        from khalifa_stewardship_tour_operating_system.models import StewardshipTour
        build_kazakhstan_clean_heat_demo()
        tour = StewardshipTour.objects.get(slug='kazakhstan-clean-heat')
        with self.assertRaises(Exception):
            tour.legacy_record

    def test_pipeline_is_idempotent(self):
        build_kazakhstan_clean_heat_demo()
        first_count = AgentRun.objects.count()
        build_kazakhstan_clean_heat_demo()
        second_count = AgentRun.objects.count()
        self.assertEqual(first_count, second_count)


class HumanApprovalGateTests(TestCase):
    def setUp(self):
        self.tour = create_stewardship_tour('kazakhstan-clean-heat', 'Kazakhstan Clean Heat Stewardship Tour', 'clean_heat')

    def test_eighteen_total_actions_registered(self):
        self.assertEqual(len(ACTIONS_REQUIRING_APPROVAL), 18)

    def test_travel_launch_authorization_blocked_without_approval(self):
        with self.assertRaises(HumanApprovalRequiredError):
            require_human_approval('travel_launch_authorization', self.tour)

    def test_travel_launch_authorization_allowed_with_approval(self):
        self.tour.human_approved = True
        self.tour.save()
        self.assertTrue(require_human_approval('travel_launch_authorization', self.tour))

    def test_technical_work_authorization_blocked_without_approval(self):
        with self.assertRaises(HumanApprovalRequiredError):
            require_human_approval('technical_work_authorization', self.tour)

    def test_vulnerable_person_filming_blocked_without_approval(self):
        with self.assertRaises(HumanApprovalRequiredError):
            require_human_approval('vulnerable_person_filming', self.tour)

    def test_shared_base_action_still_enforced(self):
        with self.assertRaises(HumanApprovalRequiredError):
            require_human_approval('funder_outreach', self.tour)

    def test_public_impact_claim_not_duplicated(self):
        # public_impact_claim is a base action, not one of this app's 10 additions.
        from khalifa_stewardship_tour_operating_system.services.human_approval_gate import (
            ADDITIONAL_ACTIONS_REQUIRING_APPROVAL,
        )
        self.assertNotIn('public_impact_claim', ADDITIONAL_ACTIONS_REQUIRING_APPROVAL)
        self.assertIn('public_impact_claim', ACTIONS_REQUIRING_APPROVAL)


class RouteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sync_registry()
        build_kazakhstan_clean_heat_demo()

    def test_overview_returns_200(self):
        response = self.client.get('/khalifa-tour-operating-system/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Khalifa Stewardship Tour Operating System')

    def test_presentation_returns_200(self):
        response = self.client.get('/khalifa-tour-operating-system/presentation/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TOURISTS LEAVE')

    def test_tours_returns_200(self):
        response = self.client.get('/khalifa-tour-operating-system/tours/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kazakhstan Clean Heat Stewardship Tour')

    def test_tour_detail_returns_200(self):
        response = self.client.get('/khalifa-tour-operating-system/tour/kazakhstan-clean-heat/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Clean heating + insulation package')

    def test_problems_returns_200(self):
        response = self.client.get('/khalifa-tour-operating-system/problems/')
        self.assertEqual(response.status_code, 200)

    def test_funding_returns_200(self):
        response = self.client.get('/khalifa-tour-operating-system/funding/')
        self.assertEqual(response.status_code, 200)

    def test_mrv_returns_200(self):
        response = self.client.get('/khalifa-tour-operating-system/mrv/')
        self.assertEqual(response.status_code, 200)

    def test_legacy_returns_200_and_shows_honest_empty_state(self):
        response = self.client.get('/khalifa-tour-operating-system/legacy/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'never before')

    def test_kazakhstan_demo_returns_200_and_shows_conditions(self):
        response = self.client.get('/khalifa-tour-operating-system/kazakhstan-clean-heat-demo/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Approved with Conditions')
        self.assertContains(response, 'Clean heating + insulation package')

    def test_no_raw_template_tags_across_all_routes(self):
        routes = [
            '/khalifa-tour-operating-system/', '/khalifa-tour-operating-system/presentation/',
            '/khalifa-tour-operating-system/tours/', '/khalifa-tour-operating-system/tour/kazakhstan-clean-heat/',
            '/khalifa-tour-operating-system/problems/', '/khalifa-tour-operating-system/funding/',
            '/khalifa-tour-operating-system/mrv/', '/khalifa-tour-operating-system/legacy/',
            '/khalifa-tour-operating-system/kazakhstan-clean-heat-demo/',
        ]
        for route in routes:
            response = self.client.get(route)
            content = response.content.decode()
            for token in RAW_TEMPLATE_TOKENS:
                self.assertNotIn(token, content, f'raw template token "{token}" leaked into {route}')

    def _assert_negated_everywhere(self, content, phrase, window=40):
        # Blunt substring checks false-positive on this app's own honest
        # disclaimer copy ("...is never the same as funding secured"), so
        # every occurrence must be preceded by a negation within `window` chars.
        idx = content.find(phrase)
        while idx != -1:
            preceding = content[max(0, idx - window):idx]
            self.assertIn('never', preceding, f'unnegated "{phrase}" found: ...{preceding}{phrase}...')
            idx = content.find(phrase, idx + 1)

    def test_no_unsafe_claims_across_all_routes(self):
        routes = [
            '/khalifa-tour-operating-system/', '/khalifa-tour-operating-system/tour/kazakhstan-clean-heat/',
            '/khalifa-tour-operating-system/kazakhstan-clean-heat-demo/',
        ]
        for route in routes:
            content = self.client.get(route).content.decode().lower()
            self._assert_negated_everywhere(content, 'funding secured')
            self.assertNotIn('verified outcome achieved', content)
            self.assertNotIn('fully autonomous', content)
            self.assertNotIn('technical installation approved', content)

    def test_platform_page_mentions_khalifa_tours(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Khalifa Stewardship Tour Operating System')
        self.assertContains(response, 'Open Khalifa Tours Operating System')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into /platform/')


class SeedCommandTests(TestCase):
    def test_seed_command_is_idempotent(self):
        from django.core.management import call_command
        call_command('seed_khalifa_stewardship_demo')
        first = (
            StewardshipTour.objects.count(),
            AgentRun.objects.count(),
        )
        call_command('seed_khalifa_stewardship_demo')
        second = (
            StewardshipTour.objects.count(),
            AgentRun.objects.count(),
        )
        self.assertEqual(first, second)
        self.assertEqual(first, (1, 12))
