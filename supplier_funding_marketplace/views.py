from django.shortcuts import render

# Connected EcoIQ modules — the Marketplace turns diagnosis into a financed, delivered project
CONNECTED_MODULES = [
    {'name': 'Asset Passport', 'role': 'Supplies the asset record a marketplace project is built from.'},
    {'name': 'Industrial Playbook Library', 'role': 'Supplies the recommended pathway used to select a solution type.'},
    {'name': 'Impact MRV Layer', 'role': 'Verifies before/after results once implementation is complete.'},
    {'name': 'Amanah Autopilot', 'role': 'Runs overnight matching of assets to suppliers and funders, and prepares a morning approval list.'},
    {'name': 'Omnimodal Evidence Panel', 'role': 'Supplies the evidence that qualifies a project for supplier and funding matching.'},
    {'name': 'Microsoft Ecosystem Core Stack', 'role': 'Provides the agent, data and dashboard building blocks a production marketplace would run on.'},
    {'name': 'Institutional Finance Engine', 'role': 'Structures the funding routes offered to a project.'},
    {'name': 'Maqasid/Mizan ethical scoring', 'role': 'Scores whether a supplier and funding match actually protects health, wealth and resources.'},
    {'name': 'No Harm Gate', 'role': 'Blocks a project from moving to implementation until harm and debt-burden risks are checked.'},
    {'name': 'Digital Twins', 'role': 'Model the asset so a proposed solution can be simulated before a supplier is contacted.'},
    {'name': 'Power BI dashboards', 'role': 'Visualise the supplier and funding pipeline.'},
]

CORE_PURPOSE = 'Turn EcoIQ recommendations into executable, financed projects.'

MAIN_WORKFLOW = [
    {
        'number': 1,
        'title': 'Asset diagnosed',
        'description': 'EcoIQ identifies a problem from photos, documents, sensor data or reports.',
        'items': [],
    },
    {
        'number': 2,
        'title': 'Playbook matched',
        'description': 'EcoIQ matches the asset to the right industrial playbook.',
        'items': [],
    },
    {
        'number': 3,
        'title': 'Solution type selected',
        'description': 'The system identifies the needed upgrade:',
        'items': [
            'Smart meters', 'Insulation', 'Boiler servicing', 'Heat pump', 'Electric boiler',
            'Solar + battery', 'Waste heat recovery', 'Water recycling', 'Sensors',
            'Predictive maintenance', 'Compressed air optimisation', 'District heating upgrade',
            'SMR feasibility review',
        ],
    },
    {
        'number': 4,
        'title': 'Supplier shortlist generated',
        'description': 'EcoIQ finds or ranks suppliers based on:',
        'items': [
            'Technology fit', 'Location', 'Certifications', 'Warranty', 'Service coverage',
            'Estimated cost', 'Installation capacity', 'Experience', 'Risk level', 'Ethical fit',
        ],
    },
    {
        'number': 5,
        'title': 'Funding route matched',
        'description': 'EcoIQ suggests funding options:',
        'items': [
            'Grant', 'CSR sponsor', 'Islamic finance', 'Waqf', 'Sadaqah jariyah',
            'Ijara / leasing', 'Sukuk', 'Green loan', 'Development bank',
            'Municipal co-finance', 'Impact investor', 'Carbon / climate finance where appropriate',
        ],
    },
    {
        'number': 6,
        'title': 'Finance memo prepared',
        'description': 'EcoIQ prepares:',
        'items': [
            'CAPEX', 'OPEX savings', 'Payback', 'Impact estimate', 'Evidence quality',
            'Maqasid/Mizan score', 'Risk summary', 'Supplier comparison', 'Funding request',
        ],
    },
    {
        'number': 7,
        'title': 'Human approval',
        'description': 'User reviews and approves before contacting suppliers or funders.',
        'items': [],
    },
    {
        'number': 8,
        'title': 'Implementation tracked',
        'description': 'Supplier tasks, quotes, invoices, installation status and project milestones are tracked.',
        'items': [],
    },
    {
        'number': 9,
        'title': 'Impact verified',
        'description': 'Impact MRV Layer verifies before/after results.',
        'items': [],
    },
]

PARTICIPANT_CARDS = [
    {
        'name': 'Suppliers',
        'applies_to': 'Equipment manufacturers, installers, energy service companies, sensor '
                      'providers, insulation contractors, boiler engineers, heat pump suppliers, '
                      'solar/battery installers, water treatment firms.',
    },
    {
        'name': 'Funders',
        'applies_to': 'Impact investors, Islamic finance providers, CSR sponsors, climate funds, '
                      'development banks, municipalities, philanthropic donors, green finance '
                      'institutions.',
    },
    {
        'name': 'Project Owners',
        'applies_to': 'Factories, mines, farms, municipalities, schools, hospitals, housing '
                      'communities, boiler houses and industrial parks.',
    },
    {
        'name': 'Verifiers',
        'applies_to': 'Engineers, auditors, environmental consultants, safety inspectors, '
                      'Islamic finance advisors, Maqasid/Mizan reviewers.',
    },
]

SUPPLIER_MATCHING_FIELDS = [
    'Supplier name', 'Solution category', 'Country / region', 'Technologies offered',
    'Certifications', 'Warranty', 'Service coverage', 'Typical project size',
    'Estimated price range', 'Installation timeline', 'Maintenance support',
    'Evidence required', 'Risk notes', 'Ethical / No Harm notes',
    'Verified project history', 'Contact status',
]

FUNDING_MATCHING_FIELDS = [
    'Funder name', 'Funding type', 'Eligible sectors', 'Eligible countries', 'Ticket size',
    'Grant / loan / lease / CSR / Islamic finance', 'Required documents',
    'Impact metrics required', 'Maqasid/Mizan relevance', 'Application deadline',
    'Probability estimate', 'Next action',
]

SUPPLIER_FIT_SCORE = [
    'Technical fit', 'Local availability', 'Certification strength', 'Cost fit',
    'Delivery speed', 'Maintenance support', 'Evidence quality', 'No Harm risk',
]

FUNDING_FIT_SCORE = [
    'Sector fit', 'Geography fit', 'Ticket size fit', 'Impact fit',
    'Documentation readiness', 'Maqasid/Mizan alignment', 'Risk level', 'Deadline urgency',
]

EXAMPLE_CARDS = [
    {
        'project': 'Boiler House #3 Modernisation',
        'recommended_solution': [
            'Pipe insulation', 'Smart heat meters', 'Boiler servicing', 'Efficiency controls',
            'Later: heat pump / electric boiler assessment',
        ],
        'supplier_shortlist': [
            'Insulation contractor', 'Smart meter provider', 'Boiler service engineer',
            'Heat pump feasibility consultant',
        ],
        'funding_routes': [
            'Municipal clean air programme', 'CSR sponsor', 'Islamic sadaqah jariyah fund',
            'Equipment leasing / ijara', 'Green efficiency grant',
        ],
        'ecoiq_output': [
            'Supplier comparison', 'Funding memo', 'Implementation timeline',
            'MRV evidence checklist', 'Maqasid/Mizan impact summary',
        ],
        'maqasid_mizan_meaning': '',
    },
    {
        'project': 'Factory Compressed Air Optimisation',
        'recommended_solution': [
            'Leak detection', 'Pressure optimisation', 'Compressor monitoring',
            'Heat recovery from compressor',
        ],
        'supplier_shortlist': [
            'Compressed air audit provider', 'Sensor provider', 'Maintenance contractor',
            'Energy efficiency consultant',
        ],
        'funding_routes': [
            'Energy efficiency grant', 'Equipment leasing', 'Internal payback-funded investment',
            'Green loan',
        ],
        'ecoiq_output': [],
        'maqasid_mizan_meaning': '',
    },
    {
        'project': 'Village Clean Heating Transition',
        'recommended_solution': [
            'Replace coal stove', 'Improve insulation', 'Install clean heating option',
            'Monitor indoor comfort and fuel reduction',
        ],
        'supplier_shortlist': [],
        'funding_routes': [
            'Sadaqah jariyah sponsor', 'CSR sponsor', 'Local government co-finance',
            'Islamic charitable fund', 'Climate adaptation grant',
        ],
        'ecoiq_output': [],
        'maqasid_mizan_meaning': 'Protect life and health, reduce harm, reduce waste, restore '
                                  'balance in household heating.',
    },
]

MARKETPLACE_WORKFLOW = [
    'Asset Passport', 'Playbook Match', 'Supplier Match', 'Funding Match', 'Finance Memo',
    'Human Approval', 'Implementation', 'Impact MRV', 'Verified Impact Report',
]

AMANAH_INTEGRATION_INTRO = 'Amanah Autopilot can run overnight and:'
AMANAH_INTEGRATION_ITEMS = [
    'Scan new projects', 'Match assets to suppliers', 'Find relevant funding opportunities',
    'Prepare draft emails', 'Identify missing documents', 'Prepare morning approval list',
]
AMANAH_MORNING_BRIEFING_EXAMPLE = (
    '3 suppliers shortlisted, 2 funding routes matched, 1 investor memo ready, '
    '4 missing documents detected.'
)

MICROSOFT_INTEGRATION = [
    {'component': 'Microsoft Fabric', 'role': 'Supplier/funder/project data.'},
    {'component': 'Power BI', 'role': 'Pipeline dashboards.'},
    {'component': 'Azure AI / Agent Framework', 'role': 'Matching agents.'},
    {'component': 'Azure Digital Twins', 'role': 'Asset relationships.'},
    {'component': 'Power Automate', 'role': 'Supplier/funder outreach workflows.'},
    {'component': 'Teams', 'role': 'Approvals and notifications.'},
    {'component': 'SharePoint', 'role': 'Documents and proposals.'},
    {'component': 'Dynamics 365', 'role': 'CRM-style opportunity tracking.'},
]

SAFETY_PRINCIPLES = [
    'EcoIQ does not automatically endorse suppliers or funders.',
    'Supplier and funding matches are decision-support suggestions and require human due diligence.',
    'Financial structures require qualified legal, tax, financial and Shariah review where relevant.',
    'High-impact industrial work requires qualified engineering review.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
    'No supplier or funder should be contacted automatically without human approval.',
    'The system must show evidence quality, missing documents and risk notes.',
]

NO_HARM_GATE_MARKETPLACE = [
    'Is the supplier qualified?',
    'Is the technology appropriate?',
    'Is financing fair and transparent?',
    'Could the project create debt burden?',
    'Could workers or communities be harmed?',
    'Is environmental impact properly checked?',
    'Is there enough evidence for the claim?',
    'Is human approval recorded?',
]

CTA_BUTTONS = [
    {'label': 'Find Suppliers', 'anchor': '#participants'},
    {'label': 'Match Funding', 'anchor': '#funding-matching'},
    {'label': 'Generate Supplier Brief', 'url_name': 'legacy_safe:ask'},
    {'label': 'Prepare Funding Memo', 'url_name': 'leads:request_review'},
    {'label': 'Create Outreach Email', 'anchor': '#amanah-integration'},
    {'label': 'Start Implementation', 'url_name': 'asset_passport:overview'},
    {'label': 'Verify Impact', 'url_name': 'impact_mrv_layer:overview'},
]


def overview(request):
    return render(request, 'supplier_funding_marketplace/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_purpose': CORE_PURPOSE,
        'main_workflow': MAIN_WORKFLOW,
        'participant_cards': PARTICIPANT_CARDS,
        'supplier_matching_fields': SUPPLIER_MATCHING_FIELDS,
        'funding_matching_fields': FUNDING_MATCHING_FIELDS,
        'supplier_fit_score': SUPPLIER_FIT_SCORE,
        'funding_fit_score': FUNDING_FIT_SCORE,
        'example_cards': EXAMPLE_CARDS,
        'marketplace_workflow': MARKETPLACE_WORKFLOW,
        'amanah_integration_intro': AMANAH_INTEGRATION_INTRO,
        'amanah_integration_items': AMANAH_INTEGRATION_ITEMS,
        'amanah_morning_briefing_example': AMANAH_MORNING_BRIEFING_EXAMPLE,
        'microsoft_integration': MICROSOFT_INTEGRATION,
        'safety_principles': SAFETY_PRINCIPLES,
        'no_harm_gate_marketplace': NO_HARM_GATE_MARKETPLACE,
        'cta_buttons': CTA_BUTTONS,
    })
