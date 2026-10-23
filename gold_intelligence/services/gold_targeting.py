"""Evidence-gated desktop gold exploration target ranking.

This is a screening tool, not a mineral discovery, resource estimate,
drill design, mineral-rights opinion or machine-learning prediction.
No default subscores are imputed for absent evidence.
"""
from __future__ import annotations

from datetime import date, datetime
from math import isfinite
from typing import Mapping

# Explicit expert-configurable screening weights; not trained or calibrated.
WEIGHTS = {
    "host_rock_favourability": 0.25,
    "structure_favourability": 0.25,
    "geochemical_anomaly": 0.25,
    "geophysical_support": 0.15,
    "alteration_support": 0.10,
}
RIGHTS_STATUSES = {"unknown", "confirmed_available", "held_by_applicant", "third_party", "restricted"}
MIN_FIELDS = ("source", "reference", "observed_at", "method")


def _check_evidence(name: str, item: Mapping) -> float:
    if not isinstance(item, Mapping):
        raise ValueError(f"{name}: evidence must be an object")
    missing = [key for key in MIN_FIELDS if not item.get(key)]
    if missing:
        raise ValueError(f"{name}: missing provenance: {', '.join(missing)}")
    try:
        date.fromisoformat(str(item["observed_at"]))
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{name}: observed_at must be YYYY-MM-DD") from exc
    value = item.get("value")
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"{name}: value must be a finite number from 0 to 1")
    if item.get("is_demo") is True:
        raise ValueError(f"{name}: demonstration evidence cannot support real scoring")
    return float(value)


def evaluate_target(target: Mapping) -> dict:
    """Rank a target only on 100% evidenced features; retain partial data.

    Inputs are independently verified normalized favourability evidence, not
    raw assay values. Any weighting/calibration must be reviewed by a geologist.
    """
    if not isinstance(target, Mapping) or not target.get("id"):
        raise ValueError("Target must have a non-empty id")
    rights = target.get("rights_status", "unknown")
    if rights not in RIGHTS_STATUSES:
        raise ValueError("Unrecognized rights_status")
    evidence = target.get("evidence") or {}
    if not isinstance(evidence, Mapping):
        raise ValueError("evidence must be an object")
    if set(evidence) - set(WEIGHTS):
        raise ValueError("Unrecognized evidence feature(s)")
    values = {name: _check_evidence(name, item) for name, item in evidence.items()}
    missing = [name for name in WEIGHTS if name not in values]
    coverage = sum(WEIGHTS[name] for name in values)
    # Absolutely no imputation for missing features.
    score = round(100 * sum(WEIGHTS[k] * values[k] for k in WEIGHTS), 2) if not missing else None
    eligibility = (
        "rights_blocked" if rights in {"third_party", "restricted"} else
        "rights_review_required" if rights == "unknown" else
        "human_geologist_review_required" if score is not None else
        "insufficient_evidence"
    )
    if missing and eligibility == "human_geologist_review_required":
        eligibility = "insufficient_evidence"
    return {
        "id": str(target["id"]),
        "name": target.get("name"),
        "score": score,
        "score_kind": "expert_weighted_screening_index" if score is not None else None,
        "score_is_probability": False,
        "evidence_coverage": round(coverage, 4),
        "feature_values": {k: values.get(k) for k in WEIGHTS},
        "missing_features": missing,
        "rights_status": rights,
        "rights_reference": target.get("rights_reference"),
        "eligibility": eligibility,
        "drilling_authorized": False,
        "resource_estimate": None,
        "gold_grade_gpt": None,
        "caveats": [
            "Does not establish economic gold mineralization or a mineral resource.",
            "A high index is not a gold discovery probability.",
            "Check cadastral rights, protected areas and required permits independently.",
        ],
    }


def rank_targets(targets) -> list[dict]:
    """Fully covered prospects first, sorted by index; unscored remain visible."""
    results = [evaluate_target(t) for t in targets]
    return sorted(results, key=lambda r: (
        r["score"] is None,
        -(r["score"] if r["score"] is not None else 0),
        r["id"],
    ))
