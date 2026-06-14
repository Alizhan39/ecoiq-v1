"""
Hikma contradiction / verification-gap analysis (read-only, deterministic).

Operates ONLY on already-stored Evidence rows (and, if present, the latest
stored AssessmentRun). It does not ingest, score, or mutate anything.

Language is deliberately careful — these are signals for analyst/scholar review,
never accusations or rulings:
  "potential gap", "requires verification", "evidence confidence is limited",
  "possible greenwashing signal", "not independently verified".
"""
from __future__ import annotations

from datetime import datetime, timezone

# source_type -> how the evidence was obtained (no DB field needed; derived)
EXTRACTION_METHOD = {
    "ecoiq_assessment": "ecoiq-computed",
    "company_disclosure": "profile-field-extraction",
    "sustainability_report": "profile-field-extraction",
    "annual_report": "profile-field-extraction",
    "public_source": "cited-source",
    "dataset": "model-estimate",
}

_LOW_TIERS = {"ai-seeded", "model-estimate"}
_CLIMATE_TERMS = ("net-zero", "net zero", "emission", "carbon", "climate", "decarbon", "renewable")
_GOV_TERMS = ("governance", "transparen", "accountab", "anti-corruption", "ethics", "board")
_SHOW_INDEPENDENT = {"dataset", "ecoiq_assessment", "public_source"}


def extraction_method(source_type: str) -> str:
    return EXTRACTION_METHOD.get(source_type, "unspecified")


def _text(evs):
    return " ".join((e.statement or "").lower() for e in evs)


def analyze(slug, evidence_qs, latest_run=None) -> dict:
    """Return contradiction/gap signals from stored evidence only."""
    evs = list(evidence_qs)
    say = [e for e in evs if e.kind == "say"]
    do = [e for e in evs if e.kind == "do"]
    show = [e for e in evs if e.kind == "show"]
    show_text = _text(show)
    do_text = _text(do)
    independent_show = [e for e in show if e.source_type in _SHOW_INDEPENDENT]

    contradiction_signals = []
    greenwashing_signals = []
    verification_gaps = []

    # ── SAY claims lacking corroborating SHOW (topic-keyword overlap) ─────────
    for s in say:
        words = {w for w in (s.statement or "").lower().split() if len(w) > 4}
        corroborated = any(w in show_text or w in do_text for w in words)
        if not corroborated:
            contradiction_signals.append({
                "type": "say_without_show",
                "claim": s.statement,
                "evidence_ids": [s.id],
                "severity": "medium",
                "assessment": "Stated claim has no corroborating action or independent outcome on record — potential gap; requires verification.",
            })

    # ── Climate/net-zero claims without measurable implementation evidence ────
    say_climate = [s for s in say if any(t in (s.statement or "").lower() for t in _CLIMATE_TERMS)]
    show_climate_measured = any(
        e.metric_value is not None and any(t in (e.statement or "").lower() for t in _CLIMATE_TERMS)
        for e in show
    )
    if say_climate and not show_climate_measured:
        greenwashing_signals.append({
            "type": "climate_claim_unverified",
            "claims": [s.statement for s in say_climate],
            "evidence_ids": [s.id for s in say_climate],
            "severity": "medium",
            "assessment": "Climate/decarbonisation claims are present without measurable, independently verified implementation evidence — possible greenwashing signal; not independently verified.",
        })

    # ── Governance claims without accountability evidence ─────────────────────
    say_gov = [s for s in say if any(t in (s.statement or "").lower() for t in _GOV_TERMS)]
    show_gov = any(any(t in (e.statement or "").lower() for t in _GOV_TERMS) for e in show)
    if say_gov and not show_gov:
        contradiction_signals.append({
            "type": "governance_claim_unverified",
            "claims": [s.statement for s in say_gov],
            "evidence_ids": [s.id for s in say_gov],
            "severity": "low",
            "assessment": "Governance/transparency claims lack corroborating accountability evidence — potential gap; requires verification.",
        })

    # ── Evidence-confidence gaps ──────────────────────────────────────────────
    low_conf = [e for e in evs if e.confidence_tier in _LOW_TIERS]
    if evs and len(low_conf) / len(evs) >= 0.4:
        verification_gaps.append({
            "type": "low_confidence_evidence_base",
            "ratio_low_confidence": round(len(low_conf) / len(evs), 2),
            "evidence_ids": [e.id for e in low_conf],
            "assessment": "A large share of evidence is AI-seeded or model-estimated — evidence confidence is limited; independent verification recommended.",
        })
    if not independent_show:
        verification_gaps.append({
            "type": "no_independent_show",
            "evidence_ids": [],
            "assessment": "No independent (dataset/regulator/cited) SHOW evidence on record — outcomes are not independently verified.",
        })

    # ── greenwashing prior from a stored run (read-only; not recomputed) ──────
    if latest_run and isinstance(latest_run.result, dict):
        gw = latest_run.result.get("flags", {}).get("greenwashing_risk")
        if gw:
            greenwashing_signals.append({
                "type": "stored_greenwashing_prior",
                "value": gw,
                "evidence_ids": [],
                "assessment": "Greenwashing prior from the latest stored assessment (Mizan engine); indicative only.",
            })

    # ── recommended next questions (review prompts, not conclusions) ──────────
    questions = []
    if say_climate and not show_climate_measured:
        questions.append("What independently verified data confirm the stated climate/emissions targets?")
    if any(c["type"] == "say_without_show" for c in contradiction_signals):
        questions.append("Which actions and independent outcomes substantiate the stated commitments?")
    if not independent_show:
        questions.append("Are there regulator filings or third-party datasets corroborating reported outcomes?")
    if say_gov and not show_gov:
        questions.append("What accountability mechanisms evidence the governance claims?")
    if not questions:
        questions.append("What additional independent evidence would raise confidence in this assessment?")

    return {
        "company_slug": slug,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "evidence_counts": {"say": len(say), "do": len(do), "show": len(show), "total": len(evs)},
        "contradiction_signals": contradiction_signals,
        "greenwashing_signals": greenwashing_signals,
        "verification_gaps": verification_gaps,
        "recommended_next_questions": questions,
        "disclaimer": (
            "Read-only, AI-assisted signals for analyst/scholar review only. These are "
            "potential gaps requiring verification — not accusations, legal findings, "
            "or rulings."
        ),
    }
