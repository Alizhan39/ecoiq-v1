from django.shortcuts import render

# Connected EcoIQ modules — the Review Board is the human-in-the-loop layer over all of them
CONNECTED_MODULES = [
    {'name': 'Command Centre', 'role': 'Assigns reviewers to projects and surfaces review status across the pipeline.'},
    {'name': 'Institutional Finance Engine', 'role': 'Supplies the financial model a financial reviewer checks.'},
    {'name': 'Supplier & Funding Marketplace', 'role': 'Supplier and funder matches are held until reviewers approve outreach.'},
    {'name': 'Impact MRV Layer', 'role': 'Supplies the evidence quality and MRV status a reviewer checks before sign-off.'},
    {'name': 'Asset Passport', 'role': 'Supplies the structured asset record under review.'},
    {'name': 'Omnimodal Evidence Panel', 'role': 'Supplies the photo, video and document evidence a reviewer inspects.'},
    {'name': 'Amanah Autopilot', 'role': 'Prepares AI drafts and evidence packs overnight for the morning review queue.'},
    {'name': 'Microsoft Ecosystem Core Stack', 'role': 'Provides the agent, storage and governance building blocks a production review board would run on.'},
    {'name': 'Responsible AI tools', 'role': 'Support explainability, bias checking and audit of AI-generated recommendations.'},
    {'name': 'Maqasid/Mizan ethical scoring', 'role': 'Is checked by the Islamic Finance / Maqasid reviewer, not treated as a final ruling.'},
    {'name': 'No Harm Gate', 'role': 'Blocks a project from moving forward until harm, debt and evidence risks are checked.'},
    {'name': 'Power BI dashboards', 'role': 'Visualises review queue status and turnaround time.'},
    {'name': 'Teams approvals', 'role': 'Routes review requests and approval decisions to the right expert.'},
    {'name': 'SharePoint evidence packs', 'role': 'Stores the bundled evidence a reviewer works from.'},
]

CORE_PURPOSE = 'Make EcoIQ trustworthy, auditable and institution-ready.'

REVIEW_ROLES = [
    {
        'number': 1,
        'title': 'Technical Reviewer',
        'reviews': [
            'Engineering assumptions', 'Equipment suitability', 'Asset condition',
            'Feasibility of upgrade', 'Safety of proposed solution', 'Implementation risk',
        ],
        'note': '',
    },
    {
        'number': 2,
        'title': 'Financial Reviewer',
        'reviews': [
            'CAPEX', 'OPEX savings', 'Payback', 'IRR / NPV assumptions',
            'Funding structure', 'Debt burden', 'Grant / CSR / investor readiness',
        ],
        'note': '',
    },
    {
        'number': 3,
        'title': 'Environmental Reviewer',
        'reviews': [
            'Emissions reduction claim', 'Water impact', 'Waste impact', 'Pollution risk',
            'Permitting needs', 'MRV evidence quality',
        ],
        'note': '',
    },
    {
        'number': 4,
        'title': 'Safety Reviewer',
        'reviews': [
            'Worker safety', 'Boiler safety', 'Electrical safety', 'Mining safety',
            'Site access risk', 'Emergency planning', 'High-risk infrastructure risks',
        ],
        'note': '',
    },
    {
        'number': 5,
        'title': 'Islamic Finance / Maqasid Reviewer',
        'reviews': [
            'Maqasid/Mizan mapping', 'Islamic finance suitability',
            'Fairness of funding structure', 'Debt burden and harm risk',
            'Sadaqah jariyah / waqf / ijara suitability',
            'Wording to avoid unsupported religious claims',
        ],
        'note': 'EcoIQ provides ethical decision-support, not a fatwa. Qualified scholars '
                'or Islamic finance advisors must review where religious or Islamic finance '
                'judgement is required.',
    },
    {
        'number': 6,
        'title': 'Community / Stakeholder Reviewer',
        'reviews': [
            'Who benefits', 'Who may be harmed', 'Local acceptance', 'Vulnerable households',
            'Worker/community concerns', 'Transparency',
        ],
        'note': '',
    },
    {
        'number': 7,
        'title': 'Data / AI Governance Reviewer',
        'reviews': [
            'Evidence quality', 'Data privacy', 'Model output reliability',
            'Bias/fairness risks', 'Missing data', 'Audit trail',
            'Responsible AI compliance',
        ],
        'note': '',
    },
]

REVIEW_WORKFLOW = [
    {
        'number': 1,
        'title': 'AI Draft Created',
        'description': 'EcoIQ agents generate diagnosis, finance model, playbook, '
                        'supplier/funding match and MRV plan.',
        'items': [],
    },
    {
        'number': 2,
        'title': 'Evidence Pack Generated',
        'description': 'System bundles photos, documents, charts, sensor data, '
                        'assumptions, citations and missing data.',
        'items': [],
    },
    {
        'number': 3,
        'title': 'No Harm Gate Check',
        'description': 'System flags:',
        'items': [
            'Weak evidence', 'Safety risk', 'Debt burden', 'Community harm',
            'Environmental uncertainty', 'Unverified supplier',
            'Islamic finance review required', 'MRV baseline missing',
        ],
    },
    {
        'number': 4,
        'title': 'Expert Assignment',
        'description': 'Command Centre assigns reviewers by category.',
        'items': [],
    },
    {
        'number': 5,
        'title': 'Review Comments',
        'description': 'Experts add comments, corrections, approvals or rejection reasons.',
        'items': [],
    },
    {
        'number': 6,
        'title': 'Status Updated',
        'description': 'Project status becomes:',
        'items': [
            'AI Draft', 'Needs More Evidence', 'Technical Review Required',
            'Finance Review Required', 'Environmental Review Required',
            'Safety Review Required', 'Maqasid/Mizan Review Required',
            'Community Review Required', 'Approved for Supplier Outreach',
            'Approved for Funding Memo', 'Approved for Implementation',
            'Approved for MRV Reporting', 'Rejected / Revise',
        ],
    },
    {
        'number': 7,
        'title': 'Audit Trail Stored',
        'description': 'Every decision stores:',
        'items': [
            'Reviewer role', 'Reviewer name/status', 'Timestamp', 'Evidence version',
            'Decision', 'Comments', 'Unresolved risks',
        ],
    },
    {
        'number': 8,
        'title': 'Implementation Permission',
        'description': 'Only approved projects can move to supplier outreach, funding '
                        'submission, implementation or verified impact reporting.',
        'items': [],
    },
]

APPROVAL_BADGES = [
    'AI Draft', 'Needs Verification', 'Expert Review Pending', 'Technical Approved',
    'Finance Approved', 'Environmental Approved', 'Safety Approved',
    'Maqasid/Mizan Reviewed', 'Community Reviewed', 'Approved for Funding',
    'Approved for Supplier Outreach', 'Approved for Implementation',
    'Approved for MRV Reporting', 'Rejected / Revise',
]

EXAMPLE_CARDS = [
    {
        'project': 'Boiler House #3 Modernisation',
        'ai_recommendation': 'Insulate pipes, install smart meters, service boiler and '
                              'prepare staged equipment upgrade.',
        'review_required': [
            'Technical reviewer: confirm heat loss assumptions and safety',
            'Financial reviewer: check CAPEX and payback',
            'Environmental reviewer: confirm emissions reduction method',
            'Maqasid/Mizan reviewer: check harm reduction and fairness logic',
            'Community reviewer: confirm household benefit and local acceptance',
        ],
        'status': 'Needs technical review before supplier outreach.',
        'no_harm_gate': [
            'MRV baseline incomplete', 'Supplier not yet verified',
            '12-month fuel data missing',
        ],
        'next_action': 'Collect fuel bills, request engineer review, then prepare supplier RFQ.',
    },
    {
        'project': 'SMR Feasibility Study',
        'ai_recommendation': 'Do not proceed directly. Run staged pathway: efficiency '
                              'first, renewables/storage comparison, grid study, '
                              'regulatory readiness, safety and waste feasibility.',
        'review_required': [
            'Nuclear safety expert', 'Regulator/legal review', 'Environmental review',
            'Financial/debt burden review', 'Community acceptance review',
            'Maqasid/Mizan review',
        ],
        'status': 'High-risk infrastructure — independent expert review required.',
        'no_harm_gate': [],
        'next_action': '',
    },
]

NO_HARM_GATE_REVIEW_INTRO = 'Before any project moves forward, check:'
NO_HARM_GATE_REVIEW_ITEMS = [
    'Is evidence strong enough?',
    'Are assumptions transparent?',
    'Could workers be harmed?',
    'Could communities be harmed?',
    'Could debt burden become unjust?',
    'Could environmental damage increase?',
    'Is the supplier qualified?',
    'Is finance fair and transparent?',
    'Is Islamic finance review required?',
    'Is MRV baseline complete?',
    'Is human approval recorded?',
]

RESPONSIBLE_AI_MICROSOFT_INTRO = 'EcoIQ can use:'
RESPONSIBLE_AI_MICROSOFT_ITEMS = [
    'Microsoft Responsible AI Toolbox for explainability and monitoring',
    'Presidio for privacy / PII protection',
    'PyRIT for red-teaming AI agents',
    'Microsoft Fabric for governed evidence storage',
    'Power BI for review dashboards',
    'Teams for approval workflows',
    'SharePoint for evidence packs and reports',
    'Power Automate for routing review tasks',
    'Dynamics 365 for investor/funder pipeline approvals',
]

REVIEW_BOARD_DASHBOARD_CARDS = [
    'Projects awaiting review', 'Projects needing more evidence',
    'Projects approved for funding', 'Projects approved for implementation',
    'High-risk No Harm Gate alerts', 'Islamic finance review required',
    'MRV reports awaiting verification', 'Average review time', 'Evidence quality average',
]

REVIEWER_TABLE_FIELDS = [
    'Project name', 'Asset type', 'Reviewer role', 'Reviewer name/status',
    'Evidence version', 'Risk level', 'Decision', 'Comments', 'Due date', 'Next action',
]

HUMAN_APPROVAL_REQUIRED_COPY = (
    'EcoIQ agents can prepare recommendations, memos and implementation plans, but they '
    'cannot approve high-impact decisions by themselves. Every industrial, financial, '
    'safety, environmental and Islamic finance decision requires human review, documented '
    'approval and an evidence trail.'
)

SAFETY_PRINCIPLES = [
    'EcoIQ is a decision-support platform, not a replacement for qualified engineers, '
    'auditors, lawyers, financial advisors, safety inspectors, environmental consultants '
    'or Islamic finance scholars.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
    'Islamic finance decisions require qualified Shariah review.',
    'High-impact infrastructure decisions such as SMR require independent regulatory, '
    'safety, environmental and community review.',
    'No supplier, funder or public claim should be approved without evidence and human sign-off.',
    'If evidence is incomplete, the system must show "Needs verification".',
]

CTA_BUTTONS = [
    {'label': 'Submit for Expert Review', 'anchor': '#review-workflow'},
    {'label': 'Request Technical Review', 'anchor': '#review-roles'},
    {'label': 'Request Maqasid/Mizan Review', 'anchor': '#review-roles'},
    {'label': 'Approve for Supplier Outreach', 'url_name': 'supplier_funding_marketplace:overview'},
    {'label': 'Approve for Funding Memo', 'url_name': 'leads:request_review'},
    {'label': 'Approve for Implementation', 'url_name': 'command_centre:overview'},
    {'label': 'Request More Evidence', 'anchor': '#no-harm-gate-review'},
    {'label': 'Export Evidence Pack', 'anchor': '#responsible-ai-microsoft'},
]


def overview(request):
    return render(request, 'governance_expert_review_board/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_purpose': CORE_PURPOSE,
        'review_roles': REVIEW_ROLES,
        'review_workflow': REVIEW_WORKFLOW,
        'approval_badges': APPROVAL_BADGES,
        'example_cards': EXAMPLE_CARDS,
        'no_harm_gate_review_intro': NO_HARM_GATE_REVIEW_INTRO,
        'no_harm_gate_review_items': NO_HARM_GATE_REVIEW_ITEMS,
        'responsible_ai_microsoft_intro': RESPONSIBLE_AI_MICROSOFT_INTRO,
        'responsible_ai_microsoft_items': RESPONSIBLE_AI_MICROSOFT_ITEMS,
        'review_board_dashboard_cards': REVIEW_BOARD_DASHBOARD_CARDS,
        'reviewer_table_fields': REVIEWER_TABLE_FIELDS,
        'human_approval_required_copy': HUMAN_APPROVAL_REQUIRED_COPY,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })
