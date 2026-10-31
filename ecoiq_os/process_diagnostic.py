"""Read-only, evidence-aware process diagnostic for the EcoIQ OS kernel.

This adapter calculates an *observed* loss ratio from like-for-like quantities
and sends the process flow to the existing deterministic OS gate. It does not
declare a loss avoidable, assess religious compliance, validate uploaded
references, infer causality, or authorise an intervention.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Any

from ecoiq_os.domains import get_domain
from ecoiq_os.evidence import UNTESTED
from ecoiq_os.flow import RESOURCE_TYPES, FlowEdge, FlowNode, UniversalFlowGraph
from ecoiq_os.kernel import EcoIQOSCase, EcoIQOSDecision, evaluate_case
from mizan.system_balance import (
    INSUFFICIENT_DATA,
    BalanceDimension,
    MizanSystemAssessment,
    assess_balance,
)


@dataclass(frozen=True)
class ProcessMeasurement:
    """One reported non-negative quantity, with a traceable source reference."""

    value: float | None
    unit: str
    period: str
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.unit, str) or not self.unit.strip():
            raise ValueError("Measurement unit is required.")
        if not isinstance(self.period, str) or not self.period.strip():
            raise ValueError("Measurement period is required.")
        if not isinstance(self.evidence_refs, tuple) or any(
            not isinstance(ref, str) or not ref.strip() for ref in self.evidence_refs
        ):
            raise ValueError("Evidence refs must be a tuple of non-empty strings.")
        if self.value is None:
            return
        if (
            isinstance(self.value, bool)
            or not isinstance(self.value, (int, float))
            or not isfinite(self.value)
            or self.value < 0
        ):
            raise ValueError("Known measurements must be finite non-negative numbers.")
        if not self.evidence_refs:
            raise ValueError("Known measurements require evidence references.")


@dataclass(frozen=True)
class ProcessSnapshot:
    """Two comparable observations for one process and measurement period.

    The reported loss must be a subset of the reported input, not an
    independently measured resource with a different accounting boundary.
    """

    case_id: str
    domain: str
    process_name: str
    resource_type: str
    input_measurement: ProcessMeasurement
    loss_measurement: ProcessMeasurement

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, str) or not self.case_id.strip():
            raise ValueError("Process case id is required.")
        if not isinstance(self.process_name, str) or not self.process_name.strip():
            raise ValueError("Process name is required.")
        get_domain(self.domain)
        if self.resource_type not in RESOURCE_TYPES:
            raise ValueError(f"Unknown resource type: {self.resource_type}")
        if not isinstance(self.input_measurement, ProcessMeasurement) or not isinstance(
            self.loss_measurement, ProcessMeasurement
        ):
            raise ValueError("Both observations must be ProcessMeasurement records.")
        if (
            self.input_measurement.unit != self.loss_measurement.unit
            or self.input_measurement.period != self.loss_measurement.period
        ):
            raise ValueError("Input and loss must share exactly the same unit and period.")
        total, loss = self.input_measurement.value, self.loss_measurement.value
        if total is not None and loss is not None and loss > total:
            raise ValueError("Recorded loss cannot exceed its input in this process boundary.")


@dataclass(frozen=True)
class ProcessDiagnostic:
    snapshot: ProcessSnapshot
    flow_graph: UniversalFlowGraph
    decision: EcoIQOSDecision
    loss_rate_percent: float | None

    def to_dict(self) -> dict[str, Any]:
        total = self.snapshot.input_measurement
        loss = self.snapshot.loss_measurement
        evidence_refs = tuple(dict.fromkeys(total.evidence_refs + loss.evidence_refs))
        return {
            "case_id": self.snapshot.case_id,
            "domain": self.snapshot.domain,
            "process_name": self.snapshot.process_name,
            "read_only": True,
            "kpi": {
                "key": "recorded_loss_rate",
                "formula": "reported_loss / reported_input * 100",
                "value": self.loss_rate_percent,
                "unit": "%",
                "status": (
                    "CALCULATED_FROM_REPORTED_INPUTS"
                    if self.loss_rate_percent is not None else "INSUFFICIENT_DATA"
                ),
                "numerator": loss.value,
                "denominator": total.value,
                "source_unit": total.unit,
                "period": total.period,
                "evidence_refs": list(evidence_refs),
                "independently_verified": False,
            },
            "flow_graph": self.flow_graph.to_dict(),
            "next_step": asdict(self.decision),
            "investigation_question": (
                "Is any of the reported loss avoidable without transferring harm?"
                if self.loss_rate_percent is not None and self.loss_rate_percent > 0
                else None
            ),
            "limitations": [
                "References are reported identifiers, not verified source records.",
                "Observed loss is not evidence of avoidable waste or a causal mechanism.",
                "No religious ruling, organisational score or change approval is produced.",
            ],
        }


def diagnose_process(
    snapshot: ProcessSnapshot,
    *,
    mizan: MizanSystemAssessment | None = None,
    hypothesis_status: str = UNTESTED,
) -> ProcessDiagnostic:
    """Analyse without guessing missing values or bypassing the OS gate.

    mizan and hypothesis_status are trusted *internal* inputs, not fields for
    an untrusted HTTP request. A reviewed assessment must be obtained through
    a separately permission-checked provenance workflow. When none is provided,
    the Mizan assessment is explicitly unknown and the OS collects evidence.
    """
    if not isinstance(snapshot, ProcessSnapshot):
        raise TypeError("snapshot must be a ProcessSnapshot.")
    total = snapshot.input_measurement
    loss = snapshot.loss_measurement
    graph = UniversalFlowGraph(
        nodes=(
            FlowNode("source", "Recorded input", "source"),
            FlowNode("process", snapshot.process_name, "process"),
            FlowNode("loss_sink", "Recorded loss", "sink"),
        ),
        edges=(
            FlowEdge(
                "input", "source", "process", snapshot.resource_type,
                value=total.value, unit=total.unit, period=total.period,
                evidence_refs=total.evidence_refs,
            ),
            FlowEdge(
                "reported_loss", "process", "loss_sink", snapshot.resource_type,
                value=loss.value, unit=loss.unit, period=loss.period,
                evidence_refs=loss.evidence_refs, is_loss=True,
            ),
        ),
    )
    if mizan is None:
        mizan = assess_balance(
            scope_level="process",
            dimensions=(
                BalanceDimension("resource_efficiency", INSUFFICIENT_DATA),
                BalanceDimension("worker", INSUFFICIENT_DATA),
                BalanceDimension("environment", INSUFFICIENT_DATA),
            ),
        )

    decision = evaluate_case(EcoIQOSCase(
        case_id=snapshot.case_id,
        domain=snapshot.domain,
        objective=f"Investigate reported {snapshot.resource_type} loss in {snapshot.process_name}.",
        flow_graph=graph,
        mizan=mizan,
        hypothesis_status=hypothesis_status,
    ))
    loss_rate = None
    if total.value is not None and loss.value is not None and total.value > 0:
        loss_rate = round((loss.value / total.value) * 100, 4)

    return ProcessDiagnostic(
        snapshot=snapshot,
        flow_graph=graph,
        decision=decision,
        loss_rate_percent=loss_rate,
    )
