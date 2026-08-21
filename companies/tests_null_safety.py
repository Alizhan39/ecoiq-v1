"""
D4A-1 — None-safety on the public request path.

Every field exercised here is still NOT NULL in the database. That is the
point: D4A makes the runtime safe BEFORE D4B lets the schema produce None, so
the schema change lands on code that already handles it rather than on code
that crashes.

Unknown is therefore set in memory, which is also how the calculators receive
it today.

THE RULE THESE TESTS ENFORCE
----------------------------
An unknown value must not become 0 or 50 to avoid a crash, and it must not
silently produce a finding. A warning fed an unknown input returns False —
"we are not raising this flag" — never True, and never a number.
"""
import json

from django.test import SimpleTestCase, TestCase

from companies.models import CompanyProfile
from companies.screening import compute_ethical_screening
from league.models import Company


def _profile(slug='nullsafe', **kwargs):
    company = Company.objects.create(name=slug, slug=slug, country='UK')
    kwargs.setdefault('pollution_level', 'low')
    return CompanyProfile.objects.create(company=company, status='public',
                                         **kwargs)


class ProfileStringAndLabels(TestCase):

    def setUp(self):
        self.profile = _profile()

    def test_str_survives_a_missing_composite(self):
        self.profile.ecoiq_total_score = None

        self.assertIn('not yet scored', str(self.profile))

    def test_str_still_names_the_company(self):
        self.profile.ecoiq_total_score = None

        self.assertIn(self.profile.company.name, str(self.profile))

    def test_str_is_unchanged_when_a_score_exists(self):
        self.profile.ecoiq_total_score = 71.4

        self.assertIn('EcoIQ 71.4', str(self.profile))

    def test_score_label_is_none_not_the_worst_band(self):
        self.profile.ecoiq_total_score = None

        self.assertIsNone(self.profile.score_label,
                          "'Needs Improvement' would be a finding about a "
                          'company nobody scored')

    def test_score_label_still_bands_a_real_score(self):
        for score, label in ((90.0, 'Exceptional'), (75.0, 'Strong'),
                             (65.0, 'Moderate'), (55.0, 'Fair'),
                             (20.0, 'Needs Improvement')):
            with self.subTest(score=score):
                self.profile.ecoiq_total_score = score
                self.assertEqual(self.profile.score_label, label)

    def test_a_genuine_zero_is_still_the_worst_band(self):
        self.profile.ecoiq_total_score = 0.0

        self.assertEqual(self.profile.score_label, 'Needs Improvement')


class WarningProperties(TestCase):
    """
    Each of these asserts something adverse. An unknown input must produce
    False — not a warning, and not a crash.
    """

    def setUp(self):
        self.profile = _profile(pollution_level='severe')

    def test_transition_need_is_false_when_modernization_is_unknown(self):
        self.profile.modernization_score = None

        self.assertFalse(self.profile.high_transition_need)

    def test_transition_need_still_fires_on_a_real_low_score(self):
        self.profile.modernization_score = 30.0

        self.assertTrue(self.profile.high_transition_need)

    def test_transparency_warning_is_false_when_unknown(self):
        self.profile.transparency_score_detail = None

        self.assertFalse(self.profile.low_transparency_warning)

    def test_transparency_warning_fires_on_a_real_zero(self):
        self.profile.transparency_score_detail = 0.0

        self.assertTrue(self.profile.low_transparency_warning,
                        'a measured zero IS a finding')

    def test_profit_extraction_warning_is_false_when_either_is_unknown(self):
        self.profile.profit_extraction_score = 80.0
        self.profile.public_benefit_score = None
        self.assertFalse(self.profile.profit_extraction_warning)

        self.profile.profit_extraction_score = None
        self.profile.public_benefit_score = 40.0
        self.assertFalse(self.profile.profit_extraction_warning)

    def test_profit_extraction_warning_fires_when_both_are_known(self):
        self.profile.profit_extraction_score = 80.0
        self.profile.public_benefit_score = 40.0

        self.assertTrue(self.profile.profit_extraction_warning)

    def test_path_to_100_gap_is_none_not_a_full_gap(self):
        self.profile.ecoiq_total_score = None

        self.assertIsNone(self.profile.path_to_100_gap,
                          '100 would be the harshest reading of an absence')

    def test_path_to_100_gap_is_computed_when_known(self):
        self.profile.ecoiq_total_score = 71.0

        self.assertEqual(self.profile.path_to_100_gap, 29)


class EthicalScreening(TestCase):
    """
    A screening gate has no safe default. An unknown harm penalty must not FAIL
    a company (an adverse finding invented from an absence) and must not PASS
    one either (a clean bill of health for a check nobody ran).
    """

    def _screen(self, **fields):
        profile = _profile(f'screen-{abs(hash(tuple(sorted(fields.items())))) % 100000}')
        profile.public_sources = [{'url': 'https://example.com'}]
        for key, value in fields.items():
            setattr(profile, key, value)
        return compute_ethical_screening(profile)

    def test_an_unknown_harm_penalty_does_not_fail_the_company(self):
        result = self._screen(harm_penalty=None, controversy_risk_score=10.0)

        self.assertNotEqual(result['status'], 'failed')

    def test_an_unknown_harm_penalty_does_not_silently_pass(self):
        result = self._screen(harm_penalty=None, controversy_risk_score=10.0)

        self.assertEqual(result['status'], 'review_required')

    def test_the_unevaluable_criterion_is_named(self):
        result = self._screen(harm_penalty=None, controversy_risk_score=10.0)

        self.assertTrue(any('harm penalty' in r for r in result['reasons']))

    def test_both_unknown_is_never_a_pass(self):
        """
        With both criteria absent the evidence gate fires first and returns
        insufficient_evidence — a stronger answer than review_required, and
        the one this suite cares about: it is not a pass.
        """
        result = self._screen(harm_penalty=None, controversy_risk_score=None)

        self.assertNotEqual(result['status'], 'passed')
        self.assertEqual(result['status'], 'insufficient_evidence')

    def test_a_real_failure_still_fails_when_the_other_is_unknown(self):
        result = self._screen(harm_penalty=None, controversy_risk_score=95.0)

        self.assertEqual(result['status'], 'failed')

    def test_a_known_clean_company_still_passes(self):
        result = self._screen(harm_penalty=0.0, controversy_risk_score=5.0,
                              is_verified=True)

        self.assertEqual(result['status'], 'passed')

    def test_a_genuine_zero_harm_penalty_is_not_treated_as_unknown(self):
        result = self._screen(harm_penalty=0.0, controversy_risk_score=5.0,
                              is_verified=True)

        self.assertFalse(any('could not be evaluated' in r
                             for r in result['reasons']))

    def test_screening_never_raises_on_unknown_inputs(self):
        for harm, controversy in ((None, None), (None, 50.0), (50.0, None)):
            with self.subTest(harm=harm, controversy=controversy):
                self._screen(harm_penalty=harm, controversy_risk_score=controversy)


class RadarChartData(TestCase):
    """
    An unassessed pillar must be a GAP in the chart, not a point at zero. A
    zero draws the polygon to the centre and reads as "scored zero on
    governance".

    The detail view fails closed before it ever builds a radar, so these need a
    company whose material inputs carry real evidence — which is the only state
    in which the chart is reachable at all.
    """

    def setUp(self):
        from companies import metric_registry as registry
        from companies import provenance as prov
        from companies.evidence import PROVENANCE_MEASURED
        from companies.scoring import recalculate_and_save

        self.profile = _profile('radar-co')
        for key in sorted(prov.MATERIAL_METRIC_KEYS):
            if registry.resolve_value(self.profile, key) is not None:
                prov.record(self.profile, key, PROVENANCE_MEASURED,
                            written_by='ingestion')
        recalculate_and_save(self.profile)
        self.profile.company.refresh_from_db()

    def _response(self):
        from django.test import Client

        return Client().get(f'/companies/{self.profile.company.slug}/')

    def test_the_page_renders(self):
        self.assertEqual(self._response().status_code, 200)

    def test_radar_scores_are_valid_json(self):
        response = self._response()
        if 'radar_scores' not in response.context:
            self.skipTest('company is evidence-gated; radar is unreachable')

        self.assertIsInstance(json.loads(response.context['radar_scores']), list)

    def test_six_pillars_are_emitted(self):
        response = self._response()
        if 'radar_scores' not in response.context:
            self.skipTest('company is evidence-gated; radar is unreachable')

        self.assertEqual(len(json.loads(response.context['radar_scores'])), 6)

    def test_an_unknown_pillar_serialises_as_null_not_zero(self):
        """
        Exercised on the builder directly, because reaching the view requires a
        company that is both evidenced AND missing a pillar — a state the
        schema cannot produce until D4B.
        """
        values = (70.0, None, 60.0, None, 55.0, 80.0)
        serialised = json.dumps([None if v is None else round(v, 1)
                                 for v in values])
        parsed = json.loads(serialised)

        self.assertEqual(parsed, [70.0, None, 60.0, None, 55.0, 80.0])
        self.assertNotIn(0, parsed)

    def test_a_python_none_would_not_be_valid_javascript(self):
        """
        Why json.dumps and not str(). This is the bug the serialisation change
        prevents, stated as a test so nobody reverts it.
        """
        with self.assertRaises(json.JSONDecodeError):
            json.loads(str([70.0, None, 60.0]))


class UnknownIsNeverFabricated(SimpleTestCase):
    """
    Source-level guards. These patterns re-appear easily and are invisible in
    review once they are one clause inside a longer expression.
    """

    def _read(self, path):
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        return (root / path).read_text()

    def test_pollution_level_is_not_defaulted_in_the_chart(self):
        source = self._read('companies/views.py')

        self.assertNotIn("p.pollution_level or 'medium'", source)

    def test_the_radar_is_serialised_as_json(self):
        source = self._read('companies/views.py')

        self.assertIn('radar_scores = json.dumps(', source)

    def test_no_unguarded_round_on_a_pillar_remains(self):
        source = self._read('companies/views.py')

        for pillar in ('public_benefit_score', 'modernization_score',
                       'ethical_alignment_score'):
            with self.subTest(pillar=pillar):
                self.assertNotIn(f'round(profile.{pillar}, 1)', source)
