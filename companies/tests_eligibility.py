"""
D5 — the publication gate.

One service decides, and every surface asks it. The company detail page renders
the composite in seventeen places; a second copy of the threshold would
eventually disagree with the first.
"""
from django.test import SimpleTestCase, TestCase

from companies import provenance as prov
from companies.confidence import CONFIDENCE_HIGH, CONFIDENCE_INSUFFICIENT
from companies.eligibility import (
    PROVISIONAL_COVERAGE, PUBLISH_COVERAGE, STATUS_INSUFFICIENT,
    STATUS_PROVISIONAL, STATUS_PUBLISHED, decide, decide_for_company,
    simulate_thresholds,
)
from companies.evidence import (
    PROVENANCE_MEASURED, PROVENANCE_SEEDED, PROVENANCE_UNKNOWN,
    public_score_state,
)
from companies.scoring import recalculate_and_save
from companies.testing import populated
from league.models import Company


def _profile(slug, score=71.4, **overrides):
    company = Company.objects.create(name=slug, slug=slug, country='UK',
                                     ecoiq_score=score)
    profile = populated(company, ecoiq_total_score=score, **overrides)
    return profile


def _evidence(profile, count=16, origin=PROVENANCE_MEASURED, review='proposed'):
    for key in sorted(prov.MATERIAL_METRIC_KEYS)[:count]:
        prov.record(profile, key, origin, written_by='t', review_status=review)
    recalculate_and_save(profile)
    profile.refresh_from_db()
    return profile


class TheThreshold(SimpleTestCase):

    def test_publication_requires_full_coverage(self):
        self.assertEqual(PUBLISH_COVERAGE, 1.0)

    def test_the_provisional_band_is_currently_empty(self):
        """
        Deliberate no-op, not an oversight. The state exists so the surfaces,
        the API contract and the tests are built for a three-state world before
        the threshold that produces the third state is chosen.
        """
        self.assertEqual(PROVISIONAL_COVERAGE, PUBLISH_COVERAGE)

    def test_the_reason_for_the_threshold_is_recorded(self):
        from companies import eligibility

        self.assertIn('467 of 467', eligibility.__doc__)
        self.assertIn('most conservative', eligibility.__doc__)


class Deciding(TestCase):

    def test_full_measured_evidence_publishes(self):
        decision = decide(_evidence(_profile('elig-full')))

        self.assertEqual(decision.status, STATUS_PUBLISHED)
        self.assertTrue(decision.is_published)
        self.assertEqual(decision.coverage_percent, 100)

    def test_partial_evidence_does_not_publish(self):
        decision = decide(_evidence(_profile('elig-partial'), count=15))

        self.assertEqual(decision.status, STATUS_INSUFFICIENT)
        self.assertLess(decision.coverage_percent, 100)

    def test_no_evidence_does_not_publish(self):
        decision = decide(_profile('elig-none'))

        self.assertEqual(decision.status, STATUS_INSUFFICIENT)
        self.assertEqual(decision.coverage_percent, 0)

    def test_seeded_evidence_can_never_publish(self):
        """The invariant that must survive every future threshold change."""
        decision = decide(_evidence(_profile('elig-seeded'),
                                    origin=PROVENANCE_SEEDED))

        self.assertEqual(decision.status, STATUS_INSUFFICIENT)
        self.assertEqual(decision.coverage_percent, 0)

    def test_legacy_evidence_can_never_publish(self):
        decision = decide(_evidence(_profile('elig-legacy'),
                                    origin=PROVENANCE_UNKNOWN))

        self.assertEqual(decision.status, STATUS_INSUFFICIENT)

    def test_no_score_does_not_publish_however_good_the_evidence(self):
        profile = _evidence(_profile('elig-no-score'))
        profile.ecoiq_total_score = None
        profile.save()

        self.assertEqual(decide(profile).status, STATUS_INSUFFICIENT)

    def test_a_missing_profile_fails_closed(self):
        self.assertEqual(decide(None).status, STATUS_INSUFFICIENT)

    def test_every_verdict_states_its_grounds(self):
        for slug, count in (('grounds-full', 16), ('grounds-partial', 4),
                            ('grounds-none', 0)):
            with self.subTest(slug=slug):
                decision = decide(_evidence(_profile(slug), count=count))
                self.assertTrue(decision.reasons)

    def test_unevidenced_inputs_are_called_out(self):
        decision = decide(_evidence(_profile('elig-unevidenced'),
                                    origin=PROVENANCE_SEEDED))

        self.assertTrue(any('seeded or legacy' in r for r in decision.reasons))


