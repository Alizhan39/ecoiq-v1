"""
digital_twin/services/outcomes.py — implementation outcome tracking.

No autonomous model retraining happens anywhere in this module — recording
a MeasuredOutcome only (a) computes an honest variance (done on
MeasuredOutcome.save() itself, never hand-entered), (b) refreshes the
parent DigitalTwin's `last_observed_at` since a real new observation just
arrived, and (c) — only when a real promoted CapitalAllocationDecision
exists — updates its `verified_impact_score` from the measured accuracy.
Any deeper "model-learning" action is deliberately left as a manual
`model_learning_note` field for a human to read, per the product
requirement that no autonomous retraining occurs in this phase.
"""
from django.utils import timezone


def record_measured_outcome(action, predicted_value=None, actual_value=None, metric_definition=None, unit=None,
                             measured_at=None, evidence_references=None, confidence_impact_note='',
                             model_learning_note=''):
    from digital_twin.models import MeasuredOutcome

    outcome = MeasuredOutcome.objects.create(
        action=action, metric_definition=metric_definition, predicted_value=predicted_value,
        actual_value=actual_value, unit=unit, measured_at=measured_at or timezone.now().date(),
        evidence_references=evidence_references or [], confidence_impact_note=confidence_impact_note,
        model_learning_note=model_learning_note,
    )

    twin = action.scenario.twin
    twin.last_observed_at = timezone.now()
    twin.save(update_fields=['last_observed_at', 'updated_at'])

    _update_verified_impact_score(action)
    return outcome


def _update_verified_impact_score(action):
    """Deterministic accuracy score: 100 minus the absolute variance
    percentage, floored at 0. Only ever applied when a real
    CapitalAllocationDecision has been promoted for this scenario, and only
    from outcomes that actually have both a predicted and an actual value —
    never fabricated from a single data point pretending to be a trend."""
    decisions = [
        d.capital_allocation_decision for d in action.scenario.human_decisions.all()
        if d.capital_allocation_decision_id
    ]
    if not decisions:
        return

    outcomes_with_variance = [
        o for o in action.measured_outcomes.all() if o.variance_pct is not None
    ]
    if not outcomes_with_variance:
        return

    average_abs_variance_pct = sum(abs(o.variance_pct) for o in outcomes_with_variance) / len(outcomes_with_variance)
    accuracy_score = max(0.0, round(100 - average_abs_variance_pct, 2))

    for decision in set(decisions):
        decision.verified_impact_score = accuracy_score
        decision.save(update_fields=['verified_impact_score'])
