"""
good_agents/services/prioritisation.py — PrioritisationEngine (PR3 Phase
15). Deliberately NOT a single "goodness score" — returns a set of labels
plus the raw dimensions behind them, so a human can see the trade-off
rather than trust one fabricated number.

PR4 Phase 12 adds a deterministic, fully-documented feedback adjustment:
repeated FALSE_POSITIVE reviews for a theme/sector pattern reduce the
adjusted confidence used for ranking (never the opportunity's own stored
`confidence` field — this only affects the transient PrioritisationResult);
repeated USEFUL/HIGH_PRIORITY reviews give a modest boost. This is
explicitly NOT opaque ML training — the exact rule and every adjustment
applied is visible in `PrioritisationResult.feedback_reasons`.
"""
from dataclasses import dataclass, field

URGENCY_THRESHOLD = 65.0
CONFIDENCE_LEVERAGE_THRESHOLD = 60.0
FEASIBILITY_LEVERAGE_THRESHOLD = 60.0
LOW_CONFIDENCE_THRESHOLD = 30.0

# Feedback adjustment thresholds/magnitudes (Phase 12) — deterministic,
# configurable constants, not a learned model.
FALSE_POSITIVE_PATTERN_THRESHOLD = 2
FALSE_POSITIVE_CONFIDENCE_PENALTY = 15.0
USEFUL_PATTERN_THRESHOLD = 2
USEFUL_CONFIDENCE_BOOST = 5.0
NOT_USEFUL_DECISIONS = frozenset({'not_useful', 'false_positive', 'not_actionable', 'duplicate', 'rejected'})
USEFUL_DECISIONS = frozenset({'useful', 'high_priority', 'approved'})


@dataclass
class PrioritisationResult:
    labels: list = field(default_factory=list)
    dimensions: dict = field(default_factory=dict)
    feedback_reasons: list = field(default_factory=list)


def _pattern_feedback(opportunity):
    """
    Looks at prior HumanReviewDecision rows for opportunities sharing the
    same (theme, sector) pattern as `opportunity` — a simple, transparent,
    deterministic proxy for "this kind of signal has been reviewed before."
    Returns (adjustment: float, reasons: list[str]).
    """
    from good_agents.models import HumanReviewDecision

    if not opportunity.theme:
        return 0.0, []

    decisions = HumanReviewDecision.objects.filter(
        opportunity__theme=opportunity.theme,
    )
    if opportunity.sector:
        decisions = decisions.filter(opportunity__sector__iexact=opportunity.sector)
    decision_values = list(decisions.values_list('decision', flat=True))

    false_positive_count = sum(1 for d in decision_values if d in NOT_USEFUL_DECISIONS)
    useful_count = sum(1 for d in decision_values if d in USEFUL_DECISIONS)

    adjustment = 0.0
    reasons = []
    if false_positive_count >= FALSE_POSITIVE_PATTERN_THRESHOLD:
        adjustment -= FALSE_POSITIVE_CONFIDENCE_PENALTY
        reasons.append(
            f'{false_positive_count} prior not-useful/false-positive reviews for theme={opportunity.theme!r}'
            f'{f", sector={opportunity.sector!r}" if opportunity.sector else ""} — '
            f'confidence reduced by {FALSE_POSITIVE_CONFIDENCE_PENALTY:.0f} for ranking purposes.'
        )
    if useful_count >= USEFUL_PATTERN_THRESHOLD:
        adjustment += USEFUL_CONFIDENCE_BOOST
        reasons.append(
            f'{useful_count} prior useful/high-priority reviews for the same pattern — '
            f'confidence boosted by {USEFUL_CONFIDENCE_BOOST:.0f} for ranking purposes.'
        )
    return adjustment, reasons


def prioritise(opportunity):
    labels = []
    dimensions = {
        'urgency': opportunity.urgency,
        'confidence': opportunity.confidence,
        'feasibility': opportunity.feasibility,
        'capital_required_usd': opportunity.capital_required_usd,
        'zero_capital_possible': opportunity.zero_capital_possible,
        'insufficient_evidence': opportunity.insufficient_evidence,
    }

    feedback_adjustment, feedback_reasons = _pattern_feedback(opportunity)
    # A ranking-only view — never mutates opportunity.confidence itself,
    # which stays the honest, evidence-derived figure from the Evidence Gate.
    adjusted_confidence = max(0.0, min(100.0, opportunity.confidence + feedback_adjustment))
    dimensions['adjusted_confidence'] = adjusted_confidence
    dimensions['feedback_adjustment'] = feedback_adjustment

    if opportunity.insufficient_evidence or adjusted_confidence < LOW_CONFIDENCE_THRESHOLD:
        labels.append('EVIDENCE_GAP')

    if opportunity.urgency >= URGENCY_THRESHOLD:
        labels.append('URGENT')

    if opportunity.zero_capital_possible:
        labels.append('ZERO_CAPITAL')
    elif opportunity.capital_required_usd:
        labels.append('CAPITAL_REQUIRED')

    if (
        adjusted_confidence >= CONFIDENCE_LEVERAGE_THRESHOLD
        and opportunity.feasibility >= FEASIBILITY_LEVERAGE_THRESHOLD
        and opportunity.affected_population
    ):
        labels.append('HIGH_LEVERAGE')

    if not labels or (labels == ['EVIDENCE_GAP'] and opportunity.status == 'potential'):
        labels.append('MONITOR')

    return PrioritisationResult(labels=labels, dimensions=dimensions, feedback_reasons=feedback_reasons)


def rank_opportunities(opportunities):
    """
    Multidimensional ranking, not a single score: sorts by (urgent first,
    then high-leverage, then feedback-adjusted confidence, then urgency) —
    ties broken by recency. Returns [(opportunity, PrioritisationResult), ...].
    """
    scored = [(opp, prioritise(opp)) for opp in opportunities]

    def sort_key(pair):
        _, result = pair
        return (
            0 if 'URGENT' in result.labels else 1,
            0 if 'HIGH_LEVERAGE' in result.labels else 1,
            -result.dimensions['adjusted_confidence'],
            -result.dimensions['urgency'],
        )

    scored.sort(key=sort_key)
    return scored
