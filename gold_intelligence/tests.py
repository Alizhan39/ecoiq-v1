"""
gold_intelligence/tests.py — EcoIQ's first flagship vertical: Kazakhstan
Gold Investment Intelligence.

Every test here is built around the platform's core discipline for this
app: no computed financial figure may ever be fabricated. Tests assert
either a real, independently-verifiable number (IRR/NPV/payback computed
by hand against a known cash-flow shape) or an honest
"Data source required"/`available: False` result when a required real
input is missing — never a plausible-looking guess.
"""
import datetime

from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from countries.models import CountryProfile
from gold_intelligence.models import (
    CapitalBudgetLine, EquipmentSpec, GoldProject, MineTimelineMilestone, ScenarioAssumption,
)
from gold_intelligence.services import aggregates, project_finance, risk_intelligence


class GoldProjectModelTests(TestCase):
    def setUp(self):
        self.kz = CountryProfile.objects.create(name='Kazakhstan', slug='kazakhstan', iso_code='KZ', is_published=True)

    def test_str_and_demo_default(self):
        project = GoldProject.objects.create(name='Test Project', slug='test-project', country=self.kz)
        self.assertEqual(str(project), 'Test Project')
        self.assertTrue(project.is_demo)   # honesty default, matches geo_intelligence's own convention

    def test_every_financial_field_defaults_to_null_never_fabricated(self):
        project = GoldProject.objects.create(name='Bare Project', slug='bare-project', country=self.kz)
        for field in (
            'total_capex_usd', 'annual_opex_usd', 'cash_cost_usd_per_oz', 'aisc_usd_per_oz',
            'gold_price_assumption_usd_per_oz', 'discount_rate_pct', 'ore_grade_g_per_tonne',
            'resource_tonnes', 'recovery_rate_pct', 'mine_life_years', 'expected_annual_production_oz',
        ):
            self.assertIsNone(getattr(project, field), f'{field} should default to None, never a fabricated value')

    def test_geo_assets_reads_real_geoasset_rows_via_soft_reference(self):
        from geo_intelligence.models import GeoAsset
        project = GoldProject.objects.create(name='Test Project', slug='test-project-2', country=self.kz)
        GeoAsset.objects.create(
            name='Test Deposit', asset_type='gold_deposit', latitude=49.9, longitude=82.6,
            source_reference=f'gold_intelligence.GoldProject:{project.slug}',
        )
        GeoAsset.objects.create(name='Unrelated Asset', asset_type='factory', latitude=1.0, longitude=2.0)
        self.assertEqual(project.geo_assets.count(), 1)
        self.assertEqual(project.geo_assets.first().name, 'Test Deposit')

    def test_risk_zones_scoped_to_project_country(self):
        from geo_intelligence.models import GeoRiskZone
        other_country = CountryProfile.objects.create(name='United Kingdom', slug='united-kingdom', iso_code='GB', is_published=True)
        project = GoldProject.objects.create(name='Test Project', slug='test-project-3', country=self.kz)
        GeoRiskZone.objects.create(name='KZ Zone', risk_type='drought', country=self.kz, latitude=49.9, longitude=82.6)
        GeoRiskZone.objects.create(name='GB Zone', risk_type='flood', country=other_country, latitude=54.0, longitude=-2.0)
        self.assertEqual(project.risk_zones.count(), 1)
        self.assertEqual(project.risk_zones.first().name, 'KZ Zone')

    def test_risk_zones_empty_when_no_country_set(self):
        project = GoldProject.objects.create(name='No Country Project', slug='no-country-project')
        self.assertEqual(project.risk_zones.count(), 0)


