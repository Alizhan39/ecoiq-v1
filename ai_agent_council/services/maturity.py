"""
ai_agent_council/services/maturity.py — Agent Training Maturity, stages 0-7.

Each stage is a measurable, checkable gate — never a self-reported label.
Stage 7 ("Production Monitored") is a permanent, hardcoded False: this
repository has no live production telemetry, so no agent can honestly claim
that stage today. This can never regress into a false claim because it
never depends on seeded data.
"""
from django.db.models import Q

from ai_agent_council.agents import AGENT_NAME_TO_FOLDER, OPERATIONAL_AGENT_NAMES

STAGE_LABELS = [
    'Defined', 'Prompted', 'Training Pack Complete', 'Scenario Tested',
    'Cross-Agent Tested', 'Human Reviewed', 'Operationally Ready', 'Production Monitored',
]

STAGE_7_BLOCKED_REASON = (
    'No live production telemetry exists in this repository — this stage cannot be '
    'reached until a real production monitoring pipeline is built.'
)


def _gate_defined(agent_name, folder_name, repo_state):
    return True


def _gate_prompted(agent_name, folder_name, repo_state):
    if not folder_name:
        return False
    return 'system_prompt.md' in repo_state['per_folder_files'].get(folder_name, [])


def _gate_training_pack_complete(agent_name, folder_name, repo_state):
    if not folder_name:
        return False
    return folder_name in repo_state['operational_folder_names']


def _gate_scenario_tested(agent_name, folder_name, repo_state):
    if not folder_name:
        return False
    from ai_agent_council.services.training_lab import load_agent_test_cases
    cases = load_agent_test_cases(folder_name)
    return bool(cases['realistic_test_cases']) and bool(cases['failure_cases'])


def _gate_cross_agent_tested(agent_name, folder_name, repo_state):
    from ai_agent_council.models import CrossExaminationExchange
    return CrossExaminationExchange.objects.filter(
        Q(questioner_agent=agent_name) | Q(target_agent=agent_name)
    ).exists()


def _gate_human_reviewed(agent_name, folder_name, repo_state):
    from ai_agent_council.models import AgentTask, CouncilDecision
    run_ids = AgentTask.objects.filter(agent_name=agent_name).values_list('run_id', flat=True)
    return CouncilDecision.objects.filter(run_id__in=run_ids, human_approved=True).exists()


def _gate_operationally_ready(agent_name, folder_name, repo_state):
    # Membership in the operational roster alone isn't enough: this gate must
    # independently re-check every prior gate so it can never show "passed"
    # while an earlier gate (e.g. Cross-Agent Tested) is still failing.
    if agent_name not in OPERATIONAL_AGENT_NAMES:
        return False
    return all([
        _gate_prompted(agent_name, folder_name, repo_state),
        _gate_training_pack_complete(agent_name, folder_name, repo_state),
        _gate_scenario_tested(agent_name, folder_name, repo_state),
        _gate_cross_agent_tested(agent_name, folder_name, repo_state),
        _gate_human_reviewed(agent_name, folder_name, repo_state),
    ])


def _gate_production_monitored(agent_name, folder_name, repo_state):
    return False


GATES = [
    (0, 'Defined', _gate_defined),
    (1, 'Prompted', _gate_prompted),
    (2, 'Training Pack Complete', _gate_training_pack_complete),
    (3, 'Scenario Tested', _gate_scenario_tested),
    (4, 'Cross-Agent Tested', _gate_cross_agent_tested),
    (5, 'Human Reviewed', _gate_human_reviewed),
    (6, 'Operationally Ready', _gate_operationally_ready),
    (7, 'Production Monitored', _gate_production_monitored),
]


def compute_maturity(agent_name, repo_state):
    """
    Returns {'agent_name', 'stage', 'stage_label', 'gates': [...], 'blocked_reason'}.
    `stage` is the highest stage number reached with every gate up to and
    including it passing (no skipping a failed gate).
    """
    folder_name = AGENT_NAME_TO_FOLDER.get(agent_name)

    gates = []
    stage = 0
    blocked_reason = ''
    still_passing = True

    for stage_num, label, gate_fn in GATES:
        passed = gate_fn(agent_name, folder_name, repo_state)
        gates.append({'stage': stage_num, 'label': label, 'passed': passed})

        if still_passing and passed:
            stage = stage_num
        elif still_passing and not passed:
            still_passing = False
            blocked_reason = STAGE_7_BLOCKED_REASON if stage_num == 7 else (
                f'Blocked at stage {stage_num} ({label}).'
            )

    return {
        'agent_name': agent_name,
        'stage': stage,
        'stage_label': STAGE_LABELS[stage],
        'gates': gates,
        'blocked_reason': blocked_reason,
    }
