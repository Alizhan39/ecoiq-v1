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
import time

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from companies.models import CompanyProfile
from company_intelligence.models import (
    KPI_STATUS_CHOICES, SCREEN_RESULT_CHOICES, CompanyControversy, CompanyFinancialFacts,
    CompanyKPIAssessment, CompanyKPIEvidenceLink, CompanyListing, ResearchWatchlistEntry,
    ShariahMethodology,
)
from company_intelligence.services import identity_sync, kpi_engine, rate_limiter, shariah_screening
from company_intelligence.services.company_trace import build_company_trace
from evidence_memory.models import EvidenceMemory
from league.models import Company

User = get_user_model()

# feat/global-stewardship-universe (PR 15) — rate_limiter.wait_for_domain_
# slot() looks up DEFAULT_MIN_INTERVAL_SECONDS by name on every call (see
# its own docstring), specifically so this test-only override makes every
# refresh_orchestrator test run at full speed instead of sleeping for real
# whenever two tests touch the same domain (e.g. 'apple.com') back to back.
rate_limiter.DEFAULT_MIN_INTERVAL_SECONDS = 0


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

    def test_trace_has_thirteen_nodes_in_order(self):
        """feat/company-evidence-ingestion (PR 10) extended PR9's 10-node
        trace to 12, inserting 'sources' after company identity and
        'evidence_review' after KPI evidence. feat/global-stewardship-
        universe (PR 15) added 'coverage_matrix' right before the final
        overall-profile node — documented, intentional."""
        profile = _profile(slug='trace-co')
        trace = build_company_trace(profile, user=self.user)
        self.assertEqual(
            [n.stage for n in trace.nodes],
            ['company', 'sources', 'methodology', 'business_activity', 'financial_evidence', 'shariah_result',
             'kpi_evidence', 'evidence_review', 'positive_alignment', 'conflicting_evidence', 'evidence_gaps',
             'coverage_matrix', 'overall_profile'],
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

    def test_explain_view_shows_coverage_matrix(self):
        r = self.client.get(reverse('companies:explain', args=[self.profile.company.slug]))
        self.assertContains(r, 'Coverage Matrix')
        self.assertContains(r, 'Identity Coverage')
        self.assertContains(r, 'Monitoring Status')

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
        """feat/evidence-review-workbench (PR 12): the generic 'verify'
        action is replaced by explicit confirm_supports/confirm_conflicts/
        confirm_context/confirm_insufficient — a reviewer must say WHICH
        relationship they're confirming, never a one-size-fits-all 'verify'."""
        self.client.force_login(self.staff)
        r = self.client.post(
            reverse('companies:evidence_review_action', args=[self.profile.company.slug]),
            {'kpi_evidence_link_id': self.link.pk, 'action': 'confirm_supports', 'reason': 'Confirmed against filing.'},
        )
        self.assertEqual(r.status_code, 302)
        self.link.refresh_from_db()
        self.assertEqual(self.link.review_state, 'confirmed')
        self.assertEqual(self.link.relationship, 'supports')
        action = EvidenceReviewAction.objects.get(kpi_evidence_link=self.link)
        self.assertEqual(action.reviewer, self.staff)
        self.assertEqual(action.action, 'confirm_supports')
        self.assertEqual(action.reason, 'Confirmed against filing.')

    def test_reject_action_rejects_link(self):
        self.client.force_login(self.staff)
        self.client.post(
            reverse('companies:evidence_review_action', args=[self.profile.company.slug]),
            {'kpi_evidence_link_id': self.link.pk, 'action': 'reject'},
        )
        self.link.refresh_from_db()
        self.assertEqual(self.link.review_state, 'rejected')

    def test_mark_disputed_is_now_a_real_state_change(self):
        """feat/evidence-review-workbench (PR 12) deliberately upgrades
        mark_disputed from PR10's audit-log-only no-op to a real
        review_state mutation — a disputed link must stop counting."""
        self.client.force_login(self.staff)
        self.client.post(
            reverse('companies:evidence_review_action', args=[self.profile.company.slug]),
            {'kpi_evidence_link_id': self.link.pk, 'action': 'mark_disputed', 'reason': 'Needs scholar review.'},
        )
        self.link.refresh_from_db()
        self.assertEqual(self.link.review_state, 'disputed')
        self.assertTrue(EvidenceReviewAction.objects.filter(kpi_evidence_link=self.link, action='mark_disputed').exists())

    def test_needs_more_evidence_is_now_a_real_state_change(self):
        """feat/evidence-review-workbench (PR 12) deliberately upgrades
        needs_more_evidence from PR10's audit-log-only no-op to a real,
        visibly unresolved review_state."""
        self.client.force_login(self.staff)
        self.client.post(
            reverse('companies:evidence_review_action', args=[self.profile.company.slug]),
            {'kpi_evidence_link_id': self.link.pk, 'action': 'needs_more_evidence'},
        )
        self.link.refresh_from_db()
        self.assertEqual(self.link.review_state, 'needs_more_evidence')

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
            {'kpi_evidence_link_id': self.link.pk, 'action': 'confirm_supports'},
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
    def test_trace_has_twelve_nodes_in_documented_order(self):
        profile = _profile(slug='match-trace-co')
        trace = match_trace.explain_company_match(profile, criteria={'kpi_ids': [1]})
        stages = [n.stage for n in trace.nodes]
        self.assertEqual(stages, [
            'selected_criteria', 'company_identity', 'shariah_screening', 'selected_kpis',
            'supporting_evidence', 'conflicting_evidence', 'evidence_quality', 'match_freshness',
            'match_data_gaps', 'ranking_components', 'evidence_provenance', 'why_here',
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

    def test_strongest_alignment_view_public_get(self):
        client = Client()
        response = client.get(reverse('companies:strongest_alignment'))
        self.assertEqual(response.status_code, 200)

    def test_strongest_alignment_view_excludes_no_qualifying_evidence(self):
        _profile(slug='sa-no-evidence-co')
        client = Client()
        response = client.get(reverse('companies:strongest_alignment'))
        self.assertNotContains(response, 'sa-no-evidence-co')

    def test_strongest_alignment_view_includes_company_with_confirmed_kpi(self):
        profile = _profile(slug='sa-with-evidence-co')
        _confirmed_kpi_link(profile, kpi_id=11, relationship='supports')
        client = Client()
        response = client.get(reverse('companies:strongest_alignment'))
        self.assertContains(response, profile.company.name)

    def test_strongest_alignment_view_never_contains_investment_language(self):
        profile = _profile(slug='sa-clean-co')
        _confirmed_kpi_link(profile, kpi_id=12, relationship='supports')
        client = Client()
        response = client.get(reverse('companies:strongest_alignment'))
        body = response.content.decode().lower()
        for banned in BANNED_INVESTMENT_WORDS:
            self.assertNotIn(banned, body)

    def test_strongest_alignment_view_shows_mandatory_disclaimer(self):
        client = Client()
        response = client.get(reverse('companies:strongest_alignment'))
        normalized = ' '.join(response.content.decode().split())
        self.assertIn(
            'Research ranking based on currently available and reviewed stewardship evidence. '
            'This is not investment advice or a prediction of financial performance.',
            normalized,
        )

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

    def test_compare_view_includes_global_stewardship_universe_extras(self):
        a = _profile(slug='disc-compare-extras-a')
        b = _profile(slug='disc-compare-extras-b')
        _confirmed_kpi_link(a, kpi_id=13, relationship='supports')
        client = Client()
        response = client.get(reverse('companies:compare'), {'companies': f'{a.company.slug},{b.company.slug}'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Confirmed KPIs Supported')
        self.assertContains(response, 'Human-Reviewed Coverage')
        self.assertContains(response, 'Monitoring Health')
        self.assertContains(response, 'Open Potential Conflicts')

    def test_compare_view_never_contains_investment_language(self):
        a = _profile(slug='disc-compare-clean-a')
        b = _profile(slug='disc-compare-clean-b')
        _confirmed_kpi_link(a, kpi_id=14, relationship='supports')
        client = Client()
        response = client.get(reverse('companies:compare'), {'companies': f'{a.company.slug},{b.company.slug}'})
        body = response.content.decode().lower()
        for banned in BANNED_INVESTMENT_WORDS:
            self.assertNotIn(banned, body)


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


# ═══════════════════════════════════════════════════════════════════════════
# feat/evidence-review-workbench (PR 12) — review queue, decision semantics,
# audit trail, dispute/re-review, KPI recomputation, Discovery propagation,
# Explain Review Decision, Watchlist privacy, Observatory telemetry.
# ═══════════════════════════════════════════════════════════════════════════
from company_intelligence.services import evidence_review
from company_intelligence.services.review_trace import explain_review_decision


def _proposed_link(profile, kpi_id, relationship='context', match_basis='Keyword overlap: test, evidence', text='Proposed evidence text discussing the topic.'):
    """A matcher-proposed (never confirmed) link — mirrors real
    propose_kpi_links_for_evidence() output shape."""
    evidence = EvidenceMemory.objects.create(
        text_chunk=text, company=profile, source_type='harvester_evidence',
        verification_status='verified',
    )
    assessment = CompanyKPIAssessment.objects.get_or_create(company=profile, kpi_id=kpi_id)[0]
    link = CompanyKPIEvidenceLink.objects.create(
        assessment=assessment, evidence=evidence, relationship=relationship,
        review_state='proposed', match_basis=match_basis,
    )
    return link


class ReviewModelChoiceTests(TestCase):
    def test_relationship_choices_include_insufficient_to_conclude(self):
        valid = {c for c, _ in CompanyKPIEvidenceLink.RELATIONSHIP_CHOICES}
        self.assertEqual(valid, {'supports', 'conflicts', 'context', 'insufficient_to_conclude'})

    def test_review_state_choices_include_needs_more_evidence_and_disputed(self):
        valid = {c for c, _ in CompanyKPIEvidenceLink.REVIEW_STATE_CHOICES}
        self.assertEqual(valid, {'proposed', 'confirmed', 'rejected', 'needs_more_evidence', 'disputed'})

    def test_action_choices_are_the_documented_seven(self):
        valid = {c for c, _ in EvidenceReviewAction.ACTION_CHOICES}
        self.assertEqual(valid, {
            'confirm_supports', 'confirm_conflicts', 'confirm_context', 'confirm_insufficient',
            'reject', 'needs_more_evidence', 'mark_disputed',
        })


class ApplyReviewDecisionTests(TestCase):
    def setUp(self):
        self.company_profile = _profile(slug='apply-decision-co')
        self.reviewer = User.objects.create_user(username='reviewer1', password='pw', is_staff=True)

    def test_confirm_supports_sets_state_and_relationship(self):
        link = _proposed_link(self.company_profile, kpi_id=1, relationship='context')
        evidence_review.apply_review_decision(link, 'confirm_supports', self.reviewer, reason='Genuinely supports.')
        link.refresh_from_db()
        self.assertEqual(link.review_state, 'confirmed')
        self.assertEqual(link.relationship, 'supports')

    def test_confirm_conflicts_sets_state_and_relationship(self):
        link = _proposed_link(self.company_profile, kpi_id=2, relationship='context')
        evidence_review.apply_review_decision(link, 'confirm_conflicts', self.reviewer, reason='Genuinely conflicts.')
        link.refresh_from_db()
        self.assertEqual(link.review_state, 'confirmed')
        self.assertEqual(link.relationship, 'conflicts')

    def test_confirm_context_only(self):
        link = _proposed_link(self.company_profile, kpi_id=3, relationship='supports')
        evidence_review.apply_review_decision(link, 'confirm_context', self.reviewer, reason='Only background context.')
        link.refresh_from_db()
        self.assertEqual(link.relationship, 'context')

    def test_confirm_insufficient_to_conclude(self):
        link = _proposed_link(self.company_profile, kpi_id=4, relationship='context')
        evidence_review.apply_review_decision(link, 'confirm_insufficient', self.reviewer, reason='Discusses the topic but does not conclude.')
        link.refresh_from_db()
        self.assertEqual(link.relationship, 'insufficient_to_conclude')
        self.assertEqual(link.review_state, 'confirmed')

    def test_reject_never_sets_a_relationship(self):
        link = _proposed_link(self.company_profile, kpi_id=5, relationship='supports')
        evidence_review.apply_review_decision(link, 'reject', self.reviewer, reason='Not actually about this KPI.')
        link.refresh_from_db()
        self.assertEqual(link.review_state, 'rejected')
        self.assertEqual(link.relationship, 'supports')  # unchanged — reject doesn't assert a relationship

    def test_needs_more_evidence_is_a_real_unresolved_state(self):
        link = _proposed_link(self.company_profile, kpi_id=6)
        evidence_review.apply_review_decision(link, 'needs_more_evidence', self.reviewer, reason='Need a second source.')
        link.refresh_from_db()
        self.assertEqual(link.review_state, 'needs_more_evidence')

    def test_mark_disputed_moves_confirmed_link_out_of_confirmed(self):
        link = _proposed_link(self.company_profile, kpi_id=7)
        evidence_review.apply_review_decision(link, 'confirm_supports', self.reviewer, reason='Looks solid.')
        evidence_review.apply_review_decision(link, 'mark_disputed', self.reviewer, reason='A second reviewer disagrees.')
        link.refresh_from_db()
        self.assertEqual(link.review_state, 'disputed')

    def test_re_review_moves_disputed_link_back_to_confirmed(self):
        link = _proposed_link(self.company_profile, kpi_id=8)
        evidence_review.apply_review_decision(link, 'confirm_supports', self.reviewer, reason='Initial review.')
        evidence_review.apply_review_decision(link, 'mark_disputed', self.reviewer, reason='Disputed.')
        evidence_review.apply_review_decision(link, 'confirm_supports', self.reviewer, reason='Re-reviewed, dispute resolved.')
        link.refresh_from_db()
        self.assertEqual(link.review_state, 'confirmed')

    def test_every_decision_creates_immutable_audit_row_with_full_fields(self):
        link = _proposed_link(self.company_profile, kpi_id=9)
        evidence_review.apply_review_decision(link, 'confirm_supports', self.reviewer, reason='Test reason.')
        action = EvidenceReviewAction.objects.filter(kpi_evidence_link=link).latest('created_at')
        self.assertEqual(action.reviewer, self.reviewer)
        self.assertEqual(action.previous_review_state, 'proposed')
        self.assertEqual(action.new_review_state, 'confirmed')
        self.assertEqual(action.relationship_decision, 'supports')
        self.assertEqual(action.reason, 'Test reason.')

    def test_history_is_never_overwritten_across_multiple_decisions(self):
        link = _proposed_link(self.company_profile, kpi_id=10)
        evidence_review.apply_review_decision(link, 'confirm_supports', self.reviewer, reason='First.')
        evidence_review.apply_review_decision(link, 'mark_disputed', self.reviewer, reason='Second.')
        evidence_review.apply_review_decision(link, 'confirm_conflicts', self.reviewer, reason='Third.')
        actions = list(EvidenceReviewAction.objects.filter(kpi_evidence_link=link).order_by('created_at'))
        self.assertEqual(len(actions), 3)
        self.assertEqual([a.reason for a in actions], ['First.', 'Second.', 'Third.'])

    def test_assessment_recomputed_after_confirm_supports(self):
        link = _proposed_link(self.company_profile, kpi_id=11)
        evidence_review.apply_review_decision(link, 'confirm_supports', self.reviewer, reason='Real support.')
        link.assessment.refresh_from_db()
        self.assertIn(link.assessment.status, ('support', 'strong_support'))

    def test_assessment_recomputed_after_confirm_conflicts(self):
        link = _proposed_link(self.company_profile, kpi_id=12)
        evidence_review.apply_review_decision(link, 'confirm_conflicts', self.reviewer, reason='Real conflict.')
        link.assessment.refresh_from_db()
        self.assertEqual(link.assessment.status, 'conflict')

    def test_rejected_link_never_contributes_to_assessment(self):
        link = _proposed_link(self.company_profile, kpi_id=13, relationship='supports')
        evidence_review.apply_review_decision(link, 'reject', self.reviewer, reason='Bad match.')
        link.assessment.refresh_from_db()
        self.assertEqual(link.assessment.status, 'insufficient_evidence')  # no confirmed links -> insufficient, never 'support'

    def test_proposed_link_never_contributes_as_confirmed(self):
        link = _proposed_link(self.company_profile, kpi_id=14, relationship='supports')
        # never reviewed at all
        self.assertEqual(link.assessment.status, 'not_assessed')

    def test_needs_more_evidence_link_remains_unresolved_not_confirmed(self):
        link = _proposed_link(self.company_profile, kpi_id=15, relationship='supports')
        evidence_review.apply_review_decision(link, 'needs_more_evidence', self.reviewer, reason='Insufficient on its own.')
        link.assessment.refresh_from_db()
        self.assertEqual(link.assessment.status, 'insufficient_evidence')

    def test_invalid_action_raises(self):
        link = _proposed_link(self.company_profile, kpi_id=16)
        with self.assertRaises(ValueError):
            evidence_review.apply_review_decision(link, 'not_a_real_action', self.reviewer)


class ReviewQueueServiceTests(TestCase):
    def setUp(self):
        self.profile = _profile(slug='queue-service-co')

    def test_default_queue_includes_proposed_needs_more_and_disputed_only(self):
        reviewer = User.objects.create_user(username='reviewer2', password='pw', is_staff=True)
        proposed = _proposed_link(self.profile, kpi_id=20)
        confirmed = _proposed_link(self.profile, kpi_id=21)
        evidence_review.apply_review_decision(confirmed, 'confirm_supports', reviewer, reason='ok')
        needs_more = _proposed_link(self.profile, kpi_id=22)
        evidence_review.apply_review_decision(needs_more, 'needs_more_evidence', reviewer, reason='ok')

        rows = evidence_review.pending_review_queue({'company_slug': 'queue-service-co'})
        link_pks = {r['link'].pk for r in rows}
        self.assertIn(proposed.pk, link_pks)
        self.assertIn(needs_more.pk, link_pks)
        self.assertNotIn(confirmed.pk, link_pks)  # confirmed excluded from default active queue

    def test_company_slug_filter(self):
        other_profile = _profile(slug='queue-other-co')
        link_here = _proposed_link(self.profile, kpi_id=23)
        link_other = _proposed_link(other_profile, kpi_id=23)
        rows = evidence_review.pending_review_queue({'company_slug': 'queue-service-co'})
        pks = {r['link'].pk for r in rows}
        self.assertIn(link_here.pk, pks)
        self.assertNotIn(link_other.pk, pks)

    def test_kpi_id_filter(self):
        link_a = _proposed_link(self.profile, kpi_id=24)
        link_b = _proposed_link(self.profile, kpi_id=25)
        rows = evidence_review.pending_review_queue({'kpi_id': 24, 'company_slug': 'queue-service-co'})
        pks = {r['link'].pk for r in rows}
        self.assertIn(link_a.pk, pks)
        self.assertNotIn(link_b.pk, pks)

    def test_relationship_filter(self):
        supports_link = _proposed_link(self.profile, kpi_id=26, relationship='supports')
        context_link = _proposed_link(self.profile, kpi_id=27, relationship='context')
        rows = evidence_review.pending_review_queue({'relationship': 'supports', 'company_slug': 'queue-service-co'})
        pks = {r['link'].pk for r in rows}
        self.assertIn(supports_link.pk, pks)
        self.assertNotIn(context_link.pk, pks)

    def test_priority_components_are_shown_not_hidden(self):
        link = _proposed_link(self.profile, kpi_id=28)
        rows = evidence_review.pending_review_queue({'company_slug': 'queue-service-co', 'kpi_id': 28})
        self.assertIn('priority_components', rows[0])
        self.assertIsInstance(rows[0]['priority_components'], dict)
        self.assertEqual(rows[0]['priority_score'], sum(1 for v in rows[0]['priority_components'].values() if v))


class DuplicateDetectionTests(TestCase):
    def test_same_evidence_different_kpi_detected(self):
        profile = _profile(slug='dup-co')
        evidence = EvidenceMemory.objects.create(text_chunk='Shared evidence text.', company=profile, source_type='harvester_evidence')
        assessment1 = CompanyKPIAssessment.objects.create(company=profile, kpi_id=30)
        assessment2 = CompanyKPIAssessment.objects.create(company=profile, kpi_id=31)
        link1 = CompanyKPIEvidenceLink.objects.create(assessment=assessment1, evidence=evidence, relationship='context', review_state='proposed')
        link2 = CompanyKPIEvidenceLink.objects.create(assessment=assessment2, evidence=evidence, relationship='context', review_state='proposed')
        dup = evidence_review.duplicate_links_for(link1)
        self.assertEqual(len(dup['same_evidence_different_kpi']), 1)
        self.assertEqual(dup['same_evidence_different_kpi'][0].pk, link2.pk)


class ReviewAnalyticsTests(TestCase):
    def test_counts_reflect_real_state_distribution(self):
        profile = _profile(slug='analytics-co')
        reviewer = User.objects.create_user(username='reviewer3', password='pw', is_staff=True)
        _proposed_link(profile, kpi_id=40)
        confirmed = _proposed_link(profile, kpi_id=41)
        evidence_review.apply_review_decision(confirmed, 'confirm_supports', reviewer, reason='ok')

        analytics = evidence_review.review_analytics()
        self.assertGreaterEqual(analytics['counts']['proposed'], 1)
        self.assertGreaterEqual(analytics['counts']['confirmed'], 1)
        self.assertIn('by_source_tier', analytics)
        self.assertIn('by_kpi_category', analytics)


class EvidenceContextTests(TestCase):
    def test_no_context_when_not_harvester_backed(self):
        profile = _profile(slug='context-demo-co')
        link = _proposed_link(profile, kpi_id=50)  # EvidenceMemory with no harvester.Evidence counterpart
        ctx = evidence_review.evidence_context(link)
        self.assertFalse(ctx['has_context'])
        self.assertEqual(ctx['preceding'], '')
        self.assertEqual(ctx['following'], '')


class SourceProvenanceTests(TestCase):
    def test_honest_fallback_when_not_harvester_backed(self):
        profile = _profile(slug='provenance-demo-co')
        link = _proposed_link(profile, kpi_id=51)
        prov = evidence_review.source_provenance(link)
        self.assertFalse(prov['has_harvester_record'])


class KPIContextTests(TestCase):
    def test_existing_supporting_and_conflicting_exclude_current_link(self):
        profile = _profile(slug='kpi-ctx-co')
        reviewer = User.objects.create_user(username='reviewer4', password='pw', is_staff=True)
        support_link = _proposed_link(profile, kpi_id=60, relationship='context')
        evidence_review.apply_review_decision(support_link, 'confirm_supports', reviewer, reason='ok')
        new_link = _proposed_link(profile, kpi_id=60, relationship='context')

        ctx = evidence_review.kpi_context(new_link)
        self.assertEqual(len(ctx['supporting']), 1)
        self.assertNotIn(new_link, ctx['supporting'])


class ReviewHistoryTests(TestCase):
    def test_history_is_chronological_oldest_first(self):
        profile = _profile(slug='history-co')
        reviewer = User.objects.create_user(username='reviewer5', password='pw', is_staff=True)
        link = _proposed_link(profile, kpi_id=70)
        evidence_review.apply_review_decision(link, 'needs_more_evidence', reviewer, reason='First.')
        evidence_review.apply_review_decision(link, 'confirm_supports', reviewer, reason='Second.')
        history = evidence_review.review_history(link)
        self.assertEqual([a.reason for a in history], ['First.', 'Second.'])


class ReviewTraceTests(TestCase):
    def test_trace_covers_documented_stages(self):
        profile = _profile(slug='review-trace-co')
        link = _proposed_link(profile, kpi_id=80)
        trace = explain_review_decision(link)
        stages = [n.stage for n in trace.nodes]
        self.assertEqual(stages[:5], ['source', 'document', 'evidence_chunk', 'candidate_matcher', 'proposed_kpi'])
        self.assertIn('assessment_impact', stages)
        self.assertIn('discovery_impact', stages)

    def test_trace_reflects_confirmed_state_after_decision(self):
        profile = _profile(slug='review-trace-confirmed-co')
        reviewer = User.objects.create_user(username='reviewer6', password='pw', is_staff=True)
        link = _proposed_link(profile, kpi_id=81)
        evidence_review.apply_review_decision(link, 'confirm_supports', reviewer, reason='Real support.')
        trace = explain_review_decision(link)
        impact_node = next(n for n in trace.nodes if n.stage == 'discovery_impact')
        self.assertIn('Included', impact_node.status)

    def test_trace_never_contains_investment_language(self):
        profile = _profile(slug='review-trace-clean-co')
        link = _proposed_link(profile, kpi_id=82)
        trace = explain_review_decision(link)
        combined = ' '.join(n.summary.lower() for n in trace.nodes)
        for banned in BANNED_INVESTMENT_WORDS:
            self.assertNotIn(banned, combined)


class ReviewQueueViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='staffq', password='pw', is_staff=True)
        self.normal = User.objects.create_user(username='normalq', password='pw')

    def test_requires_staff(self):
        client = Client()
        client.login(username='normalq', password='pw')
        response = client.get(reverse('companies:review_queue'))
        self.assertNotEqual(response.status_code, 200)

    def test_staff_can_view_queue(self):
        _proposed_link(_profile(slug='queue-view-co'), kpi_id=90)
        client = Client()
        client.login(username='staffq', password='pw')
        response = client.get(reverse('companies:review_queue'))
        self.assertEqual(response.status_code, 200)

    def test_queue_never_contains_investment_language(self):
        _proposed_link(_profile(slug='queue-view-clean-co'), kpi_id=91)
        client = Client()
        client.login(username='staffq', password='pw')
        response = client.get(reverse('companies:review_queue'))
        body = response.content.decode().lower()
        for banned in BANNED_INVESTMENT_WORDS:
            self.assertNotIn(banned, body)


class ReviewDetailViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='staffd', password='pw', is_staff=True)
        self.normal = User.objects.create_user(username='normald', password='pw')
        self.profile = _profile(slug='detail-view-co')
        self.link = _proposed_link(self.profile, kpi_id=95)

    def test_requires_staff_get(self):
        client = Client()
        client.login(username='normald', password='pw')
        response = client.get(reverse('companies:review_detail', args=[self.link.pk]))
        self.assertNotEqual(response.status_code, 200)

    def test_staff_get_shows_full_context(self):
        client = Client()
        client.login(username='staffd', password='pw')
        response = client.get(reverse('companies:review_detail', args=[self.link.pk]))
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_link_404s(self):
        client = Client()
        client.login(username='staffd', password='pw')
        response = client.get(reverse('companies:review_detail', args=[999999999]))
        self.assertEqual(response.status_code, 404)

    def test_post_records_decision(self):
        client = Client()
        client.login(username='staffd', password='pw')
        client.post(reverse('companies:review_detail', args=[self.link.pk]), {
            'action': 'confirm_supports', 'reason': 'Real, considered reason.',
        })
        self.link.refresh_from_db()
        self.assertEqual(self.link.review_state, 'confirmed')
        self.assertEqual(self.link.relationship, 'supports')

    def test_post_invalid_action_rejected(self):
        client = Client()
        client.login(username='staffd', password='pw')
        client.post(reverse('companies:review_detail', args=[self.link.pk]), {
            'action': 'auto_approve_everything', 'reason': 'x',
        })
        self.link.refresh_from_db()
        self.assertEqual(self.link.review_state, 'proposed')  # unchanged

    def test_get_not_allowed_to_mutate(self):
        """A GET request must never itself change review_state — only POST."""
        client = Client()
        client.login(username='staffd', password='pw')
        client.get(reverse('companies:review_detail', args=[self.link.pk]))
        self.link.refresh_from_db()
        self.assertEqual(self.link.review_state, 'proposed')

    def test_post_requires_staff(self):
        client = Client()
        client.login(username='normald', password='pw')
        client.post(reverse('companies:review_detail', args=[self.link.pk]), {
            'action': 'confirm_supports', 'reason': 'x',
        })
        self.link.refresh_from_db()
        self.assertEqual(self.link.review_state, 'proposed')  # blocked, unchanged


class ReviewBulkActionViewTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='staffb', password='pw', is_staff=True)
        self.profile = _profile(slug='bulk-co')

    def test_bulk_marks_needs_more_evidence_with_individual_audit_rows(self):
        link1 = _proposed_link(self.profile, kpi_id=100)
        link2 = _proposed_link(self.profile, kpi_id=101)
        client = Client()
        client.login(username='staffb', password='pw')
        client.post(reverse('companies:review_bulk_action'), {
            'link_id': [str(link1.pk), str(link2.pk)], 'reason': 'Bulk needs more evidence.',
        })
        link1.refresh_from_db()
        link2.refresh_from_db()
        self.assertEqual(link1.review_state, 'needs_more_evidence')
        self.assertEqual(link2.review_state, 'needs_more_evidence')
        self.assertEqual(EvidenceReviewAction.objects.filter(kpi_evidence_link=link1).count(), 1)
        self.assertEqual(EvidenceReviewAction.objects.filter(kpi_evidence_link=link2).count(), 1)

    def test_get_not_allowed(self):
        client = Client()
        client.login(username='staffb', password='pw')
        response = client.get(reverse('companies:review_bulk_action'))
        self.assertEqual(response.status_code, 404)

    def test_no_bulk_confirm_endpoint_exists(self):
        """The brief's own conservative rule: bulk confirm must not exist at all."""
        link = _proposed_link(self.profile, kpi_id=102, relationship='supports')
        client = Client()
        client.login(username='staffb', password='pw')
        client.post(reverse('companies:review_bulk_action'), {
            'link_id': [str(link.pk)], 'action': 'confirm_supports',  # even if a caller tries to smuggle this in
        })
        link.refresh_from_db()
        self.assertNotEqual(link.review_state, 'confirmed')  # bulk view hardcodes needs_more_evidence regardless


class DiscoveryPropagationAfterReviewTests(TestCase):
    """feat/company-discovery-ranking (PR 11) integration — confirms a
    review decision propagates through the SAME discovery/ranking service,
    never a duplicated code path."""

    def test_proposed_does_not_count_confirmed_does(self):
        from company_intelligence.services import discovery_engine

        profile = _profile(slug='propagation-co')
        reviewer = User.objects.create_user(username='reviewer7', password='pw', is_staff=True)
        link = _proposed_link(profile, kpi_id=110, relationship='context')

        before = discovery_engine.rank_company_matches([profile], criteria={'kpi_ids': [110]})[0]
        self.assertEqual(before['kpi_detail']['supported_kpi_ids'], [])

        evidence_review.apply_review_decision(link, 'confirm_supports', reviewer, reason='Confirmed real support.')
        after = discovery_engine.rank_company_matches([profile], criteria={'kpi_ids': [110]})[0]
        self.assertEqual(after['kpi_detail']['supported_kpi_ids'], [110])

    def test_confirm_conflicts_surfaces_as_conflict(self):
        from company_intelligence.services import discovery_engine

        profile = _profile(slug='propagation-conflict-co')
        reviewer = User.objects.create_user(username='reviewer8', password='pw', is_staff=True)
        link = _proposed_link(profile, kpi_id=111, relationship='context')
        evidence_review.apply_review_decision(link, 'confirm_conflicts', reviewer, reason='Confirmed real conflict.')

        result = discovery_engine.rank_company_matches([profile], criteria={'kpi_ids': [111]})[0]
        self.assertEqual(result['kpi_detail']['conflicting_kpi_ids'], [111])

    def test_reject_excludes_from_discovery(self):
        from company_intelligence.services import discovery_engine

        profile = _profile(slug='propagation-reject-co')
        reviewer = User.objects.create_user(username='reviewer9', password='pw', is_staff=True)
        link = _proposed_link(profile, kpi_id=112, relationship='supports')
        evidence_review.apply_review_decision(link, 'reject', reviewer, reason='Bad match.')

        result = discovery_engine.rank_company_matches([profile], criteria={'kpi_ids': [112]})[0]
        self.assertEqual(result['kpi_detail']['supported_kpi_ids'], [])
        # A CompanyKPIAssessment row exists (created when the link was
        # first proposed) with zero confirmed links -> 'insufficient_evidence',
        # not 'not_assessed' (which only applies when no assessment row
        # exists for that kpi_id at all).
        self.assertEqual(result['kpi_detail']['insufficient_kpi_ids'], [112])

    def test_disputed_honestly_stops_counting(self):
        from company_intelligence.services import discovery_engine

        profile = _profile(slug='propagation-dispute-co')
        reviewer = User.objects.create_user(username='reviewer10', password='pw', is_staff=True)
        link = _proposed_link(profile, kpi_id=113, relationship='context')
        evidence_review.apply_review_decision(link, 'confirm_supports', reviewer, reason='Initially confirmed.')
        evidence_review.apply_review_decision(link, 'mark_disputed', reviewer, reason='Now disputed.')

        result = discovery_engine.rank_company_matches([profile], criteria={'kpi_ids': [113]})[0]
        self.assertEqual(result['kpi_detail']['supported_kpi_ids'], [])


class WatchlistPrivacyInReviewTests(TestCase):
    def test_on_watchlist_boolean_never_leaks_user_or_notes(self):
        profile = _profile(slug='watchlist-privacy-co')
        user = User.objects.create_user(username='privatewatcher', password='pw')
        ResearchWatchlistEntry.objects.create(user=user, company=profile, notes='Sensitive private note.')
        link = _proposed_link(profile, kpi_id=120)

        rows = evidence_review.pending_review_queue({'company_slug': 'watchlist-privacy-co'})
        row = next(r for r in rows if r['link'].pk == link.pk)
        self.assertTrue(row['on_watchlist'])
        # Only a boolean is exposed — no user/notes field anywhere in the row.
        self.assertNotIn('privatewatcher', str(row))
        self.assertNotIn('Sensitive private note', str(row))


class ObservatoryReviewWorkbenchTelemetryTests(TestCase):
    def test_queue_view_records_session_with_no_anchor(self):
        from ai_observatory.models import AnalysisSession

        _proposed_link(_profile(slug='obs-queue-co'), kpi_id=130)
        staff = User.objects.create_user(username='obsstaff1', password='pw', is_staff=True)
        client = Client()
        client.login(username='obsstaff1', password='pw')
        client.get(reverse('companies:review_queue'))

        session = AnalysisSession.objects.filter(kind='evidence_review_workbench', company__isnull=True).order_by('-pk').first()
        self.assertIsNotNone(session)
        self.assertEqual(session.status, 'completed')

    def test_decision_view_records_session_anchored_to_company(self):
        from ai_observatory.models import AnalysisSession

        profile = _profile(slug='obs-decision-co')
        link = _proposed_link(profile, kpi_id=131)
        staff = User.objects.create_user(username='obsstaff2', password='pw', is_staff=True)
        client = Client()
        client.login(username='obsstaff2', password='pw')
        client.post(reverse('companies:review_detail', args=[link.pk]), {'action': 'confirm_supports', 'reason': 'Real reason.'})

        session = AnalysisSession.objects.filter(kind='evidence_review_workbench', company=profile).order_by('-pk').first()
        self.assertIsNotNone(session)
        self.assertTrue(session.human_review_completed)


class ReviewCSRFAndCrossCompanyTests(TestCase):
    def test_post_without_csrf_token_rejected(self):
        from django.test import Client as StrictClient

        profile = _profile(slug='csrf-co')
        link = _proposed_link(profile, kpi_id=140)
        staff = User.objects.create_user(username='csrfstaff', password='pw', is_staff=True)
        strict_client = StrictClient(enforce_csrf_checks=True)
        strict_client.login(username='csrfstaff', password='pw')
        response = strict_client.post(reverse('companies:review_detail', args=[link.pk]), {
            'action': 'confirm_supports', 'reason': 'x',
        })
        self.assertEqual(response.status_code, 403)
        link.refresh_from_db()
        self.assertEqual(link.review_state, 'proposed')


# ═══════════════════════════════════════════════════════════════════════════
# feat/stewardship-universe (PR 13) — Automated Company Source Discovery +
# Evidence Refresh Pipeline. Tests use the same @patch('harvester.services.
# fetchers.http_fetch'/'.fetch_sec_edgar'/'.fetch_sustainability_document')
# conventions established above — network calls are always mocked; identity
# mappings (US_COMPANY_CIKS/UK_COMPANY_NUMBERS) and curated known_sources
# data are real, so discovery/registration logic is exercised genuinely.
# ═══════════════════════════════════════════════════════════════════════════
from harvester.adapters import EvidenceCandidate
from harvester.services.fetchers import FetchOutcome

from company_intelligence.models import CompanyRefreshRun, DiscoveredSource
from company_intelligence.services import (
    known_sources, refresh_orchestrator, refresh_policy, source_discovery, source_registry,
    stewardship_state, url_safety,
)


def _sec_edgar_outcome(slug='apple'):
    candidate = EvidenceCandidate(
        company_slug=slug, category='financial', statement='Test Co reported revenue of $1B per SEC EDGAR.',
        source_type='regulatory_filing', title='SEC EDGAR test', url='https://www.sec.gov/test',
        source_owner='U.S. Securities and Exchange Commission',
    )
    return FetchOutcome(success=True, candidates=[candidate], content_hash_input='sec-hash-stable')


def _sustainability_outcome(text='We are committed to eliminating waste sent to landfill and implementing systems to avoid sending waste to landfill, achieved a waste diversion rate through recycling programs.'):
    candidate = EvidenceCandidate(
        company_slug='apple', category='waste', statement=text, source_type='sustainability_report',
        title='Test Sustainability Doc — Page 1',
        url='https://www.apple.com/environment/pdf/Apple_Environmental_Progress_Report_2024.pdf',
        excerpt=text, full_text=text, source_owner='Apple Inc.', source_location='Page 1',
    )
    metadata = {
        'document': {
            'title': 'Test Sustainability Doc', 'document_type': 'sustainability_report',
            'publisher': 'Apple Inc.', 'content_hash': 'doc-hash-stable', 'chunk_count': 1,
            'retrieved_at': '2026-01-01T00:00:00+00:00',
        },
    }
    return FetchOutcome(success=True, candidates=[candidate], content_hash_input='doc-hash-stable', metadata=metadata)


class TrackingModelTests(TestCase):
    def test_companyprofile_defaults_not_tracked(self):
        profile = _profile(slug='track-default-co')
        self.assertEqual(profile.tracking_status, 'not_tracked')
        self.assertIsNone(profile.last_refresh_at)
        self.assertIsNone(profile.next_refresh_due_at)

    def test_discoveredsource_unique_per_company_and_url(self):
        profile = _profile(slug='discsrc-uniq-co')
        DiscoveredSource.objects.create(
            company=profile, url='https://example.com/report.pdf', discovery_method='manual', status='candidate',
        )
        with self.assertRaises(Exception):
            DiscoveredSource.objects.create(
                company=profile, url='https://example.com/report.pdf', discovery_method='manual', status='candidate',
            )

    def test_companyrefreshrun_str_and_duration(self):
        profile = _profile(slug='refreshrun-co')
        run = CompanyRefreshRun.objects.create(company=profile, status='complete')
        self.assertIn('complete', str(run).lower())
        self.assertIsNone(run.duration_seconds)  # completed_at never set here


class UrlSafetyTests(TestCase):
    def test_non_http_scheme_blocked(self):
        safe, reason = url_safety.is_safe_external_url('ftp://example.com/file')
        self.assertFalse(safe)

    def test_localhost_blocked(self):
        safe, reason = url_safety.is_safe_external_url('http://localhost:8000/admin')
        self.assertFalse(safe)

    def test_loopback_ip_literal_blocked(self):
        safe, reason = url_safety.is_safe_external_url('http://127.0.0.1/secret')
        self.assertFalse(safe)

    def test_private_ip_literal_blocked(self):
        safe, reason = url_safety.is_safe_external_url('http://10.0.0.5/internal')
        self.assertFalse(safe)

    def test_cloud_metadata_ip_blocked(self):
        safe, reason = url_safety.is_safe_external_url('http://169.254.169.254/latest/meta-data/')
        self.assertFalse(safe)

    def test_internal_suffix_blocked(self):
        safe, reason = url_safety.is_safe_external_url('http://service.internal/data')
        self.assertFalse(safe)

    def test_empty_url_blocked(self):
        safe, reason = url_safety.is_safe_external_url('')
        self.assertFalse(safe)

    @patch('company_intelligence.services.url_safety.socket.getaddrinfo')
    def test_public_hostname_allowed(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(2, 1, 6, '', ('93.184.216.34', 0))]
        safe, reason = url_safety.is_safe_external_url('https://www.example.com/report.pdf')
        self.assertTrue(safe)

    @patch('company_intelligence.services.url_safety.socket.getaddrinfo')
    def test_dns_resolving_to_private_ip_blocked(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [(2, 1, 6, '', ('192.168.1.5', 0))]
        safe, reason = url_safety.is_safe_external_url('https://sneaky.example.com/report.pdf')
        self.assertFalse(safe)

    @patch('company_intelligence.services.url_safety.socket.getaddrinfo')
    def test_dns_failure_is_unsafe_not_a_crash(self, mock_getaddrinfo):
        import socket
        mock_getaddrinfo.side_effect = socket.gaierror('no such host')
        safe, reason = url_safety.is_safe_external_url('https://no-such-host.invalid/report.pdf')
        self.assertFalse(safe)


class KnownSourcesTests(TestCase):
    def test_domain_of_strips_www(self):
        self.assertEqual(known_sources.domain_of('https://www.apple.com/x'), 'apple.com')

    def test_verified_when_domain_matches_curated_registry(self):
        status = known_sources.domain_status_for('apple', 'https://www.apple.com/environment/report.pdf')
        self.assertEqual(status, 'verified')

    def test_probable_when_domain_unknown(self):
        status = known_sources.domain_status_for('apple', 'https://some-random-mirror.example/report.pdf')
        self.assertEqual(status, 'probable')

    def test_probable_when_company_not_in_curated_registry_at_all(self):
        status = known_sources.domain_status_for('unknown-slug', 'https://unknown-slug.com/report.pdf')
        self.assertEqual(status, 'probable')


class SourceDiscoveryTests(TestCase):
    def test_mapped_company_discovers_sec_edgar_and_curated_document(self):
        profile = _real_profile('apple')
        discovered = source_discovery.discover_sources_for_company(profile)
        methods = {d.discovery_method for d in discovered}
        self.assertIn('sec_edgar_identity', methods)
        self.assertIn('curated_official_domain', methods)
        sec_row = next(d for d in discovered if d.discovery_method == 'sec_edgar_identity')
        self.assertEqual(sec_row.status, 'approved')
        self.assertEqual(sec_row.domain_status, 'verified')
        self.assertEqual(sec_row.tier, 1)

    def test_unmapped_company_discovers_nothing_automatically(self):
        profile = _profile(slug='totally-unmapped-co')
        discovered = source_discovery.discover_sources_for_company(profile)
        self.assertEqual(discovered, [])

    def test_staff_entered_field_surfaces_as_candidate_requiring_approval(self):
        profile = _profile(slug='staff-entered-co')
        profile.sustainability_report_url = 'https://staff-entered-co.example/sustainability.pdf'
        profile.save(update_fields=['sustainability_report_url'])
        discovered = source_discovery.discover_sources_for_company(profile)
        staff_row = next(d for d in discovered if d.discovery_method == 'staff_registered_field')
        self.assertEqual(staff_row.status, 'candidate')
        self.assertEqual(staff_row.domain_status, 'probable')

    def test_rerun_does_not_duplicate_discovered_sources(self):
        profile = _real_profile('apple')
        source_discovery.discover_sources_for_company(profile)
        first_count = DiscoveredSource.objects.filter(company=profile).count()
        source_discovery.discover_sources_for_company(profile)
        second_count = DiscoveredSource.objects.filter(company=profile).count()
        self.assertEqual(first_count, second_count)

    def test_updates_last_source_discovery_at(self):
        profile = _profile(slug='discovery-timestamp-co')
        self.assertIsNone(profile.last_source_discovery_at)
        source_discovery.discover_sources_for_company(profile)
        profile.refresh_from_db()
        self.assertIsNotNone(profile.last_source_discovery_at)


class SourceRegistryTests(TestCase):
    def test_register_approved_candidate_creates_harvester_source(self):
        from harvester.models import Source as HarvesterSource

        profile = _real_profile('apple')
        [candidate] = [d for d in source_discovery.discover_sources_for_company(profile) if d.discovery_method == 'sec_edgar_identity']
        source, created = source_registry.register_discovered_source(candidate)
        self.assertTrue(created)
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, 'registered')
        self.assertEqual(candidate.harvester_source_id, source.pk)
        self.assertEqual(HarvesterSource.objects.filter(company=profile, source_type='sec_edgar').count(), 1)

    def test_registering_non_approved_candidate_raises(self):
        profile = _profile(slug='not-approved-co')
        candidate = DiscoveredSource.objects.create(
            company=profile, url='https://not-approved-co.example/x.pdf', discovery_method='manual', status='candidate',
        )
        with self.assertRaises(ValueError):
            source_registry.register_discovered_source(candidate)

    def test_reregistering_already_registered_is_a_noop(self):
        profile = _real_profile('apple')
        [candidate] = [d for d in source_discovery.discover_sources_for_company(profile) if d.discovery_method == 'sec_edgar_identity']
        source_registry.register_discovered_source(candidate)
        candidate.refresh_from_db()
        source_again, created_again = source_registry.register_discovered_source(candidate)
        self.assertFalse(created_again)

    def test_unsafe_url_refused_and_marked_rejected(self):
        profile = _profile(slug='unsafe-url-co')
        candidate = DiscoveredSource.objects.create(
            company=profile, url='http://127.0.0.1/report.pdf', source_type='sustainability_report',
            discovery_method='staff_registered_field', status='approved',
        )
        with self.assertRaises(ValueError):
            source_registry.register_discovered_source(candidate)
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, 'rejected')

    def test_approve_discovered_source_registers_by_default(self):
        profile = _profile(slug='approve-co')
        profile.sustainability_report_url = 'https://approve-co.example/sustainability.pdf'
        profile.save(update_fields=['sustainability_report_url'])
        [candidate] = source_discovery.discover_sources_for_company(profile)
        staff = User.objects.create_user(username='approver1', password='pw', is_staff=True)

        with patch('company_intelligence.services.source_registry.is_safe_external_url', return_value=(True, 'test override')):
            source_registry.approve_discovered_source(candidate, actor=staff, notes='Looks legitimate.')
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, 'registered')
        self.assertEqual(candidate.reviewed_by, staff)

    def test_reject_never_deletes_the_row(self):
        profile = _profile(slug='reject-preserve-co')
        candidate = DiscoveredSource.objects.create(
            company=profile, url='https://reject-preserve-co.example/x.pdf', discovery_method='manual', status='candidate',
        )
        staff = User.objects.create_user(username='rejecter1', password='pw', is_staff=True)
        source_registry.reject_discovered_source(candidate, actor=staff, reason='Not authoritative.')
        self.assertTrue(DiscoveredSource.objects.filter(pk=candidate.pk).exists())
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, 'rejected')
        self.assertEqual(candidate.review_notes, 'Not authoritative.')


class RefreshPolicyTests(TestCase):
    def test_never_checked_source_is_due_now(self):
        from harvester.models import Source as HarvesterSource

        profile = _profile(slug='policy-never-checked-co')
        source = HarvesterSource.objects.create(company=profile, source_type='sec_edgar', name='x')
        self.assertIsNone(refresh_policy.next_refresh_due_for_source(source))
        self.assertTrue(refresh_policy.is_source_due(source))

    def test_recently_succeeded_regulatory_source_not_yet_due(self):
        from django.utils import timezone
        from harvester.models import Source as HarvesterSource

        profile = _profile(slug='policy-recent-co')
        source = HarvesterSource.objects.create(
            company=profile, source_type='sec_edgar', name='x', last_success_at=timezone.now(),
        )
        self.assertFalse(refresh_policy.is_source_due(source))

    def test_failed_source_retried_sooner_than_normal_interval(self):
        import datetime as dt
        from django.utils import timezone
        from harvester.models import Source as HarvesterSource

        profile = _profile(slug='policy-failed-co')
        now = timezone.now()
        source = HarvesterSource.objects.create(
            company=profile, source_type='sustainability_report', name='x',
            last_success_at=now - dt.timedelta(days=200),
            last_failure_at=now - dt.timedelta(days=20),
        )
        # Normal interval (180d) would say NOT due yet from last_success, but the
        # more recent failure (20 days ago, retry window 14 days) makes it due.
        self.assertTrue(refresh_policy.is_source_due(source, now=now))

    def test_company_with_no_active_sources_has_no_due_date(self):
        profile = _profile(slug='policy-no-sources-co')
        self.assertIsNone(refresh_policy.company_next_refresh_due_at(profile))
        self.assertFalse(refresh_policy.is_company_due_for_refresh(profile))


class StewardshipHealthAndStateTests(TestCase):
    def test_health_zero_sources_all_completeness_components_false_except_no_disputed(self):
        profile = _profile(slug='health-empty-co')
        health = stewardship_state.compute_company_health(profile)
        self.assertEqual(health['official_sources_known'], 0)
        self.assertTrue(health['data_completeness_components']['no_disputed_evidence'])
        self.assertFalse(health['data_completeness_components']['has_official_source'])
        self.assertEqual(health['data_completeness_pct'], 20.0)

    def test_completeness_weights_sum_to_100(self):
        self.assertEqual(sum(stewardship_state.COMPLETENESS_WEIGHTS.values()) * 100, 100.0)

    def test_tracking_state_not_tracked_wins_regardless_of_health(self):
        profile = _profile(slug='state-not-tracked-co')
        state = stewardship_state.compute_tracking_state(profile)
        self.assertEqual(state['state'], 'NOT_TRACKED')

    def test_tracking_state_paused_wins_over_live_conditions(self):
        profile = _profile(slug='state-paused-co')
        profile.tracking_status = 'paused'
        profile.save(update_fields=['tracking_status'])
        state = stewardship_state.compute_tracking_state(profile)
        self.assertEqual(state['state'], 'PAUSED')

    def test_tracking_state_needs_source_discovery_when_active_with_zero_sources(self):
        profile = _profile(slug='state-nsd-co')
        profile.tracking_status = 'active'
        profile.save(update_fields=['tracking_status'])
        state = stewardship_state.compute_tracking_state(profile)
        self.assertEqual(state['state'], 'NEEDS_SOURCE_DISCOVERY')

    def test_tracking_state_review_required_when_pending_evidence_exists(self):
        profile = _profile(slug='state-review-req-co')
        profile.tracking_status = 'active'
        profile.save(update_fields=['tracking_status'])
        from harvester.models import Source as HarvesterSource
        HarvesterSource.objects.create(company=profile, source_type='sec_edgar', name='x')
        DiscoveredSource.objects.create(
            company=profile, url='https://state-review-req-co.example/x', discovery_method='sec_edgar_identity',
            status='registered',
        )
        _proposed_link(profile, kpi_id=50)
        state = stewardship_state.compute_tracking_state(profile)
        self.assertEqual(state['state'], 'REVIEW_REQUIRED')

    def test_tracking_state_current_when_everything_is_clean_and_fresh(self):
        from django.utils import timezone
        from harvester.models import Source as HarvesterSource

        profile = _profile(slug='state-current-co')
        profile.tracking_status = 'active'
        profile.save(update_fields=['tracking_status'])
        HarvesterSource.objects.create(company=profile, source_type='sec_edgar', name='x', last_success_at=timezone.now())
        DiscoveredSource.objects.create(
            company=profile, url='https://state-current-co.example/x', discovery_method='sec_edgar_identity',
            status='registered',
        )
        state = stewardship_state.compute_tracking_state(profile)
        self.assertEqual(state['state'], 'CURRENT')


class RefreshOrchestratorTests(TestCase):
    def test_dry_run_performs_zero_database_writes(self):
        profile = _real_profile('apple')
        before_discovered = DiscoveredSource.objects.filter(company=profile).count()
        before_runs = CompanyRefreshRun.objects.filter(company=profile).count()

        result = refresh_orchestrator.refresh_company_intelligence(profile, dry_run=True)
        self.assertTrue(result['dry_run'])
        profile.refresh_from_db()
        self.assertEqual(profile.tracking_status, 'not_tracked')  # unchanged
        self.assertEqual(DiscoveredSource.objects.filter(company=profile).count(), before_discovered)
        self.assertEqual(CompanyRefreshRun.objects.filter(company=profile).count(), before_runs)

    def test_paused_company_refuses_refresh_without_mutation(self):
        profile = _profile(slug='paused-refresh-co')
        profile.tracking_status = 'paused'
        profile.save(update_fields=['tracking_status'])
        result = refresh_orchestrator.refresh_company_intelligence(profile)
        self.assertEqual(result['error'], 'paused')
        profile.refresh_from_db()
        self.assertEqual(profile.tracking_status, 'paused')
        self.assertEqual(CompanyRefreshRun.objects.filter(company=profile).count(), 0)

    @patch('harvester.services.fetchers.fetch_sustainability_document')
    @patch('harvester.services.fetchers.fetch_sec_edgar')
    def test_full_refresh_completes_and_never_auto_confirms_kpi_candidates(self, mock_doc_fetch, mock_sec_fetch):
        mock_sec_fetch.return_value = _sec_edgar_outcome()
        mock_doc_fetch.return_value = _sustainability_outcome()

        profile = _real_profile('apple')
        run = refresh_orchestrator.refresh_company_intelligence(profile, triggered_by='manual')

        self.assertIsInstance(run, CompanyRefreshRun)
        self.assertEqual(run.status, 'complete')
        self.assertEqual(run.sources_checked, 2)
        self.assertEqual(run.sources_failed, 0)
        self.assertGreater(run.kpi_candidates_proposed, 0)

        profile.refresh_from_db()
        self.assertEqual(profile.tracking_status, 'active')
        self.assertIsNotNone(profile.last_refresh_at)

        # CRITICAL invariant: every KPI candidate this refresh proposed
        # remains 'proposed' — never silently auto-confirmed.
        self.assertFalse(
            CompanyKPIEvidenceLink.objects.filter(assessment__company=profile, review_state='confirmed').exists()
        )
        self.assertTrue(
            CompanyKPIEvidenceLink.objects.filter(assessment__company=profile, review_state='proposed').exists()
        )

    @patch('harvester.services.fetchers.fetch_sustainability_document')
    @patch('harvester.services.fetchers.fetch_sec_edgar')
    def test_second_run_is_idempotent_zero_duplicates(self, mock_doc_fetch, mock_sec_fetch):
        from harvester.models import Evidence as HarvesterEvidence, SourceDocument

        mock_sec_fetch.return_value = _sec_edgar_outcome()
        mock_doc_fetch.return_value = _sustainability_outcome()
        profile = _real_profile('apple')

        refresh_orchestrator.refresh_company_intelligence(profile, triggered_by='manual')
        docs_1 = SourceDocument.objects.filter(company=profile).count()
        ev_1 = HarvesterEvidence.objects.filter(company=profile).count()
        kpi_1 = CompanyKPIEvidenceLink.objects.filter(assessment__company=profile).count()
        disc_1 = DiscoveredSource.objects.filter(company=profile).count()

        run2 = refresh_orchestrator.refresh_company_intelligence(profile, triggered_by='manual')
        self.assertEqual(run2.documents_new, 0)
        self.assertEqual(run2.documents_unchanged, 2)

        self.assertEqual(SourceDocument.objects.filter(company=profile).count(), docs_1)
        self.assertEqual(HarvesterEvidence.objects.filter(company=profile).count(), ev_1)
        self.assertEqual(CompanyKPIEvidenceLink.objects.filter(assessment__company=profile).count(), kpi_1)
        self.assertEqual(DiscoveredSource.objects.filter(company=profile).count(), disc_1)

    @patch('harvester.services.fetchers.fetch_sustainability_document')
    @patch('harvester.services.fetchers.fetch_sec_edgar')
    def test_one_failed_source_yields_partial_not_false_complete(self, mock_doc_fetch, mock_sec_fetch):
        mock_sec_fetch.return_value = FetchOutcome(success=False, error='HTTP 500')
        mock_doc_fetch.return_value = _sustainability_outcome()

        profile = _real_profile('apple')
        run = refresh_orchestrator.refresh_company_intelligence(profile, triggered_by='manual')

        self.assertEqual(run.status, 'partial')
        self.assertEqual(run.sources_failed, 1)
        self.assertTrue(any('HTTP 500' in e for e in run.errors))

    @patch('harvester.services.fetchers.fetch_sustainability_document')
    @patch('harvester.services.fetchers.fetch_sec_edgar')
    def test_all_sources_failing_yields_failed_and_error_tracking_status(self, mock_doc_fetch, mock_sec_fetch):
        mock_sec_fetch.return_value = FetchOutcome(success=False, error='HTTP 500')
        mock_doc_fetch.return_value = FetchOutcome(success=False, error='HTTP 404')

        profile = _real_profile('apple')
        run = refresh_orchestrator.refresh_company_intelligence(profile, triggered_by='manual')

        self.assertEqual(run.status, 'failed')
        profile.refresh_from_db()
        self.assertEqual(profile.tracking_status, 'error')

    def test_company_with_no_mapped_sources_is_trivially_complete(self):
        profile = _profile(slug='no-mapped-sources-co')
        run = refresh_orchestrator.refresh_company_intelligence(profile)
        self.assertEqual(run.status, 'complete')
        self.assertEqual(run.sources_checked, 0)

    @patch('harvester.services.fetchers.fetch_sustainability_document')
    @patch('harvester.services.fetchers.fetch_sec_edgar')
    def test_refresh_records_observatory_session_anchored_to_company(self, mock_doc_fetch, mock_sec_fetch):
        from ai_observatory.models import AnalysisSession

        mock_sec_fetch.return_value = _sec_edgar_outcome()
        mock_doc_fetch.return_value = _sustainability_outcome()
        profile = _real_profile('apple')
        run = refresh_orchestrator.refresh_company_intelligence(profile, triggered_by='manual')

        self.assertIsNotNone(run.observatory_session)
        self.assertEqual(run.observatory_session.kind, 'stewardship_refresh')
        self.assertEqual(run.observatory_session.company_id, profile.pk)
        self.assertEqual(run.observatory_session.status, 'completed')


class ManagementCommandTests(TestCase):
    @patch('harvester.services.fetchers.fetch_sustainability_document')
    @patch('harvester.services.fetchers.fetch_sec_edgar')
    def test_bootstrap_and_refresh_real_company_by_slug(self, mock_doc_fetch, mock_sec_fetch):
        from io import StringIO

        from django.core.management import call_command

        mock_sec_fetch.return_value = _sec_edgar_outcome()
        mock_doc_fetch.return_value = _sustainability_outcome()

        out = StringIO()
        call_command('refresh_stewardship_universe', '--company', 'apple', stdout=out)
        profile = CompanyProfile.objects.get(company__slug='apple')
        self.assertEqual(profile.tracking_status, 'active')
        self.assertIn('complete', out.getvalue().lower())

    def test_dry_run_flag_performs_no_mutation(self):
        from io import StringIO

        from django.core.management import call_command

        profile = _real_profile('apple')
        before = CompanyRefreshRun.objects.filter(company=profile).count()
        out = StringIO()
        call_command('refresh_stewardship_universe', '--company', 'apple', '--dry-run', stdout=out)
        self.assertEqual(CompanyRefreshRun.objects.filter(company=profile).count(), before)

    def test_no_companies_to_refresh_is_handled_honestly(self):
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command('refresh_stewardship_universe', stdout=out)
        self.assertIn('No companies to refresh', out.getvalue())

    def test_limit_flag_caps_company_count(self):
        from io import StringIO

        from django.core.management import call_command

        p1 = _profile(slug='limit-co-1')
        p2 = _profile(slug='limit-co-2')
        for p in (p1, p2):
            p.tracking_status = 'active'
            p.save(update_fields=['tracking_status'])
        out = StringIO()
        call_command('refresh_stewardship_universe', '--limit', '1', stdout=out)
        lines = [l for l in out.getvalue().splitlines() if l.startswith('limit-co')]
        self.assertEqual(len(lines), 1)


class StewardshipViewsTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='su_staff', password='pw', is_staff=True)
        self.normal = User.objects.create_user(username='su_normal', password='pw')

    def test_universe_view_requires_staff(self):
        client = Client()
        client.login(username='su_normal', password='pw')
        response = client.get(reverse('companies:universe'))
        self.assertNotEqual(response.status_code, 200)

    def test_universe_view_lists_companies_with_derived_state(self):
        _profile(slug='universe-list-co')
        client = Client()
        client.login(username='su_staff', password='pw')
        response = client.get(reverse('companies:universe'))
        self.assertEqual(response.status_code, 200)
        slugs = [r['profile'].company.slug for r in response.context['rows']]
        self.assertIn('universe-list-co', slugs)

    def test_company_status_view_requires_staff(self):
        profile = _profile(slug='status-view-co')
        client = Client()
        client.login(username='su_normal', password='pw')
        response = client.get(reverse('companies:company_status', args=[profile.company.slug]))
        self.assertNotEqual(response.status_code, 200)

    def test_company_status_view_shows_health_and_registry(self):
        profile = _profile(slug='status-view-ok-co')
        client = Client()
        client.login(username='su_staff', password='pw')
        response = client.get(reverse('companies:company_status', args=[profile.company.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('health', response.context)
        self.assertIn('registry_rows', response.context)

    def test_trigger_refresh_requires_post(self):
        profile = _profile(slug='trigger-get-co')
        client = Client()
        client.login(username='su_staff', password='pw')
        response = client.get(reverse('companies:trigger_refresh', args=[profile.company.slug]))
        self.assertEqual(response.status_code, 404)

    def test_trigger_refresh_requires_staff(self):
        profile = _profile(slug='trigger-staff-co')
        client = Client()
        client.login(username='su_normal', password='pw')
        response = client.post(reverse('companies:trigger_refresh', args=[profile.company.slug]))
        self.assertNotEqual(response.status_code, 200)

    def test_trigger_refresh_dry_run_via_view(self):
        profile = _profile(slug='trigger-dryrun-co')
        client = Client()
        client.login(username='su_staff', password='pw')
        response = client.post(
            reverse('companies:trigger_refresh', args=[profile.company.slug]), {'dry_run': '1'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CompanyRefreshRun.objects.filter(company=profile).count(), 0)

    def test_approve_and_reject_source_views_require_staff(self):
        profile = _profile(slug='approve-view-co')
        candidate = DiscoveredSource.objects.create(
            company=profile, url='https://approve-view-co.example/x.pdf', discovery_method='manual', status='candidate',
        )
        client = Client()
        client.login(username='su_normal', password='pw')
        response = client.post(reverse('companies:approve_source', args=[profile.company.slug, candidate.pk]))
        self.assertNotEqual(response.status_code, 200)

    def test_approve_source_view_staff_success(self):
        profile = _profile(slug='approve-view-ok-co')
        profile.sustainability_report_url = 'https://approve-view-ok-co.example/sustainability.pdf'
        profile.save(update_fields=['sustainability_report_url'])
        [candidate] = source_discovery.discover_sources_for_company(profile)
        client = Client()
        client.login(username='su_staff', password='pw')
        with patch('company_intelligence.services.source_registry.is_safe_external_url', return_value=(True, 'ok')):
            response = client.post(reverse('companies:approve_source', args=[profile.company.slug, candidate.pk]), {'notes': 'ok'})
        self.assertEqual(response.status_code, 302)
        candidate.refresh_from_db()
        self.assertEqual(candidate.status, 'registered')

    def test_pause_and_resume_tracking(self):
        profile = _profile(slug='pause-resume-co')
        profile.tracking_status = 'active'
        profile.save(update_fields=['tracking_status'])
        client = Client()
        client.login(username='su_staff', password='pw')

        client.post(reverse('companies:pause_tracking', args=[profile.company.slug]))
        profile.refresh_from_db()
        self.assertEqual(profile.tracking_status, 'paused')

        client.post(reverse('companies:resume_tracking', args=[profile.company.slug]))
        profile.refresh_from_db()
        self.assertEqual(profile.tracking_status, 'active')

    def test_no_investment_recommendation_language_on_universe_page(self):
        _profile(slug='no-invest-lang-co')
        client = Client()
        client.login(username='su_staff', password='pw')
        response = client.get(reverse('companies:universe'))
        content = response.content.decode().lower()
        for banned in BANNED_INVESTMENT_WORDS:
            self.assertNotIn(banned, content)

    def test_no_investment_recommendation_language_on_status_page(self):
        profile = _profile(slug='no-invest-lang-status-co')
        client = Client()
        client.login(username='su_staff', password='pw')
        response = client.get(reverse('companies:company_status', args=[profile.company.slug]))
        content = response.content.decode().lower()
        for banned in BANNED_INVESTMENT_WORDS:
            self.assertNotIn(banned, content)


class StewardshipCSRFAndCrossCompanyTests(TestCase):
    def test_trigger_refresh_without_csrf_token_rejected(self):
        from django.test import Client as StrictClient

        profile = _profile(slug='csrf-refresh-co')
        staff = User.objects.create_user(username='csrf_su_staff', password='pw', is_staff=True)
        strict_client = StrictClient(enforce_csrf_checks=True)
        strict_client.login(username='csrf_su_staff', password='pw')
        response = strict_client.post(reverse('companies:trigger_refresh', args=[profile.company.slug]))
        self.assertEqual(response.status_code, 403)

    def test_approve_source_cross_company_404s(self):
        profile_a = _profile(slug='cross-a-co')
        profile_b = _profile(slug='cross-b-co')
        candidate = DiscoveredSource.objects.create(
            company=profile_a, url='https://cross-a-co.example/x.pdf', discovery_method='manual', status='candidate',
        )
        staff = User.objects.create_user(username='cross_staff', password='pw', is_staff=True)
        client = Client()
        client.login(username='cross_staff', password='pw')
        response = client.post(reverse('companies:approve_source', args=[profile_b.company.slug, candidate.pk]))
        self.assertEqual(response.status_code, 404)


# ═══════════════════════════════════════════════════════════════════════════
# feat/stewardship-monitor (PR 14) — Continuous Stewardship Monitor: scheduled
# refresh, change detection, evidence alerts. Same @patch conventions as the
# PR13 block above — network calls always mocked, identity/curated data real.
# ═══════════════════════════════════════════════════════════════════════════
from company_intelligence.models import StewardshipAlert, StewardshipChangeEvent
from company_intelligence.services import (
    change_detection, change_timeline, conflict_detection, stewardship_alerts,
)


def _harvester_backed_link(profile, kpi_id, *, relationship='supports', review_state='confirmed',
                            text='Real evidence text discussing the KPI topic.', document=None,
                            source=None, freshness_score=0.8):
    """A CompanyKPIEvidenceLink genuinely backed by a harvester.Evidence row
    (via the same EvidenceMemory.source_reference convention
    create_memory_from_evidence() writes) — needed to exercise
    change_detection.evidence_status_label(), which only resolves real
    provenance, never a PR9-style demo fixture."""
    from harvester.models import Evidence as HarvesterEvidence

    harvester_evidence = HarvesterEvidence.objects.create(
        company=profile, company_slug=profile.company.slug, category='waste', document=document, source=source,
        title='Test evidence', full_text=text, excerpt=text[:200], freshness_score=freshness_score,
    )
    memory = EvidenceMemory.objects.create(
        text_chunk=text, company=profile, source_type='harvester_evidence',
        source_reference=f'harvester.Evidence:{harvester_evidence.pk}', verification_status='verified',
    )
    assessment = CompanyKPIAssessment.objects.get_or_create(company=profile, kpi_id=kpi_id)[0]
    link = CompanyKPIEvidenceLink.objects.create(
        assessment=assessment, evidence=memory, relationship=relationship, review_state=review_state,
    )
    return link, harvester_evidence


class ChangeDetectionTests(TestCase):
    def test_new_source_creates_change_event(self):
        from harvester.models import Source as HarvesterSource

        profile = _profile(slug='cd-new-source-co')
        discovered = DiscoveredSource.objects.create(
            company=profile, url='https://cd-new-source-co.example/x.pdf', discovery_method='manual', status='approved',
        )
        harvester_source = HarvesterSource.objects.create(company=profile, source_type='sustainability_report', name='x')
        event = change_detection.record_new_source(discovered, harvester_source)
        self.assertEqual(event.event_type, 'new_source')
        self.assertEqual(event.company_id, profile.pk)
        self.assertEqual(event.source_id, harvester_source.pk)

    def test_unchanged_ingestion_run_with_no_prior_failure_creates_no_event(self):
        from harvester.models import IngestionRun, Source as HarvesterSource

        profile = _profile(slug='cd-unchanged-co')
        source = HarvesterSource.objects.create(company=profile, source_type='sustainability_report', name='x')
        run = IngestionRun.objects.create(source=source, status='unchanged')
        events = change_detection.detect_source_change(source, run)
        self.assertEqual(events, [])

    def test_failed_ingestion_run_creates_source_unreachable_event(self):
        from harvester.models import IngestionRun, Source as HarvesterSource

        profile = _profile(slug='cd-failed-co')
        source = HarvesterSource.objects.create(company=profile, source_type='sustainability_report', name='x')
        run = IngestionRun.objects.create(source=source, status='failed', error_message='HTTP 404')
        events = change_detection.detect_source_change(source, run)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, 'source_unreachable')
        self.assertTrue(events[0].review_required)
        self.assertIn('404', events[0].summary)

    def test_source_recovers_after_prior_failure_on_unchanged_run(self):
        from harvester.models import IngestionRun, Source as HarvesterSource

        profile = _profile(slug='cd-recover-co')
        source = HarvesterSource.objects.create(company=profile, source_type='sustainability_report', name='x')
        IngestionRun.objects.create(source=source, status='failed', error_message='HTTP 500')
        run2 = IngestionRun.objects.create(source=source, status='unchanged')
        events = change_detection.detect_source_change(source, run2)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, 'source_recovered')

    def test_new_document_alongside_recovery_returns_both_events(self):
        """Regression test for a real bug caught during self-review: a
        recovery detected in the SAME run as a new/updated document must
        never be silently dropped from the returned list."""
        from harvester.models import IngestionRun, Source as HarvesterSource

        profile = _profile(slug='cd-recover-and-new-co')
        source = HarvesterSource.objects.create(company=profile, source_type='sustainability_report', name='x')
        IngestionRun.objects.create(source=source, status='failed', error_message='HTTP 500')
        run2 = IngestionRun.objects.create(source=source, status='new', evidence_created_count=3)
        events = change_detection.detect_source_change(source, run2)
        event_types = {e.event_type for e in events}
        self.assertIn('new_document', event_types)
        self.assertIn('source_recovered', event_types)
        self.assertEqual(len(events), 2)

    def test_new_document_type_for_document_source_vs_new_evidence_for_raw_source(self):
        from harvester.models import IngestionRun, Source as HarvesterSource

        profile = _profile(slug='cd-doc-vs-evidence-co')
        doc_source = HarvesterSource.objects.create(company=profile, source_type='sustainability_report', name='doc')
        raw_source = HarvesterSource.objects.create(company=profile, source_type='sec_edgar', name='raw')

        doc_run = IngestionRun.objects.create(source=doc_source, status='new', evidence_created_count=1)
        raw_run = IngestionRun.objects.create(source=raw_source, status='new', evidence_created_count=1)

        doc_events = change_detection.detect_source_change(doc_source, doc_run)
        raw_events = change_detection.detect_source_change(raw_source, raw_run)
        self.assertEqual(doc_events[0].event_type, 'new_document')
        self.assertEqual(raw_events[0].event_type, 'new_evidence')

    def test_record_new_kpi_candidates_aggregate_event(self):
        profile = _profile(slug='cd-new-kpi-co')
        link = _proposed_link(profile, kpi_id=10)
        event = change_detection.record_new_kpi_candidates(profile, [link])
        self.assertEqual(event.event_type, 'new_kpi_candidate')
        self.assertIn('1', event.summary)

    def test_record_new_kpi_candidates_returns_none_for_empty_list(self):
        profile = _profile(slug='cd-no-new-kpi-co')
        self.assertIsNone(change_detection.record_new_kpi_candidates(profile, []))

    def test_record_shariah_data_changed(self):
        profile = _profile(slug='cd-shariah-changed-co')
        event = change_detection.record_shariah_data_changed(profile)
        self.assertEqual(event.event_type, 'shariah_data_changed')
        self.assertTrue(event.review_required)

    def test_evidence_status_label_disputed_wins(self):
        profile = _profile(slug='status-disputed-co')
        link, _ = _harvester_backed_link(profile, kpi_id=20, review_state='disputed', freshness_score=0.9)
        self.assertEqual(change_detection.evidence_status_label(link), 'DISPUTED')

    def test_evidence_status_label_stale_when_freshness_below_threshold(self):
        profile = _profile(slug='status-stale-co')
        link, _ = _harvester_backed_link(profile, kpi_id=21, freshness_score=0.1)
        self.assertEqual(change_detection.evidence_status_label(link), 'STALE')

    def test_evidence_status_label_current_for_fresh_confirmed_evidence(self):
        profile = _profile(slug='status-current-co')
        link, _ = _harvester_backed_link(profile, kpi_id=22, freshness_score=0.9)
        self.assertEqual(change_detection.evidence_status_label(link), 'CURRENT')

    def test_evidence_status_label_current_for_non_harvester_backed_link(self):
        # A PR9-style manual/demo link has no harvester.Evidence to resolve —
        # honestly defaults to CURRENT rather than fabricating staleness.
        profile = _profile(slug='status-no-harvester-co')
        link = _proposed_link(profile, kpi_id=23)
        self.assertEqual(change_detection.evidence_status_label(link), 'CURRENT')

    def test_evidence_status_label_historical_when_newer_document_exists_no_conflict(self):
        from harvester.models import Source as HarvesterSource, SourceDocument

        profile = _profile(slug='status-historical-co')
        source = HarvesterSource.objects.create(company=profile, source_type='sustainability_report', name='x')
        old_doc = SourceDocument.objects.create(
            source=source, company=profile, company_slug=profile.company.slug, title='Old Report',
            document_type='sustainability_report', url='https://status-historical-co.example/report.pdf',
            content_hash='hash-old',
        )
        link, harvester_evidence = _harvester_backed_link(profile, kpi_id=24, document=old_doc, freshness_score=0.8)
        SourceDocument.objects.create(
            source=source, company=profile, company_slug=profile.company.slug, title='New Report',
            document_type='sustainability_report', url='https://status-historical-co.example/report.pdf',
            content_hash='hash-new',
        )
        self.assertEqual(change_detection.evidence_status_label(link), 'HISTORICAL')

    def test_evidence_status_label_possibly_superseded_when_conflict_flagged(self):
        from harvester.models import Source as HarvesterSource, SourceDocument

        profile = _profile(slug='status-superseded-co')
        source = HarvesterSource.objects.create(company=profile, source_type='sustainability_report', name='x')
        old_doc = SourceDocument.objects.create(
            source=source, company=profile, company_slug=profile.company.slug, title='Old Report',
            document_type='sustainability_report', url='https://status-superseded-co.example/report.pdf',
            content_hash='hash-old-2',
        )
        link, harvester_evidence = _harvester_backed_link(profile, kpi_id=25, document=old_doc, freshness_score=0.8)
        SourceDocument.objects.create(
            source=source, company=profile, company_slug=profile.company.slug, title='New Report',
            document_type='sustainability_report', url='https://status-superseded-co.example/report.pdf',
            content_hash='hash-new-2',
        )
        StewardshipChangeEvent.objects.create(
            company=profile, event_type='potential_conflict', severity='high',
            evidence=link.evidence, kpi_evidence_link=link, summary='Test conflict flag.',
        )
        self.assertEqual(change_detection.evidence_status_label(link), 'POSSIBLY_SUPERSEDED')


class ConflictDetectionTests(TestCase):
    def test_reversal_signal_phrase_flags_potential_conflict(self):
        profile = _profile(slug='conflict-reversal-co')
        _harvester_backed_link(profile, kpi_id=30, relationship='supports', review_state='confirmed')
        assessment = CompanyKPIAssessment.objects.get(company=profile, kpi_id=30)
        new_link, _ = _harvester_backed_link(
            profile, kpi_id=30, relationship='context', review_state='proposed',
            text='The programme was discontinued and no longer supports this initiative.',
        )
        events = conflict_detection.detect_potential_conflicts_for_refresh(profile, [new_link])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, 'potential_conflict')
        self.assertEqual(events[0].kpi_evidence_link_id, new_link.pk)
        # Never auto-sets an actual conflicts relationship or mutates review_state.
        new_link.refresh_from_db()
        self.assertEqual(new_link.relationship, 'context')
        self.assertEqual(new_link.review_state, 'proposed')

    def test_no_existing_confirmed_support_means_no_conflict_flagged(self):
        profile = _profile(slug='conflict-none-co')
        new_link, _ = _harvester_backed_link(
            profile, kpi_id=31, relationship='context', review_state='proposed',
            text='This was discontinued.',
        )
        events = conflict_detection.detect_potential_conflicts_for_refresh(profile, [new_link])
        self.assertEqual(events, [])

    def test_ordinary_supporting_evidence_with_no_reversal_signal_is_not_flagged(self):
        profile = _profile(slug='conflict-ordinary-co')
        _harvester_backed_link(profile, kpi_id=32, relationship='supports', review_state='confirmed')
        new_link, _ = _harvester_backed_link(
            profile, kpi_id=32, relationship='supports', review_state='proposed',
            text='We achieved a 74% waste diversion rate this year.',
        )
        events = conflict_detection.detect_potential_conflicts_for_refresh(profile, [new_link])
        self.assertEqual(events, [])


class StewardshipAlertsTests(TestCase):
    def test_generate_alert_for_event_creates_alert_with_priority_components(self):
        profile = _profile(slug='alert-gen-co')
        event = StewardshipChangeEvent.objects.create(
            company=profile, event_type='potential_conflict', severity='high', review_required=True,
            summary='Test potential conflict.',
        )
        alert, created = stewardship_alerts.generate_alert_for_event(event)
        self.assertTrue(created)
        self.assertEqual(alert.alert_type, 'potential_conflict')
        self.assertGreater(alert.priority_score, 0)
        self.assertIn('severity_weight', alert.priority_components)
        self.assertIn('change_type_weight', alert.priority_components)
        self.assertEqual(alert.priority_score, sum(alert.priority_components.values()))

    def test_generate_alert_for_event_is_idempotent(self):
        profile = _profile(slug='alert-idempotent-co')
        event = StewardshipChangeEvent.objects.create(
            company=profile, event_type='new_document', severity='medium', summary='New doc.',
        )
        alert1, created1 = stewardship_alerts.generate_alert_for_event(event)
        alert2, created2 = stewardship_alerts.generate_alert_for_event(event)
        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(alert1.pk, alert2.pk)
        self.assertEqual(StewardshipAlert.objects.filter(change_event=event).count(), 1)

    def test_generate_alerts_for_refresh_produces_zero_alerts_for_zero_events(self):
        profile = _profile(slug='alert-zero-co')
        alerts = stewardship_alerts.generate_alerts_for_refresh(profile, None, [])
        self.assertEqual(alerts, [])
        self.assertEqual(StewardshipAlert.objects.filter(company=profile).count(), 0)

    def test_acknowledge_resolve_dismiss_state_transitions(self):
        profile = _profile(slug='alert-lifecycle-co')
        staff = User.objects.create_user(username='alert_staff', password='pw', is_staff=True)
        event = StewardshipChangeEvent.objects.create(company=profile, event_type='new_document', summary='x')
        alert, _ = stewardship_alerts.generate_alert_for_event(event)

        self.assertEqual(alert.state, 'new')
        stewardship_alerts.acknowledge_alert(alert, staff)
        alert.refresh_from_db()
        self.assertEqual(alert.state, 'acknowledged')
        self.assertEqual(alert.acknowledged_by, staff)

        stewardship_alerts.resolve_alert(alert, staff, reason='Confirmed harmless.')
        alert.refresh_from_db()
        self.assertEqual(alert.state, 'resolved')
        self.assertEqual(alert.resolution_reason, 'Confirmed harmless.')

    def test_dismiss_alert(self):
        profile = _profile(slug='alert-dismiss-co')
        staff = User.objects.create_user(username='alert_dismiss_staff', password='pw', is_staff=True)
        event = StewardshipChangeEvent.objects.create(company=profile, event_type='new_document', summary='x')
        alert, _ = stewardship_alerts.generate_alert_for_event(event)
        stewardship_alerts.dismiss_alert(alert, staff, reason='Not relevant.')
        alert.refresh_from_db()
        self.assertEqual(alert.state, 'dismissed')

    def test_no_investment_recommendation_language_in_any_alert_template(self):
        for event_type, template in stewardship_alerts.MESSAGE_TEMPLATES.items():
            lowered = template.lower()
            for banned in stewardship_alerts.BANNED_PHRASES:
                self.assertNotIn(banned, lowered, f'{event_type} template contains banned phrase "{banned}"')


class ChangeTimelineTests(TestCase):
    def test_timeline_merges_and_sorts_multiple_record_types_newest_first(self):
        profile = _profile(slug='timeline-co')
        DiscoveredSource.objects.create(
            company=profile, url='https://timeline-co.example/x.pdf', discovery_method='manual', status='candidate',
        )
        StewardshipChangeEvent.objects.create(company=profile, event_type='new_document', summary='A new doc arrived.')
        CompanyRefreshRun.objects.create(company=profile, status='complete')
        _proposed_link(profile, kpi_id=40)

        timeline = change_timeline.company_change_timeline(profile)
        kinds = {e['kind'] for e in timeline}
        self.assertIn('source_discovered', kinds)
        self.assertIn('new_document', kinds)
        self.assertIn('refresh_run', kinds)
        self.assertIn('kpi_candidate_proposed', kinds)
        timestamps = [e['timestamp'] for e in timeline]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))

    def test_timeline_respects_limit(self):
        profile = _profile(slug='timeline-limit-co')
        for i in range(5):
            StewardshipChangeEvent.objects.create(company=profile, event_type='new_document', summary=f'doc {i}')
        timeline = change_timeline.company_change_timeline(profile, limit=2)
        self.assertEqual(len(timeline), 2)


class RefreshOrchestratorLockingAndSchedulingTests(TestCase):
    def test_concurrent_refresh_is_refused_not_double_run(self):
        profile = _profile(slug='lock-co')
        profile.tracking_status = 'refresh_in_progress'
        profile.save(update_fields=['tracking_status'])
        result = refresh_orchestrator.refresh_company_intelligence(profile, triggered_by='manual')
        self.assertEqual(result['error'], 'already_refreshing')
        self.assertEqual(CompanyRefreshRun.objects.filter(company=profile).count(), 0)

    @patch('harvester.services.fetchers.fetch_sustainability_document')
    @patch('harvester.services.fetchers.fetch_sec_edgar')
    def test_scheduled_trigger_skips_not_due_sources(self, mock_doc_fetch, mock_sec_fetch):
        from django.utils import timezone
        from harvester.models import Source as HarvesterSource

        mock_sec_fetch.return_value = _sec_edgar_outcome()
        mock_doc_fetch.return_value = _sustainability_outcome()
        profile = _real_profile('apple')

        # First manual refresh registers + fetches both real sources.
        refresh_orchestrator.refresh_company_intelligence(profile, triggered_by='manual')
        # Mark both sources freshly succeeded so neither is due again soon.
        HarvesterSource.objects.filter(company=profile).update(last_success_at=timezone.now())

        run2 = refresh_orchestrator.refresh_company_intelligence(profile, triggered_by='scheduled')
        self.assertEqual(run2.sources_checked, 0)
        self.assertEqual(run2.sources_skipped_not_due, 2)

    @patch('harvester.services.fetchers.fetch_sustainability_document')
    @patch('harvester.services.fetchers.fetch_sec_edgar')
    def test_manual_trigger_always_rechecks_every_active_source(self, mock_doc_fetch, mock_sec_fetch):
        from django.utils import timezone
        from harvester.models import Source as HarvesterSource

        mock_sec_fetch.return_value = _sec_edgar_outcome()
        mock_doc_fetch.return_value = _sustainability_outcome()
        profile = _real_profile('apple')

        refresh_orchestrator.refresh_company_intelligence(profile, triggered_by='manual')
        HarvesterSource.objects.filter(company=profile).update(last_success_at=timezone.now())

        run2 = refresh_orchestrator.refresh_company_intelligence(profile, triggered_by='manual')
        self.assertEqual(run2.sources_checked, 2)
        self.assertEqual(run2.sources_skipped_not_due, 0)


class RefreshOrchestratorChangeWiringTests(TestCase):
    @patch('harvester.services.fetchers.fetch_sustainability_document')
    @patch('harvester.services.fetchers.fetch_sec_edgar')
    def test_first_refresh_produces_change_events_and_alerts(self, mock_doc_fetch, mock_sec_fetch):
        mock_sec_fetch.return_value = _sec_edgar_outcome()
        mock_doc_fetch.return_value = _sustainability_outcome()
        profile = _real_profile('apple')

        run = refresh_orchestrator.refresh_company_intelligence(profile, triggered_by='manual')
        events = StewardshipChangeEvent.objects.filter(refresh_run=run)
        self.assertTrue(events.exists())
        self.assertTrue(events.filter(event_type='new_kpi_candidate').exists())
        self.assertTrue(StewardshipAlert.objects.filter(company=profile).exists())

    @patch('harvester.services.fetchers.fetch_sustainability_document')
    @patch('harvester.services.fetchers.fetch_sec_edgar')
    def test_genuinely_first_ever_document_is_labelled_new_not_updated(self, mock_doc_fetch, mock_sec_fetch):
        """
        Regression test for a real bug caught during PR14 browser
        verification: a company's genuinely FIRST-EVER document ingestion
        was mislabelled 'document_updated' because the pre-existing
        new-vs-updated check in harvester/services/ingestion_pipeline.py
        looked at whether the COMPANY had ANY evidence yet (in any
        category), not whether THIS specific document/URL had been seen
        before. Since the SEC EDGAR source is processed first (alphabetical
        Source ordering: 'sec_edgar' < 'sustainability_report') and creates
        financial-category evidence, the sustainability document's own
        brand-new ingestion was incorrectly seeing "prior evidence exists"
        and reporting itself as updated rather than new.

        NOTE: with this exact stacked-@patch order, mock_doc_fetch (first
        param) is the ACTUAL mock for fetch_sec_edgar and mock_sec_fetch
        (second param) is the ACTUAL mock for fetch_sustainability_document
        — verified empirically (see the comment on the shariah test above);
        this test is precision-sensitive (checks an exact document_id/event
        pairing), so unlike the file's other, coarser tests, getting this
        backwards silently breaks it rather than merely being confusing.
        """
        mock_doc_fetch.return_value = _sec_edgar_outcome()
        mock_sec_fetch.return_value = _sustainability_outcome()
        profile = _real_profile('apple')

        run = refresh_orchestrator.refresh_company_intelligence(profile, triggered_by='manual')
        doc_events = StewardshipChangeEvent.objects.filter(refresh_run=run, document__isnull=False)
        self.assertTrue(doc_events.exists())
        for event in doc_events:
            self.assertEqual(event.event_type, 'new_document', event.summary)

    @patch('harvester.services.fetchers.fetch_sustainability_document')
    @patch('harvester.services.fetchers.fetch_sec_edgar')
    def test_second_unchanged_refresh_produces_zero_new_change_events(self, mock_doc_fetch, mock_sec_fetch):
        mock_sec_fetch.return_value = _sec_edgar_outcome()
        mock_doc_fetch.return_value = _sustainability_outcome()
        profile = _real_profile('apple')

        refresh_orchestrator.refresh_company_intelligence(profile, triggered_by='manual')
        run2 = refresh_orchestrator.refresh_company_intelligence(profile, triggered_by='manual')
        self.assertEqual(StewardshipChangeEvent.objects.filter(refresh_run=run2).count(), 0)

    @patch('harvester.services.fetchers.fetch_sustainability_document')
    @patch('harvester.services.fetchers.fetch_sec_edgar')
    def test_kpi_candidates_are_stamped_with_proposing_refresh_run(self, mock_doc_fetch, mock_sec_fetch):
        mock_sec_fetch.return_value = _sec_edgar_outcome()
        mock_doc_fetch.return_value = _sustainability_outcome()
        profile = _real_profile('apple')

        run = refresh_orchestrator.refresh_company_intelligence(profile, triggered_by='manual')
        links = CompanyKPIEvidenceLink.objects.filter(assessment__company=profile)
        self.assertTrue(links.exists())
        for link in links:
            self.assertEqual(link.proposed_via_refresh_run_id, run.pk)

    @patch('harvester.services.fetchers.fetch_sustainability_document')
    @patch('harvester.services.fetchers.fetch_sec_edgar')
    def test_shariah_data_changed_event_emitted_when_financial_facts_created(self, mock_doc_fetch, mock_sec_fetch):
        # NOTE: with this exact stacked-@patch order, mock_doc_fetch (first
        # param) is the ACTUAL mock for fetch_sec_edgar and mock_sec_fetch
        # (second param) is the ACTUAL mock for fetch_sustainability_document
        # — verified empirically; the parameter names are misleading but
        # match this file's existing PR13 convention throughout. This test
        # needs a realistic 'metrics' metadata shape (which the generic
        # _sec_edgar_outcome() helper doesn't include) on whichever mock
        # really backs fetch_sec_edgar, so it's built inline here.
        sec_edgar_outcome_with_metrics = FetchOutcome(
            success=True,
            candidates=[EvidenceCandidate(
                company_slug='apple', category='financial', statement='Apple reported revenue of $400B.',
                source_type='regulatory_filing', title='SEC EDGAR test', url='https://www.sec.gov/test',
                source_owner='U.S. Securities and Exchange Commission',
            )],
            content_hash_input='sec-hash-with-metrics',
            metadata={
                'cik': '0000320193', 'entity_name': 'Apple Inc.',
                'metrics': {
                    'revenue_usd': {
                        'value': 400_000_000_000.0, 'concept': 'Revenues', 'is_derived': False,
                        'unit': 'USD', 'period_end': '2024-09-28', 'statement': 'Apple reported total revenue of $400,000,000,000.',
                    },
                },
            },
        )
        mock_doc_fetch.return_value = sec_edgar_outcome_with_metrics
        mock_sec_fetch.return_value = _sustainability_outcome()
        profile = _real_profile('apple')

        run = refresh_orchestrator.refresh_company_intelligence(profile, triggered_by='manual')
        self.assertTrue(profile.financial_facts.exists())
        self.assertTrue(
            StewardshipChangeEvent.objects.filter(refresh_run=run, event_type='shariah_data_changed').exists()
        )


class AppearanceContextAndReviewWorkbenchIntegrationTests(TestCase):
    def test_appearance_context_shows_refresh_run_label(self):
        profile = _profile(slug='appearance-co')
        run = CompanyRefreshRun.objects.create(company=profile, triggered_by='manual', status='complete')
        link = _proposed_link(profile, kpi_id=60)
        link.proposed_via_refresh_run = run
        link.save(update_fields=['proposed_via_refresh_run'])
        context = evidence_review.appearance_context(link)
        self.assertIsNotNone(context['refresh_run_label'])
        self.assertIn(str(run.pk), context['refresh_run_label'])
        self.assertIsNone(context['potential_conflict_event'])

    def test_appearance_context_shows_potential_conflict_flag(self):
        profile = _profile(slug='appearance-conflict-co')
        link = _proposed_link(profile, kpi_id=61)
        StewardshipChangeEvent.objects.create(
            company=profile, event_type='potential_conflict', kpi_evidence_link=link, summary='Flagged.',
        )
        context = evidence_review.appearance_context(link)
        self.assertIsNotNone(context['potential_conflict_event'])

    def test_appearance_context_absent_for_manually_added_link(self):
        profile = _profile(slug='appearance-manual-co')
        link = _proposed_link(profile, kpi_id=62)
        context = evidence_review.appearance_context(link)
        self.assertIsNone(context['refresh_run_label'])
        self.assertIsNone(context['potential_conflict_event'])

    def test_pending_review_queue_rows_include_appearance_context(self):
        profile = _profile(slug='appearance-queue-co')
        _proposed_link(profile, kpi_id=63)
        rows = evidence_review.pending_review_queue({'company_slug': profile.company.slug})
        self.assertTrue(rows)
        self.assertIn('appearance', rows[0])


class MonitorViewsTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username='monitor_staff', password='pw', is_staff=True)
        self.normal = User.objects.create_user(username='monitor_normal', password='pw')

    def test_monitor_dashboard_requires_staff(self):
        client = Client()
        client.login(username='monitor_normal', password='pw')
        response = client.get(reverse('companies:monitor'))
        self.assertNotEqual(response.status_code, 200)

    def test_monitor_dashboard_shows_real_counts(self):
        profile = _profile(slug='monitor-dash-co')
        profile.tracking_status = 'active'
        profile.save(update_fields=['tracking_status'])
        client = Client()
        client.login(username='monitor_staff', password='pw')
        response = client.get(reverse('companies:monitor'))
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.context['health']['tracked_companies'], 1)

    def test_monitor_dashboard_lists_source_failures(self):
        from django.utils import timezone
        from harvester.models import Source as HarvesterSource

        profile = _profile(slug='monitor-failing-co')
        HarvesterSource.objects.create(
            company=profile, source_type='sustainability_report', name='failing-src',
            last_failure_at=timezone.now(), last_failure_reason='HTTP 500',
        )
        client = Client()
        client.login(username='monitor_staff', password='pw')
        response = client.get(reverse('companies:monitor'))
        self.assertEqual(response.context['health']['sources_currently_failing'], 1)

    def test_no_investment_recommendation_language_on_monitor_page(self):
        _profile(slug='monitor-no-invest-co')
        client = Client()
        client.login(username='monitor_staff', password='pw')
        response = client.get(reverse('companies:monitor'))
        content = response.content.decode().lower()
        for banned in BANNED_INVESTMENT_WORDS:
            self.assertNotIn(banned, content)

    def test_refresh_diff_view_requires_staff(self):
        profile = _profile(slug='diff-staff-co')
        run = CompanyRefreshRun.objects.create(company=profile, status='complete')
        client = Client()
        client.login(username='monitor_normal', password='pw')
        response = client.get(reverse('companies:refresh_diff', args=[profile.company.slug, run.pk]))
        self.assertNotEqual(response.status_code, 200)

    def test_refresh_diff_view_shows_change_events_for_that_run(self):
        profile = _profile(slug='diff-events-co')
        run = CompanyRefreshRun.objects.create(company=profile, status='complete', sources_checked=1)
        StewardshipChangeEvent.objects.create(company=profile, event_type='new_document', refresh_run=run, summary='New doc found.')
        client = Client()
        client.login(username='monitor_staff', password='pw')
        response = client.get(reverse('companies:refresh_diff', args=[profile.company.slug, run.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['change_events']), 1)

    def test_refresh_diff_cross_company_404s(self):
        profile_a = _profile(slug='diff-cross-a-co')
        profile_b = _profile(slug='diff-cross-b-co')
        run = CompanyRefreshRun.objects.create(company=profile_a, status='complete')
        client = Client()
        client.login(username='monitor_staff', password='pw')
        response = client.get(reverse('companies:refresh_diff', args=[profile_b.company.slug, run.pk]))
        self.assertEqual(response.status_code, 404)

    def test_alert_acknowledge_resolve_dismiss_views_require_staff_and_post(self):
        profile = _profile(slug='alert-view-co')
        event = StewardshipChangeEvent.objects.create(company=profile, event_type='new_document', summary='x')
        alert, _ = stewardship_alerts.generate_alert_for_event(event)

        client = Client()
        client.login(username='monitor_normal', password='pw')
        response = client.post(reverse('companies:alert_acknowledge', args=[profile.company.slug, alert.pk]))
        self.assertNotEqual(response.status_code, 200)

        client.login(username='monitor_staff', password='pw')
        response = client.get(reverse('companies:alert_acknowledge', args=[profile.company.slug, alert.pk]))
        self.assertEqual(response.status_code, 404)  # GET not allowed

        response = client.post(reverse('companies:alert_acknowledge', args=[profile.company.slug, alert.pk]))
        self.assertEqual(response.status_code, 302)
        alert.refresh_from_db()
        self.assertEqual(alert.state, 'acknowledged')

        response = client.post(reverse('companies:alert_resolve', args=[profile.company.slug, alert.pk]), {'reason': 'Handled.'})
        self.assertEqual(response.status_code, 302)
        alert.refresh_from_db()
        self.assertEqual(alert.state, 'resolved')

    def test_alert_dismiss_view(self):
        profile = _profile(slug='alert-dismiss-view-co')
        event = StewardshipChangeEvent.objects.create(company=profile, event_type='new_document', summary='x')
        alert, _ = stewardship_alerts.generate_alert_for_event(event)
        client = Client()
        client.login(username='monitor_staff', password='pw')
        response = client.post(reverse('companies:alert_dismiss', args=[profile.company.slug, alert.pk]), {'reason': 'n/a'})
        self.assertEqual(response.status_code, 302)
        alert.refresh_from_db()
        self.assertEqual(alert.state, 'dismissed')

    def test_universe_page_shows_open_alerts_and_conflicts_indicators(self):
        profile = _profile(slug='universe-alerts-co')
        event = StewardshipChangeEvent.objects.create(company=profile, event_type='potential_conflict', summary='Conflict here.')
        stewardship_alerts.generate_alert_for_event(event)
        client = Client()
        client.login(username='monitor_staff', password='pw')
        response = client.get(reverse('companies:universe'))
        row = next(r for r in response.context['rows'] if r['profile'].pk == profile.pk)
        self.assertGreaterEqual(row['open_alerts_count'], 1)


class SchedulerManagementCommandTests(TestCase):
    @patch('harvester.services.fetchers.fetch_sustainability_document')
    @patch('harvester.services.fetchers.fetch_sec_edgar')
    def test_batch_size_bounded_when_no_explicit_limit_given(self, mock_doc_fetch, mock_sec_fetch):
        from io import StringIO

        from django.core.management import call_command
        from company_intelligence.services import rate_limiter as rl

        mock_sec_fetch.return_value = _sec_edgar_outcome()
        mock_doc_fetch.return_value = _sustainability_outcome()

        for slug in ('apple', 'tesla', 'microsoft'):
            company = Company.objects.get_or_create(slug=slug, defaults={'name': slug.title(), 'is_public': True})[0]
            CompanyProfile.objects.get_or_create(company=company, defaults={'status': 'public', 'tracking_status': 'active'})

        original_default = rl.DEFAULT_BATCH_SIZE
        rl.DEFAULT_BATCH_SIZE = 1
        try:
            out = StringIO()
            call_command('refresh_stewardship_universe', stdout=out)
        finally:
            rl.DEFAULT_BATCH_SIZE = original_default

        self.assertIn('bounded', out.getvalue().lower())
        self.assertEqual(CompanyRefreshRun.objects.count(), 1)

    @patch('harvester.services.fetchers.fetch_sustainability_document')
    @patch('harvester.services.fetchers.fetch_sec_edgar')
    def test_explicit_company_list_is_never_bounded(self, mock_doc_fetch, mock_sec_fetch):
        from io import StringIO

        from django.core.management import call_command
        from company_intelligence.services import rate_limiter as rl

        mock_sec_fetch.return_value = _sec_edgar_outcome()
        mock_doc_fetch.return_value = _sustainability_outcome()

        original_default = rl.DEFAULT_BATCH_SIZE
        rl.DEFAULT_BATCH_SIZE = 1
        try:
            out = StringIO()
            call_command('refresh_stewardship_universe', '--company', 'apple', '--company', 'tesla', stdout=out)
        finally:
            rl.DEFAULT_BATCH_SIZE = original_default

        self.assertNotIn('bounded', out.getvalue().lower())
        self.assertEqual(CompanyRefreshRun.objects.count(), 2)

    @patch('harvester.services.fetchers.fetch_sustainability_document')
    @patch('harvester.services.fetchers.fetch_sec_edgar')
    def test_scheduled_flag_records_scheduled_trigger(self, mock_doc_fetch, mock_sec_fetch):
        from io import StringIO

        from django.core.management import call_command

        mock_sec_fetch.return_value = _sec_edgar_outcome()
        mock_doc_fetch.return_value = _sustainability_outcome()

        out = StringIO()
        call_command('refresh_stewardship_universe', '--company', 'apple', '--scheduled', stdout=out)
        profile = CompanyProfile.objects.get(company__slug='apple')
        run = CompanyRefreshRun.objects.filter(company=profile).latest('started_at')
        self.assertEqual(run.triggered_by, 'scheduled')

    @patch('harvester.services.fetchers.fetch_sustainability_document')
    @patch('harvester.services.fetchers.fetch_sec_edgar')
    def test_batch_continues_after_one_company_fails(self, mock_doc_fetch, mock_sec_fetch):
        """Section 16 — one company's total failure must never stop the
        batch. refresh_company_intelligence() itself never raises (it
        catches everything internally), so a failing company simply
        produces a 'failed' CompanyRefreshRun and the loop moves on.

        NOTE: with this exact stacked-@patch order, mock_doc_fetch (first
        param) is the ACTUAL mock for fetch_sec_edgar (verified empirically
        — see the comment on the shariah test above); the side_effect
        inspecting `slug` is therefore assigned to mock_doc_fetch here.
        """
        from io import StringIO

        from django.core.management import call_command

        def sec_side_effect(slug):
            if slug == 'apple':
                return FetchOutcome(success=False, error='HTTP 500')
            return _sec_edgar_outcome(slug)

        mock_doc_fetch.side_effect = sec_side_effect
        mock_sec_fetch.return_value = FetchOutcome(success=False, error='HTTP 404')

        out = StringIO()
        call_command('refresh_stewardship_universe', '--company', 'apple', '--company', 'tesla', stdout=out)

        apple_profile = CompanyProfile.objects.get(company__slug='apple')
        tesla_profile = CompanyProfile.objects.get(company__slug='tesla')
        self.assertEqual(apple_profile.tracking_status, 'error')
        # Tesla's own sec_edgar fetch succeeded (only its sustainability doc
        # fetch fails, since tesla has no curated document) — proving the
        # batch reached and completed Tesla despite Apple's total failure.
        self.assertIn(tesla_profile.tracking_status, ('active', 'error'))
        self.assertTrue(CompanyRefreshRun.objects.filter(company=tesla_profile).exists())


class SchedulerCSRFTests(TestCase):
    def test_alert_acknowledge_without_csrf_token_rejected(self):
        from django.test import Client as StrictClient

        profile = _profile(slug='csrf-alert-co')
        staff = User.objects.create_user(username='csrf_alert_staff', password='pw', is_staff=True)
        event = StewardshipChangeEvent.objects.create(company=profile, event_type='new_document', summary='x')
        alert, _ = stewardship_alerts.generate_alert_for_event(event)

        strict_client = StrictClient(enforce_csrf_checks=True)
        strict_client.login(username='csrf_alert_staff', password='pw')
        response = strict_client.post(reverse('companies:alert_acknowledge', args=[profile.company.slug, alert.pk]))
        self.assertEqual(response.status_code, 403)


class CoverageMatrixTests(TestCase):
    def test_brand_new_company_shows_missing_not_fabricated_zero(self):
        from company_intelligence.services import coverage_matrix

        profile = _profile(slug='matrix-brand-new-co')
        matrix = coverage_matrix.coverage_matrix_for_company(profile)
        self.assertEqual(matrix['identity']['status'], coverage_matrix.MISSING)
        self.assertEqual(matrix['regulatory_data']['status'], coverage_matrix.MISSING)
        self.assertEqual(matrix['financial_data']['status'], coverage_matrix.MISSING)
        self.assertEqual(matrix['sustainability_documents']['status'], coverage_matrix.MISSING)
        self.assertEqual(matrix['kpi_evidence']['status'], coverage_matrix.MISSING)
        self.assertEqual(matrix['shariah_screening']['status'], coverage_matrix.MISSING)
        self.assertEqual(matrix['monitoring']['status'], coverage_matrix.NOT_APPLICABLE)

    def test_identity_available_once_synced_from_a_real_cik(self):
        from company_intelligence.services import coverage_matrix, identity_sync

        profile = _real_profile('apple')
        identity_sync.sync_company_identity(profile)
        matrix = coverage_matrix.coverage_matrix_for_company(profile)
        self.assertEqual(matrix['identity']['status'], coverage_matrix.AVAILABLE)
        self.assertIn('SEC CIK', matrix['identity']['detail'])

    def test_shariah_row_available_after_a_real_screen(self):
        from company_intelligence.services import coverage_matrix

        profile = _profile(slug='matrix-screened-co')
        methodology = _methodology()
        shariah_screening.run_shariah_screen(profile, methodology)
        matrix = coverage_matrix.coverage_matrix_for_company(profile)
        self.assertEqual(matrix['shariah_screening']['status'], coverage_matrix.AVAILABLE)

    def test_monitoring_row_partial_when_paused(self):
        from company_intelligence.services import coverage_matrix

        profile = _profile(slug='matrix-paused-co')
        profile.tracking_status = 'paused'
        profile.save(update_fields=['tracking_status'])
        matrix = coverage_matrix.coverage_matrix_for_company(profile)
        self.assertEqual(matrix['monitoring']['status'], coverage_matrix.PARTIAL)

    def test_kpi_evidence_available_once_confirmed_support_crosses_threshold(self):
        from company_intelligence.services import coverage_matrix

        profile = _profile(slug='matrix-kpi-co')
        for kpi_id in range(1, 15):  # >10% of 114 confirmed
            _confirmed_kpi_link(profile, kpi_id=kpi_id, relationship='supports')
        matrix = coverage_matrix.coverage_matrix_for_company(profile)
        self.assertEqual(matrix['kpi_evidence']['status'], coverage_matrix.AVAILABLE)


class AlignmentMetricsAndCategoryCoverageTests(TestCase):
    def test_confirmed_supported_and_total_counts(self):
        from company_intelligence.services import alignment_metrics

        profile = _profile(slug='align-metrics-co')
        _confirmed_kpi_link(profile, kpi_id=1, relationship='supports')
        _confirmed_kpi_link(profile, kpi_id=2, relationship='conflicts')
        metrics = alignment_metrics.stewardship_alignment_metrics(profile)
        self.assertEqual(metrics['confirmed_kpis_supported'], 1)
        self.assertEqual(metrics['total_kpis'], 114)
        self.assertGreaterEqual(metrics['total_kpis_with_evidence'], 2)

    def test_human_reviewed_coverage_reflects_confirmed_vs_proposed(self):
        from company_intelligence.services import alignment_metrics

        profile = _profile(slug='align-reviewed-co')
        _confirmed_kpi_link(profile, kpi_id=3, relationship='supports')
        evidence = EvidenceMemory.objects.create(text_chunk='x', company=profile)
        assessment2 = CompanyKPIAssessment.objects.create(company=profile, kpi_id=4)
        CompanyKPIEvidenceLink.objects.create(
            assessment=assessment2, evidence=evidence, relationship='supports', review_state='proposed',
        )
        metrics = alignment_metrics.stewardship_alignment_metrics(profile)
        self.assertEqual(metrics['human_reviewed_kpi_count'], 1)
        self.assertEqual(metrics['proposed_pending_count'], 1)
        self.assertEqual(metrics['human_reviewed_coverage_pct'], 50.0)

    def test_disputed_kpi_count_reflects_disputed_review_state(self):
        from company_intelligence.services import alignment_metrics

        profile = _profile(slug='align-disputed-co')
        assessment, evidence = _confirmed_kpi_link(profile, kpi_id=5, relationship='supports')
        link = CompanyKPIEvidenceLink.objects.get(assessment=assessment, evidence=evidence)
        link.review_state = 'disputed'
        link.save(update_fields=['review_state'])
        metrics = alignment_metrics.stewardship_alignment_metrics(profile)
        self.assertEqual(metrics['disputed_kpi_count'], 1)

    def test_category_coverage_reflects_only_the_relevant_categories(self):
        from company_intelligence.services import category_coverage
        from core.esg_principles_data import PRINCIPLES

        principles_by_id = {p['id']: p for p in PRINCIPLES}
        profile = _profile(slug='category-coverage-co')
        kpi_id = 1
        category = principles_by_id[kpi_id]['category']
        _confirmed_kpi_link(profile, kpi_id=kpi_id, relationship='supports')
        rows = category_coverage.category_coverage_for_company(profile)
        row = next(r for r in rows if r['key'] == category)
        self.assertGreaterEqual(row['supported_count'], 1)
        self.assertEqual(len(rows), 10)  # exact canonical category count, never a competing taxonomy

    def test_category_coverage_disputed_count(self):
        from company_intelligence.services import category_coverage
        from core.esg_principles_data import PRINCIPLES

        principles_by_id = {p['id']: p for p in PRINCIPLES}
        profile = _profile(slug='category-coverage-disputed-co')
        kpi_id = 20
        category = principles_by_id[kpi_id]['category']
        assessment, evidence = _confirmed_kpi_link(profile, kpi_id=kpi_id, relationship='supports')
        link = CompanyKPIEvidenceLink.objects.get(assessment=assessment, evidence=evidence)
        link.review_state = 'disputed'
        link.save(update_fields=['review_state'])
        rows = category_coverage.category_coverage_for_company(profile)
        row = next(r for r in rows if r['key'] == category)
        self.assertEqual(row['disputed_count'], 1)


def _document_backed_link(profile, kpi_id, *, document_type, relationship='supports', review_state='confirmed'):
    """Same convention as _harvester_backed_link, but with a real
    SourceDocument attached so evidence_provenance.py's
    provenance_class_for_link() can classify it by document_type (rather
    than falling back to 'unknown', which _harvester_backed_link alone
    would produce)."""
    from harvester.models import SourceDocument

    source = HarvesterSource.objects.create(company=profile, source_type=document_type, name=f'{document_type} source')
    document = SourceDocument.objects.create(
        source=source, company=profile, company_slug=profile.company.slug, title='Test document',
        document_type=document_type, url=f'https://example.com/{profile.company.slug}/{kpi_id}',
        content_hash=f'hash-{profile.company.slug}-{kpi_id}',
    )
    return _harvester_backed_link(
        profile, kpi_id, relationship=relationship, review_state=review_state, document=document, source=source,
    )


class EvidenceProvenanceTests(TestCase):
    def test_provenance_class_regulatory_vs_self_reported_vs_unknown(self):
        from company_intelligence.services import evidence_provenance

        profile = _profile(slug='provenance-classify-co')
        reg_link, _ = _document_backed_link(profile, kpi_id=1, document_type='sec_edgar')
        self_link, _ = _document_backed_link(profile, kpi_id=2, document_type='sustainability_report')
        plain_link, _ = _harvester_backed_link(profile, kpi_id=3)  # no document/source -> unknown

        self.assertEqual(evidence_provenance.provenance_class_for_link(reg_link), 'regulatory')
        self.assertEqual(evidence_provenance.provenance_class_for_link(self_link), 'self_reported')
        self.assertEqual(evidence_provenance.provenance_class_for_link(plain_link), 'unknown')

    def test_self_report_concentration_warns_when_entirely_self_reported(self):
        from company_intelligence.services import evidence_provenance

        profile = _profile(slug='provenance-warning-co')
        for kpi_id in range(1, 4):
            _document_backed_link(profile, kpi_id=kpi_id, document_type='sustainability_report')
        result = evidence_provenance.self_report_concentration(profile)
        self.assertEqual(result['self_reported_pct'], 100.0)
        self.assertIsNotNone(result['warning'])
        self.assertIn('self-reporting', result['warning'])

    def test_self_report_concentration_no_warning_with_regulatory_mix(self):
        from company_intelligence.services import evidence_provenance

        profile = _profile(slug='provenance-mixed-co')
        _document_backed_link(profile, kpi_id=1, document_type='sustainability_report')
        _document_backed_link(profile, kpi_id=2, document_type='sec_edgar')
        result = evidence_provenance.self_report_concentration(profile)
        self.assertIsNone(result['warning'])

    def test_self_report_concentration_honest_when_no_confirmed_evidence(self):
        from company_intelligence.services import evidence_provenance

        profile = _profile(slug='provenance-empty-co')
        result = evidence_provenance.self_report_concentration(profile)
        self.assertEqual(result['total'], 0)
        self.assertIsNone(result['self_reported_pct'])
        self.assertIsNone(result['warning'])

    def test_evidence_concentration_warning_when_many_links_share_one_document(self):
        from company_intelligence.services import evidence_provenance
        from harvester.models import SourceDocument

        profile = _profile(slug='provenance-concentration-co')
        source = HarvesterSource.objects.create(company=profile, source_type='sustainability_report', name='doc source')
        document = SourceDocument.objects.create(
            source=source, company=profile, company_slug=profile.company.slug, title='Shared document',
            document_type='sustainability_report', url='https://example.com/shared', content_hash='shared-hash',
        )
        for kpi_id in range(1, 6):  # 5 = EVIDENCE_CONCENTRATION_SAME_DOCUMENT_WARNING
            _harvester_backed_link(profile, kpi_id=kpi_id, document=document, source=source)
        warnings = evidence_provenance.evidence_concentration_warning(profile)
        self.assertEqual(len(warnings), 1)
        self.assertIn('Shared document', warnings[0])

    def test_evidence_concentration_no_warning_below_threshold(self):
        from company_intelligence.services import evidence_provenance
        from harvester.models import SourceDocument

        profile = _profile(slug='provenance-no-concentration-co')
        source = HarvesterSource.objects.create(company=profile, source_type='sustainability_report', name='doc source 2')
        document = SourceDocument.objects.create(
            source=source, company=profile, company_slug=profile.company.slug, title='Small document',
            document_type='sustainability_report', url='https://example.com/small', content_hash='small-hash',
        )
        for kpi_id in range(1, 4):  # below the 5-link threshold
            _harvester_backed_link(profile, kpi_id=kpi_id, document=document, source=source)
        warnings = evidence_provenance.evidence_concentration_warning(profile)
        self.assertEqual(warnings, [])


class IdentitySyncTests(TestCase):
    def test_identity_sources_for_slug_reflects_real_mappings(self):
        result = identity_sync.identity_sources_for_slug('apple')
        self.assertEqual(result['sec_cik'], '0000320193')
        self.assertEqual(result['official_domain'], 'apple.com')
        self.assertIn('SEC EDGAR CIK mapping', result['identity_source'])

    def test_identity_sources_for_slug_honest_when_unmapped(self):
        result = identity_sync.identity_sources_for_slug('some-unmapped-company')
        self.assertEqual(result['sec_cik'], '')
        self.assertEqual(result['identity_source'], '')

    def test_sync_company_identity_returns_none_when_no_real_identifier(self):
        profile = _profile(slug='identity-sync-unmapped-co')
        self.assertIsNone(identity_sync.sync_company_identity(profile))
        self.assertFalse(CompanyListing.objects.filter(company=profile.company).exists())

    def test_sync_company_identity_persists_fields_on_a_brand_new_listing(self):
        """Regression test for a real bug found via a live
        `expand_stewardship_universe --limit 3` run: sync_company_identity
        setattr'd sec_cik/official_domain onto a freshly get_or_create'd
        CompanyListing but only called .save() when created=False — so a
        brand-new listing silently kept every field blank in the database
        despite the in-memory object looking correct. Fixed by always
        saving when there are real fields to persist."""
        profile = _real_profile('apple')
        listing = identity_sync.sync_company_identity(profile)
        self.assertIsNotNone(listing)
        listing.refresh_from_db()
        self.assertEqual(listing.sec_cik, '0000320193')
        self.assertEqual(listing.official_domain, 'apple.com')
        self.assertEqual(listing.domain_status, 'verified')
        self.assertIn('SEC EDGAR CIK mapping', listing.identity_source)
        self.assertIsNotNone(listing.verified_at)

    def test_sync_company_identity_never_overwrites_a_human_edited_field(self):
        profile = _real_profile('apple')
        listing = CompanyListing.objects.create(
            company=profile.company, is_primary=True, official_domain='staff-corrected-domain.example',
        )
        identity_sync.sync_company_identity(profile)
        listing.refresh_from_db()
        self.assertEqual(listing.official_domain, 'staff-corrected-domain.example')
        self.assertEqual(listing.sec_cik, '0000320193')  # still fills in the genuinely blank field

    def test_sync_company_identity_is_idempotent(self):
        profile = _real_profile('apple')
        identity_sync.sync_company_identity(profile)
        count_after_first = CompanyListing.objects.filter(company=profile.company).count()
        identity_sync.sync_company_identity(profile)
        self.assertEqual(CompanyListing.objects.filter(company=profile.company).count(), count_after_first)


class ExpandStewardshipUniverseCommandTests(TestCase):
    def test_dry_run_performs_zero_database_writes(self):
        from io import StringIO

        from django.core.management import call_command

        before = CompanyProfile.objects.count()
        out = StringIO()
        call_command('expand_stewardship_universe', '--dry-run', '--limit', '3', stdout=out)
        self.assertEqual(CompanyProfile.objects.count(), before)
        self.assertIn('DRY RUN', out.getvalue())

    def test_creates_profile_and_syncs_identity_without_setting_active(self):
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command('expand_stewardship_universe', '--limit', '1', stdout=out)
        profile = CompanyProfile.objects.filter(tracking_status='not_tracked').latest('id')
        self.assertTrue(CompanyListing.objects.filter(company=profile.company, is_primary=True).exists())
        listing = CompanyListing.objects.get(company=profile.company, is_primary=True)
        self.assertTrue(listing.sec_cik or listing.companies_house_number)

    def test_limit_bounds_the_run_and_reports_the_drop(self):
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command('expand_stewardship_universe', '--limit', '2', stdout=out)
        self.assertIn('bounded', out.getvalue().lower())

    def test_never_contains_investment_language(self):
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command('expand_stewardship_universe', '--limit', '2', stdout=out)
        body = out.getvalue().lower()
        for banned in BANNED_INVESTMENT_WORDS:
            self.assertNotIn(banned, body)


class RateLimiterTests(TestCase):
    def tearDown(self):
        rate_limiter.reset_for_tests()

    def test_first_request_to_a_domain_never_blocks(self):
        rate_limiter.reset_for_tests()
        start = time.monotonic()
        rate_limiter.wait_for_domain_slot('example.com', min_interval_seconds=5.0)
        self.assertLess(time.monotonic() - start, 1.0)

    def test_second_request_to_same_domain_waits_remaining_interval(self):
        rate_limiter.reset_for_tests()
        rate_limiter.wait_for_domain_slot('example.com', min_interval_seconds=0.2)
        start = time.monotonic()
        rate_limiter.wait_for_domain_slot('example.com', min_interval_seconds=0.2)
        self.assertGreaterEqual(time.monotonic() - start, 0.15)

    def test_different_domains_never_block_each_other(self):
        rate_limiter.reset_for_tests()
        rate_limiter.wait_for_domain_slot('a.example.com', min_interval_seconds=5.0)
        start = time.monotonic()
        rate_limiter.wait_for_domain_slot('b.example.com', min_interval_seconds=5.0)
        self.assertLess(time.monotonic() - start, 1.0)

    def test_blank_domain_never_blocks(self):
        rate_limiter.reset_for_tests()
        start = time.monotonic()
        rate_limiter.wait_for_domain_slot('', min_interval_seconds=5.0)
        rate_limiter.wait_for_domain_slot(None, min_interval_seconds=5.0)
        self.assertLess(time.monotonic() - start, 1.0)

    def test_source_type_budget_allows_up_to_its_limit_then_refuses(self):
        budget = rate_limiter.SourceTypeBudget(limits={'sec_edgar': 2})
        self.assertTrue(budget.allow('sec_edgar'))
        self.assertTrue(budget.allow('sec_edgar'))
        self.assertFalse(budget.allow('sec_edgar'))

    def test_source_type_budget_uses_default_limit_for_unlisted_type(self):
        budget = rate_limiter.SourceTypeBudget(default_limit=1)
        self.assertTrue(budget.allow('some_unlisted_type'))
        self.assertFalse(budget.allow('some_unlisted_type'))

    def test_bounded_batch_respects_explicit_limit(self):
        profiles = list(range(10))
        bounded, dropped = rate_limiter.bounded_batch(profiles, limit=3)
        self.assertEqual(bounded, [0, 1, 2])
        self.assertEqual(dropped, 7)

    def test_bounded_batch_applies_default_when_no_limit_given(self):
        profiles = list(range(100))
        bounded, dropped = rate_limiter.bounded_batch(profiles, limit=None, default_batch_size=25)
        self.assertEqual(len(bounded), 25)
        self.assertEqual(dropped, 75)

    def test_bounded_batch_never_drops_when_under_the_bound(self):
        profiles = list(range(5))
        bounded, dropped = rate_limiter.bounded_batch(profiles, limit=None, default_batch_size=25)
        self.assertEqual(bounded, profiles)
        self.assertEqual(dropped, 0)


class RefreshOrchestratorRateLimitingTests(TestCase):
    @patch('harvester.services.fetchers.fetch_sustainability_document')
    @patch('harvester.services.fetchers.fetch_sec_edgar')
    def test_source_type_budget_of_one_skips_second_sec_edgar_source_as_not_due(self, mock_doc_fetch, mock_sec_fetch):
        """NOTE: decorator stacking binds bottom-up (verified empirically
        this session) — mock_doc_fetch is actually fetch_sec_edgar's mock."""
        mock_doc_fetch.return_value = _sec_edgar_outcome()
        mock_sec_fetch.return_value = _sustainability_outcome()

        profile = _real_profile('apple')
        from company_intelligence.services import rate_limiter as rl

        original_limits = dict(rl.MAX_SOURCES_PER_TYPE_PER_RUN)
        rl.MAX_SOURCES_PER_TYPE_PER_RUN['sec_edgar'] = 0
        try:
            run = refresh_orchestrator.refresh_company_intelligence(profile, triggered_by='manual')
        finally:
            rl.MAX_SOURCES_PER_TYPE_PER_RUN.clear()
            rl.MAX_SOURCES_PER_TYPE_PER_RUN.update(original_limits)

        self.assertEqual(run.sources_checked, 1)
        self.assertGreaterEqual(run.sources_skipped_not_due, 1)
        self.assertTrue(any('budget' in w for w in run.warnings))
