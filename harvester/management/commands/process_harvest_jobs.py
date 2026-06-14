"""
Worker stand-in: drain pending Evidence Harvester jobs (no broker required).

Usage:
    python manage.py process_harvest_jobs [--limit N]

Mirrors hikma's process_refresh_jobs: dequeues pending HarvestJob rows and runs
the same pipeline.run_harvest used by harvest_company.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Process pending Evidence Harvester HarvestJob rows."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=20)

    def handle(self, *args, **opts):
        from harvester.models import HarvestJob
        from harvester.pipeline import run_harvest

        pending = HarvestJob.objects.filter(status="pending")[: opts["limit"]]
        n = 0
        for job in pending:
            try:
                run_harvest(job)
                self.stdout.write(self.style.SUCCESS(
                    f"job {job.id} {job.company_slug}: "
                    f"evidence={job.evidence_extracted} "
                    f"verified={job.evidence_verified} "
                    f"datapoints={job.evidence_stored}"))
            except Exception as exc:  # noqa: BLE001
                self.stdout.write(self.style.ERROR(f"job {job.id} error: {exc}"))
            n += 1
        self.stdout.write(f"processed {n} job(s)")
