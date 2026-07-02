"""
EcoIQ Microsoft Ecosystem Core Stack — presentational product module.

Shows how EcoIQ is Microsoft ecosystem-ready and could be built on Microsoft/Azure enterprise
infrastructure using specialised Microsoft open-source repositories for agents, RAG, digital
twins, IoT, dashboards, responsible AI, and sustainability. This is a roadmap/architecture page:
no repository listed here is installed, called, or wired into the running app, no external API
calls are made, and no API keys are used. EcoIQ is described as "Microsoft ecosystem-ready", not
as a Microsoft partner, unless a partnership is confirmed separately.
"""
from django.shortcuts import render

STACK_LAYERS = [
    {
        'number': 1,
        'title': 'AI Agent Brain',
        'purpose': (
            'Use this layer for EcoIQ agents that read company reports, compare industrial '
            'processes, recommend upgrades, generate investor briefings and coordinate '
            'multi-agent workflows.'
        ),
        'repos': [
            ('microsoft/agent-framework', 'Production-grade AI agents and multi-agent workflows in Python/.NET'),
            ('microsoft/semantic-kernel', 'Plugins, workflows, memory and enterprise AI orchestration'),
            ('microsoft/promptflow', 'Prompt testing, output comparison and report quality evaluation'),
            ('microsoft/graphrag', 'Knowledge graph from company reports, ESG files, ministries, suppliers and industrial assets'),
            ('microsoft/markitdown', 'Convert PDFs, Word, PowerPoint, Excel and webpages into clean Markdown for AI ingestion'),
            ('microsoft/LLMLingua', 'Compress long reports before sending to models'),
            ('microsoft/TaskWeaver', 'Data-heavy analysis for emissions, costs, ROI, CAPEX and efficiency'),
        ],
        'use_case': (
            'Upload annual report → extract data → build company profile → score climate and '
            'industrial readiness → generate investor-ready recommendations.'
        ),
    },
    {
        'number': 2,
        'title': 'RAG and Evidence Engine',
        'purpose': 'Make EcoIQ answers evidence-based, not AI guesses.',
        'repos': [
            ('Azure-Samples/azure-search-openai-demo', 'RAG template using Azure OpenAI and Azure AI Search'),
            ('Azure-Samples/azure-search-vector-samples', 'Vector search across filings, reports, regulations and supplier documents'),
            ('Azure-Samples/document-intelligence-code-samples', 'Extract tables, forms, text and scanned documents'),
            ('Azure-Samples/azure-ai-search-power-skills', 'Custom enrichment for emissions, industry tags and risk labels'),
            ('Azure-Samples/azure-ai-studio-secure-bicep', 'Secure Azure AI deployment pattern'),
        ],
        'use_case': (
            'Every EcoIQ recommendation shows source, confidence, evidence link, data age, '
            'risk level and missing data.'
        ),
    },
    {
        'number': 3,
        'title': 'Industrial, Energy and Digital Twin Layer',
        'purpose': (
            'Use this layer for gas, uranium, oil, mining, boilers, metals, agriculture, '
            'electricity, factories and district heating systems.'
        ),
        'repos': [
            ('Azure/Industrial-IoT', 'Connect industrial equipment, OPC UA, factories and energy assets'),
            ('Azure/iotedge', 'Run monitoring at factories, mines, boilers, farms and remote sites'),
            ('Azure/azure-iot-sdk-python', 'Python device data ingestion'),
            ('Azure-Samples/azure-digital-twins-samples', 'Model factories, boilers, mines, farms and energy grids'),
            ('Azure/azure-digital-twins-explorer', 'Visualise industrial assets and relationships'),
            ('Azure/opendigitaltwins-energygrid', 'Electricity, substations and grid assets'),
            ('Azure/opendigitaltwins-manufacturing', 'Production lines, machines and processes'),
            ('Azure/opendigitaltwins-building', 'Boilers, heating systems, buildings and sensors'),
            ('Azure/opendigitaltwins-agriculture', 'Farms, irrigation, soil, greenhouses and livestock'),
        ],
        'use_case': (
            'Create a digital twin of a coal boiler system → compare with electric boiler, '
            'heat pump or district heating upgrade → estimate CO₂ reduction, cost, payback '
            'and health impact.'
        ),
    },
    {
        'number': 4,
        'title': 'Data Platform and Dashboards',
        'purpose': (
            'Use this layer for investors, akimats, ministries, industrial companies and '
            'Microsoft-style dashboards.'
        ),
        'repos': [
            ('microsoft/fabric-samples', 'Lakehouse, analytics and enterprise data platform'),
            ('microsoft/SynapseML', 'Large-scale ML on industrial and climate datasets'),
            ('microsoft/PowerBI-JavaScript', 'Embed dashboards into ecoiq.uk'),
            ('microsoft/powerbi-client-react', 'React dashboard integration'),
            ('microsoft/PowerBI-visuals', 'Custom visuals for emissions, ROI and company rankings'),
            ('microsoft/DataConnectors', 'Connect external datasets, ministries and ESG portals'),
            ('microsoft/sql-server-samples', 'Enterprise SQL architecture'),
            ('Azure/azure-sdk-for-python', 'Connect EcoIQ backend to Azure services'),
        ],
        'use_case': (
            'Public dashboard: Kazakhstan industrial modernisation map. Private dashboard: '
            'company-level transition plan, ROI, emissions, Maqasid/Mizan score and investor '
            'readiness.'
        ),
    },
    {
        'number': 5,
        'title': 'Responsible AI, Trust and Compliance',
        'purpose': (
            'EcoIQ scores companies, governments and investment opportunities, so scoring '
            'must be explainable, auditable and safe.'
        ),
        'repos': [
            ('microsoft/responsible-ai-toolbox', 'Understand, assess and monitor AI systems'),
            ('microsoft/fairlearn', 'Check fairness of scoring models'),
            ('microsoft/interpret', 'Explain why a company got a score'),
            ('microsoft/presidio', 'Detect and remove personal/private data from documents'),
            ('microsoft/PyRIT', 'Red-team prompts and agents for unsafe outputs'),
            ('microsoft/garak', 'Scan LLM vulnerabilities'),
        ],
        'use_case': (
            'Every company score should answer: Why this score? Which evidence? Which '
            'assumptions? Which data is missing? What requires human review?'
        ),
    },
    {
        'number': 6,
        'title': 'Sustainability and Climate Layer',
        'purpose': 'Give EcoIQ a stronger climate-tech foundation.',
        'repos': [
            ('Green-Software-Foundation/carbon-aware-sdk', 'Emissions-aware scheduling and carbon-aware software'),
            ('microsoft/Cloud-for-Sustainability-API-Samples', 'Connect sustainability data and reporting workflows'),
            ('microsoft/PlanetaryComputerExamples', 'Climate, satellite and geospatial data'),
            ('microsoft/torchgeo', 'Geospatial ML for land, agriculture, mining and environment'),
            ('microsoft/Project15', 'IoT for conservation and environmental monitoring'),
        ],
        'use_case': (
            'Satellite + company data + emissions + industrial assets → climate risk and '
            'transition opportunity map.'
        ),
    },
]

FINAL_STACK_REPOS = [
    'microsoft/agent-framework', 'microsoft/semantic-kernel', 'microsoft/promptflow',
    'microsoft/graphrag', 'microsoft/markitdown', 'microsoft/LLMLingua', 'microsoft/TaskWeaver',
    'Azure-Samples/azure-search-openai-demo', 'Azure-Samples/azure-search-vector-samples',
    'Azure-Samples/document-intelligence-code-samples', 'Azure/Industrial-IoT', 'Azure/iotedge',
    'Azure/azure-iot-sdk-python', 'Azure-Samples/azure-digital-twins-samples',
    'Azure/azure-digital-twins-explorer', 'Azure/opendigitaltwins-energygrid',
    'Azure/opendigitaltwins-manufacturing', 'Azure/opendigitaltwins-building',
    'microsoft/fabric-samples', 'microsoft/SynapseML', 'microsoft/PowerBI-JavaScript',
    'microsoft/responsible-ai-toolbox', 'microsoft/presidio', 'microsoft/PyRIT',
    'Green-Software-Foundation/carbon-aware-sdk',
]

ARCHITECTURE_FLOW = [
    'Industrial data sources', 'Document conversion and RAG', 'Agent brain', 'Digital twin',
    'Simulation and scoring', 'Responsible AI validation', 'Power BI dashboard',
    'Investor-ready roadmap', 'Monitoring and verified impact',
]

WORKFLOW_UPLOADS = [
    'Annual report', 'ESG report', 'Energy bills', 'Equipment list',
    'Boiler photos', 'Sensor data',
]

WORKFLOW_STEPS = [
    'Convert documents with MarkItDown',
    'Build RAG evidence with Azure AI Search',
    'Build knowledge graph with GraphRAG',
    'Build digital twin with Azure Digital Twins',
    'Run agents with Agent Framework / Semantic Kernel',
    'Analyse cost, emissions, CAPEX and ROI with TaskWeaver / SynapseML',
    'Visualise results with Power BI',
    'Validate fairness, privacy and safety with Responsible AI tools',
    'Generate modernisation roadmap with Maqasid/Mizan score',
    'Track verified impact over time',
]

WHY_MICROSOFT = [
    'Enterprise trust', 'Azure security', 'Fabric data governance', 'Power BI dashboards',
    'Digital Twins for industrial assets', 'IoT integration for real equipment',
    'Responsible AI tooling', 'GitHub developer ecosystem',
    'Compatibility with Teams, SharePoint, Power Apps and Dynamics',
]

ECOIQ_ADDS = [
    'Industrial modernisation methodology', 'Maqasid/Mizan ethical scoring', 'Amanah Autopilot',
    'Omnimodal Evidence Panel', 'Boiler, factory, mining, agriculture and energy transition playbooks',
    'Investor-ready transition reports', 'Verified impact and MRV workflow',
]

SAFETY_PRINCIPLES = [
    'EcoIQ does not claim Microsoft officially endorses EcoIQ unless a partnership exists.',
    'EcoIQ describes itself as "Microsoft ecosystem-ready", not "Microsoft partner", unless confirmed.',
    'Maqasid/Mizan is presented as ethical decision-support, not a religious ruling.',
    'High-impact industrial recommendations require human expert approval.',
    'Sensitive client data defaults to Azure OpenAI / an approved enterprise deployment.',
]

CTA_BUTTONS = [
    {'label': 'Explore Microsoft Stack', 'anchor': '#stack-layers'},
    {'label': 'Generate Industrial Modernisation Roadmap', 'url_name': 'legacy_safe:ask'},
    {'label': 'Request EcoIQ Review', 'url_name': 'leads:request_review'},
    {'label': 'View Digital Twin Example', 'anchor': '#digital-twin-example'},
]


def overview(request):
    return render(request, 'microsoft_core_stack/overview.html', {
        'stack_layers': STACK_LAYERS,
        'final_stack_repos': FINAL_STACK_REPOS,
        'architecture_flow': ARCHITECTURE_FLOW,
        'workflow_uploads': WORKFLOW_UPLOADS,
        'workflow_steps': WORKFLOW_STEPS,
        'why_microsoft': WHY_MICROSOFT,
        'ecoiq_adds': ECOIQ_ADDS,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })
