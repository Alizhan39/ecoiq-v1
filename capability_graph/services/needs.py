"""
capability_graph/services/needs.py — REAL-WORLD NEED -> REQUIRED
CAPABILITY, the second node in the chain. A deterministic lookup table
over already-existing `good_agents.Need.need_type` / `GoodOpportunity.theme`
values, exactly like PR3's keyword-overlap scoring — no ML, no LLM call,
no new persisted "requirement" table. A need never silently requires zero
capabilities: anything not explicitly mapped falls back to a conservative
default (COORDINATE + REFER — "route this to someone who can figure out
what's needed") rather than crashing or fabricating a specific one.
"""

DEFAULT_CAPABILITIES = ('coordinate', 'refer')

# good_agents.Need.NEED_TYPE_CHOICES vocabulary.
REQUIRED_CAPABILITIES_BY_NEED_TYPE = {
    'energy': ('fund', 'grant', 'install', 'supply', 'provide_technology', 'provide_expertise'),
    'water': ('fund', 'install', 'supply', 'regulate', 'authorise'),
    'food': ('supply', 'donate', 'transport', 'coordinate'),
    'housing': ('fund', 'grant', 'install', 'permit', 'authorise'),
    'health': ('fund', 'provide_expertise', 'train', 'respond_to_emergency'),
    'education': ('train', 'fund', 'host', 'provide_expertise'),
    'employment': ('employ', 'train', 'refer'),
    'justice': ('regulate', 'authorise', 'refer', 'audit'),
    'environment': ('regulate', 'audit', 'verify', 'measure', 'research'),
    'biodiversity': ('research', 'measure', 'verify', 'regulate'),
    'waste': ('collect', 'recycle', 'reuse', 'transport', 'permit'),
    'climate': ('research', 'measure', 'fund', 'respond_to_emergency', 'authorise'),
    'infrastructure': ('fund', 'procure', 'install', 'manufacture', 'permit'),
    'digital_access': ('supply', 'provide_technology', 'install', 'train'),
    'financial_inclusion': ('fund', 'lend', 'grant'),
    'community_resilience': ('coordinate', 'train', 'host', 'respond_to_emergency'),
}

# GoodOpportunity.GOOD_TAXONOMY_CHOICES vocabulary — a distinct, overlapping
# but not identical set from Need.NEED_TYPE_CHOICES, so kept as its own table
# rather than forced to share one dict with mismatched keys.
REQUIRED_CAPABILITIES_BY_THEME = {
    **REQUIRED_CAPABILITIES_BY_NEED_TYPE,
    'poverty': ('fund', 'grant', 'donate', 'coordinate'),
    'circular_economy': ('collect', 'recycle', 'reuse', 'supply', 'manufacture'),
    'climate_adaptation': ('research', 'measure', 'fund', 'respond_to_emergency', 'authorise'),
    'government_efficiency': ('coordinate', 'audit', 'regulate'),
}


def required_capabilities_for_need_type(need_type):
    return REQUIRED_CAPABILITIES_BY_NEED_TYPE.get(need_type, DEFAULT_CAPABILITIES)


def required_capabilities_for_theme(theme):
    return REQUIRED_CAPABILITIES_BY_THEME.get(theme, DEFAULT_CAPABILITIES)
