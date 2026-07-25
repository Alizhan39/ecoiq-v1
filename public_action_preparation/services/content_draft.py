"""
public_action_preparation/services/content_draft.py — Phase 11-12, 15:
process-specific content drafting. One consistent versioning discipline
(editing after founder approval never mutates the approved row — it
creates the next version and invalidates the old one), but the actual
content shape depends on `content_type`: a consultation response is
never the same generic template as a data request (Phase 11's own
explicit instruction — "do not use one generic email template for
every action type").

`prepare_outreach` decisions do NOT use this module at all — they hand
off to outreach_readiness.services.message, PR12's own unmodified
versioning, so there is never a second outreach-drafting mechanism.
"""
from django.utils import timezone

from public_action_preparation.models import ActionContentDraft


class ContentDraftNotAllowedError(Exception):
    pass


# Action types this module is allowed to draft content for — prepare_outreach
# and no_action are deliberately excluded (Phase 11/19's own boundaries).
DRAFTABLE_ACTION_TYPES = frozenset({
    'use_official_public_process', 'submit_consultation_response', 'request_programme_clarification',
    'refer_to_existing_service', 'request_public_data', 'surface_funding_route', 'propose_zero_capital_connection',
})

ACTION_TYPE_TO_CONTENT_TYPE = {
    'submit_consultation_response': 'consultation_response',
    'use_official_public_process': 'consultation_response',
    'refer_to_existing_service': 'referral_brief',
    'request_programme_clarification': 'clarification_question',
    'request_public_data': 'data_request',
    'surface_funding_route': 'connection_proposal',
    'propose_zero_capital_connection': 'connection_proposal',
}


def invalidate_version(version, *, reason=''):
    version.approval_status = 'invalidated'
    version.invalidated_at = timezone.now()
    version.invalidated_reason = reason
    version.save(update_fields=['approval_status', 'invalidated_at', 'invalidated_reason'])
    return version


def create_content_draft(decision, *, actor, content_type=None, subject='', fact_points=None, inference_points=None,
                          specific_recommendation='', limitations='', source_links=None, body_text='',
                          required_fields_missing=None, change_summary=''):
    """
    Phase 12/13's own content rules (consultation response must include
    specific evidence + local implication + recommendation + limitations
    + source links; a referral brief must mark missing beneficiary
    fields rather than omit them) are enforced by the caller populating
    these real structured fields — this function only persists and
    versions what it is given, never invents filler for a blank field.
    """
    if actor is None:
        raise ContentDraftNotAllowedError('Drafting action content requires a real actor.')
    if decision.action_type not in DRAFTABLE_ACTION_TYPES:
        raise ContentDraftNotAllowedError(
            f'{decision.get_action_type_display()!r} is not a content-draftable action type in this app — '
            f'prepare_outreach uses outreach_readiness, no_action has no content.'
        )

    latest = decision.content_drafts.order_by('-version_number').first()
    next_version = (latest.version_number + 1) if latest else 1
    if latest is not None and latest.approval_status == 'founder_approved':
        invalidate_version(latest, reason=f'Superseded by version {next_version}.')

    return ActionContentDraft.objects.create(
        decision=decision, version_number=next_version,
        content_type=content_type or ACTION_TYPE_TO_CONTENT_TYPE.get(decision.action_type, 'other'),
        subject=subject, fact_points=fact_points or [], inference_points=inference_points or [],
        specific_recommendation=specific_recommendation, limitations=limitations, source_links=source_links or [],
        body_text=body_text, required_fields_missing=required_fields_missing or [],
        editor=actor, change_summary=change_summary,
    )


def mark_reviewed(draft, *, actor):
    if actor is None:
        raise ContentDraftNotAllowedError('Content review requires a real actor.')
    if draft.approval_status == 'invalidated':
        raise ContentDraftNotAllowedError('Cannot review an invalidated draft — create a new version.')
    draft.approval_status = 'reviewed'
    draft.reviewed_by = actor
    draft.reviewed_at = timezone.now()
    draft.save(update_fields=['approval_status', 'reviewed_by', 'reviewed_at'])
    return draft


def founder_approve(draft, *, actor):
    if actor is None:
        raise ContentDraftNotAllowedError('Founder content approval requires a real actor.')
    if draft.approval_status == 'invalidated':
        raise ContentDraftNotAllowedError('Cannot approve an invalidated draft — create a new version.')
    if draft.content_type == 'referral_brief' and draft.required_fields_missing:
        raise ContentDraftNotAllowedError(
            f'Cannot founder-approve a referral brief with missing required fields: {", ".join(draft.required_fields_missing)}.'
        )
    draft.approval_status = 'founder_approved'
    draft.founder_approved_by = actor
    draft.founder_approved_at = timezone.now()
    draft.save(update_fields=['approval_status', 'founder_approved_by', 'founder_approved_at'])
    return draft


def render_preview(draft):
    """Phase 18 dry-run preview — every field that would be submitted, exactly as stored, never re-derived."""
    return {
        'content_type': draft.get_content_type_display(),
        'subject': draft.subject,
        'facts': draft.fact_points,
        'inferences': draft.inference_points,
        'recommendation': draft.specific_recommendation,
        'limitations': draft.limitations,
        'source_links': draft.source_links,
        'body_text': draft.body_text,
        'missing_fields': draft.required_fields_missing,
        'word_count': draft.word_count(),
    }
