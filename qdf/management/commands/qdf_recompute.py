"""
Re-score QDF decision assessments in bulk.

Usage:
    python manage.py qdf_recompute                # all public/verified profiles
    python manage.py qdf_recompute --status public --limit 50
"""
from django.core.management.base import BaseCommand

from companies.models import CompanyProfile
from qdf.scoring import ensure_questions, compute_and_save


class Command(BaseCommand):
    help = 'Recompute QDF Decision Integrity assessments for company profiles.'

    def add_arguments(self, parser):
        parser.add_argument('--status', default='public,verified',
                            help='Comma-separated profile statuses to include.')
        parser.add_argument('--limit', type=int, default=0,
                            help='Cap the number of profiles (0 = no cap).')

    def handle(self, *args, **opts):
        ensure_questions()
        statuses = [s.strip() for s in opts['status'].split(',') if s.strip()]
        qs = (CompanyProfile.objects
              .filter(status__in=statuses)
              .select_related('company')
              .order_by('-ecoiq_total_score'))
        if opts['limit']:
            qs = qs[:opts['limit']]

        ok = fail = 0
        for p in qs:
            try:
                compute_and_save(p)
                ok += 1
            except Exception as exc:  # noqa: BLE001
                fail += 1
                self.stderr.write(f'  ! {p.company.name}: {exc}')
        self.stdout.write(self.style.SUCCESS(
            f'QDF recompute complete: {ok} assessed, {fail} failed.'))
