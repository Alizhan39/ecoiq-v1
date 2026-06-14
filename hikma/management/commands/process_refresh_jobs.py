"""Worker stand-in: drain pending Hikma refresh jobs (no broker required).

Usage: python manage.py process_refresh_jobs [--limit N]
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Process pending Hikma IngestRefreshJob rows."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)

    def handle(self, *args, **opts):
        from hikma.models import IngestRefreshJob
        from hikma.refresh import process_refresh

        pending = IngestRefreshJob.objects.filter(status="pending")[: opts["limit"]]
        n = 0
        for job in pending:
            try:
                process_refresh(job)
                self.stdout.write(self.style.SUCCESS(
                    f"job {job.id} {job.subject_ref}: created={job.evidence_created} "
                    f"skipped={job.evidence_skipped} run={job.assessment_run_id}"))
            except Exception as exc:  # noqa: BLE001
                self.stdout.write(self.style.ERROR(f"job {job.id} error: {exc}"))
            n += 1
        self.stdout.write(f"processed {n} job(s)")