class CapitalBudgetLineModelTests(TestCase):
    def setUp(self):
        self.project = GoldProject.objects.create(name='Test Project', slug='cbl-test-project')

    def test_remaining_usd_computed_from_real_fields(self):
        line = CapitalBudgetLine.objects.create(project=self.project, label='Crusher', planned_usd=1_000_000, spent_usd=400_000)
        self.assertEqual(line.remaining_usd, 600_000)

    def test_remaining_usd_none_when_either_field_missing(self):
        line = CapitalBudgetLine.objects.create(project=self.project, label='Crusher', planned_usd=1_000_000)
        self.assertIsNone(line.remaining_usd)

    def test_variance_usd_computed_from_real_fields(self):
        line = CapitalBudgetLine.objects.create(project=self.project, label='Crusher', planned_usd=1_000_000, committed_usd=1_100_000)
        self.assertEqual(line.variance_usd, 100_000)

    def test_variance_usd_none_when_either_field_missing(self):
        line = CapitalBudgetLine.objects.create(project=self.project, label='Crusher')
        self.assertIsNone(line.variance_usd)


BASE_CASE_KWARGS = dict(
    total_capex_usd=100_000_000, expected_annual_production_oz=100_000,
    gold_price_assumption_usd_per_oz=2000, aisc_usd_per_oz=1400,
    mine_life_years=8, discount_rate_pct=8,
)


class ProjectFinanceServiceTests(TestCase):
    def setUp(self):
        self.project = GoldProject(name='PF Test', slug='pf-test', **BASE_CASE_KWARGS)

    def test_missing_capex_is_honestly_unavailable(self):
        project = GoldProject(name='x', slug='x', expected_annual_production_oz=1, gold_price_assumption_usd_per_oz=1, aisc_usd_per_oz=1, mine_life_years=1)
        result = project_finance.build_cash_flow_series(project)
        self.assertFalse(result['available'])
        self.assertIn('CAPEX', result['reason'])

    def test_missing_cost_basis_is_honestly_unavailable(self):
        project = GoldProject(
            name='x', slug='x', total_capex_usd=1, expected_annual_production_oz=1,
            gold_price_assumption_usd_per_oz=1, mine_life_years=1,
        )
        result = project_finance.build_cash_flow_series(project)
        self.assertFalse(result['available'])
        self.assertIn('AISC or cash cost', result['reason'])

    def test_prefers_aisc_over_cash_cost_and_reports_which_was_used(self):
        project = GoldProject(
            name='x', slug='x', total_capex_usd=1, expected_annual_production_oz=1, mine_life_years=1,
            gold_price_assumption_usd_per_oz=2000, aisc_usd_per_oz=1400, cash_cost_usd_per_oz=900,
        )
        result = project_finance.build_cash_flow_series(project)
        self.assertEqual(result['cost_basis'], 'aisc')

    def test_falls_back_to_cash_cost_when_aisc_missing(self):
        project = GoldProject(
            name='x', slug='x', total_capex_usd=1, expected_annual_production_oz=1, mine_life_years=1,
            gold_price_assumption_usd_per_oz=2000, cash_cost_usd_per_oz=900,
        )
        result = project_finance.build_cash_flow_series(project)
        self.assertEqual(result['cost_basis'], 'cash_cost')

    def test_npv_matches_hand_calculated_annuity(self):
        # PV of an 8-year, $60M/yr annuity at 8%, minus $100M CAPEX.
        cash_flows = [-100_000_000] + [60_000_000] * 8
        npv = project_finance.compute_npv(cash_flows, 8.0)
        annuity_factor = sum(1 / (1.08 ** t) for t in range(1, 9))
        expected = round(-100_000_000 + 60_000_000 * annuity_factor, 2)
        self.assertAlmostEqual(npv, expected, places=0)

    def test_irr_root_is_a_genuine_zero_of_npv(self):
        cash_flows = [-100_000_000] + [60_000_000] * 8
        irr = project_finance.compute_irr(cash_flows)
        self.assertIsNotNone(irr)
        npv_at_irr = project_finance.compute_npv(cash_flows, irr)
        self.assertAlmostEqual(npv_at_irr, 0, delta=10000)   # near-zero relative to $100M+ scale (rounding to 2dp on the IRR% itself)

    def test_irr_none_for_all_positive_cash_flows(self):
        self.assertIsNone(project_finance.compute_irr([100, 100, 100]))

    def test_irr_none_when_never_profitable(self):
        # AISC exceeds gold price — genuinely no positive-return root exists.
        cash_flows = [-100_000_000] + [-40_000_000] * 8
        self.assertIsNone(project_finance.compute_irr(cash_flows))

    def test_payback_matches_hand_calculation(self):
        # -100M, +60M, +60M, ... crosses zero between year 1 and 2: 40M/60M = 0.667
        cash_flows = [-100_000_000, 60_000_000, 60_000_000]
        self.assertEqual(project_finance.compute_payback_years(cash_flows), 1.67)

    def test_payback_none_when_never_recovered(self):
        cash_flows = [-100_000_000, 10_000_000]
        self.assertIsNone(project_finance.compute_payback_years(cash_flows))

    def test_compute_project_economics_full_real_case(self):
        result = project_finance.compute_project_economics(self.project)
        self.assertTrue(result['available'])
        self.assertEqual(result['capex_usd'], 100_000_000)
        self.assertIsNotNone(result['irr_pct'])
        self.assertIsNotNone(result['npv_usd'])
        self.assertIsNotNone(result['payback_years'])

    def test_npv_unavailable_reason_when_no_discount_rate(self):
        project = GoldProject(name='x', slug='x', **{**BASE_CASE_KWARGS, 'discount_rate_pct': None})
        result = project_finance.compute_project_economics(project)
        self.assertIsNone(result['npv_usd'])
        self.assertIn('discount rate', result['npv_unavailable_reason'])

    def test_never_writes_to_the_database(self):
        project = GoldProject.objects.create(name='Persisted', slug='pf-persisted', **BASE_CASE_KWARGS)
        original_capex = project.total_capex_usd
        project_finance.compute_project_economics(project)
        project_finance.run_sensitivity_analysis(project)
        project.refresh_from_db()
        self.assertEqual(project.total_capex_usd, original_capex)


class SensitivityAnalysisTests(TestCase):
    def setUp(self):
        self.project = GoldProject(name='Sens Test', slug='sens-test', **BASE_CASE_KWARGS)

    def test_unavailable_when_base_case_unavailable(self):
        project = GoldProject(name='x', slug='x')
        result = project_finance.run_sensitivity_analysis(project)
        self.assertFalse(result['available'])

    def test_skips_variables_with_no_real_base_value(self):
        # cash_cost_usd_per_oz is not set on this project (only AISC is)
        result = project_finance.run_sensitivity_analysis(self.project)
        fields = {v['field'] for v in result['variables']}
        self.assertNotIn('cash_cost_usd_per_oz', fields)

    def test_includes_variables_with_a_real_base_value(self):
        result = project_finance.run_sensitivity_analysis(self.project)
        fields = {v['field'] for v in result['variables']}
        self.assertIn('gold_price_assumption_usd_per_oz', fields)
        self.assertIn('total_capex_usd', fields)

    def test_variables_sorted_by_impact_descending(self):
        result = project_finance.run_sensitivity_analysis(self.project)
        spreads = []
        for v in result['variables']:
            values = [x for x in (v['low_irr_pct'], v['high_irr_pct']) if x is not None]
            spreads.append(max(values) - min(values) if values else 0)
        self.assertEqual(spreads, sorted(spreads, reverse=True))

    def test_never_writes_to_the_database(self):
        project = GoldProject.objects.create(name='Persisted', slug='sens-persisted', **BASE_CASE_KWARGS)
        project_finance.run_sensitivity_analysis(project)
        project.refresh_from_db()
        self.assertEqual(project.gold_price_assumption_usd_per_oz, 2000)


