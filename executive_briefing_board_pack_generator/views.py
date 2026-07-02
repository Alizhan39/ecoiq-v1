from django.shortcuts import render

# Connected EcoIQ modules — the Generator turns stored evidence into decision-ready documents
CONNECTED_MODULES = [
    {'name': 'Data Room & Evidence Vault', 'role': 'Supplies the evidence links every pack cites.'},
    {'name': 'Portfolio & Country Transition Atlas', 'role': 'Supplies the country and portfolio data behind Country Transition Briefs.'},
    {'name': 'Command Centre', 'role': 'Supplies live project and pipeline status pulled into packs.'},
    {'name': 'Institutional Finance Engine', 'role': 'Supplies CAPEX, OPEX, payback and finance fit for investor and board packs.'},
    {'name': 'Governance & Expert Review Board', 'role': 'Supplies the review and approval status shown in every pack.'},
    {'name': 'Impact MRV Layer', 'role': 'Supplies verified before/after evidence for impact reports.'},
    {'name': 'Asset Passport', 'role': 'Supplies the structured asset record summarised in each pack.'},
    {'name': 'Supplier & Funding Marketplace', 'role': 'Supplies supplier and funding routes shown in relevant packs.'},
    {'name': 'Industrial Playbook Library', 'role': 'Supplies the recommended pathway referenced in board and investor packs.'},
    {'name': 'Microsoft Ecosystem Core Stack', 'role': 'Provides the agent and document-generation building blocks a production generator would run on.'},
    {'name': 'API & Integration Layer', 'role': 'Exposes pack generation and export through the API.'},
    {'name': 'Power BI', 'role': 'Supplies embedded dashboards linked from packs.'},
    {'name': 'SharePoint', 'role': 'Stores generated packs for collaboration.'},
    {'name': 'Teams', 'role': 'Routes packs for approval and sharing.'},
    {'name': 'Dynamics 365', 'role': 'Tracks which investors and funders received which packs.'},
]

CORE_PURPOSE = (
    'Convert EcoIQ intelligence into trusted executive documents for funding, approval, '
    'implementation and reporting.'
)

PACK_TYPES = [
    {
        'number': 1,
        'title': 'Investor Memo',
        'for_': 'Impact investors, infrastructure investors, climate funds, development '
                'banks, family offices and sovereign funds.',
        'includes': [
            'Executive summary', 'Investment thesis', 'Project pipeline', 'CAPEX pipeline',
            'Expected savings', 'Expected emissions reduction', 'Funding gap',
            'Risk-adjusted return', 'Evidence quality', 'Governance status',
            'MRV readiness', 'Maqasid/Mizan impact', 'Next investment action',
        ],
        'note': '',
    },
    {
        'number': 2,
        'title': 'Board Pack',
        'for_': 'Company directors, project owners, industrial groups and investment '
                'committees.',
        'includes': [
            'Decision required', 'Project background', 'Options considered',
            'Scenario comparison', 'CAPEX/OPEX/payback', 'Key risks', 'No Harm Gate',
            'Expert review status', 'Implementation timeline', 'Approval request',
        ],
        'note': '',
    },
    {
        'number': 3,
        'title': 'Akimat / Government Brief',
        'for_': 'Municipalities, regional authorities, public sector partners and '
                'national programmes.',
        'includes': [
            'Regional priority assets', 'Public health / pollution risks',
            'Clean heating opportunities', 'Finance-ready projects', 'Community benefit',
            'Required budget / co-finance', 'Implementation roadmap',
            'Verified impact tracking', 'Vulnerable community considerations',
        ],
        'note': '',
    },
    {
        'number': 4,
        'title': 'CSR / Donor Sponsor Pack',
        'for_': 'Corporates, philanthropists, sadaqah jariyah sponsors, charitable funds '
                'and community donors.',
        'includes': [
            'Community need', 'Before evidence', 'Project cost',
            'Household/community benefit', 'Clean heating or harm reduction outcome',
            'Sponsor visibility options', 'MRV proof plan', 'After-impact reporting',
            'Maqasid/Mizan meaning',
        ],
        'note': '',
    },
    {
        'number': 5,
        'title': 'Islamic Finance Brief',
        'for_': 'Islamic finance institutions, Shariah advisors, waqf boards, '
                'ijara/leasing providers and sukuk/infrastructure funders.',
        'includes': [
            'Project purpose', 'Asset-backed logic', 'Funding structure options',
            'Ijara/leasing suitability', 'Waqf suitability', 'Sadaqah jariyah suitability',
            'Debt burden check', 'Fairness/transparency check', 'Maqasid/Mizan mapping',
            'Shariah review required note',
        ],
        'note': 'EcoIQ provides ethical decision-support, not a fatwa. Islamic finance '
                'decisions require qualified Shariah review.',
    },
    {
        'number': 6,
        'title': 'Country Transition Brief',
        'for_': 'Development banks, government partners, country investors and strategic '
                'partners.',
        'includes': [
            'Country overview', 'Mapped assets', 'Highest-harm zones',
            'Highest-impact opportunities', 'Finance-ready pipeline', 'Sector comparison',
            'CAPEX pipeline', 'Funding gap', 'Verified impact projects',
            'Policy and implementation recommendations',
        ],
        'note': '',
    },
    {
        'number': 7,
        'title': 'Verified Impact Report',
        'for_': 'Investors, donors, governments, ESG teams and communities.',
        'includes': [
            'Baseline evidence', 'Action implemented', 'After evidence', 'Energy saved',
            'Cost saved', 'CO2 reduced', 'Water/waste reduction where relevant',
            'MRV verification status', 'Evidence quality', 'Before/after visuals',
            'Human approval record',
        ],
        'note': '',
    },
    {
        'number': 8,
        'title': 'Supplier RFQ Pack',
        'for_': 'Suppliers, installers, ESCOs and technology providers.',
        'includes': [
            'Asset summary', 'Site evidence', 'Required solution',
            'Technical requirements', 'Implementation constraints', 'Expected timeline',
            'Evidence needed from supplier', 'Quote template', 'Safety notes',
            'Approval process',
        ],
        'note': '',
    },
]

GENERATOR_WORKFLOW = [
    {
        'number': 1,
        'title': 'Select audience',
        'description': 'Options:',
        'items': [
            'Investor', 'Board', 'Government / akimat', 'CSR sponsor',
            'Islamic finance provider', 'Supplier', 'Community', 'Internal team',
        ],
    },
    {
        'number': 2,
        'title': 'Select scope',
        'description': 'Options:',
        'items': [
            'Single asset', 'Single project', 'Regional cluster', 'Country portfolio',
            'Sector portfolio', 'Verified impact portfolio',
        ],
    },
    {
        'number': 3,
        'title': 'Pull evidence',
        'description': 'EcoIQ pulls from:',
        'items': [
            'Asset Passport', 'Data Room', 'MRV Layer', 'Finance Engine',
            'Governance Review', 'Supplier Marketplace', 'Country Atlas', 'Command Centre',
        ],
    },
    {
        'number': 4,
        'title': 'Check evidence quality',
        'description': 'System checks:',
        'items': [
            'Missing documents', 'Weak evidence', 'Outdated files', 'Missing approvals',
            'Missing MRV baseline', 'Unsupported claims', 'No Harm Gate alerts',
        ],
    },
    {
        'number': 5,
        'title': 'Generate pack',
        'description': 'Output:',
        'items': [
            'Executive summary', 'Charts', 'Tables', 'Risks', 'Recommendations',
            'Decision request', 'Appendices', 'Evidence links',
        ],
    },
    {
        'number': 6,
        'title': 'Human review',
        'description': 'Expert / manager approves pack before sharing.',
        'items': [],
    },
    {
        'number': 7,
        'title': 'Export and share',
        'description': 'Export to:',
        'items': [
            'PDF', 'PowerPoint-style board pack', 'Word-style memo', 'SharePoint folder',
            'Teams message', 'Power BI dashboard link', 'Investor data room pack',
        ],
    },
]

REPORT_SECTIONS_TEMPLATE = [
    'Title page', 'Purpose', 'Decision required', 'Project / portfolio summary',
    'Evidence base', 'Financial model', 'Impact model', 'Risk register',
    'No Harm Gate status', 'Maqasid/Mizan assessment', 'Governance review status',
    'MRV plan or MRV outcome', 'Next actions', 'Appendices', 'Evidence links',
]

DASHBOARD_CARDS = [
    'Briefing packs generated', 'Packs awaiting review', 'Packs approved for sharing',
    'Investor memos ready', 'Board packs ready', 'Government briefs ready',
    'CSR packs ready', 'Islamic finance briefs ready', 'Verified impact reports ready',
    'Packs blocked by weak evidence', 'Missing approvals', 'No Harm Gate alerts',
]

EXAMPLE_PACKS = [
    {
        'pack': 'Kazakhstan Clean Heating Opportunity Pack',
        'audience': 'Akimat, CSR sponsors, Islamic charitable funders and development partners.',
        'includes': [
            'Mapped boiler houses and village heating needs',
            'Highest-harm heating clusters', 'Finance-ready clean heating projects',
            'CAPEX and funding gap', 'Supplier/funding routes', 'Maqasid/Mizan impact',
            'MRV plan', 'Sponsor-ready project list',
        ],
        'decision_requested': 'Approve pilot cluster and begin supplier quote collection.',
    },
    {
        'pack': 'UK Industrial Efficiency Investor Memo',
        'audience': 'Impact investors and SME finance providers.',
        'includes': [
            'Factory efficiency pipeline', 'Compressed air and waste heat quick wins',
            'Expected payback range', 'CAPEX pipeline', 'Supplier shortlist',
            'MRV evidence plan', 'Risk-adjusted opportunity summary',
        ],
        'decision_requested': 'Approve due diligence on top 5 finance-ready projects.',
    },
    {
        'pack': 'Boiler House #3 Board Pack',
        'audience': 'Municipality / project owner / investor committee.',
        'includes': [
            'Asset evidence', 'Options A-D', 'Finance model', 'No Harm Gate',
            'Expert review status', 'Supplier quote status', 'MRV baseline checklist',
            'Recommended staged pathway',
        ],
        'decision_requested': 'Approve Scenario B efficiency-first upgrade and prepare '
                               'Scenario C financing.',
    },
    {
        'pack': 'Village Clean Heating CSR / Sadaqah Jariyah Pack',
        'audience': 'CSR sponsors, donors and Islamic charitable funders.',
        'includes': [
            'Household need', 'Before evidence', 'Clean heating solution',
            'Sponsor amount', 'Expected health/harm reduction', 'MRV plan',
            'After-impact report structure', 'Maqasid/Mizan meaning',
        ],
        'decision_requested': 'Sponsor first 10 households and approve MRV reporting.',
    },
]

AI_WRITING_GUARDRAILS = [
    'Avoid unsupported ROI claims', 'Avoid unsupported emissions claims',
    'Avoid claiming verified impact without MRV evidence',
    'Avoid religious overclaiming', 'Show "Needs verification" where evidence is weak',
    'Cite evidence source links internally', 'Show assumptions clearly',
    'Distinguish estimate vs verified result', 'Require human approval before sharing',
]

MICROSOFT_INTEGRATION_ITEMS = [
    'SharePoint for storing packs', 'Teams for approval and sharing',
    'Power BI for embedded dashboards', 'Microsoft Fabric for data tables',
    'Power Automate for review workflow', 'Dynamics 365 for investor/funder pipeline',
    'Azure AI / Agent Framework for document generation',
    'Data Room & Evidence Vault for evidence links',
]

AMANAH_INTEGRATION_ITEMS = [
    'Prepare draft investor memos', 'Prepare country briefs',
    'Flag packs blocked by weak evidence', 'Update MRV impact reports',
    'Generate morning executive briefing', 'Prepare board decision notes',
    'Prepare donor/CSR impact summaries',
]
AMANAH_MORNING_BRIEFING_EXAMPLE = (
    '3 investor memos are ready, 2 board packs need finance review, 1 CSR pack is blocked '
    'by missing before photos, and Kazakhstan Clean Heating Opportunity Pack is ready for '
    'approval.'
)

NO_HARM_GATE_BRIEFINGS_ITEMS = [
    'Are all claims evidence-backed?',
    'Is verified impact actually MRV verified?',
    'Are assumptions visible?',
    'Are vulnerable communities represented carefully?',
    'Is sensitive data removed or permissioned?',
    'Is Islamic finance wording reviewed?',
    'Is human approval recorded?',
    'Are high-risk projects labelled correctly?',
    'Are public-facing statements safe?',
]

SAFETY_PRINCIPLES = [
    'Executive packs are decision-support documents, not legal, investment, engineering, '
    'environmental or religious advice.',
    'High-impact decisions require qualified expert review and human approval.',
    'Islamic finance and Maqasid/Mizan content requires qualified review where relevant.',
    'Public impact claims require MRV-backed evidence.',
    'If evidence is incomplete, the pack must show "Needs verification".',
    'EcoIQ should not share packs externally without human approval.',
]

CTA_BUTTONS = [
    {'label': 'Generate Investor Memo', 'anchor': '#pack-1'},
    {'label': 'Create Board Pack', 'anchor': '#pack-2'},
    {'label': 'Generate Akimat Brief', 'anchor': '#pack-3'},
    {'label': 'Create CSR Sponsor Pack', 'anchor': '#pack-4'},
    {'label': 'Prepare Islamic Finance Brief', 'anchor': '#pack-5'},
    {'label': 'Export Country Transition Brief', 'url_name': 'portfolio_country_transition_atlas:overview'},
    {'label': 'Generate Verified Impact Report', 'url_name': 'impact_mrv_layer:overview'},
    {'label': 'Send to Teams for Approval', 'anchor': '#microsoft-integration'},
    {'label': 'Save to Data Room', 'url_name': 'data_room_evidence_vault:overview'},
    {'label': 'Export PDF', 'anchor': '#generator-workflow'},
]


def overview(request):
    return render(request, 'executive_briefing_board_pack_generator/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_purpose': CORE_PURPOSE,
        'pack_types': PACK_TYPES,
        'generator_workflow': GENERATOR_WORKFLOW,
        'report_sections_template': REPORT_SECTIONS_TEMPLATE,
        'dashboard_cards': DASHBOARD_CARDS,
        'example_packs': EXAMPLE_PACKS,
        'ai_writing_guardrails': AI_WRITING_GUARDRAILS,
        'microsoft_integration_items': MICROSOFT_INTEGRATION_ITEMS,
        'amanah_integration_items': AMANAH_INTEGRATION_ITEMS,
        'amanah_morning_briefing_example': AMANAH_MORNING_BRIEFING_EXAMPLE,
        'no_harm_gate_briefings_items': NO_HARM_GATE_BRIEFINGS_ITEMS,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })
