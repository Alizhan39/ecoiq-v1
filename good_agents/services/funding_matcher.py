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

# PR7 — which Capability Graph capability a funder_type category maps to,
# so a FundingMatch can be enriched with a REAL organisation when (and
# only when) the graph has evidence-backed data for one. Deliberately a
# small, explicit mapping, not an inference from the funder_type string.
FUNDER_TYPE_TO_CAPABILITY = {
    'government_programme': 'fund', 'grant': 'grant', 'development_finance': 'lend',
    'impact_investor': 'fund', 'family_office': 'fund', 'philanthropy': 'donate',
    'waqf': 'donate', 'islamic_finance': 'fund', 'green_finance': 'fund', 'corporate': 'fund',
}

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


def enrich_with_capability_graph(funding_match, *, jurisdiction=None):
    """
    PR7 — resolves `funding_match.organisation` to a real Capability Graph
    organisation ONLY when exactly one evidence-backed match exists for
    the mapped capability; leaves it null (never guesses among several
    candidates, never fabricates one where the graph has none yet — which
    today is the common case, since no real funder database is connected).
    """
    from capability_graph.services.matcher import find_organisations_for_capability

    capability = FUNDER_TYPE_TO_CAPABILITY.get(funding_match.funder_type)
    if capability is None or funding_match.organisation_id:
        return funding_match
    matches = list(find_organisations_for_capability(capability, jurisdiction=jurisdiction))
    if len(matches) == 1:
        funding_match.organisation = matches[0].organisation
        funding_match.save(update_fields=['organisation'])
    return funding_match
