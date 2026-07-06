from django.shortcuts import get_object_or_404, render

from ai_agent_council.models import (
    AgentTask, CouncilDecision, CouncilDisagreement, CouncilRun,
)
from ai_agent_council.services.maturity import compute_maturity
from ai_agent_council.services.reliability import compute_reliability
from ai_agent_council.services.training_lab import load_agent_test_cases

# Agent roster, repository scan and related constants now live in agents.py
# (shared with services/*.py to avoid a circular import). Re-exported here
# under their original names so existing imports/tests are unaffected —
# e.g. `from ai_agent_council.views import _scan_ai_agents_repo_state`.
from ai_agent_council.agents import (  # noqa: F401 (re-exported for existing imports)
    AGENT_NAME_TO_FOLDER,
    MASTER_INDEX_FILENAME,
    NEXT_STAGE_AGENT_NAMES,
    NEXT_STAGE_AGENTS,
    NEXT_STAGE_STATUS_LABEL,
    OPERATIONAL_AGENT_FOLDERS,
    OPERATIONAL_AGENT_NAMES,
    OPERATIONAL_AGENTS,
    OPERATIONAL_STATUS_LABEL,
    REQUIRED_AGENT_FILES,
    _scan_ai_agents_repo_state,
)

CORE_PURPOSE = (
    "Give investors, Microsoft ecosystem stakeholders, governments, industrial "
    "operators and partners one clear place to understand EcoIQ's AI agent "
    "architecture."
)

CONNECTED_MODULES = [
    {'name': 'Agent Training & Evaluation Lab', 'role': 'Supplies the shared training method and evaluation approach every agent pack follows.'},
    {'name': 'AI Agent Operations Console', 'role': 'Monitors live agent task runs, confidence and health across the Council.'},
    {'name': 'Document Reader Agent Training Pack', 'role': 'The deep-dive training pack behind the Document Reader Agent seat.'},
    {'name': 'MRV Agent Training Pack', 'role': 'The deep-dive training pack behind the MRV Agent seat.'},
    {'name': 'Knowledge Graph & Relationship Map', 'role': 'Stores every agent handoff as an evidence-linked graph node.'},
    {'name': 'Asset Passport', 'role': 'Receives the structured asset record Asset Passport Agent builds.'},
    {'name': 'Industrial Playbook Library', 'role': 'Supplies the playbooks Industrial Playbook Matching Agent matches against.'},
    {'name': 'Institutional Finance Engine', 'role': 'Receives Finance Modelling Agent draft CAPEX/OPEX models.'},
    {'name': 'Impact MRV Layer', 'role': 'Receives MRV Agent baseline/after-data and verification status.'},
    {'name': 'Governance & Expert Review Board', 'role': 'The human review layer Governance Agent routes packets to.'},
    {'name': 'Executive Briefing & Board Pack Generator', 'role': 'Receives Report Generator Agent output for investor/board use.'},
    {'name': 'Amanah Autopilot', 'role': 'The overnight supervision this Council relies on for portfolio-wide checks.'},
    {'name': 'Data Room & Evidence Vault', 'role': 'Stores the evidence every agent handoff links back to.'},
    {'name': 'Microsoft Ecosystem Core Stack', 'role': 'Supplies the Microsoft-ready building blocks the Council is designed to integrate with.'},
]

COUNCIL_WORKFLOW_STEPS = [
    'Research', 'Document Reader', 'Photo / Visual Evidence', 'Asset Passport',
    'Playbook Matching', 'Finance', 'MRV', 'Governance', 'Report Generator',
    'Human Approval',
]

AMANAH_OVERSIGHT_ITEMS = [
    'Checks missing evidence', 'Checks blocked tasks', 'Checks review queues',
    'Checks readiness', 'Prepares morning briefing',
]

HANDOFF_PRESERVED_ITEMS = [
    'Evidence links', 'Missing data', 'Confidence', 'Risk flags',
    'Estimated vs verified status', 'Human approval requirements', 'Audit trail',
]
HANDOFF_CRITICAL_RULE = (
    'A downstream agent must never silently increase confidence, drop '
    'missing-data warnings or convert estimated data into verified data.'
)

DECISION_PROTOCOL_STEPS = [
    'Evidence exists.', 'Missing data is visible.', 'Output schema is valid.',
    'Safety rules pass.', 'No Harm Gate is checked.',
    'Human approval requirement is evaluated.', 'Sensitive data is protected.',
    'Estimated vs verified status is preserved.', 'External action is permissioned.',
    'Audit trail is created.',
]

COUNCIL_VIEWS = [
    {'number': 1, 'title': 'Architecture View', 'description': 'Shows all 16 agents and statuses.'},
    {'number': 2, 'title': 'Operational View', 'description': 'Shows only the 12 agents with full operational training packs.'},
    {'number': 3, 'title': 'Handoff View', 'description': 'Shows how data moves between agents.'},
    {'number': 4, 'title': 'Approval View', 'description': 'Shows where human review is mandatory.'},
    {'number': 5, 'title': 'Evidence View', 'description': 'Shows which agents consume and produce evidence.'},
    {'number': 6, 'title': 'Overnight View', 'description': 'Shows Amanah Autopilot supervision.'},
]

DASHBOARD_CARDS = [
    'Operationally trained agents', 'Next-stage agents', 'Total training files',
    'Golden test cases', 'Agents requiring review', 'Active human approval gates',
    'Evidence-producing agents', 'Evidence-consuming agents', 'Finance-sensitive agents',
    'MRV-sensitive agents', 'Public-output agents', 'Overnight supervisor status',
]

EXAMPLE_COUNCIL_CASE = {
    'project': 'Boiler House #3 Modernisation',
    'steps': [
        {'agent': 'Research Agent', 'action': 'Finds public/site context.'},
        {'agent': 'Document Reader Agent', 'action': 'Reads fuel bills and supplier quote.'},
        {'agent': 'Photo / Visual Evidence Agent', 'action': 'Flags visible insulation gaps and soot as hypotheses.'},
        {'agent': 'Asset Passport Agent', 'action': 'Builds asset record.'},
        {'agent': 'Playbook Matching Agent', 'action': 'Matches Boiler Modernisation Playbook.'},
        {'agent': 'Finance Modelling Agent', 'action': 'Drafts CAPEX, OPEX and payback assumptions.'},
        {'agent': 'MRV Agent', 'action': 'Checks baseline and after-data requirements.'},
        {'agent': 'Governance Agent', 'action': 'Routes technical and finance review.'},
        {'agent': 'Report Generator Agent', 'action': 'Builds decision memo.'},
        {'agent': 'Amanah Autopilot', 'action': 'Overnight checks missing evidence and prepares morning briefing.'},
        {'agent': 'Human', 'action': 'Approves high-impact external use.'},
    ],
}

WHY_COUNCIL_MATTERS = {
    'explanation': 'EcoIQ should not behave like one black-box chatbot.',
    'items': [
        'Separates specialised responsibilities', 'Preserves evidence traceability',
        'Prevents one agent from doing everything', 'Makes approvals visible',
        'Creates safer handoffs', 'Supports enterprise auditability',
        'Makes failures easier to diagnose',
    ],
}

MICROSOFT_INTEGRATION = {
    'items': [
        'Microsoft Semantic Kernel concepts', 'Azure AI Agent Framework concepts',
        'Microsoft Fabric', 'Teams approval workflows', 'SharePoint evidence packs',
        'Power BI operations dashboards', 'Responsible AI tools',
    ],
    'do_not_claim': [
        'Microsoft certification', 'Microsoft partnership', 'Official Microsoft approval',
    ],
}

