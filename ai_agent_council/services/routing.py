"""
ai_agent_council/services/routing.py — deterministic agent routing.

Proves the Council does not activate all 10 operational agents for every
task: given a task_category, a fixed lookup table decides who is selected
and gives an explicit reason for every agent NOT selected too. No
randomness, no scoring model, no LLM call — a task_category with no entry
in TASK_CATEGORY_AGENT_PLANS selects nobody and says so honestly.
"""
from ai_agent_council.agents import OPERATIONAL_AGENT_NAMES

# Each plan lists only the agents that differ from the default "not needed
# for this task category" reason, keeping each plan focused on what makes
# that task category distinctive.
TASK_CATEGORY_AGENT_PLANS = {
    'industrial_asset_modernisation': {
        'selected': {
            'Research Agent': 'Establishes public/site context before any other agent reads evidence.',
            'Document Reader Agent': 'Extracts facts from fuel bills and the supplier quote.',
            'Photo / Visual Evidence Agent': 'Site inspection photos exist for this asset and need review.',
            'Asset Passport Agent': 'A new/updated structured asset record is required for this decision.',
            'Industrial Playbook Matching Agent': 'The asset needs matching against modernisation playbooks.',
            'Finance Modelling Agent': 'A capital decision requires a draft CAPEX/OPEX/payback model.',
            'MRV Agent': 'Any efficiency claim requires a baseline/after-data verification check.',
            'Governance Agent': 'Finance- and MRV-sensitive outputs require a routed review.',
            'Report Generator Agent': 'A decision memo is the required output of this task category.',
        },
        'not_selected': {
            'Amanah Autopilot Supervisor': (
                'Runs overnight across the whole portfolio; not scoped to a single decision run.'
            ),
        },
    },
    'decision_reopening_review': {
        'selected': {
            'Research Agent': 'New public context (e.g. grid capacity data) must be re-checked.',
            'Document Reader Agent': 'The new evidence document must be read and extracted.',
            'MRV Agent': 'The verification status that blocked the original decision must be re-assessed.',
            'Governance Agent': 'A decision reopening always requires a routed governance review.',
        },
        'not_selected': {
            'Photo / Visual Evidence Agent': 'No new site inspection was performed for this review.',
            'Asset Passport Agent': 'The underlying asset record is unchanged.',
            'Industrial Playbook Matching Agent': 'No new playbook match is required to re-review a decision.',
            'Finance Modelling Agent': 'No new financial terms are in scope for this review.',
            'Report Generator Agent': 'This is a scoped re-review, not a new investor memo.',
            'Amanah Autopilot Supervisor': 'This is a scoped, human-triggered review, not a routine overnight sweep.',
        },
    },
}

DEFAULT_NOT_SELECTED_REASON = 'Not required for this task category.'
UNKNOWN_CATEGORY_REASON = 'Task category not recognised — no agent routed automatically; requires human triage.'


def select_agents_for_task(task_category):
    """Returns one {'agent_name', 'selected', 'reason'} entry per operational agent."""
    plan = TASK_CATEGORY_AGENT_PLANS.get(task_category)

    results = []
    for agent_name in OPERATIONAL_AGENT_NAMES:
        if plan is None:
            results.append({'agent_name': agent_name, 'selected': False, 'reason': UNKNOWN_CATEGORY_REASON})
            continue

        if agent_name in plan['selected']:
            results.append({'agent_name': agent_name, 'selected': True, 'reason': plan['selected'][agent_name]})
        else:
            reason = plan['not_selected'].get(agent_name, DEFAULT_NOT_SELECTED_REASON)
            results.append({'agent_name': agent_name, 'selected': False, 'reason': reason})

    return results
