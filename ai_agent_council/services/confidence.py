"""
ai_agent_council/services/confidence.py — deterministic confidence calibration.

Every confidence score in the Council must be explainable: a plain-arithmetic
breakdown that any agent's stated confidence can be reproduced from, never a
number an agent (or a person) simply asserts.

The formula below is deliberately built to reproduce the reference worked
example exactly:

    Evidence coverage: 90%, Source quality: 86%, Consistency: 82%,
    Missing data penalty: -9%, Contradiction penalty: -7%,
    Historical reliability adjustment: +3%  ->  Final confidence: 79%

Evidence coverage anchors the score. Missing-data and contradiction
penalties are subtracted directly. Historical reliability is added
directly. Source quality and consistency both describe how trustworthy the
underlying evidence is, so half of their gap is folded in as a secondary
signal (source quality outpacing consistency nudges confidence up a little;
consistency outpacing source quality nudges it down).
"""

QUALITY_CONSISTENCY_WEIGHT = 0.5


def build_confidence_breakdown(evidence_coverage, source_quality, consistency,
                                missing_data_penalty, contradiction_penalty,
                                historical_reliability_adjustment):
    """
    All inputs are 0-100 numbers. `missing_data_penalty` and
    `contradiction_penalty` are non-negative magnitudes (points deducted).
    `historical_reliability_adjustment` may be positive or negative.
    Returns the canonical breakdown dict stored verbatim by both
    AgentTask.confidence_breakdown and CouncilDecision.confidence_breakdown.
    """
    quality_consistency_adjustment = QUALITY_CONSISTENCY_WEIGHT * (source_quality - consistency)

    raw_final = (
        evidence_coverage
        - missing_data_penalty
        - contradiction_penalty
        + historical_reliability_adjustment
        + quality_consistency_adjustment
    )
    final = max(0, min(100, round(raw_final)))

    explanation = [
        f'Evidence coverage starts the score at {evidence_coverage}%.',
        f'Missing data penalty subtracts {missing_data_penalty} points.',
        f'Contradiction penalty subtracts {contradiction_penalty} points.',
        f'Historical reliability adjusts the score by {historical_reliability_adjustment:+g} points.',
        (
            f'Source quality ({source_quality}%) vs consistency ({consistency}%) contributes '
            f'{quality_consistency_adjustment:+g} points.'
        ),
        f'Final confidence: {final}%.',
    ]

    return {
        'evidence_coverage': evidence_coverage,
        'source_quality': source_quality,
        'consistency': consistency,
        'missing_data_penalty': missing_data_penalty,
        'contradiction_penalty': contradiction_penalty,
        'historical_reliability_adjustment': historical_reliability_adjustment,
        'final': final,
        'explanation': explanation,
    }
