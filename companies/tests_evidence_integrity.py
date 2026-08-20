"""
Evidence integrity invariants.

The governing principle is that UNKNOWN IS NOT NEUTRAL. These tests pin it as an
executable statement rather than a document, and they cover the five scenarios in
the plan — including the one that makes a naive `50 -> NULL` migration dangerous.

They also record, deliberately and visibly, where today's behaviour still
violates the principle. Those cases are asserted as they actually are and marked
with the plan step that will change them, so the tests document reality instead
of an aspiration. When D2 lands, the assertions move and the failure is the
signal that it worked.
"""
from django.test import SimpleTestCase, TestCase

from companies.evidence import (
    ELIGIBILITY_ELIGIBLE, ELIGIBILITY_PROVISIONAL, ELIGIBILITY_UNAVAILABLE,
    EVIDENCED_PROVENANCE, MATERIAL_INPUTS, PROVENANCE_MEASURED, PROVENANCE_SEEDED,
    PROVENANCE_UNKNOWN, AVAILABILITY_INSUFFICIENT,
    coverage_for, eligibility, field_provenance,
)
from companies.models import CompanyProfile
from league.models import Company


def _company(name, slug):
    return Company.objects.create(name=name, slug=slug, country='United Kingdom')


class MaterialInputDefinitionTests(SimpleTestCase):
    """The denominator has to be defensible or the percentage is theatre."""

    def test_weights_sum_to_the_whole_composite(self):
        total = sum(i.weight for i in MATERIAL_INPUTS)
        self.assertAlmostEqual(total, 1.0, places=6)

    def test_weights_mirror_the_scoring_engine_pillars(self):
        by_pillar: dict[str, float] = {}
        for item in MATERIAL_INPUTS:
            by_pillar[item.pillar] = by_pillar.get(item.pillar, 0.0) + item.weight
        # companies/scoring.py composite weights
        self.assertAlmostEqual(by_pillar['public_benefit'], 0.25, places=6)
        self.assertAlmostEqual(by_pillar['environmental'], 0.25, places=6)
        self.assertAlmostEqual(by_pillar['modernization'], 0.20, places=6)
        self.assertAlmostEqual(by_pillar['transparency'], 0.15, places=6)
        self.assertAlmostEqual(by_pillar['anti_corruption'], 0.10, places=6)
        self.assertAlmostEqual(by_pillar['ethical_alignment'], 0.05, places=6)

    def test_seeded_and_unknown_are_not_evidence(self):
        self.assertNotIn(PROVENANCE_SEEDED, EVIDENCED_PROVENANCE)
        self.assertNotIn(PROVENANCE_UNKNOWN, EVIDENCED_PROVENANCE)
        self.assertIn(PROVENANCE_MEASURED, EVIDENCED_PROVENANCE)


class EligibilityRuleTests(SimpleTestCase):

    def test_zero_coverage_is_never_eligible_or_provisional(self):
        """The core invariant: ZERO EVIDENCE != NEUTRAL SCORE."""
        for minimum, full in ((0.0, 0.0), (0.2, 0.4), (0.6, 0.9)):
            with self.subTest(minimum=minimum):
                self.assertEqual(
                    eligibility(0.0, minimum, full), ELIGIBILITY_UNAVAILABLE,
                    'zero coverage produced a presentable score')

    def test_partial_coverage_is_provisional_not_full(self):
        self.assertEqual(eligibility(0.30, 0.20, 0.60), ELIGIBILITY_PROVISIONAL)

    def test_full_coverage_is_eligible(self):
        self.assertEqual(eligibility(0.95, 0.20, 0.60), ELIGIBILITY_ELIGIBLE)


class ScenarioTests(TestCase):
    """The five scenarios from the plan."""

    def test_scenario_d_zero_evidence_yields_zero_coverage(self):
        """
        A profile created with nothing but model defaults. Every field holds a
        number, so any naive check would call it complete; coverage must not.
        """
        profile = CompanyProfile.objects.create(company=_company('Zero Ltd', 'zero-ltd'))
        report = coverage_for(profile)

        self.assertEqual(report.coverage, 0.0)
        self.assertEqual(report.coverage_percent, 0)
        self.assertEqual(report.availability, AVAILABILITY_INSUFFICIENT)
        self.assertEqual(report.covered_inputs, 0)
        self.assertEqual(len(report.missing), report.total_inputs)

    def test_scenario_d_zero_evidence_cannot_produce_a_confident_public_score(self):
        """
        THE critical regression test.

        A company with no evidence must not become presentable merely because the
        model defaults make every field non-null. This is the invariant the whole
        plan exists to protect.
        """
        profile = CompanyProfile.objects.create(company=_company('Nothing Co', 'nothing-co'))
        coverage = coverage_for(profile).coverage
        self.assertEqual(
            eligibility(coverage, minimum=0.20, full=0.60), ELIGIBILITY_UNAVAILABLE)

    def test_scenario_e_a_real_value_of_exactly_50_is_not_unknown(self):
        """
        Essential, and the reason a bulk `50 -> NULL` migration is forbidden.

        A genuine measurement of 50 must stay distinguishable from an unset
        default. Provenance — not the number — is what separates them, so a
        profile carrying real linked sources is not reported as SEEDED even when
        the value equals the default exactly.
        """
        evidenced = CompanyProfile.objects.create(
            company=_company('Exactly Fifty Ltd', 'exactly-fifty'),
            waste_management_score=50.0,
            public_sources=[{'url': 'https://example.org/report', 'title': 'Waste audit 2026'}],
        )
        bare = CompanyProfile.objects.create(
            company=_company('Bare Ltd', 'bare-ltd'),
            waste_management_score=50.0,
        )

        self.assertEqual(field_provenance(bare, 'waste_management_score'), PROVENANCE_SEEDED)
        self.assertNotEqual(
            field_provenance(evidenced, 'waste_management_score'), PROVENANCE_SEEDED,
            'a value with linked sources was written off as a seeded default')

    def test_scenario_e_the_two_profiles_are_distinguishable(self):
        """Same stored number, different provenance — the distinction must survive."""
        a = CompanyProfile.objects.create(
            company=_company('A Ltd', 'a-ltd'), waste_management_score=50.0,
            public_sources=[{'url': 'https://example.org/a'}])
        b = CompanyProfile.objects.create(
            company=_company('B Ltd', 'b-ltd'), waste_management_score=50.0)

        self.assertEqual(a.waste_management_score, b.waste_management_score)
        self.assertNotEqual(
            field_provenance(a, 'waste_management_score'),
            field_provenance(b, 'waste_management_score'))

    def test_scenario_a_a_non_default_value_is_still_not_evidence_without_provenance(self):
        """
        Honest about the current limit. A value of 61.3 is clearly not a default,
        but nothing in the schema records where it came from — and the seeding
        commands produce exactly such values. It must not be counted as evidence
        just because it looks specific.
        """
        profile = CompanyProfile.objects.create(
            company=_company('Specific Ltd', 'specific-ltd'),
            waste_management_score=61.3)
        self.assertEqual(field_provenance(profile, 'waste_management_score'), PROVENANCE_UNKNOWN)
        self.assertEqual(coverage_for(profile).coverage, 0.0)


class CoverageReportingTests(TestCase):

    def test_percentage_is_whole_numbers_only(self):
        """
        The denominator is ~16 inputs. Reporting '82.4%' would imply precision
        the data cannot support.
        """
        profile = CompanyProfile.objects.create(company=_company('Round Ltd', 'round-ltd'))
        self.assertIsInstance(coverage_for(profile).coverage_percent, int)

    def test_human_summary_states_the_denominator(self):
        profile = CompanyProfile.objects.create(company=_company('Summary Ltd', 'summary-ltd'))
        text = str(coverage_for(profile))
        self.assertIn('Evidence coverage', text)
        self.assertIn('material inputs', text)


class CurrentBehaviourIsRecordedTests(TestCase):
    """
    Behaviour recorded against the plan's steps.

    Two of these were written inverted in #238 to record defects that D2 has
    since fixed; their assertions moved rather than being deleted, so the file
    shows what changed. The rest still record genuinely open items — field
    nullability is D4.
    """

    def test_scoring_engine_no_longer_turns_unknown_into_zero(self):
        """
        FIXED by D2. This assertion was written inverted — `_clamp(None) == 0.0`
        — to record the defect, with a note that D2 would make it fail. It did,
        so the assertion moved here rather than being deleted: the pair is the
        record that the fix actually changed behaviour.

        `float(v or 0)` turned unknown into the worst possible score, and could
        not tell None from a real 0.0. Both now hold.
        """
        from companies.scoring import _clamp
        self.assertIsNone(_clamp(None))
        self.assertEqual(_clamp(0.0), 0.0)

    def test_scoring_engine_no_longer_invents_fifty(self):
        """
        FIXED by D2. Was asserted as `_avg(None, None, None) == 50.0` — the
        'unknown becomes average' behaviour this programme exists to remove.
        """
        from companies.scoring import _avg
        self.assertIsNone(_avg(None, None, None))
        self.assertEqual(_avg(50.0), 50.0)

    def test_score_fields_are_still_non_nullable(self):
        """Nullability is plan step D4, deliberately not D1."""
        f = CompanyProfile._meta.get_field('waste_management_score')
        self.assertFalse(f.null)
        self.assertEqual(f.default, 50.0)

    def test_this_module_changes_no_score(self):
        """
        D1 is measurement only. Computing coverage must not mutate the profile.
        """
        profile = CompanyProfile.objects.create(
            company=_company('Immutable Ltd', 'immutable-ltd'),
            waste_management_score=61.3)
        before = (profile.waste_management_score, profile.ecoiq_total_score)
        coverage_for(profile)
        profile.refresh_from_db()
        self.assertEqual((profile.waste_management_score, profile.ecoiq_total_score), before)
