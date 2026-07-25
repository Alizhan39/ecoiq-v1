"""public_action_preparation/services/ethics_review.py — Phase 14: the mandatory ethics/sensitivity checklist for the chosen action."""
from django.utils import timezone

from public_action_preparation.models import EthicsReview


class EthicsReviewNotAllowedError(Exception):
    pass


def get_or_create_review(opportunity):
    review, _ = EthicsReview.objects.get_or_create(opportunity=opportunity)
    return review


def record_ethics_review(opportunity, *, actor, answers, notes=''):
    """`answers`: dict of field -> bool. Any field not present is left at its current (default False) value — never silently assumed passed."""
    if actor is None:
        raise EthicsReviewNotAllowedError('Ethics review requires a real actor.')
    review = get_or_create_review(opportunity)
    for field in EthicsReview.CHECKLIST_FIELDS:
        if field in answers:
            setattr(review, field, bool(answers[field]))
    review.notes = notes
    review.reviewed_by = actor
    review.reviewed_at = timezone.now()
    review.save()
    return review
