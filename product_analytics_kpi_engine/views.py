from django.shortcuts import render

# Connected EcoIQ modules — the KPI Engine measures what all of them produce
CONNECTED_MODULES = [
    {'name': 'Revenue & Pricing Engine', 'role': 'Supplies the revenue events tracked in Revenue Analytics.'},
    {'name': 'Sales CRM & Partner Pipeline', 'role': 'Supplies pipeline and conversion events tracked in Sales & Partner Analytics.'},
    {'name': 'Customer Success & Renewal Engine', 'role': 'Supplies account health and renewal events tracked in Customer Success Analytics.'},
    {'name': 'Command Centre', 'role': 'Surfaces live project status feeding usage and conversion metrics.'},
    {'name': 'Asset Passport', 'role': 'Supplies asset creation events tracked in Product Usage Analytics.'},
    {'name': 'Impact MRV Layer', 'role': 'Supplies baseline, after-data and verification events tracked in Impact Analytics.'},
    {'name': 'Public Trust & Impact Portal', 'role': 'Supplies published story events tracked in Product Usage and Impact Analytics.'},
    {'name': 'Portfolio & Country Transition Atlas', 'role': 'Supplies the country and sector data behind Country & Portfolio Analytics.'},
    {'name': 'Data Room & Evidence Vault', 'role': 'Supplies evidence completeness tracked in Data Quality Analytics.'},
    {'name': 'Executive Briefing & Board Pack Generator', 'role': 'Supplies pack generation events tracked in Product Usage Analytics.'},
    {'name': 'Supplier & Funding Marketplace', 'role': 'Supplies matching events tracked in Conversion and Sales Analytics.'},
    {'name': 'Microsoft Ecosystem Core Stack', 'role': 'Provides the agent, data and dashboard building blocks a production analytics engine would run on.'},
    {'name': 'Power BI', 'role': 'Renders the KPI dashboards this module documents.'},
    {'name': 'Microsoft Fabric', 'role': 'Stores the underlying event and product data.'},
    {'name': 'Dynamics 365', 'role': 'Supplies sales and customer data used in analytics.'},
    {'name': 'Teams', 'role': 'Delivers daily KPI alerts and briefings.'},
]

CORE_PURPOSE = (
    'Turn EcoIQ into a measurable, data-driven platform that can improve conversion, '
    'retention, product quality and verified impact.'
)

ANALYTICS_CATEGORIES = [
    {
        'number': 1,
        'title': 'Product Usage Analytics',
        'track': [
            'Active users', 'Active organisations', 'Module visits',
            'Time spent by module', 'Asset Passports created', 'Inspections started',
            'Evidence uploads', 'Playbooks matched', 'Finance memos generated',
            'MRV packs created', 'Board packs generated',
            'Public impact pages published', 'Country atlas views',
            'Data room packs created',
        ],
        'funnel': [],
        'metrics': [],
    },
    {
        'number': 2,
        'title': 'Conversion Analytics',
        'track': [],
        'funnel': [
            'Free Scan', 'Asset Passport', 'Mobile Inspection', 'Playbook Diagnosis',
            'Finance Memo', 'Supplier/Funding Match', 'MRV Pack', 'Public Impact Story',
            'Enterprise Subscription',
        ],
        'metrics': [
            'Scan-to-passport conversion', 'Passport-to-inspection conversion',
            'Inspection-to-memo conversion', 'Memo-to-proposal conversion',
            'Proposal-to-contract conversion', 'Contract-to-renewal conversion',
            'Sponsor-pack conversion', 'Supplier-match conversion',
            'Enterprise pilot conversion',
        ],
    },
    {
        'number': 3,
        'title': 'Revenue Analytics',
        'track': [
            'Monthly recurring revenue', 'Project report revenue',
            'Enterprise pilot revenue', 'Marketplace revenue', 'Sponsor pack revenue',
            'API revenue', 'Country atlas revenue', 'Average revenue per account',
            'Average revenue per project', 'Revenue by country', 'Revenue by sector',
            'Revenue by product', 'Renewal revenue', 'Upsell revenue',
        ],
        'funnel': [],
        'metrics': [],
    },
    {
        'number': 4,
        'title': 'Impact Analytics',
        'track': [
            'MRV baseline completed', 'After-data collected', 'Impact verified',
            'Verified projects', 'Estimated vs verified impact', 'kWh saved where verified',
            'Fuel saved where verified', 'CO2 reduced where verified',
            'Water saved where verified', 'Waste reduced where verified',
            'Households helped', 'Public buildings improved',
            'Maqasid/Mizan score improvements',
        ],
        'funnel': [],
        'metrics': [],
    },
    {
        'number': 5,
        'title': 'Data Quality Analytics',
        'track': [
            'Evidence completeness', 'Missing baseline data', 'Missing after-data',
            'Weak evidence alerts', 'Outdated documents', 'Missing approvals',
            'Data Room completeness', 'Evidence quality by project',
            'Evidence quality by country', 'Evidence quality by module',
        ],
        'funnel': [],
        'metrics': [],
    },
    {
        'number': 6,
        'title': 'Customer Success Analytics',
        'track': [
            'Account health score', 'Onboarding completion', 'Active accounts',
            'At-risk accounts', 'Expansion-ready accounts', 'Renewals due',
            'Churn risk', 'Value reviews generated', 'Support issues',
            'Usage by customer type',
        ],
        'funnel': [],
        'metrics': [],
    },
    {
        'number': 7,
        'title': 'Sales & Partner Analytics',
        'track': [
            'Total leads', 'Qualified opportunities', 'Proposals sent',
            'Pilots in negotiation', 'Contracts won', 'Lost opportunities',
            'Weighted pipeline value', 'Partner pipeline', 'Supplier pipeline',
            'Investor/funder pipeline', 'CSR sponsor pipeline',
            'Microsoft partner pipeline',
        ],
        'funnel': [],
        'metrics': [],
    },
    {
        'number': 8,
        'title': 'Country & Portfolio Analytics',
        'track': [
            'Assets mapped by country', 'Finance-ready projects by country',
            'Highest-harm clusters', 'Highest-impact clusters',
            'Verified impact by country', 'Sector performance',
            'Regional opportunity pipeline', 'CAPEX pipeline', 'Funding gap',
        ],
        'funnel': [],
        'metrics': [],
    },
]

KPI_DASHBOARD_CARDS = [
    'Active users', 'Active organisations', 'Free scans completed',
    'Asset Passports created', 'MRV packs generated', 'Investor memos generated',
    'Board packs generated', 'Public impact stories published',
    'Total pipeline value', 'Monthly recurring revenue', 'Project revenue',
    'Scan-to-passport conversion', 'Proposal-to-contract conversion', 'Renewal rate',
    'Churn risk accounts', 'Verified impact projects', 'Evidence completeness average',
    'Maqasid/Mizan average improvement', 'No Harm Gate alerts',
]

MODULE_PERFORMANCE_FIELDS = [
    'Module name', 'Visits', 'Users', 'Conversion contribution', 'Revenue contribution',
    'Completion rate', 'Drop-off rate', 'Average time to complete', 'Support issues',
    'Evidence quality impact', 'Customer satisfaction', 'Next improvement',
]

EVENT_TRACKING_EXAMPLES = [
    'user.started_free_scan', 'asset_passport.created', 'mobile_inspection.started',
    'evidence.uploaded', 'playbook.matched', 'finance_memo.generated',
    'supplier_match.generated', 'mrv.baseline_completed', 'mrv.impact_verified',
    'board_pack.generated', 'data_room.pack_created', 'public_impact_story.published',
    'sales.proposal_sent', 'sales.contract_won', 'customer.renewal_due',
    'customer.expansion_ready',
]

FUNNEL_STAGES = [
    'Visitors', 'Free scans', 'Asset Passports', 'Paid inspections', 'Finance memos',
    'Proposals', 'Contracts', 'MRV packs', 'Renewals', 'Enterprise expansions',
]
FUNNEL_SHOWS = ['Count', 'Conversion %', 'Revenue', 'Drop-off', 'Next optimisation']

EXAMPLE_INSIGHTS = [
    {
        'number': 1,
        'insight': 'Free scans are converting well into Asset Passports in Kazakhstan '
                    'clean heating projects, but many projects are blocked by missing '
                    'baseline fuel data.',
        'recommended_action': 'Improve upload prompts and add Amanah Autopilot missing '
                               'evidence reminders.',
    },
    {
        'number': 2,
        'insight': 'UK factory efficiency projects show strong quick-payback potential '
                    'but low supplier matching completion.',
        'recommended_action': 'Add more supplier onboarding and RFQ templates.',
    },
    {
        'number': 3,
        'insight': 'CSR sponsor packs have high interest but public stories are delayed '
                    'by missing consent and MRV approval.',
        'recommended_action': 'Create a sponsor consent checklist and public reporting '
                               'workflow.',
    },
    {
        'number': 4,
        'insight': 'Country Atlas pages drive enterprise conversations but need better '
                    'conversion into pilot proposals.',
        'recommended_action': 'Add CTA to request Country Atlas pilot and link to Sales CRM.',
    },
]

AMANAH_ITEMS = [
    'Detect funnel drop-offs', 'Flag weak conversion points',
    'Identify accounts ready for upsell', 'Find stalled MRV projects',
    'Prepare missing evidence reminders', 'Identify high-performing countries',
    'Flag low-performing modules', 'Prepare daily KPI briefing',
]
AMANAH_MORNING_BRIEFING_EXAMPLE = (
    'Free Scan conversion rose this week, but MRV completion is blocked by missing '
    'after-data in 6 projects. Kazakhstan clean heating has the strongest sponsor '
    'pipeline, while UK factory projects show the fastest payback.'
)

MICROSOFT_POWERBI_ITEMS = [
    'Microsoft Fabric for event and product data', 'Power BI for KPI dashboards',
    'Dynamics 365 for sales and customer data', 'Teams for daily KPI alerts',
    'Power Automate for follow-up workflows', 'SharePoint for executive KPI reports',
    'Azure Application Insights concept for usage telemetry',
    'Microsoft Graph for activity signals where appropriate',
]

NO_HARM_GATE_ITEMS = [
    'Is data accurate?',
    'Is user privacy protected?',
    'Are sensitive projects anonymised?',
    'Are vulnerable communities not exposed?',
    'Are impact claims MRV-backed?',
    'Are revenue metrics separated from ethical impact?',
    'Is Maqasid/Mizan used responsibly?',
    'Is there risk of optimising sales over real harm reduction?',
    'Are users informed where tracking is required?',
    'Is personal data handled securely?',
]

SAFETY_PRINCIPLES = [
    'Product analytics are used to improve platform performance, not to expose '
    'sensitive users, communities or industrial data.',
    'Revenue analytics should not override No Harm, MRV evidence or ethical review.',
    'Impact metrics must distinguish estimated from verified results.',
    'Personal data and sensitive project data must be permissioned and protected.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
    'Decisions based on analytics require human judgement and context.',
]

CTA_BUTTONS = [
    {'label': 'Open KPI Dashboard', 'anchor': '#kpi-dashboard-cards'},
    {'label': 'View Product Funnel', 'anchor': '#funnel-dashboard'},
    {'label': 'Track Revenue Metrics', 'anchor': '#category-3'},
    {'label': 'View MRV Completion', 'anchor': '#category-4'},
    {'label': 'Show Country Pipeline', 'anchor': '#category-8'},
    {'label': 'Analyse Module Adoption', 'anchor': '#module-performance-table'},
    {'label': 'Export Power BI Report', 'anchor': '#microsoft-powerbi-integration'},
    {'label': 'Generate Weekly KPI Brief', 'anchor': '#amanah-analytics'},
    {'label': 'Flag Drop-Offs', 'anchor': '#funnel-dashboard'},
    {'label': 'Send KPI Briefing to Teams', 'anchor': '#microsoft-powerbi-integration'},
]


def overview(request):
    return render(request, 'product_analytics_kpi_engine/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_purpose': CORE_PURPOSE,
        'analytics_categories': ANALYTICS_CATEGORIES,
        'kpi_dashboard_cards': KPI_DASHBOARD_CARDS,
        'module_performance_fields': MODULE_PERFORMANCE_FIELDS,
        'event_tracking_examples': EVENT_TRACKING_EXAMPLES,
        'funnel_stages': FUNNEL_STAGES,
        'funnel_shows': FUNNEL_SHOWS,
        'example_insights': EXAMPLE_INSIGHTS,
        'amanah_items': AMANAH_ITEMS,
        'amanah_morning_briefing_example': AMANAH_MORNING_BRIEFING_EXAMPLE,
        'microsoft_powerbi_items': MICROSOFT_POWERBI_ITEMS,
        'no_harm_gate_items': NO_HARM_GATE_ITEMS,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })
