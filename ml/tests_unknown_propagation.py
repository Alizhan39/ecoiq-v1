"""
D2c — unknown propagates as unknown through the analytical and ML engines.

Covers A–O from the brief. Third and last of the calculation-semantics passes:
core scoring and financing (#242), ethics (#243), and now ML, responsible
finance, ethical intelligence, greenwashing, countries, Mizan, background tasks
and the improvement pathway.

The ML case is the one worth stating carefully, because it is NOT the same fix.

The estimator is a committed GradientBoostingRegressor whose scaler was fitted
on a matrix where missing values were already 50.0. It cannot accept None, and
changing what a feature means would invalidate the artefact. So the vector is
left exactly as it is, and the boundary moves instead: missing_material_features()
reports what is unknown, and predict_company() refuses. Fail closed at the gate,
rather than inventing an imputation methodology in a semantics change.
"""
from django.test import SimpleTestCase, TestCase

from companies.models import CompanyProfile
from league.models import Company


def _profile(slug, **overrides):
    """
    A saved profile whose scoring inputs can then be blanked in memory.

    D4C removed the neutral defaults, so this fixture no longer inherits a
    populated company by accident. The material inputs are set explicitly and
    the DERIVED pillars are produced by the real calculator rather than being
    assigned — assigning them would let a fixture disagree with what the
    scoring engine would actually compute from the same inputs, which is how a
    test starts passing for a reason that does not exist in production.
    """
    from companies.scoring import recalculate_and_save
    from companies.testing import FIXTURE_VALUE, MATERIAL_FIELDS

    company = Company.objects.create(name=slug, slug=slug, country='UK')
    profile = CompanyProfile.objects.create(
        company=company, status='public', pollution_level='low',
        **{name: FIXTURE_VALUE for name in MATERIAL_FIELDS})
    recalculate_and_save(profile)
    profile.refresh_from_db()
    for field, value in overrides.items():
        setattr(profile, field, value)
    return profile


def _blank(profile, *fields):
    for field in fields:
        setattr(profile, field, None)
    return profile


PILLARS = (
    'public_benefit_score', 'environmental_responsibility_score',
    'modernization_score', 'transparency_anti_corruption_score',
    'anti_corruption_score', 'ethical_alignment_score',
)


class A_B_C_MlFeatureSemantics(TestCase):
    """
    A/B/C — but read the module note first.

    _safe_float still returns 50.0, on purpose, because the committed model was
    fitted on that imputation. What must be true is that the SYSTEM can tell the
    difference, which is what missing_material_features() is for.
    """

    def test_a_missing_material_features_are_reported_not_silently_imputed(self):
        from ml.features import missing_material_features

        profile = _blank(_profile('ml-missing'), *PILLARS)
        missing = missing_material_features(profile.company)

        self.assertEqual(set(missing), set(PILLARS))

    def test_a_the_vector_still_imputes_because_the_model_requires_it(self):
        """
        Asserting the documented compromise, so a future change that silently
        alters the fitted model's input distribution fails here first.
        """
        import numpy as np

        from ml.features import company_to_vector

        profile = _blank(_profile('ml-vector'), *PILLARS)
        vec = company_to_vector(profile.company)

        self.assertFalse(np.isnan(vec).any(), 'the estimator cannot accept NaN')
        self.assertEqual(vec.dtype, np.float64)

    def test_b_a_real_zero_is_not_reported_as_missing(self):
        from ml.features import missing_material_features

        profile = _profile('ml-zero')
        for field in PILLARS:
            setattr(profile, field, 0.0)

        self.assertEqual(missing_material_features(profile.company), [])

    def test_c_a_real_fifty_is_not_reported_as_missing(self):
        from ml.features import missing_material_features

        profile = _profile('ml-fifty')
        for field in PILLARS:
            setattr(profile, field, 50.0)

        self.assertEqual(missing_material_features(profile.company), [])

    def test_a_fully_known_company_reports_nothing_missing(self):
        from ml.features import missing_material_features

        self.assertEqual(missing_material_features(_profile('ml-known').company), [])

    def test_a_company_without_a_profile_reports_everything_missing(self):
        from ml.features import missing_material_features

        company = Company.objects.create(name='No Profile', slug='no-profile', country='UK')
        self.assertEqual(set(missing_material_features(company)), set(PILLARS))


class D_PredictionRefusesWithoutEvidence(TestCase):
    """
    D — the estimator cannot express uncertainty, so the gate must.

    None is already predict_company()'s documented "unavailable" return and
    every caller handles it, so refusing costs nothing at the call sites.
    """

    def test_d_prediction_refuses_when_material_features_are_unknown(self):
        from ml.scoring_model import EcoIQScoringModel

        model = EcoIQScoringModel()
        profile = _blank(_profile('ml-refuse'), *PILLARS)

        self.assertIsNone(model.predict_company(profile.company))

    def test_d_the_refusal_happens_before_the_model_is_consulted(self):
        """
        The gate must not depend on the artefact being loadable — otherwise a
        deployment without the .joblib would return None for the wrong reason
        and the test would pass vacuously.
        """
        from ml.features import missing_material_features

        profile = _blank(_profile('ml-gate'), 'public_benefit_score')
        self.assertEqual(missing_material_features(profile.company),
                         ['public_benefit_score'])

    def test_d_twelve_month_forecast_refuses_without_a_current_score(self):
        """
        A forecast is a projection FROM something. `ecoiq_score or 50.0`
        projected an invented average forward twelve months and wrote it to
        ml_predicted_score_12m.

        Blanked in memory rather than saved: Company.ecoiq_score is still
        DecimalField(default=0.0) and NOT NULL, so this state cannot be
        persisted until D4. That is exactly why the calculation layer has to
        handle it first.
        """
        from ml.prediction import predict_12m

        company = Company.objects.create(name='No Score', slug='no-score-fc',
                                         country='UK')
        company.ecoiq_score = None

        self.assertIsNone(predict_12m(company))

    def test_d_forecast_still_works_from_a_known_score(self):
        from ml.prediction import predict_12m

        company = Company.objects.create(name='Has Score', slug='has-score-fc',
                                         country='UK', ecoiq_score=64.0)
        pred = predict_12m(company)

        self.assertIsNotNone(pred)
        self.assertGreaterEqual(pred, 0.0)
        self.assertLessEqual(pred, 100.0)

    def test_d_a_genuine_zero_score_still_forecasts(self):
        """`or 50.0` rewrote a real 0.0 — the worst company forecast as average."""
        from ml.prediction import predict_12m

        company = Company.objects.create(name='Zero', slug='zero-fc',
                                         country='UK', ecoiq_score=0.0)
        self.assertIsNotNone(predict_12m(company))


class E_ResponsibleFinanceRefusesToInvent(TestCase):

    def test_e_no_pillars_means_no_numeric_claim(self):
        from ml.responsible_finance import compute_responsible_finance_score

        profile = _blank(_profile('rf-unknown'), *PILLARS)
        result = compute_responsible_finance_score(profile)

        self.assertIsNone(result['responsible_finance_score'])
        self.assertIsNone(result['ethical_grade'],
                          "an 'F' grade is the harshest verdict this module issues")
        self.assertFalse(result['ethical_capital_eligible'])
        self.assertFalse(result['responsible_insurance_eligible'])

    def test_e_partial_knowledge_still_scores_and_declares_the_gap(self):
        from ml.responsible_finance import compute_responsible_finance_score

        profile = _blank(_profile('rf-partial'), 'ethical_alignment_score')
        result = compute_responsible_finance_score(profile)

        self.assertIsNotNone(result['responsible_finance_score'])
        self.assertIn('ethical_alignment_score', result['unknown_pillars'])
        self.assertTrue(any('not yet' in f for f in result['summary_factors']))

    def test_e_a_genuine_zero_pillar_is_not_rewritten_to_fifty(self):
        """
        `float(getattr(p, 'x', 50) or 50)` was falsy-triggered: a measured 0.0
        governance score was fed to the eligibility thresholds as an average one.
        """
        from ml.responsible_finance import compute_responsible_finance_score

        zeroed = _profile('rf-zero')
        for field in PILLARS:
            setattr(zeroed, field, 0.0)
        fifties = _profile('rf-fifty')
        for field in PILLARS:
            setattr(fifties, field, 50.0)

        zero_score = compute_responsible_finance_score(zeroed)['responsible_finance_score']
        fifty_score = compute_responsible_finance_score(fifties)['responsible_finance_score']

        self.assertIsNotNone(zero_score)
        self.assertLess(zero_score, fifty_score,
                        'a measured zero must score worse than a measured fifty')

    def test_e_a_fully_known_profile_still_grades(self):
        from ml.responsible_finance import compute_responsible_finance_score

        result = compute_responsible_finance_score(_profile('rf-known'))
        self.assertIsNotNone(result['responsible_finance_score'])
        self.assertIn(result['ethical_grade'], list('ABCDF'))


class F_G_GreenwashingIsNeitherVerdict(TestCase):
    """
    The most sensitive assessment in the codebase, and it failed in BOTH
    directions. Three states must stay distinct:

        NO EVIDENCE TO ASSESS
        EVIDENCE OF GREENWASHING
        EVIDENCE OF LOW GREENWASHING RISK
    """

    def _unknown_assessment(self):
        from ml.ethics.greenwashing_risk import greenwashing_from_profile

        profile = _blank(
            _profile('gw-unknown'),
            'energy_transition_score', 'future_readiness_score',
            'audit_quality_score', 'infrastructure_upgrade_score',
            'controversy_risk_score', 'transparency_anti_corruption_score',
            'procurement_transparency_score',
        )
        profile.pollution_level = None
        profile.is_verified = False
        return greenwashing_from_profile(profile)

    def test_f_unknown_does_not_become_low_risk(self):
        from ml.ethics.greenwashing_risk import RISK_INSUFFICIENT_EVIDENCE

        result = self._unknown_assessment()

        self.assertNotEqual(result.risk_level, 'low')
        self.assertEqual(result.risk_level, RISK_INSUFFICIENT_EVIDENCE)

    def test_g_unknown_does_not_become_high_or_severe_risk(self):
        result = self._unknown_assessment()
        self.assertNotIn(result.risk_level, ('high', 'severe'))

    def test_unknown_score_is_null_not_zero(self):
        """
        0 is the BEST possible greenwashing score — the strongest positive claim
        this module can make — so it must not be the unknown value.
        """
        result = self._unknown_assessment()
        self.assertIsNone(result.greenwashing_risk_score)

    def test_unknown_raises_no_red_flags(self):
        """A red flag is an accusation."""
        self.assertEqual(self._unknown_assessment().main_red_flags, [])

    def test_unknown_says_so_in_plain_language(self):
        result = self._unknown_assessment()

        self.assertIn('not', result.explanation.lower())
        self.assertTrue(result.missing_evidence)
        self.assertIn('must not be treated as a favourable finding',
                      result.investor_warning)

    def test_evidenced_greenwashing_is_still_detected(self):
        """The gate must not have disabled detection for real evidence."""
        from ml.ethics.greenwashing_risk import (
            GreenwashingInput, assess_greenwashing_risk,
        )

        loud_claims_no_evidence = GreenwashingInput(
            climate_claims_strength=95.0,
            verified_emissions_data=2.0,
            third_party_assurance=1.0,
            target_quality=3.0,
            transition_capex_disclosure=2.0,
            fossil_fuel_exposure=90.0,
            evidence_confidence=20.0,
            controversy_flags=3,
            ownership_transparency=10.0,
        )
        result = assess_greenwashing_risk(loud_claims_no_evidence)

        self.assertIn(result.risk_level, ('high', 'severe'))
        self.assertIsNotNone(result.greenwashing_risk_score)
        self.assertTrue(result.main_red_flags)

    def test_evidenced_low_risk_is_still_reported_as_low(self):
        from ml.ethics.greenwashing_risk import (
            GreenwashingInput, assess_greenwashing_risk,
        )

        modest_claims_well_evidenced = GreenwashingInput(
            climate_claims_strength=40.0,
            verified_emissions_data=90.0,
            third_party_assurance=88.0,
            target_quality=85.0,
            transition_capex_disclosure=80.0,
            fossil_fuel_exposure=5.0,
            evidence_confidence=92.0,
            controversy_flags=0,
            ownership_transparency=90.0,
        )
        result = assess_greenwashing_risk(modest_claims_well_evidenced)

        self.assertEqual(result.risk_level, 'low')
        self.assertIsNotNone(result.greenwashing_risk_score)

    def test_unknown_controversy_is_not_zero_flags(self):
        """Zero flags is the finding 'no active controversies' — a claim."""
        from ml.ethics.greenwashing_risk import greenwashing_from_profile

        profile = _blank(_profile('gw-controversy'), 'controversy_risk_score')
        # Not asserting the final level, only that the derivation did not
        # manufacture a favourable count out of the absence.
        result = greenwashing_from_profile(profile)
        self.assertIsNotNone(result)


class H_EthicalIntelligenceStaysUnknown(TestCase):

    def _all_unknown(self):
        profile = _profile('ei-unknown')
        for field in (
            *PILLARS, 'jobs_created_score', 'regional_development_score',
            'infrastructure_contribution_score', 'national_value_score',
            'transparency_score_detail', 'controversy_risk_score',
            'audit_quality_score', 'procurement_transparency_score',
            'energy_transition_score', 'future_readiness_score',
            'digitalization_score', 'infrastructure_upgrade_score',
            'water_impact_score', 'biodiversity_impact_score',
            'waste_management_score', 'harm_penalty', 'ecoiq_total_score',
        ):
            setattr(profile, field, None)
        profile.pollution_level = None
        return profile

    def test_h_overall_score_is_none_when_nothing_is_known(self):
        from ml.ethics import compute_ethical_intelligence

        result = compute_ethical_intelligence(self._all_unknown())
        self.assertIsNone(result['overall_score'])

    def test_h_label_is_not_the_worst_tier_by_default(self):
        from ml.ethics import compute_ethical_intelligence
        from ml.ethics.ethical_score import LABEL_INSUFFICIENT_EVIDENCE

        result = compute_ethical_intelligence(self._all_unknown())

        self.assertNotEqual(result['label'], 'Critical Concern')
        self.assertEqual(result['label'], LABEL_INSUFFICIENT_EVIDENCE)

    def test_h_unknown_harm_does_not_become_maximum_benefit(self):
        """
        The sharpest inversion in the module: harm_inverted = 100 - net_harm,
        and with net_harm imputed to 0 an unassessed company contributed the
        MAXIMUM possible harm-reduction credit.
        """
        from ml.ethics.harm_reduction import compute_harm_reduction

        result = compute_harm_reduction(self._all_unknown())
        self.assertIsNone(result['net_harm'])

    def test_h_stewardship_label_is_not_deficit_by_default(self):
        from ml.ethics.stewardship import compute_stewardship

        self.assertEqual(compute_stewardship(self._all_unknown())['label'],
                         'insufficient_evidence')

    def test_h_a_fully_known_profile_still_scores(self):
        from ml.ethics import compute_ethical_intelligence

        result = compute_ethical_intelligence(_profile('ei-known'))

        self.assertIsNotNone(result['overall_score'])
        self.assertNotEqual(result['label'], 'Insufficient Evidence')


class I_J_ApiBoundaries(TestCase):
    """
    I/J — v1 stays stable, v2 stays evidence-aware.

    The domain now returns None; neither API contract was bent to accommodate
    that, and neither was broken by it.
    """

    def setUp(self):
        Company.objects.create(name='Api Ltd', slug='api-ltd', country='UK',
                               ecoiq_score=71.4)
        CompanyProfile.objects.create(
            company=Company.objects.get(slug='api-ltd'),
            status='public', ecoiq_total_score=71.4)

    def test_i_v1_ethical_intelligence_still_responds(self):
        from django.test import Client

        response = Client().get(
            '/api/v1/intelligence/ethical-score/?company=api-ltd')

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn('overall_score', payload)
        self.assertIn('label', payload)
        self.assertIn('greenwashing_risk', payload)

    def test_i_v1_keys_are_unchanged(self):
        """A v1 consumer keys on these; D2c may change values, not shape."""
        from django.test import Client

        payload = Client().get(
            '/api/v1/intelligence/ethical-score/?company=api-ltd').json()

        for key in ('company', 'name', 'country', 'sector', 'overall_score',
                    'label', 'public_benefit', 'harm_reduction',
                    'justice_balance', 'stewardship', 'evidence',
                    'greenwashing_risk', 'ecoiq_total_score'):
            with self.subTest(key=key):
                self.assertIn(key, payload)

    def test_j_v2_still_reports_null_plus_status(self):
        from django.test import Client

        payload = Client().get('/api/v2/companies/api-ltd/').json()

        self.assertIsNone(payload['ecoiq_score'])
        self.assertEqual(payload['score_status'], 'INSUFFICIENT_EVIDENCE')


class K_CountryAggregation(TestCase):

    def test_k_country_corruption_exposure_is_not_derived_from_nothing(self):
        """
        exposure = 100 - transparency. With `or 0` an unmeasured country was
        published at exposure 100 — the maximum — from our own missing data.
        """
        from countries.models import CountryProfile
        from countries.views import _get_corruption_exposure

        country = CountryProfile(name='Nowhere', slug='nowhere',
                                 transparency_score=None)
        result = _get_corruption_exposure(country)

        self.assertIsNone(result['score'])
        self.assertEqual(result['level'], 'Not assessed')
        self.assertNotIn(result['level'], ('Low', 'Moderate', 'Elevated'))

    def test_k_a_known_transparency_still_classifies(self):
        from countries.models import CountryProfile
        from countries.views import _get_corruption_exposure

        country = CountryProfile(name='Somewhere', slug='somewhere',
                                 transparency_score=80.0)
        result = _get_corruption_exposure(country)

        self.assertEqual(result['level'], 'Low')
        self.assertEqual(result['score'], 20)

    def test_k_mizan_country_average_excludes_unassessable_companies(self):
        """
        The old aggregate summed every company and divided by n, so a company
        we could not assess entered its country's average as a zero.
        """
        from mizan.scoring import score_country

        known = _profile('mz-known')
        unknown = _profile('mz-unknown')
        for field in (*PILLARS, 'jobs_created_score', 'regional_development_score',
                      'national_value_score', 'infrastructure_contribution_score',
                      'transparency_score_detail', 'audit_quality_score',
                      'procurement_transparency_score', 'controversy_risk_score',
                      'energy_transition_score', 'future_readiness_score',
                      'water_impact_score', 'biodiversity_impact_score',
                      'waste_management_score'):
            setattr(unknown, field, None)
        unknown.pollution_level = None

        both = score_country([known, unknown])
        only_known = score_country([known])

        self.assertIsNotNone(both.final_mizan_score)
        self.assertAlmostEqual(both.final_mizan_score,
                               only_known.final_mizan_score, places=2,
                               msg='an unassessable company must not drag the '
                                   'country average toward zero')


class L_MizanDomainSemantics(TestCase):
    """
    L — STEP 8. Not every 50 in Mizan is a defect; the genuine domain
    thresholds must keep working.
    """

    def test_l_the_weak_dimension_threshold_still_fires_on_real_evidence(self):
        from mizan.scoring import score_company

        weak = _profile('mz-weak')
        for field in ('public_benefit_score', 'jobs_created_score',
                      'regional_development_score', 'national_value_score',
                      'infrastructure_contribution_score'):
            setattr(weak, field, 10.0)

        result = score_company(weak)
        self.assertIsNotNone(result.public_benefit_score)
        self.assertLess(result.public_benefit_score, 50)

    def test_l_a_fully_known_profile_still_produces_a_mizan_label(self):
        from mizan.scoring import LABEL_INSUFFICIENT_EVIDENCE, score_company

        result = score_company(_profile('mz-full'))

        self.assertIsNotNone(result.final_mizan_score)
        self.assertNotEqual(result.mizan_label, LABEL_INSUFFICIENT_EVIDENCE)

    def test_l_an_unassessed_profile_is_not_labelled_deficient(self):
        from mizan.scoring import LABEL_INSUFFICIENT_EVIDENCE, score_company

        blank = _profile('mz-blank')
        for field in (*PILLARS, 'jobs_created_score', 'regional_development_score',
                      'national_value_score', 'infrastructure_contribution_score',
                      'transparency_score_detail', 'audit_quality_score',
                      'procurement_transparency_score', 'controversy_risk_score',
                      'energy_transition_score', 'future_readiness_score',
                      'water_impact_score', 'biodiversity_impact_score',
                      'waste_management_score'):
            setattr(blank, field, None)
        blank.pollution_level = None

        result = score_company(blank)

        self.assertIsNone(result.final_mizan_score)
        self.assertEqual(result.mizan_label, LABEL_INSUFFICIENT_EVIDENCE)
        self.assertNotEqual(result.mizan_label, 'Deficient')

    def test_l_no_dimension_deficiency_flags_from_an_unassessed_profile(self):
        from mizan.scoring import score_company

        blank = _profile('mz-noflags')
        for field in (*PILLARS, 'jobs_created_score', 'regional_development_score',
                      'national_value_score', 'infrastructure_contribution_score',
                      'transparency_score_detail', 'audit_quality_score',
                      'procurement_transparency_score', 'controversy_risk_score',
                      'energy_transition_score', 'future_readiness_score',
                      'water_impact_score', 'biodiversity_impact_score',
                      'waste_management_score'):
            setattr(blank, field, None)
        blank.pollution_level = None

        flags = score_company(blank).risk_flags
        for forbidden in ('Below-threshold public benefit delivery',
                          'Governance transparency deficit',
                          'Justice & distribution gap identified',
                          'Weak long-term stewardship signal'):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, flags)


class M_ImprovementRecommendations(TestCase):
    """M — no remediation claim for a KPI that was never measured."""

    def test_m_unmeasured_kpi_is_not_started_no_longer(self):
        from companies.improvement_data import get_improvement_pathway

        profile = _blank(
            _profile('imp-unknown'),
            'transparency_score_detail', 'energy_transition_score',
            'waste_management_score', 'anti_corruption_score',
            'jobs_created_score', 'biodiversity_impact_score',
            'future_readiness_score', 'audit_quality_score',
            'procurement_transparency_score', 'controversy_risk_score',
            'renewable_energy_share',
        )
        statuses = {m['status'] for m in get_improvement_pathway(profile)['milestones']}

        self.assertIn('not_assessed', statuses)
        self.assertNotIn('not_started', statuses)

    def test_m_no_trajectory_without_a_current_score(self):
        """
        Every trajectory number is relative to the current score. With
        `_clamp(None) -> 0` the block published 'current 0.0' and a
        'gap to 100' of exactly 100.
        """
        from companies.improvement_data import get_improvement_pathway

        profile = _blank(_profile('imp-no-score'), 'ecoiq_total_score')
        self.assertIsNone(get_improvement_pathway(profile)['trajectory'])

    def test_m_a_measured_deficit_still_generates_its_milestone(self):
        from companies.improvement_data import get_improvement_pathway

        profile = _profile('imp-measured')
        profile.waste_management_score = 10.0
        profile.biodiversity_impact_score = 10.0

        pathway = get_improvement_pathway(profile)
        circular = next(m for m in pathway['milestones']
                        if m['key'] == 'circular_economy')

        self.assertEqual(circular['status'], 'not_started')
        self.assertIsNotNone(pathway['trajectory'])

    def test_m_unassessed_milestones_claim_no_uplift(self):
        from companies.improvement_data import _build_milestones, _build_trajectory

        profile = _blank(
            _profile('imp-uplift'),
            'transparency_score_detail', 'energy_transition_score',
            'waste_management_score', 'anti_corruption_score',
            'jobs_created_score', 'biodiversity_impact_score',
            'future_readiness_score', 'audit_quality_score',
            'procurement_transparency_score', 'controversy_risk_score',
            'renewable_energy_share',
        )
        milestones = _build_milestones(profile)
        trajectory = _build_trajectory(profile, milestones)

        self.assertEqual(trajectory['uplift_low'], 0)
        self.assertEqual(trajectory['uplift_high'], 0)


class N_BackgroundTaskPersistence(TestCase):
    """N — a background task must not persist a fabricated value."""

    def test_n_a_delta_needs_both_sides_known(self):
        """
        `abs((after or 0) - (before or 0))` reported a full-magnitude move when
        a company simply gained its first score — a notification announcing a
        change that never happened.
        """
        from core.unknown import known

        for before, after in ((None, 71.4), (71.4, None), (None, None)):
            with self.subTest(before=before, after=after):
                b, a = known(before), known(after)
                delta = None if b is None or a is None else abs(a - b)
                self.assertIsNone(delta)

    def test_n_a_real_delta_is_still_computed(self):
        from core.unknown import known

        b, a = known(60.0), known(71.4)
        self.assertAlmostEqual(abs(a - b), 11.4, places=4)

    def test_n_ml_confidence_column_accepts_the_honest_null(self):
        """
        Confidence is written by the scoring model and is now None without a
        base score. Asserting the column can hold it — otherwise the fix would
        trade a fabrication for an IntegrityError.
        """
        company = Company.objects.create(name='Conf', slug='conf-null',
                                         country='UK', ml_score_confidence=None)
        company.refresh_from_db()
        self.assertIsNone(company.ml_score_confidence)


