"""Evidence-state and intervention gates shared across EcoIQ OS.

The OS never stores a causal hypothesis as TRUE. Evidence states describe the
strength of support for a mechanism in an explicit population and time period.
"""
from __future__ import annotations


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


def intervention_permission(status: str) -> str:
    """Return the maximum intervention stage justified by evidence status."""
    if status not in HYPOTHESIS_STATUSES:
        raise ValueError(f"Unknown hypothesis status: {status}")
    if status == ROBUST_ASSOCIATION:
        return EXPLORATORY_MODELLING
    if status == CAUSAL_SUPPORT:
        return POLICY_SIMULATION
    if status == REPLICATED_CAUSAL_SUPPORT:
        return IMPLEMENTATION_PROPOSAL
    return NOT_ALLOWED