class ScenarioAnalysisTests(TestCase):
    def setUp(self):
        self.project = GoldProject.objects.create(name='Scenario Test', slug='scenario-test', **BASE_CASE_KWARGS)

    def test_no_scenarios_returns_empty_list(self):
        result = project_finance.run_scenario_analysis(self.project)
        self.assertTrue(result['available'])
        self.assertEqual(result['scenarios'], [])

    def test_gold_price_override_changes_irr(self):
        ScenarioAssumption.objects.create(project=self.project, name='Gold price -20%', gold_price_usd_per_oz=1600)
        result = project_finance.run_scenario_analysis(self.project)
        scenario = result['scenarios'][0]
        self.assertNotEqual(scenario['irr_pct'], result['base_case']['irr_pct'])

    def test_capex_multiplier_scales_real_capex(self):
        ScenarioAssumption.objects.create(project=self.project, name='CAPEX overrun', capex_multiplier=1.5)
        result = project_finance.run_scenario_analysis(self.project)
        self.assertEqual(result['scenarios'][0]['capex_usd'], 150_000_000)

    def test_scenario_never_mutates_the_real_project(self):
        ScenarioAssumption.objects.create(project=self.project, name='CAPEX overrun', capex_multiplier=1.5)
        project_finance.run_scenario_analysis(self.project)
        self.project.refresh_from_db()
        self.assertEqual(self.project.total_capex_usd, 100_000_000)

    def test_null_scenario_fields_do_not_override_base_case(self):
        # a scenario with every field null should reproduce the base case exactly
        ScenarioAssumption.objects.create(project=self.project, name='No changes')
        result = project_finance.run_scenario_analysis(self.project)
        self.assertEqual(result['scenarios'][0]['irr_pct'], result['base_case']['irr_pct'])


class RiskIntelligenceServiceTests(TestCase):
    def setUp(self):
        self.kz = CountryProfile.objects.create(name='Kazakhstan', slug='kazakhstan', iso_code='KZ', is_published=True)
        self.project = GoldProject.objects.create(name='Risk Test', slug='risk-test', country=self.kz)

    def test_all_eleven_dimensions_present(self):
        result = risk_intelligence.compute_risk_intelligence(self.project)
        self.assertEqual(set(result.keys()), {
            'political', 'environmental', 'climate', 'water', 'energy', 'infrastructure',
            'community', 'supply_chain', 'financial', 'construction', 'operational',
        })

    def test_five_dimensions_are_honest_stubs_with_no_data(self):
        result = risk_intelligence.compute_risk_intelligence(self.project)
        for key in ('community', 'supply_chain', 'financial', 'construction', 'operational'):
            self.assertFalse(result[key]['available'])
            self.assertIsNone(result[key]['level'])
            self.assertIn('reason', result[key])

    def test_political_dimension_reflects_real_country_score(self):
        self.kz.policy_environment_score = 70.0
        self.kz.save()
        result = risk_intelligence.compute_risk_intelligence(self.project)
        self.assertTrue(result['political']['available'])
        self.assertEqual(result['political']['level'], 'low')

    def test_political_dimension_unavailable_with_no_country(self):
        project = GoldProject.objects.create(name='No Country', slug='no-country-risk')
        result = risk_intelligence.compute_risk_intelligence(project)
        self.assertFalse(result['political']['available'])

    def test_climate_dimension_reflects_real_geo_risk_zone(self):
        from geo_intelligence.models import GeoRiskZone
        GeoRiskZone.objects.create(name='Heat Zone', risk_type='extreme_heat', country=self.kz, latitude=49.9, longitude=82.6, severity='high')
        result = risk_intelligence.compute_risk_intelligence(self.project)
        self.assertTrue(result['climate']['available'])
        self.assertEqual(result['climate']['level'], 'high')

    def test_water_dimension_unavailable_with_no_water_stress_zone(self):
        result = risk_intelligence.compute_risk_intelligence(self.project)
        self.assertFalse(result['water']['available'])

    def test_energy_dimension_reflects_real_power_plant_asset(self):
        from geo_intelligence.models import GeoAsset
        GeoAsset.objects.create(name='Substation', asset_type='power_plant', country=self.kz, latitude=49.9, longitude=82.6)
        result = risk_intelligence.compute_risk_intelligence(self.project)
        self.assertTrue(result['energy']['available'])
        self.assertEqual(result['energy']['asset_count'], 1)

    def test_never_modifies_any_real_data(self):
        before = self.kz.policy_environment_score
        risk_intelligence.compute_risk_intelligence(self.project)
        self.kz.refresh_from_db()
        self.assertEqual(self.kz.policy_environment_score, before)


class AggregatesServiceTests(TestCase):
    def setUp(self):
        self.project = GoldProject.objects.create(name='Agg Test', slug='agg-test')

    def test_capital_tracker_unavailable_with_no_lines(self):
        result = aggregates.capital_tracker_summary(self.project)
        self.assertFalse(result['available'])

    def test_capital_tracker_sums_real_lines(self):
        CapitalBudgetLine.objects.create(project=self.project, label='A', planned_usd=1_000_000, spent_usd=400_000)
        CapitalBudgetLine.objects.create(project=self.project, label='B', planned_usd=2_000_000, spent_usd=600_000)
        result = aggregates.capital_tracker_summary(self.project)
        self.assertTrue(result['available'])
        self.assertEqual(result['planned_usd'], 3_000_000)
        self.assertEqual(result['spent_usd'], 1_000_000)
        self.assertEqual(result['remaining_usd'], 2_000_000)

    def test_equipment_summary_unavailable_with_no_specs(self):
        result = aggregates.equipment_summary(self.project)
        self.assertFalse(result['available'])

    def test_equipment_summary_sums_real_specs(self):
        EquipmentSpec.objects.create(project=self.project, equipment_type='crusher', capex_usd=1_000_000, power_usage_kw=500)
        EquipmentSpec.objects.create(project=self.project, equipment_type='mill', capex_usd=2_000_000, power_usage_kw=1500)
        result = aggregates.equipment_summary(self.project)
        self.assertEqual(result['total_capex_usd'], 3_000_000)
        self.assertEqual(result['total_power_usage_kw'], 2000)

    def test_timeline_summary_unavailable_with_no_milestones(self):
        result = aggregates.timeline_summary(self.project)
        self.assertFalse(result['available'])

    def test_timeline_summary_lists_real_milestones(self):
        MineTimelineMilestone.objects.create(project=self.project, phase='exploration', status='complete')
        result = aggregates.timeline_summary(self.project)
        self.assertTrue(result['available'])
        self.assertEqual(len(result['milestones']), 1)


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME='localhost')
        self.kz = CountryProfile.objects.create(name='Kazakhstan', slug='kazakhstan', iso_code='KZ', is_published=True)
        self.project = GoldProject.objects.create(
            name='View Test Project', slug='view-test-project', country=self.kz, is_demo=True, **BASE_CASE_KWARGS,
        )

    def _all_project_urls(self):
        return [
            reverse('gold_intelligence:investor_view', args=[self.project.slug]),
            reverse('gold_intelligence:investment_dashboard', args=[self.project.slug]),
            reverse('gold_intelligence:risk_intelligence', args=[self.project.slug]),
            reverse('gold_intelligence:timeline', args=[self.project.slug]),
            reverse('gold_intelligence:capital_tracker', args=[self.project.slug]),
            reverse('gold_intelligence:equipment_intelligence', args=[self.project.slug]),
        ]

    def test_directory_returns_200(self):
        r = self.client.get(reverse('gold_intelligence:directory'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'View Test Project')

    def test_mine_map_returns_200(self):
        r = self.client.get(reverse('gold_intelligence:mine_map'))
        self.assertEqual(r.status_code, 200)

    def test_all_project_pages_return_200(self):
        for url in self._all_project_urls():
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 200)

    def test_unknown_project_slug_404s(self):
        r = self.client.get(reverse('gold_intelligence:investor_view', args=['not-a-real-project']))
        self.assertEqual(r.status_code, 404)

    def test_demo_badge_shown_on_investor_view(self):
        r = self.client.get(reverse('gold_intelligence:investor_view', args=[self.project.slug]))
        self.assertContains(r, 'gold-demo-badge')

    def test_investment_dashboard_shows_real_computed_irr(self):
        r = self.client.get(reverse('gold_intelligence:investment_dashboard', args=[self.project.slug]))
        economics = project_finance.compute_project_economics(self.project)
        self.assertContains(r, str(economics['irr_pct']))

    def test_honest_data_source_required_shown_for_missing_fields(self):
        bare_project = GoldProject.objects.create(name='Bare', slug='bare-view-project')
        r = self.client.get(reverse('gold_intelligence:investment_dashboard', args=[bare_project.slug]))
        self.assertContains(r, 'Data source required')

    def test_risk_intelligence_shows_honest_stub_dimensions(self):
        r = self.client.get(reverse('gold_intelligence:risk_intelligence', args=[self.project.slug]))
        self.assertContains(r, 'Data source required')

    def test_no_raw_template_tags_leak_on_any_page(self):
        for url in self._all_project_urls() + [reverse('gold_intelligence:directory'), reverse('gold_intelligence:mine_map')]:
            with self.subTest(url=url):
                r = self.client.get(url)
                content = r.content.decode()
                self.assertNotIn('{%', content)
                self.assertNotIn('{{', content)

    def test_decision_studio_links_use_the_real_existing_route(self):
        r = self.client.get(reverse('gold_intelligence:investor_view', args=[self.project.slug]))
        self.assertContains(r, '/decision-studio/?q=')

    def test_ask_ai_agent_links_use_the_real_existing_workbench_route(self):
        r = self.client.get(reverse('gold_intelligence:investor_view', args=[self.project.slug]))
        # investor view links to a decision-studio question; the investment
        # dashboard/mine map both surface real, existing action routes only.
        self.assertNotContains(r, '/ai-agents/gold-agent/')   # never a fabricated new agent route


class SeedCommandTests(TestCase):
    def setUp(self):
        call_command('seed_countries')

    def test_seed_creates_one_demo_project(self):
        call_command('seed_gold_intelligence_demo')
        self.assertEqual(GoldProject.objects.filter(slug='kazakhstan-gold-project-demo').count(), 1)
        project = GoldProject.objects.get(slug='kazakhstan-gold-project-demo')
        self.assertTrue(project.is_demo)

    def test_seed_is_idempotent(self):
        call_command('seed_gold_intelligence_demo')
        call_command('seed_gold_intelligence_demo')
        self.assertEqual(GoldProject.objects.filter(slug='kazakhstan-gold-project-demo').count(), 1)
        project = GoldProject.objects.get(slug='kazakhstan-gold-project-demo')
        self.assertEqual(project.capital_budget_lines.count(), 5)
        self.assertEqual(project.timeline_milestones.count(), 6)
        self.assertEqual(project.equipment_specs.count(), 7)
        self.assertEqual(project.scenarios.count(), 4)

    def test_seeded_geo_assets_are_flagged_demo(self):
        from geo_intelligence.models import GeoAsset
        call_command('seed_gold_intelligence_demo')
        project = GoldProject.objects.get(slug='kazakhstan-gold-project-demo')
        for asset in project.geo_assets:
            self.assertTrue(asset.is_demo)

    def test_seeded_project_economics_are_real_computable(self):
        call_command('seed_gold_intelligence_demo')
        project = GoldProject.objects.get(slug='kazakhstan-gold-project-demo')
        result = project_finance.compute_project_economics(project)
        self.assertTrue(result['available'])
        self.assertIsNotNone(result['irr_pct'])

    def test_missing_kazakhstan_profile_is_handled_honestly(self):
        CountryProfile.objects.filter(iso_code='KZ').delete()
        call_command('seed_gold_intelligence_demo')
        self.assertEqual(GoldProject.objects.filter(slug='kazakhstan-gold-project-demo').count(), 0)


class AdminTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.admin_user = User.objects.create_superuser('gold-admin', 'gold-admin@example.com', 'password123')
        self.client.force_login(self.admin_user)
        self.project = GoldProject.objects.create(name='Admin Test Project', slug='admin-test-project')

    def test_project_list_visible_in_admin(self):
        r = self.client.get('/admin/gold_intelligence/goldproject/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Admin Test Project')

    def test_capital_budget_line_list_visible_in_admin(self):
        CapitalBudgetLine.objects.create(project=self.project, label='Test Line', planned_usd=1000)
        r = self.client.get('/admin/gold_intelligence/capitalbudgetline/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Test Line')
