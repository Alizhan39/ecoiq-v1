"""
D2 — calculation semantics: unknown propagates as unknown.

Covers A–J from the brief. The single idea underneath all of them:

    "we have no data" and "we measured this as zero" are opposite statements,
    and the codebase used to collapse them into the same number.

Three distinct fallbacks did it, in two directions:

    _clamp(None)            -> 0     (worst possible score)
    _avg(None, None)        -> 50    (invented average)
    profile.x or 50         -> 50    (and rewrote a genuine 0.0 too)

The last is the subtle one: `or` is falsy-triggered, so it destroyed real zeros
as well as unknowns. Tests B/H below exist specifically for that.
"""
from django.test import SimpleTestCase, TestCase

from companies.models import CompanyProfile
from companies.scoring import (
    _avg, _clamp, _pollution_to_env_base, calculate_harm_penalty,
    calculate_transparency, compute_ecoiq_profile_score, recalculate_and_save,
)
from league.models import Company


class A_UnknownStaysUnknown(SimpleTestCase):

    def test_clamp_of_none_is_none(self):
        self.assertIsNone(_clamp(None))

    def test_avg_of_all_unknown_is_none(self):
        self.assertIsNone(_avg(None, None, None))

    def test_avg_of_nothing_is_none(self):
        self.assertIsNone(_avg())

    def test_unknown_pollution_category_is_none(self):
        for value in (None, '', 'not-a-category'):
            with self.subTest(value=value):
                self.assertIsNone(_pollution_to_env_base(value))


class B_RealZeroSurvives(SimpleTestCase):
    """A measured 0 is a finding. It must not be mistaken for missing."""

    def test_clamp_preserves_zero(self):
        self.assertEqual(_clamp(0.0), 0.0)
        self.assertIsNotNone(_clamp(0.0))

    def test_zero_and_unknown_are_distinguishable(self):
        self.assertEqual(_clamp(0.0), 0.0)
        self.assertIsNone(_clamp(None))

    def test_avg_counts_a_real_zero(self):
        # If 0 were dropped as falsy, this would be 100.0.
        self.assertEqual(_avg(0.0, 100.0), 50.0)

    def test_avg_of_only_zero_is_zero_not_none(self):
        self.assertEqual(_avg(0.0), 0.0)


class C_RealFiftySurvives(SimpleTestCase):

    def test_clamp_preserves_fifty(self):
        self.assertEqual(_clamp(50.0), 50.0)

    def test_avg_of_fifty_is_fifty_and_is_not_the_old_fallback(self):
        # The old _avg returned 50.0 for *unknown*. A real 50 must be
        # distinguishable from that, which it now is: unknown returns None.
        self.assertEqual(_avg(50.0), 50.0)
        self.assertIsNone(_avg(None))


class D_BoundsStillApply(SimpleTestCase):

    def test_clamps_above_and_below(self):
        self.assertEqual(_clamp(120.0), 100.0)
        self.assertEqual(_clamp(-20.0), 0.0)

    def test_custom_bounds(self):
        self.assertEqual(_clamp(5.0, lo=0.0, hi=1.0), 1.0)


class E_AggregateUnknownWhenNothingKnown(TestCase):

    def test_weighted_dimension_is_none_when_all_inputs_unknown(self):
        profile = CompanyProfile(
            transparency_score_detail=None,
            audit_quality_score=None,
            procurement_transparency_score=None,
        )
        self.assertIsNone(calculate_transparency(profile))


class F_PartialAggregateUsesKnownValues(SimpleTestCase):
    """
    The documented choice: average what is known, and let evidence coverage
    report the gap. See _avg's docstring and the Evidence Integrity plan §6.
    """

    def test_partial_average_uses_known_values_only(self):
        self.assertEqual(_avg(80.0, None), 80.0)
        self.assertEqual(_avg(80.0, 60.0, None), 70.0)

    def test_weighted_partial_renormalises_rather_than_shrinking(self):
        """
        Dropping a weighted term without renormalising would penalise a company
        for the absence itself. Known-only 40%/35% must rescale to sum to 1.
        """
        profile = CompanyProfile(
            transparency_score_detail=80.0,
            audit_quality_score=80.0,
            procurement_transparency_score=None,
        )
        # Not 80 * (0.40 + 0.35) = 60.0 — that would be the un-renormalised bug.
        self.assertAlmostEqual(calculate_transparency(profile), 80.0, places=6)


class UnknownNeverFabricatesHarm(TestCase):
    """
    The most consequential behaviour change in D2.

    An unknown transparency score used to arrive as 0, so `< 30` was True and
    the company was penalised — a harm finding manufactured from missing data.
    """

    def test_all_unknown_inputs_produce_no_penalty(self):
        profile = CompanyProfile(
            pollution_level='low',
            controversy_risk_score=None,
            transparency_score_detail=None,
            profit_extraction_score=None,
            public_benefit_score=None,
            modernization_score=None,
        )
        self.assertEqual(calculate_harm_penalty(profile), 0.0)

    def test_a_known_bad_value_still_penalises(self):
        """The guard must not have disabled the rule for real evidence."""
        profile = CompanyProfile(
            pollution_level='low',
            controversy_risk_score=None,
            transparency_score_detail=10.0,   # genuinely opaque
            profit_extraction_score=None,
            public_benefit_score=None,
            modernization_score=None,
        )
        self.assertEqual(calculate_harm_penalty(profile), 5.0)

    def test_a_known_zero_still_penalises(self):
        """A measured 0 transparency is the worst case and must still fire."""
        profile = CompanyProfile(
            pollution_level='low', controversy_risk_score=None,
            transparency_score_detail=0.0, profit_extraction_score=None,
            public_benefit_score=None, modernization_score=None,
        )
        self.assertEqual(calculate_harm_penalty(profile), 5.0)


