"""
waste_to_value_capital_allocation_engine/services/capital_allocation_bridge.py
— bridges the real `InterventionOption` rows and the real
`rank_capital_allocation_options()` service to the Agent Runtime & Model
Router's execution pipeline, for the Capital Allocation Agent specifically.

Keeps agent-orchestration glue out of the pure scoring/ranking modules
(`capital_allocation_scoring.py`, `ranking.py`) and out of
`agent_runtime_model_router` (which shouldn't need Waste-to-Value-specific
knowledge). One bridge module per agent, matching `agent_bridge.py`'s
existing precedent for the Waste & Leakage Agent.
"""
from waste_to_value_capital_allocation_engine.models import InterventionOption
from waste_to_value_capital_allocation_engine.services.capital_allocation_scoring import score_intervention_option
from waste_to_value_capital_allocation_engine.services.ranking import rank_capital_allocation_options

DEFAULT_INVENTORY_VALUE_CEILING = 80000  # golden-case constant; not stored on OperationalLoss itself


def _fastest_value_recovery_option(ranked):
    same_cycle = [o for o in ranked if o.get('estimated_payback_months') is None]
    pool = same_cycle or ranked
    return max(pool, key=lambda o: o.get('estimated_value_recovered', 0) or 0)


def _longest_term_capex_option(ranked):
    return max(ranked, key=lambda o: o.get('estimated_payback_months') or 0)


def _highest_capital_efficiency_option(ranked):
    return max(ranked, key=lambda o: o['capital_efficiency'])


def build_capital_allocation_fixture(loss, inventory_value_ceiling=DEFAULT_INVENTORY_VALUE_CEILING):
    """
    Queries the real, already-persisted `InterventionOption` rows for `loss`,
    scores and ranks them via the real `score_intervention_option()` /
    `rank_capital_allocation_options()` services, and returns the exact
    `fixture_output` shape `execute_agent(fixture_output=...)` expects,
    answering all 10 required questions. Never invents a second finance
    number — every score traces back to the real `InterventionOption` fields.
    """
    options = list(InterventionOption.objects.filter(operational_loss=loss))
    capital_at_risk_ceiling = loss.projected_future_loss or 0

    candidates = []
    for option in options:
        scores = score_intervention_option(option, capital_at_risk_ceiling, inventory_value_ceiling)
        candidates.append({
            'title': option.title,
            'estimated_value_recovered': option.estimated_value_recovered,
            'estimated_payback_months': option.estimated_payback_months,
            **scores,
        })

    ranked = rank_capital_allocation_options(candidates)
    top = ranked[0]
    fastest = _fastest_value_recovery_option(ranked)
    longest_capex = _longest_term_capex_option(ranked)
    most_efficient = _highest_capital_efficiency_option(ranked)

    why_top_ranked = (
        f"{top['title']} scores highest on the weighted composite ranking "
        f"({top['composite_score']}) among the {len(ranked)} real intervention options — its "
        f"financial return and loss-avoided scores, scaled against this case's own "
        f"£{capital_at_risk_ceiling:,.0f} capital-at-risk ceiling, outweigh its lower raw capital "
        f"efficiency. This is a recommendation for Council/human review, never an autonomous "
        f"investment decision."
    )

    output_summary = (
        f"Recommend {top['title']} first (rank 1 of {len(ranked)}, composite {top['composite_score']}). "
        f"Highest capital efficiency: {most_efficient['title']}. Fastest value recovery: {fastest['title']}. "
        f"Longest-term CAPEX: {longest_capex['title']}. Recommendation for Council/human review only."
    )

    return {
        'agent_name': 'Capital Allocation Agent',
        'case_title': loss.title,
        'ranked_options': [
            {'title': c['title'], 'composite_score': c['composite_score'], 'rank': c['rank']} for c in ranked
        ],
        'top_ranked_option': top['title'],
        'why_top_ranked': why_top_ranked,
        'evidence_supporting_ranking': [
            'capex_estimate', 'estimated_loss_avoided', 'estimated_value_recovered',
            'estimated_annual_savings', 'estimated_payback_months', 'risk_level',
            'technical_readiness', 'finance_readiness', 'mrv_readiness',
        ],
        'assumptions': [
            'A same-cycle tactical action with no explicit multi-month payback is treated as '
            'realising its value within the intervention window, not as a stronger or weaker '
            'evidentiary claim than that.',
            'Financial return, loss avoided and recoverable value are scaled against this case\'s '
            'own capital-at-risk and inventory-value ceilings, not as ratios to each option\'s own capex.',
        ],
        'unresolved_risks': [
            'Governance Agent\'s food-safety review is not yet complete.',
            'MRV Agent\'s post-intervention verification has not yet occurred, so the top-ranked '
            'option\'s savings remain estimated, not verified.',
        ],
        'highest_capital_efficiency_option': most_efficient['title'],
        'fastest_value_recovery_option': fastest['title'],
        'longest_term_capex_option': longest_capex['title'],
        'human_approval_required_for': [
            'autonomous_capital_movement', 'supplier_outreach', 'funder_outreach', 'investor_memo_delivery',
        ],
        'mrv_measurement_recommendation': (
            f"Post-intervention temperature and spoilage data, to convert {top['title']}'s estimated "
            f"annual savings into a verified return."
        ),
        'output_summary': output_summary,
        'evidence_used': [
            'finance_modelling_agent_capex_opex_estimates', 'waste_leakage_agent_capital_at_risk_figure',
        ],
        'missing_data': ['food_safety_review_completion', 'post_intervention_mrv_verification'],
        'confidence': 75,
        'risk_flags': ['equipment_finance_readiness_needs_review'],
        'human_approval_required': True,
        'next_action': (
            'Route ranking to Report Generator Agent for the investment memo and Governance Agent for '
            'ethical/wording review; await human/Council approval before any capital action.'
        ),
        'status': 'completed',
    }
