"""
outreach_readiness/services/founder_review.py — Phase 24: the one real
decision this app exists to gate. `compute_recommendation()` is a pure,
deterministic READ — it may suggest SEND/REVISE/DO_NOT_SEND, but
`record_decision()` is the only thing that makes it real, and it always
requires an actual human actor. AI must never call `record_decision()`
(Phase 27's own explicit rule) — nothing in this module accepts an
"ai_generated" path at all, by construction.
"""
from django.utils import timezone

from outreach_readiness.models import FounderSendDecision
from outreach_readiness.services.duplicate_check import prior_outreach_history


class FounderReviewNotAllowedError(Exception):
    pass


def compute_recommendation(assessment):
    """
    Deterministic, explainable — never a mysterious aggregate score
    (Phase 1's own instruction extends naturally here). Returns
    (recommendation, reasons).
    """
    reasons = []
    if assessment.is_rejected:
        reasons.append(f'Suitability review concluded {assessment.get_suitability_state_display()}.')
        return 'do_not_send', reasons

    latest = assessment.message_versions.order_by('-version_number').first()
    if latest is None:
        reasons.append('No message version has been drafted yet.')
        return 'revise', reasons
    if latest.approval_status == 'invalidated':
        reasons.append('The latest message version was invalidated.')
        return 'revise', reasons

    risk_review = getattr(latest, 'risk_review', None)
    if risk_review is None:
        reasons.append('No risk review recorded for the latest message version.')
        return 'revise', reasons
    if not risk_review.all_passed:
        reasons.append(f'Risk review has unresolved items: {", ".join(risk_review.failed_items)}.')
        return 'revise', reasons

    latest_dry_run = latest.dry_runs.order_by('-run_at').first()
    if latest_dry_run is None:
        reasons.append('No dry run has been performed for the latest message version.')
        return 'revise', reasons
    if latest_dry_run.validation_result != 'pass':
        reasons.append(f'Latest dry run failed: {", ".join(latest_dry_run.validation_details)}.')
        return 'revise', reasons

    history = prior_outreach_history(assessment)
    if history:
        reasons.append(f'{len(history)} prior outreach record(s) found for this organisation/route — review before proceeding.')
        return 'revise', reasons

    reasons.append('Suitability, route, risk review, and dry run all passed with no prior contact history found.')
    return 'send', reasons


def record_decision(assessment, decision, *, actor, message_version, rationale=''):
    """The only sanctioned way to record a real founder decision — always a real actor, never AI, never inferred."""
    if actor is None:
        raise FounderReviewNotAllowedError('A founder send decision requires a real actor.')
    if decision not in dict(FounderSendDecision.DECISION_CHOICES):
        raise FounderReviewNotAllowedError(f'Unknown decision {decision!r}.')
    founder_decision, _ = FounderSendDecision.objects.get_or_create(assessment=assessment)
    founder_decision.decision = decision
    founder_decision.message_version = message_version
    founder_decision.decided_by = actor
    founder_decision.decided_at = timezone.now()
    founder_decision.rationale = rationale
    founder_decision.save()
    return founder_decision
