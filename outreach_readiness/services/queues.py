"""outreach_readiness/services/queues.py — Phase 22: Command Centre queues. Real counts only, no vanity metrics."""
from outreach_readiness.services.readiness import compute_readiness_state


def command_centre_queues(opportunities):
    needs_suitability_review, needs_recipient_resolution = [], []
    needs_route_verification, needs_risk_review = [], []
    needs_message_review, ready_for_founder_review, rejected_for_outreach = [], [], []

    for opportunity in opportunities:
        assessment = getattr(opportunity, 'outreach_assessment', None)
        if assessment is None:
            needs_suitability_review.append(opportunity)
            continue
        state = compute_readiness_state(assessment)
        if state == 'rejected':
            rejected_for_outreach.append(opportunity)
        elif state == 'not_assessed':
            needs_suitability_review.append(opportunity)
        elif state in ('needs_evidence', 'needs_recipient'):
            needs_recipient_resolution.append(opportunity)
        elif state in ('needs_route', 'needs_ask'):
            needs_route_verification.append(opportunity)
        elif state == 'needs_risk_review':
            needs_risk_review.append(opportunity)
        elif state == 'ready_for_message_review':
            needs_message_review.append(opportunity)
        elif state == 'ready_for_founder_review':
            ready_for_founder_review.append(opportunity)

    return {
        'needs_suitability_review': needs_suitability_review,
        'needs_recipient_resolution': needs_recipient_resolution,
        'needs_route_verification': needs_route_verification,
        'needs_risk_review': needs_risk_review,
        'needs_message_review': needs_message_review,
        'ready_for_founder_review': ready_for_founder_review,
        'rejected_for_outreach': rejected_for_outreach,
    }
