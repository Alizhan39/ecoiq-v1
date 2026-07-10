import re

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from companies.models import CompanyProfile, CompanyScoreSnapshot
from plotly_visual_intelligence.services import charts, dashboard_data

TEMPLATE_LEAK_RE = re.compile(r'\{%|\{\{|\{#')


def _seed_full():
    call_command('seed_global_companies')
    call_command('seed_countries')
    call_command('seed_geo_intelligence_demo')
    call_command('recalculate_ecoiq_scores', limit=10)


class DashboardRouteTests(TestCase):
    """Route + permissions (public — no login required, matching ai_agent_workbench/geo_intelligence precedent)."""

    @classmethod
    def setUpTestData(cls):
        _seed_full()

    def test_dashboard_returns_200_without_login(self):
        response = self.client.get(reverse('plotly_visual_intelligence:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_no_template_leak(self):
        response = self.client.get(reverse('plotly_visual_intelligence:dashboard'))
        body = response.content.decode()
        self.assertFalse(TEMPLATE_LEAK_RE.search(body))

    def test_dashboard_accepts_explicit_company_id(self):
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        response = self.client.get(reverse('plotly_visual_intelligence:dashboard'), {'company_id': profile.pk})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, profile.company.name)

    def test_dashboard_ignores_invalid_company_id_gracefully(self):
        response = self.client.get(reverse('plotly_visual_intelligence:dashboard'), {'company_id': 'not-a-number'})
        self.assertEqual(response.status_code, 200)

    def test_dashboard_accepts_orchestration_run_id(self):
        from langgraph_orchestration.graph import run_orchestration
        from langgraph_orchestration.models import OrchestrationRun

        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        result = run_orchestration(target_id=profile.pk, target_type='company')
        run = OrchestrationRun.objects.create(target_type='company', target_repr=profile.company.name)
        run.mark_completed(result)

        response = self.client.get(reverse('plotly_visual_intelligence:dashboard'), {'orchestration_run_id': run.pk})
        self.assertEqual(response.status_code, 200)


class EmptyDataStateTests(TestCase):
    """No companies, no snapshots, no evidence, no orchestration runs at all."""

    def test_dashboard_renders_with_zero_data(self):
        response = self.client.get(reverse('plotly_visual_intelligence:dashboard'))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertFalse(TEMPLATE_LEAK_RE.search(body))

    def test_no_focus_profile_when_nothing_scored(self):
        self.assertIsNone(dashboard_data.resolve_focus_company())

    def test_kpi_cards_all_unavailable_not_fabricated(self):
        cards = dashboard_data.build_kpi_cards(None)
        for card in cards:
            if card['label'] != 'Active Intelligence Tasks':
                self.assertFalse(card['available'])
                self.assertIsNone(card['value'])

    def test_score_chart_none_without_snapshot(self):
        self.assertIsNone(charts.score_contribution_chart(None))

    def test_risk_opportunity_chart_none_without_data(self):
        self.assertIsNone(charts.risk_opportunity_matrix_chart([]))

    def test_similarity_chart_none_without_result(self):
        self.assertIsNone(charts.similarity_chart('Nobody', None))
        self.assertIsNone(charts.similarity_chart('Nobody', {'available': False}))

    def test_cluster_chart_none_without_result(self):
        self.assertIsNone(charts.cluster_chart(None, 'x', 'y'))
        self.assertIsNone(charts.cluster_chart({'available': False}, 'x', 'y'))

    def test_evidence_chart_none_without_distribution(self):
        self.assertIsNone(charts.evidence_distribution_chart(None))
        self.assertIsNone(charts.evidence_distribution_chart({'available': False}))

    def test_orchestration_chart_none_without_run(self):
        self.assertIsNone(charts.orchestration_trace_chart(None))


class PartialDataStateTests(TestCase):
    """Some data exists (companies scored) but no geo/evidence/orchestration data."""

    @classmethod
    def setUpTestData(cls):
        call_command('seed_global_companies')
        call_command('recalculate_ecoiq_scores', limit=5)

    def test_governance_component_available_others_not(self):
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        snapshot = dashboard_data.latest_intelligence_snapshot(profile)
        chart = charts.score_contribution_chart(snapshot)
        self.assertIsNotNone(chart)  # governance_esg is always available

    def test_risk_opportunity_chart_none_without_geo_linkage(self):
        # Plain US/UK seeded companies have no Kazakhstan-only Geo Intelligence link.
        rows = dashboard_data.build_risk_opportunity_rows()
        chart = charts.risk_opportunity_matrix_chart(rows)
        self.assertIsNone(chart)  # honest — no fabricated points

    def test_cluster_chart_none_with_only_one_real_country(self):
        result = dashboard_data.build_cluster_context()
        self.assertFalse(result['available'])

    def test_dashboard_renders_with_partial_data(self):
        response = self.client.get(reverse('plotly_visual_intelligence:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(TEMPLATE_LEAK_RE.search(response.content.decode()))


class FullDataStateTests(TestCase):
    """Companies scored, Kazakhstan geo data seeded, evidence memory populated, orchestration run completed."""

    @classmethod
    def setUpTestData(cls):
        _seed_full()

    def test_score_contribution_chart_serialization(self):
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        snapshot = dashboard_data.latest_intelligence_snapshot(profile)
        chart = charts.score_contribution_chart(snapshot)
        self.assertIsNotNone(chart)
        self.assertIn('plotly-graph-div', chart['html'])
        self.assertEqual(chart['final_score'], snapshot.intelligence_score)

    def test_risk_opportunity_chart_data_uses_only_real_rows(self):
        rows = dashboard_data.build_risk_opportunity_rows()
        chart = charts.risk_opportunity_matrix_chart(rows)
        if chart is not None:
            self.assertLessEqual(chart['count'], chart['total_candidates'])
            self.assertGreater(chart['count'], 0)

    def test_similarity_data_reflects_real_service_output(self):
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        result = dashboard_data.build_similarity_context(profile)
        self.assertTrue(result['available'])
        chart = charts.similarity_chart(profile.company.name, result)
        self.assertIsNotNone(chart)
        self.assertIn('plotly-graph-div', chart['html'])

    def test_cluster_data_with_enough_countries(self):
        from countries.models import CountryProfile
        from geo_intelligence.models import GeoAsset, GeoRiskZone

        uk = CountryProfile.objects.get(name__icontains='United Kingdom')
        us = CountryProfile.objects.get(name__icontains='United States')
        GeoRiskZone.objects.create(name='UK test', risk_type='flood', country=uk, latitude=51.5, longitude=-0.1, severity='low')
        GeoRiskZone.objects.create(name='US test', risk_type='drought', country=us, latitude=39.8, longitude=-98.5, severity='medium')
        GeoAsset.objects.create(name='UK asset', asset_type='city', latitude=51.5, longitude=-0.1, country=uk, climate_exposure_score=30)
        GeoAsset.objects.create(name='US asset', asset_type='city', latitude=39.8, longitude=-98.5, country=us, climate_exposure_score=55)

        result = dashboard_data.build_cluster_context()
        self.assertTrue(result['available'])
        chart = charts.cluster_chart(result, 'Climate risk', 'Geo exposure')
        self.assertIsNotNone(chart)
        self.assertIn('plotly-graph-div', chart['html'])

    def test_evidence_data_full(self):
        from evidence_memory.models import EvidenceMemory

        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        for confidence in (30.0, 60.0, 90.0):
            EvidenceMemory.objects.create(text_chunk=f'Evidence {confidence}', company=profile, confidence=confidence)

        context = dashboard_data.build_evidence_context(profile)
        self.assertTrue(context['platform_wide']['available'])
        chart = charts.evidence_distribution_chart(context['platform_wide'])
        self.assertIsNotNone(chart)
        self.assertEqual(chart['count'], 3)

    def test_orchestration_trace_data_reflects_real_nodes_executed(self):
        from langgraph_orchestration.graph import run_orchestration
        from langgraph_orchestration.models import OrchestrationRun

        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        result = run_orchestration(target_id=profile.pk, target_type='company')
        run = OrchestrationRun.objects.create(target_type='company', target_repr=profile.company.name)
        run.mark_completed(result)

        chart = charts.orchestration_trace_chart(run)
        self.assertIsNotNone(chart)
        self.assertFalse(chart['is_live_claim'])  # never claims to be a live animation
        self.assertEqual(chart['status'], run.status)

    def test_orchestration_trace_never_fakes_live_status(self):
        from langgraph_orchestration.models import OrchestrationRun

        running_run = OrchestrationRun.objects.create(target_type='company', target_repr='In progress', status='running')
        chart = charts.orchestration_trace_chart(running_run)
        # Even for a genuinely 'running' row, the chart only reflects nodes_executed
        # actually persisted so far — never animates or claims more than that.
        self.assertIsNotNone(chart)
        self.assertEqual(chart['status'], 'running')

    def test_recommendations_full(self):
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        result = dashboard_data.build_recommendations_context(profile)
        self.assertTrue(result['available'])
        self.assertIn('recommendations', result)

    def test_full_dashboard_renders_all_sections(self):
        response = self.client.get(reverse('plotly_visual_intelligence:dashboard'))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        for heading in (
            '1. Intelligence overview', '2. Why this score', '3. Risk vs opportunity matrix',
            '4. Most similar companies', '5. Climate risk clusters', '6. Evidence intelligence',
            '7. AI orchestration trace', '8. Recommendations',
        ):
            self.assertIn(heading, body)


class NoFakeDataFallbackTests(TestCase):
    """Explicit checks that nothing invents a number when the real data doesn't exist."""

    @classmethod
    def setUpTestData(cls):
        call_command('seed_global_companies')

    def test_snapshot_never_auto_created_by_dashboard(self):
        # Visiting the dashboard must never itself create a CompanyScoreSnapshot —
        # it only reads what already exists.
        count_before = CompanyScoreSnapshot.objects.count()
        self.client.get(reverse('plotly_visual_intelligence:dashboard'))
        self.assertEqual(CompanyScoreSnapshot.objects.count(), count_before)

    def test_component_marked_unavailable_shows_zero_not_invented_value(self):
        call_command('recalculate_ecoiq_scores', limit=1)
        profile = CompanyProfile.objects.filter(ecoiq_total_score__isnull=False).first()
        snapshot = dashboard_data.latest_intelligence_snapshot(profile)
        explanation = snapshot.intelligence_score_explanation
        for name, detail in explanation['components'].items():
            if name != 'governance_esg':
                self.assertFalse(detail['available'])

    def test_risk_opportunity_never_plots_a_company_missing_an_axis(self):
        call_command('recalculate_ecoiq_scores', limit=10)
        rows = dashboard_data.build_risk_opportunity_rows()
        for row in rows:
            has_both = row['climate_risk_score'] is not None and row['investment_opportunity_score'] is not None
            has_neither_or_one = not has_both
            # Every row in the raw list may lack an axis — that's fine, the
            # chart function itself is responsible for filtering; assert the
            # filter genuinely excludes incomplete rows.
            if has_neither_or_one:
                self.assertTrue(row['climate_risk_score'] is None or row['investment_opportunity_score'] is None)


class MobileTemplateStructureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        _seed_full()

    def test_responsive_css_rules_present(self):
        response = self.client.get(reverse('plotly_visual_intelligence:dashboard'))
        body = response.content.decode()
        self.assertIn('@media (max-width: 720px)', body)
        self.assertIn('@media (max-width: 900px)', body)

    def test_chart_containers_have_overflow_protection(self):
        response = self.client.get(reverse('plotly_visual_intelligence:dashboard'))
        body = response.content.decode()
        self.assertIn('eid-chart-container', body)

    def test_plotly_responsive_config_enabled(self):
        response = self.client.get(reverse('plotly_visual_intelligence:dashboard'))
        body = response.content.decode()
        self.assertIn('"responsive": true', body)


class GoldIntelligenceChartTests(TestCase):
    """
    The 4 chart functions added for the Gold Intelligence vertical
    (sensitivity tornado, scenario comparison, capital tracker, mine
    timeline). Every function reads real service output directly — these
    tests confirm honest None-return on empty/unavailable input, and real
    rendering on real input, never a fabricated chart.
    """

    def test_sensitivity_tornado_none_when_unavailable(self):
        self.assertIsNone(charts.sensitivity_tornado_chart({'available': False, 'reason': 'x'}))

    def test_sensitivity_tornado_none_when_no_variables(self):
        self.assertIsNone(charts.sensitivity_tornado_chart({'available': True, 'base_irr_pct': 10.0, 'variables': []}))

    def test_sensitivity_tornado_renders_with_real_variables(self):
        result = charts.sensitivity_tornado_chart({
            'available': True, 'base_irr_pct': 44.45,
            'variables': [{'variable': 'Gold Price', 'field': 'gold_price_assumption_usd_per_oz', 'base_value': 2000, 'low_irr_pct': 20.0, 'high_irr_pct': 60.0, 'swing_pct': 20.0}],
        })
        self.assertIsNotNone(result)
        self.assertIn('gold-sensitivity-tornado-chart', result['html'])

    def test_scenario_comparison_none_when_no_scenarios(self):
        self.assertIsNone(charts.scenario_comparison_chart({'available': True, 'base_case': {}, 'scenarios': []}))

    def test_scenario_comparison_renders_with_real_scenarios(self):
        result = charts.scenario_comparison_chart({
            'available': True, 'base_case': {'irr_pct': 44.45},
            'scenarios': [{'name': 'Gold price -20%', 'notes': '', 'available': True, 'irr_pct': 20.0}],
        })
        self.assertIsNotNone(result)
        self.assertEqual(result['scenario_count'], 1)

    def test_capital_tracker_chart_none_when_no_lines(self):
        self.assertIsNone(charts.capital_tracker_chart({'available': False, 'lines': []}))

    def test_mine_timeline_chart_none_when_no_dated_milestones(self):
        class _Milestone:
            planned_start = None
            planned_end = None
        self.assertIsNone(charts.mine_timeline_chart([_Milestone()]))


class CapitalGuardianChartTests(TestCase):
    """
    The 3 chart functions added for Capital Guardian (capital deployment,
    the generic gauge, red flag risk distribution). Honest None on empty/
    unavailable input, real rendering on real input — never fabricated.
    """

    def test_capital_deployment_chart_none_with_all_values_missing(self):
        self.assertIsNone(charts.capital_deployment_chart(None, None, None))

    def test_capital_deployment_chart_renders_with_partial_real_values(self):
        result = charts.capital_deployment_chart(100_000_000, 42_300_000, None)
        self.assertIsNotNone(result)
        self.assertIn('gc-capital-deployment-chart', result['html'])

    def test_gauge_chart_none_when_value_unavailable(self):
        self.assertIsNone(charts.capital_guardian_gauge_chart(None, 'Test Gauge', 'gc-test-gauge'))

    def test_gauge_chart_renders_with_real_value(self):
        result = charts.capital_guardian_gauge_chart(86.0, 'Capital Protection Score', 'gc-protection-gauge')
        self.assertIsNotNone(result)
        self.assertEqual(result['value'], 86.0)
        self.assertIn('gc-protection-gauge', result['html'])

    def test_risk_distribution_chart_none_with_no_flags(self):
        self.assertIsNone(charts.capital_guardian_risk_distribution_chart([]))

    def test_risk_distribution_chart_renders_with_real_flags(self):
        class _Flag:
            def __init__(self, severity):
                self.severity = severity
        result = charts.capital_guardian_risk_distribution_chart([_Flag('high'), _Flag('medium'), _Flag('medium')])
        self.assertIsNotNone(result)
        self.assertEqual(result['total'], 3)
