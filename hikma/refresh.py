"""
Refresh-job processing: ingest real evidence, then regenerate the AssessmentRun.

`process_refresh(job)` is decoupled from the request so a real worker (or the
`process_refresh_jobs` management command) can dequeue pending jobs. The API
endpoint creates the job then calls this inline (no broker configured yet), and
returns only the job status.
"""
from __future__ import annotations

from django.utils import timezone


def process_refresh(job) -> None:
    from hikma.assessment import build_assessment
    from hikma.ingest import ingest_for_profile
    from hikma.models import AssessmentRun

    job.status = "running"
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])
    try:
        profile = job.company
        stats = ingest_for_profile(profile)

        result = build_assessment(profile)
        run = AssessmentRun.objects.create(
            company=profile, subject_type="company", subject_ref=profile.company.slug,
            status="done", result=result,
        )

        job.sources_seen = stats["sources_seen"]
        job.evidence_created = stats["created"]
        job.evidence_skipped = stats["skipped"]
        job.assessment_run = run
        job.status = "done"
        job.completed_at = timezone.now()
        job.save()
    except Exception as exc:  # noqa: BLE001 — record any failure on the job row
        job.status = "error"
        job.error_message = f"{type(exc).__name__}: {exc}"
        job.completed_at = timezone.now()
        job.save(update_fields=["status", "error_message", "completed_at"])
        raise
