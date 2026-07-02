from django.shortcuts import render

# Connected EcoIQ modules — the Playbook Library is the "what to do next" layer
CONNECTED_MODULES = [
    {
        'name': 'Asset Passport',
        'role': 'Supplies the asset record a playbook is matched against.',
    },
    {
        'name': 'Impact MRV Layer',
        'role': 'Measures and verifies whether a playbook\'s recommended actions actually '
                'delivered the promised savings.',
    },
    {
        'name': 'Omnimodal Evidence Panel',
        'role': 'Supplies the photos, documents and sensor readings used to match an asset '
                'to the right playbook.',
    },
    {
        'name': 'Amanah Autopilot',
        'role': 'Runs overnight, matches assets to playbooks, finds quick wins and prepares '
                'morning recommendations for human approval.',
    },
    {
        'name': 'Microsoft Ecosystem Core Stack',
        'role': 'Provides the agent, data platform, digital twin and dashboard building '
                'blocks a production playbook engine would run on.',
    },
    {
        'name': 'Institutional Finance Engine',
        'role': 'Matches a playbook\'s CAPEX/OPEX/payback profile to a funding route.',
    },
    {
        'name': 'Digital Twins',
        'role': 'Model the asset so a playbook\'s recommended upgrades can be simulated '
                'before they are implemented.',
    },
    {
        'name': 'Maqasid/Mizan ethical scoring',
        'role': 'Scores whether a playbook\'s recommended pathway actually protects health, '
                'wealth and resources and restores balance.',
    },
    {
        'name': 'No Harm Gate',
        'role': 'Blocks a playbook pathway from proceeding if it would create more harm than '
                'it removes.',
    },
]

CORE_FORMULA = [
    'Evidence', 'Diagnosis', 'Playbook', 'Finance', 'Implementation', 'MRV Verified Impact',
]

PLAYBOOKS = [
    {
        'number': 1,
        'title': 'Boiler Modernisation Playbook',
        'applies_to': 'Coal boilers, gas boilers, district heating boiler houses, industrial steam systems.',
        'problem_signs': [
            'Old boiler', 'Soot marks', 'No smart meter', 'High fuel cost',
            'Uninsulated pipes', 'Poor combustion', 'Frequent maintenance',
        ],
        'evidence_needed': [
            'Boiler photos', 'Fuel bills', 'Heat output', 'Equipment age',
            'Maintenance logs', 'Temperature readings', 'Emissions data if available',
        ],
        'recommended_actions': [
            'Measure baseline', 'Insulate pipes', 'Service burner/combustion system',
            'Install smart meters', 'Add controls', 'Assess boiler replacement',
            'Assess heat pump / electric boiler / district heating upgrade',
        ],
        'maqasid_mizan_meaning': 'Reduce harm to health, reduce fuel waste, protect wealth '
                                  'and restore balance between resource input and useful heat output.',
        'mrv_metrics': [
            'Fuel saved', 'kWh saved', 'CO2 reduced', 'Cost saved', 'Heat loss reduced',
            'Safety risk reduced',
        ],
    },
    {
        'number': 2,
        'title': 'Factory Energy Efficiency Playbook',
        'applies_to': 'Manufacturing plants, production lines, packaging lines, metal processing, food processing.',
        'problem_signs': [
            'High energy per unit', 'Old motors', 'High downtime', 'High defect rate',
            'Manual quality inspection', 'Compressed air leaks', 'No sub-metering',
        ],
        'evidence_needed': [
            'Energy bills', 'Equipment list', 'Production output', 'Downtime logs',
            'Defect rate', 'Machine photos', 'Maintenance records',
        ],
        'recommended_actions': [
            'Install sub-metering', 'Fix compressed air leaks', 'Replace inefficient motors',
            'Add predictive maintenance', 'Optimise production scheduling',
            'Add camera-based quality inspection', 'Recover waste heat',
        ],
        'maqasid_mizan_meaning': 'Reduce waste, protect workers, improve fair and efficient '
                                  'use of resources.',
        'mrv_metrics': [
            'Energy per unit reduced', 'Downtime reduced', 'Defects reduced',
            'Waste reduced', 'Cost saved',
        ],
    },
    {
        'number': 3,
        'title': 'Mining Diesel Reduction Playbook',
        'applies_to': 'Mines, quarries, uranium, metals, coal, remote industrial sites.',
        'problem_signs': [
            'High diesel use', 'Long haul routes', 'Idle equipment', 'High maintenance cost',
            'Dust and emissions', 'Worker safety risk',
        ],
        'evidence_needed': [
            'Fuel logs', 'Vehicle fleet data', 'Route maps', 'Production tonnage',
            'Maintenance logs', 'Incident reports', 'Site photos',
        ],
        'recommended_actions': [
            'Optimise haul routes', 'Reduce idle time', 'Add telematics',
            'Electrify selected vehicles', 'Add renewable power for remote operations',
            'Improve maintenance planning', 'Monitor dust and safety risks',
        ],
        'maqasid_mizan_meaning': 'Reduce avoidable harm from extraction, protect workers, '
                                  'reduce waste of fuel and restore balance between economic '
                                  'benefit and environmental burden.',
        'mrv_metrics': [
            'Diesel saved', 'CO2 reduced', 'Cost saved', 'Incident risk reduced',
            'Productivity improved',
        ],
    },
    {
        'number': 4,
        'title': 'Water Recycling Playbook',
        'applies_to': 'Factories, mining, agriculture, food processing, industrial parks.',
        'problem_signs': [
            'High water withdrawal', 'Wastewater discharge', 'Leaks', 'Water stress region',
            'Poor monitoring', 'Contamination risk',
        ],
        'evidence_needed': [
            'Water bills', 'Flow meter data', 'Wastewater reports', 'Site maps',
            'Process diagrams', 'Photos of discharge/leaks', 'Water quality data',
        ],
        'recommended_actions': [
            'Install water meters', 'Detect leaks', 'Separate clean/dirty streams',
            'Add filtration/reuse', 'Treat wastewater', 'Create closed-loop systems',
            'Monitor water quality',
        ],
        'maqasid_mizan_meaning': 'Protect life-supporting resources, reduce harm to '
                                  'communities and ecosystems, restore balance in water use.',
        'mrv_metrics': [
            'Water saved', 'Wastewater reduced', 'Contamination risk reduced',
            'Cost saved', 'Water quality improved',
        ],
    },
    {
        'number': 5,
        'title': 'Smart Agriculture & Irrigation Playbook',
        'applies_to': 'Farms, greenhouses, irrigation systems, livestock, soil and water projects.',
        'problem_signs': [
            'Over-irrigation', 'Poor soil data', 'High fertiliser use', 'Crop losses',
            'Inefficient pumps', 'Weak cold storage', 'Water stress',
        ],
        'evidence_needed': [
            'Farm photos', 'Soil data', 'Irrigation logs', 'Water use', 'Crop yield',
            'Weather data', 'Pump data', 'Satellite/geospatial data',
        ],
        'recommended_actions': [
            'Soil sensors', 'Smart irrigation', 'Pump optimisation', 'Solar cold storage',
            'Greenhouse monitoring', 'Water reuse', 'Crop loss reduction',
        ],
        'maqasid_mizan_meaning': 'Protect food security, reduce waste, protect livelihoods '
                                  'and use water responsibly.',
        'mrv_metrics': [
            'Water saved', 'Crop loss reduced', 'Yield improved', 'Energy saved',
            'Farmer income improved',
        ],
    },
    {
        'number': 6,
        'title': 'Solar + Battery Industrial Playbook',
        'applies_to': 'Factories, mines, farms, warehouses, remote sites, industrial parks.',
        'problem_signs': [
            'High electricity cost', 'Unreliable grid', 'Diesel backup',
            'Peak demand charges', 'Strong solar potential', 'High daytime load',
        ],
        'evidence_needed': [
            'Electricity bills', 'Hourly load profile', 'Roof/land area',
            'Grid connection data', 'Backup generator data', 'Solar irradiation estimate',
            'Site photos',
        ],
        'recommended_actions': [
            'Measure load profile', 'Size solar system', 'Size battery',
            'Add demand response', 'Optimise peak shaving',
            'Integrate with monitoring dashboard', 'Compare grid/diesel/solar scenarios',
        ],
        'maqasid_mizan_meaning': 'Reduce fossil fuel dependency, reduce waste and create '
                                  'cleaner, more resilient energy.',
        'mrv_metrics': [
            'kWh generated', 'Grid energy reduced', 'Diesel reduced', 'CO2 reduced',
            'Cost saved', 'Reliability improved',
        ],
    },
    {
        'number': 7,
        'title': 'Waste Heat Recovery Playbook',
        'applies_to': 'Factories, furnaces, boilers, compressors, data centres, industrial heat systems.',
        'problem_signs': [
            'High exhaust heat', 'Hot surfaces', 'High cooling demand',
            'Wasted steam/heat', 'Nearby heat demand', 'Poor heat integration',
        ],
        'evidence_needed': [
            'Temperature readings', 'Process diagrams', 'Energy bills', 'Thermal photos',
            'Equipment data', 'Operating hours', 'Heat demand profile',
        ],
        'recommended_actions': [
            'Conduct heat audit', 'Identify recoverable heat sources',
            'Add heat exchangers', 'Reuse heat for process or district heating',
            'Insulate hot surfaces', 'Monitor recovered heat',
        ],
        'maqasid_mizan_meaning': 'Turn waste into benefit, reduce fuel demand and restore '
                                  'balance between energy input and useful output.',
        'mrv_metrics': [
            'Heat recovered', 'Fuel saved', 'CO2 reduced', 'Cost saved',
            'Useful heat delivered',
        ],
    },
    {
        'number': 8,
        'title': 'Compressed Air Optimisation Playbook',
        'applies_to': 'Factories, workshops, packaging, food processing, industrial lines.',
        'problem_signs': [
            'Compressor running constantly', 'Pressure drops', 'Audible leaks',
            'High electricity use', 'No leak monitoring', 'Oversized compressor',
        ],
        'evidence_needed': [
            'Compressor photos', 'Electricity data', 'Pressure data', 'Leak survey',
            'Maintenance logs', 'Production schedule',
        ],
        'recommended_actions': [
            'Leak detection', 'Pressure optimisation', 'Compressor maintenance',
            'Install monitoring', 'Resize compressor if needed', 'Recover compressor heat',
        ],
        'maqasid_mizan_meaning': 'Reduce hidden waste and protect wealth/resources through '
                                  'better measurement and maintenance.',
        'mrv_metrics': [
            'Electricity saved', 'Leak rate reduced', 'Compressor runtime reduced',
            'Cost saved',
        ],
    },
    {
        'number': 9,
        'title': 'District Heating Upgrade Playbook',
        'applies_to': 'City heat networks, boiler houses, public buildings, residential heating systems.',
        'problem_signs': [
            'High heat loss', 'Old pipes', 'Uneven heating', 'High complaints',
            'High fuel use', 'No building-level meters', 'Frequent failures',
        ],
        'evidence_needed': [
            'Heat network maps', 'Fuel data', 'Supply/return temperatures',
            'Building heat demand', 'Complaint logs', 'Pipe photos', 'Maintenance data',
        ],
        'recommended_actions': [
            'Heat metering', 'Pipe insulation', 'Leak detection', 'Pump optimisation',
            'Lower-temperature network study', 'Boiler upgrade',
            'Waste heat / heat pump integration',
        ],
        'maqasid_mizan_meaning': 'Protect families from cold and pollution, reduce waste and '
                                  'restore balance in public heating systems.',
        'mrv_metrics': [
            'Heat loss reduced', 'Fuel saved', 'Complaints reduced', 'CO2 reduced',
            'Cost saved', 'Comfort improved',
        ],
    },
    {
        'number': 10,
        'title': 'SMR Feasibility Playbook',
        'applies_to': 'Industrial clusters, remote mining regions, energy-intensive zones, '
                      'long-term baseload planning.',
        'problem_signs': [
            'Stable 24/7 high energy demand', 'Coal dependency', 'Grid reliability issues',
            'Industrial heat demand', 'Need for low-carbon baseload',
        ],
        'evidence_needed': [
            'Electricity demand', 'Peak load', 'Hourly load profile', 'Heat demand',
            'Grid data', 'Water availability', 'Site constraints', 'Regulatory readiness',
            'Public acceptance assessment', 'Nuclear safety and waste planning',
        ],
        'recommended_actions': [
            'Do not jump directly to SMR', 'Run efficiency-first pathway',
            'Compare renewables + battery', 'Assess grid upgrades',
            'Conduct nuclear regulatory readiness review',
            'Run safety and waste management feasibility',
            'Require independent expert review',
        ],
        'maqasid_mizan_meaning': 'SMR is only Maqasid-aligned if it reduces harm without '
                                  'creating a greater amanah burden through safety, waste, '
                                  'debt, security or community risk.',
        'mrv_metrics': [
            'Coal avoided', 'CO2 reduced', 'Reliability improved', 'Safety readiness',
            'Waste plan readiness', 'Public trust indicators',
        ],
    },
]

PLAYBOOK_STRUCTURE_FIELDS = [
    'Sector', 'Asset types', 'Problem signs', 'Data required', 'Visual evidence required',
    'Documents required', 'Recommended upgrades', 'Quick wins', 'Deep upgrade options',
    'CAPEX/OPEX logic', 'Finance route', 'Supplier checklist', 'No Harm Gate risks',
    'Maqasid meaning', 'Mizan meaning', 'MRV metrics', 'Human approval requirements',
]

PLAYBOOK_LIFECYCLE = [
    'Select asset',
    'Create Asset Passport',
    'Upload evidence',
    'Match best playbook',
    'Diagnose losses and harm',
    'Run simulation',
    'Estimate CAPEX/OPEX/payback',
    'Check Maqasid/Mizan and No Harm Gate',
    'Prepare finance/investor memo',
    'Implement',
    'Verify through MRV',
]

AMANAH_USES_PLAYBOOKS = (
    'Amanah Autopilot can run overnight, scan assets and evidence, match them to the right '
    'playbook, find quick wins, identify missing data and prepare morning recommendations '
    'for human approval.'
)

MICROSOFT_SUPPORTS_PLAYBOOKS = [
    {'component': 'Microsoft Fabric', 'role': 'Stores evidence and metrics.'},
    {'component': 'Azure Digital Twins', 'role': 'Maps assets.'},
    {'component': 'Azure IoT', 'role': 'Ingests sensor data.'},
    {'component': 'Azure AI / Agent Framework', 'role': 'Coordinates agents.'},
    {'component': 'Power BI', 'role': 'Visualises playbook KPIs.'},
    {'component': 'Responsible AI tools', 'role': 'Support explainability and governance.'},
]

SAFETY_PRINCIPLES = [
    'Playbooks are decision-support tools, not engineering certification.',
    'High-impact industrial, safety, nuclear, financial and environmental decisions require '
    'qualified expert review.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
    'SMR and other high-risk infrastructure options require independent regulatory, safety, '
    'environmental and community review.',
    'If evidence is incomplete, the system must show "Needs verification".',
]

CTA_BUTTONS = [
    {'label': 'Explore Playbooks', 'anchor': '#playbooks'},
    {'label': 'Match My Asset to a Playbook', 'url_name': 'asset_passport:overview'},
    {'label': 'Generate Modernisation Plan', 'url_name': 'legacy_safe:ask'},
    {'label': 'Run What-If Simulation', 'anchor': '#playbook-lifecycle'},
    {'label': 'Prepare Finance Memo', 'url_name': 'leads:request_review'},
    {'label': 'Start MRV Tracking', 'url_name': 'impact_mrv_layer:overview'},
]


def overview(request):
    return render(request, 'industrial_playbook_library/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_formula': CORE_FORMULA,
        'playbooks': PLAYBOOKS,
        'playbook_structure_fields': PLAYBOOK_STRUCTURE_FIELDS,
        'playbook_lifecycle': PLAYBOOK_LIFECYCLE,
        'amanah_uses_playbooks': AMANAH_USES_PLAYBOOKS,
        'microsoft_supports_playbooks': MICROSOFT_SUPPORTS_PLAYBOOKS,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })
