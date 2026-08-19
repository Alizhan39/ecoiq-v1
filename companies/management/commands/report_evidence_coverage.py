"""
Report evidence coverage across company profiles, and simulate eligibility
thresholds against the real distribution.

Read-only. Writes nothing, changes no score. Its purpose is to let the threshold
decision in docs/product/EVIDENCE_INTEGRITY_PLAN.md §8 be made against production
numbers rather than against a guess.

    python manage.py report_evidence_coverage
    python manage.py report_evidence_coverage --public-only
"""
from django.core.management.base import BaseCommand

from companies.evidence import (
    ELIGIBILITY_ELIGIBLE, ELIGIBILITY_PROVISIONAL, ELIGIBILITY_UNAVAILABLE,
    MATERIAL_INPUTS, coverage_for, eligibility, field_provenance,
)

CANDIDATE_THRESHOLDS = (0.20, 0.40, 0.60, 0.80)


class Command(BaseCommand):
    help = 'Report evidence coverage and simulate score-eligibility thresholds.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--public-only', action='store_true',
            help='Only profiles with status public/verified (what visitors actually see).',
        )

    def handle(self, *args, **options):
        from companies.models import CompanyProfile

        qs = CompanyProfile.objects.all()
        if options['public_only']:
            qs = qs.filter(status__in=('public', 'verified'))
        profiles = list(qs)

        if not profiles:
            self.stdout.write(self.style.WARNING('No profiles found.'))
            return

        self.stdout.write(f'\nProfiles analysed: {len(profiles)}')
        self.stdout.write(f'Material inputs per profile: {len(MATERIAL_INPUTS)}')
        self.stdout.write(
            f'Total composite weight covered: {sum(i.weight for i in MATERIAL_INPUTS):.2f}\n')

        reports = [(p, coverage_for(p)) for p in profiles]

        # ── Coverage distribution ────────────────────────────────────────────
        buckets = {'0%': 0, '1-19%': 0, '20-39%': 0, '40-59%': 0, '60-79%': 0, '80-99%': 0, '100%': 0}
        for _, r in reports:
            pct = r.coverage_percent
            key = ('0%' if pct == 0 else '100%' if pct >= 100 else
                   '1-19%' if pct < 20 else '20-39%' if pct < 40 else
                   '40-59%' if pct < 60 else '60-79%' if pct < 80 else '80-99%')
            buckets[key] += 1

        self.stdout.write(self.style.MIGRATE_HEADING('Evidence coverage distribution'))
        for label, count in buckets.items():
            share = count / len(reports) * 100
            self.stdout.write(f'  {label:>8}  {count:>6}  {share:5.1f}%  {"#" * int(share / 2)}')

        # ── Threshold simulation ─────────────────────────────────────────────
        self.stdout.write('\n' + self.style.MIGRATE_HEADING(
            'Eligibility simulation (full = minimum x 2, capped at 0.9)'))
        self.stdout.write(f'  {"min coverage":>13} {"eligible":>10} {"provisional":>12} {"unavailable":>12}')
        for minimum in CANDIDATE_THRESHOLDS:
            full = min(minimum * 2, 0.9)
            counts = {ELIGIBILITY_ELIGIBLE: 0, ELIGIBILITY_PROVISIONAL: 0, ELIGIBILITY_UNAVAILABLE: 0}
            for _, r in reports:
                counts[eligibility(r.coverage, minimum, full)] += 1
            self.stdout.write(
                f'  {minimum * 100:>12.0f}% {counts[ELIGIBILITY_ELIGIBLE]:>10}'
                f' {counts[ELIGIBILITY_PROVISIONAL]:>12} {counts[ELIGIBILITY_UNAVAILABLE]:>12}')

        # ── Provenance census ────────────────────────────────────────────────
        self.stdout.write('\n' + self.style.MIGRATE_HEADING('Provenance census (all material cells)'))
        census: dict[str, int] = {}
        for p, _ in reports:
            for item in MATERIAL_INPUTS:
                key = field_provenance(p, item.field_name)
                census[key] = census.get(key, 0) + 1
        total_cells = sum(census.values())
        for key, count in sorted(census.items(), key=lambda kv: -kv[1]):
            self.stdout.write(f'  {key:<28} {count:>7}  {count / total_cells * 100:5.1f}%')

        zero = buckets['0%']
        if zero:
            self.stdout.write('\n' + self.style.WARNING(
                f'{zero} of {len(reports)} profiles have ZERO evidence-backed material '
                f'inputs but still carry a published score.\n'
                f'See docs/product/EVIDENCE_INTEGRITY_PLAN.md §8 — this is the decision, '
                f'not a defect in this report.'))
