"""System-level Mizan balance contract.

This module deliberately does NOT produce a single moral or sustainability
score. It records explicit balance dimensions, hard constraints and conflicts
so downstream workflows can detect when a local optimisation creates a wider
system imbalance.

Unknown evidence remains unknown. Callers must provide evidence-backed
dimension states; this module never invents thresholds or fills missing values.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Iterable


HEALTHY = "HEALTHY"
WATCH = "WATCH"
IMBALANCED = "IMBALANCED"
CRITICAL = "CRITICAL"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

DIMENSION_STATUSES = (
    HEALTHY,
    WATCH,
    IMBALANCED,
    CRITICAL,
    INSUFFICIENT_DATA,
)

MIZAN_DIMENSIONS = (
    "economic",
    "resource_efficiency",
    "energy",
    "water",
    "environment",
    "human",
    "worker",
    "social",
    "justice",
    "resilience",
    "intergenerational",
)

SCOPE_LEVELS = (
    "asset",
    "process",
    "facility",
    "company",
    "supply_chain",
    "city",
    "region",
    "country",
    "ecosystem",
)

_STATUS_SEVERITY = {
    HEALTHY: 0,
    WATCH: 1,
    IMBALANCED: 2,
    CRITICAL: 3,
}


@dataclass(frozen=True)
class BalanceDimension:
    """One evidence-backed dimension in a system-level Mizan assessment."""

    key: str
    status: str
    current_value: float | None = None
    unit: str | None = None
    trend: str | None = None
    pressure: str | None = None
    threshold: float | None = None
    threshold_source: str | None = None
    affected_parties: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    notes: str = ""

    def __post_init__(self) -> None:
        if self.key not in MIZAN_DIMENSIONS:
            raise ValueError(f"Unknown Mizan dimension: {self.key}")
        if self.status not in DIMENSION_STATUSES:
            raise ValueError(f"Unknown Mizan dimension status: {self.status}")
        if self.threshold is not None and not self.threshold_source:
            raise ValueError("A numeric threshold must name its source.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MizanConstraint:
    """A hard constraint that is not tradeable against a higher score elsewhere."""

    key: str
    breached: bool
    category: str
    description: str
    source: str
    affected_parties: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.key.strip():
            raise ValueError("Constraint key is required.")
        if not self.source.strip():
            raise ValueError("Constraint source is required.")


@dataclass(frozen=True)
class MizanConflict:
    """An explicit trade-off requiring comparison rather than hidden averaging."""

    key: str
    dimensions: tuple[str, ...]
    description: str
    affected_parties: tuple[str, ...] = ()
    human_decision_required: bool = True

    def __post_init__(self) -> None:
        unknown = set(self.dimensions) - set(MIZAN_DIMENSIONS)
        if unknown:
            raise ValueError(f"Unknown Mizan conflict dimensions: {sorted(unknown)}")


@dataclass(frozen=True)
class MizanSystemAssessment:
    """System-level balance result with no fabricated aggregate score."""

    scope_level: str
    status: str
    dimensions: tuple[BalanceDimension, ...]
    conflicts: tuple[MizanConflict, ...] = ()
    constraints: tuple[MizanConstraint, ...] = ()
    time_horizons: tuple[str, ...] = ("now",)
    human_decision_required: bool = False

    @property
    def breached_constraints(self) -> tuple[MizanConstraint, ...]:
        return tuple(item for item in self.constraints if item.breached)

    @property
    def requires_islah(self) -> bool:
        return self.status in (IMBALANCED, CRITICAL)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope_level": self.scope_level,
            "status": self.status,
            "dimensions": [item.to_dict() for item in self.dimensions],
            "conflicts": [asdict(item) for item in self.conflicts],
            "constraints": [asdict(item) for item in self.constraints],
            "breached_constraints": [asdict(item) for item in self.breached_constraints],
            "time_horizons": list(self.time_horizons),
            "human_decision_required": self.human_decision_required,
            "requires_islah": self.requires_islah,
        }


def assess_balance(
    *,
    scope_level: str,
    dimensions: Iterable[BalanceDimension],
    constraints: Iterable[MizanConstraint] = (),
    conflicts: Iterable[MizanConflict] = (),
    time_horizons: Iterable[str] = ("now",),
) -> MizanSystemAssessment:
    """Aggregate explicit dimension states without inventing a master score.

    Rules:
    * no known dimensions -> INSUFFICIENT_DATA;
    * any breached hard constraint -> CRITICAL;
    * otherwise the worst known dimension controls the system status;
    * explicit conflicts always require human review.

    The function intentionally does not infer dimension states from raw numbers.
    Threshold selection belongs to a versioned, evidence-backed methodology.
    """
    if scope_level not in SCOPE_LEVELS:
        raise ValueError(f"Unknown Mizan scope level: {scope_level}")

    dims = tuple(dimensions)
    constraint_items = tuple(constraints)
    conflict_items = tuple(conflicts)
    horizons = tuple(time_horizons) or ("now",)

    duplicate_keys = {d.key for d in dims if sum(x.key == d.key for x in dims) > 1}
    if duplicate_keys:
        raise ValueError(f"Duplicate Mizan dimensions: {sorted(duplicate_keys)}")

    breached = tuple(item for item in constraint_items if item.breached)
    known = tuple(d for d in dims if d.status != INSUFFICIENT_DATA)

    if breached:
        status = CRITICAL
    elif not known:
        status = INSUFFICIENT_DATA
    else:
        status = max(known, key=lambda item: _STATUS_SEVERITY[item.status]).status

    return MizanSystemAssessment(
        scope_level=scope_level,
        status=status,
        dimensions=dims,
        conflicts=conflict_items,
        constraints=constraint_items,
        time_horizons=horizons,
        human_decision_required=bool(conflict_items or breached),
    )
