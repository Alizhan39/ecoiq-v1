from django.shortcuts import render

# Connected EcoIQ modules — the mobile layer is where field evidence enters the platform
CONNECTED_MODULES = [
    {'name': 'Omnimodal Evidence Panel', 'role': 'Displays the photos, video and sensor evidence captured on site.'},
    {'name': 'Asset Passport', 'role': 'Is automatically created or updated from a field inspection.'},
    {'name': 'Industrial Playbook Library', 'role': 'Supplies the pathway matched to what the inspector captured.'},
    {'name': 'Impact MRV Layer', 'role': 'Uses the field inspection as the before-evidence baseline.'},
    {'name': 'Supplier & Funding Marketplace', 'role': 'Receives the next-actions list generated from an inspection.'},
    {'name': 'Institutional Finance Engine', 'role': 'Uses field evidence quality to inform finance readiness.'},
    {'name': 'Amanah Autopilot', 'role': 'Reviews inspections overnight and prepares a morning follow-up list.'},
    {'name': 'Microsoft Ecosystem Core Stack', 'role': 'Provides the agent, storage and dashboard building blocks a production mobile app would run on.'},
    {'name': 'Azure AI / OpenAI Vision / Gemini Live-style multimodal workflows', 'role': 'Powers the AI photo and video diagnosis.'},
    {'name': 'Power Apps', 'role': 'A candidate mobile shell for field teams already on Microsoft 365.'},
    {'name': 'Teams', 'role': 'Delivers inspection notifications and approval requests.'},
    {'name': 'Power BI', 'role': 'Visualises inspection activity and findings.'},
    {'name': 'Azure Digital Twins', 'role': 'Links the inspected asset to its digital twin.'},
    {'name': 'Azure IoT', 'role': 'Correlates captured meter readings with live sensor streams.'},
]

CORE_PURPOSE = 'Turn field evidence into structured industrial intelligence.'

PRIMARY_WORKFLOW = [
    {
        'number': 1,
        'title': 'Open EcoIQ on mobile',
        'description': 'User opens EcoIQ from:',
        'items': ['iPhone', 'iPad', 'Android', 'Mac browser', 'Microsoft Teams', 'Power Apps', 'PWA installed app'],
    },
    {
        'number': 2,
        'title': 'Select asset type',
        'description': 'Options:',
        'items': [
            'Boiler house', 'Factory line', 'Compressor', 'Motor', 'Electrical panel',
            'Heat network', 'Building', 'Farm / greenhouse', 'Mine / quarry',
            'Water system', 'Solar + battery site',
        ],
    },
    {
        'number': 3,
        'title': 'Capture evidence',
        'description': 'User captures:',
        'items': [
            'Photos', 'Short video', 'Meter readings', 'Energy bill', 'Fuel bill',
            'Equipment nameplate', 'Maintenance log', 'Voice note', 'GPS/location',
            'Timestamp', 'Safety observation',
        ],
    },
    {
        'number': 4,
        'title': 'AI visual diagnosis',
        'description': 'EcoIQ agents detect:',
        'items': [
            'Uninsulated pipes', 'Soot marks', 'Corrosion', 'Old equipment',
            'Missing sensors', 'Safety risks', 'Heat loss signals', 'Water leaks',
            'Manual process bottlenecks', 'Poor monitoring', 'Potential downtime risks',
        ],
    },
    {
        'number': 5,
        'title': 'Create Asset Passport',
        'description': 'The inspection automatically creates or updates an Asset Passport with:',
        'items': [
            'Photos', 'Documents', 'Asset type', 'Location', 'Visible risks',
            'Baseline data', 'Missing data', 'Recommended playbook',
        ],
    },
    {
        'number': 6,
        'title': 'Match Playbook',
        'description': 'EcoIQ matches the asset to:',
        'items': [
            'Boiler Modernisation Playbook', 'Factory Energy Efficiency Playbook',
            'District Heating Upgrade Playbook', 'Mining Diesel Reduction Playbook',
            'Water Recycling Playbook', 'Smart Agriculture Playbook',
            'Solar + Battery Playbook', 'Waste Heat Recovery Playbook',
            'Compressed Air Optimisation Playbook', 'SMR Feasibility Playbook',
        ],
    },
    {
        'number': 7,
        'title': 'Generate field report',
        'description': 'EcoIQ produces:',
        'items': [
            'Visible risk summary', 'Missing data checklist', 'Recommended next actions',
            'Maqasid/Mizan meaning', 'No Harm Gate notes', 'Supplier/funding next steps',
            'MRV baseline checklist',
        ],
    },
    {
        'number': 8,
        'title': 'Human approval',
        'description': 'Inspector or manager reviews before action.',
        'items': [],
    },
    {
        'number': 9,
        'title': 'Sync to dashboard',
        'description': 'Data syncs to:',
        'items': [
            'Power BI dashboard', 'Asset Passport', 'Digital Twin', 'MRV Layer',
            'Teams notification', 'Supplier/funding workflow',
        ],
    },
]

MOBILE_SCREENS = [
    {
        'number': 1,
        'anchor': 'screen-1',
        'title': 'Start Inspection',
        'label': 'Buttons',
        'items': ['Take Photo', 'Record Video', 'Scan Meter', 'Upload Bill', 'Add Voice Note'],
    },
    {
        'number': 2,
        'anchor': 'screen-2',
        'title': 'AI Photo Diagnosis',
        'label': 'Show',
        'items': ['Image preview', 'Visual labels', 'Risk level', 'Confidence', '"Needs verification" tag'],
    },
    {
        'number': 3,
        'anchor': 'screen-3',
        'title': 'Asset Passport Created',
        'label': 'Show',
        'items': [
            'Asset name', 'Location', 'Risk score', 'Maqasid score', 'Mizan score',
            'Missing data', 'Recommended playbook',
        ],
    },
    {
        'number': 4,
        'anchor': 'screen-4',
        'title': 'Recommended Actions',
        'label': 'Show',
        'items': ['Quick wins', 'Deep upgrades', 'Supplier/funding options', 'MRV checklist'],
    },
    {
        'number': 5,
        'anchor': 'screen-5',
        'title': 'Manager Approval',
        'label': 'Show',
        'items': ['Approve', 'Request more data', 'Assign engineer', 'Generate report', 'Send to Teams'],
    },
]

EXAMPLE_CARDS = [
    {
        'inspection': 'Boiler House #3 — Karaganda Region',
        'captured': [
            '8 photos', '1 fuel bill', '1 meter reading', '1 voice note',
            'GPS location', 'Timestamp',
        ],
        'ai_findings': [
            'Uninsulated pipe detected', 'Soot marks detected', 'No smart meter visible',
            'Corrosion risk visible', 'Heat loss risk medium/high',
        ],
        'recommended_playbook': 'Boiler Modernisation Playbook',
        'next_actions': [
            'Collect 12 months of fuel bills', 'Measure pipe temperature',
            'Install smart heat meters', 'Insulate exposed pipes', 'Service boiler',
            'Prepare finance memo',
        ],
        'maqasid_mizan': 'Reduce harm to health, reduce waste of fuel, protect resources '
                         'and restore balance between fuel input and useful heat.',
    },
    {
        'inspection': 'Factory Production Line #2',
        'captured': ['Motor photos', 'Production line video', 'Downtime note', 'Electricity bill'],
        'ai_findings': [
            'Old motor visible', 'Manual inspection point', 'Congestion/bottleneck risk',
            'No sub-metering visible',
        ],
        'recommended_playbook': 'Factory Energy Efficiency Playbook',
        'next_actions': [
            'Install sub-metering', 'Log downtime reasons', 'Check motor efficiency',
            'Consider predictive maintenance sensors',
            'Assess camera-based quality inspection',
        ],
        'maqasid_mizan': '',
    },
]

OFFLINE_MODE_INTRO = 'EcoIQ should support field use in weak internet environments:'
OFFLINE_MODE_ITEMS = [
    'Save inspection locally', 'Upload when online', 'Compress images/videos',
    'Sync evidence later', 'Keep timestamp and location', 'Mark unsynced evidence clearly',
]

MICROSOFT_DEVICE_WORKFLOW = [
    'iPad / iPhone via responsive web app or PWA', 'Mac via browser',
    'Windows laptop via browser', 'Microsoft Teams app', 'Power Apps mobile',
    'SharePoint document workflow',
]

MICROSOFT_INTEGRATION = [
    {'component': 'Azure Blob Storage', 'role': 'Photos/videos.'},
    {'component': 'Azure AI / OpenAI Vision', 'role': 'Image analysis.'},
    {'component': 'Microsoft Fabric', 'role': 'Evidence and metrics.'},
    {'component': 'Azure Digital Twins', 'role': 'Asset relationships.'},
    {'component': 'Power BI', 'role': 'Dashboards.'},
    {'component': 'Power Automate', 'role': 'Approvals.'},
    {'component': 'Teams', 'role': 'Notifications.'},
    {'component': 'SharePoint', 'role': 'Reports.'},
    {'component': 'Dynamics 365', 'role': 'Supplier/funder pipeline.'},
]

OMNIMODAL_LIVE_INSPECTION_INTRO = (
    'For future live inspection, EcoIQ can support real-time camera/video workflows:'
)
OMNIMODAL_LIVE_INSPECTION_ITEMS = [
    'AI sees what the inspector sees',
    'AI asks the user to move closer to a pipe, motor or meter',
    'AI captures timestamped frames',
    'AI labels risk areas live',
    'AI creates a structured evidence trail',
]
OMNIMODAL_LIVE_INSPECTION_NOTE = 'Designed to support real-time multimodal inspection workflows.'

SAFETY_PRINCIPLES = [
    'Mobile inspection outputs are AI hypotheses, not final engineering certification.',
    'High-impact safety, financial, nuclear, environmental and industrial decisions require '
    'qualified expert review.',
    'Do not allow automatic supplier/funder outreach without human approval.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
    'If evidence is incomplete, show "Needs verification".',
    'Store location, photos and personal data according to privacy rules.',
    'Use Presidio or privacy tooling to detect personal/private data where appropriate.',
]

FIELD_INSPECTION_CHECKLIST = [
    'Asset overview photo', 'Close-up of equipment', 'Nameplate photo', 'Meter reading',
    'Fuel/energy bill', 'Visible damage', 'Safety concerns', 'Short voice note',
    'Location', 'Timestamp', 'Permission/consent if required',
]

CTA_BUTTONS = [
    {'label': 'Start Mobile Inspection', 'anchor': '#primary-workflow'},
    {'label': 'Take Asset Photo', 'anchor': '#screen-1'},
    {'label': 'Create Asset Passport', 'url_name': 'asset_passport:overview'},
    {'label': 'Run Photo Diagnosis', 'anchor': '#screen-2'},
    {'label': 'Generate Field Report', 'url_name': 'legacy_safe:ask'},
    {'label': 'Send to Teams', 'anchor': '#microsoft-device-workflow'},
    {'label': 'Start MRV Baseline', 'url_name': 'impact_mrv_layer:overview'},
    {'label': 'Request Manager Approval', 'url_name': 'leads:request_review'},
]


def overview(request):
    return render(request, 'mobile_inspection_mode/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_purpose': CORE_PURPOSE,
        'primary_workflow': PRIMARY_WORKFLOW,
        'mobile_screens': MOBILE_SCREENS,
        'example_cards': EXAMPLE_CARDS,
        'offline_mode_intro': OFFLINE_MODE_INTRO,
        'offline_mode_items': OFFLINE_MODE_ITEMS,
        'microsoft_device_workflow': MICROSOFT_DEVICE_WORKFLOW,
        'microsoft_integration': MICROSOFT_INTEGRATION,
        'omnimodal_live_inspection_intro': OMNIMODAL_LIVE_INSPECTION_INTRO,
        'omnimodal_live_inspection_items': OMNIMODAL_LIVE_INSPECTION_ITEMS,
        'omnimodal_live_inspection_note': OMNIMODAL_LIVE_INSPECTION_NOTE,
        'safety_principles': SAFETY_PRINCIPLES,
        'field_inspection_checklist': FIELD_INSPECTION_CHECKLIST,
        'cta_buttons': CTA_BUTTONS,
    })