class ReadingTheScore(TestCase):
    """
    `public_score` is the only correct way to read a score off the decision.
    Reading `.score` hands out the number regardless of the verdict.
    """

    def test_public_score_is_none_when_not_published(self):
        decision = decide(_evidence(_profile('read-partial'), count=4))

        self.assertIsNotNone(decision.score)
        self.assertIsNone(decision.public_score)

    def test_public_score_is_the_score_when_published(self):
        decision = decide(_evidence(_profile('read-full')))

        self.assertEqual(decision.public_score, decision.score)

    def test_the_decision_is_falsey_when_not_published(self):
        self.assertFalse(decide(_profile('read-falsey')))

    def test_the_decision_is_truthy_when_published(self):
        self.assertTrue(decide(_evidence(_profile('read-truthy'))))


class ConfidenceIsCarried(TestCase):

    def test_the_decision_reports_confidence(self):
        decision = decide(_evidence(_profile('elig-conf'), review='confirmed'))

        self.assertEqual(decision.confidence_label, CONFIDENCE_HIGH)

    def test_unassessable_confidence_blocks_publication(self):
        decision = decide(_evidence(_profile('elig-conf-none'),
                                    origin=PROVENANCE_SEEDED))

        self.assertEqual(decision.confidence_label, CONFIDENCE_INSUFFICIENT)
        self.assertFalse(decision.is_published)

    def test_low_confidence_does_not_block_full_coverage(self):
        """
        Confidence has its say by ruling out the unassessable case; it does not
        get a second vote. A high-confidence assessment of a quarter of the
        inputs is still an assessment of a quarter of the inputs, and the
        converse holds too — coverage is the deciding threshold.
        """
        from companies.confidence import CONFIDENCE_LOW
        from companies.evidence import PROVENANCE_INFERRED

        decision = decide(_evidence(_profile('elig-low-conf'),
                                    origin=PROVENANCE_INFERRED))

        self.assertEqual(decision.confidence_label, CONFIDENCE_LOW)
        self.assertEqual(decision.status, STATUS_PUBLISHED)


class OneRuleNotSeventeen(TestCase):

    def test_public_score_state_delegates_to_the_service(self):
        profile = _evidence(_profile('delegate-full'))

        self.assertEqual(public_score_state(profile).available,
                         decide(profile).is_published)

    def test_they_agree_when_contained(self):
        profile = _evidence(_profile('delegate-partial'), count=4)

        self.assertFalse(public_score_state(profile).available)
        self.assertFalse(decide(profile).is_published)

    def test_the_coverage_percent_matches(self):
        profile = _evidence(_profile('delegate-cov'), count=8)

        self.assertEqual(public_score_state(profile).coverage_percent,
                         decide(profile).coverage_percent)

    def test_the_threshold_appears_in_exactly_one_module(self):
        """A second copy would eventually disagree with the first."""
        import subprocess

        result = subprocess.run(
            ['grep', '-rln', 'PUBLISH_COVERAGE', '--include=*.py',
             '--exclude=tests*', '.'],
            capture_output=True, text=True, cwd='.')
        files = [f for f in result.stdout.split() if 'test' not in f]

        self.assertEqual(files, ['./companies/eligibility.py'])


class LeagueGate(TestCase):

    def test_a_company_is_gated_on_its_profile(self):
        profile = _evidence(_profile('league-full'))

        self.assertTrue(decide_for_company(profile.company).is_published)

    def test_a_company_with_no_profile_has_no_evidence(self):
        company = Company.objects.create(name='bare', slug='bare-league',
                                         country='UK', ecoiq_score=70.0)

        self.assertFalse(decide_for_company(company).is_published)

    def test_a_partially_evidenced_company_is_gated(self):
        profile = _evidence(_profile('league-partial'), count=4)

        self.assertFalse(decide_for_company(profile.company).is_published)


class ThresholdSimulation(TestCase):
    """
    Provided so the threshold can be re-taken against real data when production
    has some, rather than being argued from first principles a second time.
    """

    def test_it_reports_each_candidate(self):
        profiles = [_evidence(_profile(f'sim-{n}'), count=n)
                    for n in (0, 4, 8, 16)]

        results = simulate_thresholds(profiles)

        self.assertEqual(set(results), {0.2, 0.4, 0.6, 0.8, 1.0})

    def test_a_lower_threshold_publishes_more(self):
        profiles = [_evidence(_profile(f'sim2-{n}'), count=n)
                    for n in (0, 4, 8, 16)]

        results = simulate_thresholds(profiles)

        self.assertGreaterEqual(results[0.2]['eligible'],
                                results[1.0]['eligible'])

    def test_the_production_shape_yields_nothing_at_any_threshold(self):
        """
        Measured, not assumed: every production company sits at 0% coverage,
        so the distribution contains no information to choose a threshold with.
        """
        profiles = [_evidence(_profile(f'sim3-{i}'), origin=PROVENANCE_UNKNOWN)
                    for i in range(3)]

        results = simulate_thresholds(profiles)

        for threshold, counts in results.items():
            with self.subTest(threshold=threshold):
                self.assertEqual(counts['eligible'], 0)
                self.assertEqual(counts['unavailable'], 3)
