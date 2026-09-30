"""Islah change-design contracts for EcoIQ OS.

An Islah proposal describes which system mechanism should change and how the
flow is expected to change. It is a candidate for modelling, not permission to
implement.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from mizan.system_balance import MIZAN_DIMENSIONS


INTERVENTION_LEVELS = (
    "behaviour",
    "process",
    "contract",
    "incentive",
    "organisation",
    "regulation",
    "market_structure",
    "institution",
)


@dataclass(frozen=True)
class IslahProposal:
    id: str
    title: str
    intervention_level: str
    target_mechanism: str
    current_rule: str
    proposed_rule: str
    expected_behaviour_change: str
    expected_flow_change: str
    affected_dimensions: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()
    new_risks: tuple[str, ...] = ()
    reversible: bool | None = None
    requires_mizan_simulation: bool = True
    requires_human_review: bool = True

    def __post_init__(self) -> None:
        if self.intervention_level not in INTERVENTION_LEVELS:
            raise ValueError(f"Unknown intervention level: {self.intervention_level}")
        if not self.id.strip() or not self.title.strip():
            raise ValueError("Islah proposal id and title are required.")
        if not self.current_rule.strip() or not self.proposed_rule.strip():
            raise ValueError("Current and proposed rules must be explicit.")
        unknown_dimensions = set(self.affected_dimensions) - set(MIZAN_DIMENSIONS)
        if unknown_dimensions:
            raise ValueError(
                f"Unknown Mizan dimensions in Islah proposal: {sorted(unknown_dimensions)}"
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
