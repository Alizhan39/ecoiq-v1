"""
EcoIQ Amanah Autopilot — overnight ethical AI agent system.

This is a presentational hackathon/demo module: an overview page showing how an overnight
agent pipeline would find harm, waste, and imbalance across industry, energy, cities, and
communities, then prepare modernisation actions, funding routes, supplier shortlists, and
impact reports for human approval. All figures below are illustrative demo content, not live
production data — no agents actually run, no external services are called, and Maqasid/Mizan
are presented as an ethical decision-support framework, not a religious ruling.
"""
from django.shortcuts import render

OVERNIGHT_TIMELINE = [
    ('00:00', 'Data scan started'),
    ('01:00', 'High-risk assets detected'),
    ('02:00', 'Energy waste estimated'),
    ('03:00', 'Maqasid/Mizan assessment completed'),
    ('04:00', 'Supplier shortlist prepared'),
    ('05:00', 'Funding route identified'),
    ('06:00', 'Investor-ready memo generated'),
    ('07:00', 'Morning briefing ready'),
]

DASHBOARD_METRICS = [
    ('High-harm assets detected', '3'),
    ('Quick-win modernisation actions', '5'),
    ('Funding opportunities matched', '2'),
    ('Suppliers shortlisted', '4'),
    ('Reports generated', '1'),
    ('Maqasid/Mizan score improvement', '+6 pts'),
    ('Next actions ready for approval', '5'),
]

AGENTS = [
    {
        'name': 'Harm Detection Agent',
        'input': 'Sensor, maintenance, and safety data across assets',
        'output': 'Flagged high-harm assets, ranked by severity',
        'status': 'Completed', 'last_run': '01:00',
    },
    {
        'name': 'Waste Reduction Agent',
        'input': 'Energy, water, and material consumption data',
        'output': 'Estimated waste volumes and reduction opportunities',
        'status': 'Completed', 'last_run': '02:00',
    },
    {
        'name': 'Maqasid-Mizan Agent',
        'input': 'Harm and waste findings, stakeholder context',
        'output': 'Ethical decision-support assessment — not a religious ruling',
        'status': 'Completed', 'last_run': '03:00',
    },
    {
        'name': 'Modernisation Agent',
        'input': 'Flagged assets, waste estimates, ethical assessment',
        'output': 'Ranked modernisation actions with quick-win candidates',
        'status': 'Completed', 'last_run': '03:40',
    },
    {
        'name': 'Funding Agent',
        'input': 'Modernisation actions and cost estimates',
        'output': 'Matched funding routes and financing options',
        'status': 'Completed', 'last_run': '05:00',
    },
    {
        'name': 'Supplier Agent',
        'input': 'Modernisation actions and procurement criteria',
        'output': 'Shortlisted suppliers with lifecycle-cost comparison',
        'status': 'Completed', 'last_run': '04:00',
    },
    {
        'name': 'Report Agent',
        'input': 'All agent outputs from the overnight run',
        'output': 'Investor-ready memo and morning briefing',
        'status': 'Completed', 'last_run': '06:00',
    },
    {
        'name': 'Monitoring Agent',
        'input': 'Approved actions and their execution status',
        'output': 'Verified impact tracking once actions are approved',
        'status': 'Standing by for approval', 'last_run': '07:00',
    },
]

MORNING_BRIEFING = (
    'Overnight, Amanah Autopilot scanned energy and industrial data, flagged 3 high-harm '
    'assets, estimated significant energy waste, completed a Maqasid/Mizan ethical review, '
    'shortlisted 4 suppliers, matched 2 funding routes, and prepared an investor-ready memo. '
    '5 actions are ready for your approval.'
)

VERIFIED_IMPACT_INDICATORS = [
    'Evidence-linked findings',
    'Human approval required before any action',
    'Audit trail ready for every recommendation',
]


def overview(request):
    return render(request, 'amanah_autopilot/overview.html', {
        'timeline': OVERNIGHT_TIMELINE,
        'metrics': DASHBOARD_METRICS,
        'agents': AGENTS,
        'briefing': MORNING_BRIEFING,
        'verified_indicators': VERIFIED_IMPACT_INDICATORS,
    })
