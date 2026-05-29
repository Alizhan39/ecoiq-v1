"""
Management command: seed_score_history

Creates CompanyScoreSnapshot records for every CompanyProfile that has no
snapshots yet.  Generates 6 monthly snapshots spread over the past 18 months,
ending one month before today, showing a realistic upward trend toward the
company's current score.

Usage:
    python manage.py seed_score_history
    python manage.py seed_score_history --overwrite   # re-create even if snapshots exist
"""
import datetime
import random
from django.core.management.base import BaseCommand
from django.utils import timezone
from companies.models import CompanyProfile, CompanyScoreSnapshot


class Command(BaseCommand):
    help = 'Seed CompanyScoreSnapshot history for Chart.js trend chart'

    def add_arguments(self, parser):
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Delete existing snapshots and recreate from scratch',
        )

    def handle(self, *args, **options):
        overwrite = options['overwrite']
        today     = timezone.now().date()
        created   = 0
        skipped   = 0

        profiles = CompanyProfile.objects.select_related('company').all()

        for profile in profiles:
            if profile.score_snapshots.exists() and not overwrite:
                skipped += 1
                continue

            if overwrite:
                profile.score_snapshots.all().delete()

            current_score = float(profile.ecoiq_total_score or 0)

            # Build 6 monthly dates going back 15 months → ending ~3 months ago
            # so the chart shows "history leading to now"
            dates = []
            for i in range(5, -1, -1):
                # i=5 → 15 months ago, i=0 → last month
                months_back = (i * 3) + 1
                d = today - datetime.timedelta(days=months_back * 30)
                dates.append(d)

            # Generate scores: start ~10 pts below current, ease upward with noise
            base_start = max(current_score - 12, 5)
            random.seed(profile.pk)  # deterministic per profile

            scores = []
            for idx, d in enumerate(dates):
                progress = idx / (len(dates) - 1) if len(dates) > 1 else 1
                # Cubic ease
                eased = 3 * progress ** 2 - 2 * progress ** 3
                score = base_start + (current_score - base_start) * eased
                # ±2 point noise
                score += random.uniform(-2, 2)
                score = round(max(1, min(100, score)), 1)
                scores.append(score)

            # Ensure the last point matches current score exactly
            scores[-1] = current_score

            snapshots = [
                CompanyScoreSnapshot(
                    profile      = profile,
                    date         = dates[idx],
                    trigger      = 'seed',
                    total_score  = scores[idx],
                    # Fill pillar scores at proportional fraction of current values
                    public_benefit_score         = round(profile.public_benefit_score * scores[idx] / max(current_score, 1), 1),
                    environmental_score          = round(profile.environmental_responsibility_score * scores[idx] / max(current_score, 1), 1),
                    modernization_score          = round(profile.modernization_score * scores[idx] / max(current_score, 1), 1),
                    governance_score             = round(profile.transparency_anti_corruption_score * scores[idx] / max(current_score, 1), 1),
                    anti_corruption_score        = round(profile.anti_corruption_score * scores[idx] / max(current_score, 1), 1),
                    ethical_alignment_score      = round(profile.ethical_alignment_score * scores[idx] / max(current_score, 1), 1),
                    harm_penalty                 = round(float(profile.harm_penalty or 0), 1),
                    moral_label                  = profile.moral_label or '',
                    notes                        = 'Seeded by seed_score_history management command',
                )
                for idx in range(len(dates))
            ]

            CompanyScoreSnapshot.objects.bulk_create(snapshots)
            created += len(snapshots)
            self.stdout.write(
                self.style.SUCCESS(
                    f'  ✓ {profile.company.name}: {len(snapshots)} snapshots '
                    f'({scores[0]} → {scores[-1]})'
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone. Created {created} snapshots. Skipped {skipped} profiles '
                f'(already had snapshots — use --overwrite to reset).'
            )
        )
