"""Safe, versioned EcoIQ KPI formula language — never eval/exec arbitrary code.

A standalone deterministic draft registry for the 20 initial Business Plan 2.0
KPI *candidates*. No published benchmark or audited KPI can be inferred.
AI-generated expressions use exactly the same bounded AST evaluator.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
import re
from typing import Any, Mapping

from ecoiq_os.foundation_catalog import INITIAL_KPI_KEYS, KPI_CATALOG

MAX_EXPRESSION_CHARS = 180
MAX_AST_NODES = 35
MAX_EXPRESSION_DEPTH = 8
MAX_VARIABLES = 12
MAX_ABS_VALUE = Decimal("1e24")
MAX_OUTPUT = Decimal("1e30")
SAFE_UNIT_SYMBOLS = frozenset({
    "GBP", "kg", "kWh", "m3", "unit", "hour", "person", "incident",
    "tCO2e", "count", "1",
})
UNIT_LABEL = re.compile(r"^[A-Za-z0-9]+(?:/[A-Za-z0-9]+)?$")


class FormulaRejected(ValueError):
    """A malformed/unsupported formula, no raw customer input in message."""


def _dimensions(unit: str) -> dict[str, int]:
    if not isinstance(unit, str) or not UNIT_LABEL.fullmatch(unit):
        raise FormulaRejected("Invalid or unsupported unit notation.")
    items = unit.split("/")
    if any(part not in SAFE_UNIT_SYMBOLS for part in items):
        raise FormulaRejected("Unsupported unit; an expert must define units first.")
    if len(items) > 2:
        raise FormulaRejected("Compound unit exceeds supported notation.")
    dimensions: dict[str, int] = {}
    for i, part in enumerate(items):
        if part == "1":
            continue
        dimensions[part] = dimensions.get(part, 0) + (1 if i == 0 else -1)
    return {key: value for key, value in dimensions.items() if value}


def _combine(left: dict[str, int], right: dict[str, int], sign: int) -> dict[str, int]:
    out = left.copy()
    for key, power in right.items():
        out[key] = out.get(key, 0) + sign * power
    return {key: power for key, power in out.items() if power}


@dataclass(frozen=True)
class InputSpec:
    key: str
    unit: str
    description: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,49}", self.key):
            raise FormulaRejected("Invalid input key.")
        _dimensions(self.unit)
        if not self.description or len(self.description) > 180:
            raise FormulaRejected("Invalid input description.")


@dataclass(frozen=True)
class FormulaSpec:
    key: str
    title: str
    expression: str
    output_unit: str
    inputs: tuple[InputSpec, ...]
    interpretation_limit: str
    validation_status: str = "PROVISIONAL_FORMULA_REQUIRES_DOMAIN_REVIEW"

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,49}", self.key):
            raise FormulaRejected("Invalid formula key.")
        if not self.title or not self.interpretation_limit:
            raise FormulaRejected("Formula metadata incomplete.")
        if not isinstance(self.inputs, tuple) or not 1 <= len(self.inputs) <= MAX_VARIABLES:
            raise FormulaRejected("Formula must declare 1–12 inputs.")
        if len({x.key for x in self.inputs}) != len(self.inputs):
            raise FormulaRejected("Duplicate input variable.")
        _dimensions(self.output_unit)
        validate_formula_expression(
            self.expression, {x.key: x.unit for x in self.inputs},
            self.output_unit,
        )


@dataclass(frozen=True)
class Observation:
    value: str | int | Decimal | None
    unit: str
    period: str
    source_ref: str

    def __post_init__(self) -> None:
        _dimensions(self.unit)
        if not isinstance(self.period, str) or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", self.period):
            raise FormulaRejected("Period must be YYYY-MM.")
        if not isinstance(self.source_ref, str) or not 1 <= len(self.source_ref.strip()) <= 120:
            raise FormulaRejected("Each observation requires its source identifier.")
        if self.value is not None:
            _decimal(self.value)


def _decimal(value: Any) -> Decimal:
    if type(value) not in (str, int, Decimal):
        raise FormulaRejected("Use finite decimal strings or integers, not floats/booleans.")
    try:
        d = Decimal(value)
    except (ValueError, InvalidOperation):
        raise FormulaRejected("Invalid decimal input.") from None
    if not d.is_finite() or d < 0 or d > MAX_ABS_VALUE:
        raise FormulaRejected("Input must be a bounded finite non-negative quantity.")
    return d


def _parse_expression(expression: str, variables: Mapping[str, str],
                      output_unit: str) -> ast.Expression:
    if not isinstance(expression, str) or not 1 <= len(expression) <= MAX_EXPRESSION_CHARS:
        raise FormulaRejected("Expression too long or empty.")
    if not isinstance(variables, Mapping) or not 1 <= len(variables) <= MAX_VARIABLES:
        raise FormulaRejected("Invalid variable declaration.")
    try:
        root = ast.parse(expression, mode="eval")
    except (SyntaxError, ValueError, RecursionError):
        raise FormulaRejected("Invalid arithmetic expression.") from None
    if len(tuple(ast.walk(root))) > MAX_AST_NODES:
        raise FormulaRejected("Expression complexity exceeds bound.")

    def dimension(node: ast.AST, depth: int) -> dict[str, int]:
        if depth > MAX_EXPRESSION_DEPTH:
            raise FormulaRejected("Expression too deeply nested.")
        if isinstance(node, ast.Expression):
            return dimension(node.body, depth + 1)
        if isinstance(node, ast.Name):
            if node.id not in variables:
                raise FormulaRejected("Unknown variable in expression.")
            return _dimensions(variables[node.id])
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            if not isinstance(node.value, int):  # Never approximate literals.
                raise FormulaRejected("Use integer constants only.")
            if node.value < 0 or node.value > 1_000_000:
                raise FormulaRejected("Constant exceeds supported bound.")
            return {}
        if isinstance(node, ast.BinOp):
            left = dimension(node.left, depth + 1)
            right = dimension(node.right, depth + 1)
            if isinstance(node.op, (ast.Add, ast.Sub)):
                if left != right:
                    raise FormulaRejected("Addition/subtraction requires compatible units.")
                return left
            if isinstance(node.op, ast.Mult):
                return _combine(left, right, 1)
            if isinstance(node.op, ast.Div):
                return _combine(left, right, -1)
        raise FormulaRejected("Only +, -, *, /, integer constants and named variables are allowed.")

    computed = dimension(root, 0)
    if computed != _dimensions(output_unit):
        raise FormulaRejected("Output unit incompatible with expression dimensions.")
    return root


def validate_formula_expression(expression: str, variables: Mapping[str, str],
                                output_unit: str) -> None:
    """Compile-time syntax/dimension checks only, not economic semantics."""
    _parse_expression(expression, variables, output_unit)


def calculate_formula(spec: FormulaSpec, observations: Mapping[str, Observation]) -> dict[str, object]:
    """Evaluate a safe expression using Decimal; never substitute missing as 0."""
    if not isinstance(spec, FormulaSpec) or not isinstance(observations, Mapping):
        raise FormulaRejected("Invalid formula inputs.")
    expected = {item.key: item.unit for item in spec.inputs}
    if set(observations) != set(expected):
        raise FormulaRejected("Exactly the declared measurements are required.")
    periods: set[str] = set()
    values: dict[str, Decimal] = {}
    refs: list[str] = []
    for key, unit in expected.items():
        item = observations[key]
        if not isinstance(item, Observation) or item.unit != unit:
            raise FormulaRejected("Measurement unit does not match formula definition.")
        periods.add(item.period)
        refs.append(item.source_ref)
        if item.value is not None:
            values[key] = _decimal(item.value)
    if len(periods) != 1:
        raise FormulaRejected("All inputs must use the same reporting period.")
    if len(values) != len(expected):
        return _response(spec, None, "INSUFFICIENT_DATA", refs, periods.pop())

    root = _parse_expression(spec.expression, expected, spec.output_unit)

    def evaluate(node: ast.AST) -> Decimal:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Name):
            return values[node.id]
        if isinstance(node, ast.Constant):
            return Decimal(node.value)
        if isinstance(node, ast.BinOp):
            left, right = evaluate(node.left), evaluate(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                if right == 0:
                    raise ZeroDivisionError
                return left / right
        raise FormulaRejected("Unsupported compiled operation.")

    with localcontext() as ctx:
        ctx.prec = 28
        try:
            result = evaluate(root)
        except (ZeroDivisionError, InvalidOperation, OverflowError):
            return _response(spec, None, "UNDEFINED_DENOMINATOR_OR_RESULT", refs, periods.pop())
    if not result.is_finite() or abs(result) > MAX_OUTPUT:
        raise FormulaRejected("Result not a bounded finite number.")
    # Over-100% claims for subset ratios are not silently accepted. The
    # caller and reviewer must verify denominator scope / units.
    if spec.output_unit == "1" and result > 100 and "*" in spec.expression:
        return _response(spec, None, "REVIEW_UNPLAUSIBLE_RATIO", refs, periods.pop())
    return _response(spec, result, "REPORTED_NOT_VERIFIED", refs, periods.pop())


def _response(spec: FormulaSpec, result: Decimal | None, status: str,
              refs: list[str], period: str) -> dict[str, object]:
    return {
        "formula_key": spec.key,
        "formula_version": "candidate_formula_registry_v1",
        "expression": spec.expression,
        "value_decimal": str(result) if result is not None else None,
        "unit": spec.output_unit,
        "period": period,
        "status": status,
        "source_identifiers": list(dict.fromkeys(refs)),
        "review_status": spec.validation_status,
        "interpretation_limit": spec.interpretation_limit,
        "verified_evidence": False,
        "independently_verified": False,
        "approved_for_implementation": False,
        "shariah_verdict": None,
    }


def _spec(key: str, expression: str, unit: str, variables: tuple[tuple[str, str], ...],
          note: str) -> FormulaSpec:
    title = next(item.title for item in KPI_CATALOG if item.key == key)
    inputs = tuple(InputSpec(name, symbol, f"Documented {name.replace('_', ' ')}") for name, symbol in variables)
    return FormulaSpec(key, title, expression, unit, inputs, note)


PROVISIONAL_KPI_FORMULAS = (
    _spec("revenue", "reported_revenue", "GBP", (("reported_revenue", "GBP"),),
          "Use a specified accounting standard, currency, period and legal entity; reported revenue is not audited."),
    _spec("gross_margin", "(revenue - cost_of_goods_sold) / revenue * 100", "1",
          (("revenue", "GBP"), ("cost_of_goods_sold", "GBP")),
          "Requires consistent COGS policy and revenue exclusions; negative gross margin is possible."),
    _spec("operating_cash_flow", "operating_cash_inflows - operating_cash_outflows", "GBP",
          (("operating_cash_inflows", "GBP"), ("operating_cash_outflows", "GBP")),
          "Simplified cash-basis proposal; confirm cash-flow classification before professional use."),
    _spec("liquidity_ratio", "current_assets / current_liabilities", "1",
          (("current_assets", "GBP"), ("current_liabilities", "GBP")),
          "Current ratio, not cash coverage or a guarantee of liquidity."),
    _spec("material_loss_rate", "recorded_material_loss / material_input * 100", "1",
          (("recorded_material_loss", "kg"), ("material_input", "kg")),
          "Recorded material loss may include necessary process yield; cannot infer avoidable waste."),
    _spec("energy_intensity", "total_energy / produced_units", "kWh/unit",
          (("total_energy", "kWh"), ("produced_units", "unit")),
          "Requires consistent functional unit and organisational boundary."),
    _spec("water_intensity", "water_withdrawal / produced_units", "m3/unit",
          (("water_withdrawal", "m3"), ("produced_units", "unit")),
          "Withdrawal differs from consumption and discharge; define water accounting boundary."),
    _spec("asset_utilisation", "productive_asset_hours / available_asset_hours * 100", "1",
          (("productive_asset_hours", "hour"), ("available_asset_hours", "hour")),
          "Define available hours, downtime and overlapping shifts; >100% requires review."),
    _spec("ghg_intensity", "reported_emissions / produced_units", "tCO2e/unit",
          (("reported_emissions", "tCO2e"), ("produced_units", "unit")),
          "No scope 1/2/3, emission factors or GHG verification are assumed."),
    _spec("waste_recovery", "recovered_waste / total_generated_waste * 100", "1",
          (("recovered_waste", "kg"), ("total_generated_waste", "kg")),
          "Recovery may include recycling, reuse or other pathways; define boundary."),
    _spec("freshwater_stress", "site_freshwater_withdrawal / local_available_freshwater * 100", "1",
          (("site_freshwater_withdrawal", "m3"), ("local_available_freshwater", "m3")),
          "This is a proposed local withdrawal pressure ratio, NOT a recognised basin stress metric; hydrologist review required."),
    _spec("worker_incident_rate", "recordable_incidents / worked_hours * 1000000", "incident/hour",
          (("recordable_incidents", "incident"), ("worked_hours", "hour")),
          "Incidents per 1m worked hours; reporting rules and incident definitions require validation."),
    _spec("training_hours", "total_training_hours / eligible_workers", "hour/person",
          (("total_training_hours", "hour"), ("eligible_workers", "person")),
          "Eligible workforce and course inclusion must be consistently defined."),
    _spec("living_wage_coverage", "eligible_workers_at_or_above_local_benchmark / assessed_workers * 100", "1",
          (("eligible_workers_at_or_above_local_benchmark", "person"), ("assessed_workers", "person")),
          "Requires jurisdiction-specific, documented living wage and worker eligibility."),
    _spec("adjusted_pay_gap", "(adjusted_reference_pay - adjusted_comparison_pay) / adjusted_reference_pay * 100", "1",
          (("adjusted_reference_pay", "GBP"), ("adjusted_comparison_pay", "GBP")),
          "Only valid if pay is independently adjusted for defensible comparable roles; does not itself prove discrimination."),
    _spec("fair_procurement", "audited_procedures_meeting_criteria / assessed_procurements * 100", "1",
          (("audited_procedures_meeting_criteria", "count"), ("assessed_procurements", "count")),
          "Process-criteria coverage; cannot establish actual legal fairness or absence of bias."),
    _spec("benefit_distribution", "documented_group_benefit / total_documented_benefit * 100", "1",
          (("documented_group_benefit", "GBP"), ("total_documented_benefit", "GBP")),
          "A specific, consented beneficiary group must be defined; share is not a fairness verdict."),
    _spec("evidence_coverage", "kpi_with_traceable_sources / eligible_kpi * 100", "1",
          (("kpi_with_traceable_sources", "count"), ("eligible_kpi", "count")),
          "Traceable identifiers do not prove authenticity or correctness."),
    _spec("independent_verification", "independently_reviewed_kpi / eligible_kpi * 100", "1",
          (("independently_reviewed_kpi", "count"), ("eligible_kpi", "count")),
          "Verify reviewer independence, credentials and bound source version first."),
    _spec("decision_review_coverage", "independently_reviewed_decisions / consequential_decisions * 100", "1",
          (("independently_reviewed_decisions", "count"), ("consequential_decisions", "count")),
          "Human review is not the same as adequate rationale or authorised implementation."),
)
FORMULAS_BY_KEY = {item.key: item for item in PROVISIONAL_KPI_FORMULAS}
if len(FORMULAS_BY_KEY) != 20 or set(FORMULAS_BY_KEY) != set(INITIAL_KPI_KEYS):
    raise AssertionError("Exactly the same 20 selected foundation KPI keys need formula definitions.")


def formula_catalogue_view() -> list[dict[str, object]]:
    """Public-to-developers metadata, NOT confidential source values."""
    return [{
        "key": f.key, "title": f.title, "expression": f.expression,
        "output_unit": f.output_unit, "required_inputs": [
            {"key": inp.key, "unit": inp.unit} for inp in f.inputs
        ],
        "validation_status": f.validation_status,
        "interpretation_limit": f.interpretation_limit,
        "production_approved": False,
    } for f in PROVISIONAL_KPI_FORMULAS]
