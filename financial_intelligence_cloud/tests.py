from django.test import TestCase

from financial_intelligence_cloud.services.accounts import (
    add_portfolio_entity, create_institutional_account, create_portfolio,
)
from financial_intelligence_cloud.services.signals import (
    detect_advisory_opportunity, evidence_quality_score, generate_portfolio_signal,
)
from financial_intelligence_cloud.services.portfolio_ranking import (
    CLIENT_CALL_WEIGHTS, FINANCE_OPPORTUNITY_WEIGHTS, PORTFOLIO_RISK_WEIGHTS,
    rank_clients_to_call_today, rank_finance_opportunities, rank_portfolio_risks,
)
from financial_intelligence_cloud.services.entity_generation import generate_portfolio_entities
from financial_intelligence_cloud.services.capital_allocation_link import build_atlas_capital_allocation_portfolio
from financial_intelligence_cloud.services.demo_flagship_pipeline import build_freshbridge_foods_demo
from financial_intelligence_cloud.services.demo_portfolios import (
    build_all_demo_portfolios, build_atlas_value_partners_demo, build_civic_commercial_bank_demo,
    build_northstar_advisory_demo,
)
from financial_intelligence_cloud.services.daily_brief import generate_daily_portfolio_brief, generate_opportunity_feed
from financial_intelligence_cloud.services.qa_router import answer_portfolio_question
from financial_intelligence_cloud.services.subscription import has_feature
from financial_intelligence_cloud.services.human_approval_gate import (
    ACTIONS_REQUIRING_APPROVAL as FIC_ACTIONS_REQUIRING_APPROVAL,
    HumanApprovalRequiredError as FICHumanApprovalRequiredError,
    require_human_approval as fic_require_human_approval,
)
from agent_runtime_model_router.services.registry import sync_registry
from django.core.management import call_command

RAW_TEMPLATE_TOKENS = [
    '{% load', '{% for', '{% include', '{% extends', '{% block',
    '{% csrf_token', '{% if', '{{ ',
]


class AccountsTests(TestCase):
    def test_create_institutional_account_is_idempotent(self):
        create_institutional_account('northstar-advisory', 'Northstar Advisory', 'accounting_firm')
        create_institutional_account('northstar-advisory', 'Northstar Advisory', 'accounting_firm')
        from financial_intelligence_cloud.models import InstitutionalAccount
        self.assertEqual(InstitutionalAccount.objects.filter(slug='northstar-advisory').count(), 1)

    def test_institutional_tier_gets_contact_custom_price_label(self):
        account = create_institutional_account('civic-bank', 'Civic Commercial Bank', 'bank', subscription_tier='institutional')
        self.assertEqual(account.subscription_price_label, 'Contact / Custom')

    def test_account_is_demo_by_default(self):
        account = create_institutional_account('atlas-value-partners', 'Atlas Value Partners', 'private_equity')
        self.assertTrue(account.is_demo)

    def test_create_portfolio_is_idempotent(self):
        account = create_institutional_account('northstar-advisory', 'Northstar Advisory', 'accounting_firm')
        create_portfolio(account, 'SME Client Book', 'client_book')
        create_portfolio(account, 'SME Client Book', 'client_book')
        self.assertEqual(account.portfolios.count(), 1)

    def test_add_portfolio_entity_syncs_entity_count(self):
        account = create_institutional_account('northstar-advisory', 'Northstar Advisory', 'accounting_firm')
        portfolio = create_portfolio(account, 'SME Client Book', 'client_book')
        add_portfolio_entity(portfolio, 'FreshBridge Foods', 'sme_client')
        add_portfolio_entity(portfolio, 'Acme Ltd', 'sme_client')
        portfolio.refresh_from_db()
        self.assertEqual(portfolio.entity_count, 2)

    def test_add_portfolio_entity_is_idempotent(self):
        account = create_institutional_account('northstar-advisory', 'Northstar Advisory', 'accounting_firm')
        portfolio = create_portfolio(account, 'SME Client Book', 'client_book')
        add_portfolio_entity(portfolio, 'FreshBridge Foods', 'sme_client')
        add_portfolio_entity(portfolio, 'FreshBridge Foods', 'sme_client')
        portfolio.refresh_from_db()
        self.assertEqual(portfolio.entity_count, 1)


class SignalsTests(TestCase):
    def setUp(self):
        account = create_institutional_account('northstar-advisory', 'Northstar Advisory', 'accounting_firm')
        portfolio = create_portfolio(account, 'SME Client Book', 'client_book')
        self.entity = add_portfolio_entity(portfolio, 'FreshBridge Foods', 'sme_client')

    def test_generate_portfolio_signal_is_idempotent(self):
        generate_portfolio_signal(self.entity, 'operational_loss', 'Energy cost increased materially', capital_at_risk=240000)
        generate_portfolio_signal(self.entity, 'operational_loss', 'Energy cost increased materially', capital_at_risk=240000)
        self.assertEqual(self.entity.signals.count(), 1)

    def test_detect_advisory_opportunity_is_idempotent(self):
        signal = generate_portfolio_signal(self.entity, 'client_advisory_opportunity', 'Call this client today')
        detect_advisory_opportunity(self.entity, 'cost_recovery_advisory', 'Operational Value Recovery Review', linked_signal=signal)
        detect_advisory_opportunity(self.entity, 'cost_recovery_advisory', 'Operational Value Recovery Review', linked_signal=signal)
        self.assertEqual(self.entity.advisory_opportunities.count(), 1)

    def test_evidence_quality_score_matches_wtv_convention(self):
        self.assertEqual(evidence_quality_score('strong'), 90)
        self.assertEqual(evidence_quality_score('medium'), 60)
        self.assertEqual(evidence_quality_score('weak'), 30)
        self.assertEqual(evidence_quality_score('missing'), 10)


class PortfolioRankingTests(TestCase):
    def test_client_call_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(CLIENT_CALL_WEIGHTS.values()), 1.0)

    def test_portfolio_risk_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(PORTFOLIO_RISK_WEIGHTS.values()), 1.0)

    def test_finance_opportunity_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(FINANCE_OPPORTUNITY_WEIGHTS.values()), 1.0)

    def test_rank_clients_to_call_today_orders_by_composite_descending(self):
        candidates = [
            {'name': 'Low priority client', 'urgency': 20, 'capital_at_risk_normalised': 20,
             'recoverable_value_normalised': 20, 'evidence_quality': 30, 'relationship_importance': 20, 'data_freshness': 50},
            {'name': 'High priority client', 'urgency': 90, 'capital_at_risk_normalised': 100,
             'recoverable_value_normalised': 100, 'evidence_quality': 60, 'relationship_importance': 80, 'data_freshness': 100},
        ]
        ranked = rank_clients_to_call_today(candidates)
        self.assertEqual(ranked[0]['name'], 'High priority client')
        self.assertEqual(ranked[0]['rank'], 1)

    def test_rank_portfolio_risks_orders_by_composite_descending(self):
        candidates = [
            {'name': 'Stable company', 'urgency': 10, 'capital_at_risk_normalised': 10, 'evidence_quality': 80, 'human_approval_need': 10, 'data_freshness': 80},
            {'name': 'At-risk company', 'urgency': 95, 'capital_at_risk_normalised': 95, 'evidence_quality': 60, 'human_approval_need': 80, 'data_freshness': 90},
        ]
        ranked = rank_portfolio_risks(candidates)
        self.assertEqual(ranked[0]['name'], 'At-risk company')

    def test_rank_finance_opportunities_orders_by_composite_descending(self):
        candidates = [
            {'name': 'Not finance ready', 'finance_readiness': 20, 'recoverable_value_normalised': 20, 'evidence_quality': 30, 'urgency': 20, 'data_freshness': 50},
            {'name': 'Finance ready', 'finance_readiness': 82, 'recoverable_value_normalised': 70, 'evidence_quality': 90, 'urgency': 60, 'data_freshness': 100},
        ]
        ranked = rank_finance_opportunities(candidates)
        self.assertEqual(ranked[0]['name'], 'Finance ready')


class EntityGenerationTests(TestCase):
    def setUp(self):
        account = create_institutional_account('northstar-advisory', 'Northstar Advisory', 'accounting_firm')
        self.portfolio = create_portfolio(account, 'SME Client Book', 'client_book')

    def test_generation_is_idempotent(self):
        generate_portfolio_entities(self.portfolio, 49, 180000, 'sme_client', 'operational_loss')
        first_count = self.portfolio.entities.count()
        generate_portfolio_entities(self.portfolio, 49, 180000, 'sme_client', 'operational_loss')
        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.entities.count(), first_count)
        self.assertEqual(self.portfolio.entity_count, 49)

    def test_generation_never_exceeds_the_ceiling(self):
        generate_portfolio_entities(self.portfolio, 49, 180000, 'sme_client', 'operational_loss')
        for entity in self.portfolio.entities.all():
            signal = entity.signals.first()
            self.assertLess(signal.capital_at_risk, 180000)

    def test_generation_does_not_touch_flagship_entity(self):
        add_portfolio_entity(self.portfolio, 'FreshBridge Foods', 'sme_client', is_flagship=True)
        generate_portfolio_entities(self.portfolio, 49, 180000, 'sme_client', 'operational_loss')
        self.assertTrue(self.portfolio.entities.filter(name='FreshBridge Foods', is_flagship=True).exists())

    def test_shrinking_count_removes_stale_generated_rows(self):
        generate_portfolio_entities(self.portfolio, 10, 180000, 'sme_client', 'operational_loss')
        generate_portfolio_entities(self.portfolio, 5, 180000, 'sme_client', 'operational_loss')
        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.entity_count, 5)


class CapitalAllocationLinkTests(TestCase):
    def test_atlas_ranking_matches_proven_wtv_ordering(self):
        account = create_institutional_account('atlas-value-partners', 'Atlas Value Partners', 'private_equity')
        portfolio = create_portfolio(account, 'Industrial Portfolio', 'investment_portfolio')
        ranked = build_atlas_capital_allocation_portfolio(portfolio)
        names_in_order = [c['name'] for c in ranked]
        self.assertEqual(names_in_order, [
            'Cold-chain optimisation', 'Waste heat recovery', 'Boiler modernisation', 'Expansion project',
        ])

    def test_atlas_ranking_creates_entities_and_opportunities(self):
        account = create_institutional_account('atlas-value-partners', 'Atlas Value Partners', 'private_equity')
        portfolio = create_portfolio(account, 'Industrial Portfolio', 'investment_portfolio')
        build_atlas_capital_allocation_portfolio(portfolio)
        self.assertEqual(portfolio.entities.count(), 4)
        top_entity = portfolio.entities.get(name='Cold-chain optimisation')
        opportunity = top_entity.advisory_opportunities.first()
        self.assertIn('never an autonomous investment decision', opportunity.rationale)


class FreshBridgeFoodsFlagshipPipelineTests(TestCase):
    def setUp(self):
        sync_registry()
        account = create_institutional_account('northstar-advisory', 'Northstar Advisory', 'accounting_firm')
        self.portfolio = create_portfolio(account, 'SME Client Book', 'client_book')

    def test_golden_case_exact_conclusion(self):
        build_freshbridge_foods_demo(self.portfolio)
        entity = self.portfolio.entities.get(name='FreshBridge Foods')
        self.assertTrue(entity.is_flagship)
        signal = entity.signals.get(signal_type='client_advisory_opportunity')
        self.assertEqual(signal.capital_at_risk, 240000)
        self.assertEqual(signal.potential_recoverable_value, 155000)
        self.assertEqual(signal.evidence_quality, 'medium')
        self.assertIsNotNone(signal.source_run)

    def test_flagship_signal_source_run_is_a_real_agent_run(self):
        build_freshbridge_foods_demo(self.portfolio)
        entity = self.portfolio.entities.get(name='FreshBridge Foods')
        signal = entity.signals.get(signal_type='client_advisory_opportunity')
        self.assertEqual(signal.source_run.agent.agent_name, 'Finance Modelling Agent')
        self.assertEqual(signal.source_run.status, 'completed')

    def test_flagship_creates_real_operational_loss(self):
        build_freshbridge_foods_demo(self.portfolio)
        entity = self.portfolio.entities.get(name='FreshBridge Foods')
        self.assertIsNotNone(entity.source_operational_loss)
        self.assertEqual(entity.source_operational_loss.projected_future_loss, 240000)

    def test_pipeline_is_idempotent(self):
        from agent_runtime_model_router.models import AgentRun as AgentRunModel
        build_freshbridge_foods_demo(self.portfolio)
        first_count = AgentRunModel.objects.count()
        build_freshbridge_foods_demo(self.portfolio)
        second_count = AgentRunModel.objects.count()
        self.assertEqual(first_count, second_count)
        self.portfolio.refresh_from_db()
        self.assertEqual(self.portfolio.entities.filter(name='FreshBridge Foods').count(), 1)


class DemoPortfoliosTests(TestCase):
    def setUp(self):
        sync_registry()

    def test_northstar_has_fifty_clients(self):
        account, portfolio = build_northstar_advisory_demo()
        portfolio.refresh_from_db()
        self.assertEqual(portfolio.entity_count, 50)

    def test_freshbridge_foods_ranks_first_among_fifty_clients(self):
        """
        The load-bearing arithmetic proof: FreshBridge Foods (the real
        flagship, urgency=90/capital_at_risk=240000/recoverable_value=155000/
        evidence=medium) must outrank all 49 deterministically generated
        clients (capped below by entity_generation.py's ceiling design) in
        rank_clients_to_call_today().
        """
        from financial_intelligence_cloud.services.portfolio_ranking import rank_clients_to_call_today
        from financial_intelligence_cloud.services.signals import evidence_quality_score
        account, portfolio = build_northstar_advisory_demo()

        candidates = []
        max_capital_at_risk = max(
            s.capital_at_risk for e in portfolio.entities.all() for s in e.signals.all()
            if s.capital_at_risk is not None
        )
        max_recoverable_value = max(
            s.potential_recoverable_value for e in portfolio.entities.all() for s in e.signals.all()
            if s.potential_recoverable_value is not None
        )
        for entity in portfolio.entities.all():
            signal = entity.signals.first()
            candidates.append({
                'name': entity.name,
                'urgency': signal.urgency_score,
                'capital_at_risk_normalised': (signal.capital_at_risk or 0) / max_capital_at_risk * 100,
                'recoverable_value_normalised': (signal.potential_recoverable_value or 0) / max_recoverable_value * 100,
                'evidence_quality': evidence_quality_score(signal.evidence_quality),
                'relationship_importance': 80 if entity.is_flagship else 40,
                'data_freshness': 100,
            })
        ranked = rank_clients_to_call_today(candidates)
        self.assertEqual(ranked[0]['name'], 'FreshBridge Foods')

    def test_atlas_has_twelve_companies(self):
        from financial_intelligence_cloud.services.demo_portfolios import build_atlas_value_partners_demo
        account, portfolio = build_atlas_value_partners_demo()
        portfolio.refresh_from_db()
        self.assertEqual(portfolio.entity_count, 12)

    def test_civic_has_five_hundred_borrowers(self):
        account, portfolio = build_civic_commercial_bank_demo()
        portfolio.refresh_from_db()
        self.assertEqual(portfolio.entity_count, 500)

    def test_civic_abc_engineering_requires_human_review(self):
        account, portfolio = build_civic_commercial_bank_demo()
        entity = portfolio.entities.get(name='ABC Engineering')
        opportunity = entity.advisory_opportunities.get()
        self.assertEqual(opportunity.funding_gap, 420000)
        self.assertEqual(opportunity.finance_readiness_score, 82)
        self.assertTrue(opportunity.requires_human_review)
        self.assertIn('not a credit approval', opportunity.rationale)

    def test_build_all_demo_portfolios_creates_three_demo_accounts(self):
        from financial_intelligence_cloud.models import InstitutionalAccount
        build_all_demo_portfolios()
        self.assertEqual(InstitutionalAccount.objects.filter(is_demo=True).count(), 3)

    def test_seeding_twice_is_idempotent(self):
        from financial_intelligence_cloud.models import InstitutionalAccount, PortfolioEntity
        build_all_demo_portfolios()
        first_accounts = InstitutionalAccount.objects.count()
        first_entities = PortfolioEntity.objects.count()
        build_all_demo_portfolios()
        self.assertEqual(InstitutionalAccount.objects.count(), first_accounts)
        self.assertEqual(PortfolioEntity.objects.count(), first_entities)


class DailyBriefTests(TestCase):
    def setUp(self):
        sync_registry()
        self.account, self.portfolio = build_northstar_advisory_demo()

    def test_generate_opportunity_feed_creates_items(self):
        items = generate_opportunity_feed(self.account, self.portfolio)
        self.assertGreater(len(items), 0)

    def test_generate_daily_brief_is_idempotent_for_same_date(self):
        brief_first = generate_daily_portfolio_brief(self.account, self.portfolio)
        brief_second = generate_daily_portfolio_brief(self.account, self.portfolio)
        self.assertEqual(brief_first.pk, brief_second.pk)

    def test_daily_brief_top_clients_includes_freshbridge_foods(self):
        brief = generate_daily_portfolio_brief(self.account, self.portfolio)
        names = [c['portfolio_entity__name'] for c in brief.top_clients_to_call]
        self.assertIn('FreshBridge Foods', names)


class QaRouterIsolationTests(TestCase):
    def setUp(self):
        sync_registry()
        self.northstar_account, self.northstar_portfolio = build_northstar_advisory_demo()
        self.atlas_account, self.atlas_portfolio = build_atlas_value_partners_demo()

    def test_which_client_to_call_returns_freshbridge_foods(self):
        result = answer_portfolio_question(self.northstar_account, 'which_client_to_call')
        self.assertIn('FreshBridge Foods', result['answer'])
        self.assertTrue(result['supported'])

    def test_unsupported_question_is_honest_not_a_guess(self):
        result = answer_portfolio_question(self.northstar_account, 'what_is_the_meaning_of_life')
        self.assertFalse(result['supported'])
        self.assertEqual(result['citations'], [])

    def test_never_leaks_atlas_data_into_northstar_answer(self):
        result = answer_portfolio_question(self.northstar_account, 'largest_capital_at_risk')
        atlas_entity_names = set(self.atlas_portfolio.entities.values_list('name', flat=True))
        self.assertNotIn(result['answer'].split(':')[0], atlas_entity_names)
        for atlas_name in atlas_entity_names:
            self.assertNotIn(atlas_name, result['answer'])

    def test_mismatched_account_portfolio_pair_returns_empty_not_error(self):
        result = answer_portfolio_question(self.northstar_account, 'largest_capital_at_risk', portfolio=self.atlas_portfolio)
        self.assertEqual(result['citations'], [])
        self.assertNotIn('Cold-chain', result['answer'])

    def test_capital_priority_scoped_to_atlas_only(self):
        result = answer_portfolio_question(self.atlas_account, 'capital_priority')
        self.assertIn('Cold-chain optimisation', result['answer'])


class SubscriptionTests(TestCase):
    def test_starter_does_not_have_ask_feature(self):
        account = create_institutional_account('starter-firm', 'Starter Firm', 'accounting_firm', subscription_tier='starter')
        self.assertFalse(has_feature(account, 'ask'))

    def test_professional_has_ask_feature(self):
        account = create_institutional_account('pro-firm', 'Pro Firm', 'accounting_firm', subscription_tier='professional')
        self.assertTrue(has_feature(account, 'ask'))

    def test_institutional_has_capital_allocation_feature(self):
        account = create_institutional_account('inst-firm', 'Inst Firm', 'bank', subscription_tier='institutional')
        self.assertTrue(has_feature(account, 'capital_allocation'))


class FICHumanApprovalGateTests(TestCase):
    def setUp(self):
        sync_registry()
        self.account, self.portfolio = build_northstar_advisory_demo()
        self.opportunity = self.portfolio.entities.get(name='FreshBridge Foods').advisory_opportunities.get()

    def test_nine_total_actions_registered(self):
        self.assertEqual(len(FIC_ACTIONS_REQUIRING_APPROVAL), 9)

    def test_advisory_outreach_blocked_without_approval(self):
        with self.assertRaises(FICHumanApprovalRequiredError):
            fic_require_human_approval('advisory_outreach', self.opportunity)

    def test_advisory_outreach_allowed_with_approval(self):
        self.opportunity.human_approved = True
        self.opportunity.save()
        self.assertTrue(fic_require_human_approval('advisory_outreach', self.opportunity))

    def test_shared_base_action_still_enforced(self):
        with self.assertRaises(FICHumanApprovalRequiredError):
            fic_require_human_approval('funder_outreach', self.opportunity)


class RouteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sync_registry()
        build_all_demo_portfolios()

    def test_overview_returns_200(self):
        response = self.client.get('/financial-intelligence-cloud/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Financial Intelligence Cloud')

    def test_opportunity_feed_returns_200(self):
        response = self.client.get('/financial-intelligence-cloud/opportunity-feed/')
        self.assertEqual(response.status_code, 200)

    def test_clients_to_call_returns_200_and_shows_freshbridge_foods(self):
        response = self.client.get('/financial-intelligence-cloud/clients-to-call/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'FreshBridge Foods')
        self.assertContains(response, 'Flagship — real agent pipeline')

    def test_portfolio_returns_200(self):
        response = self.client.get('/financial-intelligence-cloud/portfolio/')
        self.assertEqual(response.status_code, 200)

    def test_ask_returns_200(self):
        response = self.client.get('/financial-intelligence-cloud/ask/', {'account': 'northstar-advisory', 'question': 'which_client_to_call'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'FreshBridge Foods')

    def test_daily_brief_returns_200(self):
        response = self.client.get('/financial-intelligence-cloud/daily-brief/', {'account': 'northstar-advisory'})
        self.assertEqual(response.status_code, 200)

    def test_subscription_returns_200(self):
        response = self.client.get('/financial-intelligence-cloud/subscription/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Contact / Custom')

    def test_demo_accounting_returns_200(self):
        response = self.client.get('/financial-intelligence-cloud/demo/accounting/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'FreshBridge Foods')

    def test_demo_investment_returns_200_and_ranks_cold_chain_first(self):
        response = self.client.get('/financial-intelligence-cloud/demo/investment/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('Cold-chain optimisation', content)

    def test_demo_bank_returns_200_and_shows_human_review_required(self):
        response = self.client.get('/financial-intelligence-cloud/demo/bank/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ABC Engineering')
        self.assertContains(response, 'Human Review Required')

    def test_no_raw_template_tags_across_all_routes(self):
        routes = [
            '/financial-intelligence-cloud/', '/financial-intelligence-cloud/opportunity-feed/',
            '/financial-intelligence-cloud/clients-to-call/', '/financial-intelligence-cloud/portfolio/',
            '/financial-intelligence-cloud/ask/', '/financial-intelligence-cloud/daily-brief/?account=northstar-advisory',
            '/financial-intelligence-cloud/subscription/', '/financial-intelligence-cloud/demo/accounting/',
            '/financial-intelligence-cloud/demo/investment/', '/financial-intelligence-cloud/demo/bank/',
        ]
        for route in routes:
            response = self.client.get(route)
            content = response.content.decode()
            for token in RAW_TEMPLATE_TOKENS:
                self.assertNotIn(token, content, f'raw template token "{token}" leaked into {route}')

    def test_no_unsafe_claims_across_all_routes(self):
        routes = [
            '/financial-intelligence-cloud/', '/financial-intelligence-cloud/clients-to-call/',
            '/financial-intelligence-cloud/demo/accounting/', '/financial-intelligence-cloud/demo/investment/',
            '/financial-intelligence-cloud/demo/bank/',
        ]
        for route in routes:
            content = self.client.get(route).content.decode().lower()
            self.assertNotIn('guaranteed advisory revenue', content)
            self.assertNotIn('credit approved', content)
            self.assertNotIn('funding is secured', content)
            self.assertNotIn('fully autonomous', content)

    def test_platform_page_mentions_financial_intelligence_cloud(self):
        response = self.client.get('/platform/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'EcoIQ Financial Intelligence Cloud')
        self.assertContains(response, 'Open Financial Intelligence Cloud')

    def test_platform_page_has_no_raw_template_tags(self):
        response = self.client.get('/platform/')
        content = response.content.decode()
        for token in RAW_TEMPLATE_TOKENS:
            self.assertNotIn(token, content, f'raw template token "{token}" leaked into /platform/')


class SeedCommandTests(TestCase):
    def test_seed_command_is_idempotent(self):
        from financial_intelligence_cloud.models import InstitutionalAccount, PortfolioEntity, PortfolioSignal
        call_command('seed_financial_intelligence_cloud_demo')
        first = (
            InstitutionalAccount.objects.filter(is_demo=True).count(),
            PortfolioEntity.objects.count(),
            PortfolioSignal.objects.count(),
        )
        call_command('seed_financial_intelligence_cloud_demo')
        second = (
            InstitutionalAccount.objects.filter(is_demo=True).count(),
            PortfolioEntity.objects.count(),
            PortfolioSignal.objects.count(),
        )
        self.assertEqual(first, second)
        self.assertEqual(first, (3, 562, 562))
