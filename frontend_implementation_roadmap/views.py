from django.shortcuts import render

# Connected EcoIQ modules — the roadmap sequences delivery across all of these
CONNECTED_MODULES = [
    {'name': 'Frontend Experience & Google Stitch Design System', 'role': 'Supplies the visual style, library stack and Stitch prompt library this roadmap sequences.'},
    {'name': 'Visual Dashboard UI Upgrade', 'role': 'Supplies the current /platform/ hero, module directory and trust badge components.'},
    {'name': 'Microsoft Ecosystem Core Stack', 'role': 'Supplies the Microsoft-ready building blocks Phase 4 sequences into the product.'},
    {'name': 'API & Integration Layer', 'role': 'Supplies the API surface the Next.js frontend in Phase 3 would consume.'},
    {'name': 'Command Centre', 'role': 'First Priority 2 target for interactive dashboards and later a Next.js app.'},
    {'name': 'Asset Passport', 'role': 'First Priority 2 target for a dedicated Next.js workspace.'},
    {'name': 'Country Transition Atlas', 'role': 'Target for map filters in Phase 2 and a full map explorer in Phase 3.'},
    {'name': 'Knowledge Graph & Relationship Map', 'role': 'Target for a Cytoscape.js teaser in Phase 2 and a React Flow explorer in Phase 3.'},
    {'name': 'Mobile / iPad Inspection Mode', 'role': 'Target for a Next.js PWA in Phase 3.'},
    {'name': 'Public Trust & Impact Portal', 'role': 'Stays in Django first — public, low-interactivity, high-trust surface.'},
    {'name': 'Product Analytics & KPI Engine', 'role': 'Target for ECharts dashboards in Phase 2.'},
    {'name': 'Security, Privacy & Compliance Centre', 'role': 'Governs permission checks for every phase, including Microsoft login.'},
    {'name': 'Certification & Trust Badge Engine', 'role': 'Supplies the trust badge components reused across every phase.'},
]

CORE_PURPOSE = 'Turn EcoIQ visual design into an executable frontend delivery plan.'

ROADMAP_PHASES = [
    {
        'number': 1,
        'title': 'Phase 1 — Strengthen Django Frontend',
        'goal': 'Improve current EcoIQ quickly without a full rewrite.',
        'use': [
            'Django templates', 'Tailwind CSS', 'HTMX', 'Alpine.js', 'Apache ECharts',
            'Leaflet / MapLibre', 'Cytoscape.js', 'PDF.js',
        ],
        'best_for': [
            'Platform pages', 'Module overview pages', 'Public Trust Portal',
            'Basic dashboards', 'Static investor/government demos', 'Rapid iteration',
        ],
        'deliverables': [
            'Improved /platform/', 'Reusable module cards', 'Trust badge components',
            'Evidence cards', 'Dashboard hero', 'Map teaser', 'Graph teaser',
            'Mobile responsive templates',
        ],
        'workflow': [],
        'important': '',
    },
    {
        'number': 2,
        'title': 'Phase 2 — Interactive Django Dashboards',
        'goal': 'Add real interactivity without switching frontend stack yet.',
        'use': [
            'HTMX partial updates', 'Alpine.js filters', 'ECharts dashboards',
            'MapLibre maps', 'Cytoscape graph views', 'SortableJS Kanban',
            'PDF.js evidence viewer',
        ],
        'best_for': [
            'Command Centre', 'Data Room', 'Knowledge Graph', 'Country Atlas',
            'Product Analytics', 'AI Agent Operations Console',
        ],
        'deliverables': [
            'Filterable module directory', 'Project pipeline Kanban', 'Evidence viewer',
            'Graph relationship explorer', 'Country map filters', 'Dashboard charts',
        ],
        'workflow': [],
        'important': '',
    },
    {
        'number': 3,
        'title': 'Phase 3 — Next.js SaaS Frontend',
        'goal': 'Build premium SaaS frontend when platform logic is mature.',
        'use': [
            'Next.js', 'React', 'TypeScript', 'Tailwind CSS', 'shadcn/ui',
            'Framer Motion', 'React Flow', 'TanStack Table', 'TanStack Query',
            'Apache ECharts', 'MapLibre GL', 'deck.gl', 'pdf.js', 'Cytoscape.js / Sigma.js',
        ],
        'best_for': [
            'Logged-in application', 'Enterprise dashboards', 'Heavy graph/map interaction',
            'Real-time agent console', 'Advanced table filtering', 'Multi-role UI',
            'API-driven frontend',
        ],
        'deliverables': [
            'Next.js app shell', 'Role-based navigation', 'React Flow Knowledge Graph',
            'Interactive Country Atlas', 'Command Centre app', 'Mobile Inspection PWA',
            'API client layer', 'Authentication integration',
        ],
        'workflow': [],
        'important': '',
    },
    {
        'number': 4,
        'title': 'Phase 4 — Microsoft Enterprise Frontend',
        'goal': 'Make EcoIQ familiar and useful for Microsoft ecosystem partners and enterprise customers.',
        'use': [
            'Fluent UI React', 'Microsoft Teams Toolkit', 'Adaptive Cards',
            'Power BI Embedded', 'MSAL React', 'Microsoft Graph SDK',
            'SharePoint integration', 'Dynamics 365 integration concept',
            'Microsoft Fabric dashboard concept',
        ],
        'best_for': [
            'Teams approval workflows', 'Power BI executive dashboards',
            'SharePoint evidence packs', 'Dynamics sales/customer pipeline',
            'Enterprise login', 'Microsoft partner demos',
        ],
        'deliverables': [
            'Teams approval card templates', 'Power BI dashboard embeds',
            'SharePoint Data Room pack concept', 'Dynamics CRM sync concept',
            'Microsoft login roadmap', 'Fluent UI component pack',
        ],
        'workflow': [],
        'important': '',
    },
    {
        'number': 5,
        'title': 'Phase 5 — Google Stitch to Production Workflow',
        'goal': 'Use Google Stitch for fast UI concepts, then convert designs into tested code.',
        'use': [],
        'best_for': [],
        'deliverables': [],
        'workflow': [
            'Generate mockup in Google Stitch.',
            'Review for EcoIQ design rules.',
            'Convert layout to Django template or Next.js component.',
            'Add real data fields.',
            'Add tests.',
            'Verify route.',
            'Check no unsupported claims.',
            'Ship via PR.',
        ],
        'important': 'Google Stitch is for design prototyping, not production guarantee.',
    },
]

PAGE_DECISION_TABLE = {
    'django_first': [
        '/', '/platform/', 'Module overview pages', 'Public Trust Portal',
        'Revenue/Pricing pages', 'Executive Briefing pages', 'Frontend Design System pages',
    ],
    'django_interactive': [
        'Command Centre', 'Country Atlas', 'Knowledge Graph', 'Data Room',
        'Product Analytics', 'AI Agent Operations Console',
    ],
    'nextjs_later': [
        'Logged-in Command Centre app', 'Asset Passport workspace', 'Mobile Inspection PWA',
        'Knowledge Graph explorer', 'Country Atlas explorer', 'Data Room file manager',
        'Agent Operations Console', 'Customer Success dashboard',
    ],
    'microsoft_later': [
        'Teams approval queue', 'Power BI dashboards', 'SharePoint evidence packs',
        'Dynamics CRM pipeline', 'Fabric analytics workspace',
    ],
}

LIBRARY_MATRIX = [
    {'name': 'Tailwind CSS', 'use_case': 'Utility-first styling for every Django page', 'phase': 'Phase 1', 'priority': 'High', 'risk': 'Low', 'why': 'Fast, consistent styling without a build pipeline change.'},
    {'name': 'HTMX', 'use_case': 'Partial page updates without full reloads', 'phase': 'Phase 2', 'priority': 'High', 'risk': 'Low', 'why': 'Adds interactivity while keeping Django as the source of truth.'},
    {'name': 'Alpine.js', 'use_case': 'Lightweight client-side filters and toggles', 'phase': 'Phase 2', 'priority': 'Medium', 'risk': 'Low', 'why': 'Small footprint, no build step, pairs naturally with HTMX.'},
    {'name': 'Apache ECharts', 'use_case': 'Dashboard charts and KPI visualisations', 'phase': 'Phase 2', 'priority': 'High', 'risk': 'Low', 'why': 'Mature, free, works in both Django and Next.js.'},
    {'name': 'MapLibre', 'use_case': 'Country Atlas interactive maps', 'phase': 'Phase 2', 'priority': 'High', 'risk': 'Medium', 'why': 'Open-source map rendering without a vendor lock-in.'},
    {'name': 'Leaflet', 'use_case': 'Lightweight asset/project map markers', 'phase': 'Phase 1', 'priority': 'Medium', 'risk': 'Low', 'why': 'Simple, well-documented, good fallback to MapLibre.'},
    {'name': 'Cytoscape.js', 'use_case': 'Knowledge Graph relationship rendering', 'phase': 'Phase 2', 'priority': 'High', 'risk': 'Medium', 'why': 'Purpose-built for node-link graph interaction.'},
    {'name': 'Sigma.js', 'use_case': 'Large-scale graph rendering alternative', 'phase': 'Phase 3', 'priority': 'Low', 'risk': 'Medium', 'why': 'Better performance at very high node counts, if ever needed.'},
    {'name': 'PDF.js', 'use_case': 'In-browser evidence document viewer', 'phase': 'Phase 1', 'priority': 'Medium', 'risk': 'Low', 'why': 'Lets reviewers preview evidence without downloading files.'},
    {'name': 'SortableJS', 'use_case': 'Drag-and-drop Kanban pipeline stages', 'phase': 'Phase 2', 'priority': 'Medium', 'risk': 'Low', 'why': 'Small library that unlocks a familiar Kanban interaction.'},
    {'name': 'Next.js', 'use_case': 'Premium SaaS application shell', 'phase': 'Phase 3', 'priority': 'High', 'risk': 'Medium', 'why': 'Industry-standard React framework with routing and SSR built in.'},
    {'name': 'React', 'use_case': 'Component model for the SaaS frontend', 'phase': 'Phase 3', 'priority': 'High', 'risk': 'Medium', 'why': 'Required foundation for Next.js and the wider component ecosystem.'},
    {'name': 'TypeScript', 'use_case': 'Type-safe frontend code across the SaaS app', 'phase': 'Phase 3', 'priority': 'High', 'risk': 'Low', 'why': 'Reduces runtime errors as the frontend team and codebase grow.'},
    {'name': 'shadcn/ui', 'use_case': 'Accessible, themeable component primitives', 'phase': 'Phase 3', 'priority': 'Medium', 'risk': 'Low', 'why': 'Fast to theme into the dark institutional style without lock-in.'},
    {'name': 'React Flow', 'use_case': 'Interactive Knowledge Graph explorer', 'phase': 'Phase 3', 'priority': 'High', 'risk': 'Medium', 'why': 'Purpose-built React library for node-link diagrams.'},
    {'name': 'TanStack Table', 'use_case': 'Advanced filtering/sorting for large tables', 'phase': 'Phase 3', 'priority': 'Medium', 'risk': 'Low', 'why': 'Handles investor memo and data room tables at scale.'},
    {'name': 'TanStack Query', 'use_case': 'Data fetching and caching against the API layer', 'phase': 'Phase 3', 'priority': 'High', 'risk': 'Low', 'why': 'Keeps the SaaS frontend in sync with the API & Integration Layer.'},
    {'name': 'Framer Motion', 'use_case': 'Subtle motion for cards and transitions', 'phase': 'Phase 3', 'priority': 'Low', 'risk': 'Low', 'why': 'Adds polish without becoming a distracting animation layer.'},
    {'name': 'Fluent UI React', 'use_case': 'Microsoft-style enterprise components', 'phase': 'Phase 4', 'priority': 'Medium', 'risk': 'Medium', 'why': 'Makes EcoIQ feel native to Microsoft enterprise reviewers.'},
    {'name': 'Power BI Embedded', 'use_case': 'Executive dashboard embeds', 'phase': 'Phase 4', 'priority': 'Medium', 'risk': 'High', 'why': 'High business value but requires a licensing/embedding decision.'},
    {'name': 'Microsoft Teams Toolkit', 'use_case': 'Teams approval card workflows', 'phase': 'Phase 4', 'priority': 'Medium', 'risk': 'Medium', 'why': 'Lets approvals happen inside a tool reviewers already use daily.'},
    {'name': 'MSAL React', 'use_case': 'Microsoft enterprise login integration', 'phase': 'Phase 4', 'priority': 'Low', 'risk': 'High', 'why': 'Only needed once real Microsoft enterprise customers require SSO.'},
    {'name': 'Microsoft Graph SDK', 'use_case': 'Document and permission access via Microsoft 365', 'phase': 'Phase 4', 'priority': 'Low', 'risk': 'High', 'why': 'High integration value, but depends on confirmed partner access.'},
]

DESIGN_TO_CODE_RULES = [
    'Do not copy mockups blindly.',
    'Convert every visual component into tested template/component code.',
    'Every route must return 200.',
    'Every route must avoid raw Django template tags.',
    'Every module link must point to a real route.',
    'Every badge must have clear meaning.',
    'Every impact claim must distinguish estimated vs verified.',
    'Every Microsoft reference must avoid unsupported certification/partner claims.',
    'Every Maqasid/Mizan reference must remain ethical decision-support, not fatwa.',
    'Public views must hide sensitive data.',
]

UI_PRIORITIES = [
    {
        'number': 1,
        'items': [
            'Platform dashboard', 'Trust badge components', 'Module directory',
            'Navigation', 'CTA consistency',
        ],
    },
    {
        'number': 2,
        'items': [
            'Command Centre dashboard', 'Asset Passport UI', 'Country Atlas map',
            'Knowledge Graph teaser', 'Public Trust Portal',
        ],
    },
    {
        'number': 3,
        'items': [
            'Mobile Inspection', 'AI Agent Operations Console',
            'Data Room Evidence Viewer', 'Product Analytics dashboard',
        ],
    },
    {
        'number': 4,
        'items': [
            'Next.js PWA', 'Teams approvals', 'Power BI embedded dashboards',
            'SharePoint evidence packs',
        ],
    },
]

IMPLEMENTATION_PLAN = [
    {
        'days': 30,
        'items': [
            'Complete Django visual upgrade', 'Trust badges', 'Platform grouping',
            'Google Stitch prompt library', 'Map/graph visual teasers',
        ],
    },
    {
        'days': 60,
        'items': [
            'Interactive dashboards with HTMX/Alpine/ECharts', 'Map filters',
            'Graph filters', 'Evidence viewer', 'Kanban pipeline',
        ],
    },
    {
        'days': 90,
        'items': [
            'Decide Next.js app structure', 'Build API-first frontend prototype',
            'Create Microsoft Teams approval demo', 'Create Power BI dashboard demo',
        ],
    },
]

MICROSOFT_DEMO = {
    'title': 'EcoIQ Microsoft-ready Industrial Intelligence Demo',
    'flow': [
        'Open Command Centre.',
        'Show Country Atlas.',
        'Click Asset Passport.',
        'Open evidence panel.',
        'Show Knowledge Graph trace.',
        'Show Finance Ready badge.',
        'Send approval to Teams.',
        'Show Power BI dashboard concept.',
        'Export evidence pack to SharePoint.',
        'Show Public Trust summary.',
    ],
    'wording_note': (
        'Use wording: "designed to integrate with Microsoft ecosystem" — not '
        '"Microsoft certified" or "official partner".'
    ),
}

STITCH_PROMPT_CATEGORIES = [
    'Dashboard prompts', 'Asset page prompts', 'Map prompts', 'Graph prompts',
    'Mobile prompts', 'Public portal prompts', 'Microsoft partner UI prompts',
]

STITCH_PROMPT_FIELDS = [
    'Screen name', 'Target user', 'Layout', 'Visual style', 'Required components',
    'Forbidden style', 'Production conversion notes',
]

SAFETY_PRINCIPLES = [
    'Frontend roadmap is an implementation plan, not a guarantee that all integrations are already live.',
    'Microsoft ecosystem-ready does not mean Microsoft certified or Microsoft partner.',
    'Google Stitch is used for prototyping and visual direction, not production deployment.',
    'Public interfaces must protect sensitive data.',
    'Trust badges are readiness/status labels unless formal certification is separately obtained.',
    'Maqasid/Mizan remains ethical decision-support, not a fatwa.',
    'Verified impact must remain separate from estimated impact.',
]

CTA_BUTTONS = [
    {'label': 'Open Frontend Roadmap', 'anchor': '#roadmap-phases'},
    {'label': 'View Phase 1 Django Plan', 'anchor': '#phase-1'},
    {'label': 'View Next.js SaaS Plan', 'anchor': '#phase-3'},
    {'label': 'View Microsoft UI Plan', 'anchor': '#phase-4'},
    {'label': 'View Google Stitch Workflow', 'anchor': '#phase-5'},
    {'label': 'View Library Matrix', 'anchor': '#library-matrix'},
    {'label': 'Open Command Centre UI Plan', 'url_name': 'command_centre:overview'},
    {'label': 'Open Mobile PWA Plan', 'url_name': 'mobile_inspection_mode:overview'},
    {'label': 'Export Frontend Roadmap', 'url_name': 'data_room_evidence_vault:overview'},
]


def overview(request):
    return render(request, 'frontend_implementation_roadmap/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_purpose': CORE_PURPOSE,
        'roadmap_phases': ROADMAP_PHASES,
        'page_decision_table': PAGE_DECISION_TABLE,
        'library_matrix': LIBRARY_MATRIX,
        'design_to_code_rules': DESIGN_TO_CODE_RULES,
        'ui_priorities': UI_PRIORITIES,
        'implementation_plan': IMPLEMENTATION_PLAN,
        'microsoft_demo': MICROSOFT_DEMO,
        'stitch_prompt_categories': STITCH_PROMPT_CATEGORIES,
        'stitch_prompt_fields': STITCH_PROMPT_FIELDS,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })
