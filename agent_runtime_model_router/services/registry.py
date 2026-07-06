"""
agent_runtime_model_router/services/registry.py — the real agent registry.

Discovers agents from `ai_agent_council.agents` (the single source of truth
for the 10 operational + 4 next-stage agents) and the real `ai_agents/`
folder on disk, then syncs `AgentRegistryEntry` rows idempotently.

Per-agent capabilities/task-types/input-types/reviewer-types are hand
-authored below rather than parsed out of each pack's markdown prose —
these packs were authored earlier in this same project and a fragile
markdown parser would be far more likely to mis-extract than a short,
accurate, human-written table. `expected_output_schema` reuses the one
canonical field list already established platform-wide in
`agent_training_evaluation_lab/views.py::AGENT_OUTPUT_SCHEMA_FIELDS`.
"""
import hashlib
from pathlib import Path

from django.conf import settings
from django.utils.text import slugify

from ai_agent_council.agents import (
    NEXT_STAGE_AGENTS, OPERATIONAL_AGENTS, REQUIRED_AGENT_FILES, _scan_ai_agents_repo_state,
)
from ai_agent_council.services.maturity import compute_maturity
from agent_runtime_model_router.models import AgentRegistryEntry

# Same shape as agent_training_evaluation_lab.views.AGENT_OUTPUT_SCHEMA_FIELDS
# — one canonical schema reused across the platform, not reinvented here.
BASE_OUTPUT_SCHEMA_FIELDS = [
    'agent_name', 'task_type', 'input_summary', 'output_summary', 'evidence_used',
    'missing_data', 'confidence', 'risk_flags', 'human_approval_required',
    'next_action', 'status',
]

AGENT_METADATA_BY_FOLDER = {
    'research_agent': {
        'capabilities': ['public_context_research', 'source_comparison'],
        'supported_task_types': ['site_context_research', 'sector_research'],
        'allowed_input_types': ['text', 'url'],
        'required_reviewer_types': [],
    },
    'document_reader_agent': {
        'capabilities': ['document_extraction', 'structured_data_extraction'],
        'supported_task_types': ['bill_extraction', 'quote_extraction', 'report_extraction'],
        'allowed_input_types': ['document', 'pdf', 'text'],
        'required_reviewer_types': [],
    },
    'photo_visual_evidence_agent': {
        'capabilities': ['visual_inspection', 'hypothesis_flagging'],
        'supported_task_types': ['site_photo_review', 'video_review'],
        'allowed_input_types': ['image', 'video'],
        'required_reviewer_types': ['technical_reviewer'],
    },
    'asset_passport_agent': {
        'capabilities': ['structured_asset_record_building'],
        'supported_task_types': ['asset_record_creation'],
        'allowed_input_types': ['structured_json', 'text'],
        'required_reviewer_types': [],
    },
    'industrial_playbook_matching_agent': {
        'capabilities': ['playbook_matching'],
        'supported_task_types': ['modernisation_pathway_matching'],
        'allowed_input_types': ['structured_json'],
        'required_reviewer_types': [],
    },
    'finance_modelling_agent': {
        'capabilities': ['finance_modelling', 'structured_output'],
        'supported_task_types': ['capex_opex_modelling', 'funding_gap_analysis'],
        'allowed_input_types': ['structured_json', 'document'],
        'required_reviewer_types': ['financial_reviewer'],
    },
    'mrv_agent': {
        'capabilities': ['impact_verification', 'baseline_assessment'],
        'supported_task_types': ['baseline_check', 'after_data_verification'],
        'allowed_input_types': ['structured_json', 'document'],
        'required_reviewer_types': ['mrv_reviewer'],
    },
    'governance_agent': {
        'capabilities': ['review_routing', 'safety_gatekeeping'],
        'supported_task_types': ['review_routing', 'wording_review'],
        'allowed_input_types': ['structured_json'],
        'required_reviewer_types': ['governance_reviewer'],
    },
    'report_generator_agent': {
        'capabilities': ['report_generation', 'evidence_linked_memo_building'],
        'supported_task_types': ['investor_memo', 'board_pack', 'public_summary'],
        'allowed_input_types': ['structured_json'],
        'required_reviewer_types': ['governance_reviewer'],
    },
    'amanah_autopilot_supervisor': {
        'capabilities': ['overnight_supervision', 'missing_evidence_detection'],
        'supported_task_types': ['overnight_portfolio_check'],
        'allowed_input_types': ['structured_json'],
        'required_reviewer_types': [],
    },
    'waste_leakage_agent': {
        'capabilities': ['loss_detection', 'capital_at_risk_quantification', 'evidence_classification'],
        'supported_task_types': ['loss_detection_and_quantification'],
        'allowed_input_types': ['structured_json', 'document', 'text'],
        'required_reviewer_types': [],
    },
    'capital_allocation_agent': {
        'capabilities': ['capital_ranking', 'multi_dimensional_scoring', 'governed_recommendation'],
        'supported_task_types': ['capital_allocation_ranking'],
        'allowed_input_types': ['structured_json'],
        'required_reviewer_types': [],
    },
}


def _compute_content_hash(folder_path):
    """Real SHA-256 over the concatenated bytes of the required files, in a fixed order."""
    digest = hashlib.sha256()
    found_any = False
    for filename in REQUIRED_AGENT_FILES:
        file_path = folder_path / filename
        if file_path.is_file():
            digest.update(file_path.read_bytes())
            found_any = True
    return digest.hexdigest() if found_any else ''


def discover_agents():
    """
    Returns a list of {agent_id, agent_name, training_pack_path, folder,
    content_hash, maturity, is_next_stage, metadata} for every agent in the
    real roster — 10 operational (from disk) + 4 next-stage (no folder).
    """
    repo_state = _scan_ai_agents_repo_state()
    base = Path(settings.BASE_DIR) / 'ai_agents'
    discovered = []

    for entry in OPERATIONAL_AGENTS:
        folder = entry['folder']
        folder_path = base / folder
        discovered.append({
            'agent_id': slugify(entry['name']),
            'agent_name': entry['name'],
            'folder': folder,
            'training_pack_path': f'ai_agents/{folder}',
            'content_hash': _compute_content_hash(folder_path),
            'maturity': compute_maturity(entry['name'], repo_state),
            'is_next_stage': False,
            'metadata': AGENT_METADATA_BY_FOLDER.get(folder, {}),
        })

    for entry in NEXT_STAGE_AGENTS:
        discovered.append({
            'agent_id': slugify(entry['name']),
            'agent_name': entry['name'],
            'folder': None,
            'training_pack_path': '',
            'content_hash': '',
            'maturity': compute_maturity(entry['name'], repo_state),
            'is_next_stage': True,
            'metadata': {},
        })

    return discovered


def sync_registry():
    """Idempotent: get_or_create + explicit field sync, never delete-then-recreate."""
    synced_ids = []

    for discovered in discover_agents():
        metadata = discovered['metadata']
        entry, _ = AgentRegistryEntry.objects.get_or_create(
            agent_id=discovered['agent_id'], defaults={'agent_name': discovered['agent_name']},
        )
        entry.agent_name = discovered['agent_name']
        entry.training_pack_path = discovered['training_pack_path']
        entry.content_hash = discovered['content_hash']
        entry.capabilities = metadata.get('capabilities', [])
        entry.supported_task_types = metadata.get('supported_task_types', [])
        entry.allowed_input_types = metadata.get('allowed_input_types', [])
        entry.expected_output_schema = {'fields': BASE_OUTPUT_SCHEMA_FIELDS}
        entry.required_reviewer_types = metadata.get('required_reviewer_types', [])
        entry.maturity_stage = discovered['maturity']['stage']
        entry.is_next_stage = discovered['is_next_stage']
        # Never falsely mark a next-stage agent as operational/enabled.
        entry.enabled = not discovered['is_next_stage']
        entry.save()
        synced_ids.append(entry.agent_id)

    AgentRegistryEntry.objects.exclude(agent_id__in=synced_ids).delete()
    return AgentRegistryEntry.objects.filter(agent_id__in=synced_ids)