PRESENTATION_MODE = {
    'headline': '12 trained operational agents working as one governed system.',
    'subheadline': (
        'From evidence collection to finance, MRV, governance and reporting — '
        'with human approval at high-impact points.'
    ),
    'story_cards': [
        {'number': 1, 'title': 'Evidence to Asset', 'flow': ['Research', 'Document Reader', 'Visual Evidence', 'Asset Passport']},
        {'number': 2, 'title': 'Asset to Investment', 'flow': ['Playbook Matching', 'Finance', 'MRV', 'Governance']},
        {'number': 3, 'title': 'Decision to Impact', 'flow': ['Report Generator', 'Human Approval', 'Implementation', 'Amanah Autopilot Monitoring']},
    ],
}

SAFETY_PRINCIPLES = [
    'EcoIQ AI agents are specialised decision-support workflows, not fully autonomous decision-makers.',
    'Twelve agents currently have full operational training packs in the repository.',
    'Four additional agents are next-stage and do not yet have the same full training-pack structure.',
    'High-impact industrial, financial, MRV, public reporting and Islamic finance outputs require human review.',
    'Visual findings remain hypotheses until verified.',
    'Estimated impact must remain separate from verified impact.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
    'Microsoft ecosystem-ready does not mean Microsoft certified or Microsoft partner.',
]

AGENT_INTERDEPENDENCY_MAP = [
    {
        'label': 'Evidence Verification',
        'agents': ['Research Agent', 'Document Reader Agent', 'Photo / Visual Evidence Agent'],
        'description': 'Cross-checks public context, extracted documents and visual findings against each other before Asset Passport builds a record.',
        'status': 'active',
    },
    {
        'label': 'Transition Risk',
        'agents': ['Asset Passport Agent', 'Industrial Playbook Matching Agent'],
        'description': 'Surfaces risk_flags (e.g. transition/procurement/baseline risk) that Governance must route for review.',
        'status': 'active',
    },
    {
        'label': 'Investor Intelligence',
        'agents': ['Finance Modelling Agent', 'Report Generator Agent'],
        'description': 'Combines draft finance modelling with the evidence-linked memo an investor or board actually reads.',
        'status': 'active',
    },
    {
        'label': 'Funding Match',
        'agents': ['Supplier / Funding Match Agent'],
        'description': 'Not yet trained — next-stage agent with no operational training pack. Shown blocked, not simulated.',
        'status': 'blocked',
    },
]

CTA_BUTTONS = [
    {'label': 'Open AI Agent Council', 'anchor': '#council-workflow'},
    {'label': 'View Operational Agents', 'anchor': '#operationally-trained-agents'},
    {'label': 'View Agent Training Lab', 'url_name': 'agent_training_evaluation_lab:overview'},
    {'label': 'Open AI Agent Operations Console', 'url_name': 'ai_agent_operations_console:overview'},
    {'label': 'View Handoff Map', 'anchor': '#agent-council-handoffs'},
    {'label': 'Open Human Approval Flow', 'anchor': '#view-4'},
    {'label': 'View Amanah Autopilot', 'anchor': '#agent-10'},
    {'label': 'Open Evidence Trace', 'url_name': 'knowledge_graph_relationship_map:overview'},
    {'label': 'View Training Index', 'anchor': '#training-pack-repository-layout'},
    {'label': 'Open Next-Stage Agents', 'anchor': '#next-stage-agents'},
]


def _council_control_room_stats():
    """
    Real counts, not illustrative numbers — every value is 0 until
    `python manage.py seed_council_demo_run` has been run.
    """
    return {
        'active_runs': CouncilRun.objects.exclude(status='closed').count(),
        # "Open" = still needs more evidence or a human, as opposed to a
        # disagreement that was auto-resolved, escalated to another agent,
        # or preserved purely as a recorded minority view.
        'open_disagreements': CouncilDisagreement.objects.filter(
            resolution_method__in=['require_human_review', 'request_more_evidence'],
        ).count(),
        'awaiting_human_review': CouncilDecision.objects.filter(
            human_approval_required=True, human_approved__isnull=True,
        ).count(),
        'low_confidence_decisions': CouncilDecision.objects.filter(confidence__lt=70).count(),
    }


