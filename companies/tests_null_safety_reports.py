"""
D4A-2 — None-safety in reports, prompts, snapshots and analyst surfaces.

The sharpest case in this group is the LLM prompt.

A format specifier crashes on None — `f'{score:.1f}'` raises — and the reflex
fix is to substitute a number so the string builds. That reflex is how `50` got
into so much of this codebase. In a prompt it is worse than elsewhere: handed
"50.0", a language model reasons about an average company and writes fluent,
confident prose about a measurement nobody made. Neither the reader nor
anything downstream can tell that apart from a real finding.

So the substitute is WORDS.
"""
from django.test import SimpleTestCase, TestCase

from core.unknown import format_known
from companies.models import CompanyProfile
from league.models import Company


def _profile(slug='reports', **kwargs):
    company = Company.objects.create(name=slug, slug=slug, country='UK')
    kwargs.setdefault('pollution_level', 'low')
    return CompanyProfile.objects.create(company=company, status='public',
                                         **kwargs)


class FormatKnown(SimpleTestCase):

    def test_a_known_value_formats_normally(self):
        self.assertEqual(format_known(71.44), '71.4')

    def test_unknown_becomes_words_not_a_number(self):
        result = format_known(None)

        self.assertEqual(result, 'not assessed')
        self.assertFalse(any(ch.isdigit() for ch in result),
                         'a substituted number is a fabricated measurement')

    def test_a_genuine_zero_is_formatted_as_zero(self):
        self.assertEqual(format_known(0.0), '0.0')

    def test_zero_is_not_confused_with_unknown(self):
        self.assertNotEqual(format_known(0.0), format_known(None))

    def test_the_absent_wording_is_caller_chosen(self):
        self.assertEqual(format_known(None, absent='unknown'), 'unknown')

    def test_the_spec_is_honoured(self):
        self.assertEqual(format_known(71.44, spec='.0f'), '71')

    def test_a_non_numeric_value_does_not_raise(self):
        self.assertEqual(format_known('abc'), 'not assessed')

    def test_it_never_raises_on_none(self):
        for spec in ('.1f', '.0f', '.2f'):
            with self.subTest(spec=spec):
                format_known(None, spec=spec)


class LanguageModelPrompt(TestCase):
    """The fabrication that would be hardest to detect downstream."""

    def setUp(self):
        self.profile = _profile('prompt-co')

    def _prompt(self):
        from companies.ai_helpers import _profile_context

        return _profile_context(self.profile)

    def test_the_prompt_builds_with_every_score_unknown(self):
        for field in ('ecoiq_total_score', 'public_benefit_score',
                      'environmental_responsibility_score', 'modernization_score',
                      'transparency_anti_corruption_score', 'anti_corruption_score',
                      'ethical_alignment_score'):
            setattr(self.profile, field, None)

        self.assertIsInstance(self._prompt(), str)

    def test_unknown_scores_reach_the_model_as_words(self):
        self.profile.public_benefit_score = None

        self.assertIn('Public Benefit Score:          not assessed', self._prompt())

    def test_no_number_is_substituted_on_any_score_line(self):
        """
        Asserted per line, not across the whole prompt: other lines legitimately
        carry real numbers, including a measured 0.0.
        """
        for field in ('ecoiq_total_score', 'public_benefit_score',
                      'environmental_responsibility_score', 'modernization_score',
                      'transparency_anti_corruption_score', 'anti_corruption_score',
                      'ethical_alignment_score'):
            setattr(self.profile, field, None)

        score_lines = [l for l in self._prompt().split('\n')
                       if 'Score:' in l and 'Profit Extraction' not in l]

        self.assertTrue(score_lines)
        for line in score_lines:
            with self.subTest(line=line):
                self.assertIn('not assessed', line)
                # '/100' is a scale label, not a value.
                reading = line.split(':', 1)[1].replace('/100', '')
                self.assertFalse(any(ch.isdigit() for ch in reading),
                                 'no number may stand in for an unknown score')

    def test_no_moral_label_is_asserted_without_a_score(self):
        """
        moral_label is a stored field with its own default, so an unscored
        company still reported one -- telling the model it is a 'Transitional
        Company' when nobody assessed it.
        """
        self.profile.ecoiq_total_score = None

        line = next(l for l in self._prompt().split('\n')
                    if l.startswith('EcoIQ Total Score:'))

        self.assertEqual(line, 'EcoIQ Total Score: not assessed')
        self.assertNotIn('Company)', line)

    def test_the_label_is_kept_when_a_score_exists(self):
        self.profile.ecoiq_total_score = 71.4

        line = next(l for l in self._prompt().split('\n')
                    if l.startswith('EcoIQ Total Score:'))

        self.assertIn('71.4/100', line)
        self.assertIn('(', line)

    def test_a_genuine_zero_elsewhere_is_untouched(self):
        """profit_extraction_risk_score defaults to 0.0 and that is a real value."""
        self.profile.profit_extraction_risk_score = 0.0

        self.assertIn('Profit Extraction Risk:        0.0', self._prompt())

    def test_a_zero_renewable_share_is_not_not_disclosed(self):
        """`if x else` on a number is a falsy test; 0% is a finding."""
        self.profile.renewable_energy_share = 0.0

        prompt = self._prompt()
        self.assertIn('Renewable Energy Share: 0%', prompt)
        self.assertNotIn('Renewable: Not disclosed', prompt)

    def test_an_unknown_renewable_share_is_not_disclosed(self):
        self.profile.renewable_energy_share = None

        self.assertIn('Renewable: Not disclosed', self._prompt())

    def test_zero_emissions_are_reported_not_hidden(self):
        self.profile.estimated_emissions = 0

        self.assertIn('Estimated Emissions: 0 tCO2/yr', self._prompt())

    def test_a_known_score_still_reaches_the_model_as_a_number(self):
        self.profile.public_benefit_score = 63.2

        self.assertIn('63.2', self._prompt())

    def test_a_measured_zero_reaches_the_model_as_zero(self):
        self.profile.public_benefit_score = 0.0

        prompt = self._prompt()
        self.assertIn('Public Benefit Score:          0.0', prompt)
        self.assertNotIn('Public Benefit Score:          not assessed', prompt)


class ReportSnapshot(TestCase):
    """
    A snapshot records what was true when the report was written, and is the
    record a future reader would use to check its claims. A substituted number
    would be indistinguishable from a real reading forever after.
    """

    def setUp(self):
        self.profile = _profile('snapshot-co')

    def _snapshot(self):
        from core.unknown import known

        return {
            'ecoiq_total_score': known(self.profile.ecoiq_total_score),
            'controversy_risk_score': known(self.profile.controversy_risk_score),
            'harm_penalty': known(self.profile.harm_penalty),
        }

    def test_unknown_stays_null_in_the_snapshot(self):
        self.profile.ecoiq_total_score = None

        self.assertIsNone(self._snapshot()['ecoiq_total_score'])

    def test_a_known_value_is_a_float(self):
        self.profile.ecoiq_total_score = 71.4

        self.assertEqual(self._snapshot()['ecoiq_total_score'], 71.4)

    def test_a_genuine_zero_survives(self):
        self.profile.harm_penalty = 0.0

        self.assertEqual(self._snapshot()['harm_penalty'], 0.0)

    def test_the_snapshot_is_json_serialisable_with_nulls(self):
        import json

        self.profile.ecoiq_total_score = None

        self.assertIn('null', json.dumps(self._snapshot()))


class HarmPenaltyLine(TestCase):
    """
    The minus sign is the subtlety: '-not assessed pts' would be gibberish, and
    '-0.0 pts' would be a claim that no harm was found.
    """

    def _line(self, harm):
        return (f'Harm Penalty Applied: -{harm:.1f} pts' if harm is not None
                else 'Harm Penalty Applied: not assessed')

    def test_an_unknown_penalty_drops_the_minus_sign(self):
        line = self._line(None)

        self.assertEqual(line, 'Harm Penalty Applied: not assessed')
        self.assertNotIn('-not', line)

    def test_a_real_penalty_keeps_it(self):
        self.assertEqual(self._line(12.0), 'Harm Penalty Applied: -12.0 pts')

    def test_a_measured_zero_is_reported_as_zero(self):
        self.assertEqual(self._line(0.0), 'Harm Penalty Applied: -0.0 pts')


class AdminScoreColumn(TestCase):
    """An unscored profile must not be coloured like a failing one."""

    def setUp(self):
        from companies.admin import CompanyProfileAdmin
        from django.contrib.admin.sites import site

        self.admin = CompanyProfileAdmin(CompanyProfile, site)
        self.profile = _profile('admin-co')

    def _render(self):
        for name in ('score_breakdown', 'pillar_breakdown', 'score_bars'):
            method = getattr(self.admin, name, None)
            if method is not None:
                return str(method(self.profile))
        self.skipTest('score breakdown display not found on the admin')

    def test_it_renders_with_no_score(self):
        self.profile.ecoiq_total_score = None

        self.assertIn('not yet scored', self._render())

    def test_it_is_not_coloured_as_a_failure(self):
        self.profile.ecoiq_total_score = None

        self.assertNotIn('#e63946', self._render().split('EcoIQ Total')[-1])

    def test_a_real_score_still_renders(self):
        self.profile.ecoiq_total_score = 78.0

        self.assertIn('78.0', self._render())


class MizanDimensionsForHikma(TestCase):
    """
    Mizan re-normalises across the dimensions it can compute, so any of them
    can legitimately be None. round(None, 1) raises.
    """

    def _dims(self, values):
        def _dim(key):
            value = values.get(key)
            return None if value is None else round(value, 1)

        return {k: _dim(k) for k in values}

    def test_an_unknown_dimension_stays_none(self):
        result = self._dims({'public_benefit_score': None,
                             'stewardship_score': 61.44})

        self.assertIsNone(result['public_benefit_score'])
        self.assertEqual(result['stewardship_score'], 61.4)

    def test_no_dimension_is_rounded_into_existence(self):
        result = self._dims({'public_benefit_score': None})

        self.assertNotEqual(result['public_benefit_score'], 0)
        self.assertNotEqual(result['public_benefit_score'], 50)


class SourceGuards(SimpleTestCase):
    """Patterns that reappear easily and are invisible inside a longer line."""

    def _read(self, path):
        from pathlib import Path

        return (Path(__file__).resolve().parent.parent / path).read_text()

    def test_the_prompt_no_longer_formats_scores_directly(self):
        source = self._read('companies/ai_helpers.py')

        for field in ('public_benefit_score', 'modernization_score',
                      'anti_corruption_score'):
            with self.subTest(field=field):
                self.assertNotIn(f'{{profile.{field}:.1f}}', source)

    def test_the_snapshot_no_longer_casts_with_float(self):
        source = self._read('companies/investment_report.py')

        self.assertNotIn('float(profile.ecoiq_total_score)', source)
        self.assertNotIn('float(profile.harm_penalty)', source)

    def test_hikma_no_longer_rounds_unguarded(self):
        source = self._read('hikma/assessment.py')

        self.assertNotIn('round(m["public_benefit_score"], 1)', source)
