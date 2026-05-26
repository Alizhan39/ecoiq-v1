"""
Management command: generate_ai_profile

Generate AI content (summary, modernization report, investment opportunity,
risk notes, recommendations) for one or more company profiles.

Usage:
    python manage.py generate_ai_profile                   # all public profiles without AI content
    python manage.py generate_ai_profile --slug kazmunaygas
    python manage.py generate_ai_profile --all             # regenerate every profile
    python manage.py generate_ai_profile --status draft    # drafts only
"""
import time
from django.core.management.base import BaseCommand, CommandError
from companies.models import CompanyProfile
from companies.ai_helpers import generate_ai_company_profile


class Command(BaseCommand):
    help = 'Generate AI profile content for CompanyProfile records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--slug',
            type=str,
            help='Generate only for the company with this slug',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            dest='regenerate_all',
            help='Regenerate AI content even if it already exists',
        )
        parser.add_argument(
            '--status',
            type=str,
            default='',
            help='Filter by profile status: draft | public | verified',
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.0,
            help='Seconds to wait between API calls (default 1.0)',
        )

    def handle(self, *args, **options):
        slug            = options['slug']
        regenerate_all  = options['regenerate_all']
        status_filter   = options['status']
        delay           = options['delay']

        qs = CompanyProfile.objects.select_related('company').all()

        if slug:
            qs = qs.filter(company__slug=slug)
            if not qs.exists():
                raise CommandError(f'No CompanyProfile found for slug "{slug}"')

        if status_filter:
            qs = qs.filter(status=status_filter)

        if not regenerate_all and not slug:
            # Only profiles missing AI content
            qs = qs.filter(ai_summary='')

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.WARNING('No profiles matched — nothing to do.'))
            return

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f'Generating AI profiles for {total} company profile(s)…'
            )
        )

        ok = 0
        errors = 0
        for i, profile in enumerate(qs, 1):
            name = profile.company.name
            self.stdout.write(f'  [{i}/{total}] {name}…', ending=' ')
            try:
                generate_ai_company_profile(profile)
                self.stdout.write(self.style.SUCCESS('✓'))
                ok += 1
            except Exception as ex:
                self.stdout.write(self.style.ERROR(f'✗  {ex}'))
                errors += 1

            if i < total:
                time.sleep(delay)

        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(f'Done — {ok} succeeded, {errors} failed.')
        )
