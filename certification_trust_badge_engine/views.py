from django.shortcuts import render

# Connected EcoIQ modules — trust badges summarise status produced across the platform
CONNECTED_MODULES = [
    {'name': 'Knowledge Graph & Relationship Map', 'role': 'Exposes badge nodes and relationships across the relationship graph.'},
    {'name': 'Frontend Experience & Google Stitch Design System', 'role': 'Defines how badges are displayed across every screen.'},
    {'name': 'Impact MRV Layer', 'role': 'Supplies MRV status feeding the MRV badge category.'},
    {'name': 'Governance & Expert Review Board', 'role': 'Supplies reviewer decisions feeding the governance badge category.'},
    {'name': 'Data Room & Evidence Vault', 'role': 'Supplies evidence completeness feeding the evidence badge category.'},
    {'name': 'Public Trust & Impact Portal', 'role': 'Publishes only badges approved for public display.'},
    {'name': 'Institutional Finance Engine', 'role': 'Supplies finance readiness feeding the finance badge category.'},
    {'name': 'Supplier & Funding Marketplace', 'role': 'Supplies due diligence status feeding supplier/funding badges.'},
    {'name': 'Portfolio & Country Transition Atlas', 'role': 'Surfaces badge status across country and portfolio views.'},
    {'name': 'Command Centre', 'role': 'Surfaces badge summaries across the live project pipeline.'},
    {'name': 'Security, Privacy & Compliance Centre', 'role': 'Enforces who may view or approve which badges.'},
    {'name': 'AI Agent Operations Console', 'role': 'Shows which agent proposed or drafted a badge.'},
    {'name': 'Product Analytics & KPI Engine', 'role': 'Tracks badge issuance and completion as platform KPIs.'},
    {'name': 'Microsoft Ecosystem Core Stack', 'role': 'Provides the building blocks Microsoft-readiness badges describe.'},
    {'name': 'Maqasid/Mizan ethical scoring', 'role': 'Supplies the ethical review status behind governance badges.'},
    {'name': 'No Harm Gate', 'role': 'Blocks badge issuance where unresolved risk remains.'},
]

CORE_PURPOSE = 'Make EcoIQ trust status visible, explainable and evidence-backed.'

# Maps each badge label to a readiness-status pill class (see the "Trust Badge
# Pills" component in static/css/ecoiq-institutional.css): verified | ready |
# review | blocked | msready. These are visual readiness/status labels, not
# formal certification.
BADGE_STATUS_CLASS = {
    'Evidence Missing': 'blocked', 'Evidence Weak': 'review', 'Evidence Medium': 'review',
    'Evidence Strong': 'verified', 'Data Room Complete': 'ready', 'Evidence Pack Ready': 'ready',
    'MRV Not Started': 'blocked', 'Baseline Captured': 'review', 'After-Data Pending': 'review',
    'MRV In Review': 'review', 'MRV Verified': 'verified', 'Verified Impact Published': 'verified',
    'Finance Not Ready': 'blocked', 'Finance Model Drafted': 'review', 'Funding Route Matched': 'review',
    'Investor Memo Ready': 'ready', 'Finance Ready': 'ready', 'Investment Committee Ready': 'ready',
    'AI Draft': 'review', 'Needs Expert Review': 'review', 'Technical Reviewed': 'verified',
    'Finance Reviewed': 'verified', 'Environmental Reviewed': 'verified', 'Safety Reviewed': 'verified',
    'Maqasid/Mizan Reviewed': 'verified', 'Expert Reviewed': 'verified', 'Human Approved': 'verified',
    'Public Reporting Blocked': 'blocked', 'Needs Consent': 'review', 'Sensitive Data Redacted': 'ready',
    'Public Summary Drafted': 'review', 'Public Summary Approved': 'verified', 'Sponsor Approved': 'verified',
    'Public Impact Story Published': 'verified',
    'Supplier Match Draft': 'review', 'Supplier Shortlisted': 'review',
    'Supplier Due Diligence Pending': 'review', 'Supplier Approved for Outreach': 'ready',
    'Sponsor Ready': 'ready', 'Grant Ready': 'ready', 'Islamic Finance Review Required': 'review',
    'Microsoft Ecosystem Ready': 'msready', 'Power BI Ready': 'msready', 'Teams Approval Ready': 'msready',
    'SharePoint Evidence Pack Ready': 'msready', 'API Integration Ready': 'msready',
    'Enterprise Pilot Ready': 'msready',
    'No Harm Gate Not Checked': 'blocked', 'No Harm Gate Warning': 'review',
    'No Harm Gate Needs Review': 'review', 'No Harm Gate Passed': 'verified',
    'High-Risk Expert Review Required': 'blocked',
}


