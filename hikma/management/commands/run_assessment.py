"""
Produce one deterministic Hikma AssessmentResult for a real company.

Usage:
    python manage.py run_assessment <company-slug> [--save] [--json]

Reuses mizan/scoring.py via hikma.assessment.build_assessment. CLI only — no
endpoint, no UI. With --save it persists an AssessmentRun row.
"""
import json

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Compute a deterministic Hikma AssessmentResult for a company slug."

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument("--save", action="store_true", help="Persist an AssessmentRun row")
        parser.add_argument("--json", action="store_true", help="Print full JSON result")

    def handle(self, *args, **opts):
        from companies.models import CompanyProfile
        from hikma.assessment import build_assessment
        from hikma.models import AssessmentRun

        slug = opts["slug"]
        try:
            profile = CompanyProfile.objects.select_related("company").get(company__slug=slug)
        except CompanyProfile.DoesNotExist:
            raise CommandError(f'No CompanyProfile for slug "{slug}".')

        result = build_assessment(profile)

        if opts["save"]:
            run = AssessmentRun.objects.create(
                company=profile,
                subject_type="company",
                subject_ref=slug,
                status="done",
                result=result,
            )
            self.stdout.write(self.style.SUCCESS(f"Saved AssessmentRun id={run.id}"))

        if opts["json"]:
            self.stdout.write(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            s = result
            self.stdout.write(self.style.SUCCESS(
                f'{s["subject"]["name"]} — composite {s["composite_score"]} ({s["rating_label"]})'))
            self.stdout.write(f'  dimensions: {s["dimensions"]}')
            self.stdout.write(f'  harm score: {s["harm_score"]} | flags: {s["flags"]["risk_flags"]}')
            self.stdout.write(f'  evidence counts: {s["evidence_counts"]}')
            self.stdout.write(f'  activated nodes ({len(s["activated_nodes"])}): '
                              + ', '.join(n["node"] for n in s["activated_nodes"][:8]))
            self.stdout.write(f'  scoring spine: {s["scoring_spine"]}')
