"""
outreach_readiness/services/candidate_review.py — Phase 1: compares a
bounded set of real GoodOpportunity rows for first-outreach suitability.
Pure read; scoring is a simple, explainable count of real yes/no answers
already recorded — never a mysterious aggregate AI score.
"""
from outreach_readiness.services.readiness import compute_readiness_state


def candidate_summary(opportunity):
    """One row for the candidate comparison table — real data only, no invented prose."""
    assessment = getattr(opportunity, 'outreach_assessment', None)
    organisation = assessment.organisation if assessment else None
    responsible_party = opportunity.responsible_parties.order_by('-confidence').first()
    if organisation is None and responsible_party is not None:
        organisation = responsible_party.organisation

    return {
        'opportunity': opportunity,
        'assessment': assessment,
        'organisation': organisation,
        'suitability_state': assessment.get_suitability_state_display() if assessment else 'Not assessed',
        'suitability_state_raw': assessment.suitability_state if assessment else 'not_ready',
        'recipient_role': assessment.get_recipient_role_display() if assessment and assessment.recipient_role else 'Not classified',
        'readiness_state': compute_readiness_state(assessment) if assessment else 'not_assessed',
        'is_sensitive': assessment.is_sensitive if assessment else False,
        'has_evidence': bool(opportunity.evidence_refs) and not opportunity.insufficient_evidence,
    }


def candidate_review_list(opportunities):
    return [candidate_summary(o) for o in opportunities]
