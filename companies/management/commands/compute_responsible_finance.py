"""
compute_responsible_finance — Compute Responsible Finance alignment scores
for all companies and store results in DataIngestionLog.

Usage:
  python manage.py compute_responsible_finance
  python manage.py compute_responsible_finance --company=schneider-electric
  python manage.py compute_responsible_finance --eligible-only
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Compute Responsible Finance scores for all company profiles'

    def add_arguments(self, parser):
        parser.add_argument('--company', type=str, default=None,
                            help='Process a single company by slug')
        parser.add_argument('--eligible-only', action='store_true',
                            help='Only show companies that pass ethical-capital eligibility')
        parser.add_argument('--min-score', type=float, default=0.0,
                            help='Only show companies above this score threshold')

    def handle(self, *args, **options):
        from companies.models import CompanyProfile, DataIngestionLog
        from ml.responsible_finance import compute_responsible_finance_score

        qs = CompanyProfile.objects.select_related('company').order_by('-ecoiq_total_score')

        if options['company']:
            qs = qs.filter(company__slug=options['company'])
            if not qs.exists():
                self.stdout.write(self.style.ERROR(f"Company not found: {options['company']}"))
                return

        total = qs.count()
        self.stdout.write(f'Computing Responsible Finance scores for {total} profiles…\n')

        results = []
        for profile in qs.iterator(chunk_size=50):
            try:
                result = compute_responsible_finance_score(profile)
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'  Error for {profile.company.name}: {e}')
                )
                continue

            rf_score = result['responsible_finance_score']
            grade    = result['ethical_grade']

            if rf_score < options['min_score']:
                continue
            if options['eligible_only'] and not result['ethical_capital_eligible']:
                continue

            results.append((profile, result))

            # Store in DataIngestionLog
            DataIngestionLog.objects.create(
                company=profile.company,
                source='manual',
                raw_data={'responsible_finance': result},
                fields_updated=['responsible_finance_score'],
                success=True,
            )

            # Console output
            eligible_flag = '✅' if result['ethical_capital_eligible'] else '  '
            self.stdout.write(
                f'{eligible_flag} {profile.company.name[:32]:<32} '
                f'RF:{rf_score:5.1f}  Grade:{grade}'
            )

        # ── Summary ─────────────────────────────────────────────────────────
        eligible_count = sum(
            1 for _, r in results if r['ethical_capital_eligible']
        )
        avg_score = (
            sum(r['responsible_finance_score'] for _, r in results) / len(results)
            if results else 0
        )

        self.stdout.write(self.style.SUCCESS(
            f'\n── Summary ──────────────────────────────────────────\n'
            f'  Processed:          {len(results)} companies\n'
            f'  Average RF score:   {avg_score:.1f}/100\n'
            f'  Ethical-capital eligible: {eligible_count} ({eligible_count/max(len(results),1)*100:.0f}%)\n'
            f'  Results saved to DataIngestionLog (source=manual).'
        ))
