"""
Seed the Waste-to-Value Capital Allocation Engine demo (idempotent).

Usage:
    python manage.py seed_waste_to_value_demo
"""
from django.core.management.base import BaseCommand

from agent_runtime_model_router.models import AgentRun
from agent_runtime_model_router.services.registry import sync_registry
from waste_to_value_capital_allocation_engine.models import (
    CapitalAllocationDecision, InterventionOption, OperationalLoss,
)
from waste_to_value_capital_allocation_engine.services.demo_pipeline import build_meat_cold_chain_demo


class Command(BaseCommand):
    help = 'Sync the agent registry and seed the Meat Cold-Chain Loss Prevention demo.'

    def handle(self, *args, **opts):
        registry_entries = sync_registry()
        council_run = build_meat_cold_chain_demo()

        self.stdout.write(self.style.SUCCESS(
            f'Waste-to-Value demo ready: {registry_entries.count()} registry entries, '
            f'{AgentRun.objects.filter(council_case=council_run).count()} agent runs, '
            f'{OperationalLoss.objects.count()} operational losses, '
            f'{InterventionOption.objects.count()} intervention options, '
            f'{CapitalAllocationDecision.objects.count()} capital allocation decisions '
            f'for "{council_run.title}".'
        ))
