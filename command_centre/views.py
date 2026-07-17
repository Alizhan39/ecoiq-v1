"""
command_centre/views.py — DEPRECATED (feat/project-command-centre-primary-surface).

This app was a static, hardcoded-data mockup of a "Command Centre" vision
page — no models, no real queries, every list below is a plain Python
literal. A REAL, backend-connected Project Command Centre now exists at
capital_guardian.views.project_command_centre (see
capital_guardian/services/command_centre.py), which computes every value
it shows from live data.

Keeping both under the same "Command Centre" name was a genuine risk of
confusion (a technical reviewer could easily mistake this static page for
the real one). Per the founder's explicit instruction, this app is not
being deleted in this PR — only its public route is redirected to a real,
safe destination (the project directory), so every existing `{% url
'command_centre:overview' %}` reference elsewhere in the codebase
(templates/platform.html, governance_expert_review_board/views.py,
frontend_implementation_roadmap/views.py) keeps resolving via the same
URL name without any template changes. The template and data below
become unreachable dead code from this point on — left in place for a
future, separate cleanup PR once usage is proven absent, not deleted here.
"""
from django.shortcuts import redirect

# Connected EcoIQ modules — the Command Centre is the single operational view over all of them
CONNECTED_MODULES = [
    {'name': 'Mobile / iPad Inspection Mode', 'role': 'Feeds new field inspections into the pipeline.'},
    {'name': 'Asset Passport', 'role': 'Supplies the structured asset record shown for every project.'},
    {'name': 'Omnimodal Evidence Panel', 'role': 'Supplies the photo, video and document evidence behind each project.'},
    {'name': 'Industrial Playbook Library', 'role': 'Supplies the matched pathway shown at the Playbook Matched stage.'},
    {'name': 'Supplier & Funding Marketplace', 'role': 'Supplies supplier and funding status at the Supplier/Funding Matched stage.'},
    {'name': 'Institutional Finance Engine', 'role': 'Supplies CAPEX, OPEX, payback, IRR/NPV and finance fit for every project.'},
    {'name': 'Impact MRV Layer', 'role': 'Supplies MRV verification status and verified impact results.'},
    {'name': 'Amanah Autopilot', 'role': 'Runs the overnight scan that produces the Morning Command Briefing.'},
    {'name': 'Microsoft Ecosystem Core Stack', 'role': 'Provides the agent, data and dashboard building blocks a production command centre would run on.'},
    {'name': 'Power BI', 'role': 'Renders the pipeline, map and KPI dashboards.'},
    {'name': 'Teams', 'role': 'Delivers approval requests and stage-change notifications.'},
    {'name': 'Azure Digital Twins', 'role': 'Links each project to its digital twin asset relationships.'},
    {'name': 'Microsoft Fabric', 'role': 'Stores the unified project, asset and finance data.'},
    {'name': 'Dynamics 365', 'role': 'Tracks the supplier and funder pipeline behind each project.'},
]

CORE_PURPOSE = 'Turn EcoIQ into a live operating system for managing industrial modernisation projects.'

PIPELINE_STAGES = [
    {
        'number': 1,
        'title': 'Discovered',
        'description': 'New asset or opportunity identified from reports, photos, public '
                        'data, sensor alerts or Amanah Autopilot.',
    },
    {
        'number': 2,
        'title': 'Evidence Captured',
        'description': 'Photos, documents, bills, meter readings, videos, voice notes and '
                        'location are uploaded.',
    },
    {
        'number': 3,
        'title': 'Asset Passport Created',
        'description': 'Asset is structured with type, owner, condition, risks, baseline '
                        'and evidence.',
    },
    {
        'number': 4,
        'title': 'Diagnosed',
        'description': 'AI agents detect losses, harm, inefficiencies, safety risks, '
                        'missing data and opportunities.',
    },
    {
        'number': 5,
        'title': 'Playbook Matched',
        'description': 'EcoIQ matches the asset to a relevant playbook: boiler, factory, '
                        'mining, water, agriculture, solar+battery, district heating, waste '
                        'heat, compressed air or SMR feasibility.',
    },
    {
        'number': 6,
        'title': 'Finance Model Ready',
        'description': 'Institutional Finance Engine calculates CAPEX, OPEX savings, '
                        'payback, IRR/NPV where applicable, funding gap and finance fit.',
    },
    {
        'number': 7,
        'title': 'Supplier / Funding Matched',
        'description': 'Marketplace identifies suppliers, installers, grants, CSR, Islamic '
                        'finance, development bank or investor routes.',
    },
    {
        'number': 8,
        'title': 'Approved',
        'description': 'Human reviewer approves next step, financing, supplier contact or '
                        'implementation.',
    },
    {
        'number': 9,
        'title': 'In Implementation',
        'description': 'Tasks, suppliers, quotes, invoices, installation and progress are tracked.',
    },
    {
        'number': 10,
        'title': 'MRV Verification',
        'description': 'Before/after evidence is collected and verified.',
    },
    {
        'number': 11,
        'title': 'Impact Reported',
        'description': 'Power BI / reports show energy saved, CO2 reduced, cost saved, harm '
                        'reduced, Maqasid/Mizan improved.',
    },
]

DASHBOARD_SUMMARY_CARDS = [
    'Total assets tracked', 'Projects discovered', 'Projects ready for finance',
    'Projects in implementation', 'Verified impact projects', 'Total CAPEX pipeline',
    'Estimated annual savings', 'Estimated CO2 reduction', 'Funding gap',
    'Maqasid average score', 'Mizan average score', 'Evidence quality average',
    'No Harm Gate alerts',
]

PROJECT_TABLE_FIELDS = [
    'Project name', 'Asset type', 'Location', 'Sector', 'Stage', 'Risk level',
    'Evidence quality', 'Recommended playbook', 'CAPEX estimate',
    'Annual savings estimate', 'Payback', 'Funding status', 'Supplier status',
    'Maqasid score', 'Mizan score', 'No Harm Gate status', 'MRV status', 'Owner',
    'Next action', 'Last updated',
]

FILTERS = [
    'Country', 'Region', 'Sector', 'Asset type', 'Project stage', 'Risk level',
    'Funding status', 'Supplier status', 'MRV status', 'Maqasid score range',
    'Mizan score range', 'Evidence quality', 'No Harm Gate alerts',
]

MAP_VIEW_INTRO = 'Show modernisation opportunities by location:'
MAP_VIEW_ASSET_TYPES = [
    'Boiler houses', 'Factories', 'Mines', 'Farms', 'Public buildings', 'Heat networks',
    'Solar/battery sites', 'Water systems',
]
MAP_VIEW_MARKER_SHOWS = [
    'Risk level', 'Project stage', 'Funding need', 'Impact potential', 'Maqasid/Mizan score',
]

KANBAN_COLUMNS = [
    'Discovered', 'Evidence Captured', 'Diagnosed', 'Finance Ready', 'Supplier Matched',
    'Approved', 'Implementing', 'MRV Verification', 'Verified Impact',
]
KANBAN_CARD_SHOWS = [
    'Project name', 'Asset type', 'Location', 'Priority', 'Next action', 'Owner',
    'Risk', 'Funding gap',
]

MORNING_BRIEFING_ITEMS = [
    'New high-harm assets found', 'Missing evidence detected', 'Funding opportunities matched',
    'Supplier shortlists prepared', 'Finance memos drafted', 'MRV follow-ups required',
    'Urgent No Harm Gate alerts',
]
MORNING_BRIEFING_EXAMPLE = (
    'Overnight, EcoIQ found 4 high-priority assets, matched 3 playbooks, prepared 2 funding '
    'memos and flagged 1 project with weak evidence.'
)

EXAMPLE_PROJECTS = [
    {
        'project': 'Boiler House #3 Modernisation',
        'stage': 'Finance Ready',
        'playbook': 'Boiler Modernisation',
        'details': ['CAPEX: medium', 'Payback: fast/medium', 'Maqasid/Mizan: high'],
        'next_action': 'Request supplier quotes and collect 12-month fuel data.',
    },
    {
        'project': 'Factory Line #2 Energy Efficiency',
        'stage': 'Diagnosed',
        'playbook': 'Factory Energy Efficiency',
        'details': ['Issue: old motors, high downtime, no sub-metering'],
        'next_action': 'Install sub-metering and run compressed air audit.',
    },
    {
        'project': 'Village Clean Heating Transition',
        'stage': 'Funding Matched',
        'playbook': 'Clean Heating / Boiler Modernisation',
        'details': ['Funding route: CSR + sadaqah jariyah + municipal co-finance'],
        'next_action': 'Human approval for outreach.',
    },
    {
        'project': 'Mining Diesel Reduction',
        'stage': 'Evidence Captured',
        'playbook': 'Mining Diesel Reduction',
        'details': [],
        'next_action': 'Upload fuel logs and haul route data.',
    },
    {
        'project': 'Water Recycling Project',
        'stage': 'Implementation',
        'playbook': 'Water Recycling',
        'details': [],
        'next_action': 'Verify post-installation water savings.',
    },
]

MICROSOFT_INTEGRATION = [
    {'component': 'Microsoft Fabric', 'role': 'Project and asset data.'},
    {'component': 'Power BI', 'role': 'Dashboards.'},
    {'component': 'Azure Digital Twins', 'role': 'Asset relationships.'},
    {'component': 'Azure IoT', 'role': 'Sensor monitoring.'},
    {'component': 'Power Automate', 'role': 'Approvals.'},
    {'component': 'Teams', 'role': 'Notifications.'},
    {'component': 'SharePoint', 'role': 'Reports and evidence.'},
    {'component': 'Dynamics 365', 'role': 'Supplier/funder pipeline.'},
    {'component': 'Azure AI / Agent Framework', 'role': 'Agents.'},
]

USER_ROLES = [
    {
        'role': 'Investor view',
        'sees': [
            'Finance-ready projects', 'Risk-adjusted return', 'Evidence quality',
            'MRV status', 'Maqasid/Mizan impact',
        ],
    },
    {
        'role': 'Government / Akimat view',
        'sees': [
            'Priority assets', 'Public health and pollution reduction', 'Budget needs',
            'Implementation status', 'Community impact',
        ],
    },
    {
        'role': 'Industrial owner view',
        'sees': [
            'Cost savings', 'Downtime reduction', 'Equipment risk', 'Payback',
            'Supplier tasks',
        ],
    },
    {
        'role': 'Community / donor view',
        'sees': ['Households helped', 'Harm reduced', 'Before/after proof', 'Verified impact'],
    },
]

DECISION_RULES = [
    'High harm + low cost = do now',
    'High harm + high cost = prepare finance',
    'Low harm + low cost = quick win',
    'Low harm + high cost = delay',
]

NO_HARM_GATE_ALERTS = [
    'Evidence is weak',
    'Debt burden is high',
    'Community risk is unclear',
    'Supplier is unverified',
    'Environmental risk is unassessed',
    'Safety review is missing',
    'Shariah/Islamic finance review is required',
    'MRV baseline is missing',
]

SAFETY_PRINCIPLES = [
    'The Command Centre is a decision-support dashboard, not a replacement for engineering, '
    'financial, legal, environmental or safety review.',
    'High-impact decisions require human approval.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
    'Projects with incomplete evidence must show "Needs verification".',
    'Supplier, funding and investment recommendations require due diligence.',
]

CTA_BUTTONS = [
    {'label': 'Open Command Centre', 'anchor': '#dashboard-summary'},
    {'label': 'View Project Pipeline', 'anchor': '#kanban-view'},
    {'label': 'Filter Finance-Ready Projects', 'anchor': '#filters'},
    {'label': 'Show High-Harm Assets', 'anchor': '#no-harm-gate-alerts'},
    {'label': 'Generate Morning Briefing', 'anchor': '#morning-briefing'},
    {'label': 'Export Power BI Dashboard', 'anchor': '#microsoft-integration'},
    {'label': 'Assign Next Action', 'anchor': '#project-table'},
    {'label': 'Verify Impact', 'url_name': 'impact_mrv_layer:overview'},
]


def overview(request):
    """
    DEPRECATED — this used to render the static mockup page directly (see
    module docstring). Redirects to the real project directory instead,
    which is the safe, honest "start here" destination for both anonymous
    visitors (the directory is itself public/read-only, so this is not a
    permission change) and staff (who additionally see a real Command
    Centre link per project once they're there). Never redirects to the
    real per-project Command Centre directly — that requires a project
    slug this route doesn't have, and is staff-only, which anonymous
    visitors of this legacy public URL are not guaranteed to be.
    """
    return redirect('capital_guardian:directory')
