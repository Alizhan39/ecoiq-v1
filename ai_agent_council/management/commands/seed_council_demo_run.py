"""
Seed the AI Agent Council demo runs (idempotent).

Usage:
    python manage.py seed_council_demo_run
"""
from django.core.management.base import BaseCommand

from ai_agent_council.models import (
    CouncilDecision, CouncilDisagreement, CouncilRun, CrossExaminationExchange,
)
from ai_agent_council.services.seed_demo import (
    create_boiler_house_demo, create_grid_capacity_reopened_demo,
)


class Command(BaseCommand):
    help = 'Seed the AI Agent Council demo runs (Boiler House #3, Grid Capacity Evidence Review).'

    def handle(self, *args, **opts):
        create_boiler_house_demo()
        create_grid_capacity_reopened_demo()

        self.stdout.write(self.style.SUCCESS(
            f'AI Agent Council demo ready: {CouncilRun.objects.count()} runs, '
            f'{CouncilDisagreement.objects.count()} disagreements, '
            f'{CrossExaminationExchange.objects.count()} cross-examination exchanges, '
            f'{CouncilDecision.objects.count()} decisions.'
        ))
