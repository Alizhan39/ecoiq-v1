"""
agent_runtime_model_router/services/training_pack_loader.py — real training
pack loading and validation, reading straight from `ai_agents/<folder>/`.

No fragile markdown-to-schema parsing: each file's raw text is exposed
under a semantic alias (system_prompt, task_prompt, output_schema,
safety_rules, evaluation_rubric), and `test_cases.json` is parsed as real
JSON. This is honest about what the packs actually contain today — prose
files, not machine schemas — rather than pretending a parser extracted
structure that isn't really there.
"""
import json
from pathlib import Path

from django.conf import settings

from ai_agent_council.agents import AGENT_NAME_TO_FOLDER, REQUIRED_AGENT_FILES

FILE_ALIASES = {
    'system_prompt':     'system_prompt.md',
    'task_prompt':       'role.md',
    'output_schema':     'outputs.md',
    'safety_rules':       'safety_rules.md',
    'human_approval_rules': 'safety_rules.md',
    'evaluation_rubric':   'evals.md',
    'inputs':             'inputs.md',
    'tools':              'tools.md',
    'demo_scenarios':      'demo_scenarios.md',
    'readme':             'README.md',
}


def load_training_pack(agent_name):
    """
    Returns {agent_name, folder, files: {filename: text}, aliases: {...},
    test_cases: parsed dict or None, test_cases_error: str or ''}.
    """
    folder = AGENT_NAME_TO_FOLDER.get(agent_name)
    base = Path(settings.BASE_DIR) / 'ai_agents' / (folder or '')

    files = {}
    for filename in REQUIRED_AGENT_FILES:
        file_path = base / filename
        if file_path.is_file():
            files[filename] = file_path.read_text()

    aliases = {alias: files.get(filename, '') for alias, filename in FILE_ALIASES.items()}

    test_cases = None
    test_cases_error = ''
    raw_test_cases = files.get('test_cases.json')
    if raw_test_cases is not None:
        try:
            test_cases = json.loads(raw_test_cases)
        except json.JSONDecodeError as exc:
            test_cases_error = str(exc)

    return {
        'agent_name': agent_name,
        'folder': folder,
        'files': files,
        'aliases': aliases,
        'test_cases': test_cases,
        'test_cases_error': test_cases_error,
    }


def validate_training_pack(agent_name):
    """
    Returns {valid, required_files_present, missing_files, test_cases_json_valid,
    agent_identity_consistent, schema_exists, safety_rules_exist}.
    """
    pack = load_training_pack(agent_name)
    missing_files = [f for f in REQUIRED_AGENT_FILES if f not in pack['files']]
    required_files_present = len(missing_files) == 0

    test_cases_json_valid = pack['test_cases'] is not None and not pack['test_cases_error']

    agent_identity_consistent = (
        test_cases_json_valid and pack['test_cases'].get('agent_name') == agent_name
    )

    schema_exists = bool(pack['aliases']['output_schema'].strip())
    safety_rules_exist = bool(pack['aliases']['safety_rules'].strip())

    valid = (
        required_files_present and test_cases_json_valid and agent_identity_consistent
        and schema_exists and safety_rules_exist
    )

    return {
        'valid': valid,
        'required_files_present': required_files_present,
        'missing_files': missing_files,
        'test_cases_json_valid': test_cases_json_valid,
        'agent_identity_consistent': agent_identity_consistent,
        'schema_exists': schema_exists,
        'safety_rules_exist': safety_rules_exist,
    }
