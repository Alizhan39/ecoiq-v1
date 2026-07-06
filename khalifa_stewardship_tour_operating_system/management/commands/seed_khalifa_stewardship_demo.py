"""
Seed the Khalifa Stewardship Tour Operating System demo (idempotent).

Usage:
    python manage.py seed_khalifa_stewardship_demo
"""
from django.core.management.base import BaseCommand

from agent_runtime_model_router.models import AgentRun
from agent_runtime_model_router.services.registry import sync_registry
from khalifa_stewardship_tour_operating_system.models import (
    StewardshipIntervention, StewardshipProblem, StewardshipTour,
)
from khalifa_stewardship_tour_operating_system.services.demo_flagship_pipeline import (
    build_kazakhstan_clean_heat_demo,
)


class Command(BaseCommand):
    help = 'Sync the agent registry and seed the Kazakhstan Clean Heat Stewardship Tour demo.'

    def handle(self, *args, **opts):
        registry_entries = sync_registry()
        council_run = build_kazakhstan_clean_heat_demo()

        self.stdout.write(self.style.SUCCESS(
            f'Khalifa Stewardship Tour demo ready: {registry_entries.count()} registry entries, '
            f'{AgentRun.objects.filter(council_case=council_run).count()} agent runs, '
            f'{StewardshipTour.objects.count()} tours, '
            f'{StewardshipProblem.objects.count()} problems, '
            f'{StewardshipIntervention.objects.count()} interventions '
            f'for "{council_run.title}".'
        ))
