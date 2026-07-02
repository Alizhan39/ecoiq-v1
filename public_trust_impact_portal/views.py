from django.shortcuts import render

# Connected EcoIQ modules — the Portal is the approved, public-facing window into verified work
CONNECTED_MODULES = [
    {'name': 'Impact MRV Layer', 'role': 'Supplies the verified before/after evidence behind every public claim.'},
    {'name': 'Data Room & Evidence Vault', 'role': 'Holds the underlying evidence that public summaries are drawn from and redacted against.'},
    {'name': 'Governance & Expert Review Board', 'role': 'Approves every public summary before it is published.'},
    {'name': 'Executive Briefing & Board Pack Generator', 'role': 'Supplies the approved content reused in public-facing reports.'},
    {'name': 'Portfolio & Country Transition Atlas', 'role': 'Supplies the country and sector data behind country progress pages.'},
    {'name': 'Command Centre', 'role': 'Flags which projects are eligible for public reporting.'},
    {'name': 'Asset Passport', 'role': 'Supplies the structured asset record behind each public project.'},
    {'name': 'Revenue & Pricing Engine', 'role': 'Sells the public impact reports and sponsor pages this portal generates.'},
    {'name': 'Supplier & Funding Marketplace', 'role': 'Supplies funding routes surfaced on sponsor pages, with approval required.'},
    {'name': 'Microsoft Ecosystem Core Stack', 'role': 'Provides the agent, storage and dashboard building blocks a production portal would run on.'},
    {'name': 'API & Integration Layer', 'role': 'Exposes the public MRV registry and impact metrics through the API.'},
    {'name': 'Maqasid/Mizan ethical scoring', 'role': 'Explains the ethical meaning of an impact story without acting as a religious ruling.'},
    {'name': 'No Harm Gate', 'role': 'Blocks publication until sensitive data, consent and evidence checks pass.'},
]

CORE_PURPOSE = 'Build public trust through transparent, approved and evidence-backed impact reporting.'

VERIFIED_IMPACT_MAP_SHOWS = [
    'Approved public project locations', 'Country/region impact',
    'Verified clean heating projects', 'Verified industrial efficiency projects',
    'Water/agriculture projects', 'Public building improvements',
]
PUBLIC_MARKER_FIELDS = [
    'Project type', 'Country / region', 'Impact category', 'Verification status',
    'Public summary', 'Before/after headline', 'Maqasid/Mizan meaning',
    'Sponsor / partner only if approved',
]
DO_NOT_SHOW_ITEMS = [
    'Exact sensitive household coordinates', 'Private documents',
    'Personal names without consent', 'Raw financial models', 'Supplier contracts',
    'Sensitive industrial data', 'Unapproved photos/videos',
]

BEFORE_AFTER_STORY_FIELDS = [
    'Problem before', 'Action taken', 'Result after', 'Verified impact status',
    'Public photos if approved', 'Community benefit', 'Maqasid/Mizan meaning',
    'Evidence quality label', 'Date verified',
]

COUNTRY_PROGRESS_COUNTRIES = ['Kazakhstan', 'United Kingdom', 'Saudi Arabia', 'Türkiye']
COUNTRY_PROGRESS_FIELDS = [
    'Projects discovered', 'Approved public summaries', 'Verified impact projects',
    'Finance-ready pipeline summary', 'Sectors covered', 'Highest public impact themes',
    'Sponsor opportunities where approved', 'Verified totals only where evidence supports them',
]

SPONSOR_CSR_SHOWS = [
    'Sponsored projects', 'Households / assets helped', 'Before/after proof',
    'Verified impact summaries', 'MRV status', 'Next funding opportunities',
]
SPONSOR_CSR_NOTE = 'Do not imply endorsement by any sponsor unless confirmed and approved.'

COMMUNITY_IMPACT_SHOWS = [
    'Households helped', 'Public buildings improved', 'Heating harm reduced',
    'Comfort improved', 'Pollution reduced where evidence supports it', 'Water saved',
    'Waste reduced', 'Community benefit',
]
COMMUNITY_IMPACT_NOTE = 'Only use verified or clearly labelled estimated data.'

