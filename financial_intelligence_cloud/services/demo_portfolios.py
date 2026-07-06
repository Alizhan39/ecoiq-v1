"""
financial_intelligence_cloud/services/demo_portfolios.py — assembles the 3
demo portfolios required by the spec, each clearly labelled DEMO
(InstitutionalAccount.is_demo=True by default). One flagship entity per
portfolio carries the worked-example numbers; the rest are deterministically
generated (see services/entity_generation.py) so re-seeding is idempotent.
"""
from financial_intelligence_cloud.services.accounts import (
    add_portfolio_entity, create_institutional_account, create_portfolio,
)
from financial_intelligence_cloud.services.capital_allocation_link import build_atlas_capital_allocation_portfolio
from financial_intelligence_cloud.services.demo_flagship_pipeline import build_freshbridge_foods_demo
from financial_intelligence_cloud.services.entity_generation import generate_portfolio_entities
from financial_intelligence_cloud.services.signals import detect_advisory_opportunity, generate_portfolio_signal

NORTHSTAR_SLUG = 'northstar-advisory'
ATLAS_SLUG = 'atlas-value-partners'
CIVIC_SLUG = 'civic-commercial-bank'


def build_northstar_advisory_demo():
    """50 SME clients: FreshBridge Foods (the one real-agent-pipeline flagship) + 49 generated."""
    account = create_institutional_account(
        NORTHSTAR_SLUG, 'Northstar Advisory', 'accounting_firm', subscription_tier='professional',
        relationship_owner='Partner: J. Whitfield',
    )
    portfolio = create_portfolio(
        account, 'SME Client Book', 'client_book', assets_under_analysis=32_000_000,
    )
    build_freshbridge_foods_demo(portfolio)
    generate_portfolio_entities(
        portfolio, count=49, capital_at_risk_ceiling=180000, entity_type='sme_client',
        signal_type='operational_loss',
    )
    return account, portfolio


def build_atlas_value_partners_demo():
    """12 industrial companies: the 4 real-ranked (via the real Capital Allocation ranking service) + 8 generated."""
    account = create_institutional_account(
        ATLAS_SLUG, 'Atlas Value Partners', 'private_equity', subscription_tier='institutional',
        relationship_owner='Partner: R. Osei',
    )
    portfolio = create_portfolio(
        account, 'Industrial Portfolio', 'investment_portfolio', assets_under_analysis=210_000_000,
    )
    build_atlas_capital_allocation_portfolio(portfolio)
    generate_portfolio_entities(
        portfolio, count=8, capital_at_risk_ceiling=90000, entity_type='portfolio_company',
        signal_type='asset_underperformance',
    )
    return account, portfolio


def build_civic_commercial_bank_demo():
    """500 business borrowers: ABC Engineering (the one worked Finance Opportunity Radar example) + 499 generated."""
    account = create_institutional_account(
        CIVIC_SLUG, 'Civic Commercial Bank', 'bank', subscription_tier='institutional',
        relationship_owner='Relationship Director: M. Idowu',
    )
    portfolio = create_portfolio(
        account, 'Business Loan Book', 'loan_book', assets_under_analysis=650_000_000,
    )

    entity = add_portfolio_entity(
        portfolio, 'ABC Engineering', 'borrower', sector='Light Manufacturing', relationship_stage='active',
    )
    signal = generate_portfolio_signal(
        entity, 'finance_opportunity', 'ABC Engineering: equipment replacement need',
        description='Equipment replacement need identified. Capital required: £750,000.',
        evidence_quality='strong', confidence=90, urgency_score=70, human_approval_required=True,
    )
    detect_advisory_opportunity(
        entity, 'finance_readiness_advisory', 'Equipment replacement — finance opportunity',
        linked_signal=signal,
        rationale=(
            'Equipment replacement need identified. Capital required: £750,000. Finance opportunity '
            'identified — this is not a credit approval.'
        ),
        finance_readiness_score=82, funding_gap=420000, currency='GBP',
        priority_score=82, requires_human_review=True, status='identified',
    )

    generate_portfolio_entities(
        portfolio, count=499, capital_at_risk_ceiling=600000, entity_type='borrower',
        signal_type='finance_opportunity',
    )
    return account, portfolio


def build_all_demo_portfolios():
    return {
        'northstar': build_northstar_advisory_demo(),
        'atlas': build_atlas_value_partners_demo(),
        'civic': build_civic_commercial_bank_demo(),
    }
