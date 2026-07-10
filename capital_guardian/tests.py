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
)
from capital_guardian.services import (
    audit_log, capital_protection, capital_trace, evidence as evidence_service, investor_dashboard,
    portfolio, red_flag_engine,
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