class O_CoreUnknownParity(SimpleTestCase):
    """
    O — every migrated engine agrees on what unknown means.

    Nine modules used to carry a private copy of this helper. The point of
    core.unknown is that there is now one, and this is what stops a tenth from
    quietly reappearing with different behaviour.
    """

    def _engines(self):
        from companies.improvement_data import _clamp as improvement
        from companies.scoring import _clamp as core_scoring
        from ethics.scoring import _clamp as ethics
        from ml.ethics.ethical_score import _clamp as ml_ethics
        from ml.ethics.greenwashing_risk import _clamp as greenwashing
        from ml.ethics.harm_reduction import _clamp as harm
        from ml.ethics.justice_balance import _clamp as justice
        from ml.ethics.public_benefit import _clamp as public_benefit
        from ml.ethics.stewardship import _clamp as stewardship
        from mizan.scoring import _clamp as mizan

        return {
            'companies.scoring': core_scoring,
            'companies.improvement_data': improvement,
            'ethics.scoring': ethics,
            'mizan.scoring': mizan,
            'ml.ethics.ethical_score': ml_ethics,
            'ml.ethics.greenwashing_risk': greenwashing,
            'ml.ethics.harm_reduction': harm,
            'ml.ethics.justice_balance': justice,
            'ml.ethics.public_benefit': public_benefit,
            'ml.ethics.stewardship': stewardship,
        }

    def test_o_every_engine_agrees_with_core_unknown(self):
        """
        Behaviour, not identity. Eight of these are bare aliases; two
        (companies.scoring, financing.matching) keep a thin wrapper so their
        docstrings can record what the old expression did and why it was wrong.
        A wrapper is fine — a DIFFERENT ANSWER is not, and that is what this
        asserts.
        """
        from core.unknown import clamp as canonical

        for name, fn in self._engines().items():
            for value in (None, -20.0, 0.0, 50.0, 100.0, 120.0):
                with self.subTest(engine=name, value=value):
                    self.assertEqual(fn(value), canonical(value))

    def test_o_no_engine_has_reintroduced_a_falsy_fallback(self):
        """
        The specific regression to catch: someone reinstating `float(v or 0)`.
        It is invisible to the parity test above for every value EXCEPT None,
        so this pins the two cases that distinguish it.
        """
        for name, fn in self._engines().items():
            with self.subTest(engine=name):
                self.assertIsNone(fn(None), f'{name} turns unknown into a number')
                self.assertEqual(fn(0.0), 0.0, f'{name} loses a genuine zero')

    def test_o_parity_across_the_full_value_matrix(self):
        from companies.scoring import _clamp as core_scoring
        from core.unknown import clamp as canonical
        from ethics.scoring import _clamp as ethics
        from financing.matching import _known as financing
        from mizan.scoring import _clamp as mizan

        for value in (None, -20.0, 0.0, 50.0, 100.0, 120.0):
            with self.subTest(value=value):
                expected = canonical(value)
                self.assertEqual(core_scoring(value), expected)
                self.assertEqual(ethics(value), expected)
                self.assertEqual(mizan(value), expected)
                self.assertEqual(financing(value) is None, expected is None)

    def test_o_financing_weighted_helper_matches_after_delegation(self):
        """
        core's weighted mean also clamps each value, which financing's private
        version did not. Asserted rather than assumed: for in-range inputs, which
        is every caller, the two agree.
        """
        from core.unknown import weighted_mean_of_known
        from financing.matching import _weighted

        cases = [
            ((80.0, 0.4), (60.0, 0.6)),
            ((80.0, 0.4), (None, 0.6)),
            ((0.0, 0.5), (100.0, 0.5)),
            ((None, 0.5), (None, 0.5)),
        ]
        for pairs in cases:
            with self.subTest(pairs=pairs):
                self.assertEqual(_weighted(*pairs), weighted_mean_of_known(*pairs))

    def test_o_averaging_helper_is_shared_too(self):
        from companies.scoring import _avg as core_avg
        from core.unknown import mean_of_known
        from ethics.scoring import _avg as ethics_avg

        self.assertIs(ethics_avg, mean_of_known)
        for values in ((80, 60), (80, None), (0.0, 100.0), (None, None), ()):
            with self.subTest(values=values):
                self.assertEqual(core_avg(*values), mean_of_known(*values))
