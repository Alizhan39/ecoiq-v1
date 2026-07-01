"""
LegacySafe AI — Microsoft Ecosystem Readiness.

A curated, read-only roadmap data structure: how EcoIQ LegacySafe AI could fit into a
Microsoft-style enterprise AI architecture for industrial modernisation. Nothing here is
installed, called, or wired into the running app beyond what already exists in legacy_safe
(Django, NetworkX, permission checks, audit logs, seed data). No Azure/Microsoft service is
called; no API keys are used.
"""

TOP_DISCLAIMER = (
    'This page is a roadmap and architecture alignment layer. The current hackathon MVP does '
    'not claim full Microsoft, Azure, Copilot, Fabric, Digital Twins, or IoT integration. These '
    'are roadmap-ready enterprise integration options.'
)

MICROSOFT_TOOLS_DISCLAIMER = (
    'These Microsoft open-source tools are roadmap-ready unless explicitly marked as '
    'implemented. EcoIQ does not claim they are fully integrated in the current hackathon MVP.'
)

# ── Section 1: Microsoft-style AI project architecture ──────────────────────────────────────

ARCHITECTURE_DIAGRAM = (
    'Industrial user → Permission-aware EcoIQ agent → Allowed industrial data only '
    '→ Selected model provider → Modernisation plan → Approved action + audit log'
)

ARCHITECTURE_MAPPING = {
    'User': [
        'Energy manager', 'Factory operator', 'Engineer', 'Government officer', 'Investor',
        'ESG analyst', 'Maintenance team', 'Procurement team', 'Community/stakeholder team',
    ],
    'Data': [
        'Legacy documents', 'Maintenance logs', 'Sensor data', 'Smart meter data',
        'Equipment records', 'Invoices', 'ESG reports', 'Grid data', 'ERP data',
        'CRM/ticket data', 'Procurement files', 'Risk registers', 'Community impact records',
    ],
    'Agent': [
        'Permission Guard Agent', 'Legacy Scanner Agent', 'Energy Modernisation Agent',
        'Equipment Upgrade Agent', 'Grid Optimisation Agent', 'Predictive Maintenance Agent',
        'Procurement Agent', 'Finance Agent', 'Justice & Maqasid Agent',
        'Audit & Compliance Agent',
    ],
    'Model': [
        'Understands technical context', 'Reasons over documents and data',
        'Compares options', 'Explains risks', 'Proposes actions',
        'Generates structured plans', 'Only receives permission-filtered context',
    ],
    'Action': [
        'Modernisation recommendation', 'Maintenance task', 'Procurement plan',
        'Investment case', 'ESG evidence report', 'Risk escalation', 'Workflow update',
        'Human approval request', 'Audit log', 'Dashboard update',
    ],
}

# ── Section 2: Microsoft ecosystem mapping ───────────────────────────────────────────────────

ECOSYSTEM_MAPPING = [
    {
        'layer': 'Azure AI / Azure OpenAI-ready',
        'use_case': 'Model-provider-ready enterprise AI layer.',
        'why': 'Allows enterprise customers to use approved Microsoft AI infrastructure.',
        'status': 'Roadmap-ready',
    },
    {
        'layer': 'Copilot-style workflows',
        'use_case': 'Energy managers and engineers can ask questions, generate reports, and trigger approved workflows.',
        'why': 'Makes AI usable inside daily enterprise work.',
        'status': 'Roadmap-ready',
    },
    {
        'layer': 'Microsoft Fabric',
        'use_case': 'Unify industrial data, ESG data, sensor data, finance data, maintenance data and reporting.',
        'why': 'Industrial modernisation depends on fragmented data becoming usable.',
        'status': 'Roadmap-ready',
    },
    {
        'layer': 'Azure Digital Twins',
        'use_case': 'Represent factories, power plants, heating systems, grids, assets and equipment as digital twins.',
        'why': 'EcoIQ can reason over real asset relationships and dependencies.',
        'status': 'Roadmap-ready',
    },
    {
        'layer': 'Azure IoT / IoT Hub',
        'use_case': 'Ingest sensor data, smart meter data, equipment status and operational telemetry.',
        'why': 'Modernisation needs live operational signals, not only documents.',
        'status': 'Roadmap-ready',
    },
    {
        'layer': 'Azure Data Lake / OneLake-ready data layer',
        'use_case': 'Store large-scale industrial documents, logs, sensor history and ESG evidence.',
        'why': 'Creates a scalable evidence foundation.',
        'status': 'Roadmap-ready',
    },
    {
        'layer': 'Microsoft Defender / security stack',
        'use_case': 'Protect enterprise data, monitor risks, secure agent workflows.',
        'why': 'AI agents must not expose sensitive infrastructure or financial data.',
        'status': 'Roadmap-ready',
    },
    {
        'layer': 'Microsoft Entra ID',
        'use_case': 'Enterprise identity, roles, groups and access control.',
        'why': "Fits EcoIQ's permission-aware retrieval model.",
        'status': 'Roadmap-ready',
    },
    {
        'layer': 'Power BI',
        'use_case': 'Industrial transition dashboards, ESG reporting, energy efficiency dashboards, investment views.',
        'why': 'Makes EcoIQ outputs usable for executives and public-sector teams.',
        'status': 'Roadmap-ready',
    },
    {
        'layer': 'Teams / Microsoft 365',
        'use_case': 'Deliver agent recommendations, approval requests, audit summaries and reports into existing workflows.',
        'why': 'Modernisation must fit where teams already work.',
        'status': 'Roadmap-ready',
    },
    {
        'layer': 'SharePoint / OneDrive',
        'use_case': 'Ingest enterprise documents, policies, engineering files and board memos.',
        'why': 'Most industrial knowledge is trapped in documents.',
        'status': 'Roadmap-ready',
    },
    {
        'layer': 'GitHub / GitHub Copilot',
        'use_case': 'Repository-aware modernisation, code scanning, change proposals, developer workflows.',
        'why': 'Legacy software and infrastructure code need controlled AI assistance.',
        'status': 'Roadmap-ready',
    },
]

# ── Section 3: Microsoft open-source and developer tools ────────────────────────────────────

MICROSOFT_OPEN_SOURCE_TOOLS = [
    ('microsoft/autogen', 'Multi-agent enterprise collaboration.',
     'Different agents collaborate on energy, finance, engineering, procurement and justice review.', 'Roadmap-ready'),
    ('microsoft/semantic-kernel', 'Enterprise orchestration, plugins, planners and workflows.',
     'Structured industrial workflows and tool-calling.', 'Roadmap-ready'),
    ('microsoft/graphrag', 'Graph-based RAG (GraphRAG).',
     'Map relationships between assets, risks, documents, systems, workers, communities and actions.', 'Next integration'),
    ('microsoft/presidio', 'PII detection and redaction (Microsoft Presidio).',
     'Protect sensitive employee, customer, household and community data before retrieval/model calls.', 'Next integration'),
    ('microsoft/markitdown', 'Convert enterprise files into Markdown/text (MarkItDown).',
     'Ingest PDFs, Word, PowerPoint, Excel, HTML and engineering documents.', 'Next integration'),
    ('microsoft/playwright', 'Browser automation and testing.',
     'Test live demo flows and future enterprise workflows.', 'Next integration'),
    ('microsoft/typescript', 'Typed frontend and agent UI.',
     'Future React/Next.js dashboards and industrial control interfaces.', 'Roadmap-ready'),
    ('microsoft/vscode', 'Developer workflow and extension ecosystem.',
     'Future VS Code extension for repo-aware industrial modernisation agents.', 'Roadmap-ready'),
]

# ── Section 4: Industrial modernisation architecture ─────────────────────────────────────────

INDUSTRIAL_SECTORS = [
    'Energy', 'Power plants', 'Grids', 'Heating networks', 'Factories', 'Water infrastructure',
    'Mining', 'Logistics', 'Public-sector assets', 'Housing/municipal infrastructure',
]

MODERNISATION_ACTIONS = [
    'Solar PV', 'Battery storage', 'Heat pumps', 'Electric boilers', 'Boiler replacement',
    'Insulation', 'Smart meters', 'IoT sensors', 'Grid optimisation', 'Load shifting',
    'Predictive maintenance', 'Equipment lifecycle planning', 'Process optimisation',
    'Finance and staged CAPEX/OPEX', 'Procurement', 'Worker transition',
    'Community protection', 'Justice & Maqasid review',
]

INDUSTRIAL_ARCHITECTURE_DIAGRAM = (
    'Industrial data foundation → Permission-aware retrieval → AI agent workflow '
    '→ Digital twin / asset graph → Modernisation plan → Human approval '
    '→ Action tracking → Audit logs → ESG / justice / investment dashboard'
)

# ── Section 5: Design thinking mapping ────────────────────────────────────────────────────────

DESIGN_THINKING = [
    {
        'stage': 'Empathise',
        'body': 'Understand real industrial users:',
        'items': [
            'Energy managers', 'Factory operators', 'Maintenance engineers', 'Finance teams',
            'Public-sector officers', 'Communities affected by transition',
        ],
    },
    {
        'stage': 'Define',
        'body': (
            'Core problem: industrial modernisation is slow because data is fragmented across '
            'old documents, sensor systems, spreadsheets, ERP, maintenance logs and policy '
            'files. Teams lack a trusted, permission-aware action plan.'
        ),
        'items': [],
    },
    {
        'stage': 'Ideate',
        'body': 'EcoIQ proposes agents for:',
        'items': [
            'Energy efficiency', 'Solar/battery planning', 'Heat replacement',
            'Predictive maintenance', 'Grid optimisation', 'Procurement', 'Finance',
            'Worker transition', 'Justice and community impact',
        ],
    },
    {
        'stage': 'Prototype',
        'body': 'Current live MVP:',
        'items': [
            '/legacy-safe/', 'Permission demo', 'Revocation demo', 'Audit logs',
            'Dependency graph', 'Justice & Maqasid layer',
        ],
    },
    {
        'stage': 'Test',
        'body': 'Run pilots with:',
        'items': [
            'One energy company', 'One industrial site', 'One heating network',
            'One municipal infrastructure portfolio', 'One investor/government transition team',
        ],
    },
]

# ── Section 6: Microsoft pilot proposal ──────────────────────────────────────────────────────

PILOT = {
    'title': 'EcoIQ Industrial Modernisation Agent Pilot',
    'goal': (
        'Use EcoIQ LegacySafe AI to help one industrial or energy organisation identify '
        'practical modernisation actions from old documents, sensor data, equipment records '
        'and ESG evidence.'
    ),
    'scope': [
        'One facility or asset portfolio', '10–50 documents', 'Sample sensor/meter data',
        'Maintenance logs', 'Equipment list', 'Budget/procurement sample',
        'ESG/public impact documents',
    ],
    'outputs': [
        'Permission-aware evidence base', 'Asset and dependency map',
        'Solar/battery/heat/efficiency opportunities', 'Predictive maintenance recommendations',
        'Investment and procurement pathway', 'Worker/community transition considerations',
        'Audit logs', 'Executive dashboard',
    ],
    'stack': [
        'Microsoft Fabric for data unification', 'Azure Digital Twins for asset modelling',
        'Azure IoT for telemetry', 'Azure AI / Azure OpenAI-ready model provider',
        'Microsoft Entra ID for permissions', 'Power BI for dashboards',
        'Teams/Copilot-style workflow for approvals', 'Presidio for data protection',
        'GraphRAG for knowledge relationships', 'MarkItDown for document ingestion',
    ],
}

# ── Section 7: Enterprise safety principles ──────────────────────────────────────────────────

SAFETY_PRINCIPLES = [
    'Permission checks before retrieval',
    'Model receives allowed context only',
    'No LLM permission decisions',
    'All actions logged',
    'Human approval for write actions',
    'No automatic execution of unknown scripts',
    'Untrusted documents treated as content, not instructions',
    'Source lineage preserved',
    'Revoked data must not appear in future outputs',
    'Sensitive sites and vulnerable communities protected',
    'Justice and stakeholder impact considered before action',
]

# ── Section 8: Questions for Microsoft advisers ──────────────────────────────────────────────

ADVISER_QUESTIONS = [
    'Which Microsoft layer should EcoIQ integrate first: Fabric, Azure AI, Digital Twins, IoT, Copilot workflows, or Entra/security?',
    'What data model would Microsoft recommend for industrial asset modernisation across energy, factories, heating, water and logistics?',
    'How should EcoIQ safely combine documents, sensor data, maintenance logs, ERP records and ESG reports?',
    'How can permission-aware AI agents be deployed without exposing restricted financial, engineering or executive data?',
    'What is the best first pilot: predictive maintenance, energy efficiency, clean heat transition, grid optimisation, or ESG evidence verification?',
    'How can Microsoft help EcoIQ scale from one facility to a national industrial transition map?',
]

# ── Section 9: Roadmap ────────────────────────────────────────────────────────────────────────

ROADMAP = {
    'MVP now': [
        'Django module', 'Permission-aware memory', 'Deterministic retrieval guard',
        'Audit logs', 'Revocation', 'Dependency graph scaffold', 'Justice & Maqasid layer',
        'Live demo',
    ],
    'Next integrations': [
        'Richer modernisation planner', 'MarkItDown document ingestion',
        'Presidio PII redaction', 'GraphRAG/NetworkX asset relationships',
        'Playwright demo tests', 'Semgrep/Tree-sitter repository scanning',
    ],
    'Roadmap-ready': [
        'Azure AI / Azure OpenAI-ready provider', 'Microsoft Fabric', 'Azure Digital Twins',
        'Azure IoT', 'Entra ID', 'Power BI', 'Teams/Copilot-style workflows',
        'Semantic Kernel', 'AutoGen',
    ],
    'Research watchlist': [
        'National-scale industrial transition modelling', 'Digital twin + justice impact graph',
        'AI-assisted procurement optimisation', 'Multi-stakeholder approval workflows',
        'Public-sector climate finance dashboards',
    ],
}
