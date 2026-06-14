"""
Hikma assessment builder (E.2 slice).

Deterministic: produces an AssessmentResult dict for a CompanyProfile by REUSING
the existing, validated mizan/scoring.py engine as the scoring spine, then
attaching any SAY/DO/SHOW Evidence on record. No new scoring math is invented
here — the six Mizan dimensions and final score come straight from MizanResult.

This is the minimal foundational slice; the richer engine modules described in
docs/hikma_*_spec.json build on this contract later.
"""
from __future__ import annotations

from mizan.scoring import score_company


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
    """Return a deterministic AssessmentResult dict for a CompanyProfile.

    profile      : companies.models.CompanyProfile
    evidence_qs  : optional iterable of hikma.models.Evidence (defaults to the
                   profile's linked evidence if available).
    """
    mizan = score_company(profile)
    m = mizan.to_dict()

    if evidence_qs is None:
        evidence_qs = list(getattr(profile, "hikma_evidence", []).all()) \
            if hasattr(profile, "hikma_evidence") else []
    else:
        evidence_qs = list(evidence_qs)

    buckets = _say_do_show(evidence_qs)
    company = profile.company

    return {
        "subject": {
            "type": "company",
            "ref": company.slug,
            "name": company.name,
        },
        "engine_version": "hikma-assess-v1",
        "scoring_spine": "mizan/scoring.py score_company (reused, unmodified)",
        # ── Mizan spine (deterministic, not re-computed) ──────────────────────
        "composite_score": round(m["final_mizan_score"], 1),
        "band": m["mizan_label"],
        "mizan_dimensions": {
            "public_benefit": round(m["public_benefit_score"], 1),
            "harm_reduction": round(m["harm_reduction_score"], 1),
            "justice_distribution": round(m["justice_distribution_score"], 1),
            "transparency_accountability": round(m["transparency_accountability_score"], 1),
            "stewardship": round(m["stewardship_score"], 1),
            "evidence_confidence": round(m["evidence_confidence_score"], 1),
        },
        "benefit_assessment": {"score": round(m["public_benefit_score"], 1)},
        "harm_assessment": {
            "score": round(100 - m["harm_reduction_score"], 1),
            "risk_flags": m["risk_flags"],
            "greenwashing_risk": m.get("greenwashing_risk", {}),
        },
        "governance_assessment": {"score": round(m["transparency_accountability_score"], 1)},
        "stewardship_assessment": {"score": round(m["stewardship_score"], 1)},
        # ── SAY / DO / SHOW evidence on record ────────────────────────────────
        "evidence_used": {
            "counts": {k: len(v) for k, v in buckets.items()},
            "say": buckets["say"],
            "do": buckets["do"],
            "show": buckets["show"],
        },
        # ── Provenance / guardrails (carried from the spec contract) ──────────
        "data_confidence": m["confidence"],
        "scholar_review_required": True,
        "recommended_next_actions": m["recommended_next_actions"],
        "disclaimer": (
            "AI-assisted, indicative, decision-support only; not investment, "
            "legal, financial, or regulatory advice; not a ruling."
        ),
    }
