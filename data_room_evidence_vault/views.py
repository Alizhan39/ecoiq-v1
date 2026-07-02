from django.shortcuts import render

# Connected EcoIQ modules — the Vault is the trusted store behind every other module
CONNECTED_MODULES = [
    {'name': 'Asset Passport', 'role': 'Supplies the asset record every vault document is linked to.'},
    {'name': 'Mobile / iPad Inspection Mode', 'role': 'Uploads field-captured evidence directly into the vault.'},
    {'name': 'Omnimodal Evidence Panel', 'role': 'Displays the photo, video and document evidence stored in the vault.'},
    {'name': 'Impact MRV Layer', 'role': 'Stores baseline, after-data and verification proof in the vault.'},
    {'name': 'Institutional Finance Engine', 'role': 'Stores finance models and memos in the vault.'},
    {'name': 'Supplier & Funding Marketplace', 'role': 'Stores supplier quotes and funding documents in the vault.'},
    {'name': 'Governance & Expert Review Board', 'role': 'Stores review comments and approval records in the vault.'},
    {'name': 'Command Centre', 'role': 'Surfaces vault completeness and missing-evidence alerts across the pipeline.'},
    {'name': 'API & Integration Layer', 'role': 'Exposes vault documents and evidence packs through the API.'},
    {'name': 'Microsoft Ecosystem Core Stack', 'role': 'Provides the storage, governance and dashboard building blocks a production vault would run on.'},
    {'name': 'SharePoint', 'role': 'Stores evidence packs and reports for collaboration.'},
    {'name': 'Azure Blob Storage', 'role': 'Stores photos, videos and large files.'},
    {'name': 'Microsoft Fabric', 'role': 'Stores structured evidence metadata.'},
    {'name': 'Power BI', 'role': 'Visualises evidence completeness dashboards.'},
    {'name': 'Teams', 'role': 'Delivers review notifications and approval workflows.'},
    {'name': 'Dynamics 365', 'role': 'Tracks investor and funder access to shared evidence packs.'},
]

CORE_PURPOSE = (
    'Turn scattered project files into a trusted, permissioned evidence base for '
    'investment, implementation and verified impact.'
)

VAULT_CATEGORIES = [
    {
        'number': 1,
        'title': 'Asset Evidence',
        'stores': [
            'Asset overview photos', 'Equipment close-ups', 'Nameplate photos', 'Videos',
            'Site maps', 'GPS/location records', 'Inspection notes', 'Voice notes',
            'Baseline readings', 'Sensor snapshots',
        ],
    },
    {
        'number': 2,
        'title': 'Technical Documents',
        'stores': [
            'Equipment manuals', 'Maintenance logs', 'Engineering reports',
            'Inspection reports', 'Feasibility studies', 'Digital twin data exports',
            'Technical drawings', 'Energy audits', 'Water audits', 'Safety documents',
        ],
    },
    {
        'number': 3,
        'title': 'Financial Documents',
        'stores': [
            'CAPEX estimates', 'OPEX assumptions', 'Payback calculations', 'IRR / NPV models',
            'Investor memos', 'Grant briefs', 'CSR sponsor memos', 'Islamic finance summaries',
            'Funding applications', 'Board memos', 'Budget approvals',
        ],
    },
    {
        'number': 4,
        'title': 'Supplier & Procurement Documents',
        'stores': [
            'Supplier quotes', 'RFQs', 'Proposals', 'Warranties', 'Installation plans',
            'Equipment specs', 'Contractor documents', 'Invoices', 'Delivery records',
            'Procurement approvals',
        ],
    },
    {
        'number': 5,
        'title': 'MRV Evidence',
        'stores': [
            'Baseline evidence', 'After-upgrade evidence', 'Meter readings', 'Energy bills',
            'Fuel bills', 'Water bills', 'Emissions reports', 'Before/after photos',
            'Sensor logs', 'Third-party verification', 'Impact calculations',
            'Verified impact reports',
        ],
    },
    {
        'number': 6,
        'title': 'Governance & Approval Records',
        'stores': [
            'Expert review comments', 'Technical approvals', 'Financial approvals',
            'Environmental approvals', 'Safety approvals', 'Maqasid/Mizan review',
            'Islamic finance review', 'Community review', 'No Harm Gate decisions',
            'Human approval records', 'Rejection/revision history',
        ],
    },
    {
        'number': 7,
        'title': 'Legal / Compliance Documents',
        'stores': [
            'Permits', 'Contracts', 'Consents', 'Data sharing agreements',
            'Privacy notices', 'Audit records', 'Environmental compliance documents',
            'Safety compliance documents', 'Shariah review documents where relevant',
        ],
    },
    {
        'number': 8,
        'title': 'Reports & Exports',
        'stores': [
            'Investor reports', 'Government reports', 'Power BI exports', 'MRV reports',
            'PDF reports', 'Excel exports', 'SharePoint evidence packs', 'Board packs',
            'Public impact summaries',
        ],
    },
]

VAULT_WORKFLOW = [
    {
        'number': 1,
        'title': 'Evidence Captured',
        'description': 'Mobile Inspection, API upload, manual upload, sensor ingestion or '
                        'document import captures project evidence.',
        'items': [],
    },
    {
        'number': 2,
        'title': 'Evidence Classified',
        'description': 'EcoIQ classifies each file:',
        'items': [
            'Photo', 'Video', 'Bill', 'Technical report', 'Supplier quote', 'Finance memo',
            'MRV proof', 'Approval record', 'Legal/compliance document',
        ],
    },
    {
        'number': 3,
        'title': 'Evidence Linked',
        'description': 'Each file is linked to:',
        'items': [
            'Project', 'Asset passport', 'Inspection', 'Playbook', 'Finance model',
            'Supplier/funder match', 'Expert review', 'MRV report', 'Impact claim',
        ],
    },
    {
        'number': 4,
        'title': 'Evidence Quality Scored',
        'description': 'EcoIQ scores evidence:',
        'items': ['Strong', 'Medium', 'Weak', 'Missing', 'Outdated', 'Needs verification'],
    },
    {
        'number': 5,
        'title': 'Permissions Applied',
        'description': 'Access is controlled by role:',
        'items': [
            'Project owner', 'Inspector', 'Engineer', 'Financial reviewer', 'Supplier',
            'Funder', 'Investor', 'Government reviewer', 'Community viewer', 'Auditor',
            'Admin',
        ],
    },
    {
        'number': 6,
        'title': 'Version Control',
        'description': 'Every upload, update and approval creates a versioned record.',
        'items': [],
    },
    {
        'number': 7,
        'title': 'Audit Trail Stored',
        'description': 'Every view, upload, download, approval and change is logged.',
        'items': [],
    },
    {
        'number': 8,
        'title': 'Evidence Pack Generated',
        'description': 'EcoIQ can generate evidence packs for:',
        'items': [
            'Investor due diligence', 'Grant application', 'Expert review', 'Supplier RFQ',
            'MRV verification', 'Government reporting', 'CSR sponsor reporting',
            'Islamic finance review',
        ],
    },
]

DASHBOARD_CARDS = [
    'Total documents', 'Evidence packs created', 'Projects with complete evidence',
    'Projects missing baseline data', 'Projects missing after-data',
    'Pending expert approvals', 'Supplier quotes uploaded', 'Finance memos ready',
    'MRV proofs verified', 'Weak evidence alerts', 'Expiring documents',
    'Restricted documents', 'Recent uploads',
]

DOCUMENT_TABLE_FIELDS = [
    'File name', 'Project', 'Asset', 'Document category', 'Evidence type',
    'Evidence quality', 'Upload date', 'Uploaded by', 'Version', 'Linked module',
    'Permission level', 'Review status', 'Expiry date if relevant', 'Next action',
]

FILTERS = [
    'Project', 'Asset', 'Country', 'Sector', 'Document category', 'Evidence quality',
    'Upload date', 'Owner', 'Permission level', 'Review status', 'MRV status',
    'Funding status', 'Supplier status', 'No Harm Gate relevance',
]

PERMISSION_LEVELS = [
    {'number': 1, 'title': 'Private', 'description': 'Only project admin and approved users.'},
    {'number': 2, 'title': 'Expert Review', 'description': 'Visible to assigned technical, financial, environmental, safety or Maqasid/Mizan reviewers.'},
    {'number': 3, 'title': 'Investor Due Diligence', 'description': 'Visible to approved investors/funders.'},
    {'number': 4, 'title': 'Supplier Pack', 'description': 'Visible to approved suppliers after human approval.'},
    {'number': 5, 'title': 'Government / Akimat Review', 'description': 'Visible to approved public sector reviewers.'},
    {'number': 6, 'title': 'Public Summary', 'description': 'Only non-sensitive, approved impact summary data.'},
]

EVIDENCE_PACK_TYPES = [
    'Investor Due Diligence Pack', 'Supplier RFQ Pack', 'Grant Application Pack',
    'CSR Sponsor Pack', 'Islamic Finance Review Pack', 'MRV Verification Pack',
    'Government Reporting Pack', 'Board Approval Pack', 'Community Impact Summary',
]

EVIDENCE_PACK_CONTENTS = [
    'Executive summary', 'Asset passport', 'Baseline evidence', 'Photos/videos',
    'Technical documents', 'Finance memo', 'Supplier quotes', 'Risk register',
    'No Harm Gate notes', 'Maqasid/Mizan summary', 'MRV plan', 'Expert approvals',
    'Missing evidence checklist',
]

EXAMPLE_CARDS = [
    {
        'project': 'Boiler House #3 Modernisation',
        'vault_contents': [
            '8 inspection photos', '1 fuel bill', '1 meter reading', '1 voice note',
            '1 draft finance memo', '2 supplier quotes', '1 technical review request',
            'MRV baseline checklist', 'No Harm Gate notes',
        ],
        'evidence_status': 'Medium evidence — needs 12 months of fuel bills and engineer '
                            'review before funding submission.',
        'generated_pack': 'Investor Due Diligence Pack',
        'next_action': 'Request missing fuel data and attach technical approval.',
    },
    {
        'project': 'Village Clean Heating Transition',
        'vault_contents': [
            'Before photos of coal stove', 'Household consent record', 'Sponsor memo',
            'Equipment quote', 'Installation photo', 'After-upgrade comfort survey',
            'MRV impact report',
        ],
        'evidence_status': 'Strong after baseline completion.',
        'generated_pack': 'CSR / Sadaqah Jariyah Impact Pack',
        'next_action': '',
    },
    {
        'project': 'SMR Feasibility Study',
        'vault_contents': [
            'Energy demand analysis', 'Grid study', 'Water availability report',
            'Regulatory readiness note', 'Safety review request',
            'Public acceptance evidence', 'No Harm Gate high-risk register',
        ],
        'evidence_status': 'High-risk infrastructure — independent expert review required.',
        'generated_pack': '',
        'next_action': '',
    },
]

MICROSOFT_INTEGRATION_ITEMS = [
    'Azure Blob Storage for photos, videos and large files',
    'SharePoint for document collaboration and evidence packs',
    'Microsoft Fabric for structured evidence metadata',
    'Power BI for evidence completeness dashboards',
    'Teams for review notifications and approval workflows',
    'Power Automate for routing evidence packs',
    'Microsoft Graph for document permissions and collaboration',
    'Purview-style governance concept for compliance and classification',
    'Presidio for PII detection in documents, images and notes',
]

API_INTEGRATION_ITEMS = [
    'Upload documents', 'Retrieve evidence packs', 'Update document status',
    'Link evidence to assets', 'Link evidence to MRV claims', 'Trigger expert review',
    'Export investor packs', 'Sync with SharePoint', 'Sync with Power BI',
    'Send Teams approval notifications',
]

API_EXAMPLES = [
    'POST /api/vault/documents/', 'GET /api/vault/documents/{id}/',
    'PATCH /api/vault/documents/{id}/status/', 'POST /api/vault/evidence-packs/',
    'GET /api/vault/evidence-packs/{id}/', 'POST /api/vault/evidence-packs/{id}/share/',
    'GET /api/vault/projects/{id}/completeness/',
    'POST /api/vault/documents/{id}/link-asset/',
    'POST /api/vault/documents/{id}/link-mrv-claim/',
]

WEBHOOK_EVENTS = [
    'vault.document_uploaded', 'vault.document_classified', 'vault.evidence_pack_created',
    'vault.evidence_pack_shared', 'vault.missing_evidence_detected',
    'vault.document_expiring', 'vault.permission_changed', 'vault.review_requested',
    'vault.review_completed',
]

EVIDENCE_COMPLETENESS_ITEMS = [
    'Baseline evidence present', 'After-data present', 'Asset photos present',
    'Energy/fuel/water bills present', 'Supplier quote present', 'Finance memo present',
    'Expert approval present', 'MRV proof present', 'No Harm Gate reviewed',
    'Missing documents flagged',
]

TRUST_AUDIT_TRAIL_ITEMS = [
    'Source', 'Uploader', 'Timestamp', 'Linked project', 'Linked asset', 'Linked claim',
    'Version', 'Permission level', 'Review status', 'Access history', 'Approval history',
    'Evidence quality score',
]

AMANAH_INTEGRATION_ITEMS = [
    'Detect missing documents', 'Flag weak evidence', 'Identify expired documents',
    'Prepare investor evidence packs', 'Prepare expert review packs',
    'Check if MRV claims lack proof', 'Identify projects ready for funding submission',
    'Prepare morning evidence checklist',
]
AMANAH_MORNING_BRIEFING_EXAMPLE = (
    '4 projects have missing baseline evidence, 2 investor packs are ready, 3 supplier '
    'quotes were uploaded, and 1 MRV claim needs stronger proof.'
)

NO_HARM_GATE_EVIDENCE_ITEMS = [
    'Is the evidence real and timestamped?',
    'Is the evidence linked to the correct project?',
    'Is sensitive data protected?',
    'Is consent required?',
    'Is personal data visible?',
    'Is the evidence strong enough for the claim?',
    'Has human approval been recorded?',
    'Is the document outdated?',
    'Is the impact claim supported by before/after proof?',
    'Is Islamic finance or Maqasid wording reviewed?',
]

SAFETY_PRINCIPLES = [
    'EcoIQ Data Room is a structured evidence and due diligence layer, not a legal, '
    'financial or engineering certification system.',
    'Access to sensitive industrial, personal, financial or community data must be '
    'permissioned.',
    'Investor, supplier, public and government sharing requires human approval.',
    'Impact claims require before/after evidence.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
    'Islamic finance documents require qualified review where relevant.',
    'If evidence is incomplete, the system must show "Needs verification".',
]

CTA_BUTTONS = [
    {'label': 'Open Data Room', 'anchor': '#vault-categories'},
    {'label': 'Upload Evidence', 'url_name': 'legacy_safe:upload'},
    {'label': 'Create Evidence Pack', 'anchor': '#evidence-pack-builder'},
    {'label': 'Generate Investor Pack', 'anchor': '#evidence-pack-builder'},
    {'label': 'Generate MRV Pack', 'url_name': 'impact_mrv_layer:overview'},
    {'label': 'Request Expert Review', 'url_name': 'governance_expert_review_board:overview'},
    {'label': 'Share with Investor', 'url_name': 'leads:request_review'},
    {'label': 'Send to Teams', 'anchor': '#microsoft-integration'},
    {'label': 'Export to SharePoint', 'anchor': '#microsoft-integration'},
    {'label': 'Check Evidence Completeness', 'anchor': '#evidence-completeness-score'},
]


def overview(request):
    return render(request, 'data_room_evidence_vault/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_purpose': CORE_PURPOSE,
        'vault_categories': VAULT_CATEGORIES,
        'vault_workflow': VAULT_WORKFLOW,
        'dashboard_cards': DASHBOARD_CARDS,
        'document_table_fields': DOCUMENT_TABLE_FIELDS,
        'filters': FILTERS,
        'permission_levels': PERMISSION_LEVELS,
        'evidence_pack_types': EVIDENCE_PACK_TYPES,
        'evidence_pack_contents': EVIDENCE_PACK_CONTENTS,
        'example_cards': EXAMPLE_CARDS,
        'microsoft_integration_items': MICROSOFT_INTEGRATION_ITEMS,
        'api_integration_items': API_INTEGRATION_ITEMS,
        'api_examples': API_EXAMPLES,
        'webhook_events': WEBHOOK_EVENTS,
        'evidence_completeness_items': EVIDENCE_COMPLETENESS_ITEMS,
        'trust_audit_trail_items': TRUST_AUDIT_TRAIL_ITEMS,
        'amanah_integration_items': AMANAH_INTEGRATION_ITEMS,
        'amanah_morning_briefing_example': AMANAH_MORNING_BRIEFING_EXAMPLE,
        'no_harm_gate_evidence_items': NO_HARM_GATE_EVIDENCE_ITEMS,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })
