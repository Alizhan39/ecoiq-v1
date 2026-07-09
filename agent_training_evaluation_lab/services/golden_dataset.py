"""
agent_training_evaluation_lab/services/golden_dataset.py — syncs the REAL
ai_agents/*/test_cases.json files into queryable GoldenDatasetCase rows.

Same idiom as agent_runtime_model_router.services.registry.sync_registry():
idempotent get_or_create + explicit field sync, never delete-then-recreate,
and a case removed from disk is genuinely removed here too (exclude().delete()).
Does not invent a single case — every row's input_summary/expected_properties
is copied verbatim from the real JSON file on disk.
"""
import json
from pathlib import Path

from django.conf import settings

from agent_training_evaluation_lab.models import GoldenDatasetCase


def _load_test_cases(folder):
    path = Path(settings.BASE_DIR) / 'ai_agents' / folder / 'test_cases.json'
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _expected_properties(case, case_type):
    if case_type == 'failure':
        return {'expected_behaviour': case.get('expected_behaviour', '')}
    expected = case.get('expected_output', {})
    return {
        'confidence': expected.get('confidence'),
        'human_approval_required': expected.get('human_approval_required'),
        'evidence_summary_includes': expected.get('evidence_summary_includes', []),
        'missing_data_includes': expected.get('missing_data_includes', []),
    }


def sync_golden_dataset():
    """Returns the queryset of GoldenDatasetCase rows synced from disk this call."""
    from agent_runtime_model_router.models import AgentRegistryEntry
    from agent_runtime_model_router.services.registry import sync_registry

    sync_registry()  # ensure AgentRegistryEntry rows/folders are current first
    synced_ids = []

    for entry in AgentRegistryEntry.objects.filter(is_next_stage=False):
        if not entry.training_pack_path:
            continue
        folder = entry.training_pack_path.split('/')[-1]
        data = _load_test_cases(folder)
        if not data:
            continue

        for case_type, key in (('realistic', 'realistic_test_cases'), ('failure', 'failure_cases')):
            for case in data.get(key, []):
                case_id = case.get('id', '')
                if not case_id:
                    continue
                row, _ = GoldenDatasetCase.objects.get_or_create(agent=entry, case_id=case_id, defaults={'case_type': case_type})
                row.case_type = case_type
                row.title = case.get('title', '')
                row.input_summary = case.get('input', {})
                row.expected_properties = _expected_properties(case, case_type)
                row.save()
                synced_ids.append(row.pk)

    GoldenDatasetCase.objects.exclude(pk__in=synced_ids).delete()
    return GoldenDatasetCase.objects.filter(pk__in=synced_ids)
