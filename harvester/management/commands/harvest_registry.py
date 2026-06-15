"""
Batch-harvest every company in the UK target registry.

Usage:
    python manage.py harvest_registry [--limit N] [--sector S] [--active-only]

Iterates RegistryCompany rows (by priority), runs the harvest pipeline for each
slug, and CONTINUES if a company fails. Persists a BatchHarvestRun summary and
prints per-company progress:

    [1/25] national-grid
    [2/25] sse
    ...

No AI, no scoring, no dashboard changes.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Run the Evidence Harvester across all registry companies."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="Max companies (0 = all).")
        parser.add_argument("--sector", default="", help="Filter by sector.")
        parser.add_argument("--active-only", action="store_true", default=True,
                            help="Only is_active companies (default true).")

    def handle(self, *args, **opts):
        from harvester.models import (
            RegistryCompany, HarvestJob, Evidence, Datapoint, BatchHarvestRun,
        )
        from harvester import pipeline
        from companies.models import CompanyProfile

        qs = RegistryCompany.objects.all().order_by("priority")
        if opts.get("active_only", True):
            qs = qs.filter(is_active=True)
        if opts["sector"]:
            qs = qs.filter(sector=opts["sector"])
        companies = list(qs)
        if opts["limit"] and opts["limit"] > 0:
            companies = companies[: opts["limit"]]
        total = len(companies)

        note = opts["sector"] or ("limit=%d" % opts["limit"] if opts["limit"] else "all")
        batch = BatchHarvestRun.objects.create(
            total_companies=total, status="running", started_at=timezone.now(),
            filter_note=note,
        )

        successful = failed = ev_created = dp_created = 0

        for i, rc in enumerate(companies, 1):
            slug = rc.slug
            self.stdout.write(f"[{i}/{total}] {slug}")

            ev_before = Evidence.objects.filter(company_slug=slug).count()
            dp_before = Datapoint.objects.filter(company_slug=slug).count()

            profile = (CompanyProfile.objects
                       .filter(company__slug=slug).select_related("company").first())
            job = HarvestJob.objects.create(
                company=profile, company_slug=slug, status="pending",
                triggered_by="harvest_registry",
            )
            try:
                pipeline.run_harvest(job)
                job.refresh_from_db()
                if job.status == "done":
                    successful += 1
                else:
                    failed += 1
                    self.stdout.write(self.style.WARNING(
                        f"      ! {slug}: {job.error_message or job.status}"))
            except Exception as exc:  # noqa: BLE001 — continue on failure
                failed += 1
                self.stdout.write(self.style.ERROR(f"      ! {slug} failed: {exc}"))

            ev_after = Evidence.objects.filter(company_slug=slug).count()
            dp_after = Datapoint.objects.filter(company_slug=slug).count()
            ev_created += max(0, ev_after - ev_before)
            dp_created += max(0, dp_after - dp_before)

        batch.successful = successful
        batch.failed = failed
        batch.evidence_created = ev_created
        batch.datapoints_created = dp_created
        batch.status = "done"
        batch.completed_at = timezone.now()
        batch.save()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Batch harvest complete:"))
        for k, v in batch.summary_dict().items():
            self.stdout.write(f"  {k}: {v}")
