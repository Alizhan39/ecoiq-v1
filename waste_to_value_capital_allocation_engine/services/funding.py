"""
waste_to_value_capital_allocation_engine/services/funding.py — lifecycle
steps 8-9: identify the funding gap, match candidate capital routes.

Required distinction, enforced throughout: funding_route_identified !=
funding_secured. `match_capital_routes()` only ever proposes candidates —
it never marks a route as secured, and Islamic finance suitability is
never counted toward the confirmed remaining_gap until a qualified review
has taken place.
"""
from waste_to_value_capital_allocation_engine.models import CapitalRouteMatch, FundingGap

ROUTE_SUITABILITY_RULES = [
    ('grant_potential',                'grant',                   'Grant potential identified from stated candidate value.'),
    ('debt_potential',                  'equipment_finance',       'Debt-financeable CAPEX identified.'),
    ('equity_potential',                'impact_investment',       'Equity/impact-investment potential identified.'),
    ('supplier_finance_potential',       'supplier_finance',        'Supplier finance potential identified from supplier relationship.'),
    ('impact_finance_potential',         'green_loan',              'Impact/green-finance potential identified.'),
    ('islamic_finance_review_potential',  'islamic_finance_review',  'Islamic finance suitability requires qualified review before counting toward the gap.'),
]


def calculate_funding_gap(total_capital_required, owner_contribution=0, committed_capital=0,
                           grant_potential=0, debt_potential=0, equity_potential=0,
                           supplier_finance_potential=0, impact_finance_potential=0,
                           islamic_finance_review_potential=0):
    """
    remaining_gap = total_capital_required - (owner_contribution +
    committed_capital + grant + debt + equity + supplier_finance +
    impact_finance). islamic_finance_review_potential is NOT subtracted —
    it requires qualified review before it can be counted as available
    capital, so it is reported separately, never assumed.
    """
    confirmed_and_candidate_capital = (
        owner_contribution + committed_capital + grant_potential + debt_potential
        + equity_potential + supplier_finance_potential + impact_finance_potential
    )
    remaining_gap = round(total_capital_required - confirmed_and_candidate_capital, 2)
    return {
        'total_capital_required': total_capital_required,
        'owner_contribution': owner_contribution,
        'committed_capital': committed_capital,
        'grant_potential': grant_potential,
        'debt_potential': debt_potential,
        'equity_potential': equity_potential,
        'supplier_finance_potential': supplier_finance_potential,
        'impact_finance_potential': impact_finance_potential,
        'islamic_finance_review_potential': islamic_finance_review_potential,
        'remaining_gap': max(0, remaining_gap),
    }


def match_capital_routes(funding_gap: FundingGap):
    """
    Deterministic rule-based candidate matching — never funding approval.
    Creates/updates CapitalRouteMatch rows for whichever potentials on
    `funding_gap` are non-zero. Idempotent via get_or_create on
    (funding_gap, route_type).
    """
    matches = []
    for field_name, route_type, reason in ROUTE_SUITABILITY_RULES:
        potential = getattr(funding_gap, field_name, 0)
        if not potential:
            continue

        suitability_score = min(100, round((potential / funding_gap.total_capital_required) * 100)) if funding_gap.total_capital_required else 0
        eligibility_status = 'needs_review' if route_type == 'islamic_finance_review' else 'eligible'

        match, _ = CapitalRouteMatch.objects.get_or_create(
            funding_gap=funding_gap, route_type=route_type, defaults={},
        )
        match.suitability_score = suitability_score
        match.match_reason = reason
        match.eligibility_status = eligibility_status
        match.due_diligence_status = 'not_started'
        match.human_approval_required = True
        match.save()
        matches.append(match)

    return matches