def overview(request):
    repo_state = _scan_ai_agents_repo_state()

    hero_metrics = [
        {'value': str(repo_state['operational_folder_count']), 'label': 'operational training packs'},
        {'value': str(repo_state['total_training_files']), 'label': 'agent training files'},
        {'value': '1' if repo_state['master_index_exists'] else '0', 'label': 'master training index'},
        {'value': str(len(NEXT_STAGE_AGENTS)), 'label': 'next-stage agents'},
        {'value': '', 'label': 'human approval gates'},
        {'value': '', 'label': 'evidence-first workflows'},
    ]

    return render(request, 'ai_agent_council/overview.html', {
        'core_purpose': CORE_PURPOSE,
        'connected_modules': CONNECTED_MODULES,
        'repo_state': repo_state,
        'hero_metrics': hero_metrics,
        'operational_agents': OPERATIONAL_AGENTS,
        'next_stage_agents': NEXT_STAGE_AGENTS,
        'operational_status_label': OPERATIONAL_STATUS_LABEL,
        'next_stage_status_label': NEXT_STAGE_STATUS_LABEL,
        'council_workflow_steps': COUNCIL_WORKFLOW_STEPS,
        'amanah_oversight_items': AMANAH_OVERSIGHT_ITEMS,
        'handoff_preserved_items': HANDOFF_PRESERVED_ITEMS,
        'handoff_critical_rule': HANDOFF_CRITICAL_RULE,
        'decision_protocol_steps': DECISION_PROTOCOL_STEPS,
        'council_views': COUNCIL_VIEWS,
        'dashboard_cards': DASHBOARD_CARDS,
        'example_council_case': EXAMPLE_COUNCIL_CASE,
        'why_council_matters': WHY_COUNCIL_MATTERS,
        'microsoft_integration': MICROSOFT_INTEGRATION,
        'presentation_mode': PRESENTATION_MODE,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
        'control_room': _council_control_room_stats(),
        'agent_interdependency_map': AGENT_INTERDEPENDENCY_MAP,
        'demo_runs': CouncilRun.objects.all(),
    })


def run_detail(request, slug):
    run = get_object_or_404(CouncilRun, slug=slug)
    decision = getattr(run, 'decision', None)
    memory_entry = getattr(decision, 'memory_entry', None) if decision else None

    return render(request, 'ai_agent_council/run_detail.html', {
        'run': run,
        'tasks': run.tasks.all(),
        'handoffs': run.handoffs.all(),
        'disagreements': run.disagreements.select_related('position_a', 'position_b').all(),
        'cross_examinations': run.cross_examinations.all(),
        'decision': decision,
        'memory_entry': memory_entry,
    })


def training(request):
    repo_state = _scan_ai_agents_repo_state()

    agent_rows = []
    for agent in OPERATIONAL_AGENTS:
        agent_rows.append({
            'agent': agent,
            'cases': load_agent_test_cases(agent['folder']),
            'maturity': compute_maturity(agent['name'], repo_state),
        })

    return render(request, 'ai_agent_council/training.html', {
        'agent_rows': agent_rows,
        'next_stage_agents': NEXT_STAGE_AGENTS,
    })


def reliability(request):
    repo_state = _scan_ai_agents_repo_state()

    reliability_rows = [compute_reliability(name) for name in OPERATIONAL_AGENT_NAMES]
    maturity_rows = [
        compute_maturity(name, repo_state)
        for name in OPERATIONAL_AGENT_NAMES + NEXT_STAGE_AGENT_NAMES
    ]

    return render(request, 'ai_agent_council/reliability.html', {
        'reliability_rows': reliability_rows,
        'maturity_rows': maturity_rows,
    })


def memory(request):
    decisions = (
        CouncilDecision.objects
        .select_related('run', 'memory_entry')
        .order_by('-run__created_at')
    )

    return render(request, 'ai_agent_council/memory.html', {
        'decisions': decisions,
    })
