"""
The evaluation framework.

The rule under test: NOT YET MEASURED is a valid result and must never become
0%. Those are different statements — 0% means "we measured and it failed";
NOT YET MEASURED means "nobody looked" — and rendering the second as the first
is the same defect as a substituted score, applied to the thing that decides
whether a module may be called production.
"""
from django.test import SimpleTestCase, TestCase

from platform_registry.evaluation import (
    DETERMINISM, NOT_MEASURED, PREDICTION_ERROR, Evaluation, Measurement,
    evaluate_all, evaluate_ml_score,
)


class UnmeasuredIsNeverZero(SimpleTestCase):

    def test_an_unmeasured_metric_displays_as_words(self):
        measurement = Measurement(PREDICTION_ERROR, None)

        self.assertEqual(measurement.display, NOT_MEASURED)
        self.assertFalse(measurement.measured)

    def test_it_is_not_rendered_as_a_number(self):
        display = Measurement(PREDICTION_ERROR, None).display

        self.assertNotEqual(display, '0')
        self.assertNotEqual(display, '0%')
        self.assertTrue(any(c.isalpha() for c in display))

    def test_a_measured_zero_is_shown_as_zero(self):
        """
        The distinction that matters: a model with zero error HAS been
        measured, and that is a strong result rather than a missing one.
        """
        measurement = Measurement(PREDICTION_ERROR, 0.0, ' points')

        self.assertTrue(measurement.measured)
        self.assertIn('0', measurement.display)
        self.assertNotEqual(measurement.display, NOT_MEASURED)

    def test_an_evaluation_with_nothing_measured_says_so(self):
        evaluation = Evaluation('x', [Measurement(PREDICTION_ERROR, None)])

        self.assertFalse(evaluation.is_measured)
        self.assertEqual(evaluation.summary, NOT_MEASURED)

    def test_asking_for_an_absent_metric_returns_unmeasured(self):
        evaluation = Evaluation('x', [])

        self.assertFalse(evaluation.get(DETERMINISM).measured)


class MeasurementsCarryTheirMethod(TestCase):

    def test_a_measured_value_states_how_it_was_obtained(self):
        """A number without a method is not a measurement."""
        for evaluation in evaluate_all().values():
            for measurement in evaluation.measurements:
                if measurement.measured:
                    with self.subTest(metric=measurement.metric):
                        self.assertTrue(measurement.method.strip())

    def test_every_evaluation_carries_a_note(self):
        for key, evaluation in evaluate_all().items():
            with self.subTest(key=key):
                self.assertTrue(evaluation.notes.strip())


class EveryModuleIsCovered(TestCase):

    def test_the_framework_covers_the_whole_registry(self):
        from platform_registry.agents import MODULES

        self.assertEqual(set(evaluate_all()), {m.key for m in MODULES})

    def test_no_generative_agent_claims_a_measurement(self):
        """
        None has a labelled evaluation set. A harness filled with generated
        examples would produce numbers measuring nothing.
        """
        from platform_registry.agents import AGENT, REGISTRY

        for key, evaluation in evaluate_all().items():
            if REGISTRY[key].kind == AGENT:
                with self.subTest(key=key):
                    self.assertFalse(evaluation.is_measured)

    def test_deterministic_engines_claim_determinism_not_accuracy(self):
        """
        The honest claim about a formula is that it is reproducible and pinned
        by tests — not that it is "accurate", which would need a ground truth
        this domain does not have.
        """
        evaluation = evaluate_all()['evidence.coverage']

        self.assertTrue(evaluation.get(DETERMINISM).measured)
        self.assertIn('ground truth', evaluation.notes)


class MlScoreMeasurement(TestCase):
    """A real measurement, over real data, with its limits stated."""

    def _profile(self, slug, composite, ml_score):
        from companies.testing import populated
        from league.models import Company

        company = Company.objects.create(name=slug, slug=slug, country='UK')
        profile = populated(company, ecoiq_total_score=composite)
        if ml_score is not None:
            company.ml_score = ml_score
            company.save()
        return profile

    def test_nothing_to_compare_is_unmeasured_not_zero_error(self):
        self._profile('no-ml', 70.0, None)

        evaluation = evaluate_ml_score()

        self.assertFalse(evaluation.is_measured)
        self.assertIn('nothing to compare', evaluation.notes)

    def test_it_measures_the_mean_absolute_difference(self):
        self._profile('pair-a', 70.0, 72.0)
        self._profile('pair-b', 60.0, 56.0)

        measurement = evaluate_ml_score().get(PREDICTION_ERROR)

        self.assertTrue(measurement.measured)
        self.assertAlmostEqual(measurement.value or 0, 3.0, places=6)

    def test_it_reports_the_sample_size(self):
        """A metric over two examples is not the claim a metric over two
        thousand would be."""
        self._profile('n-a', 70.0, 71.0)
        self._profile('n-b', 60.0, 61.0)

        self.assertEqual(evaluate_ml_score().get(PREDICTION_ERROR).sample_size, 2)

    def test_it_states_that_this_is_not_accuracy(self):
        self._profile('limits', 70.0, 71.0)

        self.assertIn('NOT accuracy against ground truth',
                      evaluate_ml_score().notes)

    def test_a_company_with_only_one_of_the_two_is_excluded(self):
        self._profile('both', 70.0, 71.0)
        self._profile('only-composite', 50.0, None)

        self.assertEqual(evaluate_ml_score().get(PREDICTION_ERROR).sample_size, 1)


class TheCommand(TestCase):

    def test_it_runs_and_reports_the_unmeasured_count(self):
        from io import StringIO

        from django.core.management import call_command

        out = StringIO()
        call_command('evaluate_modules', stdout=out)
        output = out.getvalue()

        self.assertIn(NOT_MEASURED, output)
        self.assertIn('never rendered as 0%', output)

    def test_it_offers_no_flag_to_fake_a_measurement(self):
        import inspect

        from platform_registry.management.commands import evaluate_modules

        source = inspect.getsource(evaluate_modules)

        self.assertNotIn('add_argument', source)
