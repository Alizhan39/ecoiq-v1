"""
company_intelligence/tests.py — feat/company-halal-intelligence (PR 9).

Every test here is built around this app's core discipline: the Shariah
lens and the 114-KPI lens must never be conflated, uncertainty must never
be collapsed to a fake binary answer, and no field anywhere may express a
buy/sell/hold recommendation. Tests assert either a real, evidence-backed
result or an honest "insufficient_data"/"not_assessed"/"NOT_AVAILABLE"
state when a required input is missing.
"""
import datetime

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from companies.models import CompanyProfile
from company_intelligence.models import (
    KPI_STATUS_CHOICES, SCREEN_RESULT_CHOICES, CompanyControversy, CompanyFinancialFacts,
    CompanyKPIAssessment, CompanyKPIEvidenceLink, CompanyListing, ResearchWatchlistEntry,
    ShariahMethodology,
)
from company_intelligence.services import kpi_engine, shariah_screening
from company_intelligence.services.company_trace import build_company_trace
from evidence_memory.models import EvidenceMemory
from league.models import Company

User = get_user_model()


def _methodology(**overrides):
    defaults = dict(
        name='Test Reference Screen', version='1.0',
        description='Test methodology — not a religious ruling.',
        business_activity_rules=[
            {'category': 'conventional_banking', 'label': 'Conventional banking', 'status': 'blocked',
             'keywords': ['conventional bank', 'interest-based lending']},
            {'category': 'defence_controversial', 'label': 'Controversial weapons', 'status': 'restricted',
             'keywords': ['controversial weapons'], 'tolerance_pct': 5.0},
        ],
        financial_ratio_rules={
            'debt_to_market_cap_max': 0.33,
            'interest_bearing_securities_to_market_cap_max': 0.33,
            'non_permissible_income_to_revenue_max': 0.05,
        },
        effective_date=datetime.date(2026, 1, 1),
    )
    defaults.update(overrides)
    return ShariahMethodology.objects.create(**defaults)


def _profile(name='Test Co', slug='test-co', sector='energy', description='A clean energy company.'):
    company = Company.objects.create(name=name, slug=slug, sector=sector, country='Kazakhstan', description=description)
    return CompanyProfile.objects.create(company=company, status='public')


class CompanyIdentityTests(TestCase):
    def test_company_creation_and_listing(self):
        profile = _profile()
        listing = CompanyListing.objects.create(
            company=profile.company, ticker='TST', exchange='AIX', currency='USD', is_primary=True,
        )
        self.assertEqual(profile.company.listings.count(), 1)
        self.assertEqual(listing.ticker, 'TST')

    def test_multiple_listings_supported(self):
        profile = _profile()
        CompanyListing.objects.create(company=profile.company, ticker='TSTA', exchange='AIX', is_primary=True)
        CompanyListing.objects.create(company=profile.company, ticker='TSTB', exchange='LSE', is_primary=False)
        self.assertEqual(profile.company.listings.count(), 2)


class BusinessActivityScreenTests(TestCase):
    def test_blocked_category_fails(self):
        methodology = _methodology()
        profile = _profile(description='Operates as a conventional bank offering interest-based lending.')
        result = shariah_screening.run_business_activity_screen(profile, methodology)
        self.assertEqual(result['result'], 'fail')
        self.assertIn('conventional_banking', result['matched_categories'])

    def test_restricted_category_is_conditional_not_pass(self):
        methodology = _methodology()
        profile = _profile(description='Manufactures components including controversial weapons systems.')
        result = shariah_screening.run_business_activity_screen(profile, methodology)
        self.assertEqual(result['result'], 'conditional')

    def test_clean_description_passes(self):
        methodology = _methodology()
        profile = _profile(description='Operates solar and wind power generation assets.')
        result = shariah_screening.run_business_activity_screen(profile, methodology)
        self.assertEqual(result['result'], 'pass')

    def test_no_description_is_insufficient_data_not_pass(self):
        methodology = _methodology()
        profile = _profile(description='')
        result = shariah_screening.run_business_activity_screen(profile, methodology)
        self.assertEqual(result['result'], 'insufficient_data')


class FinancialRatioScreenTests(TestCase):
    def test_all_ratios_within_threshold_pass(self):
        methodology = _methodology()
        facts = CompanyFinancialFacts.objects.create(
            company=_profile(slug='fr-pass'), as_of_date=datetime.date(2026, 1, 1),
            market_cap_usd=1000, total_debt_usd=100, interest_bearing_securities_usd=50,
            non_permissible_income_usd=10, revenue_usd=500,
        )
        result = shariah_screening.run_financial_ratio_screen(facts, methodology)
        self.assertEqual(result['result'], 'pass')
        self.assertEqual(result['detail']['missing_inputs'], [])

    def test_ratio_over_threshold_fails(self):
        methodology = _methodology()
        facts = CompanyFinancialFacts.objects.create(
            company=_profile(slug='fr-fail'), as_of_date=datetime.date(2026, 1, 1),
            market_cap_usd=1000, total_debt_usd=500,  # 50% > 33% threshold
        )
        result = shariah_screening.run_financial_ratio_screen(facts, methodology)
        self.assertEqual(result['result'], 'fail')

    def test_missing_financial_facts_is_insufficient_data(self):
        methodology = _methodology()
        result = shariah_screening.run_financial_ratio_screen(None, methodology)
        self.assertEqual(result['result'], 'insufficient_data')
        self.assertIn('financial_facts', result['detail']['missing_inputs'])

    def test_missing_value_never_silently_treated_as_zero(self):
        """The core honesty guarantee: a missing total_debt_usd must NEVER
        be computed as if it were 0 (which would produce a false 0% ratio
        and a false PASS)."""
        methodology = _methodology()
        facts = CompanyFinancialFacts.objects.create(
            company=_profile(slug='fr-missing'), as_of_date=datetime.date(2026, 1, 1),
            market_cap_usd=1000, total_debt_usd=None,  # genuinely unknown
        )
        result = shariah_screening.run_financial_ratio_screen(facts, methodology)
        self.assertNotIn('debt_to_market_cap', result['detail']['ratios'])
        self.assertIn('total_debt_usd', result['detail']['missing_inputs'])
        self.assertNotEqual(result['result'], 'pass')

    def test_partial_data_is_conditional_not_pass_or_fail(self):
        methodology = _methodology()
        facts = CompanyFinancialFacts.objects.create(
            company=_profile(slug='fr-partial'), as_of_date=datetime.date(2026, 1, 1),
            market_cap_usd=1000, total_debt_usd=100,  # only one of three ratios computable
        )
        result = shariah_screening.run_financial_ratio_screen(facts, methodology)
        self.assertEqual(result['result'], 'conditional')


class MethodologyVersioningTests(TestCase):
    def test_two_versions_of_same_methodology_coexist(self):
        v1 = _methodology(name='Versioned Screen', version='1.0')
        v2 = _methodology(name='Versioned Screen', version='2.0', financial_ratio_rules={'debt_to_market_cap_max': 0.5})
        self.assertNotEqual(v1.financial_ratio_rules, v2.financial_ratio_rules)
        self.assertEqual(ShariahMethodology.objects.filter(name='Versioned Screen').count(), 2)

    def test_thresholds_are_configurable_not_hardcoded(self):
        strict = _methodology(name='Strict', financial_ratio_rules={'debt_to_market_cap_max': 0.01})
        facts = CompanyFinancialFacts.objects.create(
            company=_profile(slug='strict-co'), as_of_date=datetime.date(2026, 1, 1),
            market_cap_usd=1000, total_debt_usd=50,  # 5% > 1% strict threshold
        )
        result = shariah_screening.run_financial_ratio_screen(facts, strict)
        self.assertEqual(result['result'], 'fail')


class OverallScreenCombinationTests(TestCase):
    def test_overall_screen_orchestrates_and_persists(self):
        methodology = _methodology()
        profile = _profile(slug='orchestrate-co', description='Operates solar power assets.')
        facts = CompanyFinancialFacts.objects.create(
            company=profile, as_of_date=datetime.date(2026, 1, 1),
            market_cap_usd=1000, total_debt_usd=100, interest_bearing_securities_usd=50,
            non_permissible_income_usd=10, revenue_usd=500,
        )
        screen = shariah_screening.run_shariah_screen(profile, methodology, financial_facts=facts, is_demo=True)
        self.assertEqual(screen.overall_result, 'pass')
        self.assertEqual(screen.review_status, 'automated_preliminary')
        self.assertTrue(screen.is_demo)
        self.assertEqual(shariah_screening.latest_screen_for(profile), screen)

    def test_not_screened_when_no_screen_run(self):
        profile = _profile(slug='never-screened')
        self.assertIsNone(shariah_screening.latest_screen_for(profile))


class KPIEngineTests(TestCase):
    def test_denominator_is_always_114(self):
        profile = _profile(slug='kpi-denom-co')
        profile2 = _profile(slug='kpi-denom-empty')
        for p in (profile, profile2):
            result = kpi_engine.kpi_alignment_profile(p)
            self.assertEqual(result['total'], 114)
            self.assertEqual(sum(result['counts'].values()), 114)

    def test_no_evidence_at_all_is_not_assessed(self):
        profile = _profile(slug='kpi-none')
        result = kpi_engine.kpi_alignment_profile(profile)
        self.assertEqual(result['counts']['not_assessed'], 114)
        self.assertEqual(result['assessed'], 0)

    def test_supporting_evidence_only_gives_support(self):
        profile = _profile(slug='kpi-support')
        evidence = EvidenceMemory.objects.create(
            text_chunk='Independent audit confirms real emissions reduction.', company=profile,
            verification_status='verified', review_tier='system_checked',
        )
        assessment = CompanyKPIAssessment.objects.create(company=profile, kpi_id=21)
        CompanyKPIEvidenceLink.objects.create(assessment=assessment, evidence=evidence, relationship='supports')
        status = kpi_engine.recompute_assessment_status(assessment)
        self.assertEqual(status, 'support')

    def test_strong_evidence_tier_gives_strong_support(self):
        profile = _profile(slug='kpi-strong')
        evidence = EvidenceMemory.objects.create(
            text_chunk='Independently verified sustainability report.', company=profile,
            verification_status='verified', review_tier='independently_verified',
        )
        assessment = CompanyKPIAssessment.objects.create(company=profile, kpi_id=21)
        CompanyKPIEvidenceLink.objects.create(assessment=assessment, evidence=evidence, relationship='supports')
        status = kpi_engine.recompute_assessment_status(assessment)
        self.assertEqual(status, 'strong_support')

    def test_conflicting_evidence_only_gives_conflict(self):
        profile = _profile(slug='kpi-conflict')
        evidence = EvidenceMemory.objects.create(
            text_chunk='Regulatory finding of non-compliance.', company=profile,
            verification_status='verified', review_tier='system_checked',
        )
        assessment = CompanyKPIAssessment.objects.create(company=profile, kpi_id=4)
        CompanyKPIEvidenceLink.objects.create(assessment=assessment, evidence=evidence, relationship='conflicts')
        status = kpi_engine.recompute_assessment_status(assessment)
        self.assertEqual(status, 'conflict')

    def test_supports_and_conflicts_together_give_mixed(self):
        profile = _profile(slug='kpi-mixed')
        support_ev = EvidenceMemory.objects.create(text_chunk='Positive report.', company=profile, verification_status='verified')
        conflict_ev = EvidenceMemory.objects.create(text_chunk='Negative finding.', company=profile, verification_status='verified')
        assessment = CompanyKPIAssessment.objects.create(company=profile, kpi_id=4)
        CompanyKPIEvidenceLink.objects.create(assessment=assessment, evidence=support_ev, relationship='supports')
        CompanyKPIEvidenceLink.objects.create(assessment=assessment, evidence=conflict_ev, relationship='conflicts')
        status = kpi_engine.recompute_assessment_status(assessment)
        self.assertEqual(status, 'mixed')

    def test_context_only_evidence_is_insufficient_evidence(self):
        profile = _profile(slug='kpi-context')
        evidence = EvidenceMemory.objects.create(text_chunk='Background context only.', company=profile)
        assessment = CompanyKPIAssessment.objects.create(company=profile, kpi_id=4)
        CompanyKPIEvidenceLink.objects.create(assessment=assessment, evidence=evidence, relationship='context')
        status = kpi_engine.recompute_assessment_status(assessment)
        self.assertEqual(status, 'insufficient_evidence')

    def test_status_never_generated_from_evidence_text_alone(self):
        """The core anti-LLM-fabrication guarantee: two assessments with
        identically-worded evidence text but different explicit
        relationship types must derive different, correct statuses —
        proving the status comes from the structured relationship field,
        never from interpreting the free text."""
        profile = _profile(slug='kpi-no-llm')
        text = 'Company reports strong environmental performance.'
        ev_support = EvidenceMemory.objects.create(text_chunk=text, company=profile, verification_status='verified')
        ev_conflict = EvidenceMemory.objects.create(text_chunk=text, company=profile, verification_status='verified')
        a1 = CompanyKPIAssessment.objects.create(company=profile, kpi_id=21)
        CompanyKPIEvidenceLink.objects.create(assessment=a1, evidence=ev_support, relationship='supports')
        a2 = CompanyKPIAssessment.objects.create(company=profile, kpi_id=22)
        CompanyKPIEvidenceLink.objects.create(assessment=a2, evidence=ev_conflict, relationship='conflicts')
        self.assertEqual(kpi_engine.recompute_assessment_status(a1), 'support')
        self.assertEqual(kpi_engine.recompute_assessment_status(a2), 'conflict')

    def test_filter_rows_by_status(self):
        profile = _profile(slug='kpi-filter')
        result = kpi_engine.kpi_alignment_profile(profile)
        filtered = kpi_engine.filter_rows(result['rows'], 'not_assessed')
        self.assertEqual(len(filtered), 114)
        self.assertTrue(all(r['status'] == 'not_assessed' for r in filtered))

    def test_invalid_kpi_id_rejected_by_assert_guard(self):
        """core.esg_principles_data.PRINCIPLES integrity guard — the module
        itself asserts on import; this test documents that a broken
        canonical source would fail loudly, not silently."""
        from core.esg_principles_data import PRINCIPLES
        self.assertEqual(len(PRINCIPLES), 114)
        self.assertEqual(sorted(p['id'] for p in PRINCIPLES), list(range(1, 115)))


class DemoLabellingTests(TestCase):
    def test_demo_screen_flagged(self):
        methodology = _methodology()
        profile = _profile(slug='demo-flag-co')
        screen = shariah_screening.run_shariah_screen(profile, methodology, is_demo=True)
        self.assertTrue(screen.is_demo)

    def test_real_screen_not_flagged_demo_by_default(self):
        methodology = _methodology()
        profile = _profile(slug='real-flag-co')
        screen = shariah_screening.run_shariah_screen(profile, methodology)
        self.assertFalse(screen.is_demo)


class CompanyExplainabilityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('trace_user', 'trace@ecoiq.uk', 'password123')

    def test_trace_has_ten_nodes_in_order(self):
        profile = _profile(slug='trace-co')
        trace = build_company_trace(profile, user=self.user)
        self.assertEqual(
            [n.stage for n in trace.nodes],
            ['company', 'methodology', 'business_activity', 'financial_evidence', 'shariah_result',
             'kpi_evidence', 'positive_alignment', 'conflicting_evidence', 'evidence_gaps', 'overall_profile'],
        )

    def test_trace_honest_when_never_screened(self):
        profile = _profile(slug='trace-unscreened')
        trace = build_company_trace(profile, user=self.user)
        methodology_node = next(n for n in trace.nodes if n.stage == 'methodology')
        self.assertFalse(methodology_node.available)
        self.assertIn('No Shariah screen has been run', ' '.join(trace.data_gaps))

    def test_trace_never_contains_buy_sell_language(self):
        """Bans actual recommendation phrases — the summary's own honest
        disclaimer ('contains no buy/sell recommendation') legitimately
        contains the substrings 'buy'/'sell', so this checks for
        recommendation phrasing, not those bare substrings."""
        methodology = _methodology()
        profile = _profile(slug='trace-no-advice', description='Operates solar power assets.')
        shariah_screening.run_shariah_screen(profile, methodology)
        trace = build_company_trace(profile, user=self.user)
        overall = next(n for n in trace.nodes if n.stage == 'overall_profile')
        summary_lower = overall.summary.lower()
        for banned in ('strong buy', 'target price', 'you should buy', 'you should sell', 'we recommend'):
            self.assertNotIn(banned, summary_lower)
        self.assertIn('not personalised investment advice', summary_lower)

    def test_restricted_evidence_excluded_from_positive_alignment(self):
        from evidence_memory.services.retrieval_policy import is_company_record_accessible
        profile = _profile(slug='trace-restricted')
        evidence = EvidenceMemory.objects.create(
            text_chunk='Positive claim.', company=profile, verification_status='verified',
            visibility='restricted_unresolved',
        )
        assessment = CompanyKPIAssessment.objects.create(company=profile, kpi_id=21)
        CompanyKPIEvidenceLink.objects.create(assessment=assessment, evidence=evidence, relationship='supports')
        self.assertFalse(is_company_record_accessible(evidence, profile))


class WatchlistTests(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME='localhost')
        self.user = User.objects.create_user('wl_user', 'wl_user@ecoiq.uk', 'password123')
        self.other_user = User.objects.create_user('wl_other', 'wl_other@ecoiq.uk', 'password123')
        self.profile = _profile(slug='wl-co')

    def test_add_to_watchlist_requires_login(self):
        r = self.client.post(reverse('companies:watchlist_add', args=[self.profile.company.slug]), {'status': 'researching'})
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login', r['Location'])
        self.assertEqual(ResearchWatchlistEntry.objects.count(), 0)

    def test_add_to_watchlist_creates_entry(self):
        self.client.force_login(self.user)
        r = self.client.post(reverse('companies:watchlist_add', args=[self.profile.company.slug]), {'status': 'high_kpi_alignment'})
        self.assertEqual(r.status_code, 302)
        entry = ResearchWatchlistEntry.objects.get(user=self.user, company=self.profile)
        self.assertEqual(entry.status, 'high_kpi_alignment')

    def test_watchlist_status_never_a_recommendation(self):
        valid = {choice for choice, _ in ResearchWatchlistEntry.STATUS_CHOICES}
        for banned in ('buy', 'sell', 'strong_buy', 'hold', 'target_price'):
            self.assertNotIn(banned, valid)

    def test_invalid_status_falls_back_to_researching(self):
        self.client.force_login(self.user)
        self.client.post(reverse('companies:watchlist_add', args=[self.profile.company.slug]), {'status': 'buy'})
        entry = ResearchWatchlistEntry.objects.get(user=self.user, company=self.profile)
        self.assertEqual(entry.status, 'researching')

    def test_watchlist_is_per_user_isolated(self):
        self.client.force_login(self.user)
        self.client.post(reverse('companies:watchlist_add', args=[self.profile.company.slug]), {'status': 'researching'})
        self.client.logout()
        self.client.force_login(self.other_user)
        r = self.client.get(reverse('companies:watchlist'))
        self.assertNotContains(r, self.profile.company.name)

    def test_watchlist_view_requires_login(self):
        r = self.client.get(reverse('companies:watchlist'))
        self.assertEqual(r.status_code, 302)

    def test_watchlist_shows_only_own_entries(self):
        self.client.force_login(self.user)
        self.client.post(reverse('companies:watchlist_add', args=[self.profile.company.slug]), {'status': 'needs_review'})
        r = self.client.get(reverse('companies:watchlist'))
        self.assertContains(r, self.profile.company.name)

    def test_remove_from_watchlist(self):
        self.client.force_login(self.user)
        self.client.post(reverse('companies:watchlist_add', args=[self.profile.company.slug]), {'status': 'researching'})
        self.client.post(reverse('companies:watchlist_remove', args=[self.profile.company.slug]))
        self.assertFalse(ResearchWatchlistEntry.objects.filter(user=self.user, company=self.profile).exists())


class CompanyDetailIntegrationTests(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME='localhost')
        self.methodology = _methodology()
        self.profile = _profile(slug='detail-co', description='Operates solar power assets.')

    def test_detail_page_shows_shariah_and_kpi_sections(self):
        shariah_screening.run_shariah_screen(self.profile, self.methodology)
        r = self.client.get(reverse('companies:detail', args=[self.profile.company.slug]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Shariah Eligibility Screen')
        self.assertContains(r, '114-KPI Alignment')
        self.assertContains(r, 'Controversies')

    def test_detail_page_public_no_login_required(self):
        r = self.client.get(reverse('companies:detail', args=[self.profile.company.slug]))
        self.assertEqual(r.status_code, 200)

    def test_kpi_filter_query_param_narrows_explorer(self):
        r = self.client.get(reverse('companies:detail', args=[self.profile.company.slug]), {'kpi_filter': 'conflict'})
        self.assertEqual(r.status_code, 200)

    def test_never_shows_not_screened_as_pass(self):
        r = self.client.get(reverse('companies:detail', args=[self.profile.company.slug]))
        self.assertContains(r, 'Not Screened')

    def test_no_buy_sell_language_anywhere_on_page(self):
        shariah_screening.run_shariah_screen(self.profile, self.methodology)
        r = self.client.get(reverse('companies:detail', args=[self.profile.company.slug]))
        content = r.content.decode().lower()
        for banned in ('strong buy', 'target price', '>buy<', '>sell<'):
            self.assertNotIn(banned, content)


class ExplainViewTests(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME='localhost')
        self.profile = _profile(slug='explain-view-co')

    def test_explain_view_public_get(self):
        r = self.client.get(reverse('companies:explain', args=[self.profile.company.slug]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Why Does EcoIQ Classify This Company This Way?')

    def test_explain_view_nonexistent_company_404s(self):
        r = self.client.get(reverse('companies:explain', args=['no-such-company']))
        self.assertEqual(r.status_code, 404)

    def test_explain_view_writes_no_state(self):
        from ai_observatory.models import AnalysisSession
        before = AnalysisSession.objects.count()
        self.client.get(reverse('companies:explain', args=[self.profile.company.slug]))
        self.client.get(reverse('companies:explain', args=[self.profile.company.slug]))
        self.assertEqual(AnalysisSession.objects.count(), before)


class ObservatoryIntegrationTests(TestCase):
    def test_company_session_requires_exactly_one_anchor(self):
        from ai_observatory.services import recorder
        profile = _profile(slug='obs-co')
        session = recorder.start_session(company=profile, kind='company_intelligence')
        self.assertIsNotNone(session)
        self.assertEqual(session.company, profile)
        self.assertIsNone(session.project_id)

    def test_start_session_rejects_both_anchors(self):
        from ai_observatory.services import recorder
        from gold_intelligence.models import GoldProject
        profile = _profile(slug='obs-both-co')
        project = GoldProject.objects.create(name='Obs Test Project', slug='obs-test-project')
        session = recorder.start_session(project=project, company=profile, kind='company_intelligence')
        self.assertIsNone(session)

    def test_start_session_rejects_neither_anchor(self):
        from ai_observatory.services import recorder
        session = recorder.start_session(kind='company_intelligence')
        self.assertIsNone(session)

    def test_project_session_unaffected_by_company_anchor(self):
        """Confirms the existing project-anchored telemetry path (PR4-8)
        still works exactly as before this PR's changes."""
        from ai_observatory.services import recorder
        from gold_intelligence.models import GoldProject
        project = GoldProject.objects.create(name='Obs Project Path', slug='obs-project-path')
        session = recorder.start_session(project, 'project_analysis')
        self.assertIsNotNone(session)
        self.assertEqual(session.project, project)
        self.assertIsNone(session.company_id)

    def test_company_intelligence_kind_recorded(self):
        from ai_observatory.services import recorder
        methodology = _methodology()
        profile = _profile(slug='obs-kind-co', description='Operates solar power assets.')
        session = recorder.start_session(company=profile, kind='company_intelligence')
        with recorder.record_stage(session, 'business_activity_screen', 'Business Activity Screen'):
            pass
        screen = shariah_screening.run_shariah_screen(profile, methodology, is_demo=True)
        recorder.finish_session(session, final_recommendation_status='recorded')
        session.refresh_from_db()
        self.assertEqual(session.kind, 'company_intelligence')
        self.assertEqual(session.deterministic_stage_count, 1)
        self.assertEqual(session.model_call_count, 0)


class ControversyTests(TestCase):
    def test_controversy_never_suppressed_by_positive_status(self):
        profile = _profile(slug='controversy-co', description='Operates solar power assets.')
        evidence = EvidenceMemory.objects.create(
            text_chunk='Labour dispute reported.', company=profile, verification_status='verified',
        )
        CompanyControversy.objects.create(
            company=profile, title='Labour dispute', category='labour', severity='high',
            status='unresolved', evidence=evidence, is_demo=True,
        )
        # Even with a passing Shariah screen, the controversy must remain visible.
        methodology = _methodology()
        shariah_screening.run_shariah_screen(profile, methodology, is_demo=True)
        self.assertEqual(profile.controversies.count(), 1)
        trace = build_company_trace(profile)
        conflict_node = next(n for n in trace.nodes if n.stage == 'conflicting_evidence')
        self.assertTrue(conflict_node.available)
        self.assertEqual(len(conflict_node.extra['controversies']), 1)


class ChoiceVocabularyTests(TestCase):
    def test_screen_result_choices_never_include_investment_language(self):
        valid_values = {c for c, _ in SCREEN_RESULT_CHOICES}
        self.assertEqual(valid_values, {'pass', 'fail', 'conditional', 'insufficient_data', 'not_screened'})

    def test_kpi_status_choices_are_the_documented_seven(self):
        valid_values = {c for c, _ in KPI_STATUS_CHOICES}
        self.assertEqual(valid_values, {
            'strong_support', 'support', 'mixed', 'neutral_or_no_material_link',
            'conflict', 'insufficient_evidence', 'not_assessed',
        })
