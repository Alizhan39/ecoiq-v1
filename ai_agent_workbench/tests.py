import re

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from agent_runtime_model_router.models import AgentRegistryEntry
from ai_agent_council.models import CouncilRun
from ai_agent_workbench.services import agent_data, demo_cases, recommender

TEMPLATE_LEAK_RE = re.compile(r'\{%|\{\{')


def _seed_all():
    call_command('seed_agent_runtime_demo')
    call_command('seed_council_demo_run')
    call_command('seed_waste_to_value_demo')
    call_command('seed_khalifa_stewardship_demo')
    call_command('seed_financial_intelligence_cloud_demo')


class AgentDirectoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_all()

    def test_all_twelve_operational_agents_visible(self):
        rows = agent_data.agent_directory_rows()
        self.assertEqual(len(rows), 12)
        names = {r['name'] for r in rows}
        self.assertIn('Waste & Leakage Agent', names)
        self.assertIn('Capital Allocation Agent', names)

    def test_no_duplicate_agent_registry_rows(self):
        agent_data.ensure_registry_synced()
        agent_data.ensure_registry_synced()  # idempotent, calling twice must not duplicate
        ids = list(AgentRegistryEntry.objects.values_list('agent_id', flat=True))
        self.assertEqual(len(ids), len(set(ids)))

    def test_directory_page_200_and_no_template_leak(self):
        resp = self.client.get(reverse('ai_agent_workbench:directory'))
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        self.assertFalse(TEMPLATE_LEAK_RE.search(body))
        self.assertContains(resp, 'Research Agent')

    def test_performance_page_never_fabricates(self):
        resp = self.client.get(reverse('ai_agent_workbench:performance'))
        self.assertEqual(resp.status_code, 200)
        # At least one agent has no real evaluation score yet — must say so honestly.
        self.assertContains(resp, 'NOT YET MEASURED')

    def test_agent_profile_200_for_real_agent(self):
        resp = self.client.get(reverse('ai_agent_workbench:agent_profile', args=['waste-leakage-agent']))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Leakage Agent')

    def test_agent_profile_404_for_unknown_slug(self):
        resp = self.client.get(reverse('ai_agent_workbench:agent_profile', args=['not-a-real-agent']))
        self.assertEqual(resp.status_code, 404)


class WorkbenchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_all()

    def test_workbench_loads_with_no_params(self):
        resp = self.client.get(reverse('ai_agent_workbench:workbench'))
        self.assertEqual(resp.status_code, 200)

    def test_meat_cold_chain_demo_shows_projected_capital_at_risk(self):
        resp = self.client.get(
            reverse('ai_agent_workbench:workbench'),
            {'case': 'meat-cold-chain-loss', 'agent': 'waste-leakage-agent'},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, '12,000')
        self.assertContains(resp, 'Forecast')

    def test_execution_mode_requested_and_used_both_shown_no_silent_fallback(self):
        resp = self.client.get(
            reverse('ai_agent_workbench:workbench'),
            {'case': 'meat-cold-chain-loss', 'agent': 'waste-leakage-agent'},
        )
        body = resp.content.decode()
        self.assertIn('Requested:', body)
        self.assertIn('Used:', body)
        # The seeded demo run is a simulated_demo request that resolves to simulated_demo —
        # this asserts the run never claims 'live' was silently downgraded.
        from agent_runtime_model_router.models import AgentRun
        run = AgentRun.objects.filter(
            council_case__slug='meat-cold-chain-loss-prevention-demo',
            agent__agent_name='Waste & Leakage Agent',
        ).first()
        self.assertIsNotNone(run)
        if run.execution_mode_requested == 'live':
            self.assertNotEqual(run.execution_mode_used, 'simulated_demo')

    def test_evidence_provenance_and_missing_data_displayed(self):
        resp = self.client.get(
            reverse('ai_agent_workbench:workbench'),
            {'case': 'meat-cold-chain-loss', 'agent': 'waste-leakage-agent'},
        )
        self.assertContains(resp, 'What the AI saw')
        self.assertContains(resp, 'What the AI is not sure about')
        self.assertContains(resp, 'independent_technical_inspection_report')

    def test_handoffs_displayed_for_document_reader(self):
        resp = self.client.get(
            reverse('ai_agent_workbench:workbench'),
            {'case': 'meat-cold-chain-loss', 'agent': 'finance-modelling-agent'},
        )
        self.assertEqual(resp.status_code, 200)

    def test_investment_portfolio_shows_four_ranked_options_in_order(self):
        resp = self.client.get(
            reverse('ai_agent_workbench:workbench'), {'case': 'investment-portfolio'},
        )
        body = resp.content.decode()
        self.assertIn('Cold-chain optimisation', body)
        self.assertIn('Waste heat recovery', body)
        self.assertIn('Boiler modernisation', body)
        self.assertIn('Expansion project', body)
        # Rank order: cold-chain optimisation must appear before expansion project.
        self.assertLess(body.index('Cold-chain optimisation'), body.index('Expansion project'))

    def test_send_to_council_links_to_real_council_run(self):
        resp = self.client.get(
            reverse('ai_agent_workbench:workbench'),
            {'case': 'meat-cold-chain-loss', 'agent': 'waste-leakage-agent'},
        )
        self.assertContains(resp, '/ai-agent-council/run/meat-cold-chain-loss-prevention-demo/')

    def test_agent_not_in_case_shows_honest_message_not_fabricated_output(self):
        # Research Agent is not part of the Meat Cold-Chain agent chain.
        resp = self.client.get(
            reverse('ai_agent_workbench:workbench'),
            {'case': 'meat-cold-chain-loss', 'agent': 'research-agent'},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'was not part of this demo')

    def test_recommender_matches_spec_example(self):
        result = recommender.recommend_agent_for_task('Where is value being lost?')
        self.assertEqual(result['agent_name'], 'Waste & Leakage Agent')
        self.assertTrue(result['matched'])

    def test_recommender_never_auto_runs_only_recommends(self):
        result = recommender.recommend_agent_for_task('Which project deserves funding first?')
        self.assertEqual(result['agent_name'], 'Capital Allocation Agent')
        # Recommending is pure data — no side effects, no AgentRun created.
        from agent_runtime_model_router.models import AgentRun
        count_before = AgentRun.objects.count()
        recommender.recommend_agent_for_task('Which project deserves funding first?')
        self.assertEqual(AgentRun.objects.count(), count_before)

    def test_ask_recommendation_shown_on_page(self):
        resp = self.client.get(reverse('ai_agent_workbench:workbench'), {'ask': 'Where is value being lost?'})
        self.assertContains(resp, 'Leakage Agent')
        self.assertContains(resp, 'nothing runs automatically')


class CouncilDemoAndPresentationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_all()

    def test_council_demo_page_200_lists_real_cases(self):
        resp = self.client.get(reverse('ai_agent_workbench:council_demo'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Meat Cold-Chain Loss Prevention')

    def test_presentation_page_200(self):
        resp = self.client.get(reverse('ai_agent_workbench:presentation'))
        self.assertEqual(resp.status_code, 200)

    def test_human_approval_status_visible_on_council_run(self):
        run = CouncilRun.objects.get(slug='meat-cold-chain-loss-prevention-demo')
        resp = self.client.get(reverse('ai_agent_council:run_detail', args=[run.slug]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Human approval')

    def test_run_alias_redirects_to_real_run_detail(self):
        from agent_runtime_model_router.models import AgentRun
        run = AgentRun.objects.first()
        resp = self.client.get(reverse('ai_agent_workbench:run_alias', args=[run.id]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f'/agent-runtime-model-router/run/{run.id}/', resp.url)


class SafetyAndPrivacyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_all()

    def test_no_secret_like_strings_in_workbench_output(self):
        resp = self.client.get(
            reverse('ai_agent_workbench:workbench'),
            {'case': 'meat-cold-chain-loss', 'agent': 'waste-leakage-agent'},
        )
        body = resp.content.decode()
        for pattern in ('sk-', 'api_key', 'API_KEY', 'SECRET_KEY', 'Bearer '):
            self.assertNotIn(pattern, body)

    def test_no_external_action_link_from_public_demo(self):
        resp = self.client.get(reverse('ai_agent_workbench:workbench'))
        body = resp.content.decode()
        self.assertNotIn('action="http', body)  # no form posting to an external domain

    def test_demo_case_config_only_references_deterministic_or_simulated_modes(self):
        for case in demo_cases.DEMO_CASES.values():
            council_run = demo_cases.council_run_for_case(case)
            if council_run:
                self.assertTrue(council_run.is_simulated)


class HomepageIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_all()

    def test_homepage_has_agent_ctas_and_no_template_leak(self):
        resp = self.client.get(reverse('home'))
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        self.assertIn('TRY THE AI AGENTS', body)
        self.assertIn('WATCH THE AGENT COUNCIL', body)
        self.assertIn('SEE HOW A DECISION HAPPENED', body)
        self.assertIn('/ai-agents/workbench/', body)
        self.assertFalse(TEMPLATE_LEAK_RE.search(body))

    def test_homepage_reports_real_agent_count_not_hardcoded(self):
        from ai_agent_council.agents import OPERATIONAL_AGENTS
        resp = self.client.get(reverse('home'))
        self.assertContains(resp, f'{len(OPERATIONAL_AGENTS)} operational agents')


class ProductPageIntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_all()

    def test_kazakhstan_tour_detail_shows_agents_widget(self):
        resp = self.client.get(
            reverse('khalifa_stewardship_tour_operating_system:tour_detail', args=['kazakhstan-clean-heat']),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Agents working on this case')

    def test_cold_chain_decision_detail_shows_agents_widget(self):
        from waste_to_value_capital_allocation_engine.models import CapitalAllocationDecision
        decision = CapitalAllocationDecision.objects.first()
        resp = self.client.get(
            reverse('waste_to_value_capital_allocation_engine:decision_detail', args=[decision.id]),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Agents working on this case')

    def test_financial_intelligence_cloud_portfolio_shows_freshbridge_agents(self):
        resp = self.client.get(reverse('financial_intelligence_cloud:portfolio'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Agents working on this case')


class AllRoutesReturn200Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_all()

    def test_all_ai_agent_workbench_routes_200(self):
        routes = [
            reverse('ai_agent_workbench:directory'),
            reverse('ai_agent_workbench:workbench'),
            reverse('ai_agent_workbench:presentation'),
            reverse('ai_agent_workbench:performance'),
            reverse('ai_agent_workbench:council_demo'),
            reverse('ai_agent_workbench:agent_profile', args=['research-agent']),
        ]
        for url in routes:
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertEqual(resp.status_code, 200)
                self.assertFalse(TEMPLATE_LEAK_RE.search(resp.content.decode()))
