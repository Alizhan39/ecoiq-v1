from django.shortcuts import render

# Connected EcoIQ modules — the Asset Passport is the record that ties them together
CONNECTED_MODULES = [
    {
        'name': 'Omnimodal Evidence Panel',
        'role': 'Supplies the photos, documents and sensor readings that populate the '
                'passport\'s evidence viewer and let reviewers see the asset directly.',
    },
    {
        'name': 'Amanah Autopilot',
        'role': 'Runs overnight checks against each passport, flagging risks and '
                'drafting the next morning\'s "Good Deeds" briefing from passport status changes.',
    },
    {
        'name': 'Microsoft Ecosystem Core Stack',
        'role': 'Provides the agent, RAG, digital twin and dashboard building blocks a '
                'production passport implementation would run on.',
    },
    {
        'name': 'Digital Twins',
        'role': 'Model the asset\'s physical relationships (pipes, boilers, meters, grid '
                'links) so simulation and scoring have a structured object to act on.',
    },
    {
        'name': 'Industrial Playbook Library',
        'role': 'Supplies the modernisation pathways (insulation, smart metering, boiler '
                'replacement, heat pumps) offered as recommended options on each passport.',
    },
    {
        'name': 'Impact MRV Layer',
        'role': 'Measures, reports and verifies the before/after evidence so a passport\'s '
                'claimed savings become independently checkable impact.',
    },
    {
        'name': 'Institutional Finance Engine',
        'role': 'Matches each passport\'s CAPEX/OPEX profile and finance readiness score to '
                'funding routes, so a modernised asset can find blended or CAPEX-free finance.',
    },
]

# Core fields captured on every Asset Passport
CORE_FIELDS = [
    ('Asset name', 'What the asset is called or numbered on site.'),
    ('Asset type', 'Boiler, factory line, mine, farm, building, grid asset or energy project.'),
    ('Location', 'Site, city and region.'),
    ('Owner / operator', 'Who owns or runs the asset day to day.'),
    ('Sector', 'Energy, manufacturing, mining, agriculture, buildings or grid.'),
    ('Age', 'Years in service since installation or last major overhaul.'),
    ('Fuel / energy source', 'Coal, gas, diesel, grid electricity, or a mixed source.'),
    ('Capacity', 'Rated output or throughput of the asset.'),
    ('Current condition', 'Working, degraded, at-risk or failing.'),
    ('Photos and visual evidence', 'Site photos showing wear, leaks, corrosion or missing controls.'),
    ('Documents and reports', 'Manuals, inspection reports, annual reports and ESG filings.'),
    ('Sensor and meter data', 'Live or logged readings from meters, sensors and controllers.'),
    ('Baseline energy / water / emissions', 'Starting-point consumption and emissions before any changes.'),
    ('Visible risks', 'Risks an inspector or photo can see directly.'),
    ('Operational risks', 'Risks to uptime, output or process continuity.'),
    ('Safety risks', 'Risks to workers or the surrounding community.'),
    ('Modernisation options', 'Candidate upgrades ranked by impact and cost.'),
    ('CAPEX estimate', 'Upfront cost of the recommended pathway.'),
    ('OPEX savings', 'Expected reduction in ongoing running costs.'),
    ('Payback estimate', 'Time to recover the investment from savings.'),
    ('Funding route', 'Grant, blended finance, CAPEX-free or investor-backed financing.'),
    ('Supplier shortlist', 'Vetted suppliers able to deliver the modernisation pathway.'),
    ('Maqasid score', 'Ethical alignment: protection of health, wealth, resources and dignity.'),
    ('Mizan score', 'Balance between input, useful output and harm created.'),
    ('No Harm Gate status', 'Whether the asset currently passes or fails the no-harm threshold.'),
    ('Human approval status', 'Whether a qualified human has reviewed and signed off the record.'),
    ('Implementation status', 'Not started, in progress, or complete.'),
    ('Monitoring KPIs', 'The indicators tracked once modernisation begins.'),
    ('Before/after evidence', 'Paired evidence proving the change actually happened.'),
    ('MRV verification status', 'Whether an independent MRV review has verified the claimed impact.'),
]

EXAMPLE_CARD = {
    'asset': 'Boiler House #3',
    'location': 'Karaganda Region',
    'type': 'Coal-fired boiler house',
    'visible_evidence': [
        'Uninsulated pipes',
        'Old boiler body',
        'Soot marks',
        'No smart meter',
    ],
    'risks': [
        'Heat loss',
        'Fuel waste',
        'Air pollution',
        'Maintenance risk',
        'Weak monitoring',
    ],
    'pathway': [
        'Measure baseline',
        'Insulate pipes',
        'Install smart meters',
        'Service or replace boiler',
        'Assess heat pump / electric boiler / district heating option',
        'Monitor verified savings',
    ],
    'maqasid_meaning': 'Protect health, reduce waste, protect wealth and resources.',
    'mizan_meaning': 'Restore balance between fuel input, useful heat output and harm reduction.',
    'finance': 'Efficiency-first quick wins, then equipment upgrade financing.',
}

DASHBOARD_LAYOUT = {
    'left': 'Asset summary and status',
    'right': 'Evidence viewer with photos/documents/sensor chart',
    'bottom': 'Modernisation roadmap, Maqasid/Mizan score, finance readiness, MRV status',
}

LIFECYCLE = [
    'Evidence captured',
    'Asset passport created',
    'Risks diagnosed',
    'Modernisation pathway selected',
    'Finance prepared',
    'Human approval',
    'Implementation',
    'Monitoring',
    'Verified impact',
]

SAFETY_COPY = (
    'The Asset Passport is an evidence and decision-support record. It does not replace '
    'engineering certification, safety inspection, environmental permitting or qualified '
    'professional review.'
)

CTA_BUTTONS = [
    {'label': 'Create Asset Passport', 'anchor': '#core-fields'},
    {'label': 'Upload Asset Evidence', 'url_name': 'legacy_safe:upload'},
    {'label': 'Run Modernisation Diagnosis', 'url_name': 'legacy_safe:ask'},
    {'label': 'Generate Investor Brief', 'url_name': 'leads:request_review'},
    {'label': 'Verify Impact', 'anchor': '#lifecycle'},
]


def overview(request):
    return render(request, 'asset_passport/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_fields': CORE_FIELDS,
        'example_card': EXAMPLE_CARD,
        'dashboard_layout': DASHBOARD_LAYOUT,
        'lifecycle': LIFECYCLE,
        'safety_copy': SAFETY_COPY,
        'cta_buttons': CTA_BUTTONS,
    })
