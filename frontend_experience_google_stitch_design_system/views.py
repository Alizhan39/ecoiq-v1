from django.shortcuts import render

# Connected EcoIQ modules — the frontend layer is how every one of these is seen and used
CONNECTED_MODULES = [
    {'name': 'Command Centre', 'role': 'Frontend defines the dashboard, pipeline table, map and Kanban views.'},
    {'name': 'Asset Passport', 'role': 'Frontend defines the one-asset, one-story layout and its panels.'},
    {'name': 'Country Transition Atlas', 'role': 'Frontend defines the interactive map and country card views.'},
    {'name': 'Knowledge Graph & Relationship Map', 'role': 'Frontend defines the node-link graph and filter/detail panels.'},
    {'name': 'Mobile / iPad Inspection Mode', 'role': 'Frontend defines the mobile-first field capture screens.'},
    {'name': 'Public Trust & Impact Portal', 'role': 'Frontend defines the public-safe, sensitive-data-free views.'},
    {'name': 'Data Room & Evidence Vault', 'role': 'Frontend defines the evidence and document review interface.'},
    {'name': 'Impact MRV Layer', 'role': 'Frontend defines how estimated vs verified impact is shown.'},
    {'name': 'Institutional Finance Engine', 'role': 'Frontend defines the finance-ready and investor memo views.'},
    {'name': 'Certification & Trust Badge Engine', 'role': 'Frontend defines the trust badge display, where built.'},
    {'name': 'Microsoft Ecosystem Core Stack', 'role': 'Supplies the Microsoft-ready building blocks the frontend can integrate with.'},
    {'name': 'AI Agent Operations Console', 'role': 'Frontend defines how agent traces and approvals are displayed.'},
    {'name': 'Security, Privacy & Compliance Centre', 'role': 'Constrains which frontend views may show which data to which viewer.'},
    {'name': 'Product Analytics & KPI Engine', 'role': 'Consumes frontend usage data to measure clarity and engagement.'},
]

CORE_PURPOSE = 'Make EcoIQ visually clear, evidence-first, mobile-friendly and enterprise-ready.'

FRONTEND_STACKS = [
    {
        'number': 1,
        'title': 'Current Django Enhancement Stack',
        'items': [
            'Tailwind CSS', 'HTMX', 'Alpine.js', 'Apache ECharts', 'Chart.js',
            'Leaflet', 'MapLibre', 'Cytoscape.js', 'Sigma.js', 'PDF.js', 'SortableJS',
        ],
        'purpose': 'Improve the current Django frontend without rewriting the whole product.',
        'note': '',
    },
    {
        'number': 2,
        'title': 'Future SaaS Frontend Stack',
        'items': [
            'Next.js', 'React', 'TypeScript', 'Tailwind CSS', 'shadcn/ui',
            'Framer Motion', 'React Flow', 'TanStack Table', 'TanStack Query',
            'Apache ECharts', 'MapLibre GL', 'deck.gl', 'pdf.js', 'Cytoscape.js or Sigma.js',
        ],
        'purpose': 'Build a premium SaaS frontend later when EcoIQ is ready for a full frontend application.',
        'note': '',
    },
    {
        'number': 3,
        'title': 'Microsoft Enterprise UI Stack',
        'items': [
            'Fluent UI React', 'Microsoft Teams Toolkit', 'Adaptive Cards',
            'Power BI Embedded', 'MSAL React', 'Microsoft Graph SDK',
            'SharePoint integration concept', 'Dynamics 365 integration concept',
        ],
        'purpose': 'Make EcoIQ feel familiar to Microsoft enterprise users and partners.',
        'note': (
            'Use "Microsoft ecosystem-ready" and "designed to integrate with Microsoft '
            'Fabric, Power BI, Teams, SharePoint and Azure Digital Twins." Do not claim '
            'Microsoft certification or partnership unless actually obtained.'
        ),
    },
    {
        'number': 4,
        'title': 'Google Stitch Design Workflow',
        'items': [
            'Google Stitch for fast UI concepts', 'Figma-style component planning',
            'Material Design usability principles',
            'Gemini-style multimodal evidence concepts where relevant',
        ],
        'purpose': 'Explore UI concepts and visual direction fast, before production build.',
        'note': (
            'Google Stitch is for design prototyping and visual direction. Production UI '
            'should be implemented in Django templates now or Next.js later.'
        ),
    },
]

VISUAL_STYLE = [
    'Enterprise SaaS', 'Microsoft-ready', 'Dark institutional theme', 'Emerald/cyan accents',
    'Evidence-first', 'Map + graph + dashboard', 'Mobile-friendly', 'High trust',
    'Not crypto-looking', 'Not toy-like', 'Calm financial dashboard feeling',
    'Clear cards', 'Clear badges', 'Readable tables', 'Subtle motion only',
]

DESIGN_PRINCIPLES = [
    {
        'number': 1,
        'title': 'Evidence-first interface',
        'description': 'Every AI recommendation should show:',
        'items': [
            'Evidence source', 'Confidence', 'Evidence quality', 'Missing data',
            'Human approval status', 'No Harm Gate status',
        ],
    },
    {
        'number': 2,
        'title': 'One project, one story',
        'description': (
            'Each project page should show: asset → problem → evidence → risk → '
            'playbook → finance → supplier/funding → MRV → badges → next action.'
        ),
        'items': [],
    },
    {
        'number': 3,
        'title': 'Role-based simplicity',
        'description': (
            'Investor, government, supplier, sponsor, engineer and internal EcoIQ user '
            'should each see the most relevant view.'
        ),
        'items': [],
    },
    {
        'number': 4,
        'title': 'Mobile-first inspection',
        'description': (
            'Field evidence capture must work on iPhone, iPad, Android, Mac, Windows, '
            'Teams and PWA.'
        ),
        'items': [],
    },
    {
        'number': 5,
        'title': 'Trust by design',
        'description': 'Every page should clearly separate:',
        'items': [
            'Draft vs verified', 'Estimated vs MRV verified', 'Public vs private',
            'AI hypothesis vs expert reviewed', 'Microsoft-ready vs Microsoft-certified',
        ],
    },
]

UI_SCREENS = [
    {
        'number': 1,
        'title': 'Command Centre Dashboard',
        'items': [
            'Finance-ready projects', 'High-harm assets', 'Verified impact',
            'Missing evidence', 'No Harm alerts', 'Project pipeline', 'Country map',
            'Kanban stages', 'Morning briefing',
        ],
    },
    {
        'number': 2,
        'title': 'Asset Passport Page',
        'items': [
            'Asset summary', 'Owner', 'Location', 'Photos', 'Documents', 'Sensor data',
            'Risks', 'Playbook match', 'Finance readiness', 'MRV status', 'Trust badges',
            'Next action',
        ],
    },
    {
        'number': 3,
        'title': 'Country Transition Atlas',
        'items': [
            'Country cards', 'Interactive map', 'Finance-ready clusters',
            'Highest-harm zones', 'Highest-impact opportunities', 'Verified impact projects',
            'Filters by country, sector, asset type, MRV status and funding status',
        ],
    },
    {
        'number': 4,
        'title': 'Knowledge Graph',
        'items': [
            'Graph filters', 'Relationship map', 'Node details', 'Evidence trace',
            'Missing links', 'No Harm risk paths', 'Process improvement recommendations',
        ],
    },
    {
        'number': 5,
        'title': 'Mobile Inspection Mode',
        'items': [
            'Start inspection', 'Take photo', 'Record video', 'Scan meter', 'Upload bill',
            'Add voice note', 'AI photo diagnosis', 'Create Asset Passport',
            'Send to Teams for approval',
        ],
    },
    {
        'number': 6,
        'title': 'Public Trust Portal',
        'items': [
            'Verified impact map', 'Public MRV registry', 'Before/after stories',
            'Country progress', 'Sponsor impact pages', 'Public-safe summaries only',
        ],
    },
]

STITCH_PROMPTS = [
    {
        'number': 1,
        'title': 'Command Centre Dashboard',
        'prompt': (
            'Create an enterprise SaaS dashboard for EcoIQ, an industrial modernisation '
            'intelligence platform. The screen should show a dark institutional theme '
            'with emerald and cyan accents. Design a high-trust Microsoft-ready dashboard '
            'for investors, governments and industrial operators. Include top KPI cards '
            'for finance-ready projects, high-harm assets, verified impact, missing '
            'evidence and No Harm Gate alerts. Add a central project pipeline table, a '
            'country/asset map, a Kanban project status view, and a morning briefing '
            'panel. The interface should feel like Power BI + enterprise command centre, '
            'evidence-first, not crypto-looking, not toy-like, mobile-friendly and '
            'professional.'
        ),
    },
    {
        'number': 2,
        'title': 'Asset Passport Page',
        'prompt': (
            'Create an Asset Passport page for EcoIQ. The design should show one '
            'industrial asset, such as Boiler House #3, with a dark institutional SaaS '
            'layout, emerald/cyan accents and high-trust evidence-first design. Left '
            'panel: asset summary, owner, location, sector, condition and risk level. '
            'Middle panel: photos, documents, sensor readings, energy bills and evidence '
            'quality. Right panel: risks, recommended playbook, finance readiness, MRV '
            'status, trust badges and No Harm Gate. Bottom panel: timeline, missing data '
            'and next actions. Make it clear for engineers, investors and municipalities. '
            'The design should be mobile-friendly and Microsoft ecosystem-ready.'
        ),
    },
    {
        'number': 3,
        'title': 'Country Transition Atlas',
        'prompt': (
            'Create a Country Transition Atlas interface for EcoIQ. It should show '
            'Kazakhstan, United Kingdom, Saudi Arabia and Türkiye as portfolio views. Use '
            'a dark institutional enterprise SaaS style with emerald/cyan accents. Main '
            'view: interactive map with asset markers for boiler houses, factories, '
            'mines, farms, water systems and public buildings. Add filters for country, '
            'region, sector, asset type, finance readiness, MRV status and No Harm Gate '
            'alerts. Include cards for highest-harm assets, highest-impact opportunities, '
            'finance-ready projects and verified impact. The design should feel like a '
            'strategic Power BI/geospatial dashboard for governments, development banks '
            'and investors.'
        ),
    },
    {
        'number': 4,
        'title': 'Knowledge Graph',
        'prompt': (
            'Create a Knowledge Graph and Relationship Map UI for EcoIQ. The screen '
            'should show relationships between assets, companies, suppliers, funders, '
            'evidence, risks, projects, countries, Maqasid/Mizan principles, MRV claims '
            'and verified impact. Use a dark institutional theme with emerald/cyan '
            'accents, high-trust enterprise SaaS styling and a Microsoft-ready feel. Left '
            'panel: filters by country, asset type, evidence quality, risk, badge, MRV '
            'status and Maqasid principle. Centre: interactive node-link graph. Right '
            'panel: selected node details with linked evidence, risks, next action, No '
            'Harm Gate status and human approval status. Bottom: missing links and '
            'process improvement recommendations. Not crypto-looking, not toy-like.'
        ),
    },
    {
        'number': 5,
        'title': 'Mobile Inspection Mode',
        'prompt': (
            'Create a mobile-first EcoIQ inspection interface for iPhone and iPad. The '
            'user is an engineer or municipal inspector visiting a boiler house, '
            'factory, farm or water system. Use dark institutional styling, emerald/cyan '
            'accents and simple large touch-friendly controls. Screens should include: '
            'Start Inspection, Take Photo, Record Video, Scan Meter, Upload Bill, Add '
            'Voice Note, AI Photo Diagnosis, Create Asset Passport, Send to Teams for '
            'Approval. Show evidence quality, AI hypothesis warning, missing data '
            'checklist and No Harm Gate status. The design should feel professional, '
            'field-ready, accessible and Microsoft/Teams-ready.'
        ),
    },
    {
        'number': 6,
        'title': 'Public Trust Portal',
        'prompt': (
            'Create a public-facing EcoIQ impact portal. It should show approved, '
            'non-sensitive, MRV-supported public summaries only. Use a clean dark '
            'institutional style with emerald/cyan accents, trustworthy public-sector '
            'feel and no sensitive data exposure. Include a Verified Impact Map, Public '
            'MRV Registry, Before/After Impact Stories, Country Progress Cards for '
            'Kazakhstan, UK, Saudi Arabia and Türkiye, and Sponsor/CSR Impact Pages. Show '
            'labels such as MRV Verified, Expert Reviewed, Public Summary Approved, Needs '
            'Verification and Sensitive Data Redacted. Make it clear that estimated '
            'impact and verified impact are different. The design should build public '
            'trust without looking like crypto or marketing hype.'
        ),
    },
]

MICROSOFT_PARTNER_PACK_ITEMS = [
    'Teams approval cards', 'Power BI embedded dashboard concept',
    'SharePoint evidence pack view', 'Microsoft Fabric data layer card',
    'Azure Digital Twins asset map concept', 'Fluent UI-inspired controls',
    'Adaptive Cards for approvals', 'Microsoft Graph document permissions concept',
]

FRONTEND_PROCESS_IMPROVEMENT_ITEMS = [
    'Reducing user confusion', 'Showing missing evidence earlier',
    'Making next actions obvious', 'Making finance readiness visible',
    'Making MRV status visible', 'Making public/private boundaries clear',
    'Making trust badges visible', 'Helping field teams upload correct evidence',
    'Helping investors understand project readiness',
    'Helping governments see country priorities visually',
    'Helping Microsoft partners understand integration points',
]

UX_QUALITY_CHECKLIST = [
    'Is the page clear in 5 seconds?', 'Is the next action obvious?',
    'Is evidence visible?', 'Is uncertainty visible?',
    'Is public/private status clear?', 'Is MRV verified separated from estimated?',
    'Is the page mobile-friendly?', 'Are tables readable?', 'Are CTAs clear?',
    'Is it enterprise and high-trust?', 'Does it avoid fake futuristic/crypto style?',
    'Does it avoid unsupported Microsoft partnership claims?',
]

SAFETY_PRINCIPLES = [
    'Frontend design must not hide uncertainty, missing evidence or risk.',
    'Visual design must not overstate impact, finance readiness, MRV verification or Microsoft affiliation.',
    'Public UI must protect sensitive data.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
    'Verified impact must be clearly separated from estimated impact.',
    'Google Stitch is for prototyping; production UI must be implemented, reviewed and tested in code.',
]

CTA_BUTTONS = [
    {'label': 'Open Design System', 'anchor': '#frontend-stacks'},
    {'label': 'Copy Google Stitch Prompts', 'anchor': '#stitch-prompts'},
    {'label': 'View Command Centre Mockup', 'anchor': '#screen-1'},
    {'label': 'View Asset Passport UI', 'anchor': '#screen-2'},
    {'label': 'View Country Atlas UI', 'anchor': '#screen-3'},
    {'label': 'View Knowledge Graph UI', 'anchor': '#screen-4'},
    {'label': 'View Mobile Inspection UI', 'anchor': '#screen-5'},
    {'label': 'View Public Trust Portal UI', 'anchor': '#screen-6'},
    {'label': 'View Microsoft Partner UI Pack', 'anchor': '#microsoft-partner-frontend-pack'},
    {'label': 'Export Component Library', 'url_name': 'data_room_evidence_vault:overview'},
]


def overview(request):
    return render(request, 'frontend_experience_google_stitch_design_system/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_purpose': CORE_PURPOSE,
        'frontend_stacks': FRONTEND_STACKS,
        'visual_style': VISUAL_STYLE,
        'design_principles': DESIGN_PRINCIPLES,
        'ui_screens': UI_SCREENS,
        'stitch_prompts': STITCH_PROMPTS,
        'microsoft_partner_pack_items': MICROSOFT_PARTNER_PACK_ITEMS,
        'frontend_process_improvement_items': FRONTEND_PROCESS_IMPROVEMENT_ITEMS,
        'ux_quality_checklist': UX_QUALITY_CHECKLIST,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })
