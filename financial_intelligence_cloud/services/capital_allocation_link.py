"""
financial_intelligence_cloud/services/capital_allocation_link.py — Atlas
Value Partners' "Where should the next £1 go?" mode. Thin adapter: calls the
REAL waste_to_value_capital_allocation_engine ranking service directly, on
the same 4-candidate fixture already regression-tested in
waste_to_value_capital_allocation_engine/tests.py::RankingTests — no forked
ranking logic, no new scoring mechanism. This is deliberate: proving the
same domain-agnostic ranking service produces the same ordering for a
second consumer is a stronger platform claim than inventing a fresh fixture.
"""
from financial_intelligence_cloud.services.accounts import add_portfolio_entity
from financial_intelligence_cloud.services.signals import detect_advisory_opportunity, generate_portfolio_signal
from waste_to_value_capital_allocation_engine.services.ranking import rank_capital_allocation_options

# Identical to waste_to_value_capital_allocation_engine/tests.py::RankingTests.CANDIDATES
# — same 4 projects, same 13 sub-scores, same regression-tested ordering.
ATLAS_PORTFOLIO_COMPANIES = [
    {'name': 'Cold-chain optimisation', 'financial_return': 85, 'capital_efficiency': 80, 'loss_avoided': 90,
     'recoverable_value': 88,
     'payback': 85, 'downside_risk': 80, 'evidence_quality': 85, 'mrv_readiness': 80, 'funding_readiness': 75,
     'asset_life_extension': 60, 'human_need_served': 50, 'harm_reduced': 50, 'maqasid_mizan_score': 60},
    {'name': 'Waste heat recovery', 'financial_return': 70, 'capital_efficiency': 65, 'loss_avoided': 70,
     'recoverable_value': 68,
     'payback': 60, 'downside_risk': 70, 'evidence_quality': 65, 'mrv_readiness': 60, 'funding_readiness': 65,
     'asset_life_extension': 70, 'human_need_served': 40, 'harm_reduced': 55, 'maqasid_mizan_score': 55},
    {'name': 'Boiler modernisation', 'financial_return': 60, 'capital_efficiency': 55, 'loss_avoided': 55,
     'recoverable_value': 55,
     'payback': 50, 'downside_risk': 60, 'evidence_quality': 60, 'mrv_readiness': 55, 'funding_readiness': 55,
     'asset_life_extension': 65, 'human_need_served': 35, 'harm_reduced': 45, 'maqasid_mizan_score': 50},
    {'name': 'Expansion project', 'financial_return': 50, 'capital_efficiency': 40, 'loss_avoided': 20,
     'recoverable_value': 25,
     'payback': 30, 'downside_risk': 40, 'evidence_quality': 45, 'mrv_readiness': 30, 'funding_readiness': 40,
     'asset_life_extension': 50, 'human_need_served': 30, 'harm_reduced': 20, 'maqasid_mizan_score': 35},
]


def build_atlas_capital_allocation_portfolio(portfolio):
    """
    Creates/updates one PortfolioEntity + PortfolioSignal + AdvisoryOpportunity
    per Atlas portfolio company, ranked by the real rank_capital_allocation_options().
    Returns the ranked list (with composite_score/rank annotated).
    """
    ranked = rank_capital_allocation_options(ATLAS_PORTFOLIO_COMPANIES)
    for candidate in ranked:
        entity = add_portfolio_entity(portfolio, candidate['name'], 'portfolio_company')
        signal = generate_portfolio_signal(
            entity, 'capital_allocation', f"{candidate['name']}: capital allocation ranking",
            description=f"Composite score {candidate['composite_score']}, rank {candidate['rank']} of {len(ranked)}.",
            evidence_quality='strong' if candidate['evidence_quality'] >= 80 else 'medium',
            confidence=candidate['evidence_quality'],
            urgency_score=candidate['loss_avoided'],
        )
        detect_advisory_opportunity(
            entity, 'capital_raise_support', f"Where should the next £1 go? — {candidate['name']}",
            linked_signal=signal,
            rationale=(
                f"Ranked #{candidate['rank']} of {len(ranked)} by the real Capital Allocation Agent ranking "
                f"service. This is a recommendation for investment-committee review, never an autonomous "
                f"investment decision."
            ),
            priority_score=candidate['composite_score'],
            requires_human_review=True,
        )
    return ranked