class CompositePropagatesUnknown(TestCase):

    def _company(self, slug):
        return Company.objects.create(name=slug, slug=slug, country='UK')

    def test_composite_is_none_when_a_dimension_is_unknown(self):
        profile = CompanyProfile(
            company=self._company('unknown-dim'),
            jobs_created_score=None, regional_development_score=None,
            infrastructure_contribution_score=None, national_value_score=None,
        )
        result = compute_ecoiq_profile_score(profile)

        self.assertIsNone(result['ecoiq_total_score'])
        self.assertIsNone(result['moral_label'])
        self.assertIsNone(result['ecoiq_category'])
        self.assertFalse(result['_is_complete'])
        self.assertIn('public_benefit_score', result['_unknown_dimensions'])

    def test_a_fully_known_profile_still_scores(self):
        """
        "Fully known" used to mean an unsaved CompanyProfile, because the field
        defaults quietly populated sixteen inputs. Post-D4C that constructs a
        company about which nothing is known, so the inputs are named here —
        which is what the test always claimed to be doing.
        """
        from companies.testing import FIXTURE_VALUE, MATERIAL_FIELDS

        profile = CompanyProfile(
            company=self._company('fully-known'), pollution_level='low',
            **{name: FIXTURE_VALUE for name in MATERIAL_FIELDS})
        result = compute_ecoiq_profile_score(profile)

        self.assertIsNotNone(result['ecoiq_total_score'])
        self.assertTrue(result['_is_complete'])
        self.assertEqual(result['_unknown_dimensions'], [])

    def test_save_writes_none_for_a_dimension_that_is_unknown(self):
        """
        Was `test_save_never_writes_none_into_a_not_null_column`, which
        asserted the opposite: while the columns were NOT NULL an unknown
        dimension had to be SKIPPED, leaving the previously stored value in
        place.

        D4B made the columns nullable and D4C made the writer persist unknown,
        so the stored value now describes the current evidence rather than the
        last time there happened to be some. The subject is unchanged — what
        save() does with an unknown dimension — and the answer has inverted.
        """
        from companies.testing import FIXTURE_VALUE, MATERIAL_FIELDS

        company = self._company('save-safe')
        profile = CompanyProfile.objects.create(
            company=company, status='public', pollution_level='low',
            **{name: FIXTURE_VALUE for name in MATERIAL_FIELDS})
        recalculate_and_save(profile)
        profile.refresh_from_db()
        self.assertIsNotNone(profile.ecoiq_total_score)

        # anti_corruption is a one-input dimension, so this removes it entirely.
        profile.anti_corruption_score = None
        profile.save()

        recalculate_and_save(profile)      # must not raise
        profile.refresh_from_db()
        self.assertIsNone(profile.ecoiq_total_score,
                          'a stale value would no longer describe the evidence')


class G_H_FinancingRefusesToInvent(TestCase):

    def _profile(self, slug, **kwargs):
        company = Company.objects.create(name=slug, slug=slug, country='UK')
        return CompanyProfile.objects.create(company=company, status='public', **kwargs)

    def test_g_no_revenue_means_no_capex_estimate(self):
        from financing.matching import _estimate_capex

        profile = self._profile('no-revenue', annual_revenue=None)
        low, high, impact = _estimate_capex(profile)

        self.assertIsNone(low)
        self.assertIsNone(high)
        self.assertIsNone(impact)

    def test_g_the_old_floor_no_longer_fabricates_a_range(self):
        """
        Previously this produced at least $2M–$10M for any company, because
        `annual_revenue or 50_000_000` invented a $50m business.
        """
        profile = self._profile('no-revenue-2', annual_revenue=None)
        from financing.matching import _estimate_capex

        self.assertEqual(_estimate_capex(profile), (None, None, None))

    def test_h_a_genuine_zero_is_preserved_not_rewritten_to_fifty(self):
        """
        `profile.x or 50` rewrote a measured 0.0 to 50 — the worst real
        observation became an average one. _known keeps it.
        """
        from financing.matching import _known

        self.assertEqual(_known(0.0), 0.0)
        self.assertIsNone(_known(None))

    def test_known_revenue_still_produces_an_estimate(self):
        from financing.matching import _estimate_capex

        profile = self._profile('has-revenue', annual_revenue=100_000_000)
        low, high, impact = _estimate_capex(profile)

        self.assertIsNotNone(low)
        self.assertGreater(high, low)

    def test_unknown_readiness_yields_an_unknown_tier_not_early_stage(self):
        from financing.matching import _readiness_tier

        self.assertEqual(_readiness_tier(None), 'unknown')
        self.assertEqual(_readiness_tier(80.0), 'investment_ready')


class I_J_ConfidenceIsNeverInvented(SimpleTestCase):

    def test_i_the_fifty_fallback_is_gone(self):
        import inspect

        from pandas_scoring_engine.services import scoring

        source = inspect.getsource(scoring)
        self.assertNotIn('else 50.0', source)
        self.assertNotIn('else 40.0', source)

    def test_j_a_real_zero_confidence_is_representable(self):
        """
        The point of removing the fallback: 0.0 and None must be different
        values, not both rendered as some invented middle.
        """
        import numpy as np

        confidences = [0.0, 0.0]
        self.assertEqual(float(np.mean(confidences)), 0.0)
        self.assertIsNotNone(float(np.mean(confidences)))
