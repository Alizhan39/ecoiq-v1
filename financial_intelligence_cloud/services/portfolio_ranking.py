"""
financial_intelligence_cloud/services/portfolio_ranking.py — "Who should I
call today?" / "Where is value at risk?" / "Which finance opportunity is
most ready?"

Deterministic weighted composites, mirroring
waste_to_value_capital_allocation_engine/services/ranking.py's
_rank_investment_options() shape exactly (named differently — not
`ranking.py` — so both modules can be imported side by side, e.g. in
services/capital_allocation_link.py, without a name collision). These
functions never make a decision automatically — a ranking is always advisory
input for a human relationship owner or portfolio manager to act on.

Candidates are plain dicts with the sub-scores below (0-100 each, already
normalized so higher is always better) — callers (services/demo_portfolios.py,
services/entity_generation.py, services/demo_flagship_pipeline.py) are
responsible for deriving those sub-scores from real PortfolioSignal /
AdvisoryOpportunity fields before calling these functions, and for writing
the resulting composite_score back onto AdvisoryOpportunity.priority_score.
"""
CLIENT_CALL_WEIGHTS = {
    'urgency':                      0.25,
    'capital_at_risk_normalised':    0.20,
    'recoverable_value_normalised':   0.20,
    'evidence_quality':              0.15,
    'relationship_importance':        0.10,
    'data_freshness':                0.10,
}

PORTFOLIO_RISK_WEIGHTS = {
    'urgency':                    0.30,
    'capital_at_risk_normalised':  0.30,
    'evidence_quality':            0.15,
    'human_approval_need':         0.15,
    'data_freshness':              0.10,
}

FINANCE_OPPORTUNITY_WEIGHTS = {
    'finance_readiness':            0.35,
    'recoverable_value_normalised':  0.25,
    'evidence_quality':              0.20,
    'urgency':                       0.10,
    'data_freshness':                0.10,
}


def _rank(candidates, weights):
    scored = []
    for candidate in candidates:
        composite = sum(weights[key] * candidate.get(key, 0) for key in weights)
        scored.append({**candidate, 'composite_score': round(composite, 2)})
    scored.sort(key=lambda c: c['composite_score'], reverse=True)
    for index, candidate in enumerate(scored, start=1):
        candidate['rank'] = index
    return scored


def rank_clients_to_call_today(candidates):
    """candidates: list of dicts with the 6 CLIENT_CALL_WEIGHTS sub-scores."""
    return _rank(candidates, CLIENT_CALL_WEIGHTS)


def rank_portfolio_risks(candidates):
    """candidates: list of dicts with the 5 PORTFOLIO_RISK_WEIGHTS sub-scores."""
    return _rank(candidates, PORTFOLIO_RISK_WEIGHTS)


def rank_finance_opportunities(candidates):
    """candidates: list of dicts with the 5 FINANCE_OPPORTUNITY_WEIGHTS sub-scores."""
    return _rank(candidates, FINANCE_OPPORTUNITY_WEIGHTS)
