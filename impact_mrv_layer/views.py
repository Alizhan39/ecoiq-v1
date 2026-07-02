from django.shortcuts import render

# Connected EcoIQ modules — the MRV Layer proves the impact those modules generate
CONNECTED_MODULES = [
    {
        'name': 'Asset Passport',
        'role': 'Supplies the asset record — baseline condition, modernisation pathway and '
                'ownership — that every MRV project tracks against.',
    },
    {
        'name': 'Omnimodal Evidence Panel',
        'role': 'Supplies the photos, videos, documents and sensor readings used as before '
                'and after evidence.',
    },
    {
        'name': 'Amanah Autopilot',
        'role': 'Runs overnight checks for missing baseline data, weak evidence or delayed '
                'implementation, and prepares a morning MRV follow-up list.',
    },
    {
        'name': 'Microsoft Ecosystem Core Stack',
        'role': 'Provides the agent, RAG, digital twin and dashboard building blocks a '
                'production MRV implementation would run on.',
    },
    {
        'name': 'Digital Twins',
        'role': 'Model the asset before and after modernisation so simulated and measured '
                'performance can be compared directly.',
    },
    {
        'name': 'Power BI dashboards',
        'role': 'Visualise energy, cost, emissions, downtime and Maqasid/Mizan trends for '
                'investors, governments and community stakeholders.',
    },
    {
        'name': 'Institutional Finance Engine',
        'role': 'Uses verified impact records as proof points to unlock the next tranche of '
                'blended, CAPEX-free or investor-backed financing.',
    },
    {
        'name': 'Maqasid/Mizan ethical scoring',
        'role': 'Scores whether the modernisation actually protected health, wealth and '
                'resources, and restored balance — not just cut a number on a spreadsheet.',
    },
]

MRV_WORKFLOW = [
    {
        'number': 1,
        'title': 'Measure Baseline',
        'description': 'Capture current energy use, fuel use, water use, emissions, cost, '
                        'downtime, safety risk, photos and documents.',
    },
    {
        'number': 2,
        'title': 'Record Evidence',
        'description': 'Store photos, videos, energy bills, fuel invoices, sensor data, '
                        'maintenance logs, inspection notes and third-party reports.',
    },
    {
        'number': 3,
        'title': 'Approve Action',
        'description': 'Human reviewer approves the recommended modernisation pathway before '
                        'implementation.',
    },
    {
        'number': 4,
        'title': 'Implement Upgrade',
        'description': 'Track supplier, budget, installation date, equipment, invoice, '
                        'project owner and implementation status.',
    },
    {
        'number': 5,
        'title': 'Measure After',
        'description': 'Collect post-upgrade data from meters, sensors, photos, bills and '
                        'operational logs.',
    },
    {
        'number': 6,
        'title': 'Compare Before/After',
        'description': 'Calculate energy saved, CO2 reduced, cost saved, downtime reduced, '
                        'waste reduced and risk reduction.',
    },
    {
        'number': 7,
        'title': 'Verify Impact',
        'description': 'Check whether evidence is strong, medium or weak. Flag missing data '
                        'and require expert review where needed.',
    },
    {
        'number': 8,
        'title': 'Generate Report',
        'description': 'Create investor, government, CSR, Islamic finance and community '
                        'impact reports.',
    },
]

EVIDENCE_TYPES = [
    'Meter readings', 'Energy bills', 'Fuel bills', 'Water bills', 'Photos', 'Videos',
    'Sensor data', 'Maintenance logs', 'Invoices', 'Supplier reports',
    'Third-party inspections', 'Satellite/geospatial data', 'Power BI dashboards',
]

IMPACT_METRICS = [
    'kWh saved', 'Fuel saved', 'CO2 reduced', 'Water saved', 'Waste reduced',
    'Heat loss reduced', 'Downtime reduced', 'Maintenance risk reduced',
    'Health risk reduced', 'Cost saved', 'Payback progress',
    'Maqasid score improvement', 'Mizan score improvement', 'No Harm Gate status',
    'Evidence quality score',
]

EXAMPLE_CARD = {
    'project': 'Boiler House #3 Modernisation',
    'before': [
        'Coal-based heating',
        'Visible soot marks',
        'Uninsulated pipes',
        'No smart meter',
        'High fuel cost',
        'High heat loss risk',
    ],
    'action': [
        'Pipe insulation',
        'Smart meters',
        'Boiler servicing',
        'Efficiency controls',
        'Monitoring dashboard',
    ],
    'after': [
        'Lower fuel use',
        'Lower heat loss',
        'Better monitoring',
        'Reduced emissions',
        'Improved safety visibility',
    ],
    'verified_impact': [
        'Energy use reduced',
        'Emissions reduced',
        'Cost reduced',
        'Maqasid score improved',
        'Mizan score improved',
        'Evidence quality: medium/high',
    ],
}

EVIDENCE_CHAIN = [
    'Source', 'Baseline fact', 'Modernisation action', 'Post-action measurement',
    'Impact calculation', 'Verification status', 'Report',
]

EVIDENCE_QUALITY_LEVELS = [
    {
        'level': 'Strong evidence',
        'description': 'Meter data, sensor logs, audited reports, invoices, before/after '
                        'photos, third-party inspection.',
    },
    {
        'level': 'Medium evidence',
        'description': 'Company documents, maintenance logs, operator notes, partial bills, '
                        'internal reports.',
    },
    {
        'level': 'Weak evidence',
        'description': 'Marketing claims, vague ESG statements, old data, no baseline, no '
                        'timestamped proof.',
    },
]

EVIDENCE_WARNING = (
    'No project should be counted as verified impact without before/after evidence.'
)

MAQASID_INTERPRETATION = (
    'Impact is not only technical. It should show protection of life, health, wealth, '
    'resources, community welfare and future generations.'
)

MIZAN_INTERPRETATION = (
    'Impact should show that the system became more balanced: less waste, less harm, '
    'more useful output, better resource stewardship.'
)

DASHBOARD_LAYOUT = {
    'top': 'Project status, MRV status, evidence quality, impact score',
    'left': 'Before evidence',
    'middle': 'Action and implementation timeline',
    'right': 'After evidence',
    'bottom': 'Charts showing energy, cost, emissions, downtime and Maqasid/Mizan improvements',
}

AMANAH_CONNECTION = (
    'Amanah Autopilot can run overnight and check whether projects have missing baseline '
    'data, weak evidence, delayed implementation, missing after-data or unverified impact. '
    'In the morning, it prepares an MRV follow-up list for human approval.'
)

MICROSOFT_CONNECTION = (
    'The MRV Layer can use Microsoft Fabric, Power BI, Azure Digital Twins, Azure IoT and '
    'Responsible AI tooling to store, monitor, visualise and audit verified impact.'
)

SAFETY_PRINCIPLES = [
    'EcoIQ MRV is an evidence and reporting layer, not a replacement for certified '
    'engineering, environmental or financial audit.',
    'High-impact claims require expert review.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
    'If evidence is incomplete, the system must show "Needs verification".',
    'Do not allow unsupported impact claims.',
]

CTA_BUTTONS = [
    {'label': 'Start MRV Tracking', 'anchor': '#mrv-workflow'},
    {'label': 'Upload Before Evidence', 'url_name': 'legacy_safe:upload'},
    {'label': 'Upload After Evidence', 'url_name': 'legacy_safe:upload'},
    {'label': 'Verify Impact', 'anchor': '#evidence-quality'},
    {'label': 'Generate MRV Report', 'url_name': 'legacy_safe:ask'},
    {'label': 'Export Investor Proof', 'url_name': 'leads:request_review'},
    {'label': 'Share with Team', 'anchor': '#dashboard-layout'},
]


def overview(request):
    return render(request, 'impact_mrv_layer/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'mrv_workflow': MRV_WORKFLOW,
        'evidence_types': EVIDENCE_TYPES,
        'impact_metrics': IMPACT_METRICS,
        'example_card': EXAMPLE_CARD,
        'evidence_chain': EVIDENCE_CHAIN,
        'evidence_quality_levels': EVIDENCE_QUALITY_LEVELS,
        'evidence_warning': EVIDENCE_WARNING,
        'maqasid_interpretation': MAQASID_INTERPRETATION,
        'mizan_interpretation': MIZAN_INTERPRETATION,
        'dashboard_layout': DASHBOARD_LAYOUT,
        'amanah_connection': AMANAH_CONNECTION,
        'microsoft_connection': MICROSOFT_CONNECTION,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })
