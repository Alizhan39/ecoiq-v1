"""
good_agents/services/agent_groups.py — dynamic operational working groups
(PR3 Phase 24). Purely a runtime clustering label over the canonical 114
principles' `category` field — never a replacement for the canonical
principle numbering, never persisted as a separate model.
"""
# Maps core.esg_principles_data.PRINCIPLE_CATEGORIES ids to one of 8
# operational groups. Every one of the 10 canonical categories is placed in
# exactly one group.
CATEGORY_TO_GROUP = {
    'governance': 'Governance & Accountability',
    'economy': 'Economic Responsibility',
    'social': 'Justice & Human Dignity',
    'earth': 'Environment & Balance',
    'justice': 'Justice & Human Dignity',
    'risk': 'Resilience & Future Generations',
    'knowledge': 'Knowledge & Truth',
    'human': 'Community & Social Welfare',
    'community': 'Community & Social Welfare',
    'longterm': 'Resilience & Future Generations',
}

OPERATIONAL_GROUPS = [
    'Justice & Human Dignity', 'Resource Stewardship', 'Economic Responsibility',
    'Environment & Balance', 'Community & Social Welfare', 'Governance & Accountability',
    'Knowledge & Truth', 'Resilience & Future Generations',
]


def group_for_category(category):
    return CATEGORY_TO_GROUP.get(category, 'Resource Stewardship')


def group_agent_definitions(definitions):
    """definitions: iterable of GoodAgentDefinition. Returns {group_name: [definitions...]}."""
    groups = {name: [] for name in OPERATIONAL_GROUPS}
    for definition in definitions:
        groups[group_for_category(definition.category)].append(definition)
    return groups
