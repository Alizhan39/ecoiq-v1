"""
ai_agent_workbench/services/agent_data.py — read-only presentation layer over
the REAL agent registry and runtime data. This module creates no new Agent,
Run or Council models: it reads `AgentRegistryEntry` / `AgentRun`
(agent_runtime_model_router) and `ai_agent_council.agents` (the single
source of truth for the 12 operational agents), and never invents a metric
that isn't actually persisted — where nothing has been measured yet, callers
must show "NOT YET MEASURED" rather than a fabricated number.
"""
import json
from pathlib import Path

from django.conf import settings
from django.utils.text import slugify

from ai_agent_council.agents import OPERATIONAL_AGENTS
from agent_runtime_model_router.models import AgentRegistryEntry, AgentRun
from agent_runtime_model_router.services.registry import AGENT_METADATA_BY_FOLDER, sync_registry

# Short, human-authored "main question" each agent answers — used on the
# directory cards, the workbench task box and the recommender. Distinct from
# `role` (what the agent does) — this is the question a user would ask it.
MAIN_QUESTIONS = {
    'Research Agent':                          'What does the public evidence say?',
    'Document Reader Agent':                    'What do these documents actually say?',
    'Photo / Visual Evidence Agent':             'What does the visual evidence suggest?',
    'Asset Passport Agent':                      'What is the structured record of this asset?',
    'Industrial Playbook Matching Agent':        'Which modernisation pathway fits?',
    'Finance Modelling Agent':                   'What are the estimated economics?',
    'MRV Agent':                                 'What is actually verified?',
    'Governance Agent':                          'What must be blocked or reviewed?',
    'Report Generator Agent':                    'How should this be reported?',
    'Amanah Autopilot Supervisor':               "What needs a human's attention this morning?",
    'Waste & Leakage Agent':                     'Where is value being lost?',
    'Capital Allocation Agent':                  'Which option deserves capital first?',
}

# Short, human-authored output-type labels (the generic expected_output_schema
# field list is identical across agents and not descriptive on its own).
OUTPUT_TYPES = {
    'Research Agent':                          ['Evidence summary', 'Source list', 'Confidence level'],
    'Document Reader Agent':                    ['Extracted facts', 'Key figures', 'Evidence quality'],
    'Photo / Visual Evidence Agent':             ['Visual hypothesis notes', 'Needs-verification flags'],
    'Asset Passport Agent':                      ['Structured asset record', 'Missing data'],
    'Industrial Playbook Matching Agent':        ['Matched playbook', 'Quick wins', 'Deeper upgrades'],
    'Finance Modelling Agent':                   ['CAPEX/OPEX model', 'Payback estimate', 'Funding gap'],
    'MRV Agent':                                 ['Verified vs estimated split', 'Baseline readiness'],
    'Governance Agent':                          ['Review routing', 'Wording constraints'],
    'Report Generator Agent':                    ['Investor memo', 'Board pack', 'Public summary'],
    'Amanah Autopilot Supervisor':               ['Overnight review queue', 'Morning briefing'],
    'Waste & Leakage Agent':                     ['Capital-at-risk figure', 'Loss classification'],
    'Capital Allocation Agent':                  ['Ranked intervention list', 'Governed recommendation'],
}

HONEST_STATUS_OPERATIONAL         = 'Operational'
HONEST_STATUS_DEMO_AVAILABLE      = 'Demo Available'
HONEST_STATUS_EVALUATION_AVAILABLE = 'Evaluation Available'
HONEST_STATUS_HUMAN_REVIEW        = 'Human Review Required'
NOT_YET_MEASURED = 'NOT YET MEASURED'


def ensure_registry_synced():
    """Idempotent sync from disk/agents.py into AgentRegistryEntry — cheap, safe to call per-request."""
    return sync_registry()


def _golden_test_count(folder):
    if not folder:
        return 0, 0
    path = Path(settings.BASE_DIR) / 'ai_agents' / folder / 'test_cases.json'
    if not path.is_file():
        return 0, 0
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return 0, 0
    realistic = len(data.get('realistic_test_cases', []))
    failures = len(data.get('failure_cases', []))
    return realistic, failures


def _agent_run_stats(agent_entry):
    runs = AgentRun.objects.filter(agent=agent_entry)
    total = runs.count()
    if total == 0:
        return {
            'run_count': 0, 'failure_count': 0, 'schema_validity_rate': None,
            'human_review_ever_required': False, 'last_run': None,
        }
    failures = runs.exclude(status='completed').count()
    schema_checked = runs.exclude(schema_valid=None)
    schema_valid_rate = None
    if schema_checked.exists():
        schema_valid_rate = round(100 * schema_checked.filter(schema_valid=True).count() / schema_checked.count(), 1)
    return {
        'run_count': total,
        'failure_count': failures,
        'schema_validity_rate': schema_valid_rate,
        'human_review_ever_required': runs.filter(human_approval_required=True).exists(),
        'last_run': runs.order_by('-created_at').first(),
    }


def _honest_status(registry_entry, run_stats):
    if registry_entry.is_next_stage or not registry_entry.enabled:
        return HONEST_STATUS_EVALUATION_AVAILABLE
    if run_stats['run_count'] > 0:
        return HONEST_STATUS_OPERATIONAL
    return HONEST_STATUS_DEMO_AVAILABLE


def agent_directory_rows():
    """One row per real operational agent (the 12), honest status, real counts."""
    ensure_registry_synced()
    rows = []
    for entry in OPERATIONAL_AGENTS:
        agent_id = slugify(entry['name'])
        registry_entry = AgentRegistryEntry.objects.filter(agent_id=agent_id).first()
        if not registry_entry:
            continue
        realistic, failures = _golden_test_count(entry['folder'])
        run_stats = _agent_run_stats(registry_entry)
        rows.append({
            'number': entry['number'],
            'name': entry['name'],
            'slug': agent_id,
            'role': entry['role'],
            'main_question': MAIN_QUESTIONS.get(entry['name'], ''),
            'handoffs': entry['handoffs'],
            'important': entry['important'],
            'registry_entry': registry_entry,
            'golden_test_count': realistic + failures,
            'status': _honest_status(registry_entry, run_stats),
            'run_stats': run_stats,
            'evaluation_status': (
                f"{registry_entry.last_evaluation_score}%" if registry_entry.last_evaluation_score is not None
                else NOT_YET_MEASURED
            ),
            'metadata': AGENT_METADATA_BY_FOLDER.get(entry['folder'], {}),
            'output_types': OUTPUT_TYPES.get(entry['name'], []),
        })
    return rows


def _evaluation_summary(registry_entry):
    """
    Reads agent_training_evaluation_lab's real, already-computed evaluation
    data for this agent — creates nothing, computes nothing itself. Used only
    on the agent profile page (minimum necessary UI, not a Workbench redesign).
    """
    from agent_training_evaluation_lab.models import AgentEvaluationRun, AgentHumanFeedback, AgentRegression

    evaluation_history = list(
        AgentEvaluationRun.objects.filter(agent=registry_entry).order_by('-started_at')[:5]
    )
    latest = evaluation_history[0] if evaluation_history else None
    score_trend = (latest.score_delta or {}).get('overall_score') if latest else None

    open_regressions = AgentRegression.objects.filter(agent=registry_entry, is_acknowledged=False).order_by('-detected_at')

    feedback_qs = AgentHumanFeedback.objects.filter(agent_run__agent=registry_entry)
    feedback_counts = {}
    for classification, label in AgentHumanFeedback.CLASSIFICATION_CHOICES:
        count = feedback_qs.filter(classification=classification).count()
        if count:
            feedback_counts[label] = count

    return {
        'latest': latest,
        'history': evaluation_history,
        'score_trend': score_trend,
        'open_regression_count': open_regressions.count(),
        'open_regressions': list(open_regressions[:5]),
        'feedback_counts': feedback_counts,
        'feedback_total': feedback_qs.count(),
    }


def agent_profile_context(slug):
    """Full detail for one agent's profile page, or None if not a real operational agent."""
    for row in agent_directory_rows():
        if row['slug'] == slug:
            registry_entry = row['registry_entry']
            recent_runs = AgentRun.objects.filter(agent=registry_entry).select_related(
                'council_case',
            ).order_by('-created_at')[:8]
            row['recent_runs'] = recent_runs
            row['evaluation'] = _evaluation_summary(registry_entry)
            return row
    return None
