from django.shortcuts import render

# Connected EcoIQ modules — the Console is the observability layer over every agent
CONNECTED_MODULES = [
    {'name': 'Amanah Autopilot', 'role': 'Runs the overnight supervisor agent this console monitors.'},
    {'name': 'Omnimodal Evidence Panel', 'role': 'Supplies the photo/video evidence the Visual Evidence Agent analyses.'},
    {'name': 'Product Analytics & KPI Engine', 'role': 'Consumes agent task metrics as part of platform-wide KPIs.'},
    {'name': 'Command Centre', 'role': 'Surfaces which projects have active agent tasks running.'},
    {'name': 'Governance & Expert Review Board', 'role': 'Receives tasks routed to the Human Approval Queue.'},
    {'name': 'Data Room & Evidence Vault', 'role': 'Stores the evidence every agent output traces back to.'},
    {'name': 'Asset Passport', 'role': 'Is created and updated by the Asset Passport Agent.'},
    {'name': 'Impact MRV Layer', 'role': 'Is populated by the MRV Agent.'},
    {'name': 'Institutional Finance Engine', 'role': 'Is populated by the Finance Modelling Agent.'},
    {'name': 'Supplier & Funding Marketplace', 'role': 'Is populated by the Supplier / Funding Match Agent.'},
    {'name': 'Executive Briefing & Board Pack Generator', 'role': 'Is populated by the Report Generator Agent.'},
    {'name': 'API & Integration Layer', 'role': 'Exposes agent task and log data through the API.'},
    {'name': 'Microsoft Ecosystem Core Stack', 'role': 'Provides the agent orchestration building blocks this console monitors.'},
    {'name': 'Responsible AI tools', 'role': 'Support explainability, bias checking and safety review of agent outputs.'},
    {'name': 'Teams approvals', 'role': 'Delivers human approval requests routed from the queue.'},
    {'name': 'Power BI dashboards', 'role': 'Renders operations dashboards for agent activity and cost.'},
    {'name': 'Microsoft Fabric', 'role': 'Stores agent logs and telemetry.'},
]

CORE_PURPOSE = 'Make EcoIQ\'s agent system observable, auditable, safe and enterprise-ready.'

AGENT_CATEGORIES = [
    {
        'number': 1,
        'title': 'Research Agent',
        'description': 'Reads public documents, websites, reports and regulatory sources.',
        'tasks': [
            'Gather evidence', 'Summarise source data', 'Identify missing documents',
            'Create source list', 'Flag outdated information',
        ],
        'note': '',
    },
    {
        'number': 2,
        'title': 'Document Reader Agent',
        'description': 'Reads PDFs, annual reports, energy bills, invoices, supplier '
                        'quotes and technical files.',
        'tasks': [
            'Extract tables', 'Detect key facts', 'Classify evidence',
            'Link documents to assets', 'Update Data Room',
        ],
        'note': '',
    },
    {
        'number': 3,
        'title': 'Photo / Visual Evidence Agent',
        'description': 'Analyses photos and videos from Mobile Inspection.',
        'tasks': [
            'Detect visible risks', 'Label asset components', 'Identify missing sensors',
            'Flag safety concerns', 'Prepare visual evidence notes',
        ],
        'note': 'Visual findings are hypotheses and must show "Needs verification" '
                'unless confirmed by expert review or measurement.',
    },
    {
        'number': 4,
        'title': 'Asset Passport Agent',
        'description': 'Creates and updates asset records.',
        'tasks': [
            'Structure asset profile', 'Link evidence', 'Detect missing baseline data',
            'Assign asset type', 'Recommend playbook',
        ],
        'note': '',
    },
    {
        'number': 5,
        'title': 'Playbook Matching Agent',
        'description': 'Matches assets to industrial modernisation playbooks.',
        'tasks': [
            'Identify best playbook', 'Recommend quick wins', 'Suggest deep upgrades',
            'Create next action checklist',
        ],
        'note': '',
    },
    {
        'number': 6,
        'title': 'Finance Modelling Agent',
        'description': 'Prepares financial models and investment logic.',
        'tasks': [
            'Estimate CAPEX/OPEX', 'Calculate payback', 'Prepare finance memo',
            'Identify funding gap', 'Flag assumptions needing review',
        ],
        'note': '',
    },
    {
        'number': 7,
        'title': 'Supplier / Funding Match Agent',
        'description': 'Matches projects to suppliers, funders and sponsors.',
        'tasks': [
            'Shortlist suppliers', 'Identify grant/CSR/funding routes',
            'Prepare RFQ pack', 'Draft outreach', 'Flag due diligence gaps',
        ],
        'note': '',
    },
    {
        'number': 8,
        'title': 'MRV Agent',
        'description': 'Tracks baseline, after-data and impact verification.',
        'tasks': [
            'Check baseline completeness', 'Compare before/after evidence',
            'Flag weak evidence', 'Prepare MRV report',
            'Distinguish estimated vs verified impact',
        ],
        'note': '',
    },
    {
        'number': 9,
        'title': 'Governance Agent',
        'description': 'Prepares expert review packets and approval workflows.',
        'tasks': [
            'Identify required reviewers', 'Prepare No Harm Gate checklist',
            'Route to technical/financial/environmental/Maqasid review',
            'Track approvals',
        ],
        'note': '',
    },
    {
        'number': 10,
        'title': 'Report Generator Agent',
        'description': 'Creates investor memos, board packs, country briefs and public summaries.',
        'tasks': [
            'Generate executive summary', 'Cite evidence', 'Create decision memo',
            'Prepare appendices', 'Flag unsupported claims',
        ],
        'note': '',
    },
    {
        'number': 11,
        'title': 'Customer Success Agent',
        'description': 'Monitors customers after sale.',
        'tasks': [
            'Detect at-risk accounts', 'Prepare value review', 'Identify renewal risk',
            'Suggest upsell', 'Flag missing MRV evidence',
        ],
        'note': '',
    },
    {
        'number': 12,
        'title': 'Sales CRM Agent',
        'description': 'Supports sales and partner pipeline.',
        'tasks': [
            'Draft outreach', 'Prepare follow-up reminders', 'Identify qualified leads',
            'Connect proposals to products', 'Flag overclaiming risk',
        ],
        'note': '',
    },
    {
        'number': 13,
        'title': 'Analytics Agent',
        'description': 'Monitors product and KPI performance.',
        'tasks': [
            'Detect funnel drop-offs', 'Prepare KPI briefing',
            'Identify high-performing countries', 'Flag weak module adoption',
            'Detect MRV bottlenecks',
        ],
        'note': '',
    },
    {
        'number': 14,
        'title': 'Amanah Autopilot Supervisor',
        'description': 'Runs overnight checks across the platform.',
        'tasks': [
            'Detect high-harm assets', 'Find missing evidence', 'Prepare morning briefing',
            'Identify finance-ready projects', 'Flag approvals needed',
            'Prepare human review queue',
        ],
        'note': '',
    },
]

TASK_STATUSES = [
    'Queued', 'Running', 'Waiting for Evidence', 'Waiting for Human Approval',
    'Needs Verification', 'Completed', 'Failed', 'Blocked', 'Escalated', 'Cancelled',
]

DASHBOARD_CARDS = [
    'Active agents', 'Queued tasks', 'Running tasks', 'Completed tasks today',
    'Failed tasks', 'Blocked tasks', 'Tasks waiting for evidence',
    'Tasks waiting for human approval', 'Estimated daily model cost',
    'Evidence sources processed', 'Reports generated', 'MRV checks completed',
    'Supplier matches generated', 'Finance memos generated', 'No Harm Gate alerts',
    'Average task completion time',
]

TASK_TABLE_FIELDS = [
    'Task ID', 'Agent name', 'Project / asset', 'Task type', 'Status', 'Priority',
    'Started at', 'Last updated', 'Evidence used', 'Output generated',
    'Confidence level', 'Cost estimate', 'Model used', 'Error message',
    'Human approval required', 'Next action',
]

