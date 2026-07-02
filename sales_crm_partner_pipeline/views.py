from django.shortcuts import render

# Connected EcoIQ modules — the CRM turns product interest into paid pilots and accounts
CONNECTED_MODULES = [
    {'name': 'Revenue & Pricing Engine', 'role': 'Supplies the product catalogue and pricing sold through this pipeline.'},
    {'name': 'Supplier & Funding Marketplace', 'role': 'Receives qualified supplier and funder leads from the CRM.'},
    {'name': 'Executive Briefing & Board Pack Generator', 'role': 'Generates the proposal packs sent at the Proposal Sent stage.'},
    {'name': 'Data Room & Evidence Vault', 'role': 'Stores the proposal, evidence and approval records linked to each opportunity.'},
    {'name': 'Command Centre', 'role': 'Surfaces which projects are commercially active and pilot-ready.'},
    {'name': 'Portfolio & Country Transition Atlas', 'role': 'Supplies the country briefs sold to government and investor leads.'},
    {'name': 'Public Trust & Impact Portal', 'role': 'Supplies the approved impact story used in sponsor outreach.'},
    {'name': 'Institutional Finance Engine', 'role': 'Supplies the finance model behind investor and funder opportunities.'},
    {'name': 'API & Integration Layer', 'role': 'Exposes CRM records to external Dynamics/Teams systems.'},
    {'name': 'Microsoft Ecosystem Core Stack', 'role': 'Underlies the Microsoft ecosystem partner pipeline.'},
    {'name': 'Teams', 'role': 'Delivers follow-up reminders and approval requests.'},
    {'name': 'Dynamics 365', 'role': 'Can host the underlying CRM records and opportunity stages.'},
    {'name': 'SharePoint', 'role': 'Stores proposal and evidence packs shared with prospects.'},
    {'name': 'Power BI', 'role': 'Visualises the sales and partner pipeline dashboards.'},
]

CORE_PURPOSE = 'Turn EcoIQ product interest into paid pilots, partnerships, contracts and long-term accounts.'

PIPELINE_STAGES = [
    {
        'number': 1,
        'title': 'New Lead',
        'description': 'A person, company, municipality, funder, supplier or sponsor shows interest.',
        'items': [],
    },
    {
        'number': 2,
        'title': 'Qualified',
        'description': 'EcoIQ confirms sector, budget, country, urgency, asset type and product fit.',
        'items': [],
    },
    {
        'number': 3,
        'title': 'Discovery Call',
        'description': 'Meeting scheduled to understand pain points, assets, evidence and commercial need.',
        'items': [],
    },
    {
        'number': 4,
        'title': 'Free Scan / Demo',
        'description': 'EcoIQ runs basic scan or demo using public data, sample asset or uploaded evidence.',
        'items': [],
    },
    {
        'number': 5,
        'title': 'Proposal Sent',
        'description': 'EcoIQ sends proposal:',
        'items': [
            'Asset Passport', 'MRV Pack', 'Investor Memo', 'Board Pack', 'Country Atlas',
            'Enterprise Pilot', 'Sponsor Impact Pack', 'Supplier Marketplace access',
        ],
    },
    {
        'number': 6,
        'title': 'Pilot Negotiation',
        'description': 'Scope, price, timeline, data access, approvals and expert review are discussed.',
        'items': [],
    },
    {
        'number': 7,
        'title': 'Contract / LOI',
        'description': 'Commercial agreement, pilot letter, LOI, MOU or sponsor agreement is signed.',
        'items': [],
    },
    {
        'number': 8,
        'title': 'Implementation',
        'description': 'Asset Passports, inspections, MRV, finance memo, supplier matching and reporting begin.',
        'items': [],
    },
    {
        'number': 9,
        'title': 'Expansion',
        'description': 'More sites, regions, assets, sponsors or enterprise modules are added.',
        'items': [],
    },
    {
        'number': 10,
        'title': 'Renewal / Long-Term Account',
        'description': 'Customer renews subscription, country atlas, MRV reporting or enterprise access.',
        'items': [],
    },
]

CRM_CONTACT_TYPES = [
    'Industrial company', 'Factory owner', 'Mine / quarry operator',
    'Municipality / akimat', 'Government agency', 'Sovereign fund',
    'Development bank', 'Impact investor', 'Islamic finance provider', 'CSR sponsor',
    'Charity / sadaqah jariyah sponsor', 'Supplier / installer',
    'Microsoft ecosystem partner', 'University / research partner',
    'NGO / community organisation', 'Verifier / consultant',
]

OPPORTUNITY_FIELDS = [
    'Organisation name', 'Contact person', 'Country', 'Region', 'Sector',
    'Organisation type', 'Opportunity type', 'Product interest', 'Estimated deal value',
    'Probability', 'Stage', 'Next action', 'Owner', 'Last contact date',
    'Next follow-up date', 'Evidence received', 'Proposal status', 'Data room status',
    'Decision maker', 'Blockers', 'Partner fit', 'Maqasid/Mizan relevance',
    'No Harm / governance notes',
]

PRODUCT_OPPORTUNITY_TYPES = [
    'Free EcoIQ Scan', 'Asset Passport', 'Mobile Inspection Pack',
    'MRV Verification Pack', 'Investor Readiness Memo',
    'Board Pack / Executive Briefing', 'Supplier & Funding Match',
    'Country Transition Atlas', 'Enterprise Subscription', 'Sponsor Impact Pack',
    'Public Trust Portal reporting', 'API / Microsoft integration pilot',
]

PARTNER_PIPELINE_VIEWS = [
    {
        'number': 1,
        'title': 'Customer Pipeline',
        'description': 'Tracks companies, municipalities, project owners and enterprise accounts.',
    },
    {
        'number': 2,
        'title': 'Investor / Funder Pipeline',
        'description': 'Tracks impact investors, development banks, CSR sponsors, Islamic '
                        'finance providers and grant funders.',
    },
    {
        'number': 3,
        'title': 'Supplier Pipeline',
        'description': 'Tracks equipment providers, installers, ESCOs, engineering firms '
                        'and consultants.',
    },
    {
        'number': 4,
        'title': 'Government / Akimat Pipeline',
        'description': 'Tracks public sector partnerships, city pilots, clean heating '
                        'programmes and regional atlas opportunities.',
    },
    {
        'number': 5,
        'title': 'Microsoft / Enterprise Partner Pipeline',
        'description': 'Tracks Microsoft ecosystem pilots, Power BI/Teams/Fabric '
                        'integration opportunities and enterprise co-sell readiness.',
    },
    {
        'number': 6,
        'title': 'Sponsor / Donor Pipeline',
        'description': 'Tracks sadaqah jariyah sponsors, CSR sponsors, charitable funds '
                        'and community impact opportunities.',
    },
]

PIPELINE_DASHBOARD_CARDS = [
    'Total leads', 'Qualified opportunities', 'Proposals sent',
    'Pilots in negotiation', 'LOIs signed', 'Contracts won', 'Active pilots',
    'Renewal opportunities', 'Total pipeline value', 'Weighted pipeline value',
    'Enterprise pipeline value', 'Sponsor pipeline value', 'Supplier pipeline value',
    'Investor/funder pipeline value', 'Average deal size', 'Conversion rate',
    'Next follow-ups due', 'Stalled opportunities',
    'High Maqasid/Mizan impact opportunities',
]

KANBAN_COLUMNS = [
    'New Lead', 'Qualified', 'Discovery Call', 'Free Scan / Demo', 'Proposal Sent',
    'Pilot Negotiation', 'Contract / LOI', 'Implementation', 'Expansion', 'Renewal',
]
KANBAN_CARD_SHOWS = [
    'Organisation', 'Country', 'Sector', 'Opportunity type', 'Value band', 'Probability',
    'Owner', 'Next action', 'Days in stage', 'Risk/blocker',
]

SCORING_LOGIC = [
    {
        'title': 'Lead Fit Score',
        'includes': [
            'Sector fit', 'Country fit', 'Asset fit', 'Urgency', 'Budget potential',
            'Data availability', 'Decision-maker access', 'Maqasid/Mizan impact potential',
            'Revenue potential',
        ],
    },
    {
        'title': 'Partner Fit Score',
        'includes': [
            'Technology relevance', 'Delivery capacity', 'Geographic coverage',
            'Credibility', 'Ethical fit', 'Evidence quality', 'No Harm risk',
            'Microsoft ecosystem compatibility where relevant',
        ],
    },
    {
        'title': 'Funding Fit Score',
        'includes': [
            'Sector fit', 'Geography fit', 'Ticket size fit', 'Impact alignment',
            'Documentation readiness', 'Deadline urgency',
            'Islamic finance suitability where relevant',
        ],
    },
]

OUTREACH_TEMPLATES = [
    {
        'number': 1,
        'title': 'Investor outreach',
        'subject': 'EcoIQ finance-ready industrial modernisation pipeline',
        'message': 'We are building an evidence-based pipeline of industrial '
                    'modernisation projects with Asset Passports, finance memos, MRV '
                    'plans and governance review. I would be happy to share a short '
                    'investor brief on opportunities across Kazakhstan, the UK, Saudi '
                    'Arabia and Türkiye.',
    },
    {
        'number': 2,
        'title': 'Akimat / Government outreach',
        'subject': 'EcoIQ clean heating and industrial modernisation atlas',
        'message': 'EcoIQ can help map high-harm assets, identify finance-ready '
                    'projects, prepare clean heating opportunities and track verified '
                    'impact through MRV.',
    },
    {
        'number': 3,
        'title': 'Supplier outreach',
        'subject': 'Supplier opportunity for verified modernisation projects',
        'message': 'EcoIQ is building a supplier and funding marketplace for '
                    'evidence-based industrial upgrades. We would like to understand '
                    'your capabilities and match qualified opportunities after human '
                    'approval.',
    },
    {
        'number': 4,
        'title': 'CSR / Sponsor outreach',
        'subject': 'Sponsor verified clean heating and community impact',
        'message': 'EcoIQ can structure sponsor-ready clean heating and harm-reduction '
                    'projects with before/after evidence, MRV reporting and approved '
                    'public impact summaries.',
    },
    {
        'number': 5,
        'title': 'Microsoft ecosystem partner outreach',
        'subject': 'EcoIQ Microsoft-ready industrial modernisation platform',
        'message': 'EcoIQ is building a Microsoft ecosystem-ready platform using '
                    'concepts around Fabric, Power BI, Teams, SharePoint, Azure Digital '
                    'Twins and AI agents to modernise industrial assets and generate '
                    'verified impact reports.',
    },
]

EXAMPLE_OPPORTUNITIES = [
    {
        'organisation': 'Kazakhstan Regional Akimat',
        'type': 'Government / Akimat',
        'interest': 'Country Transition Atlas + clean heating pilot',
        'stage': 'Proposal Sent',
        'next_action': 'Send Kazakhstan Clean Heating Opportunity Pack and request pilot meeting.',
        'potential_products': ['Country Atlas', 'Asset Passports', 'Mobile Inspection', 'MRV Packs', 'Public Trust Portal'],
    },
    {
        'organisation': 'UK Manufacturing SME',
        'type': 'Industrial company',
        'interest': 'Factory Energy Efficiency + Investor Memo',
        'stage': 'Free Scan / Demo',
        'next_action': 'Create Asset Passport for production line and propose Mobile Inspection Pack.',
        'potential_products': [],
    },
    {
        'organisation': 'CSR Sponsor',
        'type': 'Sponsor / donor',
        'interest': 'Village Clean Heating Sponsor Impact Pack',
        'stage': 'Qualified',
        'next_action': 'Share sponsor-ready project list and MRV reporting structure.',
        'potential_products': [],
    },
    {
        'organisation': 'Heat Pump Supplier',
        'type': 'Supplier / installer',
        'interest': 'Supplier Marketplace',
        'stage': 'Discovery Call',
        'next_action': 'Collect supplier capability profile and certification evidence.',
        'potential_products': [],
    },
    {
        'organisation': 'Islamic Finance Provider',
        'type': 'Funder',
        'interest': 'Clean heating / asset-backed finance',
        'stage': 'Pilot Negotiation',
        'next_action': 'Prepare Islamic Finance Brief and request Shariah review process.',
        'potential_products': [],
    },
    {
        'organisation': 'Microsoft Ecosystem Partner',
        'type': 'Enterprise / technology partner',
        'interest': 'Power BI + Teams + Fabric integration',
        'stage': 'Discovery Call',
        'next_action': 'Share Microsoft Core Stack page and propose enterprise pilot architecture review.',
        'potential_products': [],
    },
]

AMANAH_CRM_ITEMS = [
    'Find leads needing follow-up', 'Identify free scans ready for upsell',
    'Detect stalled proposals', 'Prepare outreach drafts',
    'Prepare investor/funder briefing packs', 'Flag sponsor-ready projects',
    'Identify enterprise pilot opportunities', 'Update pipeline priorities',
    'Prepare morning sales briefing',
]
AMANAH_MORNING_BRIEFING_EXAMPLE = (
    '7 follow-ups are due, 3 free scans are ready for Asset Passport upsell, 2 CSR '
    'sponsors should receive clean heating packs, 1 akimat opportunity needs a Country '
    'Atlas proposal, and 1 Microsoft partner meeting needs a technical brief.'
)

MICROSOFT_DYNAMICS_ITEMS = [
    'Dynamics 365 for CRM records and opportunity stages',
    'Microsoft Teams for follow-up reminders and approvals',
    'Outlook / Microsoft Graph for meeting and email workflows',
    'SharePoint for proposal and evidence pack storage',
    'Power BI for sales pipeline dashboards',
    'Power Automate for automated reminders and approval routing',
    'Microsoft Fabric for customer and project analytics',
]

DATA_ROOM_CONNECTION_ITEMS = [
    'Proposal pack', 'Investor memo', 'Board pack', 'Sponsor pack', 'Country atlas',
    'Supplier RFQ', 'MRV report', 'Public impact summary', 'Approval record',
]

NO_HARM_GATE_SALES_ITEMS = [
    'Is the claim evidence-backed?',
    'Is the customer vulnerable?',
    'Could pricing be unfair or unclear?',
    'Is sponsor impact verified or clearly labelled?',
    'Are supplier/funder relationships disclosed?',
    'Is Islamic finance wording reviewed?',
    'Is public impact wording approved?',
    'Is personal data protected?',
    'Is human approval needed before contacting suppliers/funders?',
    'Are we avoiding overpromising savings, funding or impact?',
]

SAFETY_PRINCIPLES = [
    'Sales pipeline outputs are commercial support tools, not legal, investment or '
    'financial advice.',
    'EcoIQ must not overpromise guaranteed funding, savings, emissions reduction or impact.',
    'Supplier, funder and sponsor claims require due diligence and approval.',
    'Islamic finance positioning requires qualified review where relevant.',
    'Public impact statements require MRV evidence and approval.',
    'Outreach should respect privacy, consent and anti-spam rules.',
]

CTA_BUTTONS = [
    {'label': 'Open Sales Pipeline', 'anchor': '#pipeline-stages'},
    {'label': 'Add New Lead', 'anchor': '#stage-1'},
    {'label': 'Create Opportunity', 'anchor': '#opportunity-fields'},
    {'label': 'Generate Proposal', 'anchor': '#stage-5'},
    {'label': 'Prepare Investor Outreach', 'anchor': '#outreach-1'},
    {'label': 'Prepare Akimat Brief', 'anchor': '#outreach-2'},
    {'label': 'Send Follow-Up to Teams', 'anchor': '#microsoft-dynamics-integration'},
    {'label': 'Create Sponsor Pack', 'anchor': '#outreach-4'},
    {'label': 'Link Data Room', 'url_name': 'data_room_evidence_vault:overview'},
    {'label': 'Update Deal Stage', 'anchor': '#kanban-columns'},
]


def overview(request):
    return render(request, 'sales_crm_partner_pipeline/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_purpose': CORE_PURPOSE,
        'pipeline_stages': PIPELINE_STAGES,
        'crm_contact_types': CRM_CONTACT_TYPES,
        'opportunity_fields': OPPORTUNITY_FIELDS,
        'product_opportunity_types': PRODUCT_OPPORTUNITY_TYPES,
        'partner_pipeline_views': PARTNER_PIPELINE_VIEWS,
        'pipeline_dashboard_cards': PIPELINE_DASHBOARD_CARDS,
        'kanban_columns': KANBAN_COLUMNS,
        'kanban_card_shows': KANBAN_CARD_SHOWS,
        'scoring_logic': SCORING_LOGIC,
        'outreach_templates': OUTREACH_TEMPLATES,
        'example_opportunities': EXAMPLE_OPPORTUNITIES,
        'amanah_crm_items': AMANAH_CRM_ITEMS,
        'amanah_morning_briefing_example': AMANAH_MORNING_BRIEFING_EXAMPLE,
        'microsoft_dynamics_items': MICROSOFT_DYNAMICS_ITEMS,
        'data_room_connection_items': DATA_ROOM_CONNECTION_ITEMS,
        'no_harm_gate_sales_items': NO_HARM_GATE_SALES_ITEMS,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })
