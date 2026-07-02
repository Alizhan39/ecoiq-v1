from django.shortcuts import render

# Connected EcoIQ modules — the Atlas rolls every project-level module up to country/portfolio scale
CONNECTED_MODULES = [
    {'name': 'Command Centre', 'role': 'Supplies the live project pipeline the Atlas aggregates to country and portfolio scale.'},
    {'name': 'Asset Passport', 'role': 'Supplies the located, structured asset records plotted on the map.'},
    {'name': 'Impact MRV Layer', 'role': 'Supplies verified impact status feeding the Verified Impact View.'},
    {'name': 'Industrial Playbook Library', 'role': 'Supplies the playbook types compared across the portfolio.'},
    {'name': 'Institutional Finance Engine', 'role': 'Supplies CAPEX, savings and finance readiness rolled up per country.'},
    {'name': 'Supplier & Funding Marketplace', 'role': 'Supplies funding status feeding the Finance-Ready View.'},
    {'name': 'Governance & Expert Review Board', 'role': 'Supplies review status feeding portfolio readiness scoring.'},
    {'name': 'Mobile / iPad Inspection Mode', 'role': 'Feeds newly discovered assets onto the map.'},
    {'name': 'Data Room & Evidence Vault', 'role': 'Supplies evidence quality used in portfolio scoring.'},
    {'name': 'API & Integration Layer', 'role': 'Exposes atlas and portfolio data to external systems.'},
    {'name': 'Microsoft Ecosystem Core Stack', 'role': 'Provides the agent, data and dashboard building blocks a production atlas would run on.'},
    {'name': 'Azure Digital Twins', 'role': 'Supplies asset relationships behind mapped clusters.'},
    {'name': 'Microsoft Fabric', 'role': 'Stores portfolio and country-level data.'},
    {'name': 'Power BI', 'role': 'Renders country and regional dashboards.'},
    {'name': 'Teams', 'role': 'Delivers country and portfolio briefings.'},
    {'name': 'Geospatial / satellite layers where relevant', 'role': 'Supplies location and land-use context for the map view.'},
    {'name': 'Maqasid/Mizan ethical scoring', 'role': 'Rolls up into the Portfolio Score alongside harm, readiness and impact.'},
    {'name': 'No Harm Gate', 'role': 'Blocks projects from being shown as finance-ready or high-impact without evidence.'},
]

CORE_PURPOSE = 'Turn project-level intelligence into a country-scale and portfolio-scale transition map.'

SUPPORTED_COUNTRIES = ['Kazakhstan', 'United Kingdom', 'Saudi Arabia', 'Türkiye']

SUPPORTED_ASSET_CATEGORIES = [
    'Boiler houses', 'District heating assets', 'Factories', 'Production lines',
    'Mines / quarries', 'Farms / greenhouses', 'Water systems', 'Public buildings',
    'Solar + battery sites', 'Compressed air systems', 'Waste heat recovery opportunities',
    'Clean heating transition projects', 'SMR feasibility zones where relevant',
]

ATLAS_VIEWS = [
    {
        'number': 1,
        'anchor': 'view-1',
        'title': 'Country Overview',
        'description': 'For each country show:',
        'items': [
            'Total assets tracked', 'Total projects discovered', 'Finance-ready projects',
            'Projects in implementation', 'Verified impact projects',
            'Total estimated CAPEX pipeline', 'Total estimated annual savings',
            'Total estimated CO2 reduction', 'Total funding gap', 'Average Maqasid score',
            'Average Mizan score', 'No Harm Gate alerts',
        ],
    },
    {
        'number': 2,
        'anchor': 'view-2',
        'title': 'Map View',
        'description': 'Display assets and projects on a map. Map markers should show:',
        'items': [
            'Asset type', 'Sector', 'Project stage', 'Risk level', 'Evidence quality',
            'Finance readiness', 'Impact potential', 'Maqasid/Mizan score',
            'No Harm Gate alert status',
        ],
        'extra_label': 'Marker colour logic',
        'extra_items': [
            'Red = highest harm / urgent', 'Orange = high risk / high waste',
            'Blue = finance-ready', 'Green = verified impact', 'Grey = needs verification',
        ],
    },
    {
        'number': 3,
        'anchor': 'view-3',
        'title': 'Portfolio View',
        'description': 'Show portfolio by:',
        'items': [
            'Country', 'Region', 'Sector', 'Asset type', 'Playbook type', 'Funding status',
            'Project stage', 'Evidence quality', 'Risk level', 'Impact potential',
        ],
    },
    {
        'number': 4,
        'anchor': 'view-4',
        'title': 'Highest Harm View',
        'description': 'Identify which assets or regions show:',
        'items': [
            'Strongest pollution signals', 'High fuel waste', 'High energy losses',
            'High indoor/outdoor harm', 'High safety risk',
            'Weak evidence but probable urgent need',
        ],
    },
    {
        'number': 5,
        'anchor': 'view-5',
        'title': 'Highest Impact View',
        'description': 'Identify which assets or regions have:',
        'items': [
            'Strong quick-payback opportunities', 'Large emissions reduction potential',
            'Strong community benefit', 'High Maqasid/Mizan uplift',
            'High readiness for funding', 'High scalability',
        ],
    },
    {
        'number': 6,
        'anchor': 'view-6',
        'title': 'Finance-Ready View',
        'description': 'Show projects that already have:',
        'items': [
            'Asset Passport complete', 'Playbook matched', 'Finance memo ready',
            'Supplier/funding routes identified',
            'Expert review completed or in progress',
            'Evidence quality sufficient for funding submission',
        ],
    },
    {
        'number': 7,
        'anchor': 'view-7',
        'title': 'Verified Impact View',
        'description': 'Show projects with:',
        'items': [
            'Baseline evidence complete', 'After-data collected', 'MRV verified',
            'Before/after proof', 'Cost savings confirmed', 'Impact report generated',
        ],
    },
]

COUNTRY_CARDS = [
    {
        'name': 'Kazakhstan',
        'priority_themes': [
            'Boiler houses', 'District heating', 'Coal-to-clean heating transition',
            'Mines and metals', 'Public building retrofits', 'Village clean heating',
            'Water systems', 'Industrial modernisation around key regions',
        ],
    },
    {
        'name': 'United Kingdom',
        'priority_themes': [
            'Public building decarbonisation', 'Industrial efficiency',
            'Heat pump / clean heat retrofits', 'Waste heat recovery',
            'ESG / investor readiness', 'Manufacturing efficiency',
            'Social housing / community heating where relevant',
        ],
    },
    {
        'name': 'Saudi Arabia',
        'priority_themes': [
            'Industrial efficiency', 'Desalination / water systems',
            'Cooling and energy efficiency', 'Industrial diversification',
            'Sustainability-linked investment',
            'Large-scale infrastructure opportunity mapping',
        ],
    },
    {
        'name': 'Türkiye',
        'priority_themes': [
            'Manufacturing', 'Textiles / production efficiency', 'Industrial heating',
            'Earthquake-resilient rebuilding opportunities where relevant',
            'Agriculture and irrigation', 'SME transition readiness',
        ],
    },
]

REGION_SUMMARY_FIELDS = [
    'Number of tracked assets', 'Number of urgent projects', 'Finance-ready projects',
    'Implementation projects', 'Verified impact projects', 'CAPEX pipeline',
    'Estimated annual savings', 'Impact potential', 'Top playbooks used',
]

SECTOR_COMPARISON_SECTORS = [
    'Energy / heating', 'Manufacturing', 'Mining', 'Agriculture', 'Water',
    'Public infrastructure',
]
SECTOR_COMPARISON_FIELDS = [
    'Project count', 'Average risk level', 'Finance readiness', 'Estimated savings',
    'Estimated CO2 reduction', 'Evidence quality', 'Average Maqasid score',
    'Average Mizan score', 'No Harm alerts',
]

ATLAS_WORKFLOW = [
    'Asset discovered', 'Asset located on map', 'Asset Passport created',
    'Playbook matched', 'Finance readiness assessed', 'Supplier / funding routes matched',
    'Governance review tracked', 'Implementation tracked', 'MRV verified',
    'Portfolio / country dashboard updated',
]

EXAMPLE_CLUSTERS = [
    {
        'title': 'Kazakhstan clean heating cluster',
        'examples': [
            'Municipal boiler houses', 'Village stove replacement',
            'District heating upgrades', 'Public building retrofits',
        ],
        'shows': [
            'Highest harm zones', 'Finance-ready heating projects',
            'CSR / sadaqah jariyah / municipal co-finance opportunities',
            'Verified household benefit',
        ],
    },
    {
        'title': 'UK industrial efficiency cluster',
        'examples': [
            'Factory motor upgrades', 'Compressed air optimisation',
            'Waste heat recovery', 'Public building efficiency',
        ],
        'shows': [
            'Quick payback opportunities', 'Finance-ready SME projects',
            'Verified savings pipeline',
        ],
    },
    {
        'title': 'Saudi industrial and water cluster',
        'examples': [
            'Industrial cooling efficiency', 'Water system upgrades',
            'Large energy-intensive assets', 'Solar + battery opportunities',
        ],
        'shows': [
            'Strategic large-ticket opportunities', 'Infrastructure readiness',
            'Country-level portfolio view',
        ],
    },
    {
        'title': 'Türkiye manufacturing and agriculture cluster',
        'examples': [
            'Production line efficiency', 'Boiler modernisation', 'Irrigation upgrades',
            'Greenhouse energy efficiency',
        ],
        'shows': [
            'SME transition readiness', 'Agriculture-water nexus',
            'Implementation-ready pipeline',
        ],
    },
]

ATLAS_DASHBOARD_CARDS = [
    'Countries covered', 'Regions tracked', 'Assets mapped', 'Projects discovered',
    'Finance-ready projects', 'High-harm assets', 'High-impact opportunities',
    'Verified impact projects', 'Total CAPEX pipeline', 'Estimated annual savings',
    'Estimated CO2 reduction', 'Total funding gap', 'Average evidence quality',
    'Average Maqasid score', 'Average Mizan score', 'No Harm alerts',
]

PROJECT_TABLE_FIELDS = [
    'Project name', 'Country', 'Region', 'Location', 'Sector', 'Asset type',
    'Project stage', 'Playbook', 'Risk level', 'Evidence quality', 'Finance readiness',
    'CAPEX estimate', 'Annual savings estimate', 'Funding status', 'MRV status',
    'Maqasid score', 'Mizan score', 'No Harm status', 'Next action',
]

FILTERS = [
    'Country', 'Region', 'City / locality if available', 'Sector', 'Asset type',
    'Project stage', 'Playbook type', 'Risk level', 'Finance readiness', 'Funding status',
    'MRV status', 'Evidence quality', 'Maqasid score range', 'Mizan score range',
    'No Harm alerts', 'Implementation status',
]

SCORING_LOGIC = [
    {
        'title': 'Harm Score',
        'description': 'Measures pollution, energy waste, health risk, safety risk and social burden.',
    },
    {
        'title': 'Readiness Score',
        'description': 'Measures evidence quality, playbook fit, finance memo readiness, '
                        'supplier/funder readiness and governance progress.',
    },
    {
        'title': 'Impact Potential Score',
        'description': 'Measures estimated cost savings, emissions reduction, community '
                        'benefit and scalability.',
    },
    {
        'title': 'Maqasid/Mizan Portfolio Score',
        'description': 'Measures ethical alignment, balance, stewardship and reduction of '
                        'waste/harm.',
    },
]
SCORING_LOGIC_NOTE = 'These are decision-support indicators, not legal, engineering or religious judgements.'

PRIORITISATION_LOGIC = [
    'High harm + high readiness = immediate priority',
    'High harm + low readiness = evidence mobilisation priority',
    'Low harm + high readiness = quick scalable win',
    'High impact + medium readiness = prepare finance and implementation',
    'High cost + high uncertainty = expert review first',
]

PORTFOLIO_PACK_OUTPUTS = [
    'Country Transition Brief', 'Investor Portfolio Brief', 'Regional Priority Heatmap',
    'Clean Heating Opportunity Pack', 'Manufacturing Efficiency Pack',
    'Mining Transition Opportunity Pack', 'Agriculture & Water Transition Pack',
    'Verified Impact Portfolio Report',
]

MICROSOFT_INTEGRATION_ITEMS = [
    'Microsoft Fabric for portfolio data',
    'Power BI for country and regional dashboards',
    'Azure Digital Twins for asset relationships',
    'Azure Maps / geospatial concept for map display',
    'Power Automate for alerts and briefings',
    'Teams for country/project notifications',
    'SharePoint for exported portfolio packs',
    'Dynamics 365 for funder and supplier pipeline linkage',
    'Azure AI / Agent Framework for portfolio intelligence agents',
]

AMANAH_INTEGRATION_ITEMS = [
    'Identify newly high-harm regions', 'Flag finance-ready projects',
    'Identify missing evidence in high-priority zones',
    'Prepare country transition briefings', 'Prepare investor portfolio packs',
    'Flag projects with strong Maqasid/Mizan uplift',
    'Highlight projects with verified impact ready for reporting',
]
AMANAH_MORNING_BRIEFING_EXAMPLE = (
    'Kazakhstan now has 12 finance-ready heating projects, the UK has 8 quick-payback '
    'industrial efficiency opportunities, Saudi Arabia shows 5 large infrastructure '
    'candidates, and Türkiye has 9 manufacturing/agriculture projects needing supplier '
    'matching.'
)

COUNTRY_EXAMPLE_CARDS = [
    {
        'country': 'Kazakhstan',
        'summary': [
            '74 assets mapped', '21 clean heating opportunities', '9 finance-ready projects',
            '5 verified impact projects',
            'Highest-harm cluster: boiler houses and village heating',
            'Highest-impact cluster: district heating upgrades and public building retrofits',
        ],
        'next_action': 'Prepare Clean Heating Opportunity Pack for municipal and donor review.',
    },
    {
        'country': 'United Kingdom',
        'summary': [
            '43 assets mapped', '15 industrial efficiency opportunities',
            '7 finance-ready projects', '6 verified impact projects',
            'Highest-harm cluster: inefficient industrial heating',
            'Highest-impact cluster: compressed air and waste heat quick wins',
        ],
        'next_action': 'Prepare Investor Portfolio Brief for SME efficiency upgrades.',
    },
    {
        'country': 'Saudi Arabia',
        'summary': [
            '29 assets mapped', '10 strategic infrastructure opportunities',
            '4 finance-ready projects',
            'Highest-impact cluster: water-energy systems and industrial cooling',
        ],
        'next_action': 'Prepare Strategic Infrastructure Transition Brief.',
    },
    {
        'country': 'Türkiye',
        'summary': [
            '38 assets mapped', '14 manufacturing and agriculture opportunities',
            '6 finance-ready projects',
            'Highest-impact cluster: production efficiency and irrigation upgrades',
        ],
        'next_action': 'Prepare Manufacturing & Agriculture Transition Pack.',
    },
]

NO_HARM_GATE_ATLAS_ITEMS = [
    'Is the evidence strong enough?',
    'Is the location correct?',
    'Are the impact assumptions transparent?',
    'Is there a risk of misrepresenting harm?',
    'Are community and environmental risks visible?',
    'Is the project still pending expert review?',
    'Is MRV verified or still provisional?',
    'Is human approval required before external reporting?',
]

SAFETY_PRINCIPLES = [
    'The Atlas is a portfolio intelligence and decision-support tool, not a replacement '
    'for engineering, financial, legal, environmental or policy review.',
    'Projects shown as finance-ready or high-impact still require due diligence and human '
    'approval.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
    'Country and regional comparisons depend on evidence quality and may include projects '
    'marked "Needs verification".',
    'Public-facing impact claims require MRV-supported evidence.',
]

CTA_BUTTONS = [
    {'label': 'Open Transition Atlas', 'anchor': '#atlas-views'},
    {'label': 'View Country Portfolio', 'anchor': '#country-cards'},
    {'label': 'Show Finance-Ready Projects', 'anchor': '#view-6'},
    {'label': 'Show Highest Harm Assets', 'anchor': '#view-4'},
    {'label': 'Show Highest Impact Opportunities', 'anchor': '#view-5'},
    {'label': 'Export Country Brief', 'anchor': '#portfolio-pack-outputs'},
    {'label': 'Generate Investor Portfolio Pack', 'anchor': '#portfolio-pack-outputs'},
    {'label': 'Open Verified Impact Map', 'anchor': '#view-7'},
    {'label': 'Send Atlas Briefing to Teams', 'anchor': '#microsoft-integration'},
]


def overview(request):
    return render(request, 'portfolio_country_transition_atlas/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_purpose': CORE_PURPOSE,
        'supported_countries': SUPPORTED_COUNTRIES,
        'supported_asset_categories': SUPPORTED_ASSET_CATEGORIES,
        'atlas_views': ATLAS_VIEWS,
        'country_cards': COUNTRY_CARDS,
        'region_summary_fields': REGION_SUMMARY_FIELDS,
        'sector_comparison_sectors': SECTOR_COMPARISON_SECTORS,
        'sector_comparison_fields': SECTOR_COMPARISON_FIELDS,
        'atlas_workflow': ATLAS_WORKFLOW,
        'example_clusters': EXAMPLE_CLUSTERS,
        'atlas_dashboard_cards': ATLAS_DASHBOARD_CARDS,
        'project_table_fields': PROJECT_TABLE_FIELDS,
        'filters': FILTERS,
        'scoring_logic': SCORING_LOGIC,
        'scoring_logic_note': SCORING_LOGIC_NOTE,
        'prioritisation_logic': PRIORITISATION_LOGIC,
        'portfolio_pack_outputs': PORTFOLIO_PACK_OUTPUTS,
        'microsoft_integration_items': MICROSOFT_INTEGRATION_ITEMS,
        'amanah_integration_items': AMANAH_INTEGRATION_ITEMS,
        'amanah_morning_briefing_example': AMANAH_MORNING_BRIEFING_EXAMPLE,
        'country_example_cards': COUNTRY_EXAMPLE_CARDS,
        'no_harm_gate_atlas_items': NO_HARM_GATE_ATLAS_ITEMS,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })
