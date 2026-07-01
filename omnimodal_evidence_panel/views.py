"""
EcoIQ Omnimodal Evidence Panel — live visual evidence interface (presentational module).

Shows how EcoIQ's interface would surface documents, photos, videos, websites, sensor data,
charts, extracted facts, and Maqasid/Mizan meaning while AI agents are working — instead of
only returning a text answer. This is a product/UI concept page: no documents are actually
read, no photos/videos are actually analysed, no external model APIs are called, and no API
keys are used. It connects conceptually to the Multi-Model Intelligence Layer, Amanah
Autopilot, LegacySafe, and the industrial modernisation planner elsewhere in EcoIQ.
"""
from django.shortcuts import render

POSITIONING_LINE = 'EcoIQ should not only answer — it should show the evidence moving behind the answer.'

CAPABILITIES = [
    {
        'title': 'Live Document Reading',
        'items': [
            'Shows PDF/report pages',
            'Highlights relevant passages',
            'Extracts facts, figures and citations',
            'Links claims to evidence',
        ],
    },
    {
        'title': 'Photo Diagnosis',
        'items': [
            'Shows uploaded industrial photos',
            'Adds visual labels and risk signals',
            'Detects visible issues such as heat loss, old equipment, corrosion, missing '
            'insulation, safety risks and lack of monitoring',
            'Marks outputs as AI hypotheses requiring expert verification',
        ],
    },
    {
        'title': 'Video Walkthrough Analysis',
        'items': [
            'Supports inspection walkthroughs from iPad, iPhone or mobile web',
            'Shows what the AI is currently focusing on',
            'Saves timestamped evidence',
            'Creates asset-level observations',
        ],
    },
    {
        'title': 'Website and Public-Data Reading',
        'items': [
            'Shows source websites or extracted content',
            'Turns public pages into clean evidence',
            'Supports company research, supplier discovery, regulation tracking and '
            'greenwashing checks',
        ],
    },
    {
        'title': 'Sensor and Meter Overlays',
        'items': [
            'Shows energy, heat, water, temperature, vibration, pressure, downtime and '
            'emissions signals',
            'Displays live charts and anomalies',
            'Links sensor data to asset passports and modernisation recommendations',
        ],
    },
    {
        'title': 'Visualisation While Reasoning',
        'items': [
            'Builds charts, scorecards, maps, timelines and process diagrams while the '
            'agent works',
            'Explains what each visual means',
            'Shows technical, financial and Maqasid/Mizan meaning together',
        ],
    },
    {
        'title': 'Evidence-to-Action Audit Trail',
        'items': [],
        'chain': [
            'Source', 'Extracted fact', 'Risk signal', 'Recommendation',
            'Human approval', 'Implementation', 'Monitoring',
        ],
    },
]

MODEL_CARDS = [
    {
        'name': 'Gemini Live / Gemini multimodal',
        'use': [
            'Real-time camera, screen and video understanding',
            'Live inspection assistant',
            'Visual walkthroughs',
            'Background evidence panel',
            'Multimodal long-context reasoning',
        ],
    },
    {
        'name': 'OpenAI / Azure OpenAI',
        'use': [
            'Vision', 'Reasoning', 'Structured outputs',
            'Enterprise-sensitive workloads through Azure OpenAI',
        ],
    },
    {
        'name': 'Claude',
        'use': [
            'Institutional finance memos', 'Long-form analysis',
            'Modelling explanations', 'Investor and board reports',
        ],
    },
    {
        'name': 'Kimi',
        'use': [
            'Long-context documents', 'Coding workflows',
            'Large document review', 'Agentic analysis',
        ],
    },
    {
        'name': 'DeepSeek',
        'use': [
            'Low-cost batch reasoning', 'Coding support',
            'Public-data classification', 'Non-sensitive bulk processing',
        ],
    },
]

ROUTER_WORKFLOW = [
    'Input', 'Omnimodal intake', 'Sensitivity check', 'Model router', 'Evidence extraction',
    'Structured output validation', 'Visualisation agent', 'Maqasid/Mizan scoring',
    'Human approval', 'Dashboard/report', 'Monitoring/MRV',
]

