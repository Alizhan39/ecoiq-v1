"""
D2b — unknown propagates as unknown through the ethics engine.

Covers A–L from the brief. The same invariant D2 established for core scoring,
now for the parallel engine:

    "we have no data" and "we measured this as zero" are opposite statements

Ethics had its own copy of the broken helper — `float(v or 0)` — over the same
CompanyProfile fields, plus a `transparency_score_detail or 50.0` that collapsed
None AND a genuine 0.0 into 50. The consequence was worse here than in core
scoring, because this module does not only produce numbers: it produces
NARRATIVE. An unknown transparency score arrived as 0, so the company was
published with a "Transparency Deficit — below minimum accountability standards"
finding and eleven improvement recommendations for KPIs nobody had assessed.

Unknown means we do not know. It does not mean bad.
"""
from django.test import SimpleTestCase, TestCase

from companies.models import CompanyProfile
from ethics.scoring import (
    _at_least, _below, _clamp, compute_and_save, compute_ethics_profile,
    compute_net_ethical_impact, compute_regenerative_value,
    compute_transition_stewardship, generate_improvement_opportunities,
    generate_key_benefits, generate_key_harms,
)
from league.models import Company


def _blank_profile(**overrides):
    """
    A CompanyProfile (unsaved) whose every scoring input is unknown.

    Explicit rather than relying on model defaults: these columns are NOT NULL
    with default=50.0 today, so an un-overridden instance would carry 50s and
    quietly test nothing. Setting them to None is what D4 will make persistable.
    """
    fields = [
        'public_benefit_score', 'environmental_responsibility_score',
        'modernization_score', 'transparency_anti_corruption_score',
        'anti_corruption_score', 'ethical_alignment_score',
        'transparency_score_detail', 'controversy_risk_score',
        'profit_extraction_score', 'energy_transition_score',
        'future_readiness_score', 'national_value_score',
        'regional_development_score', 'jobs_created_score',
        'biodiversity_impact_score', 'infrastructure_contribution_score',
        'waste_management_score', 'water_impact_score', 'digitalization_score',
        'infrastructure_upgrade_score', 'audit_quality_score',
        'procurement_transparency_score',
    ]
    kwargs = {f: None for f in fields}
    kwargs['pollution_level'] = None
    kwargs.update(overrides)
    return CompanyProfile(**kwargs)


class A_B_C_EthicsClamp(SimpleTestCase):
    """The corrected helper. Ethics delegates to core.unknown — same semantics."""

    def test_a_clamp_of_none_is_none(self):
        self.assertIsNone(_clamp(None))

    def test_b_clamp_preserves_a_real_zero(self):
        self.assertEqual(_clamp(0.0), 0.0)
        self.assertIsNotNone(_clamp(0.0))

    def test_c_clamp_preserves_a_real_fifty(self):
        self.assertEqual(_clamp(50.0), 50.0)

    def test_bounds_still_apply(self):
        self.assertEqual(_clamp(120.0), 100.0)
        self.assertEqual(_clamp(-20.0), 0.0)

    def test_zero_and_unknown_are_distinguishable(self):
        self.assertEqual(_clamp(0.0), 0.0)
        self.assertIsNone(_clamp(None))


class ParityWithCoreScoring(SimpleTestCase):
    """
    Ethics, core scoring and financing must agree on what unknown means.

    They are separate engines with separate call graphs, and before D2b each
    carried its own private helper that had drifted. They now share
    core.unknown; this asserts the shared semantics rather than trusting that
    three modules stay aligned by convention.
    """

    def test_all_three_engines_agree_on_the_full_matrix(self):
        from companies.scoring import _clamp as core_clamp
        from core.unknown import clamp as canonical
        from financing.matching import _known as financing_known

        for value in (None, 0.0, 50.0, 100.0):
            with self.subTest(value=value):
                expected = canonical(value)
                self.assertEqual(_clamp(value), expected)
                self.assertEqual(core_clamp(value), expected)
                # _known does not clamp, but must agree on known-vs-unknown.
                self.assertEqual(financing_known(value) is None, expected is None)

    def test_averaging_is_the_same_helper_everywhere(self):
        from companies.scoring import _avg as core_avg
        from core.unknown import mean_of_known
        from ethics.scoring import _avg as ethics_avg

        self.assertIs(ethics_avg, mean_of_known)
        self.assertEqual(core_avg(80, None), mean_of_known(80, None))
        self.assertIsNone(core_avg(None, None))
        self.assertIsNone(mean_of_known(None, None))


class D_E_TransparencyFallback(SimpleTestCase):
    """
    `transparency_score_detail or 50.0` conflated three different states.

    Unknown became 50 (opacity harm 0 — a positive claim of adequate
    disclosure), and a genuine measured 0.0 became 50 as well, so the most
    opaque company possible was recorded as averagely transparent.
    """

    def test_d_unknown_transparency_does_not_become_fifty(self):
        profile = _blank_profile(transparency_score_detail=None)
        nei, benefit, harm = compute_net_ethical_impact(profile)

        # The old code produced opacity_harm = (50 - 50) * 2 = 0.
        self.assertIsNone(harm, 'unknown transparency must not yield zero harm')
        self.assertIsNone(nei)

    def test_e_a_genuine_zero_transparency_yields_maximum_opacity_harm(self):
        profile = _blank_profile(
            transparency_score_detail=0.0,
            controversy_risk_score=0.0,
            pollution_level='low',
        )
        _, _, harm = compute_net_ethical_impact(profile)

        # opacity_harm = (50 - 0) * 2 = 100, weighted 0.20; pollution low = 8
        # at 0.50; controversy 0 at 0.30.
        self.assertIsNotNone(harm)
        self.assertAlmostEqual(harm, 8 * 0.50 + 0.0 * 0.30 + 100 * 0.20, places=1)

    def test_a_measured_fifty_transparency_is_not_the_old_fallback(self):
        real_fifty = _blank_profile(transparency_score_detail=50.0,
                                    controversy_risk_score=0.0,
                                    pollution_level='low')
        unknown = _blank_profile(transparency_score_detail=None,
                                 controversy_risk_score=0.0,
                                 pollution_level='low')

        self.assertIsNotNone(compute_net_ethical_impact(real_fifty)[2])
        self.assertIsNotNone(compute_net_ethical_impact(unknown)[2])
        # Both harms are computable, but from different weight bases — the real
        # 50 contributes an opacity term, the unknown is re-normalised away.
        self.assertNotEqual(
            compute_net_ethical_impact(real_fifty)[2],
            compute_net_ethical_impact(unknown)[2],
        )


class F_AllUnknownProducesNoComposite(SimpleTestCase):

    def test_f_nei_is_none_when_everything_is_unknown(self):
        nei, benefit, harm = compute_net_ethical_impact(_blank_profile())
        self.assertIsNone(nei)
        self.assertIsNone(benefit)
        self.assertIsNone(harm)

    def test_f_tss_is_none_when_everything_is_unknown(self):
        self.assertIsNone(compute_transition_stewardship(_blank_profile()))

    def test_f_rvi_is_none_when_everything_is_unknown(self):
        self.assertIsNone(compute_regenerative_value(_blank_profile()))

    def test_nei_refuses_when_only_one_side_is_known(self):
        """
        'Net' is a claim about benefit AND harm. A benefit-only figure published
        under that name would assert something about harm we have not
        established.
        """
        benefit_only = _blank_profile(public_benefit_score=80.0)
        nei, benefit, harm = compute_net_ethical_impact(benefit_only)

        self.assertEqual(benefit, 80.0)
        self.assertIsNone(harm)
        self.assertIsNone(nei, 'net impact needs both sides')

    def test_a_fully_known_profile_still_scores(self):
        profile = _blank_profile(
            public_benefit_score=70.0, environmental_responsibility_score=70.0,
            modernization_score=70.0, transparency_anti_corruption_score=70.0,
            anti_corruption_score=70.0, ethical_alignment_score=70.0,
            transparency_score_detail=70.0, controversy_risk_score=10.0,
            energy_transition_score=70.0, future_readiness_score=70.0,
            national_value_score=70.0, regional_development_score=70.0,
            jobs_created_score=70.0, biodiversity_impact_score=70.0,
            infrastructure_contribution_score=70.0, pollution_level='low',
        )
        nei, benefit, harm = compute_net_ethical_impact(profile)

        self.assertIsNotNone(nei)
        self.assertIsNotNone(compute_transition_stewardship(profile))
        self.assertIsNotNone(compute_regenerative_value(profile))
        self.assertEqual(benefit, 70.0)

    def test_partial_weighted_dimension_renormalises_rather_than_shrinking(self):
        """RVI is weighted — dropping a term must not penalise the absence."""
        full = _blank_profile(
            national_value_score=80.0, regional_development_score=80.0,
            future_readiness_score=80.0, ethical_alignment_score=80.0,
            jobs_created_score=80.0, biodiversity_impact_score=80.0,
            infrastructure_contribution_score=80.0, pollution_level='medium',
            transparency_score_detail=None,
        )
        partial = _blank_profile(
            national_value_score=80.0, regional_development_score=80.0,
            future_readiness_score=80.0, ethical_alignment_score=80.0,
            jobs_created_score=80.0, biodiversity_impact_score=80.0,
            infrastructure_contribution_score=None, pollution_level='medium',
            transparency_score_detail=None,
        )
        # Both are 80 across every KNOWN weight, so both must be 80.0 — not
        # 80 * 0.95 = 76.0 for the partial one.
        self.assertEqual(compute_regenerative_value(full), 80.0)
        self.assertEqual(compute_regenerative_value(partial), 80.0)


class G_UnknownNeverTriggersHarm(SimpleTestCase):
    """The most consequential behaviour change in D2b."""

    def test_g_no_harm_signals_from_an_entirely_unknown_profile(self):
        self.assertEqual(generate_key_harms(_blank_profile()), [])

    def test_g_known_bad_values_still_produce_harm_signals(self):
        """The guards must not have disabled the rules for real evidence."""
        profile = _blank_profile(
            transparency_score_detail=10.0,
            anti_corruption_score=20.0,
            controversy_risk_score=90.0,
            pollution_level='severe',
        )
        labels = {h['label'] for h in generate_key_harms(profile)}

        self.assertIn('Transparency Deficit', labels)
        self.assertIn('Anti-Corruption Gap', labels)
        self.assertIn('High Controversy Risk', labels)
        self.assertIn('Severe Pollution Impact', labels)

    def test_g_a_measured_zero_still_produces_harm_signals(self):
        """A measured 0 is the worst case and must still fire."""
        profile = _blank_profile(transparency_score_detail=0.0,
                                 anti_corruption_score=0.0)
        labels = {h['label'] for h in generate_key_harms(profile)}

        self.assertIn('Transparency Deficit', labels)
        self.assertIn('Anti-Corruption Gap', labels)

    def test_g_low_public_benefit_flag_needs_both_halves_known(self):
        unknown_benefit = _blank_profile(profit_extraction_score=90.0,
                                         public_benefit_score=None)
        known_benefit = _blank_profile(profit_extraction_score=90.0,
                                       public_benefit_score=10.0)

        self.assertNotIn(
            'Low Public Benefit Return',
            {h['label'] for h in generate_key_harms(unknown_benefit)},
        )
        self.assertIn(
            'Low Public Benefit Return',
            {h['label'] for h in generate_key_harms(known_benefit)},
        )

    def test_below_predicate_is_false_for_unknown(self):
        self.assertFalse(_below(None, 30))
        self.assertTrue(_below(10.0, 30))
        self.assertTrue(_below(0.0, 30), 'a measured zero is below the threshold')


class H_UnknownNeverTriggersPositiveClaim(SimpleTestCase):
    """
    The mirror of G, and it matters just as much. Absence of evidence is not
    evidence of virtue.
    """

    def test_h_no_benefit_signals_from_an_entirely_unknown_profile(self):
        self.assertEqual(generate_key_benefits(_blank_profile()), [])

    def test_h_known_good_values_still_produce_benefit_signals(self):
        profile = _blank_profile(
            public_benefit_score=80.0, transparency_score_detail=80.0,
            modernization_score=80.0, anti_corruption_score=80.0,
            pollution_level='low',
        )
        labels = {b['label'] for b in generate_key_benefits(profile)}

        self.assertIn('Strong Public Benefit', labels)
        self.assertIn('Transparent Reporting', labels)
        self.assertIn('Clean Operations', labels)

    def test_h_unknown_earns_no_modernization_momentum_bonus(self):
        """TSS adjustments are claims too."""
        known_low = _blank_profile(environmental_responsibility_score=60.0,
                                   modernization_score=60.0,
                                   pollution_level='medium')
        unknown_mod = _blank_profile(environmental_responsibility_score=60.0,
                                     modernization_score=None,
                                     pollution_level='medium')

        self.assertEqual(compute_transition_stewardship(known_low), 62.0)
        self.assertEqual(compute_transition_stewardship(unknown_mod), 60.0)

    def test_h_unknown_transparency_earns_no_disclosure_premium(self):
        with_premium = _blank_profile(national_value_score=60.0,
                                      transparency_score_detail=80.0,
                                      pollution_level='medium')
        without = _blank_profile(national_value_score=60.0,
                                 transparency_score_detail=None,
                                 pollution_level='medium')

        self.assertEqual(compute_regenerative_value(with_premium), 63.0)
        self.assertEqual(compute_regenerative_value(without), 60.0)

    def test_at_least_predicate_is_false_for_unknown(self):
        self.assertFalse(_at_least(None, 65))
        self.assertTrue(_at_least(80.0, 65))


class UnknownNeverGeneratesRecommendations(SimpleTestCase):
    """
    A recommendation is a claim that a specific KPI is deficient. Eleven of the
    thirteen triggers were bare `_clamp(x) < N`, so an unassessed company was
    handed a full improvement roadmap it had never been measured against.
    """

    def test_no_recommendations_from_an_entirely_unknown_profile(self):
        self.assertEqual(generate_improvement_opportunities(_blank_profile()), [])

    def test_known_deficits_still_generate_recommendations(self):
        profile = _blank_profile(waste_management_score=20.0,
                                 transparency_score_detail=20.0)
        titles = {o['title'] for o in generate_improvement_opportunities(profile)}

        self.assertIn('Implement Circular Waste Systems', titles)
        self.assertIn('Publish Annual ESG / Sustainability Report', titles)

    def test_a_measured_zero_still_generates_its_recommendation(self):
        profile = _blank_profile(waste_management_score=0.0)
        titles = {o['title'] for o in generate_improvement_opportunities(profile)}

        self.assertIn('Implement Circular Waste Systems', titles)

    def test_pollution_recommendation_still_fires_on_a_known_category(self):
        titles = {
            o['title']
            for o in generate_improvement_opportunities(
                _blank_profile(pollution_level='severe')
            )
        }
        self.assertIn('Reduce Pollution Intensity', titles)


class I_IngestionDoesNotFabricate(TestCase):
    """
    STEP 7. These columns are still NOT NULL with default=0.0, so there is no
    way to STORE an unknown master score. The available honest option is not to
    write one.
    """

    def _profile(self, slug, **overrides):
        company = Company.objects.create(name=slug, slug=slug, country='UK')
        profile = CompanyProfile.objects.create(company=company, status='public')
        for field, value in overrides.items():
            setattr(profile, field, value)
        return profile

    def test_i_no_row_is_created_when_a_master_score_is_unknown(self):
        """
        Creating one would take the model default 0.0 — recording an unassessed
        company as having the worst possible ethical impact.
        """
        from ethics.models import CompanyEthicsProfile

        profile = self._profile('unknown-ethics')
        profile.pollution_level = None
        profile.transparency_score_detail = None
        profile.controversy_risk_score = None

        result = compute_and_save(profile)

        self.assertIsNone(result)
        self.assertFalse(
            CompanyEthicsProfile.objects.filter(profile=profile).exists(),
            'a row of zeros must not be created for an unassessed company',
        )

    def test_i_an_existing_row_keeps_its_value_rather_than_being_zeroed(self):
        from ethics.models import CompanyEthicsProfile

        profile = self._profile('had-ethics')
        CompanyEthicsProfile.objects.create(profile=profile,
                                            net_ethical_impact=61.5,
                                            transition_stewardship=58.0,
                                            regenerative_value=55.0)

        profile.pollution_level = None
        profile.transparency_score_detail = None
        profile.controversy_risk_score = None
        compute_and_save(profile)          # must not raise IntegrityError

        row = CompanyEthicsProfile.objects.get(profile=profile)
        self.assertEqual(row.net_ethical_impact, 61.5,
                         'the unknown must not be written as 0.0')

    def test_i_a_fully_known_profile_still_persists(self):
        """
        "Fully known" relied on the model defaults to populate the inputs.
        D4C removed them, so the inputs are named explicitly here.
        """
        from ethics.models import CompanyEthicsProfile
        from companies.testing import populate_material

        profile = self._profile('known-ethics')
        populate_material(profile)
        profile.pollution_level = 'low'
        result = compute_and_save(profile)

        self.assertIsNotNone(result)
        self.assertTrue(CompanyEthicsProfile.objects.filter(profile=profile).exists())

    def test_i_the_ingestion_call_site_tolerates_a_none_return(self):
        """ingestion/pipeline.py discards the return value — assert it may."""
        profile = self._profile('ingest-unknown')
        profile.pollution_level = None
        profile.transparency_score_detail = None
        profile.controversy_risk_score = None

        self.assertIsNone(compute_and_save(profile))

    def test_unknown_scores_are_named_not_just_absent(self):
        profile = self._profile('named-unknowns')
        profile.pollution_level = None
        profile.transparency_score_detail = None
        profile.controversy_risk_score = None

        data = compute_ethics_profile(profile)

        self.assertIn('net_ethical_impact', data['_unknown_scores'])
        self.assertIn('total_harm_score', data['_unknown_scores'])
        self.assertIsNone(data['net_ethical_impact'])
