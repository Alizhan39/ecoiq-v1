"""Formula Registry safety, arithmetic correctness, dimensionality, provenance."""
from __future__ import annotations

import unittest
from decimal import Decimal

from ecoiq_os.foundation_catalog import INITIAL_KPI_KEYS
from ecoiq_os.formula_designer import EXTRA_SITUATION_FORMULAS, suggest_offline_formula
from ecoiq_os.formula_registry import (
    FORMULAS_BY_KEY, FormulaRejected, FormulaSpec, InputSpec, Observation,
    PROVISIONAL_KPI_FORMULAS, calculate_formula, formula_catalogue_view,
    validate_formula_expression,
)


def observations(spec, data: dict[str, str | None]):
    return {
        item.key: Observation(
            value=data.get(item.key), unit=item.unit, period="2026-10",
            source_ref=f"synthetic:{item.key}",
        )
        for item in spec.inputs
    }


class FormulaRegistryTests(unittest.TestCase):
    def test_exact_20_priority_keys_have_explicit_contracts(self):
        self.assertEqual(len(PROVISIONAL_KPI_FORMULAS), 20)
        self.assertEqual(set(FORMULAS_BY_KEY), set(INITIAL_KPI_KEYS))
        self.assertTrue(all(x.validation_status.startswith("PROVISIONAL_")
                            for x in PROVISIONAL_KPI_FORMULAS))
        self.assertTrue(all(not item["production_approved"] for item in formula_catalogue_view()))
        self.assertEqual(len(formula_catalogue_view()), 20)

    def test_every_initial_formula_evaluates_from_declared_synthetic_inputs(self):
        for spec in PROVISIONAL_KPI_FORMULAS:
            with self.subTest(kpi=spec.key):
                samples = {input_spec.key: "10" for input_spec in spec.inputs}
                out = calculate_formula(spec, observations(spec, samples))
                self.assertEqual(out["formula_key"], spec.key)
                self.assertIn(out["status"], ("REPORTED_NOT_VERIFIED", "REVIEW_UNPLAUSIBLE_RATIO"))
                self.assertFalse(out["approved_for_implementation"])
                self.assertFalse(out["verified_evidence"])

    def test_gross_margin_and_cash_flow_with_exact_decimal(self):
        margin = FORMULAS_BY_KEY["gross_margin"]
        result = calculate_formula(margin, observations(
            margin, {"revenue": "1000.00", "cost_of_goods_sold": "650.00"},
        ))
        self.assertEqual(Decimal(result["value_decimal"]), Decimal("35"))
        self.assertEqual(result["status"], "REPORTED_NOT_VERIFIED")
        self.assertFalse(result["approved_for_implementation"])
        self.assertFalse(result["independently_verified"])
        cash = FORMULAS_BY_KEY["operating_cash_flow"]
        out = calculate_formula(cash, observations(
            cash, {"operating_cash_inflows": "1000.75",
                   "operating_cash_outflows": "1300.25"},
        ))
        self.assertEqual(Decimal(out["value_decimal"]), Decimal("-299.50"))

    def test_zero_denominator_unknown_and_zero_numerator_are_distinct(self):
        spec = FORMULAS_BY_KEY["material_loss_rate"]
        for values, expected_status, expected in (
            ({"recorded_material_loss": "0", "material_input": "1000"}, "REPORTED_NOT_VERIFIED", Decimal("0")),
            ({"recorded_material_loss": None, "material_input": "1000"}, "INSUFFICIENT_DATA", None),
            ({"recorded_material_loss": "0", "material_input": "0"}, "UNDEFINED_DENOMINATOR_OR_RESULT", None),
        ):
            with self.subTest(values=values):
                out = calculate_formula(spec, observations(spec, values))
                self.assertEqual(out["status"], expected_status)
                self.assertEqual(
                    Decimal(out["value_decimal"]) if out["value_decimal"] is not None else None,
                    expected,
                )

    def test_reject_input_float_boolean_infinite_negative_and_huge(self):
        for bad in (float("nan"), float("inf"), float("-inf"), 1.0, True,
                    "NaN", "-1", "Infinity", "1e100"):
            with self.subTest(bad=bad), self.assertRaises(FormulaRejected):
                Observation(bad, "kg", "2026-10", "synthetic")

    def test_incompatible_units_periods_and_extra_fields_rejected(self):
        spec = FORMULAS_BY_KEY["energy_intensity"]
        values = observations(spec, {"total_energy": "150", "produced_units": "20"})
        values["total_energy"] = Observation("150", "kg", "2026-10", "S1")
        with self.assertRaises(FormulaRejected):
            calculate_formula(spec, values)
        values = observations(spec, {"total_energy": "150", "produced_units": "20"})
        values["total_energy"] = Observation("150", "kWh", "2026-09", "S1")
        with self.assertRaises(FormulaRejected):
            calculate_formula(spec, values)
        values = observations(spec, {"total_energy": "150", "produced_units": "20"})
        values["foreign_variable"] = Observation("1", "kg", "2026-10", "S3")
        with self.assertRaises(FormulaRejected):
            calculate_formula(spec, values)

    def test_reject_malformed_or_executable_formula_expressions(self):
        variables = {"a": "kg", "b": "kg"}
        for expression in (
            "__import__('os').system('whoami')", "a.__class__",
            "[a for a in [1]]", "a ** 8", "a // b",
            "a if b else b", "a[0]", "(lambda: 1)()",
            "a / missing", "a + (b / a)",
            "2.0 * a", "a + (-1)", "a + 1e3",
            "a / b + a", "a ** (100000000)",
        ):
            with self.subTest(expr=expression), self.assertRaises(FormulaRejected):
                validate_formula_expression(expression, variables, "kg")
        with self.assertRaises(FormulaRejected):
            validate_formula_expression("a / b", variables, "kg")
        with self.assertRaises(FormulaRejected):
            validate_formula_expression("a + b", variables, "1")

    def test_formula_complexity_and_fractional_rates(self):
        with self.assertRaises(FormulaRejected):
            validate_formula_expression("a + " * 100 + "b", {"a": "kg", "b": "kg"}, "kg")
        incident = FORMULAS_BY_KEY["worker_incident_rate"]
        value = calculate_formula(incident, observations(incident, {
            "recordable_incidents": "3", "worked_hours": "1000000",
        }))
        self.assertEqual(Decimal(value["value_decimal"]), Decimal("3"))
        self.assertEqual(value["unit"], "incident/hour")
        self.assertFalse(value["verified_evidence"])

    def test_implausible_coverage_does_not_silently_pass(self):
        spec = FORMULAS_BY_KEY["living_wage_coverage"]
        result = calculate_formula(spec, observations(spec, {
            "eligible_workers_at_or_above_local_benchmark": "20",
            "assessed_workers": "10",
        }))
        self.assertIsNone(result["value_decimal"])
        self.assertEqual(result["status"], "REVIEW_UNPLAUSIBLE_RATIO")

    def test_unbounded_variance_and_pressure_are_not_falsely_clamped(self):
        variance = EXTRA_SITUATION_FORMULAS["project_schedule_variance"]
        result = calculate_formula(variance, observations(variance, {
            "actual_project_hours": "350", "baseline_planned_hours": "100",
        }))
        self.assertEqual(result["value_decimal"], "250")
        self.assertEqual(result["status"], "REPORTED_NOT_VERIFIED")
        pressure = FORMULAS_BY_KEY["freshwater_stress"]
        high = calculate_formula(pressure, observations(pressure, {
            "site_freshwater_withdrawal": "200",
            "local_available_freshwater": "100",
        }))
        self.assertEqual(high["value_decimal"], "200")
        self.assertEqual(high["status"], "REPORTED_NOT_VERIFIED")

    def test_additional_scenarios_are_separately_reviewed(self):
        self.assertGreaterEqual(len(EXTRA_SITUATION_FORMULAS), 6)
        row = suggest_offline_formula("equipment_downtime")
        self.assertEqual(row["candidate"]["expression"],
                         "downtime_hours / scheduled_hours * 100")
        self.assertFalse(row["model_called"])
        self.assertFalse(row["candidate"]["approved_for_production"])
        self.assertEqual(suggest_offline_formula("never_defined")["status"],
                         "NO_PREDEFINED_FORMULA")


if __name__ == "__main__":
    unittest.main()
