from django.shortcuts import render

# Connected EcoIQ modules — the Renewal Engine manages what happens after the sale
CONNECTED_MODULES = [
    {'name': 'Sales CRM & Partner Pipeline', 'role': 'Hands off a won opportunity into the customer success lifecycle.'},
    {'name': 'Revenue & Pricing Engine', 'role': 'Supplies the package purchased that onboarding and renewal track against.'},
    {'name': 'Command Centre', 'role': 'Surfaces live project status feeding account health.'},
    {'name': 'Asset Passport', 'role': 'Supplies the asset records created during onboarding and expansion.'},
    {'name': 'Impact MRV Layer', 'role': 'Supplies MRV progress that drives health score and renewal readiness.'},
    {'name': 'Data Room & Evidence Vault', 'role': 'Supplies evidence completeness used in health scoring.'},
    {'name': 'Executive Briefing & Board Pack Generator', 'role': 'Generates the value review and renewal proposal documents.'},
    {'name': 'Public Trust & Impact Portal', 'role': 'Supplies the approved public story used in sponsor renewal updates.'},
    {'name': 'Portfolio & Country Transition Atlas', 'role': 'Supplies expansion opportunities across regions and sectors.'},
    {'name': 'Governance & Expert Review Board', 'role': 'Supplies the stakeholder approval status tracked per account.'},
    {'name': 'Supplier & Funding Marketplace', 'role': 'Supplies supplier and funding progress relevant to renewal.'},
    {'name': 'Microsoft Ecosystem Core Stack', 'role': 'Underlies Microsoft-based renewal and expansion pilots.'},
    {'name': 'Teams', 'role': 'Delivers customer success alerts and follow-up reminders.'},
    {'name': 'Power BI', 'role': 'Renders account health dashboards.'},
    {'name': 'Dynamics 365', 'role': 'Can host account, renewal and opportunity records.'},
    {'name': 'SharePoint', 'role': 'Stores customer reports and evidence packs.'},
]

CORE_PURPOSE = 'Make EcoIQ sticky, measurable and renewal-ready after the first sale.'

LIFECYCLE_STAGES = [
    {
        'number': 1,
        'title': 'Contract Won',
        'description': 'Customer signs pilot, subscription, sponsor pack or project report agreement.',
        'items': [],
    },
    {
        'number': 2,
        'title': 'Onboarding',
        'description': 'EcoIQ sets up:',
        'items': [
            'Account owner', 'Users', 'Project scope', 'Assets', 'Permissions',
            'Data room', 'Reporting expectations', 'Success metrics',
        ],
    },
    {
        'number': 3,
        'title': 'First Value Delivered',
        'description': 'Customer receives first output:',
        'items': [
            'Asset Passport', 'Free Scan result', 'Mobile Inspection report',
            'Investor Memo', 'MRV baseline', 'Board Pack', 'Country Atlas brief',
            'Supplier/Funding match',
        ],
    },
    {
        'number': 4,
        'title': 'Active Usage',
        'description': 'Customer actively uses:',
        'items': [
            'Command Centre', 'Data Room', 'MRV Layer', 'Finance Engine',
            'Supplier Marketplace', 'Public Trust Portal', 'Executive Briefing Generator',
        ],
    },
    {
        'number': 5,
        'title': 'Impact Progress',
        'description': 'Project moves toward:',
        'items': [
            'Implementation', 'Evidence completion', 'MRV verification',
            'Public summary approval', 'Finance readiness / supplier-funding progress',
        ],
    },
    {
        'number': 6,
        'title': 'Value Review',
        'description': 'EcoIQ reviews:',
        'items': [
            'Outputs delivered', 'Time saved', 'Risks identified', 'Evidence collected',
            'Funding opportunities', 'Verified impact', 'Next opportunities',
        ],
    },
    {
        'number': 7,
        'title': 'Renewal Preparation',
        'description': 'EcoIQ checks:',
        'items': [
            'Usage level', 'Value delivered', 'Stakeholder satisfaction',
            'Unresolved blockers', 'MRV progress', 'Expansion potential', 'Renewal risk',
        ],
    },
    {
        'number': 8,
        'title': 'Renewal / Expansion',
        'description': 'Customer renews or expands into:',
        'items': [
            'More assets', 'More countries', 'More MRV packs', 'More reports',
            'Enterprise subscription', 'API integration', 'Public Trust Portal reporting',
            'Supplier/funding marketplace', 'Microsoft integration',
        ],
    },
]

HEALTH_SCORE_ITEMS = [
    'Onboarding completion', 'Usage frequency', 'Evidence completeness',
    'Asset passports created', 'MRV progress', 'Reports delivered',
    'Stakeholder approvals completed', 'Unresolved blockers', 'Support issues',
    'Renewal date proximity', 'Commercial value delivered',
    'Maqasid/Mizan impact progress',
]
HEALTH_LABELS = ['Healthy', 'Watch', 'At Risk', 'Needs Executive Attention', 'Expansion Ready']

RENEWAL_RISK_SIGNALS = [
    'Customer has not uploaded evidence', 'Asset Passport incomplete',
    'MRV baseline missing', 'No stakeholder approval', 'Report not delivered',
    'No active usage in 30 days', 'Supplier/funding match stalled',
    'Public impact story blocked', 'Unpaid invoice', 'Decision maker changed',
    'Unresolved support issue', 'Project impact not visible',
]

EXPANSION_SIGNALS = [
    'Multiple assets identified', 'One project verified successfully',
    'Customer asks for more reports', 'Country atlas opportunity exists',
    'Sponsor-ready projects available', 'Supplier/funding demand increasing',
    'API integration requested', 'Power BI dashboard requested',
    'Public impact reporting requested', 'Additional departments or regions involved',
]

DASHBOARD_CARDS = [
    'Active customers', 'Onboarding accounts', 'Healthy accounts', 'At-risk accounts',
    'Expansion-ready accounts', 'Renewals due this quarter', 'MRV projects in progress',
    'Verified impact delivered', 'Reports delivered', 'Data Room completeness average',
    'Asset Passports created', 'Public impact stories approved', 'Support issues open',
    'Upsell pipeline value', 'Renewal pipeline value',
]

ACCOUNT_TABLE_FIELDS = [
    'Account name', 'Customer type', 'Country', 'Sector', 'Package purchased',
    'Contract start date', 'Renewal date', 'Account owner', 'Health score',
    'Onboarding status', 'Usage status', 'Evidence completeness', 'MRV status',
    'Reports delivered', 'Stakeholder approval status', 'Support status',
    'Expansion potential', 'Renewal risk', 'Next action',
]

CUSTOMER_TYPES = [
    'Industrial company', 'Municipality / akimat', 'Government agency', 'CSR sponsor',
    'Islamic finance provider', 'Impact investor', 'Development bank',
    'Supplier / installer', 'Microsoft ecosystem partner', 'NGO / community organisation',
]

PLAYBOOKS = [
    {
        'number': 1,
        'title': 'New Customer Onboarding Playbook',
        'steps': [
            'Confirm scope', 'Create account', 'Assign owner', 'Set permissions',
            'Create first Asset Passport', 'Open Data Room', 'Schedule kickoff',
            'Define success metrics', 'Create first report timeline',
        ],
    },
    {
        'number': 2,
        'title': 'MRV Completion Playbook',
        'steps': [
            'Check baseline evidence', 'Collect after-data', 'Review evidence quality',
            'Request expert review', 'Generate MRV report',
            'Approve public summary if relevant',
        ],
    },
    {
        'number': 3,
        'title': 'Renewal Rescue Playbook',
        'steps': [
            'Identify blocker', 'Schedule executive review', 'Deliver value summary',
            'Resolve missing evidence', 'Prepare renewal proposal',
            'Show next impact opportunity',
        ],
    },
    {
        'number': 4,
        'title': 'Expansion Playbook',
        'steps': [
            'Identify new assets', 'Prepare portfolio view', 'Generate expansion proposal',
            'Show verified impact achieved',
            'Propose enterprise subscription or country atlas',
        ],
    },
    {
        'number': 5,
        'title': 'Sponsor Reporting Playbook',
        'steps': [
            'Collect before/after evidence', 'Verify MRV status',
            'Prepare sponsor impact pack', 'Approve public story', 'Send sponsor report',
            'Propose next sponsored project',
        ],
    },
]

EXAMPLE_ACCOUNTS = [
    {
        'account': 'Kazakhstan Regional Akimat',
        'package': 'Country Atlas + Clean Heating Pilot',
        'health': 'Watch',
        'issue': 'MRV baseline incomplete for several heating projects.',
        'value_delivered': '',
        'next_action': 'Request missing fuel data and schedule technical review.',
        'expansion_opportunity': 'Regional clean heating programme and Public Trust Portal reporting.',
    },
    {
        'account': 'UK Manufacturing SME',
        'package': 'Asset Passport + Mobile Inspection + Investor Memo',
        'health': 'Expansion Ready',
        'issue': '',
        'value_delivered': 'Factory energy losses identified, compressed air playbook '
                            'matched, finance memo prepared.',
        'next_action': 'Offer MRV Pack and Supplier/Funding Match.',
        'expansion_opportunity': '',
    },
    {
        'account': 'CSR Sponsor',
        'package': 'Village Clean Heating Sponsor Impact Pack',
        'health': 'Healthy',
        'issue': '',
        'value_delivered': 'Sponsor pack generated, project evidence collected, public '
                            'summary awaiting approval.',
        'next_action': 'Prepare second sponsor project list.',
        'expansion_opportunity': '',
    },
    {
        'account': 'Supplier Partner',
        'package': 'Supplier Marketplace Access',
        'health': 'Watch',
        'issue': 'Supplier profile missing certifications and verified project history.',
        'value_delivered': '',
        'next_action': 'Request documents and update supplier fit score.',
        'expansion_opportunity': '',
    },
    {
        'account': 'Islamic Finance Provider',
        'package': 'Investor Readiness + Islamic Finance Brief',
        'health': 'Needs Executive Attention',
        'issue': 'Shariah review process not confirmed.',
        'value_delivered': '',
        'next_action': 'Prepare qualified review workflow and update No Harm Gate notes.',
        'expansion_opportunity': '',
    },
]

AMANAH_ITEMS = [
    'Detect at-risk accounts', 'Find renewals due soon', 'Identify accounts ready for upsell',
    'Flag missing MRV evidence', 'Prepare customer value summaries', 'Draft renewal emails',
    'Prepare sponsor impact updates', 'Flag stalled stakeholder approvals',
    'Prepare morning customer success briefing',
]
AMANAH_MORNING_BRIEFING_EXAMPLE = (
    '5 accounts need follow-up, 2 renewals are due within 30 days, 3 projects are '
    'blocked by missing MRV evidence, 1 sponsor report is ready, and 2 accounts are '
    'expansion-ready.'
)

MICROSOFT_DYNAMICS_ITEMS = [
    'Dynamics 365 for accounts, renewals and opportunities',
    'Teams for customer success alerts',
    'Outlook / Microsoft Graph for follow-up reminders',
    'SharePoint for reports and evidence packs', 'Power BI for health dashboards',
    'Power Automate for renewal workflows',
    'Microsoft Fabric for customer usage analytics',
]

VALUE_REVIEW_SUMMARY_ITEMS = [
    'What was purchased', 'What was delivered', 'Evidence collected',
    'Reports generated', 'Risks identified', 'Impact achieved', 'MRV progress',
    'Money saved or opportunity created where evidence supports it',
    'Stakeholder approvals completed', 'Next recommended module',
    'Renewal / expansion recommendation',
]

NO_HARM_GATE_ITEMS = [
    'Has real value been delivered?',
    'Are claims evidence-backed?',
    'Is the customer vulnerable or under pressure?',
    'Are impact claims MRV-backed?',
    'Is pricing transparent?',
    'Are unresolved issues disclosed?',
    'Is Islamic finance wording reviewed where relevant?',
    'Are public impact statements approved?',
    'Is upsell appropriate and beneficial?',
    'Is human approval required before external reporting?',
]

SAFETY_PRINCIPLES = [
    'Customer success recommendations are commercial support tools, not legal, '
    'investment or financial advice.',
    'EcoIQ must not overpromise guaranteed savings, funding, emissions reduction or impact.',
    'Renewal and upsell should be based on real delivered value.',
    'Public impact claims require MRV evidence and approval.',
    'Islamic finance and Maqasid/Mizan content requires qualified review where relevant.',
    'Customer data, evidence and communications must be permissioned and handled securely.',
]

CTA_BUTTONS = [
    {'label': 'Open Customer Success Dashboard', 'anchor': '#dashboard-cards'},
    {'label': 'Onboard New Customer', 'anchor': '#stage-2'},
    {'label': 'Generate Value Review', 'anchor': '#value-review-summary'},
    {'label': 'Check Renewal Risk', 'anchor': '#renewal-risk-signals'},
    {'label': 'Prepare Renewal Proposal', 'anchor': '#playbook-3'},
    {'label': 'Identify Expansion Opportunity', 'anchor': '#expansion-signals'},
    {'label': 'Generate Sponsor Update', 'anchor': '#playbook-5'},
    {'label': 'Request Missing Evidence', 'url_name': 'data_room_evidence_vault:overview'},
    {'label': 'Send Follow-Up to Teams', 'anchor': '#microsoft-dynamics-integration'},
    {'label': 'Create Customer Health Report', 'anchor': '#account-health-score'},
]


def overview(request):
    return render(request, 'customer_success_renewal_engine/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_purpose': CORE_PURPOSE,
        'lifecycle_stages': LIFECYCLE_STAGES,
        'health_score_items': HEALTH_SCORE_ITEMS,
        'health_labels': HEALTH_LABELS,
        'renewal_risk_signals': RENEWAL_RISK_SIGNALS,
        'expansion_signals': EXPANSION_SIGNALS,
        'dashboard_cards': DASHBOARD_CARDS,
        'account_table_fields': ACCOUNT_TABLE_FIELDS,
        'customer_types': CUSTOMER_TYPES,
        'playbooks': PLAYBOOKS,
        'example_accounts': EXAMPLE_ACCOUNTS,
        'amanah_items': AMANAH_ITEMS,
        'amanah_morning_briefing_example': AMANAH_MORNING_BRIEFING_EXAMPLE,
        'microsoft_dynamics_items': MICROSOFT_DYNAMICS_ITEMS,
        'value_review_summary_items': VALUE_REVIEW_SUMMARY_ITEMS,
        'no_harm_gate_items': NO_HARM_GATE_ITEMS,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })
