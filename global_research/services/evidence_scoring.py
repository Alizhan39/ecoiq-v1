"""
global_research/services/evidence_scoring.py — deterministic ClaimAssessment
scoring. Adapts (does not fork) `harvester.verification`'s pure
`freshness()`/`corroboration()` functions rather than re-deriving that
arithmetic. See docs/research_evidence_methodology.md §3 for the full
formula and docs/adr/ADR-global-research-engine.md decision 3.
"""
from harvester.verification import corroboration as harvester_corroboration
from harvester.verification import freshness as harvester_freshness

FORMULA_VERSION = '1.0.0'

TIER_AUTHORITY_SCORE = {'A': 95.0, 'B': 75.0, 'C': 50.0, 'D': 20.0}

WEIGHTS = {
    'source_authority': 0.25,
    'methodological_quality': 0.15,
    'independence': 0.20,
    'reproducibility': 0.15,
    'recency': 0.10,
    'applicability': 0.15,
}
CONTRADICTION_PENALTY_PER_UNRESOLVED = 15.0


def _source_authority_score(source):
    return TIER_AUTHORITY_SCORE.get(source.evidence_tier, TIER_AUTHORITY_SCORE['D'])


def _methodological_quality_score(source):
    if source.independently_reproduced:
        return 80.0
    if source.source_type in ('peer_reviewed_paper', 'conference_paper'):
        return 55.0
    return 35.0


def _independence_score(claim):
    return 10.0 if claim.vendor_provided else 90.0


def _reproducibility_score(independent_corroboration_count):
    return round(harvester_corroboration(independent_corroboration_count) * 100, 2)


def _recency_score(source):
    return round(harvester_freshness(source.publication_date) * 100, 2)


def _applicability_score(claim, target_conditions):
    """A claim without stated conditions is never treated as universally
    applicable — see docs/research_evidence_methodology.md §2."""
    if not claim.conditions:
        return 0.0 if target_conditions else 50.0
    if not target_conditions:
        return 50.0
    matches = sum(1 for k, v in target_conditions.items() if claim.conditions.get(k) == v)
    if matches == len(target_conditions):
        return 100.0
    return 50.0 if matches > 0 else 0.0


def count_independent_corroborations(claim):
    """Other, independently-sourced claims for the same (subject,
    predicate) — never counting the claim's own source."""
    from global_research.models import ResearchClaim

    return (
        ResearchClaim.objects.filter(
            mission_id=claim.mission_id, subject=claim.subject, predicate=claim.predicate, vendor_provided=False,
        )
        .exclude(pk=claim.pk)
        .count()
    )


def score_claim(claim, target_conditions=None, unresolved_contradiction_count=0, save=True):
    """Computes and persists a ClaimAssessment for `claim`. Idempotent
    (update_or_create). Also updates claim.confidence/verified — `verified`
    is only ever set True from an independent corroboration, never from
    the claim's own source (docs/research_evidence_methodology.md §2)."""
    from global_research.models import ClaimAssessment

    source = claim.source
    source_authority = _source_authority_score(source)
    methodological_quality = _methodological_quality_score(source)
    independence = _independence_score(claim)
    independent_corroborations = count_independent_corroborations(claim)
    reproducibility = _reproducibility_score(independent_corroborations)
    recency = _recency_score(source)
    applicability = _applicability_score(claim, target_conditions)
    contradiction_penalty = CONTRADICTION_PENALTY_PER_UNRESOLVED * unresolved_contradiction_count

    overall = (
        WEIGHTS['source_authority'] * source_authority
        + WEIGHTS['methodological_quality'] * methodological_quality
        + WEIGHTS['independence'] * independence
        + WEIGHTS['reproducibility'] * reproducibility
        + WEIGHTS['recency'] * recency
        + WEIGHTS['applicability'] * applicability
        - contradiction_penalty
    )
    overall = max(0.0, min(100.0, round(overall, 2)))

    rationale = (
        f'source_authority={source_authority} (tier {source.evidence_tier}), '
        f'methodological_quality={methodological_quality}, '
        f'independence={independence} (vendor_provided={claim.vendor_provided}), '
        f'reproducibility={reproducibility} ({independent_corroborations} independent corroboration(s)), '
        f'recency={recency}, applicability={applicability}, '
        f'contradiction_penalty={contradiction_penalty}. Overall={overall}.'
    )

    assessment, _ = ClaimAssessment.objects.update_or_create(
        claim=claim,
        defaults=dict(
            source_authority_score=source_authority, methodological_quality_score=methodological_quality,
            independence_score=independence, reproducibility_score=reproducibility, recency_score=recency,
            applicability_score=applicability, contradiction_penalty=contradiction_penalty,
            overall_evidence_score=overall, rationale=rationale, formula_version=FORMULA_VERSION,
        ),
    )
    claim.confidence = overall
    claim.verified = independent_corroborations >= 1
    if save:
        claim.save(update_fields=['confidence', 'verified', 'updated_at'])
    return assessment