AGENT_RUN_DETAIL_FIELDS = [
    'Prompt / instruction summary', 'Input data', 'Evidence sources',
    'Documents read', 'Photos analysed', 'Model used', 'Tokens / estimated cost',
    'Output summary', 'Confidence', 'Missing data', 'Safety flags',
    'No Harm Gate flags', 'Human approval status', 'Final decision', 'Audit trail',
]

EVIDENCE_TRACE_ITEMS = [
    'What evidence was used', 'Where it came from', 'When it was uploaded',
    'Whether it is strong/medium/weak', 'Whether it is verified',
    'Whether it is stale', 'Which claims depend on it',
    'Which human reviewer approved it',
]

COST_MODEL_ITEMS = [
    'Model used', 'Task type', 'Token usage estimate', 'Cost estimate',
    'Cost by agent', 'Cost by customer', 'Cost by project', 'Cost by product module',
    'High-cost tasks', 'Failed-cost waste', 'Cheaper model candidate',
    'Sensitive-data model routing',
]

MODEL_ROUTING_EXAMPLES = [
    'Sensitive client data → approved enterprise model / Azure OpenAI',
    'Public data and reports → lower-cost model allowed',
    'Complex finance memo → high-reasoning model',
    'Image inspection → vision model',
    'Long documents → long-context model',
    'High-impact decision → human review required',
]

HUMAN_APPROVAL_QUEUE_ITEMS = [
    'Technical review', 'Finance review', 'Environmental review', 'Safety review',
    'Maqasid/Mizan review', 'Islamic finance review', 'Public summary approval',
    'Supplier outreach approval', 'Funding memo approval', 'MRV verification approval',
]

FAILURE_DEBUG_ITEMS = [
    'Failed document parsing', 'Missing evidence', 'Model timeout',
    'Invalid JSON output', 'Unsupported claim', 'Hallucination risk',
    'Source mismatch', 'Route/API error', 'Permission error', 'Privacy/PII risk',
    'Failed supplier match', 'Failed finance calculation', 'Blocked public reporting',
]

RECOVERY_ACTIONS = [
    'Retry task', 'Request missing evidence', 'Downgrade claim to "Needs verification"',
    'Assign human reviewer', 'Switch model', 'Reduce context', 'Open Data Room',
    'Open evidence trace', 'Create support ticket',
]

EXAMPLE_AGENT_RUNS = [
    {
        'agent': 'Photo / Visual Evidence Agent',
        'run_label': 'Project',
        'run_name': 'Boiler House #3',
        'input': '8 inspection photos',
        'output_label': 'Findings',
        'output': [
            'Uninsulated pipe visible', 'Soot marks visible', 'No smart meter visible',
            'Corrosion risk possible',
        ],
        'status': 'Needs Verification',
        'blocker': '',
        'next_action': 'Request engineer review and collect 12 months fuel data.',
    },
    {
        'agent': 'Finance Modelling Agent',
        'run_label': 'Project',
        'run_name': 'Factory Compressed Air Optimisation',
        'input': 'Energy bill, compressor photos, playbook match',
        'output_label': 'Output',
        'output': ['Draft payback estimate and investor memo outline.'],
        'status': 'Waiting for Human Approval',
        'blocker': '',
        'next_action': 'Financial reviewer checks assumptions.',
    },
    {
        'agent': 'MRV Agent',
        'run_label': 'Project',
        'run_name': 'Village Clean Heating Pilot',
        'input': 'Before photos, installation record, after comfort survey',
        'output_label': 'Output',
        'output': ['MRV report draft.'],
        'status': 'Blocked',
        'blocker': 'After fuel data missing.',
        'next_action': 'Request missing after-data before verified impact claim.',
    },
    {
        'agent': 'Amanah Autopilot Supervisor',
        'run_label': 'Run',
        'run_name': 'Overnight portfolio scan',
        'input': '',
        'output_label': 'Output',
        'output': [
            '4 missing evidence alerts, 2 finance-ready projects, 1 public summary '
            'ready for review.',
        ],
        'status': 'Completed',
        'blocker': '',
        'next_action': '',
    },
]