def _classified(labels):
    return [{'label': label, 'cls': BADGE_STATUS_CLASS.get(label, 'review')} for label in labels]


BADGE_CATEGORIES = [
    {
        'number': 1,
        'title': 'Evidence Badges',
        'badges': [
            'Evidence Missing', 'Evidence Weak', 'Evidence Medium', 'Evidence Strong',
            'Data Room Complete', 'Evidence Pack Ready',
        ],
        'rule_label': 'Rules',
        'rule': (
            'Evidence Strong requires baseline evidence, relevant documents, '
            'timestamped files and linked asset/project records.'
        ),
    },
    {
        'number': 2,
        'title': 'MRV Badges',
        'badges': [
            'MRV Not Started', 'Baseline Captured', 'After-Data Pending', 'MRV In Review',
            'MRV Verified', 'Verified Impact Published',
        ],
        'rule_label': 'Rules',
        'rule': (
            'MRV Verified requires before/after evidence, measurement or documented '
            'proxy, evidence quality review and human approval.'
        ),
    },
    {
        'number': 3,
        'title': 'Finance Badges',
        'badges': [
            'Finance Not Ready', 'Finance Model Drafted', 'Funding Route Matched',
            'Investor Memo Ready', 'Finance Ready', 'Investment Committee Ready',
        ],
        'rule_label': 'Rules',
        'rule': (
            'Finance Ready requires CAPEX/OPEX assumptions, payback logic, risk notes, '
            'evidence quality and governance review.'
        ),
    },
    {
        'number': 4,
        'title': 'Governance Badges',
        'badges': [
            'AI Draft', 'Needs Expert Review', 'Technical Reviewed', 'Finance Reviewed',
            'Environmental Reviewed', 'Safety Reviewed', 'Maqasid/Mizan Reviewed',
            'Expert Reviewed', 'Human Approved',
        ],
        'rule_label': 'Rules',
        'rule': (
            'Expert Reviewed requires assigned reviewer decision, timestamp, evidence '
            'version and audit trail.'
        ),
    },
    {
        'number': 5,
        'title': 'Public Reporting Badges',
        'badges': [
            'Public Reporting Blocked', 'Needs Consent', 'Sensitive Data Redacted',
            'Public Summary Drafted', 'Public Summary Approved', 'Sponsor Approved',
            'Public Impact Story Published',
        ],
        'rule_label': 'Rules',
        'rule': (
            'Public Summary Approved requires MRV support or clear estimated label, '
            'privacy check, consent where needed and human approval.'
        ),
    },
    {
        'number': 6,
        'title': 'Supplier / Funding Badges',
        'badges': [
            'Supplier Match Draft', 'Supplier Shortlisted', 'Supplier Due Diligence Pending',
            'Supplier Approved for Outreach', 'Funding Route Matched', 'Sponsor Ready',
            'Grant Ready', 'Islamic Finance Review Required',
        ],
        'rule_label': 'Rules',
        'rule': 'Supplier Approved requires human approval and relevant due diligence notes.',
    },
    {
        'number': 7,
        'title': 'Microsoft / Enterprise Readiness Badges',
        'badges': [
            'Microsoft Ecosystem Ready', 'Power BI Ready', 'Teams Approval Ready',
            'SharePoint Evidence Pack Ready', 'API Integration Ready', 'Enterprise Pilot Ready',
        ],
        'rule_label': 'Important',
        'rule': (
            'Do not claim Microsoft certification or partnership unless actually '
            'obtained. Use "ready" or "designed to integrate with".'
        ),
    },
    {
        'number': 8,
        'title': 'No Harm Gate Badges',
        'badges': [
            'No Harm Gate Not Checked', 'No Harm Gate Warning', 'No Harm Gate Needs Review',
            'No Harm Gate Passed', 'High-Risk Expert Review Required',
        ],
        'rule_label': 'Rules',
        'rule': (
            'No Harm Gate Passed requires evidence, risk review, human approval and no '
            'unresolved high-risk alerts.'
        ),
    },
]

BADGE_LIFECYCLE = [
    'Draft', 'Evidence Captured', 'Evidence Reviewed', 'Playbook Matched',
    'Finance Drafted', 'Expert Reviewed', 'MRV Verified', 'Public Summary Approved',
    'Published / Investment Ready',
]

