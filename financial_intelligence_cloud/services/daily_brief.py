"""
financial_intelligence_cloud/services/daily_brief.py — "What changed since
yesterday?" Builds the continuously ranked opportunity feed and the dated
daily portfolio brief from real PortfolioSignal/AdvisoryOpportunity rows —
never recomputes ranking here, just reads the already-stored priority_score/
urgency_score fields.
"""
from django.db import models as db_models
from django.utils import timezone

from financial_intelligence_cloud.models import (
    AdvisoryOpportunity, OpportunityFeedItem, PortfolioDailyBrief, PortfolioSignal,
)


def generate_opportunity_feed(institutional_account, portfolio=None, limit=10):
    """Idempotent via get_or_create keyed on (institutional_account, related_signal)."""
    signals = PortfolioSignal.objects.filter(portfolio_entity__portfolio__institutional_account=institutional_account)
    if portfolio is not None:
        signals = signals.filter(portfolio_entity__portfolio=portfolio)
    signals = signals.order_by('-urgency_score', '-detected_at')[:limit]

    feed_items = []
    for signal in signals:
        item, _ = OpportunityFeedItem.objects.get_or_create(
            institutional_account=institutional_account, related_signal=signal,
            defaults={'item_type': 'new_signal', 'portfolio': signal.portfolio_entity.portfolio},
        )
        item.portfolio = signal.portfolio_entity.portfolio
        item.headline = f'{signal.portfolio_entity.name}: {signal.title}'
        item.detail = signal.description
        item.item_type = 'human_approval_needed' if signal.human_approval_required else 'new_signal'
        item.save()
        feed_items.append(item)
    return feed_items


def generate_daily_portfolio_brief(institutional_account, portfolio=None, brief_date=None):
    """Idempotent via get_or_create keyed on (institutional_account, brief_date) — a dated snapshot, never silently drifting."""
    brief_date = brief_date or timezone.now().date()

    signals_qs = PortfolioSignal.objects.filter(portfolio_entity__portfolio__institutional_account=institutional_account)
    opportunities_qs = AdvisoryOpportunity.objects.filter(portfolio_entity__portfolio__institutional_account=institutional_account)
    if portfolio is not None:
        signals_qs = signals_qs.filter(portfolio_entity__portfolio=portfolio)
        opportunities_qs = opportunities_qs.filter(portfolio_entity__portfolio=portfolio)

    top_clients = list(
        opportunities_qs.order_by('-priority_score')[:5]
        .values('portfolio_entity__name', 'headline', 'priority_score')
    )
    top_risks = list(
        signals_qs.order_by('-urgency_score')[:5]
        .values('portfolio_entity__name', 'title', 'urgency_score', 'capital_at_risk')
    )
    top_finance = list(
        opportunities_qs.filter(finance_readiness_score__isnull=False).order_by('-finance_readiness_score')[:5]
        .values('portfolio_entity__name', 'headline', 'finance_readiness_score')
    )

    verified_total = signals_qs.aggregate(total=db_models.Sum('verified_recovered_value'))['total'] or 0

    brief, _ = PortfolioDailyBrief.objects.get_or_create(
        institutional_account=institutional_account, brief_date=brief_date, defaults={},
    )
    brief.headline_summary = (
        f'{signals_qs.count()} signals analysed, {opportunities_qs.count()} opportunities identified.'
    )
    brief.top_clients_to_call = top_clients
    brief.top_portfolio_risks = top_risks
    brief.top_finance_opportunities = top_finance
    brief.new_signals_count = signals_qs.count()
    brief.human_approvals_pending = signals_qs.filter(human_approval_required=True).count()
    brief.verified_value_recovered_to_date = verified_total
    brief.save()
    return brief
