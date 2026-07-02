from django.shortcuts import render

# Connected EcoIQ modules — the API layer is the connective tissue linking all of them externally
CONNECTED_MODULES = [
    {'name': 'Microsoft Ecosystem Core Stack', 'role': 'Provides the agent, data and dashboard building blocks the API layer exposes.'},
    {'name': 'Command Centre', 'role': 'Exposes pipeline and project status through the Command Centre API.'},
    {'name': 'Governance & Expert Review Board', 'role': 'Exposes review submission and approval endpoints.'},
    {'name': 'Mobile / iPad Inspection Mode', 'role': 'Submits captured evidence through the Inspection API.'},
    {'name': 'Asset Passport', 'role': 'Exposes asset records through the Asset Passport API.'},
    {'name': 'Impact MRV Layer', 'role': 'Exposes baseline, after-data and verification endpoints.'},
    {'name': 'Industrial Playbook Library', 'role': 'Exposes playbook matching through the Playbook API.'},
    {'name': 'Supplier & Funding Marketplace', 'role': 'Exposes supplier and funding matching endpoints.'},
    {'name': 'Institutional Finance Engine', 'role': 'Exposes finance model and memo endpoints.'},
    {'name': 'Amanah Autopilot', 'role': 'Triggers webhook events from its overnight scans.'},
    {'name': 'Omnimodal Evidence Panel', 'role': 'Supplies the evidence attached to API payloads.'},
    {'name': 'Digital Twins', 'role': 'Synced via Azure Digital Twins integration.'},
    {'name': 'IoT sensors', 'role': 'Feed live meter and sensor data through the sensor integrations.'},
    {'name': 'Power BI dashboards', 'role': 'Consume EcoIQ data through the reporting export integrations.'},
    {'name': 'Teams approvals', 'role': 'Receive approval tasks routed by the integration workflow.'},
    {'name': 'SharePoint evidence packs', 'role': 'Store evidence packs exported through the API layer.'},
    {'name': 'Dynamics 365 pipeline tracking', 'role': 'Tracks supplier and funder pipeline synced from EcoIQ.'},
]

CORE_PURPOSE = 'Make EcoIQ integration-ready for enterprise, government, investor and industrial workflows.'

INTEGRATION_CATEGORIES = [
    {
        'number': 1,
        'title': 'Microsoft Integrations',
        'connect_to': [
            'Microsoft Teams', 'Power BI', 'SharePoint', 'Microsoft Fabric',
            'Azure Digital Twins', 'Azure IoT', 'Azure Blob Storage',
            'Azure AI / Agent Framework', 'Power Automate', 'Power Apps',
            'Dynamics 365', 'Microsoft Graph',
        ],
        'use_cases': [
            'Send project approvals to Teams', 'Export MRV dashboards to Power BI',
            'Store evidence packs in SharePoint', 'Sync asset data with Azure Digital Twins',
            'Ingest sensor data through Azure IoT',
            'Manage funder/supplier pipelines in Dynamics 365',
            'Trigger approval flows through Power Automate',
            'Build field forms with Power Apps',
        ],
    },
    {
        'number': 2,
        'title': 'Sensor & IoT Integrations',
        'connect_to': [
            'Smart meters', 'Heat meters', 'Electricity meters', 'Water meters',
            'Temperature sensors', 'Pressure sensors', 'Vibration sensors',
            'Air quality sensors', 'Compressor monitoring', 'Boiler controls',
            'Solar/battery monitoring', 'Factory production sensors',
        ],
        'use_cases': [
            'Collect baseline data', 'Detect abnormal energy use',
            'Monitor before/after impact', 'Feed Digital Twins', 'Trigger MRV verification',
            'Alert Command Centre', 'Support predictive maintenance',
        ],
    },
    {
        'number': 3,
        'title': 'Supplier Integrations',
        'connect_to': [
            'Supplier quote systems', 'Installer portals', 'Equipment catalogues',
            'Maintenance providers', 'Service ticket systems', 'Warranty databases',
            'Procurement platforms',
        ],
        'use_cases': [
            'Request supplier quotes', 'Compare equipment options',
            'Track installation progress', 'Upload invoices', 'Verify warranty',
            'Update implementation status', 'Feed supplier performance score',
        ],
    },
    {
        'number': 4,
        'title': 'Funding & Investor Integrations',
        'connect_to': [
            'Investor CRM', 'Grant application portals', 'CSR sponsor databases',
            'Islamic finance providers', 'Development bank pipelines',
            'Municipal finance systems', 'Carbon/climate finance tools where appropriate',
        ],
        'use_cases': [
            'Export finance memo', 'Submit funding brief', 'Track application status',
            'Sync investor pipeline', 'Attach MRV evidence', 'Update funding readiness',
            'Monitor funding gap',
        ],
    },
    {
        'number': 5,
        'title': 'Government / Akimat Integrations',
        'connect_to': [
            'Municipal asset registries', 'Public building databases',
            'Boiler house registries', 'Regional emissions datasets',
            'Procurement systems', 'Inspection systems', 'Public reporting dashboards',
        ],
        'use_cases': [
            'Identify priority assets', 'Track public sector modernisation',
            'Report verified impact', 'Manage co-finance programmes',
            'Monitor vulnerable communities', 'Support clean heating transitions',
        ],
    },
    {
        'number': 6,
        'title': 'Reporting & Data Export Integrations',
        'connect_to': [
            'CSV', 'Excel', 'PDF', 'JSON', 'API endpoint', 'Power BI dataset',
            'SharePoint report', 'Investor memo', 'MRV evidence pack', 'Government report',
        ],
        'use_cases': [
            'Board reporting', 'Investor due diligence', 'Grant application',
            'CSR reporting', 'Public impact dashboard', 'Expert review evidence pack',
        ],
    },
]

API_ENDPOINT_GROUPS = [
    {
        'title': 'Asset Passport API',
        'endpoints': [
            'GET /api/assets/', 'GET /api/assets/{id}/', 'POST /api/assets/',
            'PATCH /api/assets/{id}/',
        ],
    },
    {
        'title': 'Inspection API',
        'endpoints': [
            'POST /api/inspections/', 'GET /api/inspections/{id}/',
            'POST /api/inspections/{id}/evidence/',
        ],
    },
    {
        'title': 'Playbook API',
        'endpoints': ['GET /api/playbooks/', 'POST /api/playbooks/match/'],
    },
    {
        'title': 'Finance API',
        'endpoints': ['POST /api/finance/model/', 'GET /api/finance/memos/{id}/'],
    },
    {
        'title': 'Marketplace API',
        'endpoints': [
            'POST /api/suppliers/match/', 'POST /api/funding/match/',
            'GET /api/suppliers/{id}/', 'GET /api/funders/{id}/',
        ],
    },
    {
        'title': 'MRV API',
        'endpoints': [
            'POST /api/mrv/baseline/', 'POST /api/mrv/after-data/',
            'GET /api/mrv/report/{id}/',
        ],
    },
    {
        'title': 'Governance API',
        'endpoints': [
            'POST /api/reviews/submit/', 'PATCH /api/reviews/{id}/approve/',
            'PATCH /api/reviews/{id}/request-evidence/',
        ],
    },
    {
        'title': 'Command Centre API',
        'endpoints': [
            'GET /api/projects/pipeline/', 'GET /api/projects/{id}/status/',
            'PATCH /api/projects/{id}/stage/',
        ],
    },
]

WEBHOOK_EVENTS = [
    'asset.created', 'inspection.completed', 'evidence.uploaded', 'playbook.matched',
    'finance.memo_ready', 'supplier.shortlisted', 'funding.route_matched',
    'review.requested', 'review.approved', 'implementation.started',
    'mrv.baseline_completed', 'mrv.impact_verified', 'no_harm_gate.alert',
]

INTEGRATION_WORKFLOW = [
    'Field inspection captured', 'Asset Passport API updates asset',
    'Playbook matching API selects pathway', 'Finance API prepares model',
    'Marketplace API matches suppliers/funders', 'Governance API requests expert approval',
    'Teams / Power Automate sends approval task', 'Supplier quote uploaded',
    'Implementation status updated', 'IoT sensor data feeds MRV',
    'Power BI dashboard updates verified impact',
]

SECURITY_ITEMS = [
    'Role-based access control', 'API keys / OAuth where appropriate', 'Audit logs',
    'Evidence versioning', 'Human approval records', 'Private data protection',
    'PII detection', 'Supplier/funder access limits', 'Read/write permissions by role',
    'Secure document storage', 'Rate limiting', 'Integration logs',
]

USER_ROLES_API = [
    'Admin', 'Project owner', 'Inspector', 'Engineer', 'Finance reviewer', 'Supplier',
    'Funder', 'Government reviewer', 'Community viewer', 'Auditor',
    'API integration user',
]

DATA_GOVERNANCE_RULES = [
    'No automatic supplier or funder outreach without human approval.',
    'Sensitive industrial data must be protected.',
    'Personal data in photos, voice notes or documents must be detected and handled carefully.',
    'Evidence should keep timestamp, source and version.',
    'High-impact decisions require documented approval.',
    'MRV claims require before/after evidence.',
    'Islamic finance data requires qualified review where relevant.',
]

EXAMPLE_CARDS = [
    {
        'integration': 'Boiler House #3 Modernisation',
        'connected_systems': [
            'Mobile inspection app captures photos', 'Azure Blob stores evidence',
            'Asset Passport API updates asset', 'Power BI displays risk and savings',
            'Teams sends expert review task', 'Supplier API receives RFQ after approval',
            'SharePoint stores evidence pack', 'MRV API tracks before/after fuel data',
        ],
        'result': 'One project moves from field evidence to expert review, supplier '
                   'outreach, finance memo and verified impact without losing audit trail.',
    },
    {
        'integration': 'Factory Energy Efficiency Dashboard',
        'connected_systems': [
            'Smart meters', 'Production data', 'Power BI',
            'Institutional Finance Engine', 'Command Centre', 'MRV Layer',
        ],
        'result': 'EcoIQ compares energy per unit before and after motor upgrades and '
                   'reports verified savings.',
    },
]

MICROSOFT_BLUEPRINT_FLOW = [
    'Mobile Inspection / Power Apps', 'Azure Blob Storage', 'Microsoft Fabric',
    'Azure Digital Twins', 'Azure AI Agent Framework', 'EcoIQ APIs', 'Power BI Dashboard',
    'Teams Approval', 'SharePoint Evidence Pack', 'Dynamics 365 Supplier/Funder Pipeline',
    'Impact MRV Report',
]

DEVELOPER_EXPERIENCE_ITEMS = [
    'API documentation', 'Sample payloads', 'Webhook documentation', 'Integration sandbox',
    'Test API keys', 'Data schema reference', 'Export templates',
    'Power BI connector concept', 'Microsoft Teams approval template',
    'SharePoint evidence pack template',
]

SAFETY_PRINCIPLES = [
    'API integrations are decision-support infrastructure, not automatic approval systems.',
    'High-impact industrial, financial, environmental, safety and Islamic finance decisions '
    'require human review.',
    'EcoIQ should not automatically contact suppliers, funders or communities without '
    'documented approval.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
    'Sensitive data must be protected through permissions, audit logs and privacy controls.',
    'Unsupported impact claims must remain marked as "Needs verification".',
]

CTA_BUTTONS = [
    {'label': 'View API Docs', 'anchor': '#api-endpoints'},
    {'label': 'Connect Microsoft Teams', 'url_name': 'microsoft_core_stack:overview'},
    {'label': 'Export to Power BI', 'anchor': '#integration-categories'},
    {'label': 'Sync Asset Passport', 'url_name': 'asset_passport:overview'},
    {'label': 'Create Webhook', 'anchor': '#webhook-events'},
    {'label': 'Connect IoT Sensor', 'anchor': '#integration-categories'},
    {'label': 'Generate Evidence Pack', 'anchor': '#developer-experience'},
    {'label': 'Send Approval to Teams', 'url_name': 'governance_expert_review_board:overview'},
    {'label': 'Export MRV Report', 'url_name': 'impact_mrv_layer:overview'},
]


def overview(request):
    return render(request, 'api_integration_layer/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_purpose': CORE_PURPOSE,
        'integration_categories': INTEGRATION_CATEGORIES,
        'api_endpoint_groups': API_ENDPOINT_GROUPS,
        'webhook_events': WEBHOOK_EVENTS,
        'integration_workflow': INTEGRATION_WORKFLOW,
        'security_items': SECURITY_ITEMS,
        'user_roles_api': USER_ROLES_API,
        'data_governance_rules': DATA_GOVERNANCE_RULES,
        'example_cards': EXAMPLE_CARDS,
        'microsoft_blueprint_flow': MICROSOFT_BLUEPRINT_FLOW,
        'developer_experience_items': DEVELOPER_EXPERIENCE_ITEMS,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })
