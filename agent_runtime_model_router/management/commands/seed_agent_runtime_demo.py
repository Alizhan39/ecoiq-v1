"""
Seed the Agent Runtime & Model Router demo (idempotent).

Usage:
    python manage.py seed_agent_runtime_demo
"""
from django.core.management.base import BaseCommand

from agent_runtime_model_router.models import AgentRegistryEntry, AgentRun
from agent_runtime_model_router.services.demo_pipeline import build_boiler_house_runtime_demo
from agent_runtime_model_router.services.registry import sync_registry


class Command(BaseCommand):
    help = 'Sync the agent registry and seed the Boiler House #3 Agent Runtime demo.'

    def handle(self, *args, **opts):
        registry_entries = sync_registry()
        council_run = build_boiler_house_runtime_demo()

        self.stdout.write(self.style.SUCCESS(
            f'Agent Runtime & Model Router demo ready: {registry_entries.count()} registry entries, '
            f'{AgentRun.objects.filter(council_case=council_run).count()} agent runs for '
            f'"{council_run.title}".'
        ))
