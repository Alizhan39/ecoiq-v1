"""
outreach_readiness/services/message.py — Phase 8-11, 15: the outreach
pack / message version. Editing after approval NEVER mutates the approved
row — it always creates the next version and invalidates the old one, so
"the founder-approved version" is always one exact, immutable row.
"""
from django.utils import timezone

from outreach_readiness.models import SUITABILITY_PROCEEDABLE_STATES, OutreachMessageVersion

TARGET_WORD_RANGE = (100, 180)


class MessageNotAllowedError(Exception):
    pass


def create_message_version(assessment, *, actor, subject, fact_points, inference_points, the_request, unknowns,
                            body_text, sender_name, sender_role, sender_organisation, reply_to,
                            value_offered='', sender_website='', signature_block='', change_summary=''):
    """
    Phase 8/9 — a message can only be drafted once the candidate has
    cleared suitability review (never draftable for a rejected candidate
    — Phase 30's "do not lower the standards merely to produce a
    message"). Creating a new version after a prior one was
    founder-approved automatically invalidates that approval (Phase 15 —
    "any edit after approval invalidates that approval").
    """
    if actor is None:
        raise MessageNotAllowedError('Drafting a message requires a real actor.')
    if assessment.suitability_state not in SUITABILITY_PROCEEDABLE_STATES:
        raise MessageNotAllowedError(
            f'Cannot draft an outreach message for a candidate assessed as '
            f'{assessment.get_suitability_state_display()!r} — suitability review must find it '
            f'SUITABLE or POTENTIALLY_SUITABLE first.'
        )

    latest = assessment.message_versions.order_by('-version_number').first()
    next_version = (latest.version_number + 1) if latest else 1
    if latest is not None and latest.approval_status == 'approved':
        invalidate_version(latest, reason=f'Superseded by version {next_version}.')

    return OutreachMessageVersion.objects.create(
        assessment=assessment, version_number=next_version, subject=subject,
        fact_points=fact_points, inference_points=inference_points, the_request=the_request, unknowns=unknowns,
        value_offered=value_offered, body_text=body_text, sender_name=sender_name, sender_role=sender_role,
        sender_organisation=sender_organisation, reply_to=reply_to, sender_website=sender_website,
        signature_block=signature_block, editor=actor, change_summary=change_summary,
    )


def mark_reviewed(version, *, actor):
    if actor is None:
        raise MessageNotAllowedError('Message review requires a real actor.')
    if version.approval_status == 'invalidated':
        raise MessageNotAllowedError('Cannot review an invalidated message version — create a new one.')
    version.approval_status = 'reviewed'
    version.reviewed_by = actor
    version.reviewed_at = timezone.now()
    version.save(update_fields=['approval_status', 'reviewed_by', 'reviewed_at'])
    return version


def founder_approve(version, *, actor):
    """
    NOT the send decision (see services/founder_review.py) — this marks
    the message CONTENT itself as the one the founder is prepared to
    consider sending. `all_risk_checks_passed` and a passing dry run are
    still separately required before Founder Send Review even shows this
    version as ready.
    """
    if actor is None:
        raise MessageNotAllowedError('Founder approval requires a real actor.')
    if version.approval_status == 'invalidated':
        raise MessageNotAllowedError('Cannot approve an invalidated message version — create a new one.')
    risk_review = getattr(version, 'risk_review', None)
    if risk_review is None or not risk_review.all_passed:
        raise MessageNotAllowedError('Cannot found-approve a message version whose risk review has not fully passed.')
    version.approval_status = 'approved'
    version.founder_approved_by = actor
    version.founder_approved_at = timezone.now()
    version.save(update_fields=['approval_status', 'founder_approved_by', 'founder_approved_at'])
    return version


def invalidate_version(version, *, reason=''):
    version.approval_status = 'invalidated'
    version.invalidated_at = timezone.now()
    version.invalidated_reason = reason
    version.save(update_fields=['approval_status', 'invalidated_at', 'invalidated_reason'])
    return version


def word_count_status(version):
    """Phase 10 — target 100-180 words excluding signature/source links; never enforced silently, just reported."""
    count = version.word_count()
    low, high = TARGET_WORD_RANGE
    if count < low:
        return {'count': count, 'in_range': False, 'note': f'{low - count} words under the {low}-{high} target range.'}
    if count > high:
        return {'count': count, 'in_range': False, 'note': f'{count - high} words over the {low}-{high} target range.'}
    return {'count': count, 'in_range': True, 'note': 'Within target range.'}
