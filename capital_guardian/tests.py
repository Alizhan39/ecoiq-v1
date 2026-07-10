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
from gold_intelligence.models import CapitalBudgetLine, EquipmentSpec, GoldProject, MineTimelineMilestone

from capital_guardian.models import CapitalTraceEntry, OperationalSnapshot, ProjectGovernance, RedFlag
from capital_guardian.services import capital_protection, capital_trace, investor_dashboard, red_flag_engine


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
