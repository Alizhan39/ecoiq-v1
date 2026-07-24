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

# PR5 Phase 24 — learning from real ACTION outcomes (not just human review
# decisions). Same discipline as Phase 12 above: deterministic, documented,
# ranking-only, never mutates the opportunity's own stored fields.
NOT_ACTIONABLE_GATE_STATES = frozenset({'rejected', 'not_actionable'})
NOT_ACTIONABLE_PATTERN_THRESHOLD = 2
NOT_ACTIONABLE_CONFIDENCE_PENALTY = 10.0
SUCCESSFUL_ZERO_CAPITAL_PATTERN_THRESHOLD = 2
SUCCESSFUL_ZERO_CAPITAL_CONFIDENCE_BOOST = 5.0
DECLINED_CONNECTION_PATTERN_THRESHOLD = 2
DECLINED_CONNECTION_CONFIDENCE_PENALTY = 8.0


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


def _action_outcome_feedback(opportunity):
    """
    PR5 Phase 24 — looks at prior ACTION outcomes (not human review
    decisions) for opportunities sharing the same theme: repeated
    rejected/not-actionable action gates reduce ranking confidence;
    repeated completed zero-capital pathways boost it; repeated declined
    connection candidates reduce it (a proxy for "matches for this theme
    keep turning out to be poor-fit — require stronger compatibility").
    Returns (adjustment: float, reasons: list[str]).
    """
    from good_agents.models import ActionGate, ActionPathway, ConnectionCandidate

    if not opportunity.theme:
        return 0.0, []

    adjustment = 0.0
    reasons = []

    not_actionable_count = ActionGate.objects.filter(
        opportunity__theme=opportunity.theme, current_state__in=NOT_ACTIONABLE_GATE_STATES,
    ).exclude(opportunity=opportunity).count()
    if not_actionable_count >= NOT_ACTIONABLE_PATTERN_THRESHOLD:
        adjustment -= NOT_ACTIONABLE_CONFIDENCE_PENALTY
        reasons.append(
            f'{not_actionable_count} prior rejected/not-actionable action gates for theme={opportunity.theme!r} — '
            f'confidence reduced by {NOT_ACTIONABLE_CONFIDENCE_PENALTY:.0f} for ranking purposes.'
        )

    successful_zero_capital_count = ActionPathway.objects.filter(
        opportunity__theme=opportunity.theme, capital_required='no', status='completed',
    ).exclude(opportunity=opportunity).count()
    if successful_zero_capital_count >= SUCCESSFUL_ZERO_CAPITAL_PATTERN_THRESHOLD:
        adjustment += SUCCESSFUL_ZERO_CAPITAL_CONFIDENCE_BOOST
        reasons.append(
            f'{successful_zero_capital_count} prior completed zero-capital pathways for the same theme — '
            f'confidence boosted by {SUCCESSFUL_ZERO_CAPITAL_CONFIDENCE_BOOST:.0f} for ranking purposes.'
        )

    declined_connection_count = ConnectionCandidate.objects.filter(
        resource_match__need__opportunity__theme=opportunity.theme, status='declined',
    ).exclude(resource_match__need__opportunity=opportunity).count()
    if declined_connection_count >= DECLINED_CONNECTION_PATTERN_THRESHOLD:
        adjustment -= DECLINED_CONNECTION_CONFIDENCE_PENALTY
        reasons.append(
            f'{declined_connection_count} prior declined connection candidates for the same theme — '
            f'confidence reduced by {DECLINED_CONNECTION_CONFIDENCE_PENALTY:.0f}; future matches for this '
            f'theme should require stronger compatibility before being surfaced as ready.'
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

    review_adjustment, review_reasons = _pattern_feedback(opportunity)
    action_adjustment, action_reasons = _action_outcome_feedback(opportunity)
    feedback_adjustment = review_adjustment + action_adjustment
    feedback_reasons = review_reasons + action_reasons
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
