"""
Seed the EcoIQ Financial Intelligence Cloud demo (idempotent).

Usage:
    python manage.py seed_financial_intelligence_cloud_demo
"""
from django.core.management.base import BaseCommand

from agent_runtime_model_router.services.registry import sync_registry
from financial_intelligence_cloud.models import (
    AdvisoryOpportunity, InstitutionalAccount, PortfolioEntity, PortfolioSignal,
)
from financial_intelligence_cloud.services.daily_brief import generate_daily_portfolio_brief, generate_opportunity_feed
from financial_intelligence_cloud.services.demo_portfolios import build_all_demo_portfolios


class Command(BaseCommand):
    help = 'Sync the agent registry and seed the Northstar Advisory, Atlas Value Partners and Civic Commercial Bank demo portfolios.'

    def handle(self, *args, **opts):
        registry_entries = sync_registry()
        results = build_all_demo_portfolios()

        for account, portfolio in results.values():
            generate_opportunity_feed(account, portfolio)
            generate_daily_portfolio_brief(account, portfolio)

        self.stdout.write(self.style.SUCCESS(
            f'Financial Intelligence Cloud demo ready: {registry_entries.count()} registry entries, '
            f'{InstitutionalAccount.objects.filter(is_demo=True).count()} demo accounts, '
            f'{PortfolioEntity.objects.count()} portfolio entities, '
            f'{PortfolioSignal.objects.count()} signals, '
            f'{AdvisoryOpportunity.objects.count()} advisory opportunities.'
        ))
