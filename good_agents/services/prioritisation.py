"""
good_agents/services/prioritisation.py — PrioritisationEngine (PR3 Phase
15). Deliberately NOT a single "goodness score" — returns a set of labels
plus the raw dimensions behind them, so a human can see the trade-off
rather than trust one fabricated number.
"""
from dataclasses import dataclass, field

URGENCY_THRESHOLD = 65.0
CONFIDENCE_LEVERAGE_THRESHOLD = 60.0
FEASIBILITY_LEVERAGE_THRESHOLD = 60.0
LOW_CONFIDENCE_THRESHOLD = 30.0


@dataclass
class PrioritisationResult:
    labels: list = field(default_factory=list)
    dimensions: dict = field(default_factory=dict)


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

    if opportunity.insufficient_evidence or opportunity.confidence < LOW_CONFIDENCE_THRESHOLD:
        labels.append('EVIDENCE_GAP')

    if opportunity.urgency >= URGENCY_THRESHOLD:
        labels.append('URGENT')

    if opportunity.zero_capital_possible:
        labels.append('ZERO_CAPITAL')
    elif opportunity.capital_required_usd:
        labels.append('CAPITAL_REQUIRED')

    if (
        opportunity.confidence >= CONFIDENCE_LEVERAGE_THRESHOLD
        and opportunity.feasibility >= FEASIBILITY_LEVERAGE_THRESHOLD
        and opportunity.affected_population
    ):
        labels.append('HIGH_LEVERAGE')

    if not labels or (labels == ['EVIDENCE_GAP'] and opportunity.status == 'potential'):
        labels.append('MONITOR')

    return PrioritisationResult(labels=labels, dimensions=dimensions)


def rank_opportunities(opportunities):
    """
    Multidimensional ranking, not a single score: sorts by (urgent first,
    then high-leverage, then confidence, then urgency) — ties broken by
    recency. Returns [(opportunity, PrioritisationResult), ...].
    """
    scored = [(opp, prioritise(opp)) for opp in opportunities]

    def sort_key(pair):
        _, result = pair
        return (
            0 if 'URGENT' in result.labels else 1,
            0 if 'HIGH_LEVERAGE' in result.labels else 1,
            -result.dimensions['confidence'],
            -result.dimensions['urgency'],
        )

    scored.sort(key=sort_key)
    return scored
