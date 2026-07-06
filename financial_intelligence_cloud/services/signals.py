"""
financial_intelligence_cloud/services/signals.py — turns a portfolio entity's
underlying evidence into a PortfolioSignal, and a signal into an
AdvisoryOpportunity. Pure deterministic persistence + scoring helpers — no
agent calls here (those live in services/agent_bridge.py /
services/demo_flagship_pipeline.py for the one flagship case per portfolio).
"""
from financial_intelligence_cloud.models import AdvisoryOpportunity, PortfolioSignal

EVIDENCE_QUALITY_SCORE = {'strong': 90, 'medium': 60, 'weak': 30, 'missing': 10}


def generate_portfolio_signal(portfolio_entity, signal_type, title, **fields):
    """Idempotent via get_or_create keyed on (portfolio_entity, title)."""
    signal, _ = PortfolioSignal.objects.get_or_create(
        portfolio_entity=portfolio_entity, title=title, defaults={'signal_type': signal_type},
    )
    signal.signal_type = signal_type
    for field, value in fields.items():
        setattr(signal, field, value)
    signal.save()
    return signal


def detect_advisory_opportunity(portfolio_entity, opportunity_type, headline, linked_signal=None, **fields):
    """Idempotent via get_or_create keyed on (portfolio_entity, headline)."""
    opportunity, _ = AdvisoryOpportunity.objects.get_or_create(
        portfolio_entity=portfolio_entity, headline=headline, defaults={'opportunity_type': opportunity_type},
    )
    opportunity.opportunity_type = opportunity_type
    opportunity.linked_signal = linked_signal
    for field, value in fields.items():
        setattr(opportunity, field, value)
    opportunity.save()
    return opportunity


def evidence_quality_score(evidence_quality):
    """Maps the strong/medium/weak/missing vocabulary to a 0-100 score, reused everywhere a signal's evidence needs to feed a ranking composite."""
    return EVIDENCE_QUALITY_SCORE.get(evidence_quality, 50)
