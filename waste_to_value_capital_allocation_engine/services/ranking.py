"""
waste_to_value_capital_allocation_engine/services/ranking.py — "Where should
the next £1 of capital go?"

Deterministic weighted composite across the 12 scored dimensions. This
prepares a governed recommendation for human review — it never makes a
financial allocation decision automatically.
"""
RANKING_WEIGHTS = {
    'financial_return':       0.14,
    'capital_efficiency':     0.12,
    'loss_avoided':           0.12,
    'payback':                0.10,  # caller passes an already-inverted "payback speed" goodness score
    'downside_risk':          0.09,  # caller passes an already-inverted "safety" goodness score
    'evidence_quality':        0.09,
    'mrv_readiness':           0.08,
    'funding_readiness':       0.08,
    'asset_life_extension':    0.06,
    'human_need_served':       0.04,
    'harm_reduced':            0.04,
    'maqasid_mizan_score':      0.04,
}


def _rank_investment_options(candidates):
    scored = []
    for candidate in candidates:
        composite = sum(RANKING_WEIGHTS[key] * candidate.get(key, 0) for key in RANKING_WEIGHTS)
        scored.append({**candidate, 'composite_score': round(composite, 2)})
    scored.sort(key=lambda c: c['composite_score'], reverse=True)
    for index, candidate in enumerate(scored, start=1):
        candidate['rank'] = index
    return scored


def rank_capital_allocation_options(candidates):
    """
    candidates: list of dicts with the 12 sub-scores (0-100 each, already
    normalized so higher is always better — e.g. 'payback' should be a
    payback-speed goodness score, not raw months; 'downside_risk' should
    already be inverted so higher = lower risk).
    Returns the same candidates sorted descending by weighted composite
    score, each annotated with 'composite_score' and 'rank'.
    """
    return _rank_investment_options(candidates)
