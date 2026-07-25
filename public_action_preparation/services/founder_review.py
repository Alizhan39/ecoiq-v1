"""
public_action_preparation/services/founder_review.py — Phase 17: the one
real decision this app exists to gate. `compute_recommendation()` is a
pure, deterministic READ; `record_decision()` is the only thing that
makes a decision real, and always requires a real human actor — AI must
never call it (Phase 16's own explicit rule; no "ai_generated" path
exists anywhere in this module).
"""
from django.utils import timezone

from public_action_preparation.models import FounderActionDecision
from public_action_preparation.services.readiness import compute_action_readiness


class FounderActionReviewNotAllowedError(Exception):
    pass


def compute_recommendation(opportunity):
    """Returns (recommendation, reasons) — never a mysterious aggregate score."""
    reasons = []
    readiness = compute_action_readiness(opportunity)

    if readiness == 'rejected':
        reasons.append('This candidate was decided as no_action.')
        return 'do_not_proceed', reasons
    if readiness == 'blocked':
        decision = getattr(opportunity, 'action_type_decision', None)
        if decision and decision.action_type == 'refer_to_existing_service':
            reasons.append('refer_to_existing_service is blocked without a real, evidenced beneficiary — do not fabricate one.')
        else:
            reasons.append('The verified official process is expired/closed — do not proceed via that process.')
        return 'do_not_proceed', reasons
    if readiness in ('not_assessed', 'needs_evidence', 'needs_responsible_body', 'needs_process_verification',
                      'needs_action_definition', 'needs_ethics_review', 'ready_for_content_review'):
        reasons.append(f'Readiness is currently {readiness!r} — revise/complete before this can reach Founder Action Review.')
        return 'revise', reasons

    reasons.append('Evidence, responsible body, process verification (where relevant), ethics review, and content review all passed.')
    return 'proceed', reasons


def record_decision(opportunity, decision_value, *, actor, content_draft=None, rationale=''):
    if actor is None:
        raise FounderActionReviewNotAllowedError('A founder action decision requires a real actor.')
    if decision_value not in dict(FounderActionDecision.DECISION_CHOICES):
        raise FounderActionReviewNotAllowedError(f'Unknown decision {decision_value!r}.')
    founder_decision, _ = FounderActionDecision.objects.get_or_create(opportunity=opportunity)
    founder_decision.decision = decision_value
    founder_decision.content_draft = content_draft
    founder_decision.decided_by = actor
    founder_decision.decided_at = timezone.now()
    founder_decision.rationale = rationale
    founder_decision.save()
    return founder_decision