BADGE_DASHBOARD_CARDS = [
    'Total badges issued', 'MRV Verified projects', 'Finance Ready projects',
    'Expert Reviewed projects', 'Public Summary Approved projects',
    'Data Room Complete projects', 'No Harm Gate Passed projects',
    'Badges needing review', 'Expired badges', 'High-risk badges',
    'Microsoft-ready projects', 'Sponsor-ready projects', 'Investment-ready projects',
]

BADGE_TABLE_FIELDS = [
    'Project name', 'Asset type', 'Country', 'Badge', 'Badge category', 'Status',
    'Evidence quality', 'Reviewer', 'Issued date', 'Expiry / review date',
    'Linked evidence', 'Linked approval', 'Public visibility', 'Next action',
]

BADGE_STATUS_LEVELS = [
    'Not started', 'Draft', 'Pending evidence', 'Pending review', 'Approved',
    'Verified', 'Expired', 'Revoked', 'Blocked',
]

EXAMPLE_PROJECT_BADGES = [
    {
        'name': 'Boiler House #3 Modernisation',
        'badges': [
            'Evidence Medium', 'Baseline Captured', 'Finance Model Drafted',
            'Needs Expert Review', 'No Harm Gate Needs Review', 'Supplier Match Draft',
        ],
        'next_action': 'Collect 12 months fuel data and request technical review.',
    },
    {
        'name': 'Factory Compressed Air Optimisation',
        'badges': [
            'Evidence Strong', 'Finance Ready', 'Supplier Shortlisted', 'MRV In Review',
            'Expert Reviewed', 'No Harm Gate Passed',
        ],
        'next_action': 'Complete after-data collection for MRV Verified badge.',
    },
    {
        'name': 'Village Clean Heating Pilot',
        'badges': [
            'Sponsor Ready', 'Needs Consent', 'Public Summary Drafted', 'Baseline Captured',
            'Maqasid/Mizan Reviewed', 'Islamic Finance Review Required',
        ],
        'next_action': 'Record consent and complete after-data before public impact story.',
    },
    {
        'name': 'UK SME Efficiency Portfolio',
        'badges': [
            'Investor Memo Ready', 'Finance Ready', 'Data Room Complete', 'Power BI Ready',
            'Enterprise Pilot Ready',
        ],
        'next_action': 'Share investor due diligence pack after approval.',
    },
]

BADGE_EVIDENCE_REQUIREMENTS_ITEMS = [
    'What it means', 'What evidence is required', 'Who can approve it',
    'Whether it can be public', 'Whether it expires', 'What blocks it',
    'What next action unlocks it',
]

PUBLIC_BADGE_RULES = {
    'public_if': [
        'Public summary approved', 'Sensitive data redacted',
        'Consent recorded where needed', 'MRV/estimate label is clear',
        'Sponsor name approved if shown', 'No Harm Gate checked',
    ],
    'private_if': [
        'Financial models', 'Supplier due diligence', 'Sensitive industrial data',
        'Personal/community data', 'Unresolved expert review comments',
    ],
}

BADGE_REVOCATION_RULES = [
    'Evidence is found weak', 'Consent expires', 'MRV data is corrected',
    'Expert review is reversed', 'Supplier due diligence fails',
    'Public claim becomes unsupported', 'Project conditions change',
    'Security/privacy concern appears',
]

FRONTEND_INTEGRATION = {
    'surfaces': [
        'Command Centre', 'Asset Passport', 'Country Atlas', 'Knowledge Graph',
        'Public Trust Portal', 'Data Room', 'Investor Memo', 'Board Pack',
        'Mobile Inspection', 'Product Analytics',
    ],
    'display_rules': [
        'Use clear badge colours', 'Separate draft from verified',
        'Separate estimated from MRV verified',
        'Show tooltip with evidence requirement', 'Show linked evidence and approval',
        'Never make unverified badges look certified',
        'Never imply Microsoft certification unless actually obtained',
    ],
}

KNOWLEDGE_GRAPH_INTEGRATION = {
    'relationships': [
        'PROJECT_HAS_BADGE', 'BADGE_REQUIRES_EVIDENCE', 'BADGE_APPROVED_BY_REVIEW',
        'BADGE_BLOCKED_BY_RISK', 'BADGE_VISIBLE_IN_PUBLIC_PORTAL',
        'BADGE_REVOKED_DUE_TO_EVIDENCE_CHANGE',
    ],
    'graph_shows': [
        'Which projects are Finance Ready', 'Which projects are MRV Verified',
        'Which badges are blocked', 'Which evidence unlocks badges',
        'Which badges are public-safe', 'Which badges require human approval',
    ],
}

AMANAH_ITEMS = [
    'Detect projects ready for new badges', 'Flag badges blocked by missing evidence',
    'Identify expired badges', 'Downgrade unsupported claims to Needs Verification',
    'Prepare badge review queue', 'Suggest finance-ready or sponsor-ready projects',
    'Prepare morning trust status briefing',
]
AMANAH_MORNING_BRIEFING_EXAMPLE = (
    'Overnight, 4 projects became Finance Ready, 2 public summaries need consent, '
    '1 MRV badge is blocked by missing after-data and 3 Data Rooms are now complete.'
)

MICROSOFT_INTEGRATION_ITEMS = [
    'Microsoft Fabric for badge metadata', 'Power BI for trust badge dashboards',
    'Teams for badge approval workflows', 'SharePoint for evidence pack links',
    'Power Automate for expiry/review alerts',
    'Dynamics 365 for investor/customer badge status',
    'Security/Compliance Centre for permission checks',
]
MICROSOFT_INTEGRATION_WORDING_NOTE = (
    'Use careful wording: "designed to integrate with" or "can use", not '
    '"Microsoft certified".'
)

NO_HARM_GATE_ITEMS = [
    'Is the evidence strong enough?', 'Is the badge meaning clear?',
    'Could the badge be misunderstood as formal certification?',
    'Is human approval required?', 'Is public display allowed?',
    'Is consent recorded?',
    'Are financial, environmental and impact claims supported?',
    'Is Islamic finance or Maqasid/Mizan wording reviewed?',
    'Is the badge expiry/review period defined?',
    'Can every badge claim be traced to evidence?',
]

SAFETY_PRINCIPLES = [
    'EcoIQ trust badges are internal readiness and evidence-status labels unless '
    'formal certification is separately obtained.',
    'Do not claim third-party certification, Microsoft certification, Shariah '
    'certification or regulatory approval unless actually granted.',
    'MRV Verified means verified according to EcoIQ evidence workflow, not '
    'necessarily external audit unless stated.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
    'Public badges require consent, privacy review, evidence support and human approval.',
    'Badges must be downgraded or revoked if evidence changes.',
]

CTA_BUTTONS = [
    {'label': 'Open Trust Badge Engine', 'anchor': '#badge-categories'},
    {'label': 'Issue Badge', 'anchor': '#badge-lifecycle'},
    {'label': 'Review Badge Evidence', 'anchor': '#badge-evidence-requirements'},
    {'label': 'Approve Public Badge', 'anchor': '#public-badge-rules'},
    {'label': 'Revoke Badge', 'anchor': '#badge-revocation-rules'},
    {'label': 'Check Badge Requirements', 'anchor': '#badge-table-fields'},
    {'label': 'Export Badge Report', 'url_name': 'data_room_evidence_vault:overview'},
    {'label': 'Send Badge Review to Teams', 'anchor': '#amanah-autopilot-for-trust-badges'},
    {'label': 'Show Finance Ready Projects', 'anchor': '#badge-dashboard-cards'},
    {'label': 'Show MRV Verified Projects', 'anchor': '#badge-dashboard-cards'},
]


def overview(request):
    badge_categories = [
        {**cat, 'badges': _classified(cat['badges'])} for cat in BADGE_CATEGORIES
    ]
    example_project_badges = [
        {**p, 'badges': _classified(p['badges'])} for p in EXAMPLE_PROJECT_BADGES
    ]
    return render(request, 'certification_trust_badge_engine/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_purpose': CORE_PURPOSE,
        'badge_categories': badge_categories,
        'badge_lifecycle': BADGE_LIFECYCLE,
        'badge_dashboard_cards': BADGE_DASHBOARD_CARDS,
        'badge_table_fields': BADGE_TABLE_FIELDS,
        'badge_status_levels': BADGE_STATUS_LEVELS,
        'example_project_badges': example_project_badges,
        'badge_evidence_requirements_items': BADGE_EVIDENCE_REQUIREMENTS_ITEMS,
        'public_badge_rules': PUBLIC_BADGE_RULES,
        'badge_revocation_rules': BADGE_REVOCATION_RULES,
        'frontend_integration': FRONTEND_INTEGRATION,
        'knowledge_graph_integration': KNOWLEDGE_GRAPH_INTEGRATION,
        'amanah_items': AMANAH_ITEMS,
        'amanah_morning_briefing_example': AMANAH_MORNING_BRIEFING_EXAMPLE,
        'microsoft_integration_items': MICROSOFT_INTEGRATION_ITEMS,
        'microsoft_integration_wording_note': MICROSOFT_INTEGRATION_WORDING_NOTE,
        'no_harm_gate_items': NO_HARM_GATE_ITEMS,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })
