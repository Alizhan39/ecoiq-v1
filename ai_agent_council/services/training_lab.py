"""
ai_agent_council/services/training_lab.py — real ai_agents/*/test_cases.json readout.

The 8 spec scenario categories (normal, incomplete evidence, conflicting
evidence, adversarial input, permission denied, low confidence, cross-agent
disagreement, human override) have no per-case tag in the training packs
today. `load_agent_test_cases` maps existing case text onto these
categories by keyword matching — a heuristic categorisation of existing
fixture text, explicitly labelled as such (`is_heuristic: True`), never a
count the training pack itself promises or guarantees.
"""
import json
from pathlib import Path

from django.conf import settings

SCENARIO_CATEGORY_KEYWORDS = {
    'normal': ['draft', 'model', 'standard', 'summary', 'estimate', 'request'],
    'incomplete_evidence': ['missing', 'zero', 'incomplete', 'no evidence', 'blocked', 'gap'],
    'conflicting_evidence': ['conflicting', 'contradict', 'mismatch', 'disagreement', 'inconsistent'],
    'adversarial_input': ['guaranteed', 'asserting', 'certif', 'shariah-compliant', 'compliance'],
    'permission_denied': ['unauthorised', 'unauthorized', 'permission', 'restricted', 'confidential', 'access'],
    'low_confidence': ['low confidence', 'uncertain', 'insufficient', 'cannot verify', 'baseline incomplete'],
    'cross_agent_disagreement': ['another agent', 'disagree', 'handoff conflict'],
    'human_override': ['human', 'override', 'reviewer', 'approval'],
}


def _matched_categories(text):
    text_lower = text.lower()
    return [
        category for category, keywords in SCENARIO_CATEGORY_KEYWORDS.items()
        if any(keyword in text_lower for keyword in keywords)
    ]


def load_agent_test_cases(folder_name):
    """
    Reads ai_agents/<folder_name>/test_cases.json and returns real counts plus
    a heuristic scenario-category cross-reference. Returns empty structures
    (not an error) if the folder or file doesn't exist yet.
    """
    path = Path(settings.BASE_DIR) / 'ai_agents' / folder_name / 'test_cases.json'

    if not path.is_file():
        return {
            'realistic_test_cases': [],
            'failure_cases': [],
            'realistic_count': 0,
            'failure_count': 0,
            'scenario_category_matches': {category: [] for category in SCENARIO_CATEGORY_KEYWORDS},
            'is_heuristic': True,
        }

    data = json.loads(path.read_text())
    realistic_test_cases = data.get('realistic_test_cases', [])
    failure_cases = data.get('failure_cases', [])

    scenario_category_matches = {category: [] for category in SCENARIO_CATEGORY_KEYWORDS}
    for case in realistic_test_cases + failure_cases:
        text = ' '.join(str(value) for value in [
            case.get('title', ''),
            case.get('expected_behaviour', ''),
            json.dumps(case.get('expected_output', {})),
        ])
        case_label = case.get('id') or case.get('title', '')
        for category in _matched_categories(text):
            scenario_category_matches[category].append(case_label)

    return {
        'realistic_test_cases': realistic_test_cases,
        'failure_cases': failure_cases,
        'realistic_count': len(realistic_test_cases),
        'failure_count': len(failure_cases),
        'scenario_category_matches': scenario_category_matches,
        'is_heuristic': True,
    }
