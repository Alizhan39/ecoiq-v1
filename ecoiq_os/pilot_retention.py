"""Stage 8 read-only retention inventory; never silently erase audit history.

A deletion/redaction workflow needs an approved retention schedule, backup
and legal-hold policy. This module only counts records beyond review targets.
"""
from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

PENDING_DAYS = 30
DECIDED_DAYS = 90


def retention_inventory(*, now=None) -> dict[str, object]:
    """Aggregate counts only: never include user/project/source text or IDs."""
    from api.models import (
        ProcessAIProcessingReadiness, ProcessAIReviewCase, ProcessAIReviewEvent,
    )

    at = now or timezone.now()
    pending_cutoff = at - timedelta(days=PENDING_DAYS)
    decided_cutoff = at - timedelta(days=DECIDED_DAYS)
    old_pending = ProcessAIReviewCase.objects.filter(
        status=ProcessAIReviewCase.Status.PENDING,
        created_at__lt=pending_cutoff,
    ).count()
    old_decided = ProcessAIReviewCase.objects.exclude(
        status=ProcessAIReviewCase.Status.PENDING,
    ).filter(reviewed_at__lt=decided_cutoff).count()
    stale_readiness = ProcessAIProcessingReadiness.objects.filter(
        expires_at__lt=at,
    ).count()
    old_events = ProcessAIReviewEvent.objects.filter(
        created_at__lt=decided_cutoff,
    ).count()
    return {
        "policy": "stage8_proposed_review_targets_v1",
        "pending_review_target_days": PENDING_DAYS,
        "decided_review_target_days": DECIDED_DAYS,
        "pending_exceeding_target": old_pending,
        "decided_exceeding_target": old_decided,
        "expired_readiness_records": stale_readiness,
        "events_older_than_decided_target": old_events,
        "delete_performed": False,
        "approved_purge_workflow_available": False,
        "legal_hold_review_required": True,
    }
