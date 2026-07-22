"""
good_agents/services/funding_matcher.py — FundingMatcher (PR3 Phase 11).

No real grant/investor database exists in this repo (confirmed in the PR3
Phase 0 verification — only finance-scoped opportunity models exist
elsewhere, none of them a funder directory). This matcher is therefore
deliberately conservative: it never asserts `eligible` on its own, and any
waqf/Islamic-finance funder type is routed to `requires_sharia_review`
unconditionally (enforced structurally in `FundingMatch.save()`, not just
by this service).
"""
from good_agents.models import FundingMatch

# A funder type is only worth recording against an opportunity if the
# opportunity's theme plausibly fits — avoids spamming a "green finance"
# match onto an unrelated justice opportunity.
FUNDER_TYPE_RELEVANT_THEMES = {
    'government_programme': None,  # None = potentially relevant to any theme
    'grant': None,
    'development_finance': {'energy', 'water', 'food', 'housing', 'health', 'infrastructure', 'climate_adaptation'},
    'impact_investor': {'energy', 'financial_inclusion', 'circular_economy', 'digital_access'},
    'family_office': None,
    'philanthropy': None,
    'waqf': None,
    'islamic_finance': {'financial_inclusion', 'housing', 'employment'},
    'green_finance': {'energy', 'environment', 'climate_adaptation', 'biodiversity', 'waste'},
    'corporate': None,
}


def suggest_funding_matches(opportunity, funder_types=None):
    """
    Creates a FundingMatch per relevant funder_type (all of them if none
    specified), each starting at 'potentially_relevant' or
    'eligibility_unknown' — never higher without real evidence supplied by
    the caller. Idempotent per (opportunity, funder_type): re-running does
    not duplicate.
    """
    funder_types = funder_types or list(FUNDER_TYPE_RELEVANT_THEMES.keys())
    created = []
    for funder_type in funder_types:
        relevant_themes = FUNDER_TYPE_RELEVANT_THEMES.get(funder_type)
        if relevant_themes is not None and opportunity.theme and opportunity.theme not in relevant_themes:
            continue

        status = 'requires_sharia_review' if funder_type in FundingMatch.SHARIA_SENSITIVE_FUNDER_TYPES else 'potentially_relevant'
        match, _ = FundingMatch.objects.get_or_create(
            opportunity=opportunity, funder_type=funder_type,
            defaults=dict(
                eligibility_status=status,
                notes=(
                    'No real funder database is connected yet — this is a category-level suggestion for human '
                    'research, not a verified eligible funder.'
                ),
            ),
        )
        created.append(match)
    return created
