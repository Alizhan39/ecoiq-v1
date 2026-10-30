"""Synthetic analytics composed with EcoIQ's EXISTING process engine.

No new CSV parser, KPI system, causal classifier or model router. This is
offline educational code, never a real business finding or approved decision.
"""
from __future__ import annotations

from math import isfinite
from statistics import mean, median

from ecoiq_os.decision_islah import build_preliminary_brief
from ecoiq_os.process_csv import diagnose_csv

HEADER = (
    "record_id,case_id,domain,process_name,resource_type,period,"
    "unit,flow_type,quantity,evidence_ref\n"
)


def synthetic_csv(*, input_quantity: int | None = 1000,
                  loss_quantity: int | None = 120) -> str:
    """Build fictional observations with fake source identifiers."""
    def field(value: int | None) -> str:
        if value is None:
            return ""
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError("Synthetic quantities must be nonnegative integers or None")
        return str(value)

    return HEADER + (
        "I-1,EXAMPLE-001,construction,Concrete delivery,material,2026-10,kg,"
        f"input,{field(input_quantity)},FAKE-IN-1\n"
        "L-1,EXAMPLE-001,construction,Concrete delivery,material,2026-10,kg,"
        f"loss,{field(loss_quantity)},FAKE-LOSS-1\n"
    )


def analyse_synthetic_case(*, input_quantity: int | None = 1000,
                           loss_quantity: int | None = 120) -> dict[str, object]:
    """Synthetic CSV -> reported KPI -> falsifiable questions."""
    report = diagnose_csv(synthetic_csv(
        input_quantity=input_quantity, loss_quantity=loss_quantity,
    ))
    kpi = report["kpi"]
    brief = build_preliminary_brief(
        case_id=report["case_id"], domain=report["domain"],
        process_name=report["process_name"], resource_type="material",
        period=kpi["period"], unit=kpi["source_unit"],
        reported_input=kpi["denominator"], reported_loss=kpi["numerator"],
    )
    return {
        "recorded_loss_percent": kpi["value"],
        "kpi_status": kpi["status"],
        "next_stage": report["next_step"]["next_stage"],
        "hypotheses": len(brief["hypotheses"]),
        "source_authentication": "NOT_VERIFIED",
        "implementation_permitted": brief["implementation_permitted"],
        "ai_model_called": brief["ai_model_called"],
    }


def describe_synthetic_series(values: list[float | None]) -> dict[str, object]:
    """Descriptive stats only with complete, finite, nonnegative input.

    A partially missing series cannot be silently summed into a false total.
    This illustrates the same boundary as the real EcoIQ parser, not a
    replacement for that parser.
    """
    if not values:
        return {"count": 0, "missing": 0, "total": None,
                "mean": None, "median": None, "complete": False}
    for value in values:
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, (int, float))
            or not isfinite(value) or value < 0
        ):
            raise ValueError("Values must be finite nonnegative numbers or None")
    known = [float(value) for value in values if value is not None]
    complete = len(known) == len(values)
    return {
        "count": len(values), "missing": len(values) - len(known),
        "total": sum(known) if complete else None,
        "mean": mean(known) if complete else None,
        "median": median(known) if complete else None,
        "complete": complete,
    }
