from django.shortcuts import render

CORE_PURPOSE = "Turn EcoIQ's 14 AI agent categories into testable, safe and measurable agent workflows."

IMPORTANT_CLARIFICATION = (
    'GitHub Copilot Agents sessions are not the same as EcoIQ internal AI agents. '
    'EcoIQ agents are product architecture roles. They can later be implemented '
    'through LangGraph, Semantic Kernel, Azure AI Agent Framework, Celery tasks or '
    'other orchestration tools.'
)

AGENTS_REQUIRED_QA = {
    'question': 'Are all 14 agents required?',
    'answer': 'No. For MVP, EcoIQ should start with a smaller core set and expand later.',
}

AGENT_ROLLOUT_GROUPS = [
    {
        'title': 'MVP agents',
        'agents': [
            'Research Agent', 'Document Reader Agent', 'Asset Passport Agent',
            'Playbook Matching Agent', 'Finance Modelling Agent', 'MRV Agent',
        ],
    },
    {
        'title': 'Phase 2 agents',
        'agents': [
            'Photo / Visual Evidence Agent', 'Supplier / Funding Match Agent',
            'Governance Agent', 'Report Generator Agent',
        ],
    },
    {
        'title': 'Phase 3 agents',
        'agents': [
            'Sales CRM Agent', 'Customer Success Agent', 'Analytics Agent',
            'Amanah Autopilot Supervisor',
        ],
    },
]

AGENT_CARDS = [
    {
        'number': 1, 'name': 'Research Agent',
        'purpose': 'Find and summarise public evidence from reports, websites and trusted sources.',
        'inputs': ['Company name', 'Country', 'Sector', 'Public documents', 'Web links', 'User question'],
        'outputs': ['Evidence summary', 'Source list', 'Missing data', 'Confidence level', 'Outdated information flags'],
        'good_output': 'Evidence-backed, source-aware, cautious.',
        'bad_output': 'Claims without sources or pretending uncertain data is verified.',
        'human_approval': 'Public claims affect investors, governments or public reporting.',
        'rules': '', 'important': '',
    },
    {
        'number': 2, 'name': 'Document Reader Agent',
        'purpose': 'Extract facts from PDFs, energy bills, reports, invoices, technical files and supplier quotes.',
        'inputs': ['PDF', 'Image', 'Bill', 'Annual report', 'Maintenance log', 'Supplier quote'],
        'outputs': ['Extracted facts', 'Tables', 'Key figures', 'Document type', 'Evidence quality', 'Linked asset/project'],
        'good_output': '', 'bad_output': '', 'human_approval': '',
        'rules': 'If a field is missing, say "missing", not guessed.', 'important': '',
    },
    {
        'number': 3, 'name': 'Photo / Visual Evidence Agent',
        'purpose': 'Analyse inspection photos and videos.',
        'inputs': ['Asset photos', 'Equipment photos', 'Meter photos', 'Site videos'],
        'outputs': ['Visible risk notes', 'Asset components', 'Possible issues', 'Missing sensors', 'Safety concerns', '"Needs verification" labels'],
        'good_output': '', 'bad_output': '', 'human_approval': '', 'rules': '',
        'important': 'Photo findings are hypotheses, not engineering conclusions.',
    },
    {
        'number': 4, 'name': 'Asset Passport Agent',
        'purpose': 'Create structured asset records.',
        'inputs': ['Asset name', 'Location', 'Owner', 'Evidence', 'Photos', 'Bills', 'Inspection notes'],
        'outputs': ['Asset Passport draft', 'Asset type', 'Condition', 'Baseline fields', 'Missing data', 'Recommended next step'],
        'good_output': '', 'bad_output': '', 'human_approval': '', 'rules': '', 'important': '',
    },
    {
        'number': 5, 'name': 'Playbook Matching Agent',
        'purpose': 'Match assets to modernisation playbooks.',
        'inputs': ['Asset passport', 'Evidence', 'Sector', 'Risks', 'Country', 'Constraints'],
        'outputs': ['Best playbook', 'Quick wins', 'Deep upgrades', 'MRV metrics', 'Supplier needs', 'No Harm risks'],
        'good_output': '', 'bad_output': '', 'human_approval': '', 'rules': '', 'important': '',
    },
    {
        'number': 6, 'name': 'Finance Modelling Agent',
        'purpose': 'Prepare draft financial logic.',
        'inputs': ['CAPEX estimate', 'OPEX', 'Energy bills', 'Savings assumptions', 'Supplier quote', 'Payback target'],
        'outputs': ['Finance memo draft', 'CAPEX/OPEX logic', 'Payback estimate', 'Assumptions', 'Risk notes', 'Funding gap'],
        'good_output': '', 'bad_output': '', 'human_approval': '',
        'rules': 'Never claim guaranteed savings. Use "estimated" unless verified.', 'important': '',
    },
    {
        'number': 7, 'name': 'Supplier / Funding Match Agent',
        'purpose': 'Match projects to suppliers, funders, sponsors and grants.',
        'inputs': ['Project type', 'Location', 'Technology need', 'Funding amount', 'Eligibility', 'Risk profile'],
        'outputs': ['Supplier shortlist', 'Funding routes', 'RFQ pack', 'Outreach draft', 'Due diligence gaps'],
        'good_output': '', 'bad_output': '', 'human_approval': '',
        'rules': 'Do not imply endorsement without approval.', 'important': '',
    },
    {
        'number': 8, 'name': 'MRV Agent',
        'purpose': 'Track measurement, reporting and verification.',
        'inputs': ['Baseline data', 'After-data', 'Photos', 'Bills', 'Meter readings', 'Evidence records'],
        'outputs': ['MRV status', 'Verified vs estimated impact', 'Missing evidence', 'Before/after comparison', 'Public reporting readiness'],
        'good_output': '', 'bad_output': '', 'human_approval': '',
        'rules': 'No MRV Verified claim without evidence and human approval.', 'important': '',
    },
    {
        'number': 9, 'name': 'Governance Agent',
        'purpose': 'Prepare expert review and approval workflows.',
        'inputs': ['Project risks', 'Evidence', 'Finance memo', 'MRV claim', 'Public summary', 'Supplier match'],
        'outputs': ['Review packet', 'Reviewer type', 'No Harm checklist', 'Approval status', 'Blockers'],
        'good_output': '', 'bad_output': '', 'human_approval': '', 'rules': '', 'important': '',
    },
    {
        'number': 10, 'name': 'Report Generator Agent',
        'purpose': 'Generate investor memos, board packs, public summaries and country briefs.',
        'inputs': ['Asset Passport', 'Finance model', 'MRV status', 'Evidence', 'Governance review', 'Graph trace'],
        'outputs': ['Report draft', 'Executive summary', 'Risks', 'Assumptions', 'Next action', 'Evidence links'],
        'good_output': '', 'bad_output': '', 'human_approval': '',
        'rules': 'Every claim must be traceable to evidence.', 'important': '',
    },
    {
        'number': 11, 'name': 'Customer Success Agent',
        'purpose': 'Track customer value, renewal and expansion.',
        'inputs': ['Account usage', 'Package purchased', 'Reports delivered', 'MRV progress', 'Support issues', 'Renewal date'],
        'outputs': ['Health score', 'Renewal risk', 'Expansion signal', 'Value review', 'Next action'],
        'good_output': '', 'bad_output': '', 'human_approval': '', 'rules': '', 'important': '',
    },
    {
        'number': 12, 'name': 'Sales CRM Agent',
        'purpose': 'Support sales and partnerships.',
        'inputs': ['Lead', 'Organisation type', 'Country', 'Sector', 'Product interest', 'Stage'],
        'outputs': ['Lead fit score', 'Outreach draft', 'Proposal next step', 'CRM stage update', 'Risk notes'],
        'good_output': '', 'bad_output': '', 'human_approval': '',
        'rules': 'Do not overpromise funding, savings or impact.', 'important': '',
    },
    {
        'number': 13, 'name': 'Analytics Agent',
        'purpose': 'Analyse product usage, conversion, revenue and MRV bottlenecks.',
        'inputs': ['Usage events', 'Funnel data', 'Revenue data', 'MRV completion data', 'Country pipeline'],
        'outputs': ['KPI insights', 'Drop-off points', 'Growth opportunities', 'Risk flags', 'Weekly briefing'],
        'good_output': '', 'bad_output': '', 'human_approval': '', 'rules': '', 'important': '',
    },
    {
        'number': 14, 'name': 'Amanah Autopilot Supervisor',
        'purpose': 'Run overnight checks across EcoIQ.',
        'inputs': ['Projects', 'Evidence', 'MRV claims', 'Customer accounts', 'Agent tasks', 'Risk alerts'],
        'outputs': ['Morning briefing', 'Missing evidence alerts', 'Finance-ready opportunities', 'Human approval queue', 'No Harm alerts'],
        'good_output': '', 'bad_output': '', 'human_approval': '',
        'rules': 'Amanah Autopilot prepares actions for human review. It does not independently make high-impact decisions.',
        'important': '',
    },
]

AGENT_TRAINING_METHOD = [
    'Define role.', 'Define allowed inputs.', 'Define required output schema.',
    'Add 5 good examples.', 'Add 5 bad examples.', 'Add No Harm rules.',
    'Add human approval triggers.', 'Add tests.', 'Run evaluation.', 'Improve prompt.',
]

GOLDEN_TEST_CASE_EXAMPLE = {
    'agent': 'Document Reader Agent',
    'scenario': 'Document Reader Agent receives an energy bill.',
    'expected_output': [
        'Document type: energy bill', 'Billing period', 'kWh', 'Cost', 'Supplier',
        'Asset link', 'Missing fields', 'Evidence quality',
    ],
    'bad_output': [
        'Guesses missing kWh', 'Invents supplier', 'Claims verified savings',
    ],
}

AGENT_OUTPUT_SCHEMA_FIELDS = [
    'agent_name', 'task_type', 'input_summary', 'output_summary', 'evidence_used',
    'missing_data', 'confidence', 'risk_flags', 'human_approval_required',
    'next_action', 'status',
]

EVALUATION_METRICS = [
    'Evidence accuracy', 'Missing data detection', 'Unsupported claim rate',
    'JSON validity', 'Human approval correctness', 'Hallucination risk',
    'Task completion rate', 'Confidence calibration', 'Reviewer acceptance rate',
    'Time saved',
]

AGENT_DASHBOARD_CARDS = [
    'Agents defined', 'MVP agents ready', 'Golden test cases', 'Evaluations passed',
    'Failed evaluations', 'Unsupported claim alerts', 'Human approval triggers',
    'Agents needing review', 'Average confidence', 'Reviewer acceptance rate',
]

PROMPT_LIBRARY_FIELDS = [
    'System prompt', 'Task prompt', 'Output schema', 'Safety rules', 'Examples',
    'Failure cases', 'Review checklist',
]

HUMAN_REVIEW_TRIGGERS = [
    'Finance-ready claims', 'MRV Verified claims', 'Public summaries',
    'Supplier/funder outreach', 'Islamic finance wording', 'Maqasid/Mizan public claims',
    'Safety/environmental claims', 'High-impact industrial recommendations',
    'Data sharing with external parties',
]

NO_HARM_GATE_ITEMS = [
    'Does it cite or link evidence?', 'Does it separate estimate from verified?',
    'Does it avoid overclaiming?', 'Does it protect sensitive data?',
    'Does it trigger human review when needed?',
    'Does it avoid unsupported Microsoft claims?',
    'Does it avoid religious overclaiming?',
    'Does it label visual findings as hypotheses?',
    'Does it show missing data?', 'Can every output be audited?',
]

IMPLEMENTATION_OPTIONS = [
    'LangGraph', 'Microsoft Semantic Kernel', 'Azure AI Agent Framework concept',
    'Celery background tasks', 'Django management commands',
    'OpenAI / Anthropic / Gemini / Azure OpenAI model routing',
    'Pydantic output validation', 'JSON schema validation',
    'Human-in-the-loop review queues',
]
IMPLEMENTATION_OPTIONS_NOTE = (
    'This module defines training and evaluation workflow. It does not claim all '
    'agents are fully autonomous production agents yet.'
)

GITHUB_VS_ECOIQ_AGENTS_TEXT = (
    'GitHub Copilot Agents sessions are coding-agent sessions inside GitHub. EcoIQ '
    'AI agents are internal product agents designed for industrial intelligence '
    'workflows. Seeing "0 active / 0 completed" GitHub agent sessions does not mean '
    'EcoIQ agents do not exist; it only means no GitHub Copilot agent sessions are '
    'running.'
)

SAFETY_PRINCIPLES = [
    'Agent training improves prompts, schemas and evaluation workflows; it is not '
    'model fine-tuning unless explicitly implemented.',
    'Agent outputs are decision-support drafts until reviewed where required.',
    'High-impact industrial, finance, MRV, public reporting and Islamic finance '
    'outputs require human approval.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
    'Visual findings are hypotheses until verified.',
    'GitHub Copilot Agents sessions are separate from EcoIQ internal product agents.',
]

CTA_BUTTONS = [
    {'label': 'Open Agent Training Lab', 'anchor': '#agent-cards'},
    {'label': 'View MVP Agents', 'anchor': '#agent-rollout'},
    {'label': 'Create Golden Test Case', 'anchor': '#golden-test-cases'},
    {'label': 'Run Agent Evaluation', 'anchor': '#evaluation-metrics'},
    {'label': 'Review Failed Output', 'anchor': '#agent-dashboard-cards'},
    {'label': 'Open Prompt Library', 'anchor': '#prompt-library'},
    {'label': 'View Human Approval Rules', 'anchor': '#human-review-rules'},
    {'label': 'Train Document Reader Agent', 'anchor': '#agent-2'},
    {'label': 'Train MRV Agent', 'anchor': '#agent-8'},
    {'label': 'Train Finance Agent', 'anchor': '#agent-6'},
]


def overview(request):
    return render(request, 'agent_training_evaluation_lab/overview.html', {
        'core_purpose': CORE_PURPOSE,
        'important_clarification': IMPORTANT_CLARIFICATION,
        'agents_required_qa': AGENTS_REQUIRED_QA,
        'agent_rollout_groups': AGENT_ROLLOUT_GROUPS,
        'agent_cards': AGENT_CARDS,
        'agent_training_method': AGENT_TRAINING_METHOD,
        'golden_test_case_example': GOLDEN_TEST_CASE_EXAMPLE,
        'agent_output_schema_fields': AGENT_OUTPUT_SCHEMA_FIELDS,
        'evaluation_metrics': EVALUATION_METRICS,
        'agent_dashboard_cards': AGENT_DASHBOARD_CARDS,
        'prompt_library_fields': PROMPT_LIBRARY_FIELDS,
        'human_review_triggers': HUMAN_REVIEW_TRIGGERS,
        'no_harm_gate_items': NO_HARM_GATE_ITEMS,
        'implementation_options': IMPLEMENTATION_OPTIONS,
        'implementation_options_note': IMPLEMENTATION_OPTIONS_NOTE,
        'github_vs_ecoiq_agents_text': GITHUB_VS_ECOIQ_AGENTS_TEXT,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })
