"""Code-owned contracts for the EcoIQ Poverty & Justice Engine.

The first invariant is epistemic: a hypothesis is never stored as TRUE.
Interventions are gated by evidence status, and association alone cannot unlock
policy simulation or implementation proposals.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


UNTESTED = "UNTESTED"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
ASSOCIATION_ONLY = "ASSOCIATION_ONLY"
FAILED_FALSIFICATION_1 = "FAILED_FALSIFICATION_1"
FAILED_FALSIFICATION_2 = "FAILED_FALSIFICATION_2"
ROBUST_ASSOCIATION = "ROBUST_ASSOCIATION"
CAUSAL_SUPPORT = "CAUSAL_SUPPORT"
REPLICATED_CAUSAL_SUPPORT = "REPLICATED_CAUSAL_SUPPORT"
REFORMULATED = "REFORMULATED"
REJECTED = "REJECTED"

HYPOTHESIS_STATUSES = (
    UNTESTED,
    INSUFFICIENT_DATA,
    ASSOCIATION_ONLY,
    FAILED_FALSIFICATION_1,
    FAILED_FALSIFICATION_2,
    ROBUST_ASSOCIATION,
    CAUSAL_SUPPORT,
    REPLICATED_CAUSAL_SUPPORT,
    REFORMULATED,
    REJECTED,
)

NOT_ALLOWED = "NOT_ALLOWED"
EXPLORATORY_MODELLING = "EXPLORATORY_MODELLING"
POLICY_SIMULATION = "POLICY_SIMULATION"
IMPLEMENTATION_PROPOSAL = "IMPLEMENTATION_PROPOSAL"

TEST_TYPES = (
    "DESCRIPTIVE",
    "ASSOCIATION",
    "MATCHED_COMPARISON",
    "MULTILEVEL_REGRESSION",
    "PROPENSITY_WEIGHTED",
    "FIXED_EFFECTS",
    "DIFFERENCE_IN_DIFFERENCES",
    "EVENT_STUDY",
    "REGRESSION_DISCONTINUITY",
    "INSTRUMENTAL_VARIABLE",
    "SURVIVAL_ANALYSIS",
    "SENSITIVITY_ANALYSIS",
    "PLACEBO",
    "NEGATIVE_CONTROL",
    "OUT_OF_SAMPLE",
)


def intervention_permission(status: str) -> str:
    """Return the maximum intervention stage unlocked by evidence status."""
    if status not in HYPOTHESIS_STATUSES:
        raise ValueError(f"Unknown hypothesis status: {status}")
    if status == ROBUST_ASSOCIATION:
        return EXPLORATORY_MODELLING
    if status == CAUSAL_SUPPORT:
        return POLICY_SIMULATION
    if status == REPLICATED_CAUSAL_SUPPORT:
        return IMPLEMENTATION_PROPOSAL
    return NOT_ALLOWED


@dataclass(frozen=True)
class PopulationScope:
    unit: str
    country: str
    regions: tuple[str, ...] = ("ALL",)
    period_start: str | None = None
    period_end: str | None = None

    def __post_init__(self) -> None:
        if self.unit not in ("household", "individual", "region", "institution"):
            raise ValueError(f"Unsupported unit of analysis: {self.unit}")
        if not self.country:
            raise ValueError("Country is required.")


@dataclass(frozen=True)
class CausalQuestion:
    exposure: str
    outcome: str
    estimand: str

    def __post_init__(self) -> None:
        if not self.exposure.strip() or not self.outcome.strip():
            raise ValueError("Exposure and outcome are required.")
        if not self.estimand.strip():
            raise ValueError("Estimand is required.")


@dataclass(frozen=True)
class TestRequirement:
    test_type: str
    required: bool = True

    def __post_init__(self) -> None:
        if self.test_type not in TEST_TYPES:
            raise ValueError(f"Unsupported causal test type: {self.test_type}")


@dataclass(frozen=True)
class CausalTestSpec:
    hypothesis_id: str
    hypothesis_statement: str
    scope: PopulationScope
    causal_question: CausalQuestion
    confounders: tuple[str, ...] = ()
    mediators: tuple[str, ...] = ()
    colliders: tuple[str, ...] = ()
    effect_modifiers: tuple[str, ...] = ()
    tests: tuple[TestRequirement, ...] = ()
    kill_conditions: tuple[str, ...] = ()
    alternative_explanations: tuple[str, ...] = ()
    temporal_order_required: bool = False
    survey_weights_required: bool = False
    minimum_sample_size: int | None = None
    status: str = UNTESTED

    def __post_init__(self) -> None:
        if self.status not in HYPOTHESIS_STATUSES:
            raise ValueError(f"Unknown hypothesis status: {self.status}")
        if self.status == "TRUE":
            raise ValueError("TRUE is not a valid hypothesis status.")
        if not self.hypothesis_id.strip():
            raise ValueError("Hypothesis id is required.")
        if not self.hypothesis_statement.strip():
            raise ValueError("Hypothesis statement is required.")
        if self.minimum_sample_size is not None and self.minimum_sample_size <= 0:
            raise ValueError("minimum_sample_size must be positive.")

        overlap = set(self.confounders) & set(self.mediators)
        if overlap:
            raise ValueError(
                f"Variables cannot be both confounders and mediators: {sorted(overlap)}"
            )
        overlap = set(self.confounders) & set(self.colliders)
        if overlap:
            raise ValueError(
                f"Variables cannot be both confounders and colliders: {sorted(overlap)}"
            )

    @property
    def intervention_permission(self) -> str:
        return intervention_permission(self.status)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["intervention_permission"] = self.intervention_permission
        return payload


@dataclass(frozen=True)
class FalsificationAssessment:
    hypothesis_id: str
    current_status: str
    recommended_status: str
    strongest_evidence_for: tuple[str, ...] = ()
    strongest_evidence_against: tuple[str, ...] = ()
    counterexamples: tuple[str, ...] = ()
    alternative_mechanisms: tuple[str, ...] = ()
    data_gaps: tuple[str, ...] = ()
    next_test: str | None = None
    limitations: tuple[str, ...] = ()
    bias_checks: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for status in (self.current_status, self.recommended_status):
            if status not in HYPOTHESIS_STATUSES:
                raise ValueError(f"Unknown hypothesis status: {status}")

    @property
    def intervention_permission(self) -> str:
        return intervention_permission(self.recommended_status)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["intervention_permission"] = self.intervention_permission
        return payload
