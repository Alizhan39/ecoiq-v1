"""
python manage.py recalculate_ecoiq_scores [--company-id ID] [--limit N]

Recomputes the EcoIQ Intelligence Score (pandas_scoring_engine) for one
company (--company-id) or a bounded batch of companies (--limit, default 25
— cost control: never "every company" by accident), and records each result
as a new companies.CompanyScoreSnapshot row (trigger='intelligence_score_recalc').
"""
from django.core.management.base import BaseCommand

from companies.models import CompanyProfile, CompanyScoreSnapshot
from pandas_scoring_engine.services.scoring import compute_company_intelligence_score


class Command(BaseCommand):
    help = 'Recompute the EcoIQ Intelligence Score for one or a bounded batch of companies.'

    def add_arguments(self, parser):
        parser.add_argument('--company-id', type=int, default=None, help='Recalculate a single CompanyProfile by id.')
        parser.add_argument('--limit', type=int, default=25, help='Batch size when --company-id is not given (default 25).')

    def handle(self, *args, **options):
        if options['company_id'] is not None:
            queryset = CompanyProfile.objects.filter(pk=options['company_id'])
            if not queryset.exists():
                self.stdout.write(self.style.ERROR(f'CompanyProfile {options["company_id"]} does not exist.'))
                return
        else:
            queryset = CompanyProfile.objects.filter(status__in=('public', 'verified')).select_related('company')[:options['limit']]

        processed = 0
        for profile in queryset:
            scores = compute_company_intelligence_score(profile)
            CompanyScoreSnapshot.create_from_profile(
                profile, trigger='intelligence_score_recalc',
                notes='Recalculated via recalculate_ecoiq_scores management command.',
                intelligence_scores=scores,
            )
            processed += 1
            name = profile.company.name if profile.company_id else f'Profile #{profile.pk}'
            score_display = f'{scores["intelligence_score"]:.1f}' if scores['intelligence_score'] is not None else 'n/a'
            self.stdout.write(f'  {name}: intelligence_score={score_display}')

        self.stdout.write(self.style.SUCCESS(f'Recalculated EcoIQ Intelligence Score for {processed} company(ies).'))
