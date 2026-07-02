from django.shortcuts import render

# Connected EcoIQ modules — the Revenue Engine packages what these modules produce into paid products
CONNECTED_MODULES = [
    {'name': 'Asset Passport', 'role': 'Is sold directly as a paid product and underlies most other paid packs.'},
    {'name': 'Impact MRV Layer', 'role': 'Powers the paid MRV Verification Pack and sponsor impact reporting.'},
    {'name': 'Supplier & Funding Marketplace', 'role': 'Generates marketplace matching and success-fee revenue.'},
    {'name': 'Institutional Finance Engine', 'role': 'Powers the paid Investor Readiness Memo.'},
    {'name': 'Command Centre', 'role': 'Is bundled into the Enterprise Subscription tier.'},
    {'name': 'Data Room & Evidence Vault', 'role': 'Is bundled into Institutional and Enterprise tiers as due diligence storage.'},
    {'name': 'Executive Briefing & Board Pack Generator', 'role': 'Powers the paid Board Pack / Executive Briefing product.'},
    {'name': 'Public Trust & Impact Portal', 'role': 'Supplies the approved public impact story used in Sponsor Impact Packs.'},
    {'name': 'Portfolio & Country Transition Atlas', 'role': 'Powers the paid Country Transition Atlas product.'},
    {'name': 'API & Integration Layer', 'role': 'Underlies paid API access for enterprise partners.'},
    {'name': 'Microsoft Ecosystem Core Stack', 'role': 'Underlies Microsoft-based enterprise pilot monetisation.'},
]

CORE_PURPOSE = 'Make EcoIQ commercially scalable and investor-ready.'

REVENUE_PRODUCTS = [
    {
        'number': 1,
        'title': 'Free EcoIQ Scan',
        'price': '£0',
        'audience': 'Companies, municipalities, factories, farms, boiler houses, SMEs, public buildings.',
        'includes': [
            'Basic public/company scan', 'Preliminary risk signals', 'Basic EcoIQ score',
            'Missing data checklist', 'Recommended next step',
        ],
        'purpose': 'Lead generation and qualification.',
        'note': '',
        'cta': 'Start Free Scan',
    },
    {
        'number': 2,
        'title': 'Asset Passport',
        'price': '£190–£490 per asset',
        'audience': 'Industrial sites, boiler houses, factories, public buildings, farms, mines.',
        'includes': [
            'Asset profile', 'Evidence upload', 'Visual risk notes', 'Baseline fields',
            'Missing data checklist', 'Recommended playbook', 'Maqasid/Mizan initial score',
        ],
        'purpose': 'Turn one asset into a structured modernisation record.',
        'note': '',
        'cta': 'Create Asset Passport',
    },
    {
        'number': 3,
        'title': 'Mobile Inspection Pack',
        'price': '£290–£790 per inspection',
        'audience': 'Field teams, engineers, municipalities, suppliers, project owners.',
        'includes': [
            'Photo/video inspection', 'Meter reading capture', 'AI visual diagnosis',
            'Field report', 'Asset Passport update', 'Recommended playbook',
            'MRV baseline checklist',
        ],
        'purpose': '',
        'note': '',
        'cta': 'Book Mobile Inspection',
    },
    {
        'number': 4,
        'title': 'MRV Verification Pack',
        'price': '£490–£1,500 per project',
        'audience': 'CSR sponsors, investors, governments, donors, project owners.',
        'includes': [
            'Baseline evidence review', 'After-data review', 'Before/after comparison',
            'Evidence quality score', 'Impact report', 'Public summary readiness',
            '"Needs verification" flags',
        ],
        'purpose': '',
        'note': '',
        'cta': 'Generate MRV Pack',
    },
    {
        'number': 5,
        'title': 'Investor Readiness Memo',
        'price': '£990–£2,500 per project',
        'audience': 'Project owners, startups, municipalities, suppliers, funders.',
        'includes': [
            'Finance model', 'CAPEX/OPEX/payback', 'Funding route', 'Risk register',
            'Maqasid/Mizan impact', 'No Harm Gate', 'Investor memo', 'Data room checklist',
        ],
        'purpose': '',
        'note': '',
        'cta': 'Generate Investor Memo',
    },
    {
        'number': 6,
        'title': 'Board Pack / Executive Briefing',
        'price': '£1,500–£5,000 per pack',
        'audience': 'Boards, investors, akimats, government partners, CSR sponsors, development banks.',
        'includes': [
            'Executive summary', 'Decision request', 'Options comparison',
            'Financial model', 'Impact model', 'Risks', 'Evidence links', 'MRV plan',
            'Approval checklist',
        ],
        'purpose': '',
        'note': '',
        'cta': 'Create Board Pack',
    },
    {
        'number': 7,
        'title': 'Supplier & Funding Match',
        'price': 'Fixed fee per match, success fee where appropriate, subscription for '
                 'suppliers/funders, or enterprise marketplace access',
        'audience': 'Suppliers, installers, funders, project owners, investors.',
        'includes': [
            'Supplier shortlist', 'Funding route shortlist', 'RFQ pack', 'Funding memo',
            'Outreach draft', 'Due diligence checklist',
        ],
        'purpose': '',
        'note': 'Do not imply automatic endorsement of suppliers or funders.',
        'cta': 'Match Suppliers & Funding',
    },
    {
        'number': 8,
        'title': 'Country Transition Atlas',
        'price': '£5,000–£25,000 per country/region brief',
        'audience': 'Development banks, government partners, sovereign funds, investors, municipalities.',
        'includes': [
            'Country map', 'Sector opportunity analysis', 'Finance-ready pipeline',
            'Highest-harm assets', 'Highest-impact opportunities', 'CAPEX pipeline',
            'Funding gap', 'Country transition brief',
        ],
        'purpose': '',
        'note': '',
        'cta': 'Generate Country Atlas',
    },
    {
        'number': 9,
        'title': 'Enterprise Subscription',
        'price': '£10,000–£100,000+ per year depending on scope',
        'audience': 'Industrial groups, municipalities, sovereign funds, development banks, enterprise partners.',
        'includes': [
            'Command Centre', 'Portfolio dashboard', 'Multiple Asset Passports',
            'MRV tracking', 'Data room', 'API access', 'Microsoft integration',
            'Expert review workflows', 'Custom reports',
        ],
        'purpose': '',
        'note': '',
        'cta': 'Request Enterprise Pilot',
    },
    {
        'number': 10,
        'title': 'Sponsor Impact Pack',
        'price': '£490–£2,500 per sponsor/project pack',
        'audience': 'CSR sponsors, donors, sadaqah jariyah sponsors, charitable funds.',
        'includes': [
            'Sponsor-ready project summary', 'Before/after evidence', 'MRV plan',
            'Public impact story', 'Sponsor report', 'Maqasid/Mizan meaning',
            'Approved public summary',
        ],
        'purpose': '',
        'note': '',
        'cta': 'Create Sponsor Impact Pack',
    },
]

PRICING_TIERS = [
    {
        'title': 'Starter',
        'description': 'For first scans and small projects.',
        'includes': ['Free Scan', 'Asset Passport', 'Mobile Inspection Pack'],
    },
    {
        'title': 'Growth',
        'description': 'For project owners and suppliers.',
        'includes': ['MRV Pack', 'Investor Memo', 'Supplier/Funding Match', 'Board Pack'],
    },
    {
        'title': 'Institutional',
        'description': 'For investors, governments and enterprise.',
        'includes': [
            'Country Atlas', 'Command Centre', 'Data Room', 'API access',
            'Enterprise Subscription', 'Executive Briefing packs',
        ],
    },
    {
        'title': 'Impact',
        'description': 'For CSR, donors and Islamic finance.',
        'includes': [
            'Sponsor Impact Pack', 'Public Trust Portal summary', 'MRV reporting',
            'Clean heating project pack', 'Maqasid/Mizan summary',
        ],
    },
]

REVENUE_MODEL_CARDS = [
    {
        'number': 1,
        'title': 'SaaS Subscription',
        'description': 'Recurring revenue from enterprise access to Command Centre, Data '
                        'Room, Atlas and API.',
    },
    {
        'number': 2,
        'title': 'Project-Based Reports',
        'description': 'One-off fees for Asset Passport, MRV Pack, Investor Memo, Board '
                        'Pack and Country Briefs.',
    },
    {
        'number': 3,
        'title': 'Marketplace Revenue',
        'description': 'Supplier/funder matching fees, subscription access or '
                        'success-based fees where legally appropriate.',
    },
    {
        'number': 4,
        'title': 'Enterprise Pilots',
        'description': 'Paid pilots for municipalities, industrial groups, sovereign '
                        'funds, development banks and Microsoft ecosystem partners.',
    },
    {
        'number': 5,
        'title': 'Sponsor / CSR Packs',
        'description': 'Paid impact reporting for sponsor-backed clean heating, public '
                        'building and community projects.',
    },
    {
        'number': 6,
        'title': 'API / Data Access',
        'description': 'Paid API access for approved partners, dashboards, investors and '
                        'enterprise systems.',
    },
]

CONVERSION_FUNNEL = [
    'Free Scan', 'Asset Passport', 'Mobile Inspection', 'Playbook Diagnosis',
    'Finance Memo', 'Supplier/Funding Match', 'MRV Pack', 'Public Impact Story',
    'Enterprise Subscription',
]

CUSTOMER_JOURNEYS = [
    {
        'title': 'Factory Owner Journey',
        'steps': [
            'Starts with Free Scan.', 'Buys Asset Passport and Mobile Inspection.',
            'Then buys Investor Memo and Supplier Match.',
            'Later subscribes to Command Centre.',
        ],
    },
    {
        'title': 'Municipality / Akimat Journey',
        'steps': [
            'Starts with Country Atlas.', 'Buys clean heating opportunity pack.',
            'Runs pilot Asset Passports.',
            'Uses MRV and Public Trust Portal for reporting.',
            'Later upgrades to enterprise subscription.',
        ],
    },
    {
        'title': 'CSR Sponsor Journey',
        'steps': [
            'Chooses Village Clean Heating project.',
            'Pays for Sponsor Impact Pack.',
            'Receives MRV report and approved public story.',
            'Can fund more projects.',
        ],
    },
    {
        'title': 'Supplier Journey',
        'steps': [
            'Subscribes to marketplace access.',
            'Receives approved RFQ opportunities.',
            'Uploads quotes and implementation evidence.',
            'Builds verified project history.',
        ],
    },
    {
        'title': 'Investor Journey',
        'steps': [
            'Buys Investor Portfolio Brief.', 'Accesses Data Room.',
            'Reviews finance-ready projects.', 'Tracks MRV verified impact.',
        ],
    },
]

REVENUE_DASHBOARD_CARDS = [
    'Monthly recurring revenue', 'Project report revenue', 'Enterprise pilot revenue',
    'Marketplace revenue', 'Sponsor pack revenue', 'API revenue', 'Number of free scans',
    'Scan-to-passport conversion', 'Passport-to-memo conversion',
    'Memo-to-funding conversion', 'MRV pack conversion', 'Enterprise pipeline value',
    'Average revenue per project', 'Country atlas pipeline',
    'Supplier marketplace pipeline',
]

COMMERCIAL_READINESS_FIELDS = [
    'Product sold', 'Price band', 'Customer type', 'Project stage', 'Revenue status',
    'Invoice status', 'Payment status', 'Renewal potential', 'Upsell opportunity',
    'Data room status', 'MRV status', 'Public impact status', 'Account owner',
    'Next commercial action',
]

PRICING_GUARDRAILS = [
    'Prices are indicative and can vary by scope, country, complexity and evidence quality.',
    'High-impact engineering, finance, legal, environmental or Islamic finance work may '
    'require external experts and separate fees.',
    'EcoIQ outputs are decision-support, not investment advice or certification.',
    'Supplier/funder marketplace fees must be transparent.',
    'Success fees must comply with legal and regulatory requirements.',
    'Islamic finance suitability requires qualified review.',
    'Public impact claims require MRV-backed evidence.',
]

MICROSOFT_MONETISATION_ITEMS = [
    'Enterprise pilots on Microsoft stack', 'Power BI dashboard setup',
    'Teams approval workflows', 'SharePoint evidence room setup',
    'Azure Digital Twins asset mapping', 'Microsoft Fabric data integration',
    'API integration support', 'Custom enterprise reporting',
    'Managed MRV dashboards',
]

AMANAH_REVENUE_SUPPORT_ITEMS = [
    'Free scans ready for upsell', 'Assets missing passports',
    'Projects ready for MRV packs', 'Finance-ready projects needing investor memos',
    'Sponsor-ready clean heating projects', 'Enterprise accounts with renewal potential',
    'Country atlas opportunities', 'Marketplace revenue opportunities',
]
AMANAH_MORNING_BRIEFING_EXAMPLE = (
    '12 free scans are ready for Asset Passport upsell, 4 projects are ready for '
    'Investor Memo, 3 clean heating projects are sponsor-ready and 1 municipality is '
    'ready for a Country Atlas proposal.'
)

NO_HARM_GATE_REVENUE_ITEMS = [
    'Is the customer need real?',
    'Are claims evidence-backed?',
    'Are prices transparent?',
    'Is the customer vulnerable?',
    'Could the finance structure create unfair burden?',
    'Are sponsor claims verified?',
    'Are public impact claims MRV-backed?',
    'Is Islamic finance wording reviewed?',
    'Are marketplace relationships disclosed?',
    'Is human approval required before external outreach?',
]

SAFETY_PRINCIPLES = [
    'EcoIQ pricing and product packaging are commercial guidance, not financial advice.',
    'Final pricing depends on project scope, data quality, country, complexity and '
    'required expert review.',
    'Investment, legal, engineering, environmental and Islamic finance decisions require '
    'qualified review.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
    'Public claims must be MRV-supported and approved before publication.',
    'EcoIQ must not overclaim guaranteed savings, funding or impact.',
]

CTA_BUTTONS = [
    {'label': 'Start Free Scan', 'anchor': '#product-1'},
    {'label': 'Create Asset Passport', 'anchor': '#product-2'},
    {'label': 'Book Mobile Inspection', 'anchor': '#product-3'},
    {'label': 'Generate MRV Pack', 'anchor': '#product-4'},
    {'label': 'Generate Investor Memo', 'anchor': '#product-5'},
    {'label': 'Create Board Pack', 'anchor': '#product-6'},
    {'label': 'Match Suppliers & Funding', 'anchor': '#product-7'},
    {'label': 'Request Country Atlas', 'anchor': '#product-8'},
    {'label': 'Request Enterprise Pilot', 'anchor': '#product-9'},
    {'label': 'Create Sponsor Impact Pack', 'anchor': '#product-10'},
]


def overview(request):
    return render(request, 'revenue_pricing_engine/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_purpose': CORE_PURPOSE,
        'revenue_products': REVENUE_PRODUCTS,
        'pricing_tiers': PRICING_TIERS,
        'revenue_model_cards': REVENUE_MODEL_CARDS,
        'conversion_funnel': CONVERSION_FUNNEL,
        'customer_journeys': CUSTOMER_JOURNEYS,
        'revenue_dashboard_cards': REVENUE_DASHBOARD_CARDS,
        'commercial_readiness_fields': COMMERCIAL_READINESS_FIELDS,
        'pricing_guardrails': PRICING_GUARDRAILS,
        'microsoft_monetisation_items': MICROSOFT_MONETISATION_ITEMS,
        'amanah_revenue_support_items': AMANAH_REVENUE_SUPPORT_ITEMS,
        'amanah_morning_briefing_example': AMANAH_MORNING_BRIEFING_EXAMPLE,
        'no_harm_gate_revenue_items': NO_HARM_GATE_REVENUE_ITEMS,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })
