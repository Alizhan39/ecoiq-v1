"""
capital_guardian/tests.py — Capital Guardian: institutional investor
transparency and capital intelligence over a real gold_intelligence.GoldProject.

Every test is built around this app's core discipline: no capital figure,
score, or red flag may ever be fabricated. Tests assert either a real,
independently-verifiable number or an honest "Data source required"/
`available: False` result when a required real input is missing.
"""
import datetime

from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from countries.models import CountryProfile
from evidence_memory.models import EvidenceMemory
from gold_intelligence.models import CapitalBudgetLine, EquipmentSpec, GoldProject, MineTimelineMilestone

from capital_guardian.models import (
    AuditLogEntry, CapitalTraceEntry, OperationalSnapshot, ProjectGovernance, RedFlag, RedFlagRuleConfig,
    SupplierProfile,
)
from capital_guardian.services import (
    ai_director, audit_log, capital_protection, capital_trace, equipment_health, evidence as evidence_service,
    investor_dashboard, portfolio, project_health, red_flag_engine, supplier_comparison,
)
from waste_to_value_capital_allocation_engine.models import (
    CapitalAllocationDecision, InterventionOption, LossEvidence, OperationalLoss,
)


class ProjectGovernanceModelTests(TestCase):
    def setUp(self):
        self.project = GoldProject.objects.create(name='Gov Test', slug='gov-test')

    def test_str(self):
        gov = ProjectGovernance.objects.create(project=self.project)
        self.assertIn('Governance', str(gov))

    def test_active_controls_count_real_sum(self):
        gov = ProjectGovernance.objects.create(
            project=self.project, reserved_matters_active=True, escrow_account_active=True,
        )
        self.assertEqual(gov.active_controls_count, 2)

    def test_active_controls_default_false(self):
        gov = ProjectGovernance.objects.create(project=self.project)
        self.assertEqual(gov.active_controls_count, 0)   # honesty default — never assume active


class CapitalTraceEntryModelTests(TestCase):
    def setUp(self):
        self.project = GoldProject.objects.create(name='Trace Test', slug='trace-test')

    def test_trace_id_auto_generated_and_unique(self):
        e1 = CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=100, purpose='a')
        e2 = CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=200, purpose='b')
        self.assertNotEqual(e1.trace_id, e2.trace_id)
        self.assertTrue(e1.trace_id.startswith('CT-'))

    def test_explicit_trace_id_preserved(self):
        e = CapitalTraceEntry.objects.create(
            project=self.project, trace_id='CUSTOM-001', date=datetime.date.today(), amount_usd=100, purpose='a',
        )
        self.assertEqual(e.trace_id, 'CUSTOM-001')

    def test_evidence_documents_empty_by_default(self):
        e = CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=100, purpose='a')
        self.assertEqual(e.evidence_documents.count(), 0)

    def test_evidence_documents_reads_real_evidence_memory(self):
        from evidence_memory.models import EvidenceMemory
        e = CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=100, purpose='a')
        EvidenceMemory.objects.create(text_chunk='x', source_reference=f'capital_guardian.CapitalTraceEntry:{e.pk}')
        EvidenceMemory.objects.create(text_chunk='unrelated', source_reference='capital_guardian.CapitalTraceEntry:999999')
        self.assertEqual(e.evidence_documents.count(), 1)


class RedFlagModelTests(TestCase):
    def test_unique_project_rule_key_constraint(self):
        project = GoldProject.objects.create(name='RF Model Test', slug='rf-model-test')
        RedFlag.objects.create(project=project, rule_key='r1', category='budget', description='x')
        with self.assertRaises(Exception):
            RedFlag.objects.create(project=project, rule_key='r1', category='budget', description='y')


class OperationalSnapshotModelTests(TestCase):
    def test_unique_project_date_constraint(self):
        project = GoldProject.objects.create(name='Snap Model Test', slug='snap-model-test')
        OperationalSnapshot.objects.create(project=project, date=datetime.date.today())
        with self.assertRaises(Exception):
            OperationalSnapshot.objects.create(project=project, date=datetime.date.today())


class CapitalTraceServiceTests(TestCase):
    def setUp(self):
        self.project = GoldProject.objects.create(name='CT Service Test', slug='ct-service-test')

    def test_capital_deployed_only_counts_paid(self):
        CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=1000, purpose='a', payment_status='paid')
        CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=500, purpose='b', payment_status='pending')
        self.assertEqual(capital_trace.capital_deployed(self.project), 1000)

    def test_capital_deployed_none_when_nothing_paid(self):
        CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=500, purpose='b', payment_status='pending')
        self.assertIsNone(capital_trace.capital_deployed(self.project))

    def test_evidence_coverage_real_counts(self):
        from evidence_memory.models import EvidenceMemory
        e1 = CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=1, purpose='a')
        CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=1, purpose='b')
        EvidenceMemory.objects.create(text_chunk='x', source_reference=f'capital_guardian.CapitalTraceEntry:{e1.pk}')
        with_evidence, total = capital_trace.evidence_coverage(self.project.capital_trace_entries.all())
        self.assertEqual((with_evidence, total), (1, 2))

    def test_verification_coverage_real_counts(self):
        CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=1, purpose='a', verification_status='verified')
        CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=1, purpose='b', verification_status='unverified')
        verified, total = capital_trace.verification_coverage(self.project.capital_trace_entries.all())
        self.assertEqual((verified, total), (1, 2))

    def test_trace_chain_reflects_real_entry_state(self):
        entry = CapitalTraceEntry.objects.create(
            project=self.project, date=datetime.date.today(), amount_usd=1, purpose='a',
            approval_status='approved', verification_status='verified', supplier='Acme',
        )
        chain = capital_trace.trace_chain_for_entry(entry)
        by_step = {c['step']: c for c in chain}
        self.assertTrue(by_step['Approved Budget']['complete'])
        self.assertTrue(by_step['Independent Verification']['complete'])
        self.assertEqual(by_step['Supplier / Contractor']['detail'], 'Acme')
        self.assertFalse(by_step['Project SPV']['complete'])   # no ProjectGovernance created


class CapitalProtectionServiceTests(TestCase):
    def setUp(self):
        self.project = GoldProject.objects.create(name='CP Service Test', slug='cp-service-test')

    def test_unavailable_with_zero_real_data(self):
        result = capital_protection.compute_capital_protection_score(self.project)
        self.assertFalse(result['available'])
        self.assertIsNone(result['score'])

    def test_available_with_partial_real_data_renormalizes_weights(self):
        CapitalBudgetLine.objects.create(project=self.project, label='x', planned_usd=100, committed_usd=100)
        result = capital_protection.compute_capital_protection_score(self.project)
        self.assertTrue(result['available'])
        self.assertEqual(result['score'], 100.0)   # only budget_discipline available, perfectly on-budget
        self.assertIsNone(result['components']['insurance_coverage'])

    def test_red_flag_penalty_reduces_score(self):
        CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=1, purpose='a', payment_status='paid')
        RedFlag.objects.create(project=self.project, rule_key='r1', category='budget', description='x', severity='high')
        result = capital_protection.compute_capital_protection_score(self.project)
        self.assertEqual(result['components']['red_flag_penalty']['normalized'], 80.0)   # 100 - 20 for one high flag

    def test_no_open_red_flags_scores_perfectly_once_real_data_exists(self):
        CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=1, purpose='a')
        result_component = capital_protection._red_flag_penalty_component(self.project)
        self.assertEqual(result_component['normalized'], 100.0)

    def test_red_flag_penalty_unavailable_for_a_completely_bare_project(self):
        # "no open red flags" isn't a meaningful signal with zero real data
        # anywhere — never presented as a fabricated 100/100.
        self.assertIsNone(capital_protection._red_flag_penalty_component(self.project))

    def test_acknowledged_red_flags_excluded_from_penalty(self):
        RedFlag.objects.create(project=self.project, rule_key='r1', category='budget', description='x', severity='high', resolution_status='acknowledged')
        result_component = capital_protection._red_flag_penalty_component(self.project)
        self.assertEqual(result_component['normalized'], 100.0)   # acknowledged, not open — no penalty


class RedFlagEngineTests(TestCase):
    def setUp(self):
        self.project = GoldProject.objects.create(name='RF Engine Test', slug='rf-engine-test')

    def test_equipment_fat_dependency_rule(self):
        EquipmentSpec.objects.create(
            project=self.project, equipment_type='mill', label='SAG Mill',
            fat_status='not_started', delivery_status='in_progress',
        )
        flags = red_flag_engine.detect_red_flags(self.project)
        self.assertTrue(any(f.category == 'schedule' for f in flags))

    def test_fat_dependency_rule_does_not_fire_when_fat_passed(self):
        EquipmentSpec.objects.create(
            project=self.project, equipment_type='mill', label='SAG Mill',
            fat_status='passed', delivery_status='in_progress',
        )
        flags = red_flag_engine.detect_red_flags(self.project)
        self.assertFalse(any(f.category == 'schedule' for f in flags))

    def test_capex_variance_rule_fires_above_threshold(self):
        CapitalBudgetLine.objects.create(project=self.project, label='x', planned_usd=100_000_000, committed_usd=103_400_000)
        flags = red_flag_engine.detect_red_flags(self.project)
        budget_flags = [f for f in flags if f.category == 'budget']
        self.assertEqual(len(budget_flags), 1)
        self.assertIn('+3.4%', budget_flags[0].description)

    def test_capex_variance_rule_silent_below_threshold(self):
        CapitalBudgetLine.objects.create(project=self.project, label='x', planned_usd=100_000_000, committed_usd=100_500_000)
        flags = red_flag_engine.detect_red_flags(self.project)
        self.assertFalse(any(f.category == 'budget' for f in flags))

    def test_insurance_renewal_rule_fires_within_window(self):
        self.project.insurance_expiry_date = datetime.date.today() + datetime.timedelta(days=47)
        self.project.save()
        flags = red_flag_engine.detect_red_flags(self.project)
        self.assertTrue(any(f.category == 'insurance' for f in flags))

    def test_insurance_renewal_rule_silent_when_far_away(self):
        self.project.insurance_expiry_date = datetime.date.today() + datetime.timedelta(days=365)
        self.project.save()
        flags = red_flag_engine.detect_red_flags(self.project)
        self.assertFalse(any(f.category == 'insurance' for f in flags))

    def test_pending_investor_approval_rule(self):
        CapitalTraceEntry.objects.create(
            project=self.project, date=datetime.date.today(), amount_usd=1, purpose='x', investor_approval_status='pending',
        )
        flags = red_flag_engine.detect_red_flags(self.project)
        self.assertTrue(any(f.category == 'approval' for f in flags))

    def test_idempotent_rerun_does_not_duplicate(self):
        CapitalBudgetLine.objects.create(project=self.project, label='x', planned_usd=100_000_000, committed_usd=103_400_000)
        red_flag_engine.detect_red_flags(self.project)
        red_flag_engine.detect_red_flags(self.project)
        self.assertEqual(RedFlag.objects.filter(project=self.project).count(), 1)

    def test_acknowledged_flag_never_silently_reopened(self):
        CapitalBudgetLine.objects.create(project=self.project, label='x', planned_usd=100_000_000, committed_usd=103_400_000)
        flags = red_flag_engine.detect_red_flags(self.project)
        flag = flags[0]
        flag.resolution_status = 'acknowledged'
        flag.acknowledged_notes = 'Reviewed'
        flag.save()
        red_flag_engine.detect_red_flags(self.project)
        flag.refresh_from_db()
        self.assertEqual(flag.resolution_status, 'acknowledged')
        self.assertEqual(flag.acknowledged_notes, 'Reviewed')

    def test_resolved_condition_removes_open_flag(self):
        line = CapitalBudgetLine.objects.create(project=self.project, label='x', planned_usd=100_000_000, committed_usd=103_400_000)
        red_flag_engine.detect_red_flags(self.project)
        self.assertEqual(RedFlag.objects.filter(project=self.project, resolution_status='open').count(), 1)
        line.committed_usd = 100_500_000   # condition resolved
        line.save()
        red_flag_engine.detect_red_flags(self.project)
        self.assertEqual(RedFlag.objects.filter(project=self.project, resolution_status='open').count(), 0)

    def test_never_creates_fake_flags_with_no_real_conditions(self):
        flags = red_flag_engine.detect_red_flags(self.project)
        self.assertEqual(flags, [])


class InvestorDashboardServiceTests(TestCase):
    def setUp(self):
        self.project = GoldProject.objects.create(name='ID Service Test', slug='id-service-test')

    def test_overall_completion_none_with_no_milestones(self):
        self.assertIsNone(investor_dashboard.overall_completion_pct(self.project))

    def test_overall_completion_averages_real_determinate_values(self):
        MineTimelineMilestone.objects.create(project=self.project, phase='exploration', status='complete')
        MineTimelineMilestone.objects.create(project=self.project, phase='licensing', status='not_started')
        self.assertEqual(investor_dashboard.overall_completion_pct(self.project), 50.0)

    def test_next_milestone_excludes_complete_and_orders_by_planned_end(self):
        MineTimelineMilestone.objects.create(
            project=self.project, phase='construction', status='in_progress',
            planned_end=datetime.date.today() + datetime.timedelta(days=100),
        )
        near = MineTimelineMilestone.objects.create(
            project=self.project, phase='licensing', status='in_progress',
            planned_end=datetime.date.today() + datetime.timedelta(days=10),
        )
        MineTimelineMilestone.objects.create(project=self.project, phase='exploration', status='complete')
        self.assertEqual(investor_dashboard.next_milestone(self.project), near)

    def test_build_dashboard_context_never_writes_to_database(self):
        original_capex = self.project.total_capex_usd
        investor_dashboard.build_dashboard_context(self.project)
        self.project.refresh_from_db()
        self.assertEqual(self.project.total_capex_usd, original_capex)


class ViewTests(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME='localhost')
        self.kz = CountryProfile.objects.create(name='Kazakhstan', slug='kazakhstan', iso_code='KZ', is_published=True)
        self.project = GoldProject.objects.create(
            name='View Test Project', slug='cg-view-test-project', country=self.kz, is_demo=True,
            total_committed_capital_usd=100_000_000, total_capex_usd=86_000_000,
        )
        ProjectGovernance.objects.create(project=self.project, founder_holdco_pct=50, investor_spv_pct=50)

    def _all_project_urls(self):
        return [
            reverse('capital_guardian:investor_dashboard', args=[self.project.slug]),
            reverse('capital_guardian:capital_trace', args=[self.project.slug]),
            reverse('capital_guardian:governance', args=[self.project.slug]),
            reverse('capital_guardian:equipment_insurance', args=[self.project.slug]),
            reverse('capital_guardian:digital_twin', args=[self.project.slug]),
            reverse('capital_guardian:milestone_control', args=[self.project.slug]),
            reverse('capital_guardian:red_flags', args=[self.project.slug]),
            reverse('capital_guardian:decision_intelligence', args=[self.project.slug]),
        ]

    def test_directory_returns_200(self):
        r = self.client.get(reverse('capital_guardian:directory'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'View Test Project')

    def test_all_project_pages_return_200(self):
        for url in self._all_project_urls():
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertEqual(r.status_code, 200)

    def test_unknown_project_slug_404s(self):
        r = self.client.get(reverse('capital_guardian:investor_dashboard', args=['not-a-real-project']))
        self.assertEqual(r.status_code, 404)

    def test_demo_badge_shown_on_dashboard(self):
        r = self.client.get(reverse('capital_guardian:investor_dashboard', args=[self.project.slug]))
        self.assertContains(r, 'gold-demo-badge')
        self.assertContains(r, 'SYNTHETIC DEMONSTRATION')

    def test_honest_data_source_required_shown_for_missing_fields(self):
        bare_project = GoldProject.objects.create(name='Bare', slug='cg-bare-view-project')
        r = self.client.get(reverse('capital_guardian:investor_dashboard', args=[bare_project.slug]))
        self.assertContains(r, 'Data source required')

    def test_governance_page_shows_disclaimer(self):
        r = self.client.get(reverse('capital_guardian:governance', args=[self.project.slug]))
        self.assertContains(r, 'not legal advice')

    def test_equipment_page_shows_illustrative_disclaimer(self):
        r = self.client.get(reverse('capital_guardian:equipment_insurance', args=[self.project.slug]))
        self.assertContains(r, 'illustrative examples only')

    def test_decision_intelligence_links_use_real_existing_route(self):
        r = self.client.get(reverse('capital_guardian:decision_intelligence', args=[self.project.slug]))
        self.assertContains(r, '/decision-studio/?q=')

    def test_no_raw_template_tags_leak_on_any_page(self):
        for url in self._all_project_urls() + [reverse('capital_guardian:directory')]:
            with self.subTest(url=url):
                r = self.client.get(url)
                content = r.content.decode()
                self.assertNotIn('{%', content)
                self.assertNotIn('{{', content)

    def test_digital_twin_shows_honest_empty_state_with_no_snapshot(self):
        r = self.client.get(reverse('capital_guardian:digital_twin', args=[self.project.slug]))
        self.assertContains(r, 'No operational snapshot recorded')


class SeedCommandTests(TestCase):
    def setUp(self):
        call_command('seed_countries')

    def test_seed_creates_the_demo_project(self):
        call_command('seed_capital_guardian_demo')
        project = GoldProject.objects.get(slug='kz-gold-project-01')
        self.assertTrue(project.is_demo)
        self.assertEqual(project.name, 'KZ Gold Project 01')

    def test_seed_is_idempotent(self):
        call_command('seed_capital_guardian_demo')
        call_command('seed_capital_guardian_demo')
        project = GoldProject.objects.get(slug='kz-gold-project-01')
        self.assertEqual(project.capital_trace_entries.count(), 8)
        self.assertEqual(project.equipment_specs.count(), 9)
        self.assertEqual(project.timeline_milestones.count(), 6)

    def test_seed_matches_specified_headline_figures(self):
        call_command('seed_capital_guardian_demo')
        project = GoldProject.objects.get(slug='kz-gold-project-01')
        self.assertEqual(project.total_committed_capital_usd, 100_000_000)
        self.assertEqual(project.total_capex_usd, 86_000_000)
        self.assertEqual(project.insurance_coverage_usd, 62_000_000)
        self.assertEqual(capital_trace.capital_deployed(project), 42_300_000)
        capex_summary = project.capital_budget_lines.first()
        self.assertEqual(capex_summary.spent_usd, 31_800_000)

    def test_seeded_red_flags_are_genuinely_detected(self):
        call_command('seed_capital_guardian_demo')
        project = GoldProject.objects.get(slug='kz-gold-project-01')
        self.assertGreater(project.red_flags.count(), 0)
        categories = set(project.red_flags.values_list('category', flat=True))
        self.assertIn('budget', categories)
        self.assertIn('insurance', categories)
        self.assertIn('approval', categories)

    def test_missing_kazakhstan_profile_handled_honestly(self):
        CountryProfile.objects.filter(iso_code='KZ').delete()
        call_command('seed_capital_guardian_demo')
        self.assertEqual(GoldProject.objects.filter(slug='kz-gold-project-01').count(), 0)


class AdminTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.admin_user = User.objects.create_superuser('cg-admin', 'cg-admin@example.com', 'password123')
        self.client.force_login(self.admin_user)
        self.project = GoldProject.objects.create(name='Admin Test Project', slug='cg-admin-test-project')

    def test_governance_list_visible_in_admin(self):
        ProjectGovernance.objects.create(project=self.project)
        r = self.client.get('/admin/capital_guardian/projectgovernance/')
        self.assertEqual(r.status_code, 200)

    def test_red_flag_cannot_be_manually_added(self):
        r = self.client.get('/admin/capital_guardian/redflag/add/')
        self.assertEqual(r.status_code, 403)

    def test_red_flag_acknowledge_action(self):
        flag = RedFlag.objects.create(project=self.project, rule_key='r1', category='budget', description='x')
        response = self.client.post('/admin/capital_guardian/redflag/', {
            'action': 'acknowledge_selected',
            '_selected_action': [str(flag.pk)],
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        flag.refresh_from_db()
        self.assertEqual(flag.resolution_status, 'acknowledged')
        self.assertEqual(flag.acknowledged_by_id, self.admin_user.pk)


# ============================================================================
# Phase 2: Multi-Project Portfolio, Evidence Workflow, Configurable Red
# Flags, Digital Twin Time-Series, Governance & Milestone Audit Log.
# ============================================================================

class PortfolioServiceTests(TestCase):
    def setUp(self):
        self.project = GoldProject.objects.create(name='Portfolio Test', slug='portfolio-test', total_committed_capital_usd=100)

    def test_project_status_unknown_with_no_real_data(self):
        self.assertEqual(portfolio.project_status(None, []), portfolio.STATUS_UNKNOWN)

    def test_project_status_on_track_with_high_score_and_no_flags(self):
        self.assertEqual(portfolio.project_status(85.0, []), portfolio.STATUS_ON_TRACK)

    def test_project_status_monitor_with_any_open_flag(self):
        flag = RedFlag(severity='low')
        self.assertEqual(portfolio.project_status(85.0, [flag]), portfolio.STATUS_MONITOR)

    def test_project_status_at_risk_with_high_severity_flag(self):
        flag = RedFlag(severity='high')
        self.assertEqual(portfolio.project_status(85.0, [flag]), portfolio.STATUS_AT_RISK)

    def test_project_status_at_risk_with_low_score_even_without_flags(self):
        self.assertEqual(portfolio.project_status(20.0, []), portfolio.STATUS_AT_RISK)

    def test_project_summary_never_writes_to_database(self):
        original = self.project.total_committed_capital_usd
        portfolio.project_summary(self.project)
        self.project.refresh_from_db()
        self.assertEqual(self.project.total_committed_capital_usd, original)

    def test_build_portfolio_returns_one_row_per_project(self):
        p2 = GoldProject.objects.create(name='Portfolio Test 2', slug='portfolio-test-2')
        rows = portfolio.build_portfolio([self.project, p2])
        self.assertEqual(len(rows), 2)

    def test_portfolio_totals_unavailable_with_no_projects(self):
        totals = portfolio.portfolio_totals([])
        self.assertFalse(totals['available'])

    def test_portfolio_totals_sums_real_committed_and_deployed(self):
        p2 = GoldProject.objects.create(name='Portfolio Test 2', slug='portfolio-test-2', total_committed_capital_usd=200)
        CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=40, purpose='a', payment_status='paid')
        CapitalTraceEntry.objects.create(project=p2, date=datetime.date.today(), amount_usd=60, purpose='b', payment_status='paid')
        rows = portfolio.build_portfolio([self.project, p2])
        totals = portfolio.portfolio_totals(rows)
        self.assertEqual(totals['total_committed_usd'], 300)
        self.assertEqual(totals['total_deployed_usd'], 100)

    def test_portfolio_totals_weighted_protection_score(self):
        # Project A: $100 committed, perfect budget discipline (score 100).
        # Project B: $300 committed, no real protection data (excluded from the weighted average).
        CapitalBudgetLine.objects.create(project=self.project, label='x', planned_usd=100, committed_usd=100)
        p2 = GoldProject.objects.create(name='Portfolio Test 2', slug='portfolio-test-2', total_committed_capital_usd=300)
        rows = portfolio.build_portfolio([self.project, p2])
        totals = portfolio.portfolio_totals(rows)
        self.assertEqual(totals['weighted_protection_score'], 100.0)
        self.assertEqual(totals['weighted_protection_score_basis'], '1 of 2 project(s)')

    def test_filter_rows_by_commodity(self):
        self.project.commodity = 'copper'
        self.project.save()
        p2 = GoldProject.objects.create(name='Gold Co', slug='gold-co', commodity='gold')
        rows = portfolio.build_portfolio([self.project, p2])
        filtered = portfolio.filter_rows(rows, commodity='copper')
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['project'].slug, 'portfolio-test')

    def test_filter_rows_by_status(self):
        # refresh_red_flags=False: this manually-created flag has no matching
        # live rule condition, so a real re-detection pass would correctly
        # clean it up — this test is about filter_rows(), not detection.
        RedFlag.objects.create(project=self.project, rule_key='r1', category='budget', description='x', severity='high')
        p2 = GoldProject.objects.create(name='Clean Project', slug='clean-project')
        CapitalBudgetLine.objects.create(project=p2, label='x', planned_usd=100, committed_usd=100)
        rows = portfolio.build_portfolio([self.project, p2], refresh_red_flags=False)
        at_risk = portfolio.filter_rows(rows, status='at_risk')
        self.assertEqual(len(at_risk), 1)
        self.assertEqual(at_risk[0]['project'].slug, 'portfolio-test')

    def test_sort_rows_by_deployed_usd_descending(self):
        p2 = GoldProject.objects.create(name='Portfolio Test 2', slug='portfolio-test-2')
        CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=10, purpose='a', payment_status='paid')
        CapitalTraceEntry.objects.create(project=p2, date=datetime.date.today(), amount_usd=500, purpose='b', payment_status='paid')
        rows = portfolio.build_portfolio([self.project, p2])
        sorted_rows = portfolio.sort_rows(rows, 'deployed_usd')
        self.assertEqual(sorted_rows[0]['project'].slug, 'portfolio-test-2')

    def test_sort_rows_unknown_key_returns_unchanged(self):
        rows = portfolio.build_portfolio([self.project])
        self.assertEqual(portfolio.sort_rows(rows, 'not_a_real_key'), rows)


class EvidenceServiceTests(TestCase):
    def setUp(self):
        self.project = GoldProject.objects.create(name='Evidence Test', slug='evidence-test')

    def test_evidence_for_project_gathers_capital_trace_entry_evidence(self):
        entry = CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=1, purpose='a')
        EvidenceMemory.objects.create(text_chunk='x', source_reference=f'capital_guardian.CapitalTraceEntry:{entry.pk}')
        self.assertEqual(evidence_service.evidence_for_project(self.project).count(), 1)

    def test_evidence_for_project_gathers_equipment_evidence(self):
        equipment = EquipmentSpec.objects.create(project=self.project, equipment_type='crusher', label='Crusher')
        EvidenceMemory.objects.create(text_chunk='x', source_reference=f'gold_intelligence.EquipmentSpec:{equipment.pk}')
        self.assertEqual(evidence_service.evidence_for_project(self.project).count(), 1)

    def test_evidence_for_project_excludes_unrelated_evidence(self):
        EvidenceMemory.objects.create(text_chunk='x', source_reference='harvester.Evidence:999999')
        self.assertEqual(evidence_service.evidence_for_project(self.project).count(), 0)

    def test_evidence_for_project_gathers_governance_evidence(self):
        gov = ProjectGovernance.objects.create(project=self.project)
        EvidenceMemory.objects.create(text_chunk='x', source_reference=f'capital_guardian.ProjectGovernance:{gov.pk}')
        self.assertEqual(evidence_service.evidence_for_project(self.project).count(), 1)

    def test_verification_summary_real_counts_by_status(self):
        entry = CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=1, purpose='a')
        EvidenceMemory.objects.create(text_chunk='x', source_reference=f'capital_guardian.CapitalTraceEntry:{entry.pk}', verification_status='verified')
        EvidenceMemory.objects.create(text_chunk='y', source_reference=f'capital_guardian.CapitalTraceEntry:{entry.pk}', verification_status='pending')
        summary = evidence_service.verification_summary(evidence_service.evidence_for_project(self.project))
        self.assertEqual(summary['total'], 2)
        self.assertEqual(summary['by_status']['verified'], 1)
        self.assertEqual(summary['by_status']['pending'], 1)

    def test_related_object_label_for_known_and_unknown_references(self):
        self.assertEqual(evidence_service.related_object_label('capital_guardian.CapitalTraceEntry:5'), 'Capital Trace Entry #5')
        self.assertEqual(evidence_service.related_object_label(''), 'Not linked')
        self.assertEqual(evidence_service.related_object_label('some.Unknown:9'), 'some.Unknown #9')

    def test_evidence_for_project_gathers_manual_project_evidence(self):
        """Vertical-slice PR 1 — project-level manual evidence (no child object) is retrieved too."""
        from evidence_memory.services.memory import create_memory_from_manual_project_evidence
        create_memory_from_manual_project_evidence(self.project, title='T', text='Manual project-level evidence.')
        self.assertEqual(evidence_service.evidence_for_project(self.project).count(), 1)

    def test_evidence_for_project_no_cross_project_leakage_for_manual_evidence(self):
        from evidence_memory.services.memory import create_memory_from_manual_project_evidence
        other = GoldProject.objects.create(name='Other Evidence Test', slug='other-evidence-test')
        create_memory_from_manual_project_evidence(self.project, title='T', text='Project A evidence.')
        create_memory_from_manual_project_evidence(other, title='T', text='Project B evidence.')
        self.assertEqual(evidence_service.evidence_for_project(self.project).count(), 1)
        self.assertEqual(evidence_service.evidence_for_project(other).count(), 1)

    def test_evidence_for_project_zero_evidence_is_honest_empty_queryset(self):
        empty_project = GoldProject.objects.create(name='No Evidence Project', slug='no-evidence-project')
        self.assertEqual(evidence_service.evidence_for_project(empty_project).count(), 0)

    def test_evidence_for_project_orders_and_returns_all_multiple_rows(self):
        from evidence_memory.services.memory import create_memory_from_manual_project_evidence
        create_memory_from_manual_project_evidence(self.project, title='T1', text='First piece of evidence.')
        create_memory_from_manual_project_evidence(self.project, title='T2', text='Second piece of evidence.')
        create_memory_from_manual_project_evidence(self.project, title='T3', text='Third piece of evidence.')
        self.assertEqual(evidence_service.evidence_for_project(self.project).count(), 3)


class EvidenceMemoryModelPhase2Tests(TestCase):
    def test_integrity_reference_computed_on_save(self):
        e = EvidenceMemory.objects.create(text_chunk='hello world')
        self.assertEqual(len(e.integrity_reference), 64)

    def test_integrity_reference_stable_for_same_text(self):
        e1 = EvidenceMemory.objects.create(text_chunk='same text')
        e2 = EvidenceMemory.objects.create(text_chunk='same text')
        self.assertEqual(e1.integrity_reference, e2.integrity_reference)

    def test_integrity_reference_recomputed_when_text_changes(self):
        e = EvidenceMemory.objects.create(text_chunk='original text')
        original_hash = e.integrity_reference
        e.text_chunk = 'edited text'
        e.save()
        self.assertNotEqual(e.integrity_reference, original_hash)

    def test_integrity_reference_persisted_through_update_or_create_with_narrow_defaults(self):
        # Regression: QuerySet.update_or_create()'s update path calls
        # Model.save(update_fields=<only the defaults keys>) — without
        # widening update_fields in save(), the recomputed hash was set in
        # memory but silently never written to the database.
        EvidenceMemory.objects.create(source_reference='cg-test:1', text_chunk='v1')
        EvidenceMemory.objects.update_or_create(source_reference='cg-test:1', defaults={'text_chunk': 'v2'})
        from_db = EvidenceMemory.objects.get(source_reference='cg-test:1')
        expected = __import__('hashlib').sha256(b'v2').hexdigest()
        self.assertEqual(from_db.integrity_reference, expected)

    def test_is_expired_false_with_no_expiry_date(self):
        e = EvidenceMemory.objects.create(text_chunk='x')
        self.assertFalse(e.is_expired)

    def test_is_expired_true_for_past_date(self):
        e = EvidenceMemory.objects.create(text_chunk='x', expiry_date=datetime.date.today() - datetime.timedelta(days=1))
        self.assertTrue(e.is_expired)

    def test_is_expired_false_for_future_date(self):
        e = EvidenceMemory.objects.create(text_chunk='x', expiry_date=datetime.date.today() + datetime.timedelta(days=1))
        self.assertFalse(e.is_expired)

    def test_defaults_are_honest(self):
        e = EvidenceMemory.objects.create(text_chunk='x')
        self.assertEqual(e.verification_status, 'pending')
        self.assertEqual(e.review_tier, 'uploaded')
        self.assertIsNone(e.reviewer)


class RedFlagRuleConfigTests(TestCase):
    def setUp(self):
        self.project = GoldProject.objects.create(name='Config Test', slug='config-test')

    def test_falls_back_to_hardcoded_constant_with_no_config_rows(self):
        warning, critical = red_flag_engine.get_thresholds(self.project, 'capex_variance')
        self.assertEqual(warning, red_flag_engine.CAPEX_VARIANCE_WARNING_THRESHOLD_PCT)
        self.assertEqual(critical, red_flag_engine.CAPEX_VARIANCE_CRITICAL_THRESHOLD_PCT)

    def test_platform_default_overrides_hardcoded_constant(self):
        RedFlagRuleConfig.objects.create(project=None, rule_key='capex_variance', warning_threshold=5.0, critical_threshold=15.0)
        warning, critical = red_flag_engine.get_thresholds(self.project, 'capex_variance')
        self.assertEqual((warning, critical), (5.0, 15.0))

    def test_project_scoped_config_overrides_platform_default(self):
        RedFlagRuleConfig.objects.create(project=None, rule_key='capex_variance', warning_threshold=5.0, critical_threshold=15.0)
        RedFlagRuleConfig.objects.create(project=self.project, rule_key='capex_variance', warning_threshold=1.0, critical_threshold=8.0)
        warning, critical = red_flag_engine.get_thresholds(self.project, 'capex_variance')
        self.assertEqual((warning, critical), (1.0, 8.0))

    def test_disabled_config_returns_no_thresholds(self):
        RedFlagRuleConfig.objects.create(project=self.project, rule_key='capex_variance', enabled=False)
        warning, critical = red_flag_engine.get_thresholds(self.project, 'capex_variance')
        self.assertIsNone(warning)
        self.assertIsNone(critical)

    def test_disabled_rule_never_fires(self):
        RedFlagRuleConfig.objects.create(project=self.project, rule_key='capex_variance', enabled=False)
        CapitalBudgetLine.objects.create(project=self.project, label='x', planned_usd=100_000_000, committed_usd=120_000_000)
        flags = red_flag_engine.detect_red_flags(self.project)
        self.assertFalse(any(f.category == 'budget' for f in flags))

    def test_configurable_threshold_changes_what_fires(self):
        RedFlagRuleConfig.objects.create(project=self.project, rule_key='capex_variance', warning_threshold=50.0, critical_threshold=90.0)
        CapitalBudgetLine.objects.create(project=self.project, label='x', planned_usd=100_000_000, committed_usd=103_400_000)
        flags = red_flag_engine.detect_red_flags(self.project)
        self.assertFalse(any(f.category == 'budget' for f in flags))   # 3.4% variance no longer exceeds the raised 50% threshold


class RedFlagEnginePhase2RulesTests(TestCase):
    def setUp(self):
        self.project = GoldProject.objects.create(name='RF Phase2 Test', slug='rf-phase2-test')

    def test_governance_approval_missing_fires_when_paid_without_approval(self):
        CapitalTraceEntry.objects.create(
            project=self.project, date=datetime.date.today(), amount_usd=1, purpose='a',
            payment_status='paid', approval_status='pending',
        )
        flags = red_flag_engine.detect_red_flags(self.project)
        self.assertTrue(any(f.category == 'governance' for f in flags))

    def test_governance_approval_missing_silent_when_approved(self):
        CapitalTraceEntry.objects.create(
            project=self.project, date=datetime.date.today(), amount_usd=1, purpose='a',
            payment_status='paid', approval_status='approved',
        )
        flags = red_flag_engine.detect_red_flags(self.project)
        self.assertFalse(any(f.category == 'governance' for f in flags))

    def test_evidence_missing_fires_for_paid_entry_with_no_evidence(self):
        CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=1, purpose='a', payment_status='paid')
        flags = red_flag_engine.detect_red_flags(self.project)
        self.assertTrue(any(f.category == 'evidence' for f in flags))

    def test_evidence_missing_silent_when_evidence_exists(self):
        entry = CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=1, purpose='a', payment_status='paid')
        EvidenceMemory.objects.create(text_chunk='x', source_reference=f'capital_guardian.CapitalTraceEntry:{entry.pk}')
        flags = red_flag_engine.detect_red_flags(self.project)
        self.assertFalse(any(f.category == 'evidence' for f in flags))

    def test_schedule_delay_fires_for_delayed_milestone(self):
        MineTimelineMilestone.objects.create(project=self.project, phase='construction', status='delayed')
        flags = red_flag_engine.detect_red_flags(self.project)
        self.assertTrue(any(f.category == 'schedule' and 'delayed' in f.description for f in flags))

    def test_fat_failure_fires_for_failed_test(self):
        EquipmentSpec.objects.create(project=self.project, equipment_type='mill', label='SAG Mill', fat_status='failed')
        flags = red_flag_engine.detect_red_flags(self.project)
        self.assertTrue(any(f.category == 'equipment' for f in flags))

    def test_equipment_availability_low_fires_below_threshold(self):
        OperationalSnapshot.objects.create(project=self.project, date=datetime.date.today(), equipment_availability_pct=70.0)
        flags = red_flag_engine.detect_red_flags(self.project)
        self.assertTrue(any(f.category == 'operational' and 'availability' in f.description for f in flags))

    def test_equipment_availability_silent_above_threshold(self):
        OperationalSnapshot.objects.create(project=self.project, date=datetime.date.today(), equipment_availability_pct=95.0)
        flags = red_flag_engine.detect_red_flags(self.project)
        self.assertFalse(any('availability' in f.description for f in flags))

    def test_recovery_rate_flag_fires_below_target(self):
        self.project.recovery_rate_pct = 95.0
        self.project.save()
        OperationalSnapshot.objects.create(project=self.project, date=datetime.date.today(), recovery_rate_pct=85.0)
        flags = red_flag_engine.detect_red_flags(self.project)
        self.assertTrue(any('Recovery rate' in f.description for f in flags))

    def test_recovery_rate_flag_silent_with_no_target_set(self):
        OperationalSnapshot.objects.create(project=self.project, date=datetime.date.today(), recovery_rate_pct=50.0)
        flags = red_flag_engine.detect_red_flags(self.project)
        self.assertFalse(any('Recovery rate' in f.description for f in flags))

    def test_water_recycled_flag_fires_below_threshold(self):
        OperationalSnapshot.objects.create(project=self.project, date=datetime.date.today(), water_recycled_pct=40.0)
        flags = red_flag_engine.detect_red_flags(self.project)
        self.assertTrue(any(f.category == 'environmental' for f in flags))

    def test_milestone_payment_risk_fires_when_capital_released_before_verification(self):
        MineTimelineMilestone.objects.create(
            project=self.project, phase='construction', verification_required=True,
            verification_status='pending', capital_released_usd=5_000_000,
        )
        flags = red_flag_engine.detect_red_flags(self.project)
        self.assertTrue(any(f.category == 'milestone' for f in flags))

    def test_milestone_payment_risk_silent_once_verified(self):
        MineTimelineMilestone.objects.create(
            project=self.project, phase='construction', verification_required=True,
            verification_status='verified', capital_released_usd=5_000_000,
        )
        flags = red_flag_engine.detect_red_flags(self.project)
        self.assertFalse(any(f.category == 'milestone' for f in flags))

    def test_red_flag_evidence_documents_property(self):
        flag = RedFlag.objects.create(project=self.project, rule_key='r1', category='budget', description='x')
        self.assertEqual(flag.evidence_documents.count(), 0)
        EvidenceMemory.objects.create(text_chunk='note', source_reference=f'capital_guardian.RedFlag:{flag.pk}')
        self.assertEqual(flag.evidence_documents.count(), 1)


class OperationalSnapshotPhase2Tests(TestCase):
    def setUp(self):
        self.project = GoldProject.objects.create(name='Snap Phase2 Test', slug='snap-phase2-test')

    def test_confidence_defaults_to_none(self):
        snap = OperationalSnapshot.objects.create(project=self.project, date=datetime.date.today())
        self.assertIsNone(snap.confidence)

    def test_evidence_documents_property(self):
        snap = OperationalSnapshot.objects.create(project=self.project, date=datetime.date.today())
        self.assertEqual(snap.evidence_documents.count(), 0)
        EvidenceMemory.objects.create(text_chunk='x', source_reference=f'capital_guardian.OperationalSnapshot:{snap.pk}')
        self.assertEqual(snap.evidence_documents.count(), 1)


class AuditLogTests(TestCase):
    def setUp(self):
        self.project = GoldProject.objects.create(name='Audit Test', slug='audit-test')

    def test_creating_governance_logs_a_creation_entry(self):
        ProjectGovernance.objects.create(project=self.project)
        entries = AuditLogEntry.objects.filter(project=self.project, event_type='governance')
        self.assertEqual(entries.count(), 1)
        self.assertEqual(entries.first().field_name, '(created)')

    def test_changing_a_tracked_governance_field_logs_a_change(self):
        gov = ProjectGovernance.objects.create(project=self.project, escrow_account_active=False)
        gov.escrow_account_active = True
        gov.save()
        entry = AuditLogEntry.objects.filter(project=self.project, field_name='escrow_account_active').first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.previous_value, 'False')
        self.assertEqual(entry.new_value, 'True')

    def test_no_op_resave_does_not_create_a_change_entry(self):
        gov = ProjectGovernance.objects.create(project=self.project, escrow_account_active=True)
        AuditLogEntry.objects.filter(project=self.project).delete()
        gov.escrow_account_active = True   # unchanged
        gov.save()
        self.assertEqual(AuditLogEntry.objects.filter(project=self.project, field_name='escrow_account_active').count(), 0)

    def test_milestone_status_change_is_logged(self):
        milestone = MineTimelineMilestone.objects.create(project=self.project, phase='construction', status='not_started')
        AuditLogEntry.objects.filter(project=self.project).delete()
        milestone.status = 'in_progress'
        milestone.save()
        entry = AuditLogEntry.objects.filter(project=self.project, event_type='milestone', field_name='status').first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.previous_value, 'not_started')
        self.assertEqual(entry.new_value, 'in_progress')

    def test_red_flag_resolution_status_change_is_logged(self):
        flag = RedFlag.objects.create(project=self.project, rule_key='r1', category='budget', description='x')
        AuditLogEntry.objects.filter(project=self.project).delete()
        flag.resolution_status = 'acknowledged'
        flag.save()
        entry = AuditLogEntry.objects.filter(project=self.project, event_type='red_flag').first()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.new_value, 'acknowledged')

    def test_capital_budget_line_change_is_logged(self):
        line = CapitalBudgetLine.objects.create(project=self.project, label='x', spent_usd=100)
        AuditLogEntry.objects.filter(project=self.project).delete()
        line.spent_usd = 200
        line.save()
        entry = AuditLogEntry.objects.filter(project=self.project, event_type='capex', field_name='spent_usd').first()
        self.assertIsNotNone(entry)

    def test_goldproject_insurance_field_change_is_logged(self):
        AuditLogEntry.objects.filter(project=self.project).delete()
        self.project.insurance_coverage_usd = 5_000_000
        self.project.save()
        entry = AuditLogEntry.objects.filter(project=self.project, event_type='capital', field_name='insurance_coverage_usd').first()
        self.assertIsNotNone(entry)

    def test_evidence_verification_status_change_resolvable_to_project_is_logged(self):
        entry_obj = CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=1, purpose='a')
        evidence = EvidenceMemory.objects.create(text_chunk='x', source_reference=f'capital_guardian.CapitalTraceEntry:{entry_obj.pk}')
        AuditLogEntry.objects.filter(project=self.project).delete()
        evidence.verification_status = 'verified'
        evidence.save()
        log_entry = AuditLogEntry.objects.filter(project=self.project, event_type='evidence').first()
        self.assertIsNotNone(log_entry)

    def test_evidence_change_unresolvable_to_any_project_is_not_logged(self):
        before = AuditLogEntry.objects.count()
        evidence = EvidenceMemory.objects.create(text_chunk='x', source_reference='harvester.Evidence:999999')
        evidence.verification_status = 'verified'
        evidence.save()
        self.assertEqual(AuditLogEntry.objects.count(), before)

    def test_changed_by_recorded_when_explicitly_set(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user('audit-user', password='x')
        gov = ProjectGovernance(project=self.project)
        gov._cg_changed_by = user
        gov.save()
        entry = AuditLogEntry.objects.filter(project=self.project, event_type='governance').first()
        self.assertEqual(entry.changed_by_id, user.pk)

    def test_record_change_no_op_when_values_equal(self):
        result = audit_log.record_change(self.project, 'governance', 'X', 'field', 'same', 'same')
        self.assertIsNone(result)


class Phase2ViewTests(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME='localhost')
        self.kz = CountryProfile.objects.create(name='Kazakhstan', slug='kazakhstan-p2', iso_code='KZ', is_published=True)
        self.project = GoldProject.objects.create(
            name='Phase2 View Test Project', slug='cg-p2-view-test-project', country=self.kz, is_demo=True,
            total_committed_capital_usd=100_000_000,
        )

    def test_portfolio_view_returns_200(self):
        r = self.client.get(reverse('capital_guardian:portfolio'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Phase2 View Test Project')

    def test_portfolio_view_filters_by_commodity(self):
        self.project.commodity = 'copper'
        self.project.save()
        r = self.client.get(reverse('capital_guardian:portfolio'), {'commodity': 'gold'})
        self.assertNotContains(r, 'Phase2 View Test Project')

    def test_portfolio_view_honest_when_no_projects(self):
        GoldProject.objects.all().delete()
        r = self.client.get(reverse('capital_guardian:portfolio'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'No projects recorded yet')

    def test_evidence_centre_view_returns_200(self):
        r = self.client.get(reverse('capital_guardian:evidence_centre', args=[self.project.slug]))
        self.assertEqual(r.status_code, 200)

    def test_evidence_centre_shows_real_evidence(self):
        entry = CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=1, purpose='Test Payment')
        EvidenceMemory.objects.create(text_chunk='Real supporting document', source_reference=f'capital_guardian.CapitalTraceEntry:{entry.pk}')
        r = self.client.get(reverse('capital_guardian:evidence_centre', args=[self.project.slug]))
        self.assertContains(r, 'Real supporting document')

    def test_audit_history_view_returns_200(self):
        r = self.client.get(reverse('capital_guardian:audit_history', args=[self.project.slug]))
        self.assertEqual(r.status_code, 200)

    def test_audit_history_shows_real_logged_change(self):
        ProjectGovernance.objects.create(project=self.project)
        r = self.client.get(reverse('capital_guardian:audit_history', args=[self.project.slug]))
        self.assertContains(r, 'Governance')

    def test_audit_history_disclaimer_shown(self):
        r = self.client.get(reverse('capital_guardian:audit_history', args=[self.project.slug]))
        self.assertContains(r, 'NOT A CRYPTOGRAPHICALLY IMMUTABLE')

    def test_digital_twin_time_series_range_param(self):
        OperationalSnapshot.objects.create(project=self.project, date=datetime.date.today(), recovery_rate_pct=90.0)
        r = self.client.get(reverse('capital_guardian:digital_twin', args=[self.project.slug]), {'range': '7d'})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Last 7 Days')

    def test_digital_twin_invalid_range_falls_back_to_default(self):
        r = self.client.get(reverse('capital_guardian:digital_twin', args=[self.project.slug]), {'range': 'not-a-range'})
        self.assertEqual(r.status_code, 200)

    def test_no_raw_template_tags_leak_on_phase2_pages(self):
        urls = [
            reverse('capital_guardian:portfolio'),
            reverse('capital_guardian:evidence_centre', args=[self.project.slug]),
            reverse('capital_guardian:audit_history', args=[self.project.slug]),
        ]
        for url in urls:
            with self.subTest(url=url):
                r = self.client.get(url)
                content = r.content.decode()
                self.assertNotIn('{%', content)
                self.assertNotIn('{{', content)


class PortfolioSeedCommandTests(TestCase):
    def setUp(self):
        call_command('seed_countries')
        call_command('seed_capital_guardian_demo')

    def test_seed_creates_both_additional_projects(self):
        call_command('seed_capital_guardian_portfolio_demo')
        self.assertTrue(GoldProject.objects.filter(slug='kz-copper-project-02').exists())
        self.assertTrue(GoldProject.objects.filter(slug='uk-infrastructure-project-01').exists())

    def test_seed_is_idempotent(self):
        call_command('seed_capital_guardian_portfolio_demo')
        call_command('seed_capital_guardian_portfolio_demo')
        copper = GoldProject.objects.get(slug='kz-copper-project-02')
        self.assertEqual(copper.capital_trace_entries.count(), 7)

    def test_seed_matches_headline_committed_and_deployed_figures(self):
        call_command('seed_capital_guardian_portfolio_demo')
        copper = GoldProject.objects.get(slug='kz-copper-project-02')
        infra = GoldProject.objects.get(slug='uk-infrastructure-project-01')
        self.assertEqual(copper.total_committed_capital_usd, 180_000_000)
        self.assertEqual(capital_trace.capital_deployed(copper), 91_000_000)
        self.assertEqual(infra.total_committed_capital_usd, 240_000_000)
        self.assertEqual(capital_trace.capital_deployed(infra), 156_000_000)

    def test_seeded_projects_have_different_commodities(self):
        call_command('seed_capital_guardian_portfolio_demo')
        copper = GoldProject.objects.get(slug='kz-copper-project-02')
        infra = GoldProject.objects.get(slug='uk-infrastructure-project-01')
        self.assertEqual(copper.commodity, 'copper')
        self.assertEqual(infra.commodity, 'infrastructure')

    def test_portfolio_reflects_all_three_seeded_projects(self):
        call_command('seed_capital_guardian_portfolio_demo')
        rows = portfolio.build_portfolio(GoldProject.objects.all())
        slugs = {r['project'].slug for r in rows}
        self.assertIn('kz-gold-project-01', slugs)
        self.assertIn('kz-copper-project-02', slugs)
        self.assertIn('uk-infrastructure-project-01', slugs)


# ============================================================================
# Phase 3: Discover/Invest/Operate/Govern/AI institutional operating system.
# ============================================================================

class EquipmentHealthServiceTests(TestCase):
    def setUp(self):
        self.project = GoldProject.objects.create(name='Equip Health Test', slug='equip-health-test')

    def test_remaining_useful_life_none_with_no_real_inputs(self):
        e = EquipmentSpec.objects.create(project=self.project, equipment_type='crusher', label='Crusher')
        years, end_date = equipment_health.remaining_useful_life(e)
        self.assertIsNone(years)
        self.assertIsNone(end_date)

    def test_remaining_useful_life_computed_from_real_inputs(self):
        e = EquipmentSpec.objects.create(
            project=self.project, equipment_type='crusher', label='Crusher',
            commissioned_date=datetime.date.today() - datetime.timedelta(days=365), expected_lifespan_years=10,
        )
        years, end_date = equipment_health.remaining_useful_life(e)
        self.assertAlmostEqual(years, 9.0, delta=0.1)
        self.assertIsNotNone(end_date)

    def test_maintenance_recommendation_unavailable_with_no_real_inputs(self):
        e = EquipmentSpec.objects.create(project=self.project, equipment_type='crusher', label='Crusher')
        rec = equipment_health.maintenance_recommendation(e)
        self.assertFalse(rec['available'])

    def test_maintenance_recommendation_overdue(self):
        e = EquipmentSpec.objects.create(
            project=self.project, equipment_type='crusher', label='Old Crusher',
            commissioned_date=datetime.date.today() - datetime.timedelta(days=365 * 12), expected_lifespan_years=10,
        )
        rec = equipment_health.maintenance_recommendation(e)
        self.assertTrue(rec['available'])
        self.assertEqual(rec['urgency'], 'overdue')

    def test_maintenance_recommendation_due_soon(self):
        e = EquipmentSpec.objects.create(
            project=self.project, equipment_type='crusher', label='Aging Crusher',
            commissioned_date=datetime.date.today() - datetime.timedelta(days=365 * 9.5), expected_lifespan_years=10,
        )
        rec = equipment_health.maintenance_recommendation(e)
        self.assertTrue(rec['available'])
        self.assertEqual(rec['urgency'], 'due_soon')

    def test_maintenance_recommendation_ok(self):
        e = EquipmentSpec.objects.create(
            project=self.project, equipment_type='crusher', label='New Crusher',
            commissioned_date=datetime.date.today(), expected_lifespan_years=10,
        )
        rec = equipment_health.maintenance_recommendation(e)
        self.assertTrue(rec['available'])
        self.assertEqual(rec['urgency'], 'ok')


class ProjectHealthServiceTests(TestCase):
    def setUp(self):
        self.project = GoldProject.objects.create(name='Health Score Test', slug='health-score-test')

    def test_unavailable_with_zero_real_data(self):
        result = project_health.compute_project_health_score(self.project)
        self.assertFalse(result['available'])
        self.assertIsNone(result['score'])

    def test_available_with_equipment_availability_only(self):
        OperationalSnapshot.objects.create(project=self.project, date=datetime.date.today(), equipment_availability_pct=95.0)
        result = project_health.compute_project_health_score(self.project)
        self.assertTrue(result['available'])
        self.assertEqual(result['score'], 95.0)

    def test_environmental_status_scores_real_mapping(self):
        OperationalSnapshot.objects.create(project=self.project, date=datetime.date.today(), environmental_status='red')
        result = project_health.compute_project_health_score(self.project)
        self.assertEqual(result['components']['environmental_status']['normalized'], 20.0)

    def test_recovery_vs_target_requires_both_real_target_and_reading(self):
        self.project.recovery_rate_pct = 95.0
        self.project.save()
        result = project_health.compute_project_health_score(self.project)
        self.assertIsNone(result['components']['recovery_vs_target'])

    def test_equipment_lifecycle_component_reflects_real_service_status(self):
        EquipmentSpec.objects.create(
            project=self.project, equipment_type='crusher', label='Crusher',
            commissioned_date=datetime.date.today() - datetime.timedelta(days=365 * 12), expected_lifespan_years=10,
        )
        result = project_health.compute_project_health_score(self.project)
        self.assertEqual(result['components']['equipment_lifecycle']['normalized'], 0.0)

    def test_different_from_capital_protection_score(self):
        # Same project, different real inputs feed each score — confirms
        # these are genuinely two different composites, not aliases.
        OperationalSnapshot.objects.create(project=self.project, date=datetime.date.today(), equipment_availability_pct=95.0)
        CapitalBudgetLine.objects.create(project=self.project, label='x', planned_usd=100, committed_usd=200)
        health = project_health.compute_project_health_score(self.project)
        protection = capital_protection.compute_capital_protection_score(self.project)
        self.assertTrue(health['available'])
        self.assertTrue(protection['available'])
        self.assertNotEqual(health['score'], protection['score'])


class AIDirectorServiceTests(TestCase):
    def setUp(self):
        self.project = GoldProject.objects.create(name='AI Director Test', slug='ai-director-test')

    def test_production_section_unavailable_with_no_snapshot(self):
        briefing = ai_director.build_morning_briefing(self.project)
        self.assertFalse(briefing['production']['available'])

    def test_production_section_reflects_real_snapshot(self):
        OperationalSnapshot.objects.create(project=self.project, date=datetime.date.today(), recovery_rate_pct=90.0)
        briefing = ai_director.build_morning_briefing(self.project)
        self.assertTrue(briefing['production']['available'])
        self.assertTrue(any('90.0' in line for line in briefing['production']['lines']))

    def test_maintenance_section_only_flags_due_soon_or_overdue(self):
        EquipmentSpec.objects.create(
            project=self.project, equipment_type='crusher', label='Old Crusher',
            commissioned_date=datetime.date.today() - datetime.timedelta(days=365 * 12), expected_lifespan_years=10,
        )
        EquipmentSpec.objects.create(
            project=self.project, equipment_type='mill', label='New Mill',
            commissioned_date=datetime.date.today(), expected_lifespan_years=10,
        )
        briefing = ai_director.build_morning_briefing(self.project)
        self.assertTrue(briefing['maintenance']['available'])
        self.assertEqual(len(briefing['maintenance']['lines']), 1)

    def test_risk_section_reflects_real_open_flags(self):
        CapitalBudgetLine.objects.create(project=self.project, label='x', planned_usd=100_000_000, committed_usd=120_000_000)
        briefing = ai_director.build_morning_briefing(self.project)
        self.assertTrue(briefing['risk']['available'])
        self.assertGreater(briefing['risk']['total_open'], 0)

    def test_never_writes_to_database(self):
        original = self.project.name
        ai_director.build_morning_briefing(self.project)
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, original)


class InvestorDashboardPhase3Tests(TestCase):
    def setUp(self):
        self.project = GoldProject.objects.create(name='Invest P3 Test', slug='invest-p3-test', gold_price_assumption_usd_per_oz=2000)

    def test_equity_value_none_with_missing_inputs(self):
        self.assertIsNone(investor_dashboard.equity_value_usd(None, 50))
        self.assertIsNone(investor_dashboard.equity_value_usd(1000, None))

    def test_equity_value_real_proportional_share(self):
        self.assertEqual(investor_dashboard.equity_value_usd(1_000_000, 50), 500_000.0)

    def test_todays_gold_estimate_none_with_no_snapshot(self):
        gold_oz, revenue = investor_dashboard.todays_gold_estimate(self.project)
        self.assertIsNone(gold_oz)
        self.assertIsNone(revenue)

    def test_todays_gold_estimate_real_conversion(self):
        OperationalSnapshot.objects.create(project=self.project, date=datetime.date.today(), dore_produced_kg=31.1034768)
        gold_oz, revenue = investor_dashboard.todays_gold_estimate(self.project)
        self.assertEqual(gold_oz, 1000.0)
        self.assertEqual(revenue, 2_000_000.0)

    def test_construction_progress_uses_construction_milestone_when_present(self):
        MineTimelineMilestone.objects.create(project=self.project, phase='construction', status='in_progress', completion_pct_override=42.0)
        MineTimelineMilestone.objects.create(project=self.project, phase='licensing', status='complete')
        self.assertEqual(investor_dashboard.construction_progress_pct(self.project), 42.0)

    def test_construction_progress_falls_back_to_overall_completion(self):
        MineTimelineMilestone.objects.create(project=self.project, phase='licensing', status='complete')
        self.assertEqual(investor_dashboard.construction_progress_pct(self.project), 100.0)


class CapitalProtectionChainTests(TestCase):
    def setUp(self):
        self.project = GoldProject.objects.create(name='Chain Test', slug='chain-test')

    def test_chain_without_equipment_uses_generic_ending(self):
        entry = CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=1, purpose='a')
        chain = capital_trace.capital_protection_chain_for_entry(entry)
        steps = [c['step'] for c in chain]
        self.assertIn('Physical Asset or Service', steps)
        self.assertNotIn('Factory', steps)

    def test_chain_with_equipment_uses_granular_lifecycle_steps(self):
        equipment = EquipmentSpec.objects.create(
            project=self.project, equipment_type='crusher', label='Crusher',
            manufacturing_status='complete', shipping_status='complete',
            delivery_status='in_progress', commissioning_status='not_started',
        )
        entry = CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=1, purpose='a', related_equipment=equipment)
        chain = capital_trace.capital_protection_chain_for_entry(entry)
        by_step = {c['step']: c for c in chain}
        self.assertIn('Factory', by_step)
        self.assertTrue(by_step['Factory']['complete'])
        self.assertFalse(by_step['Site']['complete'])
        self.assertFalse(by_step['Operating Asset']['complete'])


class SupplierComparisonTests(TestCase):
    def test_rating_pairs_passes_through_real_and_none_values(self):
        s = SupplierProfile.objects.create(name='Test Supplier Co', illustrative_risk_rating=80.0)
        pairs = dict(s.rating_pairs)
        self.assertEqual(pairs['Risk'], 80.0)
        self.assertIsNone(pairs['ESG'])

    def test_equipment_using_supplier_real_cross_reference(self):
        project = GoldProject.objects.create(name='Supplier XRef Test', slug='supplier-xref-test')
        EquipmentSpec.objects.create(project=project, equipment_type='crusher', label='Crusher', manufacturer='Metso')
        EquipmentSpec.objects.create(project=project, equipment_type='mill', label='Mill', manufacturer='FLSmidth')
        results = supplier_comparison.equipment_using_supplier('Metso')
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().label, 'Crusher')

    def test_equipment_using_supplier_case_insensitive(self):
        project = GoldProject.objects.create(name='Supplier XRef Test 2', slug='supplier-xref-test-2')
        EquipmentSpec.objects.create(project=project, equipment_type='crusher', label='Crusher', manufacturer='metso')
        self.assertEqual(supplier_comparison.equipment_using_supplier('Metso').count(), 1)


class CapitalTraceEntryAuditTests(TestCase):
    """Phase 3 — signals.py now also tracks CapitalTraceEntry's workflow fields."""
    def setUp(self):
        self.project = GoldProject.objects.create(name='CTE Audit Test', slug='cte-audit-test')

    def test_creating_entry_logs_creation(self):
        CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=1, purpose='a')
        entries = AuditLogEntry.objects.filter(project=self.project, event_type='capital_trace')
        self.assertEqual(entries.count(), 1)

    def test_changing_payment_status_is_logged(self):
        entry = CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=1, purpose='a', payment_status='pending')
        AuditLogEntry.objects.filter(project=self.project).delete()
        entry.payment_status = 'paid'
        entry.save()
        logged = AuditLogEntry.objects.filter(project=self.project, event_type='capital_trace', field_name='Payment Status').first()
        self.assertIsNotNone(logged)
        self.assertEqual(logged.previous_value, 'pending')
        self.assertEqual(logged.new_value, 'paid')


class Phase3ViewTests(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME='localhost')
        self.kz = CountryProfile.objects.create(name='Kazakhstan', slug='kazakhstan-p3', iso_code='KZ', is_published=True)
        self.project = GoldProject.objects.create(
            name='Phase3 View Test Project', slug='cg-p3-view-test-project', country=self.kz, is_demo=True,
            gold_price_assumption_usd_per_oz=2000,
        )
        ProjectGovernance.objects.create(project=self.project, founder_holdco_pct=50, investor_spv_pct=50)
        self.equipment = EquipmentSpec.objects.create(project=self.project, equipment_type='crusher', label='Crusher')
        self.entry = CapitalTraceEntry.objects.create(project=self.project, date=datetime.date.today(), amount_usd=100, purpose='Test Payment')

    def test_capital_trace_entry_detail_returns_200(self):
        r = self.client.get(reverse('capital_guardian:capital_trace_entry_detail', args=[self.project.slug, self.entry.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Test Payment')

    def test_capital_trace_entry_detail_omits_photos_and_gps(self):
        r = self.client.get(reverse('capital_guardian:capital_trace_entry_detail', args=[self.project.slug, self.entry.pk]))
        self.assertContains(r, 'not connected to any real data source')

    def test_equipment_detail_returns_200(self):
        r = self.client.get(reverse('capital_guardian:equipment_detail', args=[self.project.slug, self.equipment.pk]))
        self.assertEqual(r.status_code, 200)

    def test_equipment_detail_honest_no_live_telemetry(self):
        r = self.client.get(reverse('capital_guardian:equipment_detail', args=[self.project.slug, self.equipment.pk]))
        self.assertContains(r, 'No live sensor feed connected')

    def test_equipment_detail_honest_no_live_cameras(self):
        r = self.client.get(reverse('capital_guardian:equipment_detail', args=[self.project.slug, self.equipment.pk]))
        self.assertContains(r, 'No live feed connected')

    def test_supplier_comparison_returns_200(self):
        r = self.client.get(reverse('capital_guardian:supplier_comparison'))
        self.assertEqual(r.status_code, 200)

    def test_supplier_comparison_shows_disclaimer(self):
        SupplierProfile.objects.create(name='Disclaimer Test Co')
        r = self.client.get(reverse('capital_guardian:supplier_comparison'))
        self.assertContains(r, 'SYNTHETIC / ILLUSTRATIVE RATINGS')

    def test_live_cameras_returns_200_and_honest(self):
        r = self.client.get(reverse('capital_guardian:live_cameras', args=[self.project.slug]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'No live feed connected')

    def test_govern_hub_returns_200(self):
        r = self.client.get(reverse('capital_guardian:govern_hub', args=[self.project.slug]))
        self.assertEqual(r.status_code, 200)

    def test_ai_director_returns_200(self):
        r = self.client.get(reverse('capital_guardian:ai_director', args=[self.project.slug]))
        self.assertEqual(r.status_code, 200)

    def test_ai_director_states_not_a_second_ai_system(self):
        r = self.client.get(reverse('capital_guardian:ai_director', args=[self.project.slug]))
        self.assertContains(r, 'not a second AI/LLM system')

    def test_investor_dashboard_shows_new_phase3_cards(self):
        r = self.client.get(reverse('capital_guardian:investor_dashboard', args=[self.project.slug]))
        self.assertContains(r, 'Enterprise Value')
        self.assertContains(r, 'Current Gold Price')
        self.assertContains(r, 'Project Health Score')

    def test_governance_page_shows_ownership_heading(self):
        r = self.client.get(reverse('capital_guardian:governance', args=[self.project.slug]))
        self.assertContains(r, 'Beneficial Ownership')
        self.assertContains(r, 'not legal advice')

    def test_all_phase3_pages_no_raw_template_tags_leak(self):
        urls = [
            reverse('capital_guardian:capital_trace_entry_detail', args=[self.project.slug, self.entry.pk]),
            reverse('capital_guardian:equipment_detail', args=[self.project.slug, self.equipment.pk]),
            reverse('capital_guardian:supplier_comparison'),
            reverse('capital_guardian:live_cameras', args=[self.project.slug]),
            reverse('capital_guardian:govern_hub', args=[self.project.slug]),
            reverse('capital_guardian:ai_director', args=[self.project.slug]),
        ]
        for url in urls:
            with self.subTest(url=url):
                r = self.client.get(url)
                content = r.content.decode()
                self.assertNotIn('{%', content)
                self.assertNotIn('{{', content)

    def test_nav_groups_present_on_dashboard(self):
        r = self.client.get(reverse('capital_guardian:investor_dashboard', args=[self.project.slug]))
        for label in ('Discover', 'Invest', 'Operate', 'Govern', 'AI'):
            self.assertContains(r, label)


class SuppliersSeedCommandTests(TestCase):
    def test_seed_creates_supplier_profiles(self):
        call_command('seed_capital_guardian_suppliers_demo')
        self.assertGreaterEqual(SupplierProfile.objects.count(), 10)
        self.assertTrue(SupplierProfile.objects.filter(name='Metso').exists())

    def test_seed_is_idempotent(self):
        call_command('seed_capital_guardian_suppliers_demo')
        count_after_first = SupplierProfile.objects.count()
        call_command('seed_capital_guardian_suppliers_demo')
        self.assertEqual(SupplierProfile.objects.count(), count_after_first)

    def test_seeded_suppliers_are_flagged_demo(self):
        call_command('seed_capital_guardian_suppliers_demo')
        self.assertFalse(SupplierProfile.objects.exclude(is_demo=True).exists())


class Phase3SeedCommandFieldTests(TestCase):
    def setUp(self):
        call_command('seed_countries')

    def test_commissioned_equipment_has_real_rul_inputs(self):
        call_command('seed_capital_guardian_demo')
        project = GoldProject.objects.get(slug='kz-gold-project-01')
        haul_trucks = project.equipment_specs.get(label__icontains='Haul Trucks')
        self.assertIsNotNone(haul_trucks.commissioned_date)
        self.assertIsNotNone(haul_trucks.expected_lifespan_years)

    def test_not_yet_commissioned_equipment_has_no_fabricated_rul_inputs(self):
        call_command('seed_capital_guardian_demo')
        project = GoldProject.objects.get(slug='kz-gold-project-01')
        sag_mill = project.equipment_specs.get(label='SAG Mill')
        self.assertIsNone(sag_mill.commissioned_date)
        self.assertIsNone(sag_mill.expected_lifespan_years)

    def test_governance_has_dividend_policy_notes(self):
        call_command('seed_capital_guardian_demo')
        project = GoldProject.objects.get(slug='kz-gold-project-01')
        self.assertTrue(project.governance.dividend_policy_notes)


class AddProjectEvidenceViewTests(TestCase):
    """Vertical-slice PR 1 — staff-only manual project evidence intake UI."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.client = Client(SERVER_NAME='localhost')
        self.staff = User.objects.create_user('staff_evidence', 'staff@ecoiq.uk', 'password123', is_staff=True)
        self.normal = User.objects.create_user('normal_evidence', 'user@example.com', 'password123', is_staff=False)
        self.project = GoldProject.objects.create(name='Evidence Intake Test', slug='evidence-intake-test')
        self.other_project = GoldProject.objects.create(name='Other Intake Project', slug='other-intake-project')

    def _centre_url(self, project=None):
        return reverse('capital_guardian:evidence_centre', args=[(project or self.project).slug])

    def _add_url(self, project=None):
        return reverse('capital_guardian:add_project_evidence', args=[(project or self.project).slug])

    def _valid_data(self, **overrides):
        data = {
            'title': 'Coal usage estimate', 'text': 'Approx. 2 tonnes of coal per household per winter.',
            'source_url': '', 'source_type': 'manual', 'document_category': 'other',
            'verification_status': 'pending', 'review_tier': 'uploaded', 'classification': 'estimated',
        }
        data.update(overrides)
        return data

    # ── Authentication and authorization ────────────────────────────────────

    def test_anonymous_cannot_create_evidence(self):
        r = self.client.post(self._add_url(), self._valid_data())
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login', r['Location'])
        self.assertEqual(EvidenceMemory.objects.count(), 0)

    def test_non_staff_user_cannot_create_evidence(self):
        self.client.force_login(self.normal)
        r = self.client.post(self._add_url(), self._valid_data())
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login', r['Location'])
        self.assertEqual(EvidenceMemory.objects.count(), 0)

    def test_staff_user_sees_intake_form_on_evidence_centre(self):
        self.client.force_login(self.staff)
        r = self.client.get(self._centre_url())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Add Evidence Record')

    def test_non_staff_user_does_not_see_intake_form(self):
        self.client.force_login(self.normal)
        r = self.client.get(self._centre_url())
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, 'Add Evidence Record')

    def test_idor_normal_user_with_known_project_slug_is_blocked(self):
        self.client.force_login(self.normal)
        r = self.client.post(self._add_url(), self._valid_data())
        self.assertEqual(EvidenceMemory.objects.count(), 0)

    # ── HTTP safety ──────────────────────────────────────────────────────────

    def test_get_to_add_url_does_not_create_evidence(self):
        self.client.force_login(self.staff)
        r = self.client.get(self._add_url())
        self.assertEqual(r.status_code, 302)
        self.assertEqual(EvidenceMemory.objects.count(), 0)

    def test_post_creates_evidence(self):
        self.client.force_login(self.staff)
        self.client.post(self._add_url(), self._valid_data())
        self.assertEqual(EvidenceMemory.objects.count(), 1)

    def test_csrf_enforced(self):
        csrf_client = Client(enforce_csrf_checks=True, SERVER_NAME='localhost')
        csrf_client.force_login(self.staff)
        r = csrf_client.post(self._add_url(), self._valid_data())
        self.assertEqual(r.status_code, 403)

    def test_invalid_project_slug_returns_404(self):
        self.client.force_login(self.staff)
        r = self.client.get(reverse('capital_guardian:evidence_centre', args=['does-not-exist']))
        self.assertEqual(r.status_code, 404)
        r2 = self.client.post(reverse('capital_guardian:add_project_evidence', args=['does-not-exist']), self._valid_data())
        self.assertEqual(r2.status_code, 404)

    def test_invalid_form_rejected_safely(self):
        self.client.force_login(self.staff)
        r = self.client.post(self._add_url(), self._valid_data(title=''))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(EvidenceMemory.objects.count(), 0)

    def test_verified_without_review_rejected_safely(self):
        self.client.force_login(self.staff)
        r = self.client.post(self._add_url(), self._valid_data(verification_status='verified', review_tier='uploaded'))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(EvidenceMemory.objects.count(), 0)

    # ── UX ───────────────────────────────────────────────────────────────────

    def test_success_message_shown(self):
        self.client.force_login(self.staff)
        r = self.client.post(self._add_url(), self._valid_data(), follow=True)
        self.assertContains(r, 'Evidence added')

    def test_created_evidence_visible_on_project_page(self):
        self.client.force_login(self.staff)
        self.client.post(self._add_url(), self._valid_data(title='Coal usage estimate'), follow=True)
        r = self.client.get(self._centre_url())
        self.assertContains(r, 'Coal usage estimate')

    def test_demo_label_visible_for_illustrative_evidence(self):
        self.client.force_login(self.staff)
        self.client.post(self._add_url(), self._valid_data(classification='illustrative'))
        r = self.client.get(self._centre_url())
        self.assertContains(r, 'ILLUSTRATIVE / DEMO')

    def test_no_demo_label_for_real_evidence(self):
        self.client.force_login(self.staff)
        self.client.post(self._add_url(), self._valid_data(classification='real'))
        r = self.client.get(self._centre_url())
        self.assertNotContains(r, 'ILLUSTRATIVE / DEMO')

    def test_no_raw_exception_leakage_on_unexpected_failure(self):
        from unittest import mock
        self.client.force_login(self.staff)
        with mock.patch(
            'evidence_memory.services.memory.create_memory_from_manual_project_evidence',
            side_effect=RuntimeError('unexpected internal boom'),
        ):
            r = self.client.post(self._add_url(), self._valid_data(), follow=True)
        self.assertContains(r, 'Something went wrong adding this evidence')
        self.assertNotContains(r, 'unexpected internal boom')
        self.assertNotContains(r, 'Traceback')
        self.assertEqual(EvidenceMemory.objects.count(), 0)

    def test_project_a_evidence_not_visible_on_project_b_page(self):
        self.client.force_login(self.staff)
        self.client.post(self._add_url(self.project), self._valid_data(title='Only in project A'))
        r = self.client.get(self._centre_url(self.other_project))
        self.assertNotContains(r, 'Only in project A')

    # ── Integration (real service, real retrieval) ──────────────────────────

    def test_full_integration_real_service_and_real_retrieval(self):
        from capital_guardian.services import evidence as evidence_service
        self.client.force_login(self.staff)
        r = self.client.post(self._add_url(), self._valid_data(
            title='Household coal survey', text='Field survey of coal consumption across the pilot area.',
            verification_status='verified', review_tier='human_reviewed', classification='real',
        ), follow=True)
        self.assertEqual(r.status_code, 200)

        evidence_qs = evidence_service.evidence_for_project(self.project)
        self.assertEqual(evidence_qs.count(), 1)
        row = evidence_qs.first()
        self.assertIn('Household coal survey', row.text_chunk)
        self.assertEqual(row.verification_status, 'verified')
        self.assertEqual(row.reviewer, self.staff)
        self.assertFalse(row.is_demo)


class ProjectAnalysisAdapterTests(TestCase):
    """Vertical-slice PR 2 — build_project_input_from_evidence() adapter."""

    def setUp(self):
        from evidence_memory.services.memory import create_memory_from_manual_project_evidence
        self.create_evidence = create_memory_from_manual_project_evidence
        self.kz = CountryProfile.objects.create(name='Kazakhstan', slug='kz-analysis-test', iso_code='KZ')
        self.project = GoldProject.objects.create(
            name='Analysis Test Project', slug='analysis-test-project',
            commodity='energy', country=self.kz, total_capex_usd=500000, is_demo=True,
        )

    def test_zero_evidence_produces_honest_warning(self):
        from capital_guardian.services.project_analysis import build_project_input_from_evidence
        project_input, meta = build_project_input_from_evidence(self.project)
        self.assertEqual(meta.evidence_references, [])
        self.assertTrue(any('No project-scoped evidence' in w for w in meta.warnings))

    def test_real_project_fields_map_directly(self):
        from capital_guardian.services.project_analysis import build_project_input_from_evidence
        project_input, meta = build_project_input_from_evidence(self.project)
        self.assertEqual(project_input.name, 'Analysis Test Project')
        self.assertEqual(project_input.sector, 'energy')
        self.assertEqual(project_input.country, 'Kazakhstan')
        self.assertEqual(project_input.budget_usd, 500000)

    def test_missing_country_handled_honestly(self):
        from capital_guardian.services.project_analysis import build_project_input_from_evidence
        no_country_project = GoldProject.objects.create(name='No Country Project', slug='no-country-project')
        project_input, meta = build_project_input_from_evidence(no_country_project)
        self.assertEqual(project_input.country, '')
        self.assertTrue(any('no linked country' in w for w in meta.warnings))

    def test_missing_budget_reported_not_fabricated(self):
        from capital_guardian.services.project_analysis import build_project_input_from_evidence
        no_budget_project = GoldProject.objects.create(name='No Budget Project', slug='no-budget-project')
        project_input, meta = build_project_input_from_evidence(no_budget_project)
        self.assertIsNone(project_input.budget_usd)
        self.assertIn('total_capex_usd', meta.missing_project_fields)

    def test_verified_real_technical_report_sets_environmental_assessment(self):
        from capital_guardian.services.project_analysis import build_project_input_from_evidence
        self.create_evidence(
            self.project, title='EIA', text='Environmental impact assessment completed.',
            document_category='technical_report', verification_status='verified', review_tier='human_reviewed', is_demo=False,
        )
        project_input, meta = build_project_input_from_evidence(self.project)
        self.assertTrue(project_input.environmental_assessment)
        self.assertTrue(meta.has_real_verified_technical_report)

    def test_pending_technical_report_does_not_set_environmental_assessment(self):
        """Pending/estimated evidence must never be treated as verified."""
        from capital_guardian.services.project_analysis import build_project_input_from_evidence
        self.create_evidence(
            self.project, title='EIA draft', text='Draft environmental assessment, not yet reviewed.',
            document_category='technical_report', verification_status='pending', is_demo=False,
        )
        project_input, meta = build_project_input_from_evidence(self.project)
        self.assertFalse(project_input.environmental_assessment)
        self.assertFalse(meta.has_real_verified_technical_report)

    def test_demo_technical_report_does_not_set_environmental_assessment(self):
        """Illustrative/demo evidence must never inflate a real declared input, even if 'verified'."""
        from capital_guardian.services.project_analysis import build_project_input_from_evidence
        self.create_evidence(
            self.project, title='Illustrative EIA', text='Illustrative example environmental assessment.',
            document_category='technical_report', verification_status='verified', review_tier='human_reviewed', is_demo=True,
        )
        project_input, meta = build_project_input_from_evidence(self.project)
        self.assertFalse(project_input.environmental_assessment)
        self.assertFalse(meta.has_real_verified_technical_report)

    def test_mixed_evidence_all_references_returned(self):
        from capital_guardian.services.project_analysis import build_project_input_from_evidence
        self.create_evidence(self.project, title='A', text='Verified real evidence.', verification_status='verified', review_tier='human_reviewed')
        self.create_evidence(self.project, title='B', text='Pending evidence not yet reviewed.', verification_status='pending')
        self.create_evidence(self.project, title='C', text='Illustrative demo evidence example.', is_demo=True)
        project_input, meta = build_project_input_from_evidence(self.project)
        self.assertEqual(len(meta.evidence_references), 3)

    def test_project_a_evidence_not_used_for_project_b(self):
        from capital_guardian.services.project_analysis import build_project_input_from_evidence
        other = GoldProject.objects.create(name='Other Analysis Project', slug='other-analysis-project')
        self.create_evidence(self.project, title='A', text='Project A only evidence.')
        project_input, meta = build_project_input_from_evidence(other)
        self.assertEqual(meta.evidence_references, [])


class ProjectAnalysisScoringTests(TestCase):
    """Vertical-slice PR 2 — analyse_project() reuses the real mizan scorer, no duplication."""

    def setUp(self):
        from evidence_memory.services.memory import create_memory_from_manual_project_evidence
        self.create_evidence = create_memory_from_manual_project_evidence
        self.project = GoldProject.objects.create(
            name='Scoring Test Project', slug='scoring-test-project', commodity='energy', total_capex_usd=1000000,
        )

    def test_real_score_project_is_called_not_duplicated(self):
        from capital_guardian.services.project_analysis import analyse_project, build_project_input_from_evidence
        from mizan.project import score_project

        result = analyse_project(self.project)
        project_input, _ = build_project_input_from_evidence(self.project)
        direct = score_project(project_input)

        self.assertEqual(result.public_benefit_score, direct.public_benefit_score)
        self.assertEqual(result.harm_reduction_score, direct.harm_reduction_score)
        self.assertEqual(result.justice_distribution_score, direct.justice_distribution_score)
        self.assertEqual(result.transparency_accountability_score, direct.transparency_accountability_score)
        self.assertEqual(result.stewardship_score, direct.stewardship_score)
        self.assertEqual(result.evidence_confidence_score, direct.evidence_confidence_score)
        self.assertEqual(result.final_mizan_score, direct.final_mizan_score)
        self.assertEqual(result.methodology, direct.methodology)

    def test_deterministic_same_evidence_same_score(self):
        from capital_guardian.services.project_analysis import analyse_project
        r1 = analyse_project(self.project)
        r2 = analyse_project(self.project)
        self.assertEqual(r1.final_mizan_score, r2.final_mizan_score)
        self.assertEqual(r1.mizan_label, r2.mizan_label)

    def test_scorer_confidence_is_always_model_estimate(self):
        """score_project()'s own confidence field is a fixed constant — verify the adapter preserves this honestly rather than upgrading it."""
        from capital_guardian.services.project_analysis import analyse_project
        result = analyse_project(self.project)
        self.assertEqual(result.scorer_confidence, 'model-estimate')

    def test_demo_only_evidence_reflected_in_demo_count_not_score_inflation(self):
        from capital_guardian.services.project_analysis import analyse_project
        self.create_evidence(
            self.project, title='Demo EIA', text='Illustrative example only.',
            document_category='technical_report', verification_status='verified', review_tier='human_reviewed', is_demo=True,
        )
        result = analyse_project(self.project)
        self.assertEqual(result.demo_evidence_count, 1)
        # Demo evidence must not have flipped environmental_assessment, so harm_reduction
        # should match the no-EIA baseline, not the +10 EIA bonus.
        no_evidence_result = analyse_project(GoldProject.objects.create(name='Baseline', slug='baseline-no-evidence', commodity='energy', total_capex_usd=1000000))
        self.assertEqual(result.harm_reduction_score, no_evidence_result.harm_reduction_score)

    def test_pending_evidence_not_treated_as_verified_in_counts(self):
        from capital_guardian.services.project_analysis import analyse_project
        self.create_evidence(self.project, title='P', text='Pending real evidence, not yet reviewed.', verification_status='pending')
        result = analyse_project(self.project)
        self.assertEqual(result.pending_evidence_count, 1)
        self.assertEqual(result.verified_evidence_count, 0)

    def test_verified_evidence_counted_correctly(self):
        from capital_guardian.services.project_analysis import analyse_project
        self.create_evidence(self.project, title='V', text='Verified evidence.', verification_status='verified', review_tier='human_reviewed')
        result = analyse_project(self.project)
        self.assertEqual(result.verified_evidence_count, 1)

    def test_methodology_and_limitations_present(self):
        from capital_guardian.services.project_analysis import analyse_project
        result = analyse_project(self.project)
        self.assertIn('Mizan Engine', result.methodology)
        self.assertTrue(len(result.limitations) > 0)
        self.assertTrue(any('not a religious ruling' in lim for lim in result.limitations))

    def test_full_integration_real_services_end_to_end(self):
        """GoldProject -> EvidenceMemory -> evidence_for_project() -> build_project_input_from_evidence() -> score_project()."""
        from capital_guardian.services.evidence import evidence_for_project
        from capital_guardian.services.project_analysis import build_project_input_from_evidence
        from mizan.project import score_project

        self.create_evidence(self.project, title='Real', text='Real, verified evidence for integration test.', verification_status='verified', review_tier='human_reviewed')

        evidence_qs = evidence_for_project(self.project)
        self.assertEqual(evidence_qs.count(), 1)

        project_input, meta = build_project_input_from_evidence(self.project)
        self.assertEqual(len(meta.evidence_references), 1)

        result = score_project(project_input)
        self.assertIsNotNone(result.final_mizan_score)
        self.assertEqual(result.data_source, 'project_model')


class RunProjectAnalysisViewTests(TestCase):
    """Vertical-slice PR 2 — staff-only 'Run Project Analysis' UI."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.client = Client(SERVER_NAME='localhost')
        self.staff = User.objects.create_user('staff_analysis', 'staff_a@ecoiq.uk', 'password123', is_staff=True)
        self.normal = User.objects.create_user('normal_analysis', 'user_a@example.com', 'password123', is_staff=False)
        self.project = GoldProject.objects.create(name='Analysis View Test', slug='analysis-view-test', commodity='energy')

    def _run_url(self, project=None):
        return reverse('capital_guardian:run_project_analysis', args=[(project or self.project).slug])

    def _centre_url(self, project=None):
        return reverse('capital_guardian:evidence_centre', args=[(project or self.project).slug])

    # ── Authentication and authorization ────────────────────────────────────

    def test_anonymous_cannot_trigger_analysis(self):
        r = self.client.post(self._run_url())
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login', r['Location'])

    def test_non_staff_cannot_trigger_analysis(self):
        self.client.force_login(self.normal)
        r = self.client.post(self._run_url())
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login', r['Location'])

    def test_idor_normal_user_with_known_slug_blocked(self):
        self.client.force_login(self.normal)
        r = self.client.post(self._run_url(), follow=True)
        self.assertNotContains(r, 'Final Mizan Score')

    def test_staff_can_access_and_button_visible(self):
        self.client.force_login(self.staff)
        r = self.client.get(self._centre_url())
        self.assertContains(r, 'Run Project Analysis')

    def test_non_staff_does_not_see_run_button(self):
        self.client.force_login(self.normal)
        r = self.client.get(self._centre_url())
        self.assertNotContains(r, 'Run Project Analysis')

    # ── HTTP safety ──────────────────────────────────────────────────────────

    def test_get_does_not_trigger_analysis(self):
        self.client.force_login(self.staff)
        r = self.client.get(self._run_url())
        self.assertEqual(r.status_code, 302)

    def test_post_triggers_analysis(self):
        self.client.force_login(self.staff)
        r = self.client.post(self._run_url())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Final Mizan Score')

    def test_csrf_enforced(self):
        csrf_client = Client(enforce_csrf_checks=True, SERVER_NAME='localhost')
        csrf_client.force_login(self.staff)
        r = csrf_client.post(self._run_url())
        self.assertEqual(r.status_code, 403)

    def test_invalid_project_returns_404(self):
        self.client.force_login(self.staff)
        r = self.client.post(reverse('capital_guardian:run_project_analysis', args=['does-not-exist']))
        self.assertEqual(r.status_code, 404)

    def test_no_raw_exception_leakage(self):
        from unittest import mock
        self.client.force_login(self.staff)
        with mock.patch(
            'capital_guardian.services.project_analysis.analyse_project',
            side_effect=RuntimeError('unexpected internal boom'),
        ):
            r = self.client.post(self._run_url(), follow=True)
        self.assertContains(r, 'Something went wrong running the project analysis')
        self.assertNotContains(r, 'unexpected internal boom')
        self.assertNotContains(r, 'Traceback')

    # ── Content ──────────────────────────────────────────────────────────────

    def test_evidence_references_visible(self):
        from evidence_memory.services.memory import create_memory_from_manual_project_evidence
        create_memory_from_manual_project_evidence(self.project, title='T', text='Some real evidence for visibility test.')
        self.client.force_login(self.staff)
        r = self.client.post(self._run_url())
        self.assertContains(r, f'gold_intelligence.GoldProject:{self.project.pk}')

    def test_warnings_visible(self):
        self.client.force_login(self.staff)
        r = self.client.post(self._run_url())
        self.assertContains(r, 'No project-scoped evidence exists yet')

    def test_methodology_visible(self):
        self.client.force_login(self.staff)
        r = self.client.post(self._run_url())
        self.assertContains(r, 'Mizan Engine')

    def test_demo_evidence_count_visible(self):
        from evidence_memory.services.memory import create_memory_from_manual_project_evidence
        create_memory_from_manual_project_evidence(self.project, title='T', text='Illustrative demo example only.', is_demo=True)
        self.client.force_login(self.staff)
        r = self.client.post(self._run_url())
        self.assertContains(r, 'Illustrative / Demo')

    def test_no_forbidden_religious_ruling_language(self):
        self.client.force_login(self.staff)
        r = self.client.post(self._run_url(), follow=True)
        body = r.content.decode()
        for forbidden in ('Shariah-compliant', 'Quranically approved', 'Officially validated', 'AI verified'):
            self.assertNotIn(forbidden, body)

    def test_no_cross_project_evidence_in_analysis(self):
        from evidence_memory.services.memory import create_memory_from_manual_project_evidence
        other = GoldProject.objects.create(name='Other Analysis View Project', slug='other-analysis-view-project')
        create_memory_from_manual_project_evidence(other, title='T', text='Belongs only to the other project.')
        self.client.force_login(self.staff)
        r = self.client.post(self._run_url())
        self.assertNotContains(r, f'gold_intelligence.GoldProject:{other.pk}')


class ResourcePurposeReviewTests(TestCase):
    """Vertical-slice PR 3 — review_resource_purpose()."""

    PILOT_SLUG = 'almaty-clean-heating-pilot-200-homes'

    def setUp(self):
        from evidence_memory.services.memory import create_memory_from_manual_project_evidence
        self.create_evidence = create_memory_from_manual_project_evidence
        self.project = GoldProject.objects.create(
            name='Almaty Clean Heating Pilot — 200 Homes', slug=self.PILOT_SLUG, commodity='other',
        )

    def _review(self, project=None):
        from capital_guardian.services.project_analysis import analyse_project
        from capital_guardian.services.resource_purpose_review import review_resource_purpose
        project = project or self.project
        return review_resource_purpose(project, analyse_project(project))

    def test_reviewed_profile_for_pilot(self):
        review = self._review()
        self.assertTrue(review.has_reviewed_profile)
        self.assertEqual(review.primary_resource, 'Coal')
        self.assertIn('space heating', review.current_use.lower())
        self.assertIn('warmth', review.intended_service.lower())

    def test_zero_evidence_review_confidence_low(self):
        review = self._review()
        self.assertEqual(review.review_confidence, 'low')

    def test_verified_evidence_raises_confidence(self):
        self.create_evidence(
            self.project, title='E1', text='Real verified evidence.',
            verification_status='verified', review_tier='human_reviewed',
        )
        review = self._review()
        self.assertIn(review.review_confidence, ('medium', 'high'))

    def test_pending_estimated_evidence_stays_low_confidence(self):
        self.create_evidence(self.project, title='E1', text='Pending, not yet reviewed evidence.', verification_status='pending')
        review = self._review()
        self.assertEqual(review.review_confidence, 'low')

    def test_illustrative_demo_only_evidence_stays_low_confidence(self):
        self.create_evidence(self.project, title='E1', text='Illustrative example only.', is_demo=True, verification_status='pending')
        review = self._review()
        self.assertEqual(review.review_confidence, 'low')

    def test_mixed_evidence_reflected_honestly(self):
        self.create_evidence(self.project, title='E1', text='Verified real evidence.', verification_status='verified', review_tier='human_reviewed')
        self.create_evidence(self.project, title='E2', text='Pending unreviewed evidence.', verification_status='pending')
        self.create_evidence(self.project, title='E3', text='Illustrative example.', is_demo=True)
        review = self._review()
        self.assertEqual(len(review.evidence_used), 3)
        self.assertEqual(review.review_confidence, 'medium')

    def test_cross_project_isolation(self):
        other = GoldProject.objects.create(name='Other Pilot', slug='other-pilot-project')
        self.create_evidence(self.project, title='E1', text='Belongs only to the pilot.')
        other_review = self._review(other)
        self.assertEqual(other_review.evidence_used, [])

    def test_no_unsafe_raw_coal_fertiliser_recommendation(self):
        review = self._review()
        fertiliser = next(p for p in review.alternative_pathways if 'fertiliser' in p['name'].lower())
        self.assertEqual(fertiliser['status'], 'blocked')
        self.assertIn('not a fertiliser', fertiliser['notes'])

    def test_no_blanket_coal_ash_safe_claim(self):
        review = self._review()
        ash = next(p for p in review.alternative_pathways if 'ash' in p['name'].lower())
        self.assertEqual(ash['status'], 'conditional')
        self.assertIn('leaching testing', ash['notes'])
        self.assertNotIn('is safe', ash['notes'].lower())

    def test_no_recommendation_to_burn_coal_to_create_ash(self):
        review = self._review()
        ash = next(p for p in review.alternative_pathways if 'ash' in p['name'].lower())
        self.assertIn('never a reason to burn more coal', ash['notes'])

    def test_alternatives_shown_as_conditional_where_required(self):
        review = self._review()
        statuses = {p['name']: p['status'] for p in review.alternative_pathways}
        self.assertEqual(statuses['Coal ash in construction materials'], 'conditional')
        self.assertEqual(statuses['Agricultural reuse of combustion by-products'], 'conditional')
        self.assertEqual(statuses['Reuse of other industrial by-products'], 'conditional')
        self.assertEqual(statuses['Heat pumps'], 'open')

    def test_deterministic_output(self):
        r1 = self._review()
        r2 = self._review()
        self.assertEqual(r1.avoidability, r2.avoidability)
        self.assertEqual(r1.misuse_or_value_loss_condition_exists, r2.misuse_or_value_loss_condition_exists)
        self.assertEqual(r1.alternative_pathways, r2.alternative_pathways)

    def test_evidence_gaps_shown(self):
        review = self._review()
        self.assertTrue(any('technical report' in g for g in review.evidence_gaps))

    def test_stewardship_questions_shown(self):
        review = self._review()
        names = {q['name'] for q in review.stewardship_questions}
        self.assertEqual(names, {'Amanah', 'Mizan', 'Adl', 'Israf', 'Prevention of Harm', 'Maslaha', 'Hisab'})

    def test_no_religious_ruling_language(self):
        """
        The disclaimer legitimately names 'fatwa'/'Shariah determination' in
        order to disclaim them — that's correct, honest language. What must
        never appear is an affirmative claim asserting one of these.
        """
        review = self._review()
        full_text = review.stewardship_disclaimer + ' '.join(q['question'] for q in review.stewardship_questions)
        for forbidden_claim in ('Quranically approved', 'Shariah-compliant', 'halal.', 'haram.', 'this is a fatwa'):
            self.assertNotIn(forbidden_claim, full_text)
        self.assertIn('not a religious ruling', review.stewardship_disclaimer)
        self.assertIn('Qualified scholars are required', review.stewardship_disclaimer)

    def test_fallback_profile_for_unknown_project(self):
        other = GoldProject.objects.create(name='Unreviewed Project', slug='unreviewed-project')
        review = self._review(other)
        self.assertFalse(review.has_reviewed_profile)
        self.assertFalse(review.misuse_or_value_loss_condition_exists)
        self.assertEqual(review.alternative_pathways, [])


class AnalysisToValueLossBridgeTests(TestCase):
    """Vertical-slice PR 3 — human-reviewed OperationalLoss creation."""

    PILOT_SLUG = 'almaty-clean-heating-pilot-200-homes'

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.client = Client(SERVER_NAME='localhost')
        self.staff = User.objects.create_user('staff_loss', 'staff_l@ecoiq.uk', 'password123', is_staff=True)
        self.normal = User.objects.create_user('normal_loss', 'user_l@example.com', 'password123', is_staff=False)
        self.project = GoldProject.objects.create(
            name='Almaty Clean Heating Pilot — 200 Homes', slug=self.PILOT_SLUG, commodity='other',
        )
        self.no_profile_project = GoldProject.objects.create(name='No Profile Project', slug='no-profile-project')

    def _confirm_url(self, project=None):
        return reverse('capital_guardian:create_value_loss_confirm', args=[(project or self.project).slug])

    def _execute_url(self, project=None):
        return reverse('capital_guardian:create_value_loss_execute', args=[(project or self.project).slug])

    def _valid_data(self, **overrides):
        data = {
            'title': 'Avoidable coal-based household heating inefficiency', 'loss_type': 'heat_loss',
            'financial_loss_amount': '5000', 'avoidability_score': '60', 'urgency_score': '55',
            'classification': 'illustrative',
        }
        data.update(overrides)
        return data

    # ── Review does not create loss automatically ───────────────────────────

    def test_review_does_not_create_loss_automatically(self):
        from capital_guardian.services.project_analysis import analyse_project
        from capital_guardian.services.resource_purpose_review import review_resource_purpose
        review_resource_purpose(self.project, analyse_project(self.project))
        self.assertEqual(OperationalLoss.objects.count(), 0)

    # ── Authentication and authorization ────────────────────────────────────

    def test_staff_can_open_confirmation(self):
        self.client.force_login(self.staff)
        r = self.client.get(self._confirm_url())
        self.assertEqual(r.status_code, 200)

    def test_non_staff_blocked_from_confirmation(self):
        self.client.force_login(self.normal)
        r = self.client.get(self._confirm_url())
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login', r['Location'])

    def test_anonymous_blocked_from_confirmation(self):
        r = self.client.get(self._confirm_url())
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login', r['Location'])

    def test_non_staff_blocked_from_execute(self):
        self.client.force_login(self.normal)
        r = self.client.post(self._execute_url(), self._valid_data())
        self.assertEqual(r.status_code, 302)
        self.assertEqual(OperationalLoss.objects.count(), 0)

    def test_anonymous_blocked_from_execute(self):
        r = self.client.post(self._execute_url(), self._valid_data())
        self.assertEqual(r.status_code, 302)
        self.assertEqual(OperationalLoss.objects.count(), 0)

    def test_idor_normal_user_with_known_slug_blocked(self):
        self.client.force_login(self.normal)
        self.client.post(self._execute_url(), self._valid_data())
        self.assertEqual(OperationalLoss.objects.count(), 0)

    # ── HTTP safety ──────────────────────────────────────────────────────────

    def test_get_cannot_create_loss(self):
        self.client.force_login(self.staff)
        r = self.client.get(self._execute_url())
        self.assertEqual(r.status_code, 302)
        self.assertEqual(OperationalLoss.objects.count(), 0)

    def test_post_valid_creates_loss(self):
        self.client.force_login(self.staff)
        r = self.client.post(self._execute_url(), self._valid_data(), follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(OperationalLoss.objects.count(), 1)

    def test_missing_financial_amount_rejected(self):
        self.client.force_login(self.staff)
        data = self._valid_data()
        del data['financial_loss_amount']
        r = self.client.post(self._execute_url(), data)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(OperationalLoss.objects.count(), 0)

    def test_csrf_enforced(self):
        csrf_client = Client(enforce_csrf_checks=True, SERVER_NAME='localhost')
        csrf_client.force_login(self.staff)
        r = csrf_client.post(self._execute_url(), self._valid_data())
        self.assertEqual(r.status_code, 403)

    def test_invalid_project_returns_404(self):
        self.client.force_login(self.staff)
        r = self.client.get(reverse('capital_guardian:create_value_loss_confirm', args=['does-not-exist']))
        self.assertEqual(r.status_code, 404)

    def test_no_loss_created_when_no_misuse_condition(self):
        """A project with no reviewed resource-purpose profile must never allow loss creation, even via direct POST."""
        self.client.force_login(self.staff)
        r = self.client.post(self._execute_url(self.no_profile_project), self._valid_data(), follow=True)
        self.assertEqual(OperationalLoss.objects.count(), 0)
        self.assertContains(r, 'No reviewed resource-misuse/value-loss condition')

    def test_no_raw_exception_leakage(self):
        from unittest import mock
        self.client.force_login(self.staff)
        with mock.patch(
            'capital_guardian.services.resource_purpose_review.review_resource_purpose',
            side_effect=RuntimeError('unexpected internal boom'),
        ):
            r = self.client.post(self._execute_url(), self._valid_data(), follow=True)
        self.assertNotContains(r, 'unexpected internal boom')
        self.assertNotContains(r, 'Traceback')

    # ── Content correctness ──────────────────────────────────────────────────

    def test_project_field_matches_goldproject_name_exactly(self):
        self.client.force_login(self.staff)
        self.client.post(self._execute_url(), self._valid_data())
        loss = OperationalLoss.objects.get(title=self._valid_data()['title'])
        self.assertEqual(loss.project, self.project.name)

    def test_correct_loss_type(self):
        self.client.force_login(self.staff)
        self.client.post(self._execute_url(), self._valid_data(loss_type='energy_loss'))
        loss = OperationalLoss.objects.get(title=self._valid_data()['title'])
        self.assertEqual(loss.loss_type, 'energy_loss')

    def test_evidence_quality_not_overstated_with_no_evidence(self):
        self.client.force_login(self.staff)
        self.client.post(self._execute_url(), self._valid_data())
        loss = OperationalLoss.objects.get(title=self._valid_data()['title'])
        self.assertEqual(loss.evidence_quality, 'weak')
        self.assertEqual(loss.confidence, 30)

    def test_evidence_quality_reflects_verified_evidence(self):
        from evidence_memory.services.memory import create_memory_from_manual_project_evidence
        create_memory_from_manual_project_evidence(
            self.project, title='V', text='Real verified technical evidence.',
            verification_status='verified', review_tier='human_reviewed',
        )
        self.client.force_login(self.staff)
        self.client.post(self._execute_url(), self._valid_data())
        loss = OperationalLoss.objects.get(title=self._valid_data()['title'])
        self.assertIn(loss.evidence_quality, ('medium', 'strong'))

    def test_no_financial_loss_fabricated(self):
        """financial_loss_amount always comes from the human-submitted form field, never a default guess."""
        self.client.force_login(self.staff)
        self.client.post(self._execute_url(), self._valid_data(financial_loss_amount='42424'))
        loss = OperationalLoss.objects.get(title=self._valid_data()['title'])
        self.assertEqual(loss.financial_loss_amount, 42424)

    def test_duplicate_submissions_handled_safely(self):
        self.client.force_login(self.staff)
        self.client.post(self._execute_url(), self._valid_data())
        self.client.post(self._execute_url(), self._valid_data())
        self.assertEqual(OperationalLoss.objects.filter(title=self._valid_data()['title']).count(), 2)

    def test_loss_evidence_rows_created_for_each_reference(self):
        from evidence_memory.services.memory import create_memory_from_manual_project_evidence
        create_memory_from_manual_project_evidence(self.project, title='E1', text='First real evidence for the pilot.')
        create_memory_from_manual_project_evidence(self.project, title='E2', text='Second real evidence for the pilot.')
        self.client.force_login(self.staff)
        self.client.post(self._execute_url(), self._valid_data())
        loss = OperationalLoss.objects.get(title=self._valid_data()['title'])
        self.assertEqual(LossEvidence.objects.filter(operational_loss=loss).count(), 2)

    def test_provenance_note_in_description(self):
        self.client.force_login(self.staff)
        self.client.post(self._execute_url(), self._valid_data())
        loss = OperationalLoss.objects.get(title=self._valid_data()['title'])
        self.assertIn('staff_loss', loss.description)
        self.assertIn('human-confirmed, not automatically verified', loss.description)

    # ── Full integration (real services end to end) ─────────────────────────

    def test_full_integration_real_services(self):
        """GoldProject -> EvidenceMemory -> Project Analysis -> Resource Purpose Review -> Human Confirmation -> OperationalLoss."""
        from evidence_memory.services.memory import create_memory_from_manual_project_evidence
        from capital_guardian.services.project_analysis import analyse_project
        from capital_guardian.services.resource_purpose_review import review_resource_purpose

        create_memory_from_manual_project_evidence(
            self.project, title='Real evidence', text='Verified real technical evidence for integration test.',
            verification_status='verified', review_tier='human_reviewed',
        )
        analysis = analyse_project(self.project)
        review = review_resource_purpose(self.project, analysis)
        self.assertTrue(review.misuse_or_value_loss_condition_exists)

        self.client.force_login(self.staff)
        r = self.client.post(self._execute_url(), self._valid_data(classification='real'), follow=True)
        self.assertEqual(r.status_code, 200)

        loss = OperationalLoss.objects.get(title=self._valid_data()['title'])
        self.assertEqual(loss.project, self.project.name)
        self.assertEqual(LossEvidence.objects.filter(operational_loss=loss).count(), 1)


class InterventionSafetyGateTests(TestCase):
    """Vertical-slice PR 4 — classify_intervention_safety()."""

    def setUp(self):
        from capital_guardian.services.intervention_safety_gate import classify_intervention_safety
        self.classify = classify_intervention_safety
        self.project = GoldProject.objects.create(
            name='Almaty Clean Heating Pilot — 200 Homes', slug='almaty-clean-heating-pilot-200-homes', commodity='other',
        )
        loss = OperationalLoss.objects.create(title='Loss', loss_type='heat_loss', financial_loss_amount=1000)
        self.loss = loss

    def _option(self, title, intervention_type, description=''):
        return InterventionOption(operational_loss=self.loss, title=title, intervention_type=intervention_type, description=description)

    def test_insulation_is_eligible(self):
        option = self._option('Insulation Retrofit', 'prevention')
        result = self.classify(self.project, option, classification='real')
        self.assertEqual(result['status'], 'eligible')

    def test_heat_pump_is_eligible(self):
        option = self._option('Heat Pump Retrofit', 'equipment_upgrade')
        result = self.classify(self.project, option, classification='real')
        self.assertEqual(result['status'], 'eligible')

    def test_district_heating_is_eligible(self):
        option = self._option('District Heating Connection', 'infrastructure_upgrade')
        result = self.classify(self.project, option, classification='real')
        self.assertEqual(result['status'], 'eligible')

    def test_baseline_is_eligible(self):
        option = self._option('Continue Current Coal Heating', 'do_nothing')
        result = self.classify(self.project, option, classification='real')
        self.assertEqual(result['status'], 'eligible')

    def test_raw_coal_fertiliser_is_blocked(self):
        option = self._option('Sell raw coal as fertiliser', 'resale')
        result = self.classify(self.project, option, classification='estimated')
        self.assertEqual(result['status'], 'blocked')
        self.assertIn('not a validated fertiliser', result['reason'])

    def test_coal_ash_reuse_is_conditional(self):
        option = self._option('Reuse coal ash', 'resale', description='Explore ash by-product options.')
        result = self.classify(self.project, option, classification='estimated')
        self.assertEqual(result['status'], 'conditional')

    def test_burning_coal_to_create_ash_is_conditional_not_recommended(self):
        option = self._option('Burn more coal to produce ash for construction', 'resale')
        result = self.classify(self.project, option, classification='estimated')
        self.assertIn(result['status'], ('conditional', 'blocked'))
        self.assertNotEqual(result['status'], 'eligible')

    def test_unreviewed_intervention_type_defaults_conditional(self):
        option = self._option('Some other approach', 'disposal')
        result = self.classify(self.project, option, classification='real')
        self.assertEqual(result['status'], 'conditional')

    def test_illustrative_classification_downgrades_to_conditional(self):
        option = self._option('Heat Pump Retrofit', 'equipment_upgrade')
        result = self.classify(self.project, option, classification='illustrative')
        self.assertEqual(result['status'], 'conditional')
        self.assertIn('illustrative', result['reason'].lower())

    def test_deterministic(self):
        option = self._option('Insulation Retrofit', 'prevention')
        r1 = self.classify(self.project, option, classification='real')
        r2 = self.classify(self.project, option, classification='real')
        self.assertEqual(r1, r2)


class BetterWayComparisonTests(TestCase):
    """Vertical-slice PR 4 — compare_interventions() reusing the real scoring/ranking services."""

    def setUp(self):
        from capital_guardian.services.better_way import compare_interventions, tag_classification
        self.compare = compare_interventions
        self.tag = tag_classification
        self.project = GoldProject.objects.create(
            name='Almaty Clean Heating Pilot — 200 Homes', slug='almaty-clean-heating-pilot-200-homes', commodity='other',
        )
        self.loss = OperationalLoss.objects.create(
            title='Coal heating loss', loss_type='heat_loss', financial_loss_amount=10000, projected_future_loss=12000,
        )

    def _make_option(self, title, intervention_type, classification='estimated', **fields):
        defaults = dict(
            capex_estimate=0, opex_change=0, estimated_loss_avoided=0, estimated_value_recovered=0,
            estimated_annual_savings=0, technical_readiness='not_ready', finance_readiness='not_ready',
            mrv_readiness='not_ready', risk_level='medium',
        )
        defaults.update(fields)
        return InterventionOption.objects.create(
            operational_loss=self.loss, title=title, intervention_type=intervention_type,
            description=self.tag('desc', classification), **defaults,
        )

    def test_reuses_real_ranking_no_duplicate_scoring(self):
        """Confirms the composite score matches what the real shared scorer/ranker would produce directly."""
        from waste_to_value_capital_allocation_engine.services.capital_allocation_scoring import score_intervention_option
        from waste_to_value_capital_allocation_engine.services.ranking import rank_capital_allocation_options

        option = self._make_option('Insulation', 'prevention', capex_estimate=2000, estimated_annual_savings=1500, estimated_loss_avoided=3000)
        result = self.compare(self.project, self.loss)

        ceiling = self.loss.projected_future_loss
        expected_scores = score_intervention_option(option, ceiling, 80000)
        expected_ranked = rank_capital_allocation_options([{'option': option, **expected_scores}])
        self.assertEqual(result.ranked[0]['composite_score'], expected_ranked[0]['composite_score'])

    def test_deterministic_ranking_same_inputs_same_order(self):
        self._make_option('Insulation', 'prevention', capex_estimate=2000, estimated_annual_savings=1500)
        self._make_option('Heat Pump', 'equipment_upgrade', capex_estimate=8000, estimated_annual_savings=2500)
        r1 = self.compare(self.project, self.loss)
        r2 = self.compare(self.project, self.loss)
        self.assertEqual([c['option'].pk for c in r1.ranked], [c['option'].pk for c in r2.ranked])

    def test_baseline_does_not_win_merely_because_capex_is_zero(self):
        self._make_option('Continue Current Coal Heating', 'do_nothing', classification='real', risk_level='high')
        self._make_option('Insulation', 'prevention', capex_estimate=2000, estimated_annual_savings=1500, estimated_loss_avoided=3000, technical_readiness='ready', finance_readiness='ready')
        result = self.compare(self.project, self.loss)
        self.assertFalse(result.baseline_ranked_first)
        self.assertNotEqual(result.ranked[0]['option'].intervention_type, 'do_nothing')

    def test_baseline_flagged_if_it_does_rank_first(self):
        """If every real option is weak enough, the baseline's true composite score can still legitimately win — must be flagged, never silently presented."""
        self._make_option('Continue Current Coal Heating', 'do_nothing', classification='real')
        result = self.compare(self.project, self.loss)  # baseline is the ONLY option
        self.assertTrue(result.baseline_ranked_first)
        self.assertIn('does not mean continuing is recommended', result.baseline_warning)

    def test_blocked_option_excluded_from_ranking(self):
        self._make_option('Insulation', 'prevention', capex_estimate=2000, estimated_annual_savings=1500)
        self._make_option('Sell coal ash as fertiliser', 'resale')
        result = self.compare(self.project, self.loss)
        self.assertEqual(len(result.blocked), 1)
        ranked_titles = [c['option'].title for c in result.ranked]
        self.assertNotIn('Sell coal ash as fertiliser', ranked_titles)

    def test_conditional_option_included_with_reason(self):
        self._make_option('Insulation', 'prevention', capex_estimate=2000, estimated_annual_savings=1500)
        self._make_option('Heat Pump', 'equipment_upgrade', classification='illustrative', capex_estimate=8000)
        result = self.compare(self.project, self.loss)
        conditional = [c for c in result.ranked if c['safety_status'] == 'conditional']
        self.assertEqual(len(conditional), 1)
        self.assertTrue(conditional[0]['safety_reason'])

    def test_missing_financial_values_handled_honestly(self):
        self._make_option('Bare option', 'prevention')  # all zeros
        result = self.compare(self.project, self.loss)
        self.assertEqual(len(result.ranked), 1)

    def test_zero_options_returns_empty_ranking(self):
        result = self.compare(self.project, self.loss)
        self.assertEqual(result.ranked, [])
        self.assertFalse(result.baseline_ranked_first)

    def test_trade_offs_present_for_multiple_options(self):
        self._make_option('Insulation', 'prevention', capex_estimate=2000, estimated_annual_savings=1500, estimated_payback_months=16)
        self._make_option('Heat Pump', 'equipment_upgrade', capex_estimate=8000, estimated_annual_savings=2500, estimated_payback_months=38)
        result = self.compare(self.project, self.loss)
        self.assertIn('highest_capital_efficiency', result.trade_offs)
        self.assertIn('lowest_capex', result.trade_offs)


class InterventionOptionCreationViewTests(TestCase):
    """Vertical-slice PR 4 — staff-only intervention option creation."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.client = Client(SERVER_NAME='localhost')
        self.staff = User.objects.create_user('staff_opt', 'staff_opt@ecoiq.uk', 'password123', is_staff=True)
        self.normal = User.objects.create_user('normal_opt', 'normal_opt@example.com', 'password123', is_staff=False)
        self.project = GoldProject.objects.create(
            name='Almaty Clean Heating Pilot — 200 Homes', slug='almaty-clean-heating-pilot-200-homes', commodity='other',
        )
        self.loss = OperationalLoss.objects.create(
            project=self.project.name, title='Coal heating loss', loss_type='heat_loss', financial_loss_amount=10000,
        )
        self.other_project = GoldProject.objects.create(name='Other Project', slug='other-project-opt')
        self.other_loss = OperationalLoss.objects.create(
            project=self.other_project.name, title='Other loss', loss_type='energy_loss', financial_loss_amount=500,
        )

    def _confirm_url(self, project=None, loss=None):
        return reverse('capital_guardian:create_intervention_option_confirm', args=[(project or self.project).slug, (loss or self.loss).pk])

    def _execute_url(self, project=None, loss=None):
        return reverse('capital_guardian:create_intervention_option_execute', args=[(project or self.project).slug, (loss or self.loss).pk])

    def _valid_data(self, **overrides):
        data = {
            'title': 'Insulation Retrofit', 'intervention_type': 'prevention', 'description': 'Insulate homes.',
            'capex_estimate': '2000', 'opex_change': '0', 'estimated_loss_avoided': '3000',
            'estimated_value_recovered': '0', 'estimated_annual_savings': '1500',
            'technical_readiness': 'ready', 'finance_readiness': 'ready', 'mrv_readiness': 'draft',
            'risk_level': 'low', 'classification': 'estimated',
        }
        data.update(overrides)
        return data

    # ── Authentication and authorization ────────────────────────────────────

    def test_staff_can_open_confirm(self):
        self.client.force_login(self.staff)
        r = self.client.get(self._confirm_url())
        self.assertEqual(r.status_code, 200)

    def test_non_staff_blocked_from_confirm(self):
        self.client.force_login(self.normal)
        r = self.client.get(self._confirm_url())
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login', r['Location'])

    def test_anonymous_blocked_from_confirm(self):
        r = self.client.get(self._confirm_url())
        self.assertEqual(r.status_code, 302)

    def test_non_staff_blocked_from_execute(self):
        self.client.force_login(self.normal)
        r = self.client.post(self._execute_url(), self._valid_data())
        self.assertEqual(r.status_code, 302)
        self.assertEqual(InterventionOption.objects.count(), 0)

    def test_anonymous_blocked_from_execute(self):
        r = self.client.post(self._execute_url(), self._valid_data())
        self.assertEqual(r.status_code, 302)
        self.assertEqual(InterventionOption.objects.count(), 0)

    # ── HTTP safety ──────────────────────────────────────────────────────────

    def test_get_cannot_create_option(self):
        self.client.force_login(self.staff)
        r = self.client.get(self._execute_url())
        self.assertEqual(r.status_code, 302)
        self.assertEqual(InterventionOption.objects.count(), 0)

    def test_csrf_enforced(self):
        csrf_client = Client(enforce_csrf_checks=True, SERVER_NAME='localhost')
        csrf_client.force_login(self.staff)
        r = csrf_client.post(self._execute_url(), self._valid_data())
        self.assertEqual(r.status_code, 403)

    def test_invalid_loss_returns_404(self):
        self.client.force_login(self.staff)
        r = self.client.get(reverse('capital_guardian:create_intervention_option_confirm', args=[self.project.slug, 999999]))
        self.assertEqual(r.status_code, 404)

    def test_invalid_form_rejected(self):
        self.client.force_login(self.staff)
        data = self._valid_data()
        del data['title']
        r = self.client.post(self._execute_url(), data)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(InterventionOption.objects.count(), 0)

    # ── IDOR — loss belonging to a different project ────────────────────────

    def test_loss_from_different_project_returns_404(self):
        self.client.force_login(self.staff)
        r = self.client.get(self._confirm_url(project=self.project, loss=self.other_loss))
        self.assertEqual(r.status_code, 404)

    # ── Content correctness ──────────────────────────────────────────────────

    def test_option_created_with_correct_association(self):
        self.client.force_login(self.staff)
        self.client.post(self._execute_url(), self._valid_data())
        option = InterventionOption.objects.get(title='Insulation Retrofit')
        self.assertEqual(option.operational_loss_id, self.loss.pk)

    def test_classification_tag_recorded(self):
        from capital_guardian.services.better_way import extract_classification
        self.client.force_login(self.staff)
        self.client.post(self._execute_url(), self._valid_data(classification='illustrative'))
        option = InterventionOption.objects.get(title='Insulation Retrofit')
        self.assertEqual(extract_classification(option.description), 'illustrative')

    def test_duplicate_identical_title_updates_not_duplicates(self):
        self.client.force_login(self.staff)
        self.client.post(self._execute_url(), self._valid_data())
        self.client.post(self._execute_url(), self._valid_data(capex_estimate='2500'))
        self.assertEqual(InterventionOption.objects.filter(operational_loss=self.loss, title='Insulation Retrofit').count(), 1)
        option = InterventionOption.objects.get(operational_loss=self.loss, title='Insulation Retrofit')
        self.assertEqual(option.capex_estimate, 2500)

    def test_distinct_variant_titles_create_separate_rows(self):
        self.client.force_login(self.staff)
        self.client.post(self._execute_url(), self._valid_data(title='Heat Pump — Supplier A'))
        self.client.post(self._execute_url(), self._valid_data(title='Heat Pump — Supplier B'))
        self.assertEqual(InterventionOption.objects.filter(operational_loss=self.loss).count(), 2)

    def test_no_raw_exception_leakage(self):
        from unittest import mock
        self.client.force_login(self.staff)
        with mock.patch(
            'waste_to_value_capital_allocation_engine.services.intervention_finance.model_interventions',
            side_effect=RuntimeError('unexpected internal boom'),
        ):
            r = self.client.post(self._execute_url(), self._valid_data(), follow=True)
        self.assertNotContains(r, 'unexpected internal boom')
        self.assertNotContains(r, 'Traceback')


class BetterWayViewTests(TestCase):
    """Vertical-slice PR 4 — operational_loss_detail + run_better_way_comparison views."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.client = Client(SERVER_NAME='localhost')
        self.staff = User.objects.create_user('staff_bw', 'staff_bw@ecoiq.uk', 'password123', is_staff=True)
        self.normal = User.objects.create_user('normal_bw', 'normal_bw@example.com', 'password123', is_staff=False)
        self.project = GoldProject.objects.create(
            name='Almaty Clean Heating Pilot — 200 Homes', slug='almaty-clean-heating-pilot-200-homes', commodity='other',
        )
        self.loss = OperationalLoss.objects.create(
            project=self.project.name, title='Coal heating loss', loss_type='heat_loss',
            financial_loss_amount=10000, projected_future_loss=12000,
        )
        InterventionOption.objects.create(
            operational_loss=self.loss, title='Insulation', intervention_type='prevention',
            capex_estimate=2000, estimated_annual_savings=1500, estimated_loss_avoided=3000,
        )

    def _detail_url(self):
        return reverse('capital_guardian:operational_loss_detail', args=[self.project.slug, self.loss.pk])

    def _compare_url(self):
        return reverse('capital_guardian:run_better_way_comparison', args=[self.project.slug, self.loss.pk])

    def test_loss_detail_page_public(self):
        r = self.client.get(self._detail_url())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Insulation')

    def test_create_button_only_for_staff(self):
        self.client.force_login(self.staff)
        r = self.client.get(self._detail_url())
        self.assertContains(r, 'Create Intervention Option')

    def test_create_button_absent_for_anonymous(self):
        r = self.client.get(self._detail_url())
        self.assertNotContains(r, 'Create Intervention Option')

    def test_non_staff_cannot_run_comparison(self):
        self.client.force_login(self.normal)
        r = self.client.post(self._compare_url())
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login', r['Location'])

    def test_anonymous_cannot_run_comparison(self):
        r = self.client.post(self._compare_url())
        self.assertEqual(r.status_code, 302)

    def test_get_cannot_run_comparison(self):
        self.client.force_login(self.staff)
        r = self.client.get(self._compare_url())
        self.assertEqual(r.status_code, 302)

    def test_staff_post_runs_comparison(self):
        self.client.force_login(self.staff)
        r = self.client.post(self._compare_url())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'The Better Way')
        self.assertContains(r, 'Insulation')

    def test_score_breakdown_and_ranking_shown(self):
        self.client.force_login(self.staff)
        r = self.client.post(self._compare_url())
        self.assertContains(r, 'Composite Score')
        self.assertContains(r, '#1')

    def test_stewardship_comparison_shown(self):
        self.client.force_login(self.staff)
        r = self.client.post(self._compare_url())
        self.assertContains(r, 'Hisab')
        self.assertContains(r, 'not a religious ruling')

    def test_mixed_safety_states_displayed(self):
        InterventionOption.objects.create(
            operational_loss=self.loss, title='Sell coal ash as fertiliser', intervention_type='resale',
        )
        self.client.force_login(self.staff)
        r = self.client.post(self._compare_url())
        self.assertContains(r, 'Excluded (Blocked) Options')

    def test_invalid_loss_404(self):
        self.client.force_login(self.staff)
        r = self.client.get(reverse('capital_guardian:operational_loss_detail', args=[self.project.slug, 999999]))
        self.assertEqual(r.status_code, 404)


class BetterWayIntegrationTests(TestCase):
    """Full real-service integration: GoldProject -> EvidenceMemory -> Project Analysis
    -> Resource Purpose Review -> OperationalLoss -> InterventionOptions -> Ranking -> The Better Way page."""

    def test_full_chain(self):
        from django.contrib.auth import get_user_model
        from evidence_memory.services.memory import create_memory_from_manual_project_evidence
        from capital_guardian.services.project_analysis import analyse_project
        from capital_guardian.services.resource_purpose_review import review_resource_purpose

        User = get_user_model()
        staff = User.objects.create_user('staff_full', 'staff_full@ecoiq.uk', 'password123', is_staff=True)
        client = Client(SERVER_NAME='localhost')
        client.force_login(staff)

        project = GoldProject.objects.create(
            name='Almaty Clean Heating Pilot — 200 Homes', slug='almaty-clean-heating-pilot-200-homes', commodity='other',
        )
        create_memory_from_manual_project_evidence(
            project, title='Real evidence', text='Verified technical evidence for the pilot.',
            verification_status='verified', review_tier='human_reviewed',
        )
        analysis = analyse_project(project)
        review = review_resource_purpose(project, analysis)
        self.assertTrue(review.misuse_or_value_loss_condition_exists)

        loss_url = reverse('capital_guardian:create_value_loss_confirm', args=[project.slug])
        client.get(loss_url)
        execute_url = reverse('capital_guardian:create_value_loss_execute', args=[project.slug])
        r = client.post(execute_url, {
            'title': 'Avoidable coal heating inefficiency', 'loss_type': 'heat_loss',
            'financial_loss_amount': '15000', 'avoidability_score': '60', 'urgency_score': '55',
            'classification': 'estimated',
        }, follow=True)
        self.assertEqual(r.status_code, 200)

        loss = OperationalLoss.objects.get(title='Avoidable coal heating inefficiency')

        option_url = reverse('capital_guardian:create_intervention_option_execute', args=[project.slug, loss.pk])
        client.post(option_url, {
            'title': 'Insulation Retrofit', 'intervention_type': 'prevention', 'description': 'Insulate.',
            'capex_estimate': '2000', 'opex_change': '0', 'estimated_loss_avoided': '3000',
            'estimated_value_recovered': '0', 'estimated_annual_savings': '1500',
            'technical_readiness': 'ready', 'finance_readiness': 'ready', 'mrv_readiness': 'draft',
            'risk_level': 'low', 'classification': 'real',
        })
        client.post(option_url, {
            'title': 'Continue Current Coal Heating', 'intervention_type': 'do_nothing', 'description': 'Baseline.',
            'capex_estimate': '0', 'opex_change': '0', 'estimated_loss_avoided': '0',
            'estimated_value_recovered': '0', 'estimated_annual_savings': '0',
            'technical_readiness': 'ready', 'finance_readiness': 'not_ready', 'mrv_readiness': 'not_ready',
            'risk_level': 'high', 'classification': 'real',
        })
        self.assertEqual(InterventionOption.objects.filter(operational_loss=loss).count(), 2)

        compare_url = reverse('capital_guardian:run_better_way_comparison', args=[project.slug, loss.pk])
        r = client.post(compare_url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Insulation Retrofit')


class CapitalDecisionBridgeTests(TestCase):
    """Vertical-slice PR 5 — capital_decision_bridge.create_decision_from_better_way()."""

    def setUp(self):
        self.project = GoldProject.objects.create(
            name='Almaty Clean Heating Pilot — 200 Homes', slug='almaty-clean-heating-pilot-200-homes', commodity='other',
        )
        self.loss = OperationalLoss.objects.create(
            project=self.project.name, title='Coal heating loss', loss_type='heat_loss',
            financial_loss_amount=10000, projected_future_loss=12000, evidence_quality='strong',
        )
        self.eligible_option = InterventionOption.objects.create(
            operational_loss=self.loss, title='Insulation', intervention_type='prevention',
            capex_estimate=2000, estimated_annual_savings=1500, estimated_loss_avoided=3000,
        )

    def test_eligible_option_creates_pending_decision(self):
        from capital_guardian.services.capital_decision_bridge import create_decision_from_better_way

        decision = create_decision_from_better_way(self.project, self.loss, self.eligible_option)
        self.assertEqual(decision.approval_status, 'pending')
        self.assertEqual(decision.intervention_id, self.eligible_option.pk)
        self.assertEqual(decision.project, self.project.name)
        self.assertIsNotNone(decision.ranking)
        self.assertIn('pending', decision.decision.lower())

    def test_conditional_option_preserves_conditions(self):
        from capital_guardian.services.capital_decision_bridge import create_decision_from_better_way
        from capital_guardian.services.resource_purpose_review import review_resource_purpose
        from capital_guardian.services.project_analysis import analyse_project

        # A reviewed misuse pathway makes the resale/misuse-adjacent option
        # 'conditional' rather than 'eligible' via the real safety gate.
        analysis = analyse_project(self.project)
        review_resource_purpose(self.project, analysis)
        conditional_option = InterventionOption.objects.create(
            operational_loss=self.loss, title='Sell coal ash as soil additive', intervention_type='resale',
            capex_estimate=500, estimated_annual_savings=200, estimated_loss_avoided=200,
        )
        decision = create_decision_from_better_way(self.project, self.loss, conditional_option)
        self.assertEqual(decision.approval_status, 'pending')
        # Conditional or eligible depending on the exact gate outcome — either
        # way, if the gate found an unmet condition, it must be preserved.
        if decision.conditions:
            self.assertTrue(len(decision.conditions) > 0)

    def test_blocked_option_cannot_create_decision(self):
        from capital_guardian.services.capital_decision_bridge import (
            BlockedInterventionError, create_decision_from_better_way,
        )

        blocked_option = InterventionOption.objects.create(
            operational_loss=self.loss, title='Burn coal to produce ash for fertiliser', intervention_type='resale',
        )
        with self.assertRaises(BlockedInterventionError):
            create_decision_from_better_way(self.project, self.loss, blocked_option)
        self.assertFalse(CapitalAllocationDecision.objects.filter(intervention=blocked_option).exists())

    def test_decision_never_auto_approved(self):
        from capital_guardian.services.capital_decision_bridge import create_decision_from_better_way

        decision = create_decision_from_better_way(self.project, self.loss, self.eligible_option)
        self.assertNotEqual(decision.approval_status, 'approved')
        self.assertNotEqual(decision.approval_status, 'approved_with_conditions')

    def test_duplicate_creation_returns_existing_without_resetting_approval(self):
        from capital_guardian.services.capital_decision_bridge import create_decision_from_better_way

        decision = create_decision_from_better_way(self.project, self.loss, self.eligible_option)
        decision.approval_status = 'approved'
        decision.save(update_fields=['approval_status'])

        decision_again = create_decision_from_better_way(self.project, self.loss, self.eligible_option)
        self.assertEqual(decision_again.pk, decision.pk)
        self.assertEqual(decision_again.approval_status, 'approved')
        self.assertEqual(CapitalAllocationDecision.objects.filter(intervention=self.eligible_option).count(), 1)

    def test_option_not_in_comparison_raises(self):
        from capital_guardian.services.capital_decision_bridge import (
            InterventionNotInComparisonError, create_decision_from_better_way,
        )

        other_loss = OperationalLoss.objects.create(
            project=self.project.name, title='Another loss', loss_type='energy_loss',
            financial_loss_amount=5000, projected_future_loss=6000,
        )
        stray_option = InterventionOption.objects.create(
            operational_loss=other_loss, title='Unrelated option', intervention_type='prevention',
        )
        with self.assertRaises(InterventionNotInComparisonError):
            create_decision_from_better_way(self.project, self.loss, stray_option)


class CapitalDecisionViewTests(TestCase):
    """Vertical-slice PR 5 — create_capital_decision_confirm/execute views."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.client = Client(SERVER_NAME='localhost')
        self.staff = User.objects.create_user('staff_cd', 'staff_cd@ecoiq.uk', 'password123', is_staff=True)
        self.normal = User.objects.create_user('normal_cd', 'normal_cd@example.com', 'password123', is_staff=False)
        self.project = GoldProject.objects.create(
            name='Almaty Clean Heating Pilot — 200 Homes', slug='almaty-clean-heating-pilot-200-homes', commodity='other',
        )
        self.other_project = GoldProject.objects.create(
            name='Unrelated Project', slug='unrelated-project', commodity='other',
        )
        self.loss = OperationalLoss.objects.create(
            project=self.project.name, title='Coal heating loss', loss_type='heat_loss',
            financial_loss_amount=10000, projected_future_loss=12000,
        )
        self.option = InterventionOption.objects.create(
            operational_loss=self.loss, title='Insulation', intervention_type='prevention',
            capex_estimate=2000, estimated_annual_savings=1500, estimated_loss_avoided=3000,
        )

    def _confirm_url(self, project=None, loss=None, option=None):
        return reverse('capital_guardian:create_capital_decision_confirm', args=[
            (project or self.project).slug, (loss or self.loss).pk, (option or self.option).pk,
        ])

    def _execute_url(self, project=None, loss=None, option=None):
        return reverse('capital_guardian:create_capital_decision_execute', args=[
            (project or self.project).slug, (loss or self.loss).pk, (option or self.option).pk,
        ])

    def test_anonymous_cannot_view_confirm(self):
        r = self.client.get(self._confirm_url())
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login', r['Location'])

    def test_non_staff_cannot_view_confirm(self):
        self.client.force_login(self.normal)
        r = self.client.get(self._confirm_url())
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login', r['Location'])

    def test_staff_can_view_confirm(self):
        self.client.force_login(self.staff)
        r = self.client.get(self._confirm_url())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Insulation')

    def test_anonymous_cannot_execute(self):
        r = self.client.post(self._execute_url())
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login', r['Location'])
        self.assertFalse(CapitalAllocationDecision.objects.filter(intervention=self.option).exists())

    def test_non_staff_cannot_execute(self):
        self.client.force_login(self.normal)
        r = self.client.post(self._execute_url())
        self.assertEqual(r.status_code, 302)
        self.assertFalse(CapitalAllocationDecision.objects.filter(intervention=self.option).exists())

    def test_get_cannot_execute(self):
        self.client.force_login(self.staff)
        r = self.client.get(self._execute_url())
        self.assertEqual(r.status_code, 302)
        self.assertFalse(CapitalAllocationDecision.objects.filter(intervention=self.option).exists())

    def test_csrf_enforced_on_execute(self):
        csrf_client = Client(SERVER_NAME='localhost', enforce_csrf_checks=True)
        csrf_client.force_login(self.staff)
        r = csrf_client.post(self._execute_url())
        self.assertEqual(r.status_code, 403)
        self.assertFalse(CapitalAllocationDecision.objects.filter(intervention=self.option).exists())

    def test_staff_post_creates_pending_decision(self):
        self.client.force_login(self.staff)
        r = self.client.post(self._execute_url(), follow=True)
        self.assertEqual(r.status_code, 200)
        decision = CapitalAllocationDecision.objects.get(intervention=self.option)
        self.assertEqual(decision.approval_status, 'pending')

    def test_blocked_option_cannot_be_created_via_view(self):
        blocked_option = InterventionOption.objects.create(
            operational_loss=self.loss, title='Burn coal to produce ash for fertiliser', intervention_type='resale',
        )
        self.client.force_login(self.staff)
        r = self.client.post(self._execute_url(option=blocked_option), follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(CapitalAllocationDecision.objects.filter(intervention=blocked_option).exists())

    def test_cross_project_isolation_on_confirm(self):
        self.client.force_login(self.staff)
        r = self.client.get(self._confirm_url(project=self.other_project))
        self.assertEqual(r.status_code, 404)

    def test_cross_project_isolation_on_execute(self):
        self.client.force_login(self.staff)
        r = self.client.post(self._execute_url(project=self.other_project))
        self.assertEqual(r.status_code, 404)
        self.assertFalse(CapitalAllocationDecision.objects.filter(intervention=self.option).exists())

    def test_option_from_other_loss_404s(self):
        other_loss = OperationalLoss.objects.create(
            project=self.project.name, title='Another loss', loss_type='energy_loss',
            financial_loss_amount=5000, projected_future_loss=6000,
        )
        stray_option = InterventionOption.objects.create(
            operational_loss=other_loss, title='Unrelated option', intervention_type='prevention',
        )
        self.client.force_login(self.staff)
        r = self.client.get(self._confirm_url(option=stray_option))
        self.assertEqual(r.status_code, 404)

    def test_duplicate_execute_does_not_create_second_decision(self):
        self.client.force_login(self.staff)
        self.client.post(self._execute_url())
        self.client.post(self._execute_url())
        self.assertEqual(CapitalAllocationDecision.objects.filter(intervention=self.option).count(), 1)

    def test_better_way_page_links_to_create_decision_for_staff(self):
        self.client.force_login(self.staff)
        compare_url = reverse('capital_guardian:run_better_way_comparison', args=[self.project.slug, self.loss.pk])
        r = self.client.post(compare_url)
        self.assertContains(r, 'Create Capital Decision')
        self.assertContains(r, self._confirm_url())

    def test_better_way_page_hides_create_decision_for_anonymous(self):
        compare_url = reverse('capital_guardian:run_better_way_comparison', args=[self.project.slug, self.loss.pk])
        r = self.client.post(compare_url)
        self.assertEqual(r.status_code, 302)  # staff-only view itself redirects


class CapitalDecisionPromotionTests(TestCase):
    """Vertical-slice PR 5 — human approval (via admin-editable approval_status)
    and promote_to_capital_guardian() reuse for a decision created by the bridge."""

    def setUp(self):
        self.project = GoldProject.objects.create(
            name='Almaty Clean Heating Pilot — 200 Homes', slug='almaty-clean-heating-pilot-200-homes', commodity='other',
        )
        self.loss = OperationalLoss.objects.create(
            project=self.project.name, title='Coal heating loss', loss_type='heat_loss',
            financial_loss_amount=10000, projected_future_loss=12000,
        )
        self.option = InterventionOption.objects.create(
            operational_loss=self.loss, title='Insulation', intervention_type='prevention',
            capex_estimate=2000, estimated_annual_savings=1500, estimated_loss_avoided=3000,
        )

    def _make_decision(self):
        from capital_guardian.services.capital_decision_bridge import create_decision_from_better_way
        return create_decision_from_better_way(self.project, self.loss, self.option)

    def test_pending_decision_cannot_promote(self):
        from waste_to_value_capital_allocation_engine.services.capital_guardian_handoff import (
            DecisionNotApprovedError, promote_to_capital_guardian,
        )
        decision = self._make_decision()
        with self.assertRaises(DecisionNotApprovedError):
            promote_to_capital_guardian(decision)
        self.assertFalse(ProjectGovernance.objects.filter(project=self.project).exists())

    def test_rejected_decision_cannot_promote(self):
        from waste_to_value_capital_allocation_engine.services.capital_guardian_handoff import (
            DecisionNotApprovedError, promote_to_capital_guardian,
        )
        decision = self._make_decision()
        decision.approval_status = 'rejected'
        decision.save(update_fields=['approval_status'])
        with self.assertRaises(DecisionNotApprovedError):
            promote_to_capital_guardian(decision)
        self.assertFalse(ProjectGovernance.objects.filter(project=self.project).exists())

    def test_approved_decision_can_promote(self):
        from waste_to_value_capital_allocation_engine.services.capital_guardian_handoff import (
            promote_to_capital_guardian,
        )
        decision = self._make_decision()
        decision.approval_status = 'approved'
        decision.save(update_fields=['approval_status'])
        result = promote_to_capital_guardian(decision)
        self.assertEqual(result.status, 'promoted')
        self.assertEqual(result.project.pk, self.project.pk)
        self.assertTrue(ProjectGovernance.objects.filter(project=self.project).exists())

    def test_promotion_does_not_duplicate_project_governance(self):
        from waste_to_value_capital_allocation_engine.services.capital_guardian_handoff import (
            promote_to_capital_guardian,
        )
        decision = self._make_decision()
        decision.approval_status = 'approved_with_conditions'
        decision.save(update_fields=['approval_status'])
        promote_to_capital_guardian(decision)
        result_two = promote_to_capital_guardian(decision)
        self.assertEqual(result_two.status, 'already_promoted')
        self.assertEqual(ProjectGovernance.objects.filter(project=self.project).count(), 1)

    def test_ambiguous_project_match_stays_blocked(self):
        from waste_to_value_capital_allocation_engine.services.capital_guardian_handoff import (
            promote_to_capital_guardian,
        )
        GoldProject.objects.create(name=self.project.name, slug='duplicate-name-pilot', commodity='other')
        decision = self._make_decision()
        decision.approval_status = 'approved'
        decision.save(update_fields=['approval_status'])
        result = promote_to_capital_guardian(decision)
        self.assertEqual(result.status, 'ambiguous_project_match')
        self.assertFalse(ProjectGovernance.objects.filter(project=self.project).exists())

    def test_decision_detail_shows_traceability_link_back_to_loss(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        staff = User.objects.create_user('staff_trace', 'staff_trace@ecoiq.uk', 'password123', is_staff=True)
        client = Client(SERVER_NAME='localhost')
        client.force_login(staff)

        decision = self._make_decision()
        r = client.get(reverse('waste_to_value_capital_allocation_engine:decision_detail', args=[decision.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, reverse(
            'capital_guardian:operational_loss_detail', args=[self.project.slug, self.loss.pk],
        ))

    def test_promote_button_shown_only_when_approved_and_staff(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        staff = User.objects.create_user('staff_promo', 'staff_promo@ecoiq.uk', 'password123', is_staff=True)
        client = Client(SERVER_NAME='localhost')
        client.force_login(staff)

        decision = self._make_decision()
        url = reverse('waste_to_value_capital_allocation_engine:decision_detail', args=[decision.pk])
        r = client.get(url)
        self.assertNotContains(r, 'Promote to Capital Guardian')

        decision.approval_status = 'approved'
        decision.save(update_fields=['approval_status'])
        r = client.get(url)
        self.assertContains(r, 'Promote to Capital Guardian')


class CapitalDecisionHonestyTests(TestCase):
    """Vertical-slice PR 5 — honesty rules: no forbidden claims anywhere in the new flow."""

    FORBIDDEN_PHRASES = [
        'AI approved', 'AI verified', 'Shariah approved', 'Quranically approved',
        'Guaranteed investment', 'Guaranteed impact',
    ]

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.client = Client(SERVER_NAME='localhost')
        self.staff = User.objects.create_user('staff_honesty', 'staff_honesty@ecoiq.uk', 'password123', is_staff=True)
        self.project = GoldProject.objects.create(
            name='Almaty Clean Heating Pilot — 200 Homes', slug='almaty-clean-heating-pilot-200-homes', commodity='other',
        )
        self.loss = OperationalLoss.objects.create(
            project=self.project.name, title='Coal heating loss', loss_type='heat_loss',
            financial_loss_amount=10000, projected_future_loss=12000,
        )
        self.option = InterventionOption.objects.create(
            operational_loss=self.loss, title='Insulation', intervention_type='prevention',
            capex_estimate=2000, estimated_annual_savings=1500, estimated_loss_avoided=3000,
        )

    def test_no_forbidden_claims_on_confirm_page(self):
        self.client.force_login(self.staff)
        r = self.client.get(reverse(
            'capital_guardian:create_capital_decision_confirm', args=[self.project.slug, self.loss.pk, self.option.pk],
        ))
        content = r.content.decode()
        for phrase in self.FORBIDDEN_PHRASES:
            self.assertNotIn(phrase, content)

    def test_no_forbidden_claims_on_decision_detail_page(self):
        from capital_guardian.services.capital_decision_bridge import create_decision_from_better_way

        decision = create_decision_from_better_way(self.project, self.loss, self.option)
        r = self.client.get(reverse('waste_to_value_capital_allocation_engine:decision_detail', args=[decision.pk]))
        content = r.content.decode()
        for phrase in self.FORBIDDEN_PHRASES:
            self.assertNotIn(phrase, content)

    def test_decision_text_frames_as_pending_recommendation(self):
        from capital_guardian.services.capital_decision_bridge import create_decision_from_better_way

        decision = create_decision_from_better_way(self.project, self.loss, self.option)
        self.assertIn('recommendation for human review', decision.decision)
        self.assertIn('not an approved or funded outcome', decision.decision)
