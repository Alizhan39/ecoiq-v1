"""
Seed the Khalifa Stewardship Tour Operating System demo (idempotent).

Usage:
    python manage.py seed_khalifa_stewardship_demo
"""
from django.core.management.base import BaseCommand

from agent_runtime_model_router.models import AgentRun
from agent_runtime_model_router.services.registry import sync_registry
from khalifa_stewardship_tour_operating_system.models import (
    LaunchChecklistItem, StewardshipIntervention, StewardshipProblem, StewardshipTour,
    TourBeneficiary,
)
from khalifa_stewardship_tour_operating_system.services.demo_flagship_pipeline import (
    build_kazakhstan_clean_heat_demo, build_kazakhstan_pilot_readiness_layer,
)
from khalifa_stewardship_tour_operating_system.services.launch_readiness import (
    calculate_tour_launch_readiness,
)


class Command(BaseCommand):
    help = 'Sync the agent registry and seed the Kazakhstan Clean Heat Stewardship Tour demo, including the real pilot readiness layer.'

    def handle(self, *args, **opts):
        registry_entries = sync_registry()
        council_run = build_kazakhstan_clean_heat_demo()
        tour = build_kazakhstan_pilot_readiness_layer()
        readiness = calculate_tour_launch_readiness(tour)

        self.stdout.write(self.style.SUCCESS(
            f'Khalifa Stewardship Tour demo ready: {registry_entries.count()} registry entries, '
            f'{AgentRun.objects.filter(council_case=council_run).count()} agent runs, '
            f'{StewardshipTour.objects.count()} tours, '
            f'{StewardshipProblem.objects.count()} problems, '
            f'{StewardshipIntervention.objects.count()} interventions, '
            f'{TourBeneficiary.objects.count()} beneficiaries, '
            f'{LaunchChecklistItem.objects.count()} launch checklist items '
            f'for "{council_run.title}" — ready_to_launch={readiness["ready_to_launch"]}.'
        ))
