from django.shortcuts import render

# Connected EcoIQ modules — the Compliance Centre governs access across all of them
CONNECTED_MODULES = [
    {'name': 'Data Room & Evidence Vault', 'role': 'Enforces the permission levels documented in Data Room Permissions.'},
    {'name': 'API & Integration Layer', 'role': 'Enforces the API keys, scopes and rate limits documented in API Security.'},
    {'name': 'AI Agent Operations Console', 'role': 'Supplies the agent outputs governed by AI Agent Safety & Governance.'},
    {'name': 'Governance & Expert Review Board', 'role': 'Approves the human review decisions this centre tracks.'},
    {'name': 'Public Trust & Impact Portal', 'role': 'Enforces the Public Reporting Controls before publication.'},
    {'name': 'Command Centre', 'role': 'Surfaces security and compliance alerts across the project pipeline.'},
    {'name': 'Mobile / iPad Inspection Mode', 'role': 'Captures the photos and personal data governed by Privacy / PII Protection.'},
    {'name': 'Supplier & Funding Marketplace', 'role': 'Operates within the supplier and funder access scopes defined here.'},
    {'name': 'Institutional Finance Engine', 'role': 'Its financial models are protected under Data Room Permissions.'},
    {'name': 'Sales CRM & Partner Pipeline', 'role': 'Its contact and outreach data falls under Privacy / PII Protection.'},
    {'name': 'Customer Success & Renewal Engine', 'role': 'Its account data is governed by Role-Based Access Control.'},
    {'name': 'Product Analytics & KPI Engine', 'role': 'Its usage data is subject to the same privacy and retention rules.'},
    {'name': 'Microsoft Ecosystem Core Stack', 'role': 'Provides the identity, governance and monitoring building blocks this centre documents.'},
    {'name': 'SharePoint', 'role': 'Enforces evidence pack permissions.'},
    {'name': 'Teams', 'role': 'Delivers access review and approval notifications.'},
    {'name': 'Microsoft Fabric', 'role': 'Stores governed metadata and audit telemetry.'},
    {'name': 'Power BI', 'role': 'Renders security and compliance dashboards.'},
    {'name': 'Dynamics 365', 'role': 'Applies access scopes to customer and partner records.'},
    {'name': 'Presidio-style privacy tooling', 'role': 'Detects PII across documents, images and notes.'},
    {'name': 'Responsible AI tools', 'role': 'Support explainability and governance of AI agent outputs.'},
]

CORE_PURPOSE = 'Make EcoIQ secure, permissioned, auditable and compliant-by-design.'

SECURITY_DOMAINS = [
    {
        'number': 1,
        'title': 'Role-Based Access Control',
        'sections': [
            {
                'label': 'Roles',
                'items': [
                    'Admin', 'Project owner', 'Inspector', 'Engineer',
                    'Financial reviewer', 'Environmental reviewer', 'Safety reviewer',
                    'Maqasid/Mizan reviewer', 'Islamic finance reviewer', 'Supplier',
                    'Funder', 'Investor', 'Government reviewer', 'Community viewer',
                    'Auditor', 'API integration user',
                ],
            },
            {
                'label': 'Permissions should control',
                'items': [
                    'View project', 'Upload evidence', 'Edit Asset Passport',
                    'Run AI diagnosis', 'View financial model', 'View supplier quotes',
                    'View MRV evidence', 'Approve public summary', 'Export report',
                    'Share Data Room pack', 'Access API', 'View audit logs',
                ],
            },
        ],
        'note': '',
    },
    {
        'number': 2,
        'title': 'Data Room Permissions',
        'sections': [
            {
                'label': 'Permission levels',
                'items': [
                    'Private internal', 'Expert review only', 'Investor due diligence',
                    'Supplier RFQ pack', 'Government / akimat review',
                    'Sponsor / CSR pack', 'Public summary only',
                ],
            },
            {
                'label': 'Rules',
                'items': [
                    'Suppliers should not see investor-only documents',
                    'Investors should not see private personal data unless approved',
                    'Public viewers should only see approved summaries',
                    'Community data must be anonymised where needed',
                    'Sensitive industrial data must stay restricted',
                ],
            },
        ],
        'note': '',
    },
    {
        'number': 3,
        'title': 'Privacy / PII Protection',
        'sections': [
            {
                'label': 'Protect',
                'items': [
                    'Personal names', 'Phone numbers', 'Emails', 'Addresses',
                    'Exact household locations', 'Faces in photos', 'Voice notes',
                    'Signatures', 'Personal documents', 'Sensitive community data',
                ],
            },
            {
                'label': 'Capabilities',
                'items': [
                    'Detect PII in documents', 'Flag faces or personal details in images',
                    'Redact sensitive fields', 'Require consent before publication',
                    'Mark public-safe summaries', 'Track privacy risk',
                ],
            },
        ],
        'note': '',
    },
    {
        'number': 4,
        'title': 'Consent Management',
        'sections': [
            {
                'label': 'Track consent for',
                'items': [
                    'Household photos', 'Community stories', 'Sponsor visibility',
                    'Public impact stories', 'Before/after images', 'Location sharing',
                    'Data sharing with suppliers', 'Data sharing with investors',
                    'Public reporting',
                ],
            },
            {
                'label': 'Consent statuses',
                'items': [
                    'Consent required', 'Consent requested', 'Consent granted',
                    'Consent denied', 'Consent expired', 'Public sharing approved',
                    'Internal only',
                ],
            },
        ],
        'note': '',
    },
    {
        'number': 5,
        'title': 'Audit Logs',
        'sections': [
            {
                'label': 'Track',
                'items': [
                    'File uploaded', 'File viewed', 'File downloaded',
                    'Evidence shared', 'Data Room pack created', 'Data Room pack shared',
                    'Public summary approved', 'Supplier invited', 'Funder invited',
                    'AI task started', 'AI output generated', 'Expert review approved',
                    'MRV claim verified', 'Permission changed', 'API key created',
                    'API access used',
                ],
            },
            {
                'label': 'Every audit record should include',
                'items': [
                    'User', 'Role', 'Timestamp', 'Action', 'Project', 'Asset',
                    'Document/evidence', 'Previous value', 'New value',
                    'IP/session concept', 'Reason or note where relevant',
                ],
            },
        ],
        'note': '',
    },
    {
        'number': 6,
        'title': 'Data Retention & Deletion',
        'sections': [
            {
                'label': 'Track',
                'items': [
                    'Document age', 'Retention period', 'Expiry date',
                    'Deletion request', 'Archive status', 'Legal hold',
                    'Consent expiry', 'Public summary review date',
                ],
            },
            {
                'label': 'Rules',
                'items': [
                    'Expired consent should block public display',
                    'Outdated evidence should be flagged',
                    'Deletion requests should be tracked',
                    'Audit logs should preserve compliance history where legally appropriate',
                    'Sensitive documents should have retention policies',
                ],
            },
        ],
        'note': '',
    },
    {
        'number': 7,
        'title': 'API Security',
        'sections': [
            {
                'label': 'Controls',
                'items': [
                    'API keys', 'OAuth concept', 'Scoped tokens', 'Rate limiting',
                    'Webhook signing', 'Integration logs', 'Supplier/funder access scopes',
                    'Read-only vs write access', 'Revoked tokens',
                    'Suspicious activity alerts',
                ],
            },
        ],
        'note': '',
    },
    {
        'number': 8,
        'title': 'AI Agent Safety & Governance',
        'sections': [
            {
                'label': 'Track',
                'items': [
                    'Model used', 'Data sensitivity level', 'Evidence used',
                    'Prompt/instruction summary', 'Output status', 'Hallucination risk',
                    'Unsupported claim flag', 'Human approval required', 'PII detected',
                    'No Harm Gate status', 'Public reporting block',
                ],
            },
            {
                'label': 'Rules',
                'items': [
                    'High-impact decisions require human approval',
                    'Visual findings are hypotheses until verified',
                    'Public summaries require approval',
                    'Islamic finance/Maqasid wording requires review where relevant',
                    'Sensitive data should use approved enterprise routing',
                ],
            },
        ],
        'note': '',
    },
    {
        'number': 9,
        'title': 'Public Reporting Controls',
        'sections': [
            {
                'label': 'Before publishing, check',
                'items': [
                    'Public summary approved', 'MRV evidence available',
                    'Consent recorded', 'Sensitive data redacted',
                    'Sponsor name approved', 'Exact location safe to show',
                    'Maqasid/Mizan wording reviewed',
                    'Claims labelled estimated vs verified', 'Human approval recorded',
                ],
            },
        ],
        'note': '',
    },
    {
        'number': 10,
        'title': 'Compliance Readiness',
        'sections': [
            {
                'label': 'Show readiness for',
                'items': [
                    'Enterprise procurement', 'Investor due diligence',
                    'Government review', 'Supplier access governance', 'Privacy review',
                    'Audit review', 'Responsible AI review', 'Data room due diligence',
                    'Microsoft ecosystem governance concepts',
                ],
            },
        ],
        'note': 'Do not claim formal certification unless actually obtained. Phrase as '
                '"compliance-ready controls" or "designed to support".',
    },
]

DASHBOARD_CARDS = [
    'Active users', 'Roles configured', 'Restricted documents', 'Public-safe documents',
    'Consent records', 'Expired consents', 'PII alerts', 'Open privacy risks',
    'Audit log events', 'Data Room packs shared', 'API keys active',
    'Revoked access tokens', 'Public summaries awaiting approval',
    'No Harm Gate security alerts', 'AI outputs needing review',
    'Suspicious access alerts',
]

SECURITY_TABLE_FIELDS = [
    'Item', 'Project', 'Asset', 'Data type', 'Sensitivity level', 'Permission level',
    'Owner', 'Access status', 'Consent status', 'PII risk', 'Retention status',
    'Last accessed', 'Last reviewed', 'Next action',
]

SENSITIVITY_LEVELS = ['Public', 'Internal', 'Confidential', 'Restricted', 'Highly sensitive']

DATA_TYPES = [
    'Asset evidence', 'Personal data', 'Financial model', 'Supplier quote',
    'Investor memo', 'MRV proof', 'Expert review', 'Legal/compliance document',
    'AI agent log', 'Public summary', 'API record',
]

EXAMPLE_SCENARIOS = [
    {
        'project': 'Village Clean Heating Pilot',
        'risk': 'Household photos and location data may contain personal information.',
        'controls': [
            'Consent required', 'Exact address hidden', 'Public summary only',
            'Before/after photos approved before publication',
            'Sponsor name shown only if approved',
        ],
        'status': 'Public reporting blocked until consent is recorded.',
    },
    {
        'project': 'Factory Energy Efficiency Memo',
        'risk': 'Financial model and production data are commercially sensitive.',
        'controls': [
            'Investor due diligence permission only',
            'Supplier cannot view financial model',
            'Public portal shows only aggregated impact', 'Audit log tracks access',
        ],
        'status': 'Restricted.',
    },
    {
        'project': 'Supplier RFQ Pack',
        'risk': 'Supplier needs technical specs but should not see investor documents.',
        'controls': [
            'Supplier pack permission level', 'Quote upload only',
            'No access to finance memo', 'No public sharing',
        ],
        'status': 'Ready for approved supplier outreach.',
    },
    {
        'project': 'AI Agent Photo Diagnosis',
        'risk': 'AI visual finding may be interpreted as confirmed engineering fact.',
        'controls': [
            'Label as AI hypothesis', 'Requires engineer verification',
            'Cannot be used in public report until reviewed',
        ],
        'status': 'Needs verification.',
    },
]

MICROSOFT_SECURITY_ITEMS = [
    'Microsoft Entra ID concept for identity and access',
    'Microsoft Purview-style data governance concept',
    'SharePoint permissions for evidence packs', 'Teams approvals for human review',
    'Microsoft Fabric for governed metadata', 'Power BI for security dashboards',
    'Power Automate for access review workflows', 'Presidio-style PII detection',
    'Responsible AI Toolbox for explainability and governance',
    'Azure Monitor / Application Insights concept for logs',
    'Key Vault concept for secrets and API keys',
]
MICROSOFT_SECURITY_WORDING_NOTE = (
    'Use careful wording: "designed to integrate with" or "can use", not '
    '"certified by Microsoft".'
)

AMANAH_COMPLIANCE_ITEMS = [
    'Detect expired consents', 'Flag PII in new documents',
    'Identify public summaries missing approval',
    'Detect Data Room packs shared too widely', 'Find AI outputs needing human review',
    'Flag stale evidence', 'Prepare access review list',
    'Generate compliance morning briefing',
]
AMANAH_MORNING_BRIEFING_EXAMPLE = (
    'Overnight, EcoIQ found 3 documents with possible PII, 2 public summaries missing '
    'consent, 1 supplier pack shared too broadly and 4 AI outputs requiring human review.'
)

NO_HARM_GATE_ITEMS = [
    'Is the user authorised?',
    'Is the document permissioned correctly?',
    'Does the file contain personal data?',
    'Is consent recorded?',
    'Is the evidence public-safe?',
    'Are exact locations safe to show?',
    'Is supplier/funder access limited?',
    'Is the AI output approved?',
    'Is the impact claim MRV-backed?',
    'Is the audit trail complete?',
]

SAFETY_PRINCIPLES = [
    'EcoIQ security controls are platform governance features and do not replace '
    'formal legal, compliance, cybersecurity or data protection review.',
    'Do not claim certification unless obtained.',
    'Sensitive data must be permissioned, audited and protected.',
    'Public reporting requires consent, MRV evidence and human approval.',
    'AI outputs require review before high-impact use.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
]

CTA_BUTTONS = [
    {'label': 'Open Compliance Centre', 'anchor': '#security-domains'},
    {'label': 'Review Access Permissions', 'anchor': '#domain-1'},
    {'label': 'Scan for PII', 'anchor': '#domain-3'},
    {'label': 'Create Consent Record', 'anchor': '#domain-4'},
    {'label': 'View Audit Logs', 'anchor': '#domain-5'},
    {'label': 'Review Public Summary', 'anchor': '#domain-9'},
    {'label': 'Revoke Access', 'anchor': '#domain-7'},
    {'label': 'Export Compliance Report', 'anchor': '#dashboard-cards'},
    {'label': 'Send Review to Teams', 'anchor': '#microsoft-security-integration'},
    {'label': 'Check Data Room Permissions', 'anchor': '#domain-2'},
]


def overview(request):
    return render(request, 'security_privacy_compliance_centre/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_purpose': CORE_PURPOSE,
        'security_domains': SECURITY_DOMAINS,
        'dashboard_cards': DASHBOARD_CARDS,
        'security_table_fields': SECURITY_TABLE_FIELDS,
        'sensitivity_levels': SENSITIVITY_LEVELS,
        'data_types': DATA_TYPES,
        'example_scenarios': EXAMPLE_SCENARIOS,
        'microsoft_security_items': MICROSOFT_SECURITY_ITEMS,
        'microsoft_security_wording_note': MICROSOFT_SECURITY_WORDING_NOTE,
        'amanah_compliance_items': AMANAH_COMPLIANCE_ITEMS,
        'amanah_morning_briefing_example': AMANAH_MORNING_BRIEFING_EXAMPLE,
        'no_harm_gate_items': NO_HARM_GATE_ITEMS,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })
