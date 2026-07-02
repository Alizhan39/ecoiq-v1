from django.shortcuts import render

# Connected EcoIQ modules — the Reliability Centre keeps every one of them operable in production
CONNECTED_MODULES = [
    {'name': 'Security, Privacy & Compliance Centre', 'role': 'Supplies the permission and audit controls this centre monitors during incidents.'},
    {'name': 'AI Agent Operations Console', 'role': 'Supplies agent task health tracked in Error Monitoring.'},
    {'name': 'Product Analytics & KPI Engine', 'role': 'Consumes reliability metrics as part of platform-wide KPIs.'},
    {'name': 'API & Integration Layer', 'role': 'Its endpoints are tracked in Health Checks.'},
    {'name': 'Data Room & Evidence Vault', 'role': 'Its backup and access status is tracked in Backup & Restore.'},
    {'name': 'Command Centre', 'role': 'Surfaces operational alerts across the project pipeline.'},
    {'name': 'Microsoft Ecosystem Core Stack', 'role': 'Provides the agent, data and monitoring building blocks this centre documents.'},
    {'name': 'Customer Success & Renewal Engine', 'role': 'Its account data availability depends on the reliability this centre tracks.'},
    {'name': 'Revenue & Pricing Engine', 'role': 'Its billing-relevant uptime is tracked in Deployment Monitoring.'},
    {'name': 'Public Trust & Impact Portal', 'role': 'Its public route health is tracked in Route Verification.'},
    {'name': 'Teams', 'role': 'Delivers incident alerts and escalation notifications.'},
    {'name': 'Power BI', 'role': 'Renders reliability and uptime dashboards.'},
    {'name': 'Microsoft Fabric', 'role': 'Stores operational logs and telemetry.'},
    {'name': 'Azure Monitor / Application Insights concept', 'role': 'Supplies the telemetry model this centre is designed to integrate with.'},
    {'name': 'GitHub Actions / CI concept', 'role': 'Supplies the CI/CD model behind Release History and CI/Test Quality.'},
    {'name': 'Render / cloud deployment concept', 'role': 'Supplies the deployment model behind Deployment Monitoring.'},
]

CORE_PURPOSE = 'Make EcoIQ production-ready, observable, recoverable and enterprise-operable.'

RELIABILITY_DOMAINS = [
    {
        'number': 1,
        'title': 'Deployment Monitoring',
        'sections': [
            {
                'label': 'Track',
                'items': [
                    'Current environment', 'Current release version',
                    'Current branch / commit', 'Deployment status', 'Deployment time',
                    'Build status', 'Migration status', 'Static files status',
                    'Health check status', 'Rollback option',
                ],
            },
            {
                'label': 'Statuses',
                'items': [
                    'Healthy', 'Deploying', 'Failed', 'Rollback recommended',
                    'Needs review', 'Maintenance mode',
                ],
            },
        ],
        'note': '',
    },
    {
        'number': 2,
        'title': 'Release History',
        'sections': [
            {
                'label': 'Track',
                'items': [
                    'Release version', 'PR number', 'Module added', 'Commit hash',
                    'Deployment date', 'Tests run', 'Routes verified', 'Known issues',
                    'Rollback notes', 'Owner',
                ],
            },
        ],
        'note': '',
    },
    {
        'number': 3,
        'title': 'Health Checks',
        'sections': [
            {
                'label': 'Check',
                'items': [
                    'Homepage route', 'Platform route', 'Module routes',
                    'Admin route if relevant', 'Database connection', 'Static assets',
                    'Media storage', 'API endpoints', 'Background tasks', 'Agent queue',
                    'Email / notification service', 'Public portal', 'Data Room access',
                ],
            },
        ],
        'note': '',
    },
    {
        'number': 4,
        'title': 'Database Health',
        'sections': [
            {
                'label': 'Track',
                'items': [
                    'Database connectivity', 'Migration status', 'Table count',
                    'Slow query warnings', 'Storage usage', 'Backup status',
                    'Replication concept where relevant', 'Failed migration alerts',
                    'Data integrity checks',
                ],
            },
        ],
        'note': '',
    },
    {
        'number': 5,
        'title': 'Backup & Restore',
        'sections': [
            {
                'label': 'Track',
                'items': [
                    'Last backup time', 'Backup status', 'Backup location',
                    'Restore test status', 'Retention policy', 'Critical data covered',
                    'Data Room backup', 'Database backup', 'Media/evidence backup',
                    'Configuration backup',
                ],
            },
        ],
        'note': 'Do not claim backups are implemented unless they are actually '
                'configured. Phrase as "designed to monitor" or "backup readiness".',
    },
    {
        'number': 6,
        'title': 'Error Monitoring',
        'sections': [
            {
                'label': 'Track',
                'items': [
                    'Server errors', '404 route errors', '500 errors',
                    'Template rendering errors', 'Raw Django template tag alerts',
                    'API errors', 'Agent failures', 'Document parsing failures',
                    'File upload failures', 'Permission errors',
                    'Public reporting errors',
                ],
            },
        ],
        'note': '',
    },
    {
        'number': 7,
        'title': 'Incident Response',
        'sections': [
            {
                'label': 'Incident stages',
                'items': [
                    'Detected', 'Triaged', 'Owner assigned', 'User impact assessed',
                    'Mitigation started', 'Fixed', 'Postmortem required', 'Resolved',
                ],
            },
            {
                'label': 'Incident fields',
                'items': [
                    'Incident ID', 'Severity', 'Affected module', 'Affected users',
                    'Start time', 'Detection source', 'Owner', 'Mitigation',
                    'Resolution', 'Postmortem notes',
                ],
            },
        ],
        'note': '',
    },
    {
        'number': 8,
        'title': 'Rollback Planning',
        'sections': [
            {
                'label': 'Track',
                'items': [
                    'Last stable release', 'Rollback commit', 'Migration rollback risk',
                    'Data loss risk', 'Feature flag status', 'Affected modules',
                    'Approval required', 'Rollback command checklist',
                ],
            },
        ],
        'note': '',
    },
    {
        'number': 9,
        'title': 'Environment Readiness',
        'sections': [
            {
                'label': 'Environments',
                'items': ['Development', 'Staging', 'Production'],
            },
            {
                'label': 'For each environment show',
                'items': [
                    'App status', 'Database status', 'Environment variables',
                    'Secrets configured', 'Storage configured', 'Email configured',
                    'Monitoring configured', 'Debug mode status', 'Allowed hosts',
                    'HTTPS status', 'Static/media status',
                ],
            },
        ],
        'note': '',
    },
    {
        'number': 10,
        'title': 'CI / Test Quality',
        'sections': [
            {
                'label': 'Track',
                'items': [
                    'Module test pass rate', 'Full suite status',
                    'Known unrelated failures', 'Skipped tests', 'Coverage concept',
                    'Linting concept', 'Route verification',
                    'Raw template syntax check', 'Browser verification',
                    'Regression tests',
                ],
            },
        ],
        'note': '',
    },
]

DASHBOARD_CARDS = [
    'Current release', 'Deployment status', 'Uptime status', 'Routes healthy',
    'Database status', 'Last backup', 'Open incidents', 'Failed tasks', 'API errors',
    'Agent errors', '500 errors', 'Raw template tag alerts', 'Public portal status',
    'Data Room status', 'Average response time concept', 'Rollback readiness',
    'Tests passing',
]

ROUTE_TABLE_FIELDS = [
    'Route', 'Module', 'HTTP status', 'Raw template syntax check',
    'Expected content check', 'Last verified', 'Owner', 'Status',
]

ROUTES_TRACKED = [
    '/', '/platform/', '/deployment-devops-reliability-centre/',
    '/security-privacy-compliance-centre/', '/ai-agent-operations-console/',
    '/product-analytics-kpi-engine/', '/customer-success-renewal-engine/',
    '/sales-crm-partner-pipeline/', '/public-trust-impact-portal/',
    '/revenue-pricing-engine/', '/executive-briefing-board-pack-generator/',
    '/portfolio-country-transition-atlas/', '/data-room-evidence-vault/',
    '/api-integration-layer/', '/governance-expert-review-board/',
    '/command-centre/', '/mobile-inspection-mode/', '/institutional-finance-engine/',
    '/supplier-funding-marketplace/', '/industrial-playbook-library/',
    '/impact-mrv-layer/', '/microsoft-ecosystem-core-stack/', '/legacy-safe/',
]

EXAMPLE_INCIDENTS = [
    {
        'incident': 'Raw Django template tags visible in preview',
        'severity': 'Medium',
        'cause': 'Preview opened raw platform.html instead of Django route /platform/.',
        'resolution': 'Verify real route and add a regression test checking for raw '
                       'Django template syntax in the rendered response.',
    },
    {
        'incident': 'MRV report generation failed',
        'severity': 'High',
        'cause': 'Missing after-data evidence.',
        'resolution': 'Downgrade claim to "Needs verification" and request missing evidence.',
    },
    {
        'incident': 'Data Room access too broad',
        'severity': 'High',
        'cause': 'Supplier pack shared with investor-only document.',
        'resolution': 'Revoke access, update permission level and log audit event.',
    },
    {
        'incident': 'Agent output unsupported claim',
        'severity': 'Medium/High',
        'cause': 'Finance agent generated savings claim without verified evidence.',
        'resolution': 'Flag No Harm Gate, require human review and evidence trace.',
    },
]

AMANAH_ITEMS = [
    'Check route health', 'Detect failed agent tasks', 'Identify stale evidence jobs',
    'Flag public pages with missing approval', 'Check backup freshness',
    'Prepare incident summary', 'Detect modules with repeated errors',
    'Prepare morning reliability briefing',
]
AMANAH_MORNING_BRIEFING_EXAMPLE = (
    'All 25 routes are healthy, 1 agent task failed due to missing evidence, no raw '
    'template tags detected, last database backup was 8 hours ago, and 2 Data Room '
    'documents need permission review.'
)

MICROSOFT_AZURE_ITEMS = [
    'Azure Monitor / Application Insights concept for telemetry',
    'Microsoft Fabric for operational logs', 'Power BI for reliability dashboards',
    'Teams for incident alerts', 'Power Automate for escalation workflows',
    'GitHub Actions concept for CI/CD', 'Azure Key Vault concept for secrets',
    'Azure Blob Storage for evidence backup', 'Microsoft Entra concept for identity',
]
MICROSOFT_AZURE_WORDING_NOTE = (
    'Use careful wording: "designed to integrate with" or "can use", not '
    '"currently certified".'
)

NO_HARM_GATE_ITEMS = [
    'Are tests passing?',
    'Are routes verified?',
    'Are migrations safe?',
    'Is rollback possible?',
    'Are backups fresh?',
    'Are sensitive documents protected?',
    'Are public claims approved?',
    'Are AI agent outputs still marked correctly?',
    'Are incidents resolved or documented?',
    'Is user impact understood?',
    'Is human approval required?',
]

SAFETY_PRINCIPLES = [
    'DevOps and reliability dashboards are operational support tools and do not '
    'replace professional cybersecurity, infrastructure or compliance review.',
    'Do not claim backup, certification, monitoring or enterprise-grade guarantees '
    'unless implemented and verified.',
    'High-impact production changes require testing, rollback planning and human approval.',
    'Sensitive data and evidence must remain permissioned during incidents and debugging.',
    'Public impact claims must remain MRV-backed and approved after releases.',
]

CTA_BUTTONS = [
    {'label': 'Open Reliability Centre', 'anchor': '#reliability-domains'},
    {'label': 'Check Route Health', 'anchor': '#route-verification-table'},
    {'label': 'View Deployment Status', 'anchor': '#domain-1'},
    {'label': 'Review Release History', 'anchor': '#domain-2'},
    {'label': 'Check Database Health', 'anchor': '#domain-4'},
    {'label': 'Verify Backups', 'anchor': '#domain-5'},
    {'label': 'Open Incident Log', 'anchor': '#domain-7'},
    {'label': 'Run Route Verification', 'anchor': '#route-verification-table'},
    {'label': 'Prepare Rollback Plan', 'anchor': '#domain-8'},
    {'label': 'Send Incident Alert to Teams', 'anchor': '#microsoft-azure-integration'},
]


def overview(request):
    return render(request, 'deployment_devops_reliability_centre/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_purpose': CORE_PURPOSE,
        'reliability_domains': RELIABILITY_DOMAINS,
        'dashboard_cards': DASHBOARD_CARDS,
        'route_table_fields': ROUTE_TABLE_FIELDS,
        'routes_tracked': ROUTES_TRACKED,
        'example_incidents': EXAMPLE_INCIDENTS,
        'amanah_items': AMANAH_ITEMS,
        'amanah_morning_briefing_example': AMANAH_MORNING_BRIEFING_EXAMPLE,
        'microsoft_azure_items': MICROSOFT_AZURE_ITEMS,
        'microsoft_azure_wording_note': MICROSOFT_AZURE_WORDING_NOTE,
        'no_harm_gate_items': NO_HARM_GATE_ITEMS,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })
