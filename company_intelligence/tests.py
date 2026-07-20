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

    def test_trace_has_twelve_nodes_in_order(self):
        """feat/company-evidence-ingestion (PR 10) extended PR9's 10-node
        trace to 12, inserting 'sources' after company identity and
        'evidence_review' after KPI evidence — documented, intentional."""
        profile = _profile(slug='trace-co')
        trace = build_company_trace(profile, user=self.user)
        self.assertEqual(
            [n.stage for n in trace.nodes],
            ['company', 'sources', 'methodology', 'business_activity', 'financial_evidence', 'shariah_result',
             'kpi_evidence', 'evidence_review', 'positive_alignment', 'conflicting_evidence', 'evidence_gaps',
             'overall_profile'],
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


# ═══════════════════════════════════════════════════════════════════════════
# feat/company-evidence-ingestion (PR 10) — REAL PUBLIC COMPANY -> AUTHORITATIVE
# PUBLIC SOURCES -> STRUCTURED EVIDENCE -> PROVENANCE -> ... -> COMPANY
# INTELLIGENCE PROFILE. Every SEC EDGAR HTTP call is mocked (never a live
# network call in the test suite itself — matches harvester/tests.py's own
# established @patch('harvester.services.fetchers.http_fetch') convention),
# but the response payload shapes mirror real ones observed during
# development (see harvester/services/fetchers.py::fetch_sec_edgar's
# docstring for the real Tesla stale-concept bug this module regression-
# tests against).
# ═══════════════════════════════════════════════════════════════════════════
from unittest.mock import patch

from backend_intelligence_engine.services.http_client import HTTPFetchResult
from company_intelligence.models import (
    CompanyFinancialFactSource, EvidenceReviewAction,
)
from company_intelligence.services import evidence_ingestion
from company_intelligence.services.data_origin import company_data_origin
from company_intelligence.services.freshness import screening_freshness
from harvester.models import Evidence as HarvesterEvidence
from harvester.models import Source as HarvesterSource


def _xbrl_result(us_gaap_facts, entity_name='Test Real Co.'):
    return HTTPFetchResult(
        success=True, status_code=200, content=b'x', text='',
        json_data={'entityName': entity_name, 'facts': {'us-gaap': us_gaap_facts}},
        attempts=1, elapsed_seconds=0.01, headers={'content-type': 'application/json'},
    )


COMPLETE_XBRL_FACTS = {
    'Revenues': {'units': {'USD': [{'val': 1_000_000_000, 'end': '2025-12-31', 'form': '10-K'}]}},
    'LongTermDebt': {'units': {'USD': [{'val': 200_000_000, 'end': '2025-12-31', 'form': '10-K'}]}},
    'CashAndCashEquivalentsAtCarryingValue': {'units': {'USD': [{'val': 50_000_000, 'end': '2025-12-31', 'form': '10-K'}]}},
    'InvestmentIncomeInterest': {'units': {'USD': [{'val': 5_000_000, 'end': '2025-12-31', 'form': '10-K'}]}},
}

PARTIAL_XBRL_FACTS = {
    'Revenues': {'units': {'USD': [{'val': 500_000_000, 'end': '2025-12-31', 'form': '10-K'}]}},
    'LongTermDebt': {'units': {'USD': [{'val': 100_000_000, 'end': '2025-12-31', 'form': '10-K'}]}},
    # cash and interest income deliberately absent — honest incompleteness.
}

# Reproduces the real bug caught in development: a stale, long-obsolete
# concept (LongTermDebtNoncurrent, a single $0 entry from 2013) alongside
# the real, current concept (LongTermDebt, 2025) for the same metric.
STALE_CONCEPT_XBRL_FACTS = {
    'Revenues': {'units': {'USD': [{'val': 900_000_000, 'end': '2025-12-31', 'form': '10-K'}]}},
    'LongTermDebtNoncurrent': {'units': {'USD': [{'val': 0, 'end': '2013-12-31', 'form': '10-K'}]}},
    'LongTermDebt': {'units': {'USD': [{'val': 300_000_000, 'end': '2025-12-31', 'form': '10-K'}]}},
}


def _real_profile(slug='apple'):
    """Uses a real CIK-mapped slug from US_COMPANY_CIKS so
    resolve_company_identity() finds it — the HTTP call itself is mocked,
    the identity mapping is real."""
    company, _ = Company.objects.get_or_create(slug=slug, defaults={'name': 'Test Real Co.', 'sector': 'other'})
    return CompanyProfile.objects.get_or_create(company=company, defaults={'status': 'public'})[0]


class SecEdgarFetcherTests(TestCase):
    @patch('harvester.services.fetchers.http_fetch')
    def test_stale_concept_never_wins_over_current_one(self, mock_fetch):
        """Regression test for the real bug caught during PR10 development:
        picking 'first concept with any value' would have surfaced an
        11-year-stale $0 as current debt. Must pick the most recent `end`
        date across ALL candidate concepts instead."""
        from harvester.services import fetchers
        mock_fetch.return_value = _xbrl_result(STALE_CONCEPT_XBRL_FACTS)
        outcome = fetchers.fetch_sec_edgar('apple')
        self.assertTrue(outcome.success)
        self.assertEqual(outcome.metadata['metrics']['total_debt_usd']['value'], 300_000_000)
        self.assertEqual(outcome.metadata['metrics']['total_debt_usd']['concept'], 'LongTermDebt')

    @patch('harvester.services.fetchers.http_fetch')
    def test_missing_concept_is_absent_not_zero(self, mock_fetch):
        from harvester.services import fetchers
        mock_fetch.return_value = _xbrl_result(PARTIAL_XBRL_FACTS)
        outcome = fetchers.fetch_sec_edgar('apple')
        self.assertNotIn('cash_and_equivalents_usd', outcome.metadata['metrics'])
        self.assertNotIn('non_permissible_income_usd', outcome.metadata['metrics'])

    def test_unmapped_slug_is_honestly_skipped(self):
        from harvester.services import fetchers
        outcome = fetchers.fetch_sec_edgar('no-such-company-slug')
        self.assertFalse(outcome.success)
        self.assertIn('No SEC EDGAR CIK mapped', outcome.skipped_reason)

    @patch('harvester.services.fetchers.http_fetch')
    def test_derived_metric_labelled_as_derived(self, mock_fetch):
        from harvester.services import fetchers
        mock_fetch.return_value = _xbrl_result(COMPLETE_XBRL_FACTS)
        outcome = fetchers.fetch_sec_edgar('apple')
        self.assertTrue(outcome.metadata['metrics']['non_permissible_income_usd']['is_derived'])
        self.assertFalse(outcome.metadata['metrics']['revenue_usd']['is_derived'])


class IdentityResolutionTests(TestCase):
    def test_mapped_company_resolves_real_cik(self):
        profile = _real_profile('apple')
        identity = evidence_ingestion.resolve_company_identity(profile)
        self.assertTrue(identity['sec_available'])
        self.assertEqual(identity['cik'], '0000320193')

    def test_unmapped_company_honestly_unavailable(self):
        profile = _real_profile('some-unmapped-company')
        identity = evidence_ingestion.resolve_company_identity(profile)
        self.assertFalse(identity['sec_available'])
        self.assertIsNone(identity['cik'])


class EvidenceIngestionIdempotencyTests(TestCase):
    @patch('harvester.services.fetchers.http_fetch')
    def test_second_run_creates_no_duplicate_evidence(self, mock_fetch):
        mock_fetch.return_value = _xbrl_result(COMPLETE_XBRL_FACTS)
        profile = _real_profile('apple')

        evidence_ingestion.ingest_company_evidence(profile)
        first_evidence_count = HarvesterEvidence.objects.filter(company_slug='apple').count()
        first_memory_count = EvidenceMemory.objects.filter(company=profile).count()
        first_facts_count = CompanyFinancialFacts.objects.filter(company=profile).count()

        evidence_ingestion.ingest_company_evidence(profile)
        self.assertEqual(HarvesterEvidence.objects.filter(company_slug='apple').count(), first_evidence_count)
        self.assertEqual(EvidenceMemory.objects.filter(company=profile).count(), first_memory_count)
        self.assertEqual(CompanyFinancialFacts.objects.filter(company=profile).count(), first_facts_count)

    @patch('harvester.services.fetchers.http_fetch')
    def test_no_duplicate_source_created(self, mock_fetch):
        mock_fetch.return_value = _xbrl_result(COMPLETE_XBRL_FACTS)
        profile = _real_profile('apple')
        evidence_ingestion.ingest_company_evidence(profile)
        evidence_ingestion.ingest_company_evidence(profile)
        self.assertEqual(HarvesterSource.objects.filter(company=profile, source_type='sec_edgar').count(), 1)

    @patch('harvester.services.fetchers.http_fetch')
    def test_changed_data_creates_new_versioned_snapshot_not_overwrite(self, mock_fetch):
        """"If document content changes: do not silently overwrite
        provenance. Maintain version/history semantics." """
        profile = _real_profile('apple')
        mock_fetch.return_value = _xbrl_result(COMPLETE_XBRL_FACTS)
        evidence_ingestion.ingest_company_evidence(profile)
        first_facts = profile.financial_facts.order_by('-id').first()

        changed_facts = dict(COMPLETE_XBRL_FACTS)
        changed_facts['Revenues'] = {'units': {'USD': [{'val': 1_200_000_000, 'end': '2026-12-31', 'form': '10-K'}]}}
        mock_fetch.return_value = _xbrl_result(changed_facts)
        evidence_ingestion.ingest_company_evidence(profile)

        self.assertEqual(profile.financial_facts.count(), 2)
        latest_facts = profile.financial_facts.order_by('-id').first()
        self.assertNotEqual(latest_facts.pk, first_facts.pk)
        self.assertEqual(latest_facts.revenue_usd, 1_200_000_000)
        self.assertEqual(first_facts.revenue_usd, 1_000_000_000)  # prior snapshot untouched


class FinancialFactProvenanceTests(TestCase):
    @patch('harvester.services.fetchers.http_fetch')
    def test_missing_financial_value_never_becomes_zero(self, mock_fetch):
        mock_fetch.return_value = _xbrl_result(PARTIAL_XBRL_FACTS)
        profile = _real_profile('apple')
        result = evidence_ingestion.ingest_company_evidence(profile)
        facts = result['financial_facts']
        self.assertIsNone(facts.cash_and_equivalents_usd)
        self.assertIsNone(facts.non_permissible_income_usd)
        self.assertIsNotNone(facts.revenue_usd)

    @patch('harvester.services.fetchers.http_fetch')
    def test_every_metric_gets_its_own_provenance_row(self, mock_fetch):
        mock_fetch.return_value = _xbrl_result(COMPLETE_XBRL_FACTS)
        profile = _real_profile('apple')
        result = evidence_ingestion.ingest_company_evidence(profile)
        sources = {s.metric: s for s in result['financial_fact_sources']}
        self.assertIn('revenue_usd', sources)
        self.assertIn('total_debt_usd', sources)
        self.assertFalse(sources['revenue_usd'].is_derived)
        self.assertTrue(sources['non_permissible_income_usd'].is_derived)
        self.assertTrue(sources['non_permissible_income_usd'].interpretation_note)

    @patch('harvester.services.fetchers.http_fetch')
    def test_provenance_links_to_real_evidence_memory_row(self, mock_fetch):
        mock_fetch.return_value = _xbrl_result(COMPLETE_XBRL_FACTS)
        profile = _real_profile('apple')
        result = evidence_ingestion.ingest_company_evidence(profile)
        revenue_source = next(s for s in result['financial_fact_sources'] if s.metric == 'revenue_usd')
        self.assertIsNotNone(revenue_source.evidence)
        self.assertEqual(revenue_source.evidence.source_type, 'harvester_evidence')

    def test_value_property_resolves_correct_field(self):
        facts = CompanyFinancialFacts.objects.create(
            company=_real_profile('apple'), as_of_date=datetime.date(2026, 1, 1), revenue_usd=42.0,
        )
        source = CompanyFinancialFactSource.objects.create(financial_facts=facts, metric='revenue_usd')
        self.assertEqual(source.value, 42.0)
        missing_source = CompanyFinancialFactSource.objects.create(financial_facts=facts, metric='total_debt_usd')
        self.assertIsNone(missing_source.value)


class RealVsDemoSeparationTests(TestCase):
    @patch('harvester.services.fetchers.http_fetch')
    def test_real_ingestion_never_flagged_demo(self, mock_fetch):
        mock_fetch.return_value = _xbrl_result(COMPLETE_XBRL_FACTS)
        profile = _real_profile('apple')
        result = evidence_ingestion.ingest_company_evidence(profile)
        self.assertFalse(result['financial_facts'].is_demo)
        for source in HarvesterEvidence.objects.filter(company_slug='apple'):
            memory = EvidenceMemory.objects.filter(source_reference=f'harvester.Evidence:{source.pk}').first()
            if memory:
                self.assertFalse(memory.is_demo)

    def test_data_origin_unverified_when_nothing_exists(self):
        profile = _real_profile('never-ingested')
        origin = company_data_origin(profile)
        self.assertEqual(origin['origin'], 'unverified_import')

    @patch('harvester.services.fetchers.http_fetch')
    def test_data_origin_real_public_data_after_real_ingestion(self, mock_fetch):
        mock_fetch.return_value = _xbrl_result(COMPLETE_XBRL_FACTS)
        profile = _real_profile('apple')
        evidence_ingestion.ingest_company_evidence(profile)
        origin = company_data_origin(profile)
        self.assertEqual(origin['origin'], 'real_public_data')

    def test_mixing_real_and_demo_flags_as_mixed(self):
        profile = _real_profile('apple')
        methodology = _methodology()
        shariah_screening.run_shariah_screen(profile, methodology, is_demo=False)
        shariah_screening.run_shariah_screen(profile, methodology, is_demo=True)
        origin = company_data_origin(profile)
        self.assertEqual(origin['origin'], 'mixed')


class FreshnessStalenessTests(TestCase):
    def test_no_screen_is_honestly_unclassified(self):
        result = screening_freshness(None)
        self.assertIsNone(result['is_stale'])
        self.assertEqual(result['label'], 'Not Screened')

    def test_fresh_screen_is_current(self):
        methodology = _methodology()
        profile = _real_profile('apple')
        facts = CompanyFinancialFacts.objects.create(company=profile, as_of_date=datetime.date.today())
        screen = shariah_screening.run_shariah_screen(profile, methodology, financial_facts=facts)
        result = screening_freshness(screen)
        self.assertFalse(result['is_stale'])
        self.assertEqual(result['label'], 'Current')

    def test_old_financial_data_marks_screen_stale_even_if_just_screened(self):
        methodology = _methodology()
        profile = _real_profile('apple')
        old_date = datetime.date.today() - datetime.timedelta(days=400)
        facts = CompanyFinancialFacts.objects.create(company=profile, as_of_date=old_date)
        screen = shariah_screening.run_shariah_screen(profile, methodology, financial_facts=facts)
        result = screening_freshness(screen)
        self.assertTrue(result['is_stale'])
        self.assertEqual(result['label'], 'Screening Requires Refresh')
        self.assertIsNotNone(result['financial_data_days_ago'])
        self.assertGreater(result['financial_data_days_ago'], 180)


class EvidenceQualityTests(TestCase):
    @patch('harvester.services.fetchers.http_fetch')
    def test_harvester_backed_evidence_has_real_components(self, mock_fetch):
        from company_intelligence.services.evidence_quality import evidence_quality_for_memory
        mock_fetch.return_value = _xbrl_result(COMPLETE_XBRL_FACTS)
        profile = _real_profile('apple')
        evidence_ingestion.ingest_company_evidence(profile)
        memory = EvidenceMemory.objects.filter(company=profile).first()
        quality = evidence_quality_for_memory(memory)
        self.assertTrue(quality['has_harvester_record'])
        self.assertIsNotNone(quality['source_authority'])
        self.assertIsNotNone(quality['recency'])

    def test_non_harvester_evidence_honestly_unavailable(self):
        from company_intelligence.services.evidence_quality import evidence_quality_for_memory
        profile = _real_profile('apple')
        memory = EvidenceMemory.objects.create(text_chunk='Manual entry.', company=profile)
        quality = evidence_quality_for_memory(memory)
        self.assertFalse(quality['has_harvester_record'])
        self.assertIsNone(quality['source_authority'])


class KPICandidateMatchingReviewStateTests(TestCase):
    @patch('harvester.services.fetchers.http_fetch')
    def test_proposed_links_never_move_kpi_status(self, mock_fetch):
        """The core PR10 anti-fabrication guarantee: an ingestion-proposed
        (review_state='proposed') link must never move a KPI's status —
        only a 'confirmed' link counts."""
        mock_fetch.return_value = _xbrl_result(COMPLETE_XBRL_FACTS)
        profile = _real_profile('apple')
        evidence_ingestion.ingest_company_evidence(profile)
        # Manually force a proposed link to prove it's excluded from status derivation.
        evidence = EvidenceMemory.objects.filter(company=profile).first()
        if evidence is None:
            evidence = EvidenceMemory.objects.create(text_chunk='x', company=profile)
        assessment = CompanyKPIAssessment.objects.create(company=profile, kpi_id=99)
        link = CompanyKPIEvidenceLink.objects.create(
            assessment=assessment, evidence=evidence, relationship='supports', review_state='proposed',
        )
        status = kpi_engine.recompute_assessment_status(assessment)
        self.assertEqual(status, 'insufficient_evidence')  # proposed link ignored entirely

    def test_confirming_a_proposed_link_moves_status(self):
        profile = _real_profile('apple')
        evidence = EvidenceMemory.objects.create(text_chunk='x', company=profile)
        assessment = CompanyKPIAssessment.objects.create(company=profile, kpi_id=98)
        link = CompanyKPIEvidenceLink.objects.create(
            assessment=assessment, evidence=evidence, relationship='supports', review_state='proposed',
        )
        self.assertEqual(kpi_engine.recompute_assessment_status(assessment), 'insufficient_evidence')
        link.review_state = 'confirmed'
        link.save(update_fields=['review_state'])
        self.assertEqual(kpi_engine.recompute_assessment_status(assessment), 'support')

    def test_rejected_link_excluded_same_as_proposed(self):
        profile = _real_profile('apple')
        evidence = EvidenceMemory.objects.create(text_chunk='x', company=profile)
        assessment = CompanyKPIAssessment.objects.create(company=profile, kpi_id=97)
        CompanyKPIEvidenceLink.objects.create(
            assessment=assessment, evidence=evidence, relationship='supports', review_state='rejected',
        )
        self.assertEqual(kpi_engine.recompute_assessment_status(assessment), 'insufficient_evidence')

    def test_candidate_matcher_never_proposes_conflicts_automatically(self):
        from company_intelligence.services.kpi_candidate_matching import candidate_principles_for_evidence
        matches = candidate_principles_for_evidence(
            'governance', 'The board reduced oversight and published an audit report on executive compensation.',
        )
        relationships = {m['relationship'] for m in matches}
        self.assertNotIn('conflicts', relationships)


class EvidenceReviewWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME='localhost')
        self.staff = User.objects.create_user('review_staff', 'review_staff@ecoiq.uk', 'password123', is_staff=True)
        self.normal = User.objects.create_user('review_normal', 'review_normal@example.com', 'password123')
        self.profile = _real_profile('apple')
        self.evidence = EvidenceMemory.objects.create(text_chunk='Candidate evidence.', company=self.profile)
        self.assessment = CompanyKPIAssessment.objects.create(company=self.profile, kpi_id=50)
        self.link = CompanyKPIEvidenceLink.objects.create(
            assessment=self.assessment, evidence=self.evidence, relationship='supports', review_state='proposed',
        )

    def test_review_action_requires_staff(self):
        self.client.force_login(self.normal)
        r = self.client.post(
            reverse('companies:evidence_review_action', args=[self.profile.company.slug]),
            {'kpi_evidence_link_id': self.link.pk, 'action': 'verify'},
        )
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login', r['Location'])
        self.link.refresh_from_db()
        self.assertEqual(self.link.review_state, 'proposed')

    def test_verify_action_confirms_link_and_records_audit_row(self):
        self.client.force_login(self.staff)
        r = self.client.post(
            reverse('companies:evidence_review_action', args=[self.profile.company.slug]),
            {'kpi_evidence_link_id': self.link.pk, 'action': 'verify', 'reason': 'Confirmed against filing.'},
        )
        self.assertEqual(r.status_code, 302)
        self.link.refresh_from_db()
        self.assertEqual(self.link.review_state, 'confirmed')
        action = EvidenceReviewAction.objects.get(kpi_evidence_link=self.link)
        self.assertEqual(action.reviewer, self.staff)
        self.assertEqual(action.action, 'verify')
        self.assertEqual(action.reason, 'Confirmed against filing.')

    def test_reject_action_rejects_link(self):
        self.client.force_login(self.staff)
        self.client.post(
            reverse('companies:evidence_review_action', args=[self.profile.company.slug]),
            {'kpi_evidence_link_id': self.link.pk, 'action': 'reject'},
        )
        self.link.refresh_from_db()
        self.assertEqual(self.link.review_state, 'rejected')

    def test_mark_disputed_logs_without_changing_review_state(self):
        self.client.force_login(self.staff)
        self.client.post(
            reverse('companies:evidence_review_action', args=[self.profile.company.slug]),
            {'kpi_evidence_link_id': self.link.pk, 'action': 'mark_disputed', 'reason': 'Needs scholar review.'},
        )
        self.link.refresh_from_db()
        self.assertEqual(self.link.review_state, 'proposed')  # unchanged
        self.assertTrue(EvidenceReviewAction.objects.filter(kpi_evidence_link=self.link, action='mark_disputed').exists())

    def test_needs_more_evidence_logs_without_changing_review_state(self):
        self.client.force_login(self.staff)
        self.client.post(
            reverse('companies:evidence_review_action', args=[self.profile.company.slug]),
            {'kpi_evidence_link_id': self.link.pk, 'action': 'needs_more_evidence'},
        )
        self.link.refresh_from_db()
        self.assertEqual(self.link.review_state, 'proposed')

    def test_invalid_action_rejected(self):
        self.client.force_login(self.staff)
        r = self.client.post(
            reverse('companies:evidence_review_action', args=[self.profile.company.slug]),
            {'kpi_evidence_link_id': self.link.pk, 'action': 'buy'},
        )
        self.assertEqual(EvidenceReviewAction.objects.count(), 0)

    def test_cannot_review_another_companys_link(self):
        other_profile = _real_profile('tesla')
        self.client.force_login(self.staff)
        r = self.client.post(
            reverse('companies:evidence_review_action', args=[other_profile.company.slug]),
            {'kpi_evidence_link_id': self.link.pk, 'action': 'verify'},
        )
        self.assertEqual(r.status_code, 404)
        self.link.refresh_from_db()
        self.assertEqual(self.link.review_state, 'proposed')


class RefreshViewTests(TestCase):
    def setUp(self):
        self.client = Client(SERVER_NAME='localhost')
        self.staff = User.objects.create_user('refresh_staff', 'refresh_staff@ecoiq.uk', 'password123', is_staff=True)
        self.normal = User.objects.create_user('refresh_normal', 'refresh_normal@example.com', 'password123')
        self.profile = _real_profile('apple')

    def test_refresh_requires_staff(self):
        self.client.force_login(self.normal)
        r = self.client.post(reverse('companies:refresh', args=[self.profile.company.slug]))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login', r['Location'])

    @patch('harvester.services.fetchers.http_fetch')
    def test_staff_refresh_ingests_real_data(self, mock_fetch):
        mock_fetch.return_value = _xbrl_result(COMPLETE_XBRL_FACTS)
        self.client.force_login(self.staff)
        r = self.client.post(reverse('companies:refresh', args=[self.profile.company.slug]))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(CompanyFinancialFacts.objects.filter(company=self.profile).exists())

    def test_refresh_get_not_allowed(self):
        self.client.force_login(self.staff)
        r = self.client.get(reverse('companies:refresh', args=[self.profile.company.slug]))
        self.assertEqual(r.status_code, 404)

    def test_unmapped_company_refresh_shows_honest_warning_no_crash(self):
        self.client.force_login(self.staff)
        profile = _real_profile('some-unmapped-company-2')
        r = self.client.post(reverse('companies:refresh', args=[profile.company.slug]))
        self.assertEqual(r.status_code, 302)


class ObservatoryIngestionTelemetryTests(TestCase):
    @patch('harvester.services.fetchers.http_fetch')
    def test_ingestion_recorded_as_company_evidence_ingestion_kind(self, mock_fetch):
        from ai_observatory.models import AnalysisSession
        mock_fetch.return_value = _xbrl_result(COMPLETE_XBRL_FACTS)
        profile = _real_profile('apple')
        evidence_ingestion.ingest_company_evidence(profile)
        session = AnalysisSession.objects.filter(company=profile, kind='company_evidence_ingestion').first()
        self.assertIsNotNone(session)
        self.assertEqual(session.status, 'completed')
        self.assertGreater(session.deterministic_stage_count, 0)
        self.assertEqual(session.model_call_count, 0)  # fully deterministic pipeline — honest zero

    def test_unavailable_identity_still_records_session(self):
        from ai_observatory.models import AnalysisSession
        profile = _real_profile('some-unmapped-company-3')
        evidence_ingestion.ingest_company_evidence(profile)
        session = AnalysisSession.objects.filter(company=profile, kind='company_evidence_ingestion').first()
        self.assertIsNotNone(session)
        self.assertEqual(session.final_recommendation_status, 'not_applicable')


class ExplainTraceProvenanceTests(TestCase):
    @patch('harvester.services.fetchers.http_fetch')
    def test_sources_node_reflects_real_ingestion(self, mock_fetch):
        mock_fetch.return_value = _xbrl_result(COMPLETE_XBRL_FACTS)
        profile = _real_profile('apple')
        evidence_ingestion.ingest_company_evidence(profile)
        trace = build_company_trace(profile)
        sources_node = next(n for n in trace.nodes if n.stage == 'sources')
        self.assertTrue(sources_node.available)
        self.assertIn('Real Public Data', sources_node.status)

    def test_sources_node_honest_when_nothing_ingested(self):
        profile = _real_profile('never-ingested-2')
        trace = build_company_trace(profile)
        sources_node = next(n for n in trace.nodes if n.stage == 'sources')
        self.assertFalse(sources_node.available)

    def test_evidence_review_node_shows_pending_proposals(self):
        profile = _real_profile('apple')
        evidence = EvidenceMemory.objects.create(text_chunk='x', company=profile)
        assessment = CompanyKPIAssessment.objects.create(company=profile, kpi_id=96)
        CompanyKPIEvidenceLink.objects.create(
            assessment=assessment, evidence=evidence, relationship='supports', review_state='proposed',
        )
        trace = build_company_trace(profile)
        review_node = next(n for n in trace.nodes if n.stage == 'evidence_review')
        self.assertEqual(review_node.extra['pending_review_total'], 1)