AMANAH_MORNING_OPERATIONS_BRIEFING = (
    'Overnight, 42 tasks ran across 11 agents. 31 completed, 6 need evidence, 3 need '
    'human approval and 2 failed due to missing documents. Estimated model cost was '
    '£4.80. Top priority: Boiler House #3 finance memo needs technical review before '
    'supplier outreach.'
)

MICROSOFT_INTEGRATION_ITEMS = [
    'Azure AI Agent Framework / Semantic Kernel concepts for orchestration',
    'Microsoft Fabric for agent logs and telemetry', 'Power BI for operations dashboards',
    'Teams for human approval notifications', 'SharePoint / Data Room for evidence packs',
    'Azure Monitor / Application Insights concept for tracing',
    'Responsible AI Toolbox for explainability', 'Presidio for privacy / PII detection',
    'PyRIT / red-team checks for agent safety',
]

NO_HARM_GATE_AGENTS_ITEMS = [
    'Is the evidence strong enough?',
    'Is the output clearly labelled as draft/verified?',
    'Is human approval required?',
    'Does the agent overclaim savings, funding or impact?',
    'Is personal or sensitive data protected?',
    'Is public reporting approved?',
    'Are religious/Maqasid/Mizan claims safe and not overstated?',
    'Is model routing appropriate for sensitive data?',
    'Is the task auditable?',
    'Can the user trace every claim to evidence?',
]

SAFETY_PRINCIPLES = [
    'Agent outputs are decision-support drafts until reviewed and approved where required.',
    'High-impact industrial, financial, environmental, safety, public reporting and '
    'Islamic finance decisions require human approval.',
    'Visual inspection findings are hypotheses unless verified by measurement or expert review.',
    'EcoIQ must not publish or act on unsupported claims.',
    'Sensitive data must be routed, logged and protected according to permissions.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
]

CTA_BUTTONS = [
    {'label': 'Open Agent Console', 'anchor': '#agent-categories'},
    {'label': 'View Running Tasks', 'anchor': '#dashboard-cards'},
    {'label': 'Review Failed Tasks', 'anchor': '#failure-debugging'},
    {'label': 'Open Human Approval Queue', 'anchor': '#human-approval-queue'},
    {'label': 'View Evidence Trace', 'anchor': '#evidence-trace'},
    {'label': 'Retry Failed Task', 'anchor': '#recovery-actions'},
    {'label': 'Request Missing Evidence', 'url_name': 'data_room_evidence_vault:overview'},
    {'label': 'Export Agent Logs', 'anchor': '#cost-model-monitoring'},
    {'label': 'Send Approval to Teams', 'anchor': '#microsoft-integration'},
    {'label': 'Generate Morning Operations Briefing', 'anchor': '#amanah-morning-briefing'},
]


def overview(request):
    return render(request, 'ai_agent_operations_console/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_purpose': CORE_PURPOSE,
        'agent_categories': AGENT_CATEGORIES,
        'task_statuses': TASK_STATUSES,
        'dashboard_cards': DASHBOARD_CARDS,
        'task_table_fields': TASK_TABLE_FIELDS,
        'agent_run_detail_fields': AGENT_RUN_DETAIL_FIELDS,
        'evidence_trace_items': EVIDENCE_TRACE_ITEMS,
        'cost_model_items': COST_MODEL_ITEMS,
        'model_routing_examples': MODEL_ROUTING_EXAMPLES,
        'human_approval_queue_items': HUMAN_APPROVAL_QUEUE_ITEMS,
        'failure_debug_items': FAILURE_DEBUG_ITEMS,
        'recovery_actions': RECOVERY_ACTIONS,
        'example_agent_runs': EXAMPLE_AGENT_RUNS,
        'amanah_morning_operations_briefing': AMANAH_MORNING_OPERATIONS_BRIEFING,
        'microsoft_integration_items': MICROSOFT_INTEGRATION_ITEMS,
        'no_harm_gate_agents_items': NO_HARM_GATE_AGENTS_ITEMS,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })
