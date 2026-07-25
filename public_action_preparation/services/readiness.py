"""
public_action_preparation/services/readiness.py — Phase 15: the
deterministic action-readiness ladder. Deliberately NOT a stored field —
always recomputed from the real rows that exist (same discipline as
outreach_readiness.services.readiness.compute_readiness_state()).
READY_FOR_FOUNDER_ACTION_REVIEW is never returned unless ethics review
has genuinely passed and, for content-draftable action types, a real
founder-approved content draft exists.
"""
from public_action_preparation.models import ACTION_TYPES_REQUIRING_PROCESS_VERIFICATION
from public_action_preparation.services.content_draft import DRAFTABLE_ACTION_TYPES

READINESS_LABELS = {
    'not_assessed': 'Not assessed', 'needs_evidence': 'Needs evidence',
    'needs_process_verification': 'Needs process verification', 'needs_responsible_body': 'Needs responsible body',
    'needs_action_definition': 'Needs action definition', 'needs_ethics_review': 'Needs ethics review',
    'ready_for_content_review': 'Ready for content review', 'ready_for_founder_action_review': 'Ready for Founder Action Review',
    'blocked': 'Blocked', 'rejected': 'Rejected',
}


def compute_action_readiness(opportunity):
    decision = getattr(opportunity, 'action_type_decision', None)
    if decision is None or not decision.action_type:
        return 'not_assessed'
    if decision.action_type == 'no_action':
        return 'rejected'

    if opportunity.insufficient_evidence or not opportunity.evidence_refs:
        return 'needs_evidence'

    candidate = getattr(opportunity, 'pilot_candidate_assessment', None)
    if candidate is None or not candidate.organisation_roles.filter(confirmed=True).exists():
        return 'needs_responsible_body'

    if decision.action_type == 'refer_to_existing_service' and not decision.has_real_beneficiary:
        return 'blocked'

    if decision.action_type in ACTION_TYPES_REQUIRING_PROCESS_VERIFICATION:
        process = getattr(opportunity, 'verified_official_process', None)
        if process is None or process.status == 'unknown':
            return 'needs_process_verification'
        if process.status == 'expired':
            return 'blocked'

    ethics = getattr(opportunity, 'ethics_review', None)
    if ethics is None or not ethics.all_passed:
        return 'needs_ethics_review'

    if decision.action_type == 'prepare_outreach':
        # Handed off to outreach_readiness entirely — this app's own
        # readiness stops at "ethics passed, ready to hand off."
        return 'ready_for_founder_action_review'

    if decision.action_type not in DRAFTABLE_ACTION_TYPES:
        return 'needs_action_definition'

    latest_draft = decision.content_drafts.order_by('-version_number').first()
    if latest_draft is None or latest_draft.approval_status == 'invalidated':
        return 'needs_action_definition'
    if latest_draft.approval_status in ('draft', 'reviewed'):
        return 'ready_for_content_review'

    return 'ready_for_founder_action_review'