ROUTING_RULES = [
    'Sensitive industrial/client data defaults to Azure OpenAI or an approved enterprise deployment.',
    'Public websites and open reports may use Kimi, DeepSeek, Gemini or OpenAI depending on task and cost.',
    'Live inspection/video workflows may use Gemini Live-style multimodal capabilities or OpenAI/Azure vision.',
    'Finance/investor memos may use Claude/OpenAI.',
    'All high-impact recommendations require human review and approval.',
]

UI_LAYOUT = [
    {'panel': 'Left panel — AI reasoning', 'items': ['AI reasoning', 'Summary', 'Risks', 'Recommendations', 'Next actions', 'Approval status']},
    {'panel': 'Right panel — live evidence viewer', 'items': ['Live evidence viewer', 'PDF page / photo / video frame / website / sensor stream', 'Highlighted source', 'Bounding boxes or visual labels', 'Extracted facts']},
    {'panel': 'Bottom panel — impact and roadmap', 'items': ['Charts', 'Maqasid/Mizan score', 'No Harm Gate', 'Finance impact', 'Implementation roadmap']},
]

EXAMPLES = [
    {
        'title': 'Example 1 — Boiler House Photo',
        'evidence': ['Uninsulated pipe', 'Old boiler', 'Soot marks', 'No smart meter'],
        'output': [
            'Heat loss risk', 'Combustion/pollution risk', 'Monitoring gap',
            'Recommendation: measure baseline, insulate pipes, add smart meters, service or '
            'replace boiler',
        ],
        'maqasid': [
            'Reduce harm to health', 'Reduce waste of fuel',
            'Restore balance between resource input and useful heat',
        ],
    },
    {
        'title': 'Example 2 — Factory Production Line',
        'evidence': ['Old motor', 'Manual inspection', 'Congestion', 'Downtime signs', 'Lack of sensors'],
        'output': [
            'Energy hotspot', 'Automation opportunity', 'Quality control risk',
            'Recommendation: sub-metering, predictive maintenance, camera-based quality inspection',
        ],
        'maqasid': ['Reduce waste', 'Protect workers', 'Improve fair and efficient use of resources'],
    },
    {
        'title': 'Example 3 — Annual Report / ESG Claim',
        'evidence': [
            'Company claims sustainability progress',
            'AI checks whether there is baseline data, CAPEX, KPIs and year-on-year progress',
        ],
        'output': ['Evidence quality score', 'Greenwashing risk', 'Missing data list', 'Investor-ready questions'],
        'maqasid': [],
    },
]

SAFETY_PRINCIPLES = [
    'The Omnimodal Evidence Panel shows evidence and AI hypotheses, not final engineering certification.',
    'High-impact industrial, financial, safety and environmental decisions require human expert approval.',
    'Maqasid/Mizan is an ethical decision-support framework, not a fatwa or religious ruling.',
    'Every recommendation must link back to evidence, confidence level and missing data.',
    'The system should show "Needs verification" when data is incomplete.',
]

AMANAH_INTEGRATION_ITEMS = [
    'High-harm assets', 'Visible risks', 'Missing data',
    'Funding opportunities', 'Supplier shortlist', 'Reports ready for approval',
]

MORNING_BRIEFING_ITEMS = [
    'Evidence reviewed', 'Risks detected', 'Quick wins identified',
    'Maqasid/Mizan score impact', 'Next actions ready for human approval',
]


def overview(request):
    return render(request, 'omnimodal_evidence_panel/overview.html', {
        'positioning_line': POSITIONING_LINE,
        'capabilities': CAPABILITIES,
        'model_cards': MODEL_CARDS,
        'router_workflow': ROUTER_WORKFLOW,
        'routing_rules': ROUTING_RULES,
        'ui_layout': UI_LAYOUT,
        'examples': EXAMPLES,
        'safety_principles': SAFETY_PRINCIPLES,
        'amanah_integration_items': AMANAH_INTEGRATION_ITEMS,
        'morning_briefing_items': MORNING_BRIEFING_ITEMS,
    })
