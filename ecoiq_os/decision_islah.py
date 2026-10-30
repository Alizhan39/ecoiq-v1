"""EcoIQ OS Decision & Islah: evidence-first, read-only candidate briefing.

This is a deterministic hypothesis and falsification planner, NOT a
generative AI judgement. It accepts reported aggregate facts; it cannot
discover causes, verify sources, predict savings or authorise intervention.
Existing evidence, Mizan, kernel and Islah contracts remain authoritative.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
import re
from typing import Any

from ecoiq_os.domains import get_domain
from ecoiq_os.evidence import UNTESTED
from ecoiq_os.islah import IslahProposal
from ecoiq_os.flow import RESOURCE_TYPES
from ecoiq_os.kernel import (
    COLLECT_EVIDENCE, DESIGN_ISLAH, HUMAN_REVIEW_FOR_IMPLEMENTATION,
    SIMULATE_ISLAH, EcoIQOSCase, evaluate_case,
)
from mizan.system_balance import MIZAN_DIMENSIONS


@dataclass(frozen=True)
class FalsifiableHypothesis:
    """An untested question, not a measured explanation or causal finding."""

    key: str
    question: str
    disconfirming_observation: str
    evidence_needed: tuple[str, ...]
    status: str = UNTESTED

    def __post_init__(self) -> None:
        if self.status != UNTESTED:
            raise ValueError("Generated candidate hypotheses must stay UNTESTED.")
        if not self.key or not self.question or not self.disconfirming_observation:
            raise ValueError("Hypothesis requires a question and a disconfirmation test.")
        if not self.evidence_needed:
            raise ValueError("A test must state the necessary evidence.")


@dataclass(frozen=True)
class IslahStudy:
    """A suggested *study*, not an IslahProposal or an approved rule change."""

    key: str
    question: str
    prerequisite: str
    affected_dimensions: tuple[str, ...]
    possible_unintended_effects: tuple[str, ...]
    status: str = "STUDY_ONLY"

    def __post_init__(self) -> None:
        if not self.key or not self.question or not self.prerequisite:
            raise ValueError("Study must have a question and prerequisite.")
        if not self.affected_dimensions or (
            set(self.affected_dimensions) - set(MIZAN_DIMENSIONS)
        ):
            raise ValueError("Study dimensions must be declared Mizan dimensions.")
        if self.status != "STUDY_ONLY":
            raise ValueError("Generated studies are not implementation permission.")


def _reported_quantity(value: float | None, label: str) -> float | None:
    if value is None:
        return None
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not isfinite(value) or value < 0):
        raise ValueError(f"{label} must be finite, non-negative or unknown.")
    return float(value)


def build_preliminary_brief(
    *, case_id: str, domain: str, process_name: str, resource_type: str,
    period: str, unit: str, reported_input: float | None,
    reported_loss: float | None,
) -> dict[str, Any]:
    """Create a minimal, safe briefing from unverified aggregate observations.

    Source records and their permissions are NOT available to this pure
    function; callers must separately enforce project READ access. The
    retained history is not signed evidence. No user-supplied flags can
    promote a finding, safety state or intervention permission here.
    """
    get_domain(domain)
    for label, value in (
        ("case_id", case_id), ("process_name", process_name),
        ("resource_type", resource_type), ("period", period), ("unit", unit),
    ):
        if not isinstance(value, str) or not value.strip() or len(value) > 128:
            raise ValueError(f"Invalid {label}.")
    if resource_type not in RESOURCE_TYPES:
        raise ValueError("Unknown EcoIQ OS resource type.")
    if re.fullmatch(r"[0-9]{4}-(?:0[1-9]|1[0-2])", period) is None:
        raise ValueError("Period must use YYYY-MM.")
    total = _reported_quantity(reported_input, "reported_input")
    loss = _reported_quantity(reported_loss, "reported_loss")
    if total is not None and loss is not None and loss > total:
        raise ValueError("Reported loss cannot exceed reported input.")

    has_usable_loss = total is not None and total > 0 and loss is not None and loss > 0
    has_reported_zero_loss = total is not None and total > 0 and loss == 0
    hypotheses: tuple[FalsifiableHypothesis, ...]
    studies: tuple[IslahStudy, ...]

    if has_usable_loss:
        hypotheses = (
            FalsifiableHypothesis(
                key="MEASUREMENT_BOUNDARY",
                question="Could reporting cut-offs or stock movements explain part of the reported loss?",
                disconfirming_observation=(
                    "Independent input, stock and disposal records reconcile within "
                    "a documented common accounting boundary."
                ),
                evidence_needed=(
                    "Dated receipts and delivery notes", "Opening and closing stock",
                    "Physical waste and returns records",
                ),
            ),
            FalsifiableHypothesis(
                key="PLANNED_YIELD",
                question="Does the recorded loss include expected or necessary process yield?",
                disconfirming_observation=(
                    "A signed method or bill of quantities identifies the reported "
                    "loss as outside documented normal yield."
                ),
                evidence_needed=(
                    "Approved process specification", "Expected yield method",
                    "Product and waste classifications",
                ),
            ),
            FalsifiableHypothesis(
                key="HANDLING_AND_STORAGE",
                question="Could handling or storage conditions contribute to excess loss?",
                disconfirming_observation=(
                    "Comparable observed batches show no material change in "
                    "loss with different handling or storage conditions."
                ),
                evidence_needed=(
                    "Batch-level observations", "Site handling and storage records",
                    "Worker safety and environmental impact review",
                ),
            ),
        )
        studies = (
            IslahStudy(
                key="RECONCILE_FLOW",
                question="Should the team audit the common resource and stock boundary before proposing change?",
                prerequisite="Independent measurement and source reconciliation.",
                affected_dimensions=("resource_efficiency", "economic", "justice"),
                possible_unintended_effects=(
                    "Additional reporting burden on workers",
                    "Incorrect attribution of discrepancies to suppliers or staff",
                ),
            ),
            IslahStudy(
                key="TEST_HANDLING",
                question="Would a small, safe observation study clarify whether handling contributes to loss?",
                prerequisite="Site safety review and a pre-registered observational method.",
                affected_dimensions=("resource_efficiency", "worker", "environment", "economic"),
                possible_unintended_effects=(
                    "Worker safety or workload changes",
                    "Shifted waste or emissions into another process",
                ),
            ),
        )
    else:
        hypotheses = ()
        studies = (
            IslahStudy(
                key="ESTABLISH_BASELINE",
                question="Can independent measurements establish a complete and comparable process baseline?",
                prerequisite="Verified receipt, stock, output and loss definitions.",
                affected_dimensions=("resource_efficiency", "economic", "worker"),
                possible_unintended_effects=(
                    "Administrative workload", "False certainty from incomplete records",
                ),
            ),
        )

    missing = ["authenticated_source_documents", "measurement_boundary_review",
               "worker_safety_assessment", "environmental_assessment",
               "causal_falsification", "independent_mizan_review",
               "human_approval"]
    if total is None or total == 0:
        missing.insert(0, "usable_reported_input")
    if loss is None:
        missing.insert(0, "reported_loss_measurement")

    return {
        "case_id": case_id,
        "domain": domain,
        "process_name": process_name,
        "period": period,
        "resource_type": resource_type,
        "unit": unit,
        "engine": "DETERMINISTIC_DECISION_BRIEF_V1",
        "ai_model_called": False,
        "read_only": True,
        "independently_verified": False,
        "observed_loss": loss,
        "observed_input": total,
        "observed_zero_loss": has_reported_zero_loss,
        "hypothesis_status": UNTESTED,
        "next_stage": COLLECT_EVIDENCE,
        "implementation_permitted": False,
        "causal_conclusion": None,
        "savings_forecast": None,
        "mizan_score": None,
        "hypotheses": [asdict(item) for item in hypotheses],
        "islah_studies": [asdict(item) for item in studies],
        "missing_evidence": missing,
        "safety_note": (
            "A reported loss is not necessarily avoidable waste. Hypotheses and "
            "studies are untested; do not modify a process without verified "
            "evidence, Mizan review and explicit human approval."
        ),
    }


def check_islah_readiness(
    *, case: EcoIQOSCase, proposal: IslahProposal,
) -> dict[str, Any]:
    """Internal ONLY: inspect a real, explicit-rule Islah proposal.

    The caller MUST obtain reviewed project, source and causal-state context
    through trusted services. A proposed Islah record never upgrades kernel
    permission. This function issues NO implementation permission, including
    for replicated causal support.
    """
    if not isinstance(case, EcoIQOSCase) or not isinstance(proposal, IslahProposal):
        raise TypeError("Provide trusted EcoIQOSCase and IslahProposal records.")
    if not proposal.requires_mizan_simulation or not proposal.requires_human_review:
        raise ValueError("Mizan simulation and human review cannot be disabled.")
    decision = evaluate_case(case)
    allowed_design = decision.next_stage in (
        DESIGN_ISLAH, SIMULATE_ISLAH, HUMAN_REVIEW_FOR_IMPLEMENTATION,
    )
    return {
        "case_id": case.case_id,
        "proposal_id": proposal.id,
        "kernel": asdict(decision),
        "design_study_permitted": allowed_design,
        "simulation_study_permitted": decision.next_stage in (
            SIMULATE_ISLAH, HUMAN_REVIEW_FOR_IMPLEMENTATION,
        ),
        "needs_human_implementation_review": (
            decision.next_stage == HUMAN_REVIEW_FOR_IMPLEMENTATION
        ),
        "requires_mizan_simulation": True,
        "read_only": True,
        "implementation_permitted": False,
        "approval_recorded": False,
        "blocked_by": list(decision.blocked_by),
    }
