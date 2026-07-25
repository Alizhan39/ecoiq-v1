"""outreach_readiness/services/risk.py — Phase 12: the mandatory 15-item risk checklist."""
from django.utils import timezone

from outreach_readiness.models import OutreachRiskReview


class RiskReviewNotAllowedError(Exception):
    pass


def record_risk_review(message_version, *, actor, answers, notes=''):
    """
    Creates or updates the ONE risk review for this message version.
    Every item defaults False — an item not present in `answers` stays
    (or starts) unreviewed/failed, never silently assumed to pass.
    """
    if actor is None:
        raise RiskReviewNotAllowedError('Risk review requires a real actor.')
    review, _ = OutreachRiskReview.objects.get_or_create(message_version=message_version)
    for field in OutreachRiskReview.CHECKLIST_FIELDS:
        if field in answers:
            setattr(review, field, bool(answers[field]))
    if notes:
        review.notes = notes
    review.reviewed_by = actor
    review.reviewed_at = timezone.now()
    review.save()
    return review
