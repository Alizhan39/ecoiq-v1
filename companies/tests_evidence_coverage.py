"""
D5 — Evidence Coverage, computed from the provenance store.

Coverage answers one question:

    HOW MUCH of the information this assessment requires is defensibly
    supported?

Until now it guessed. `field_provenance()` compared a stored value against the
model default and called a match SEEDED — a stand-in for a store that did not
exist when it was written. D3 built the store; D4C removed the defaults it
compared against, leaving the guess inert and every company at zero coverage.

This is where the two are joined.
"""
from django.test import SimpleTestCase, TestCase

from companies import provenance as prov
from companies.evidence import (
    AVAILABILITY_AVAILABLE, AVAILABILITY_INSUFFICIENT, AVAILABILITY_PARTIAL,
    EVIDENCED_MATERIAL_ORIGINS, PROVENANCE_ESTIMATED, PROVENANCE_INFERRED,
    PROVENANCE_MEASURED, PROVENANCE_MODELLED, PROVENANCE_SEEDED,
    PROVENANCE_UNKNOWN, _weight_by_field, coverage_for, derived_coverage_for,
    field_provenance, public_score_state,
)
from companies.scoring import recalculate_and_save
from companies.testing import FIXTURE_VALUE, MATERIAL_FIELDS, populated
from league.models import Company


def _profile(slug, **overrides):
    company = Company.objects.create(name=slug, slug=slug, country='UK')
    return populated(company, **overrides)


def _evidence(profile, keys=None, origin=PROVENANCE_MEASURED, writer='ingestion'):
    for key in (keys if keys is not None else sorted(prov.MATERIAL_METRIC_KEYS)):
        prov.record(profile, key, origin, written_by=writer)
    return profile


class TheDenominator(SimpleTestCase):

    def test_weights_are_the_scoring_engines_own(self):
        self.assertAlmostEqual(sum(_weight_by_field().values()), 1.0, places=6)

    def test_a_shared_input_is_counted_once(self):
        """
        national_value_score feeds two pillars, so it appears twice in
        MATERIAL_INPUTS. Counting it twice would ask a company for 17 pieces of
        evidence when there are 16 to give, and put 100% out of reach.
        """
        self.assertEqual(len(_weight_by_field()), 16)

    def test_its_weight_is_the_sum_of_both_contributions(self):
        weights = _weight_by_field()

        self.assertGreater(weights['national_value_score'],
                           weights['jobs_created_score'])

    def test_the_denominator_matches_the_registry(self):
        self.assertEqual(set(_weight_by_field()), set(prov.MATERIAL_METRIC_KEYS))


class WhatCountsAsEvidence(SimpleTestCase):

    def test_measured_inferred_and_estimated_count(self):
        self.assertEqual(
            set(EVIDENCED_MATERIAL_ORIGINS),
            {PROVENANCE_MEASURED, PROVENANCE_INFERRED, PROVENANCE_ESTIMATED})

    def test_modelled_does_not_count_for_a_material_input(self):
        """
        The substantive decision in this module. A material input carrying
        MODELLED is a model output wearing an input's clothes, and counting it
        would let a model corroborate itself.
        """
        self.assertNotIn(PROVENANCE_MODELLED, EVIDENCED_MATERIAL_ORIGINS)

    def test_seeded_and_legacy_never_count(self):
        self.assertNotIn(PROVENANCE_SEEDED, EVIDENCED_MATERIAL_ORIGINS)
        self.assertNotIn(PROVENANCE_UNKNOWN, EVIDENCED_MATERIAL_ORIGINS)


class FieldProvenanceReadsTheStore(TestCase):

    def setUp(self):
        self.profile = _profile('field-prov')

    def test_it_returns_the_recorded_origin(self):
        prov.record(self.profile, 'water_impact_score', PROVENANCE_MEASURED)

        self.assertEqual(field_provenance(self.profile, 'water_impact_score'),
                         PROVENANCE_MEASURED)

    def test_an_unrecorded_value_is_legacy(self):
        self.assertEqual(field_provenance(self.profile, 'water_impact_score'),
                         PROVENANCE_UNKNOWN)

    def test_an_absent_value_has_no_origin(self):
        from companies.evidence import PROVENANCE_NO_VALUE

        self.profile.water_impact_score = None
        self.profile.save()

        self.assertEqual(field_provenance(self.profile, 'water_impact_score'),
                         PROVENANCE_NO_VALUE)

    def test_it_no_longer_guesses_from_the_default(self):
        """A value of exactly 50 is not evidence of anything either way."""
        self.profile.water_impact_score = 50.0
        self.profile.save()
        prov.record(self.profile, 'water_impact_score', PROVENANCE_MEASURED)

        self.assertEqual(field_provenance(self.profile, 'water_impact_score'),
                         PROVENANCE_MEASURED)


class CoverageArithmetic(TestCase):

    def test_no_evidence_is_zero_percent(self):
        report = coverage_for(_profile('cov-none'))

        self.assertEqual(report.coverage_percent, 0)
        self.assertEqual(report.numerator, 0)
        self.assertEqual(report.denominator, 16)
        self.assertEqual(report.availability, AVAILABILITY_INSUFFICIENT)

    def test_complete_evidence_is_one_hundred_percent(self):
        report = coverage_for(_evidence(_profile('cov-all')))

        self.assertEqual(report.coverage_percent, 100)
        self.assertEqual(report.numerator, 16)
        self.assertEqual(report.availability, AVAILABILITY_AVAILABLE)

    def test_partial_evidence_is_weighted_not_counted(self):
        """
        A company missing the 25%-weighted public-benefit pillar must not read
        the same as one missing the 5%-weighted ethical-alignment one.
        """
        heavy = _evidence(_profile('cov-heavy'),
                          keys=['jobs_created_score', 'regional_development_score',
                                'infrastructure_contribution_score',
                                'national_value_score'])
        light = _evidence(_profile('cov-light'), keys=['anti_corruption_score'])

        self.assertGreater(coverage_for(heavy).coverage_percent,
                           coverage_for(light).coverage_percent)

    def test_partial_reports_as_partial(self):
        report = coverage_for(_evidence(_profile('cov-partial'),
                                        keys=['anti_corruption_score']))

        self.assertEqual(report.availability, AVAILABILITY_PARTIAL)

    def test_the_percentage_is_a_whole_number(self):
        report = coverage_for(_evidence(_profile('cov-round'),
                                        keys=['anti_corruption_score']))

        self.assertIsInstance(report.coverage_percent, int)

    def test_it_can_say_n_of_m(self):
        report = coverage_for(_evidence(_profile('cov-n-of-m'),
                                        keys=sorted(prov.MATERIAL_METRIC_KEYS)[:11]))

        self.assertEqual(report.numerator, 11)
        self.assertEqual(report.denominator, 16)
        self.assertIn('11 of 16', str(report))


class ExcludedOrigins(TestCase):

    def test_seeded_evidence_is_zero_coverage(self):
        report = coverage_for(_evidence(_profile('cov-seeded'),
                                        origin=PROVENANCE_SEEDED,
                                        writer='seed:test'))

        self.assertEqual(report.coverage_percent, 0)

    def test_legacy_evidence_is_zero_coverage(self):
        report = coverage_for(_evidence(_profile('cov-legacy'),
                                        origin=PROVENANCE_UNKNOWN,
                                        writer='d3b_backfill'))

        self.assertEqual(report.coverage_percent, 0)

    def test_excluded_inputs_are_reported_as_unevidenced_not_missing(self):
        """
        "We hold a number we cannot stand behind" is a different problem from
        "we hold nothing", and they need different work to fix.
        """
        report = coverage_for(_evidence(_profile('cov-unevidenced'),
                                        origin=PROVENANCE_SEEDED,
                                        writer='seed:test'))

        self.assertEqual(len(report.unevidenced), 16)
        self.assertEqual(report.missing, [])

    def test_an_absent_value_is_missing_not_unevidenced(self):
        profile = _profile('cov-absent')
        profile.water_impact_score = None
        profile.save()

        report = coverage_for(profile)

        self.assertIn('water_impact_score', report.missing)
        self.assertNotIn('water_impact_score', report.unevidenced)

    def test_a_mixture_is_counted_correctly(self):
        profile = _profile('cov-mixed')
        keys = sorted(prov.MATERIAL_METRIC_KEYS)
        _evidence(profile, keys=keys[:8], origin=PROVENANCE_MEASURED)
        _evidence(profile, keys=keys[8:12], origin=PROVENANCE_SEEDED,
                  writer='seed:test')

        report = coverage_for(profile)

        self.assertEqual(report.numerator, 8)
        self.assertEqual(len(report.unevidenced), 4)
        self.assertEqual(len(report.missing), 4)


class DerivedCoverage(TestCase):
    """Coverage for a derived metric comes from the graph it actually consumed."""

    def setUp(self):
        self.profile = _evidence(_profile('derived-cov'))
        recalculate_and_save(self.profile)
        self.profile.refresh_from_db()

    def test_the_composite_covers_all_sixteen(self):
        report = derived_coverage_for(self.profile, 'company.ecoiq_total')

        self.assertEqual(report.denominator, 16)
        self.assertEqual(report.coverage_percent, 100)

    def test_a_pillar_covers_only_its_own_inputs(self):
        """
        Reporting whole-estate coverage against a four-input pillar would
        describe a different calculation from the one that produced it.
        """
        report = derived_coverage_for(self.profile, 'company.public_benefit')

        self.assertEqual(report.denominator, 4)

    def test_a_shared_ancestor_is_counted_once(self):
        """
        Diamonds are common: several pillars share material inputs. Counting a
        shared ancestor once per path would inflate coverage for exactly the
        metrics whose evidence is most concentrated.
        """
        report = derived_coverage_for(self.profile, 'company.ecoiq_total')

        self.assertEqual(report.denominator, 16,
                         'seventeen would mean national_value_score was '
                         'counted on both of its paths')

    def test_a_metric_with_no_lineage_reports_zero(self):
        report = derived_coverage_for(self.profile, 'mizan.score')

        self.assertEqual(report.coverage_percent, 0)
        self.assertEqual(report.denominator, 0)
        self.assertEqual(report.availability, AVAILABILITY_INSUFFICIENT)

    def test_seeded_ancestry_gives_zero_derived_coverage(self):
        seeded = _evidence(_profile('derived-seeded'), origin=PROVENANCE_SEEDED,
                           writer='seed:test')
        recalculate_and_save(seeded)
        seeded.refresh_from_db()

        report = derived_coverage_for(seeded, 'company.ecoiq_total')

        self.assertEqual(report.coverage_percent, 0)
        self.assertEqual(len(report.unevidenced), 16)


class ThePublicationGate(TestCase):
    """
    The floor was `covered_inputs > 0` while coverage was inert. Now that
    coverage works, that floor would publish a company with ONE evidenced input
    out of sixteen.
    """

    def _with(self, slug, n, origin=PROVENANCE_MEASURED):
        profile = _profile(slug, ecoiq_total_score=71.4)
        profile.company.ecoiq_score = 71.4
        profile.company.save()
        _evidence(profile, keys=sorted(prov.MATERIAL_METRIC_KEYS)[:n], origin=origin)
        recalculate_and_save(profile)
        profile.refresh_from_db()
        return profile

    def test_one_evidenced_input_does_not_publish(self):
        self.assertFalse(public_score_state(self._with('gate-1', 1)).available)

    def test_most_inputs_evidenced_does_not_publish(self):
        self.assertFalse(public_score_state(self._with('gate-15', 15)).available)

    def test_full_coverage_publishes(self):
        state = public_score_state(self._with('gate-16', 16))

        self.assertTrue(state.available)
        self.assertEqual(state.status, 'PUBLISHED')
        self.assertEqual(state.coverage_percent, 100)

    def test_seeded_full_coverage_never_publishes(self):
        """The invariant that must survive every future threshold change."""
        profile = self._with('gate-seeded', 16, origin=PROVENANCE_SEEDED)

        self.assertFalse(public_score_state(profile).available)

    def test_the_gate_reports_the_coverage_it_used(self):
        state = public_score_state(self._with('gate-reports', 8))

        self.assertFalse(state.available)
        self.assertGreater(state.coverage_percent, 0)
        self.assertLess(state.coverage_percent, 100)

    def test_no_score_never_publishes_however_good_the_evidence(self):
        profile = _evidence(_profile('gate-no-score'))
        profile.ecoiq_total_score = None
        profile.save()

        self.assertFalse(public_score_state(profile).available)


class ProductionEstateIsUnaffected(TestCase):
    """
    Every company in production carries LEGACY_UNKNOWN_PROVENANCE, so wiring
    coverage onto the store publishes nothing that was not publishable before.
    """

    def test_a_legacy_company_stays_contained(self):
        profile = _evidence(_profile('legacy-estate', ecoiq_total_score=71.4),
                            origin=PROVENANCE_UNKNOWN, writer='d3b_backfill')
        recalculate_and_save(profile)
        profile.refresh_from_db()

        self.assertEqual(coverage_for(profile).coverage_percent, 0)
        self.assertFalse(public_score_state(profile).available)

    def test_a_company_with_no_provenance_at_all_stays_contained(self):
        profile = _profile('no-prov-estate', ecoiq_total_score=71.4)

        self.assertEqual(coverage_for(profile).coverage_percent, 0)
        self.assertFalse(public_score_state(profile).available)
