"""
Management command: recalculate_scores

Recompute EcoIQ scores for all (or filtered) CompanyProfile records using
the live scoring engine. Safe to re-run at any time — idempotent.

Usage:
    python manage.py recalculate_scores                # all profiles
    python manage.py recalculate_scores --slug kaspi
    python manage.py recalculate_scores --status draft
    python manage.py recalculate_scores --dry-run      # preview without saving
"""
from django.core.management.base import BaseCommand, CommandError
from companies.models import CompanyProfile
from companies.scoring import compute_ecoiq_profile_score


class Command(BaseCommand):
    help = 'Recalculate EcoIQ scores for CompanyProfile records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--slug',
            type=str,
            help='Recalculate only for the company with this slug',
        )
        parser.add_argument(
            '--status',
            type=str,
            default='',
            help='Filter by profile status: draft | public | verified',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would change without saving',
        )

    def handle(self, *args, **options):
        slug       = options['slug']
        status_f   = options['status']
        dry_run    = options['dry_run']

        qs = CompanyProfile.objects.select_related('company').all()

        if slug:
            qs = qs.filter(company__slug=slug)
            if not qs.exists():
                raise CommandError(f'No CompanyProfile found for slug "{slug}"')

        if status_f:
            qs = qs.filter(status=status_f)

        total = qs.count()
        if total == 0:
            self.stdout.write(self.style.WARNING('No profiles matched — nothing to do.'))
            return

        mode = '[DRY-RUN] ' if dry_run else ''
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f'{mode}Recalculating EcoIQ scores for {total} profile(s)…'
            )
        )

        changed = 0
        for profile in qs:
            old_score = profile.ecoiq_total_score
            results   = compute_ecoiq_profile_score(profile)
            new_score = results['ecoiq_total_score']
            label     = results['moral_label']
            delta     = new_score - old_score

            if not dry_run:
                SCORE_FIELDS = [
                    'public_benefit_score', 'environmental_responsibility_score',
                    'modernization_score', 'transparency_anti_corruption_score',
                    'anti_corruption_score', 'ethical_alignment_score',
                    'harm_penalty', 'ecoiq_total_score', 'moral_label', 'ecoiq_category',
                ]
                for field in SCORE_FIELDS:
                    if field in results:
                        setattr(profile, field, results[field])
                profile.save(update_fields=SCORE_FIELDS + ['updated_at'])

            arrow = '↑' if delta > 0.05 else ('↓' if delta < -0.05 else '→')
            color = self.style.SUCCESS if delta >= 0 else self.style.ERROR
            self.stdout.write(
                f'  {profile.company.name:<35} '
                f'{old_score:5.1f} {arrow} {new_score:5.1f}  '
                + color(f'{label}')
            )
            if abs(delta) > 0.05:
                changed += 1

        verb = 'would change' if dry_run else 'changed'
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                f'{mode}Done — {total} profiles processed, {changed} scores {verb}.'
            )
        )
