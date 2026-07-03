from pathlib import Path

from django.conf import settings
from django.shortcuts import render

# The 10 files every operational agent training pack must contain.
REQUIRED_AGENT_FILES = [
    'README.md', 'system_prompt.md', 'role.md', 'inputs.md', 'outputs.md',
    'tools.md', 'safety_rules.md', 'test_cases.json', 'evals.md', 'demo_scenarios.md',
]

MASTER_INDEX_FILENAME = 'ai_agent_training_index.md'


def _scan_ai_agents_repo_state():
    """
    Read the real ai_agents/ directory on disk so the counts shown on this
    page always reflect the actual repository state rather than a hardcoded
    number that could go stale if the repo structure changes.
    """
    base = Path(settings.BASE_DIR) / 'ai_agents'
    operational_folder_names = []
    total_training_files = 0

    if base.is_dir():
        for entry in sorted(base.iterdir()):
            if entry.is_dir():
                present = [f for f in REQUIRED_AGENT_FILES if (entry / f).is_file()]
                if present:
                    operational_folder_names.append(entry.name)
                    total_training_files += len(present)

    master_index_exists = (base / MASTER_INDEX_FILENAME).is_file()

    return {
        'operational_folder_names': operational_folder_names,
        'operational_folder_count': len(operational_folder_names),
        'total_training_files': total_training_files,
        'master_index_exists': master_index_exists,
    }


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

OPERATIONAL_AGENTS = [
    {
        'number': 1, 'name': 'Research Agent', 'folder': 'research_agent',
        'role': 'Finds, compares and summarises trusted evidence.',
        'handoffs': ['Document Reader Agent'], 'important': '',
    },
    {
        'number': 2, 'name': 'Document Reader Agent', 'folder': 'document_reader_agent',
        'role': 'Extracts facts from bills, PDFs, reports, technical documents and supplier quotes.',
        'handoffs': ['Asset Passport Agent', 'Finance Modelling Agent', 'MRV Agent'], 'important': '',
    },
    {
        'number': 3, 'name': 'Photo / Visual Evidence Agent', 'folder': 'photo_visual_evidence_agent',
        'role': 'Analyses inspection photos and videos while labelling findings as hypotheses until verified.',
        'handoffs': ['Asset Passport Agent', 'Governance Agent'], 'important': '',
    },
    {
        'number': 4, 'name': 'Asset Passport Agent', 'folder': 'asset_passport_agent',
        'role': 'Creates the structured digital record of each industrial asset.',
        'handoffs': ['Industrial Playbook Matching Agent'], 'important': '',
    },
    {
        'number': 5, 'name': 'Industrial Playbook Matching Agent', 'folder': 'industrial_playbook_matching_agent',
        'role': 'Matches assets to modernisation pathways, quick wins and deeper upgrades.',
        'handoffs': ['Finance Modelling Agent', 'Supplier / Funding Match Agent later'], 'important': '',
    },
    {
        'number': 6, 'name': 'Finance Modelling Agent', 'folder': 'finance_modelling_agent',
        'role': 'Prepares draft CAPEX, OPEX, payback, funding gap and finance-readiness logic.',
        'handoffs': ['Governance Agent', 'Report Generator Agent'], 'important': '',
    },
    {
        'number': 7, 'name': 'MRV Agent', 'folder': 'mrv_agent',
        'role': 'Separates estimated impact from verified impact and checks baseline/after-data readiness.',
        'handoffs': ['Governance Agent', 'Public Trust workflows'], 'important': '',
    },
    {
        'number': 8, 'name': 'Governance Agent', 'folder': 'governance_agent',
        'role': 'Routes high-impact outputs to technical, finance, MRV, safety, privacy and ethical review.',
        'handoffs': ['Report Generator Agent'], 'important': '',
    },
    {
        'number': 9, 'name': 'Report Generator Agent', 'folder': 'report_generator_agent',
        'role': 'Builds evidence-linked investor memos, board packs, country briefs and public summaries.',
        'handoffs': ['Human approval', 'External output'], 'important': '',
    },
    {
        'number': 10, 'name': 'Amanah Autopilot Supervisor', 'folder': 'amanah_autopilot_supervisor',
        'role': 'Runs overnight checks, finds missing evidence, prepares review queues and generates the morning briefing.',
        'handoffs': [],
        'important': (
            'Amanah Autopilot prepares actions for human review. It must not be '
            'presented as independently making high-impact decisions.'
        ),
    },
]

NEXT_STAGE_AGENTS = [
    {'number': 11, 'name': 'Supplier / Funding Match Agent'},
    {'number': 12, 'name': 'Customer Success Agent'},
    {'number': 13, 'name': 'Sales CRM Agent'},
    {'number': 14, 'name': 'Analytics Agent'},
]

OPERATIONAL_STATUS_LABEL = 'Operational Training Pack Ready'
NEXT_STAGE_STATUS_LABEL = 'Next Training Pack'

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
    {'number': 1, 'title': 'Architecture View', 'description': 'Shows all 14 agents and statuses.'},
    {'number': 2, 'title': 'Operational View', 'description': 'Shows only the 10 agents with full operational training packs.'},
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
    'headline': '10 trained operational agents working as one governed system.',
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
    'Ten agents currently have full operational training packs in the repository.',
    'Four additional agents are next-stage and do not yet have the same full training-pack structure.',
    'High-impact industrial, financial, MRV, public reporting and Islamic finance outputs require human review.',
    'Visual findings remain hypotheses until verified.',
    'Estimated impact must remain separate from verified impact.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
    'Microsoft ecosystem-ready does not mean Microsoft certified or Microsoft partner.',
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
    })
