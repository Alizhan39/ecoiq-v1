"""
Hikma assessment builder (E.2 + activation slice).

Deterministic: produces an AssessmentResult dict for a CompanyProfile by REUSING
the existing, validated mizan/scoring.py engine as the scoring spine, attaching
any SAY/DO/SHOW Evidence on record, and surfacing the committed graph nodes the
evidence + scoring signals activate (keyword-based, deterministic).

No new scoring math and no new theological claims are introduced here.
"""
from __future__ import annotations

from datetime import datetime, timezone

from mizan.scoring import score_company
from hikma.activation import activate


def _say_do_show(evidence_qs):
    buckets = {"say": [], "do": [], "show": []}
    for ev in evidence_qs:
        if ev.kind in buckets:
            buckets[ev.kind].append({
                "evidence_id": ev.id,
                "statement": ev.statement,
                "source_type": ev.source_type,
                "confidence_tier": ev.confidence_tier,
            })
    return buckets


def build_assessment(profile, evidence_qs=None) -> dict:
    """Return a deterministic AssessmentResult dict for a CompanyProfile."""
    mizan = score_company(profile)
    m = mizan.to_dict()

    if evidence_qs is None:
        evidence_qs = list(profile.hikma_evidence.all()) \
            if hasattr(profile, "hikma_evidence") else []
    else:
        evidence_qs = list(evidence_qs)

    buckets = _say_do_show(evidence_qs)
    company = profile.company

    dimensions = {
        "public_benefit": round(m["public_benefit_score"], 1),
        "harm_reduction": round(m["harm_reduction_score"], 1),
        "justice_distribution": round(m["justice_distribution_score"], 1),
        "transparency_accountability": round(m["transparency_accountability_score"], 1),
        "stewardship": round(m["stewardship_score"], 1),
        "evidence_confidence": round(m["evidence_confidence_score"], 1),
    }
    risk_flags = m["risk_flags"]
    source_evidence_ids = [e.id for e in evidence_qs]

    # ── deterministic node activation over the committed graph ────────────────
    activated_nodes = activate(
        statements=[e.statement for e in evidence_qs],
        dimension_labels=list(dimensions.keys()),
        risk_flags=risk_flags,
    )

    return {
        "company_slug": company.slug,
        "subject": {"type": "company", "ref": company.slug, "name": company.name},
        "engine_version": "hikma-assess-v1",
        "scoring_spine": "mizan/scoring.py score_company (reused, unmodified)",
        "composite_score": round(m["final_mizan_score"], 1),
        "rating_label": m["mizan_label"],
        "dimensions": dimensions,
        "harm_score": round(100 - m["harm_reduction_score"], 1),
        "evidence_counts": {k: len(v) for k, v in buckets.items()},
        "evidence_confidence": m["confidence"],
        "evidence_used": buckets,
        "activated_nodes": activated_nodes,
        "source_evidence_ids": source_evidence_ids,
        "flags": {
            "risk_flags": risk_flags,
            "greenwashing_risk": m.get("greenwashing_risk", {}),
            "scholar_review_required": True,
        },
        "recommended_next_actions": m["recommended_next_actions"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "disclaimer": (
            "AI-assisted, indicative, decision-support only; not investment, "
            "legal, financial, or regulatory advice; not a ruling."
        ),
    }
