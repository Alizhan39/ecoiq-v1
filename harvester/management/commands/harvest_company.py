"""
Harvest evidence for one company end-to-end.

Usage:
    python manage.py harvest_company national-grid

Creates a HarvestJob, runs the full pipeline inline (discover → verify → dedup →
normalize → persist Datapoints), and prints the job stats plus a datapoint
summary. Deterministic and offline. No scoring/brief/balance logic.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run the Evidence Harvester pipeline for a company slug."

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument("--show-datapoints", action="store_true",
                            help="Print extracted datapoints.")

    def handle(self, *args, **opts):
        from companies.models import CompanyProfile
        from harvester.models import HarvestJob, Datapoint
        from harvester.pipeline import run_harvest

        slug = opts["slug"]
        profile = (CompanyProfile.objects
                   .filter(company__slug=slug).select_related("company").first())

        job = HarvestJob.objects.create(
            company=profile, company_slug=slug, status="pending",
            triggered_by="harvest_company",
        )
        try:
            run_harvest(job)
        except Exception:  # noqa: BLE001 — status captured on the job row
            job.refresh_from_db()

        s = job.status_dict()
        style = self.style.SUCCESS if job.status == "done" else self.style.ERROR
        self.stdout.write(style(f"HarvestJob {job.id} [{slug}] → {job.status}"))
        for k, v in s["stats"].items():
            self.stdout.write(f"  {k}: {v}")
        if s["error"]:
            self.stdout.write(self.style.ERROR(f"  error: {s['error']}"))

        if opts["show_datapoints"]:
            self.stdout.write("  datapoints:")
            for dp in Datapoint.objects.filter(company_slug=slug).order_by("category", "metric"):
                val = dp.value if dp.value is not None else "—"
                self.stdout.write(
                    f"    [{dp.status}] {dp.metric} = {val} {dp.unit} "
                    f"({dp.period or 'n/a'}, conf {dp.confidence})")
