"""
EcoIQ Evidence Harvester — Verification Engine (Slice 2, additive, deterministic).

Computes four sub-scores for an Evidence item and maps them to a status. Pure
functions: no I/O, no randomness, no scoring of the *company* — this scores the
*evidence* (how trustworthy/corroborated the record is), not the subject.

  source_quality_score  ← Source.confidence_base (or source-type fallback)
  freshness_score       ← decay from publication_date (5-year horizon)
  corroboration_score   ← rises with the number of independent corroborating sources
  confidence_score      ← 0.5·quality + 0.2·freshness + 0.3·corroboration

Status:
  CONTRADICTED          — sources disagree (flagged by the dedup engine)
  NOT_FOUND             — no source/evidence at all
  INSUFFICIENT_EVIDENCE — single weak source, no corroboration
  VERIFIED              — corroborated (≥2 independent sources) AND high confidence
  PARTIAL               — single credible source, not yet corroborated
  UNVERIFIED            — recorded but below the thresholds above
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

# Fallback source-class quality when no Source row is attached. Mirrors the
# Source Registry base-confidence bands (primary filings high … media medium).
SOURCE_TYPE_QUALITY = {
    "companies_house": 0.92, "sec_edgar": 0.92, "fca_filing": 0.92, "ofgem": 0.88,
    "environment_agency": 0.88, "regulatory_filing": 0.85, "sbti": 0.85,
    "annual_report": 0.85, "issb": 0.82, "cdp": 0.82, "iea": 0.82,
    "tcfd_report": 0.80, "world_bank": 0.80, "oecd": 0.80, "gri": 0.80,
    "sasb": 0.80, "transition_plan": 0.78, "undp": 0.78,
    "sustainability_report": 0.75, "esg_report": 0.75, "tender_portal": 0.75,
    "procurement_db": 0.75, "investor_relations": 0.70,
    "financial_times": 0.65, "reuters": 0.65, "bloomberg": 0.65,
    "press_release": 0.60, "company_website": 0.55,
}
DEFAULT_QUALITY = 0.5

FRESHNESS_HORIZON_YEARS = 5.0
UNKNOWN_DATE_FRESHNESS = 0.3   # present-but-undated penalty (not zero, not full)

# Status thresholds
VERIFIED_MIN_CONFIDENCE = 0.60
VERIFIED_MIN_CORROBORATION = 0.50   # ≥2 independent sources (see corroboration curve)
PARTIAL_MIN_QUALITY = 0.60
INSUFFICIENT_MAX_QUALITY = 0.45


@dataclass
class VerificationResult:
    source_quality_score: float
    freshness_score: float
    corroboration_score: float
    confidence_score: float
    verification_status: str


def _clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def source_quality(source_type: str = "", confidence_base: float | None = None) -> float:
    """Base trust for the source. Prefers an explicit Source.confidence_base."""
    if confidence_base is not None:
        return _clamp(float(confidence_base))
    return SOURCE_TYPE_QUALITY.get(source_type, DEFAULT_QUALITY)


def freshness(publication_date, *, now: date | None = None) -> float:
    """Linear decay over FRESHNESS_HORIZON_YEARS. Undated → small fixed penalty."""
    if not publication_date:
        return UNKNOWN_DATE_FRESHNESS
    now = now or datetime.now(timezone.utc).date()
    years = (now - publication_date).days / 365.0
    if years < 0:
        years = 0.0  # future-dated → treat as current
    return _clamp(1.0 - years / FRESHNESS_HORIZON_YEARS)


def corroboration(independent_sources: int) -> float:
    """0 corroborating → 0.0; saturating curve as more independent sources agree.
    1→0.50, 2→0.75, 3→0.875 … (1 - 0.5**n)."""
    n = max(0, int(independent_sources))
    return _clamp(1.0 - (0.5 ** n)) if n > 0 else 0.0


def confidence(quality: float, fresh: float, corrob: float) -> float:
    return _clamp(0.5 * quality + 0.2 * fresh + 0.3 * corrob)


def score(*, source_type="", confidence_base=None, publication_date=None,
          corroborating_sources=0, contradicted=False, has_evidence=True,
          now: date | None = None) -> VerificationResult:
    """Core pure scorer. `corroborating_sources` = number of ADDITIONAL
    independent sources beyond the primary one."""
    if not has_evidence:
        return VerificationResult(0.0, 0.0, 0.0, 0.0, "NOT_FOUND")

    q = source_quality(source_type, confidence_base)
    f = freshness(publication_date, now=now)
    c = corroboration(corroborating_sources)
    conf = confidence(q, f, c)

    if contradicted:
        status = "CONTRADICTED"
    elif q <= INSUFFICIENT_MAX_QUALITY and corroborating_sources == 0:
        status = "INSUFFICIENT_EVIDENCE"
    elif c >= VERIFIED_MIN_CORROBORATION and conf >= VERIFIED_MIN_CONFIDENCE:
        status = "VERIFIED"
    elif q >= PARTIAL_MIN_QUALITY:
        status = "PARTIAL"
    else:
        status = "UNVERIFIED"

    return VerificationResult(round(q, 4), round(f, 4), round(c, 4),
                              round(conf, 4), status)


def verify_evidence(evidence, *, corroborating_sources=None, contradicted=False,
                    now: date | None = None, save=True) -> VerificationResult:
    """Score a harvester.Evidence instance and write the results back.

    corroborating_sources defaults to evidence.corroboration_count. Source
    quality prefers the attached Source.confidence_base, else the source_type
    fallback (derived from the Source or any single EvidenceSourceRef).
    """
    src = getattr(evidence, "source", None)
    conf_base = getattr(src, "confidence_base", None) if src else None
    source_type = getattr(src, "source_type", "") if src else ""
    if not source_type:
        ref = evidence.source_refs.first() if evidence.pk else None
        source_type = getattr(ref, "source_type", "") if ref else ""

    n = (corroborating_sources if corroborating_sources is not None
         else getattr(evidence, "corroboration_count", 0))

    result = score(
        source_type=source_type, confidence_base=conf_base,
        publication_date=evidence.publication_date,
        corroborating_sources=n, contradicted=contradicted,
        has_evidence=True, now=now,
    )

    evidence.source_quality_score = result.source_quality_score
    evidence.freshness_score = result.freshness_score
    evidence.corroboration_score = result.corroboration_score
    evidence.confidence_score = result.confidence_score
    evidence.confidence = result.confidence_score
    evidence.verification_status = result.verification_status
    if save and evidence.pk:
        evidence.save(update_fields=[
            "source_quality_score", "freshness_score", "corroboration_score",
            "confidence_score", "confidence", "verification_status",
        ])
    return result