PUBLIC_MRV_REGISTRY_FIELDS = [
    'Public project ID', 'Country', 'Region', 'Project type', 'Action completed',
    'Verification status', 'Evidence quality', 'Impact metrics', 'Approval date',
    'Public report link',
]

PUBLIC_PROJECT_PIPELINE_LABELS = [
    'Verified Impact', 'In Progress', 'Estimated Impact', 'Needs Verification',
    'Sponsor Ready', 'Finance Ready',
]

PUBLIC_TRUST_LABELS = [
    'MRV Verified', 'Expert Reviewed', 'Public Summary Approved',
    'Evidence Quality: Strong', 'Evidence Quality: Medium', 'In Progress',
    'Needs Verification', 'Estimated Impact', 'Sensitive Data Redacted',
    'Sponsor Approved', 'Community Consent Recorded',
]

PUBLIC_IMPACT_METRICS = [
    'Projects verified', 'Households helped', 'Public buildings improved',
    'Assets modernised', 'kWh saved where verified', 'Fuel saved where verified',
    'CO2 reduced where verified', 'Water saved where verified',
    'Cost savings where approved for public release', 'Clean heating projects completed',
    'Sponsor-backed projects', 'Maqasid/Mizan improvement summary',
]

APPROVAL_WORKFLOW = [
    'MRV result generated', 'Evidence reviewed', 'Governance Board approves public summary',
    'Sensitive data removed', 'Public wording checked', 'Maqasid/Mizan wording reviewed',
    'Sponsor/partner approval checked if named', 'Public impact page published',
    'Impact portal updated',
]

EXAMPLE_PROJECTS = [
    {
        'project': 'Village Clean Heating Pilot',
        'country': 'Kazakhstan',
        'before': 'Coal-based heating, fuel burden and visible smoke risk.',
        'action': 'Clean heating upgrade and monitoring.',
        'after': 'Improved heating comfort and reduced visible smoke risk.',
        'status': 'In Progress — Needs Final Verification.',
        'public_label': '',
        'maqasid_mizan_meaning': 'Protect health, reduce harm and restore balance in '
                                  'household energy use.',
    },
    {
        'project': 'Factory Compressed Air Optimisation',
        'country': 'United Kingdom',
        'before': 'Compressor running continuously and high electricity use.',
        'action': 'Leak detection, pressure optimisation and monitoring.',
        'after': 'Reduced electricity waste and improved operational visibility.',
        'status': 'MRV Verified.',
        'public_label': 'Verified Impact',
        'maqasid_mizan_meaning': '',
    },
    {
        'project': 'Water Recycling Upgrade',
        'country': 'Türkiye',
        'before': 'High water withdrawal and weak monitoring.',
        'action': 'Metering, leak detection and water reuse pathway.',
        'after': 'Lower water waste risk and improved water accountability.',
        'status': 'Expert Reviewed — MRV in progress.',
        'public_label': '',
        'maqasid_mizan_meaning': '',
    },
    {
        'project': 'Industrial Cooling Efficiency',
        'country': 'Saudi Arabia',
        'before': 'High energy intensity from cooling demand.',
        'action': 'Energy assessment, supplier matching and finance memo.',
        'after': 'Project ready for investment review.',
        'status': 'Finance Ready — Not Yet Verified Impact.',
        'public_label': '',
        'maqasid_mizan_meaning': '',
    },
]

MAQASID_MIZAN_PUBLIC_EXPLANATION = (
    'EcoIQ uses Maqasid/Mizan as an ethical decision-support lens. It helps explain '
    'whether a project reduces harm, protects health, reduces waste, supports communities '
    'and restores balance between resource use and benefit. It is not a fatwa or '
    'religious ruling.'
)

MICROSOFT_INTEGRATION_ITEMS = [
    'Power BI for approved aggregated metrics', 'SharePoint for approved public reports',
    'Microsoft Fabric for aggregated portfolio data',
    'Azure Maps / geospatial concept for country impact maps',
    'Teams and Power Automate for approval workflows',
    'Azure AI for generating public summaries from approved evidence',
    'Presidio-style privacy tooling for detecting sensitive data before publication',
]

AMANAH_INTEGRATION_ITEMS = [
    'Find projects ready for public reporting', 'Flag impact claims without MRV proof',
    'Detect sensitive data before publication', 'Prepare draft public summaries',
    'Identify sponsor reports ready for approval', 'Prepare country progress updates',
]
AMANAH_MORNING_BRIEFING_EXAMPLE = (
    '2 projects are ready for public impact summaries, 1 sponsor page needs approval, '
    '3 impact claims need stronger MRV evidence, and Kazakhstan clean heating progress '
    'can be updated after review.'
)

NO_HARM_GATE_PUBLIC_ITEMS = [
    'Is the impact verified or clearly labelled estimated?',
    'Is sensitive data removed?',
    'Are photos approved?',
    'Is community consent recorded where needed?',
    'Are sponsor names approved?',
    'Are claims supported by MRV evidence?',
    'Is Maqasid/Mizan wording safe and not overclaimed?',
    'Is human approval recorded?',
    'Could publication harm a community, supplier or project owner?',
    'Are exact locations safe to show?',
]

SAFETY_PRINCIPLES = [
    'Public portal content must be approved before publication.',
    'EcoIQ must not publish private, personal, financial, supplier or sensitive '
    'industrial data without permission.',
    'Verified impact claims require MRV-backed evidence.',
    'Estimated or in-progress claims must be clearly labelled.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
    'Sponsor, partner or government names must not be shown without approval.',
    'The portal should prioritise transparency without creating reputational, privacy, '
    'security or community harm.',
]

CTA_BUTTONS = [
    {'label': 'Open Public Impact Portal', 'anchor': '#verified-impact-map'},
    {'label': 'Publish Verified Impact Story', 'anchor': '#before-after-stories'},
    {'label': 'Generate Public Summary', 'anchor': '#approval-workflow'},
    {'label': 'Review Public MRV Registry', 'anchor': '#public-mrv-registry'},
    {'label': 'Create Sponsor Impact Page', 'anchor': '#sponsor-csr-pages'},
    {'label': 'Update Country Progress', 'anchor': '#country-progress'},
    {'label': 'Export Public Impact Report', 'anchor': '#public-impact-metrics'},
    {'label': 'Send for Approval', 'url_name': 'governance_expert_review_board:overview'},
    {'label': 'Redact Sensitive Data', 'anchor': '#no-harm-gate-public'},
    {'label': 'View Verified Impact Map', 'anchor': '#verified-impact-map'},
]


def overview(request):
    return render(request, 'public_trust_impact_portal/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_purpose': CORE_PURPOSE,
        'verified_impact_map_shows': VERIFIED_IMPACT_MAP_SHOWS,
        'public_marker_fields': PUBLIC_MARKER_FIELDS,
        'do_not_show_items': DO_NOT_SHOW_ITEMS,
        'before_after_story_fields': BEFORE_AFTER_STORY_FIELDS,
        'country_progress_countries': COUNTRY_PROGRESS_COUNTRIES,
        'country_progress_fields': COUNTRY_PROGRESS_FIELDS,
        'sponsor_csr_shows': SPONSOR_CSR_SHOWS,
        'sponsor_csr_note': SPONSOR_CSR_NOTE,
        'community_impact_shows': COMMUNITY_IMPACT_SHOWS,
        'community_impact_note': COMMUNITY_IMPACT_NOTE,
        'public_mrv_registry_fields': PUBLIC_MRV_REGISTRY_FIELDS,
        'public_project_pipeline_labels': PUBLIC_PROJECT_PIPELINE_LABELS,
        'public_trust_labels': PUBLIC_TRUST_LABELS,
        'public_impact_metrics': PUBLIC_IMPACT_METRICS,
        'approval_workflow': APPROVAL_WORKFLOW,
        'example_projects': EXAMPLE_PROJECTS,
        'maqasid_mizan_public_explanation': MAQASID_MIZAN_PUBLIC_EXPLANATION,
        'microsoft_integration_items': MICROSOFT_INTEGRATION_ITEMS,
        'amanah_integration_items': AMANAH_INTEGRATION_ITEMS,
        'amanah_morning_briefing_example': AMANAH_MORNING_BRIEFING_EXAMPLE,
        'no_harm_gate_public_items': NO_HARM_GATE_PUBLIC_ITEMS,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })
