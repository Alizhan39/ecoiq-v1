"""
ai_agent_workbench/services/recommender.py — recommend_agent_for_task().

Deliberately NOT a live LLM classifier: this is a deterministic keyword rule
table over the natural-language task box (homepage §14/§15). Building a real
NLU classifier would mean creating another inference runtime, which the spec
explicitly rules out — a transparent, inspectable rule table is also more
honest for a public demo than a black-box guess. Recommends only; never
auto-runs anything.
"""
# Ordered: first matching rule wins. Each rule: (keywords, agent_name, why, supporting_agents)
RULES = [
    (
        ['deserve capital', 'deserves capital', 'where should the next', 'fund first', 'which project'],
        'Capital Allocation Agent',
        'The question compares competing uses of capital.',
        ['Finance Modelling Agent', 'MRV Agent', 'Governance Agent'],
    ),
    (
        ['missing from these documents', 'missing information', 'what information is missing', 'extract the facts'],
        'Document Reader Agent',
        'The question is about what the source documents actually contain.',
        ['Research Agent'],
    ),
    (
        ['value being lost', 'where is value', 'losing value', 'loss detection', 'value at risk'],
        'Waste & Leakage Agent',
        'The question is about detecting and quantifying operational loss.',
        ['Document Reader Agent', 'Finance Modelling Agent'],
    ),
    (
        ['actually verified', 'is verified', 'verified impact', 'verified or estimated'],
        'MRV Agent',
        'The question is about separating verified fact from estimate.',
        ['Governance Agent'],
    ),
    (
        ['why did the agents disagree', 'why did they disagree', 'disagreement', 'cross-examin'],
        'Governance Agent',
        'The question is about how a Council disagreement was resolved.',
        ['Capital Allocation Agent'],
    ),
    (
        ['human approve', 'needs approval', 'must a human', 'sign off', 'sign-off'],
        'Governance Agent',
        'The question is about which outputs require human review before release.',
        ['Report Generator Agent'],
    ),
    (
        ['estimated economics', 'capex', 'opex', 'payback', 'funding gap', 'financial model'],
        'Finance Modelling Agent',
        'The question is about draft financial modelling.',
        ['MRV Agent'],
    ),
    (
        ['photo', 'visual', 'inspection image', 'video review'],
        'Photo / Visual Evidence Agent',
        'The question concerns visual/photographic evidence.',
        ['Asset Passport Agent'],
    ),
    (
        ['playbook', 'modernisation pathway', 'quick win', 'upgrade path'],
        'Industrial Playbook Matching Agent',
        'The question is about matching an asset to a modernisation pathway.',
        ['Finance Modelling Agent'],
    ),
    (
        ['asset record', 'asset passport', 'structured record'],
        'Asset Passport Agent',
        'The question is about the structured digital record of an asset.',
        ['Industrial Playbook Matching Agent'],
    ),
    (
        ['overnight', 'morning briefing', 'review queue'],
        'Amanah Autopilot Supervisor',
        'The question is about overnight supervision and the morning review queue.',
        [],
    ),
    (
        ['report', 'investor memo', 'board pack', 'public summary'],
        'Report Generator Agent',
        'The question is about producing an evidence-linked report or memo.',
        ['Governance Agent'],
    ),
]

DEFAULT_RECOMMENDATION = (
    'Research Agent',
    'No sharper match found — Research Agent is the general entry point for gathering evidence first.',
    ['Document Reader Agent'],
)


def recommend_agent_for_task(task_text):
    """
    Returns {agent_name, why, supporting_agents, matched} for a free-text
    task question. Never runs anything — recommendation only, confirmed by
    the user before any agent executes (see workbench view).
    """
    text = (task_text or '').strip().lower()
    if not text:
        return {'agent_name': None, 'why': '', 'supporting_agents': [], 'matched': False}

    for keywords, agent_name, why, supporting in RULES:
        for kw in keywords:
            if kw in text:
                return {'agent_name': agent_name, 'why': why, 'supporting_agents': supporting, 'matched': True}

    agent_name, why, supporting = DEFAULT_RECOMMENDATION
    return {'agent_name': agent_name, 'why': why, 'supporting_agents': supporting, 'matched': False}
