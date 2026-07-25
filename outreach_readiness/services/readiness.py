"""
outreach_readiness/services/readiness.py — Phase 14: the deterministic
readiness ladder. Deliberately NOT a stored field — always recomputed
from the real rows that exist, so it can never drift from what has
genuinely been completed (the same discipline PR11's blockers()/
next_best_action() established).
"""
from outreach_readiness.models import SUITABILITY_TERMINAL_REJECTED_STATES
from outreach_readiness.services.route import active_route

READINESS_LABELS = {
    'not_assessed': 'Not assessed', 'needs_evidence': 'Needs evidence', 'needs_recipient': 'Needs recipient',
    'needs_route': 'Needs route', 'needs_ask': 'Needs ask', 'needs_risk_review': 'Needs risk review',
    'ready_for_message_review': 'Ready for message review', 'ready_for_founder_review': 'Ready for founder review',
    'blocked': 'Blocked', 'rejected': 'Rejected',
}


def compute_readiness_state(assessment):
    """
    Never returns READY_FOR_FOUNDER_REVIEW unless risk review has
    genuinely passed and a dry run genuinely passed — no shortcut path.

    `not_assessed` covers a fresh assessment with no verdict yet
    (`suitability_state == 'not_ready'`) REGARDLESS of what other fields
    happen to be filled in — a candidate isn't "needs recipient" just
    because no organisation is resolved if no one has even started
    reviewing it yet. Every state below this point in the function only
    fires once a real SUITABLE/POTENTIALLY_SUITABLE verdict exists.
    """
    if assessment is None or assessment.suitability_state == 'not_ready':
        return 'not_assessed'
    if assessment.suitability_state in SUITABILITY_TERMINAL_REJECTED_STATES:
        return 'rejected'

    opportunity = assessment.opportunity
    if opportunity.insufficient_evidence or not opportunity.evidence_refs:
        return 'needs_evidence'
    if assessment.organisation is None:
        return 'needs_recipient'

    if active_route(assessment) is None:
        return 'needs_route'
    if not assessment.minimum_viable_ask:
        return 'needs_ask'

    latest = assessment.message_versions.order_by('-version_number').first()
    if latest is None or latest.approval_status == 'invalidated':
        return 'needs_risk_review'

    risk_review = getattr(latest, 'risk_review', None)
    if risk_review is None or not risk_review.all_passed:
        return 'needs_risk_review'

    if latest.approval_status == 'draft':
        return 'ready_for_message_review'

    latest_dry_run = latest.dry_runs.order_by('-run_at').first()
    if latest_dry_run is None or latest_dry_run.validation_result != 'pass':
        return 'blocked'

    return 'ready_for_founder_review'