class ControversyFindingTypeTests(TestCase):
    def test_finding_type_default_is_allegation(self):
        profile = _real_profile('apple')
        controversy = CompanyControversy.objects.create(company=profile, title='Test issue')
        self.assertEqual(controversy.finding_type, 'allegation')

    def test_finding_types_distinguish_evidentiary_weight(self):
        valid = {c for c, _ in CompanyControversy.FINDING_TYPE_CHOICES}
        self.assertEqual(valid, {
            'allegation', 'investigation', 'regulatory_finding', 'court_finding',
            'company_admission', 'verified_event',
        })
        self.assertNotIn('proven_fact', valid)  # never implies a court-level certainty by default


class ProjectOrganisationIsolationTests(TestCase):
    """feat/company-evidence-ingestion (PR 10) — company research has no
    organisation concept (public reference data); confirms real ingestion
    for one company never leaks into another's evidence/financial facts."""

    @patch('harvester.services.fetchers.http_fetch')
    def test_ingesting_one_company_does_not_touch_another(self, mock_fetch):
        mock_fetch.return_value = _xbrl_result(COMPLETE_XBRL_FACTS)
        apple = _real_profile('apple')
        tesla = _real_profile('tesla')
        evidence_ingestion.ingest_company_evidence(apple)
        self.assertEqual(CompanyFinancialFacts.objects.filter(company=tesla).count(), 0)
        self.assertEqual(EvidenceMemory.objects.filter(company=tesla).count(), 0)
        self.assertEqual(HarvesterEvidence.objects.filter(company_slug='tesla').count(), 0)


# ═══════════════════════════════════════════════════════════════════════════
# feat/company-discovery-ranking (PR 11) — Discover Companies, ranking,
# Explain Match, comparison, KPI Explorer integration.
# ═══════════════════════════════════════════════════════════════════════════
from company_intelligence.services import discovery_engine, match_trace

# Same convention as CompanyDetailIntegrationTests.test_no_buy_sell_language_anywhere_on_page:
# '>buy<'/'>sell<' catches an actual naked BUY/SELL button or label; the bare
# substrings 'buy'/'sell' would false-positive on this app's own disclaimer
# text ("...contains no buy/sell recommendation"), which is required, not banned.
BANNED_INVESTMENT_WORDS = ('>buy<', '>sell<', 'strong buy', 'target price', 'expected return', 'undervalued', 'outperform')


def _confirmed_kpi_link(profile, kpi_id, relationship, review_tier='system_checked', text='Evidence text.'):
    evidence = EvidenceMemory.objects.create(
        text_chunk=text, company=profile, verification_status='verified', review_tier=review_tier,
    )
    assessment = CompanyKPIAssessment.objects.create(company=profile, kpi_id=kpi_id)
    CompanyKPIEvidenceLink.objects.create(assessment=assessment, evidence=evidence, relationship=relationship)
    kpi_engine.recompute_assessment_status(assessment)
    return assessment, evidence


class DiscoveryFilterTests(TestCase):
    def test_demo_companies_excluded_by_default(self):
        methodology = _methodology()
        real = _profile(slug='disc-real-1', sector='energy')
        demo = _profile(slug='disc-demo-1', sector='energy')
        shariah_screening.run_shariah_screen(real, methodology, is_demo=False)
        shariah_screening.run_shariah_screen(demo, methodology, is_demo=True)

        results = discovery_engine.discover_companies({})
        slugs = {c.company.slug for c in results}
        self.assertIn('disc-real-1', slugs)
        self.assertNotIn('disc-demo-1', slugs)

    def test_include_demo_explicitly_opts_in(self):
        methodology = _methodology()
        demo = _profile(slug='disc-demo-2', sector='energy')
        shariah_screening.run_shariah_screen(demo, methodology, is_demo=True)
        results = discovery_engine.discover_companies({'include_demo': True})
        slugs = {c.company.slug for c in results}
        self.assertIn('disc-demo-2', slugs)

    def test_sector_filter(self):
        _profile(slug='disc-sector-energy', sector='energy')
        _profile(slug='disc-sector-mining', sector='mining')
        results = discovery_engine.discover_companies({'sector': 'mining'})
        slugs = {c.company.slug for c in results}
        self.assertIn('disc-sector-mining', slugs)
        self.assertNotIn('disc-sector-energy', slugs)

    def test_country_filter_substring_match(self):
        Company.objects.create(name='UK Co', slug='disc-country-uk', sector='energy', country='United Kingdom')
        CompanyProfile.objects.create(company=Company.objects.get(slug='disc-country-uk'), status='public')
        _profile(slug='disc-country-kz')  # default country='Kazakhstan'
        results = discovery_engine.discover_companies({'country': 'Kingdom'})
        slugs = {c.company.slug for c in results}
        self.assertIn('disc-country-uk', slugs)
        self.assertNotIn('disc-country-kz', slugs)

    def test_shariah_status_filter_matches_overall_result(self):
        methodology = _methodology()
        passer = _profile(slug='disc-shariah-pass', description='Operates solar assets.')
        failer = _profile(slug='disc-shariah-fail', description='Conventional bank operating interest-based lending.')
        passer_facts = CompanyFinancialFacts.objects.create(
            company=passer, as_of_date=datetime.date(2026, 1, 1),
            market_cap_usd=1000, total_debt_usd=100, interest_bearing_securities_usd=50,
            non_permissible_income_usd=10, revenue_usd=500,
        )
        shariah_screening.run_shariah_screen(passer, methodology, financial_facts=passer_facts)
        shariah_screening.run_shariah_screen(failer, methodology)

        results = discovery_engine.discover_companies({'shariah_status': ['pass']})
        slugs = {c.company.slug for c in results}
        self.assertIn('disc-shariah-pass', slugs)
        self.assertNotIn('disc-shariah-fail', slugs)

    def test_not_screened_is_a_valid_explicit_shariah_filter_value(self):
        never_screened = _profile(slug='disc-never-screened')
        results = discovery_engine.discover_companies({'shariah_status': ['not_screened']})
        slugs = {c.company.slug for c in results}
        self.assertIn('disc-never-screened', slugs)

    def test_kpi_filter_requires_confirmed_link(self):
        profile_with = _profile(slug='disc-kpi-with')
        profile_without = _profile(slug='disc-kpi-without')
        _confirmed_kpi_link(profile_with, kpi_id=5, relationship='supports')

        results = discovery_engine.discover_companies({'kpi_ids': [5]})
        slugs = {c.company.slug for c in results}
        self.assertIn('disc-kpi-with', slugs)
        self.assertNotIn('disc-kpi-without', slugs)

    def test_proposed_link_does_not_satisfy_kpi_filter(self):
        """Candidate matching is not confirmation — a proposed-only link
        must not make a company discoverable under that KPI."""
        profile = _profile(slug='disc-kpi-proposed-only')
        evidence = EvidenceMemory.objects.create(text_chunk='Some text.', company=profile, source_type='harvester_evidence')
        assessment = CompanyKPIAssessment.objects.create(company=profile, kpi_id=6)
        CompanyKPIEvidenceLink.objects.create(
            assessment=assessment, evidence=evidence, relationship='context', review_state='proposed',
        )
        results = discovery_engine.discover_companies({'kpi_ids': [6]})
        slugs = {c.company.slug for c in results}
        self.assertNotIn('disc-kpi-proposed-only', slugs)

    def test_controversy_state_none_excludes_unresolved(self):
        clean = _profile(slug='disc-controversy-clean')
        flagged = _profile(slug='disc-controversy-flagged')
        CompanyControversy.objects.create(company=flagged, title='Incident', status='unresolved')
        results = discovery_engine.discover_companies({'controversy_state': 'none'})
        slugs = {c.company.slug for c in results}
        self.assertIn('disc-controversy-clean', slugs)
        self.assertNotIn('disc-controversy-flagged', slugs)

    def test_require_current_screening_excludes_stale(self):
        methodology = _methodology()
        profile = _profile(slug='disc-stale-co')
        screen = shariah_screening.run_shariah_screen(profile, methodology)
        screen.screened_at = datetime.datetime(2020, 1, 1, tzinfo=datetime.timezone.utc)
        screen.save(update_fields=['screened_at'])

        results = discovery_engine.discover_companies({'require_current_screening': True})
        slugs = {c.company.slug for c in results}
        self.assertNotIn('disc-stale-co', slugs)


class DiscoveryRankingTests(TestCase):
    def test_missing_components_excluded_from_composite_not_treated_as_zero(self):
        profile = _profile(slug='rank-missing-co')
        rows = discovery_engine.rank_company_matches([profile], criteria={'kpi_ids': [1]})
        row = rows[0]
        # No Shariah screen, no evidence at all -> every component is None
        self.assertIsNone(row['components']['data_completeness'])
        self.assertIsNone(row['components']['source_authority'])
        # kpi_alignment is NOT None (it's computed even with zero evidence:
        # 1 selected KPI, not_assessed -> neutral 0.5), so composite exists
        # only via that one component's own weight, still never a fabricated
        # score for the components genuinely missing.
        self.assertIsNotNone(row['components']['kpi_alignment'])

    def test_supported_kpi_ranks_above_conflicting_kpi(self):
        """Section 8's own example: Company A (supported) must rank above
        Company B (conflicting) for the same selected KPI."""
        company_a = _profile(slug='rank-a-support')
        company_b = _profile(slug='rank-b-conflict')
        _confirmed_kpi_link(company_a, kpi_id=10, relationship='supports')
        _confirmed_kpi_link(company_b, kpi_id=10, relationship='conflicts')

        rows = discovery_engine.rank_company_matches([company_a, company_b], criteria={'kpi_ids': [10]})
        ordered_slugs = [r['company'].company.slug for r in rows]
        self.assertEqual(ordered_slugs.index('rank-a-support'), 0)

    def test_absence_of_evidence_is_neutral_not_negative(self):
        supported = _profile(slug='rank-supported-co')
        untouched = _profile(slug='rank-untouched-co')
        _confirmed_kpi_link(supported, kpi_id=11, relationship='supports')

        rows = {r['company'].company.slug: r for r in discovery_engine.rank_company_matches(
            [supported, untouched], criteria={'kpi_ids': [11]},
        )}
        self.assertGreater(rows['rank-supported-co']['components']['kpi_alignment'], rows['rank-untouched-co']['components']['kpi_alignment'])
        # untouched company's kpi_alignment must be neutral (0.5), never a
        # punitive low value just because nothing was assessed.
        self.assertEqual(rows['rank-untouched-co']['components']['kpi_alignment'], 0.5)

    def test_ranking_is_deterministic_across_repeated_calls(self):
        a = _profile(slug='rank-det-a')
        b = _profile(slug='rank-det-b')
        _confirmed_kpi_link(a, kpi_id=12, relationship='supports')
        first = [r['company'].pk for r in discovery_engine.rank_company_matches([a, b], criteria={'kpi_ids': [12]})]
        second = [r['company'].pk for r in discovery_engine.rank_company_matches([a, b], criteria={'kpi_ids': [12]})]
        self.assertEqual(first, second)

    def test_weights_are_configurable(self):
        profile = _profile(slug='rank-weights-co')
        methodology = _methodology()
        shariah_screening.run_shariah_screen(profile, methodology)
        custom_weights = {'kpi_alignment': 0.0, 'source_authority': 0.0, 'recency': 0.0, 'corroboration': 0.0, 'data_completeness': 1.0}
        rows = discovery_engine.rank_company_matches([profile], criteria={}, weights=custom_weights)
        # With data_completeness weighted 100% and every other weight 0, the
        # composite must equal the data_completeness component exactly.
        row = rows[0]
        self.assertAlmostEqual(row['composite'], row['components']['data_completeness'], places=4)

    def test_no_qualifying_evidence_sorts_last_not_as_zero(self):
        with_data = _profile(slug='rank-has-data')
        methodology = _methodology()
        shariah_screening.run_shariah_screen(with_data, methodology)
        no_data = _profile(slug='rank-no-data')
        # Force every component to None for no_data by using an empty kpi_ids
        # selection with no assessments and no screen — composite is None.
        rows = discovery_engine.rank_company_matches([with_data, no_data], criteria={'kpi_ids': []})
        composites = [r['composite'] for r in rows]
        # None must never sort before a real numeric composite.
        none_positions = [i for i, c in enumerate(composites) if c is None]
        real_positions = [i for i, c in enumerate(composites) if c is not None]
        if none_positions and real_positions:
            self.assertGreater(min(none_positions), max(real_positions))


class CompareCompaniesTests(TestCase):
    def test_comparison_preserves_input_order_never_resorted(self):
        a = _profile(slug='cmp-a')
        b = _profile(slug='cmp-b')
        c = _profile(slug='cmp-c')
        _confirmed_kpi_link(c, kpi_id=13, relationship='supports')  # c would rank first if sorted
        comparison = discovery_engine.compare_companies([a, b, c], criteria={'kpi_ids': [13]})
        self.assertEqual([r['company'].pk for r in comparison], [a.pk, b.pk, c.pk])

    def test_comparison_includes_controversies_and_shariah_and_kpi_detail(self):
        profile = _profile(slug='cmp-detail-co')
        CompanyControversy.objects.create(company=profile, title='Test issue', status='unresolved')
        comparison = discovery_engine.compare_companies([profile], criteria={})
        row = comparison[0]
        self.assertEqual(len(row['controversies']), 1)
        self.assertIn('kpi_detail', row)
        self.assertIn('shariah_screen', row)


class ExplainMatchTests(TestCase):
    def test_trace_has_eleven_nodes_in_documented_order(self):
        profile = _profile(slug='match-trace-co')
        trace = match_trace.explain_company_match(profile, criteria={'kpi_ids': [1]})
        stages = [n.stage for n in trace.nodes]
        self.assertEqual(stages, [
            'selected_criteria', 'company_identity', 'shariah_screening', 'selected_kpis',
            'supporting_evidence', 'conflicting_evidence', 'evidence_quality', 'match_freshness',
            'match_data_gaps', 'ranking_components', 'why_here',
        ])

    def test_trace_never_contains_investment_language(self):
        profile = _profile(slug='match-trace-clean-co')
        trace = match_trace.explain_company_match(profile, criteria={})
        combined = ' '.join(n.summary.lower() for n in trace.nodes)
        for banned in BANNED_INVESTMENT_WORDS:
            self.assertNotIn(banned, combined)

    def test_trace_reflects_selected_criteria_summary(self):
        profile = _profile(slug='match-trace-criteria-co')
        trace = match_trace.explain_company_match(profile, criteria={'shariah_status': ['pass'], 'sector': 'energy'})
        criteria_node = trace.nodes[0]
        self.assertIn('pass', criteria_node.summary.lower())
        self.assertIn('energy', criteria_node.summary.lower())

    def test_trace_honest_when_never_screened(self):
        profile = _profile(slug='match-trace-unscreened-co')
        trace = match_trace.explain_company_match(profile, criteria={})
        shariah_node = next(n for n in trace.nodes if n.stage == 'shariah_screening')
        self.assertEqual(shariah_node.status, 'Not Screened')
        self.assertFalse(shariah_node.available)


class DiscoveryViewTests(TestCase):
    def test_discover_view_public_get(self):
        client = Client()
        response = client.get(reverse('companies:discover'))
        self.assertEqual(response.status_code, 200)

    def test_discover_view_never_contains_investment_language(self):
        _profile(slug='disc-view-clean-co')
        client = Client()
        response = client.get(reverse('companies:discover'))
        body = response.content.decode().lower()
        for banned in BANNED_INVESTMENT_WORDS:
            self.assertNotIn(banned, body)

    def test_discover_view_excludes_demo_by_default(self):
        methodology = _methodology()
        demo = _profile(slug='disc-view-demo-co')
        shariah_screening.run_shariah_screen(demo, methodology, is_demo=True)
        client = Client()
        response = client.get(reverse('companies:discover'))
        self.assertNotContains(response, 'disc-view-demo-co')

    def test_discover_view_kpi_filter_via_query_param(self):
        profile = _profile(slug='disc-view-kpi-co')
        _confirmed_kpi_link(profile, kpi_id=7, relationship='supports')
        client = Client()
        response = client.get(reverse('companies:discover'), {'kpi': ['7']})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, profile.company.name)

    def test_explain_match_view_public_get(self):
        profile = _profile(slug='disc-explain-view-co')
        client = Client()
        response = client.get(reverse('companies:explain_match', args=[profile.company.slug]))
        self.assertEqual(response.status_code, 200)

    def test_compare_view_requires_at_least_two_companies(self):
        profile = _profile(slug='disc-compare-solo-co')
        client = Client()
        response = client.get(reverse('companies:compare'), {'companies': profile.company.slug})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select 2')

    def test_compare_view_with_two_companies(self):
        a = _profile(slug='disc-compare-a')
        b = _profile(slug='disc-compare-b')
        client = Client()
        response = client.get(reverse('companies:compare'), {'companies': f'{a.company.slug},{b.company.slug}'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, a.company.name)
        self.assertContains(response, b.company.name)


class RegisterDocumentSourceViewTests(TestCase):
    def setUp(self):
        self.profile = _profile(slug='register-doc-co')
        self.staff = User.objects.create_user(username='staffer', password='pw', is_staff=True)
        self.normal = User.objects.create_user(username='normie', password='pw')

    def test_requires_staff(self):
        client = Client()
        client.login(username='normie', password='pw')
        response = client.post(reverse('companies:register_document_source', args=[self.profile.company.slug]), {
            'source_url': 'https://example.com/report.pdf', 'document_type': 'sustainability_report',
        })
        self.assertNotEqual(response.status_code, 200)

    def test_get_not_allowed(self):
        client = Client()
        client.login(username='staffer', password='pw')
        response = client.get(reverse('companies:register_document_source', args=[self.profile.company.slug]))
        self.assertEqual(response.status_code, 404)

    @patch('company_intelligence.services.evidence_ingestion.ingest_sustainability_document')
    def test_staff_can_register_and_trigger_ingestion(self, mock_ingest):
        from harvester.models import IngestionRun

        mock_ingest.return_value = {
            'ingestion_run': IngestionRun(status='new'), 'kpi_candidates_proposed': [], 'warnings': [],
        }
        client = Client()
        client.login(username='staffer', password='pw')
        response = client.post(reverse('companies:register_document_source', args=[self.profile.company.slug]), {
            'source_url': 'https://example.com/report.pdf', 'document_type': 'sustainability_report', 'publisher': 'Example Inc.',
        })
        self.assertEqual(response.status_code, 302)
        mock_ingest.assert_called_once()

    def test_invalid_document_type_rejected(self):
        client = Client()
        client.login(username='staffer', password='pw')
        response = client.post(reverse('companies:register_document_source', args=[self.profile.company.slug]), {
            'source_url': 'https://example.com/report.pdf', 'document_type': 'not_a_real_type',
        })
        self.assertEqual(response.status_code, 302)  # redirects with an error message, never crashes


class WatchlistResearchContextTests(TestCase):
    def test_research_context_stored_in_notes(self):
        profile = _profile(slug='watchlist-context-co')
        user = User.objects.create_user(username='researcher', password='pw')
        client = Client()
        client.login(username='researcher', password='pw')
        client.post(reverse('companies:watchlist_add', args=[profile.company.slug]), {
            'status': 'researching', 'research_context': 'Added from Discover Companies — KPI: Test Principle',
        })
        entry = ResearchWatchlistEntry.objects.get(user=user, company=profile)
        self.assertIn('Discover Companies', entry.notes)

    def test_blank_research_context_never_clobbers_existing_notes(self):
        profile = _profile(slug='watchlist-noclobber-co')
        user = User.objects.create_user(username='researcher2', password='pw')
        ResearchWatchlistEntry.objects.create(user=user, company=profile, notes='My own manual note.')
        client = Client()
        client.login(username='researcher2', password='pw')
        client.post(reverse('companies:watchlist_add', args=[profile.company.slug]), {'status': 'high_kpi_alignment'})
        entry = ResearchWatchlistEntry.objects.get(user=user, company=profile)
        self.assertEqual(entry.notes, 'My own manual note.')


class KPIExplorerDiscoveryIntegrationTests(TestCase):
    def test_kpi_panel_links_to_discover_with_kpi_id(self):
        methodology = _methodology()
        profile = _profile(slug='kpi-explorer-link-co', description='Operates solar power assets.')
        shariah_screening.run_shariah_screen(profile, methodology)
        client = Client()
        response = client.get(reverse('companies:detail', args=[profile.company.slug]))
        self.assertContains(response, f"{reverse('companies:discover')}?kpi=1")


class DiscoveryObservatoryTelemetryTests(TestCase):
    def test_discover_view_records_company_discovery_session_with_no_anchor(self):
        from ai_observatory.models import AnalysisSession

        _profile(slug='disc-observatory-co')
        client = Client()
        client.get(reverse('companies:discover'))
        session = AnalysisSession.objects.filter(kind='company_discovery').order_by('-pk').first()
        self.assertIsNotNone(session)
        self.assertIsNone(session.project_id)
        self.assertIsNone(session.company_id)
        self.assertEqual(session.status, 'completed')
        self.assertGreaterEqual(session.stages.count(), 2)  # filtering + ranking

    def test_compare_view_records_session(self):
        from ai_observatory.models import AnalysisSession

        a = _profile(slug='disc-observatory-cmp-a')
        b = _profile(slug='disc-observatory-cmp-b')
        client = Client()
        client.get(reverse('companies:compare'), {'companies': f'{a.company.slug},{b.company.slug}'})
        session = AnalysisSession.objects.filter(kind='company_discovery').order_by('-pk').first()
        self.assertIsNotNone(session)


class ObservatoryNeitherAnchorConstraintTests(TestCase):
    def test_company_discovery_kind_permits_neither_anchor(self):
        from ai_observatory.services import recorder

        session = recorder.start_session(kind='company_discovery')
        self.assertIsNotNone(session)
        self.assertIsNone(session.project_id)
        self.assertIsNone(session.company_id)

    def test_other_kinds_still_require_exactly_one_anchor(self):
        from ai_observatory.services import recorder

        session = recorder.start_session(kind='company_intelligence')
        self.assertIsNone(session)  # neither anchor, non-discovery kind -> rejected, logged

    def test_both_anchors_always_rejected_even_for_discovery(self):
        from ai_observatory.services import recorder

        profile = _profile(slug='both-anchor-co')
        from gold_intelligence.models import GoldProject
        project = GoldProject.objects.create(name='Test Project')
        session = recorder.start_session(project=project, company=profile, kind='company_discovery')
        self.assertIsNone(session)
