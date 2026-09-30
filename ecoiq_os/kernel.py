"""Deterministic decision kernel for EcoIQ OS.

This kernel coordinates evidence state, Universal Flow Graph validity and Mizan
system balance. It does not call an LLM and does not implement policy. Its job
is to say which OS stage is justified next.
"""
from __future__ import annotations

from dataclasses import dataclass

from ecoiq_os.domains import get_domain
from ecoiq_os.evidence import (
    CAUSAL_SUPPORT,
    REPLICATED_CAUSAL_SUPPORT,
    ROBUST_ASSOCIATION,
    intervention_permission,
)
from ecoiq_os.flow import UniversalFlowGraph
from mizan.system_balance import (
    CRITICAL,
    IMBALANCED,
    INSUFFICIENT_DATA,
    MizanSystemAssessment,
)


COLLECT_EVIDENCE = "COLLECT_EVIDENCE"
REPAIR_FLOW_GRAPH = "REPAIR_FLOW_GRAPH"
RUN_FALSIFICATION = "RUN_FALSIFICATION"
DESIGN_ISLAH = "DESIGN_ISLAH"
SIMULATE_ISLAH = "SIMULATE_ISLAH"
HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
HUMAN_REVIEW_FOR_IMPLEMENTATION = "HUMAN_REVIEW_FOR_IMPLEMENTATION"
IHSAN_OPTIMISATION = "IHSAN_OPTIMISATION"


@dataclass(frozen=True)
class EcoIQOSCase:
    case_id: str
    domain: str
    objective: str
    flow_graph: UniversalFlowGraph
    mizan: MizanSystemAssessment
    hypothesis_status: str

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise ValueError("case_id is required.")
        if not self.objective.strip():
            raise ValueError("objective is required.")
        get_domain(self.domain)
        intervention_permission(self.hypothesis_status)


@dataclass(frozen=True)
class EcoIQOSDecision:
    next_stage: str
    reason: str
    intervention_permission: str
    requires_human_review: bool
    blocked_by: tuple[str, ...] = ()


def evaluate_case(case: EcoIQOSCase) -> EcoIQOSDecision:
    """Return the next justified OS stage without overclaiming evidence."""
    permission = intervention_permission(case.hypothesis_status)
    flow_issues = case.flow_graph.validation_issues()

    if flow_issues:
        return EcoIQOSDecision(
            next_stage=REPAIR_FLOW_GRAPH,
            reason="The Universal Flow Graph is structurally invalid; analysis must stop before optimisation.",
            intervention_permission=permission,
            requires_human_review=False,
            blocked_by=tuple(issue.code for issue in flow_issues),
        )

    if case.mizan.breached_constraints:
        return EcoIQOSDecision(
            next_stage=HUMAN_REVIEW_REQUIRED,
            reason="A hard Mizan constraint is breached; it blocks automated progression and cannot be averaged away by benefits elsewhere.",
            intervention_permission=permission,
            requires_human_review=True,
            blocked_by=tuple(item.key for item in case.mizan.breached_constraints),
        )

    if case.mizan.human_decision_required:
        return EcoIQOSDecision(
            next_stage=HUMAN_REVIEW_REQUIRED,
            reason="Mizan identified an explicit cross-dimension conflict that requires a human decision before the OS can progress.",
            intervention_permission=permission,
            requires_human_review=True,
            blocked_by=tuple(conflict.key for conflict in case.mizan.review_conflicts),
        )

    if case.mizan.status == INSUFFICIENT_DATA:
        return EcoIQOSDecision(
            next_stage=COLLECT_EVIDENCE,
            reason="Mizan cannot assess system balance from the available evidence.",
            intervention_permission=permission,
            requires_human_review=False,
            blocked_by=("mizan_insufficient_data",),
        )

    if case.hypothesis_status not in (
        ROBUST_ASSOCIATION,
        CAUSAL_SUPPORT,
        REPLICATED_CAUSAL_SUPPORT,
    ):
        return EcoIQOSDecision(
            next_stage=RUN_FALSIFICATION,
            reason="The candidate mechanism has not survived enough falsification to justify Islah modelling.",
            intervention_permission=permission,
            requires_human_review=False,
        )

    if case.mizan.status in (IMBALANCED, CRITICAL):
        if case.hypothesis_status == ROBUST_ASSOCIATION:
            return EcoIQOSDecision(
                next_stage=DESIGN_ISLAH,
                reason="A material imbalance exists and the mechanism has robust association; exploratory Islah design is allowed.",
                intervention_permission=permission,
                requires_human_review=False,
            )
        if case.hypothesis_status == CAUSAL_SUPPORT:
            return EcoIQOSDecision(
                next_stage=SIMULATE_ISLAH,
                reason="The mechanism has causal support; simulate alternative system changes and re-run Mizan before any implementation decision.",
                intervention_permission=permission,
                requires_human_review=False,
            )
        return EcoIQOSDecision(
            next_stage=HUMAN_REVIEW_FOR_IMPLEMENTATION,
            reason="Replicated causal support permits an implementation proposal, but consequential change remains human-reviewed.",
            intervention_permission=permission,
            requires_human_review=True,
        )

    return EcoIQOSDecision(
        next_stage=IHSAN_OPTIMISATION,
        reason="No material Mizan imbalance is established; continue improvement without inventing a corrective mechanism.",
        intervention_permission=permission,
        requires_human_review=case.mizan.human_decision_required,
    )
