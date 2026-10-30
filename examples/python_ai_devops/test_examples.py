"""Fast contract tests. PyTorch learning tests skip when torch is absent."""
import asyncio
import importlib.util
import unittest

from examples.python_ai_devops.process_pipeline import (
    analyse_synthetic_case, describe_synthetic_series, synthetic_csv,
)
from examples.python_ai_devops.syntax_gallery import (
    Observation, assignment_examples, async_label, classify_state,
    known_values, operator_examples, signatures, square, variadic,
)
from examples.python_ai_devops.torch_lab import (
    train_tiny_character_generator, train_tiny_regression,
)


class PythonContractsTests(unittest.TestCase):
    def test_signatures(self):
        example = signatures("EX-1", 10, unit="kg", team="demo")
        self.assertEqual(example["metadata"], {"team": "demo"})
        self.assertEqual(example["quantity"], 10)
        with self.assertRaises(TypeError):
            signatures(case_id="EX-1")
        self.assertEqual(variadic(1, 2, 3, scale=2), (2, 4, 6))

    def test_all_operator_families(self):
        self.assertEqual(assignment_examples()["final"], 0)
        values = operator_examples()
        self.assertEqual(values["arithmetic"]["floor"], 2)
        self.assertEqual(values["bitwise"]["and"], 3)
        self.assertEqual(values["bitwise"]["xor"], 4)
        self.assertTrue(values["comparison"]["chained"])
        self.assertTrue(values["identity"]["is"])
        self.assertTrue(values["membership"]["in"])
        self.assertFalse(values["logic"]["and"])

    def test_patterns_generator_and_coroutine(self):
        self.assertEqual(classify_state(None), "UNKNOWN")
        self.assertEqual(classify_state(0), "MEASURED_ZERO")
        self.assertEqual(classify_state(4), "POSITIVE")
        self.assertEqual(classify_state(-3), "NEGATIVE")
        self.assertEqual(list(known_values([
            Observation("a", None), Observation("b", 0),
        ])), [0])
        self.assertEqual(square(3), 9)
        self.assertEqual(asyncio.run(async_label("demo")), "case:demo")

    def test_existing_ecoiq_process_kernel_with_fake_input(self):
        result = analyse_synthetic_case()
        self.assertEqual(result["recorded_loss_percent"], 12)
        self.assertEqual(result["next_stage"], "COLLECT_EVIDENCE")
        self.assertEqual(result["hypotheses"], 3)
        self.assertFalse(result["implementation_permitted"])
        self.assertFalse(result["ai_model_called"])
        self.assertEqual(result["source_authentication"], "NOT_VERIFIED")
        missing = analyse_synthetic_case(loss_quantity=None)
        self.assertIsNone(missing["recorded_loss_percent"])
        self.assertEqual(missing["hypotheses"], 0)
        self.assertEqual(analyse_synthetic_case(loss_quantity=0)["recorded_loss_percent"], 0)

    def test_unknown_totals_and_invalid_data(self):
        result = describe_synthetic_series([10, None, 5])
        self.assertIsNone(result["total"])
        self.assertIsNone(result["mean"])
        self.assertEqual(result["missing"], 1)
        valid = describe_synthetic_series([10, 0, 5])
        self.assertEqual(valid["total"], 15)
        self.assertEqual(valid["median"], 5)
        with self.assertRaises(ValueError):
            describe_synthetic_series([1, float("nan")])
        with self.assertRaises(ValueError):
            synthetic_csv(loss_quantity=-1)


@unittest.skipUnless(importlib.util.find_spec("torch") is not None,
                     "Optional PyTorch not installed in standard web runtime")
class OptionalNeuralTests(unittest.TestCase):
    def test_mlp_trains_on_synthetic_data(self):
        result = train_tiny_regression(steps=75)
        self.assertLess(result["final_training_mse"],
                        result["initial_training_mse"])

    def test_generation_is_offline_and_not_approved(self):
        result = train_tiny_character_generator(steps=8, max_new_tokens=4)
        self.assertEqual(len(result["generated_sample"]), 5)
        self.assertTrue(result["trained_only_on_synthetic_data"])
        self.assertFalse(result["uses_external_api"])
        self.assertFalse(result["approved_for_customer_decisions"])


if __name__ == "__main__":
    unittest.main()
