"""
agent_runtime_model_router/services/confidence_calibration.py — never trust
raw model confidence directly.

Maps this app's richer runtime signal set (evidence quality, source count,
missing data, schema validity, unresolved disagreements, contradiction
severity, training maturity, reviewer status, safety warnings) down to the
6 parameters `ai_agent_council.services.confidence.build_confidence_breakdown`
already expects, then delegates to that function unchanged for the final
arithmetic — reusing the Council's own tested formula rather than inventing
a second, incompatible one.
"""
from ai_agent_council.services.confidence import build_confidence_breakdown

CONSISTENCY_SEVERITY_POINTS = {'none': 0, 'low': 10, 'medium': 25, 'high': 45}
CONTRADICTION_SEVERITY_POINTS = {'none': 0, 'low': 5, 'medium': 15, 'high': 30}
REVIEWER_ADJUSTMENT = {'human_reviewed': 2, 'pending': 0, 'rejected': -5}


def _maturity_adjustment(maturity_stage):
    if maturity_stage >= 6:
        return 3
    if maturity_stage >= 3:
        return 0
    return -3


def _safety_penalty(safety_findings):
    counts = {'warning': 0, 'needs_review': 0, 'blocking': 0}
    for finding in safety_findings:
        severity = finding.get('severity')
        if severity in counts:
            counts[severity] += 1
    return counts['warning'] * 1 + counts['needs_review'] * 3 + counts['blocking'] * 8


def calibrate_confidence(evidence_quality_score, num_supporting_sources, missing_data,
                          schema_valid, unresolved_disagreements, contradiction_severity,
                          maturity_stage, reviewer_status, safety_findings):
    """
    Returns the canonical confidence breakdown dict from
    build_confidence_breakdown() (evidence_coverage, source_quality,
    consistency, missing_data_penalty, contradiction_penalty,
    historical_reliability_adjustment, final, explanation).
    """
    evidence_coverage = max(0, min(100, evidence_quality_score + min(10, num_supporting_sources * 2)))
    source_quality = evidence_quality_score
    consistency = 100 - unresolved_disagreements * 15 - CONSISTENCY_SEVERITY_POINTS.get(contradiction_severity, 0)

    missing_data_penalty = len(missing_data) * 4 + (0 if schema_valid else 20)
    contradiction_penalty = (
        unresolved_disagreements * 6 + CONTRADICTION_SEVERITY_POINTS.get(contradiction_severity, 0)
    )

    historical_reliability_adjustment = (
        _maturity_adjustment(maturity_stage)
        + REVIEWER_ADJUSTMENT.get(reviewer_status, 0)
        - _safety_penalty(safety_findings)
    )

    return build_confidence_breakdown(
        evidence_coverage, source_quality, consistency,
        missing_data_penalty, contradiction_penalty, historical_reliability_adjustment,
    )
