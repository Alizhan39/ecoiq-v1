"""
ai_agent_workbench/services/demo_cases.py — the 3 pre-seeded demo cases the
workbench lets a visitor pick from. Every case here points at a REAL,
already-persisted `CouncilRun` (or ranked portfolio) built by an existing
seed command — no new demo logic, no hand-authored AgentRun rows. If the
underlying seed command hasn't been run yet, `council_run` / `ranked_options`
will simply come back empty and the template must say so honestly rather
than inventing output.

- Kazakhstan Clean Heat  -> khalifa_stewardship_tour_operating_system
  (seed_khalifa_stewardship_demo)
- Meat Cold-Chain Loss   -> waste_to_value_capital_allocation_engine
  (seed_waste_to_value_demo)
- Investment Portfolio   -> financial_intelligence_cloud's Atlas Value
  Partners ranked portfolio (seed_financial_intelligence_cloud_demo),
  reusing waste_to_value_capital_allocation_engine.services.ranking directly
"""
from ai_agent_council.models import CouncilRun

KAZAKHSTAN_CLEAN_HEAT = 'kazakhstan-clean-heat'
MEAT_COLD_CHAIN = 'meat-cold-chain-loss'
INVESTMENT_PORTFOLIO = 'investment-portfolio'

DEMO_CASES = {
    KAZAKHSTAN_CLEAN_HEAT: {
        'slug': KAZAKHSTAN_CLEAN_HEAT,
        'title': 'Kazakhstan Clean Heat',
        'question': 'Which intervention deserves support before this stewardship tour can launch?',
        'council_run_slug': 'kazakhstan-clean-heat-stewardship-demo',
        'agents_involved': [
            'Research Agent', 'Document Reader Agent', 'Photo / Visual Evidence Agent',
            'Waste & Leakage Agent', 'Asset Passport Agent', 'Industrial Playbook Matching Agent',
            'Finance Modelling Agent', 'Capital Allocation Agent', 'MRV Agent',
            'Governance Agent', 'Report Generator Agent', 'Amanah Autopilot Supervisor',
        ],
    },
    MEAT_COLD_CHAIN: {
        'slug': MEAT_COLD_CHAIN,
        'title': 'Meat Cold-Chain Loss',
        'question': 'What value is at risk and which intervention deserves capital first?',
        'council_run_slug': 'meat-cold-chain-loss-prevention-demo',
        'known_facts': [
            '£80,000 inventory', '15% historical exposure', '36-hour intervention window',
        ],
        'agents_involved': [
            'Waste & Leakage Agent', 'Document Reader Agent', 'Photo / Visual Evidence Agent',
            'Asset Passport Agent', 'Industrial Playbook Matching Agent', 'Finance Modelling Agent',
            'MRV Agent', 'Governance Agent', 'Report Generator Agent', 'Amanah Autopilot Supervisor',
            'Capital Allocation Agent',
        ],
    },
    INVESTMENT_PORTFOLIO: {
        'slug': INVESTMENT_PORTFOLIO,
        'title': 'Investment Portfolio',
        'question': 'Where should the next £1 go?',
        'council_run_slug': None,  # ranked directly, not via a CouncilRun — see ranked_options()
        'atlas_account_slug': 'atlas-value-partners',
        'agents_involved': ['Capital Allocation Agent'],
    },
}


def get_demo_case(slug):
    return DEMO_CASES.get(slug)


def council_run_for_case(demo_case):
    """Returns the real, persisted CouncilRun for a demo case, or None if not seeded yet."""
    council_run_slug = demo_case.get('council_run_slug')
    if not council_run_slug:
        return None
    return CouncilRun.objects.filter(slug=council_run_slug).prefetch_related(
        'tasks', 'handoffs', 'disagreements', 'agent_runs',
    ).first()


def ranked_investment_options(demo_case):
    """
    Investment Portfolio case: reuses the real, already-seeded Atlas Value
    Partners portfolio (financial_intelligence_cloud) — the same
    rank_capital_allocation_options() service the Capital Allocation Agent
    uses elsewhere produced these AdvisoryOpportunity rows, ordered by the
    real `priority_score` (composite_score). Returns [] if the demo hasn't
    been seeded yet.
    """
    account_slug = demo_case.get('atlas_account_slug')
    if not account_slug:
        return []
    from financial_intelligence_cloud.models import AdvisoryOpportunity, InstitutionalAccount

    account = InstitutionalAccount.objects.filter(slug=account_slug).first()
    if not account:
        return []
    portfolio = account.portfolios.first()
    if not portfolio:
        return []
    return list(
        AdvisoryOpportunity.objects
        .filter(portfolio_entity__portfolio=portfolio, opportunity_type='capital_raise_support')
        .select_related('portfolio_entity')
        .order_by('-priority_score')
    )
