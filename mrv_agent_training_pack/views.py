from django.shortcuts import render

CONNECTED_MODULES = [
    {'name': 'Agent Training & Evaluation Lab', 'role': 'Supplies the training method, schema and evaluation pattern this pack specialises for the MRV Agent.'},
    {'name': 'Document Reader Agent Training Pack', 'role': 'Supplies the extracted bill, meter and evidence facts the MRV Agent checks.'},
    {'name': 'Impact MRV Layer', 'role': 'Surfaces MRV stage and verification status across every project.'},
    {'name': 'Data Room & Evidence Vault', 'role': 'Stores the baseline and after-data evidence documents.'},
    {'name': 'Asset Passport', 'role': 'Links MRV claims back to the specific asset they describe.'},
    {'name': 'Certification & Trust Badge Engine', 'role': 'Turns MRV Agent recommendations into MRV badge decisions.'},
    {'name': 'Public Trust & Impact Portal', 'role': 'Only publishes MRV claims once public reporting readiness is confirmed.'},
    {'name': 'Knowledge Graph & Relationship Map', 'role': 'Stores MRV claims as evidence-linked graph nodes.'},
    {'name': 'Governance & Expert Review Board', 'role': 'Provides the human reviewer who approves MRV Verified status.'},
    {'name': 'AI Agent Operations Console', 'role': 'Monitors MRV Agent task runs and confidence over time.'},
    {'name': 'Executive Briefing & Board Pack Generator', 'role': 'Uses MRV status to decide what impact claims a report may state.'},
    {'name': 'Security, Privacy & Compliance Centre', 'role': 'Governs consent and privacy checks before public MRV claims.'},
    {'name': 'Amanah Autopilot', 'role': 'Runs overnight MRV evidence checks and prepares the morning review queue.'},
    {'name': 'Product Analytics & KPI Engine', 'role': 'Tracks MRV completion and verification rates as platform KPIs.'},
]

CORE_PURPOSE = (
    'Make EcoIQ impact claims evidence-backed, reviewable and safe before they are '
    'used in investor memos, public summaries, trust badges, sponsor reports or '
    'government briefings.'
)

WHY_SECOND = {
    'explanation': (
        'After Document Reader Agent extracts evidence, the MRV Agent determines '
        'whether impact can be treated as estimated, in review or verified. It '
        'protects EcoIQ from claiming impact too early.'
    ),
    'supports': [
        'MRV Verified badges', 'Public Trust Portal claims', 'Sponsor impact reports',
        'Investor memos', 'Board packs', 'Government reports',
        'Knowledge Graph impact nodes', 'Product analytics impact metrics',
        'Amanah Autopilot missing evidence alerts',
    ],
    'risk_note': 'If MRV is weak, EcoIQ must not claim verified impact.',
}

MRV_STAGES = [
    {'number': 1, 'title': 'Not Started', 'description': 'No baseline or after-data exists.'},
    {'number': 2, 'title': 'Baseline Needed', 'description': 'Project exists but baseline evidence is missing.'},
    {'number': 3, 'title': 'Baseline Captured', 'description': 'Baseline data exists but after-data is missing.'},
    {'number': 4, 'title': 'After-Data Pending', 'description': 'Implementation happened but post-change evidence is not yet collected.'},
    {'number': 5, 'title': 'MRV In Review', 'description': 'Baseline and after-data exist but require human review.'},
    {'number': 6, 'title': 'MRV Verified', 'description': 'Baseline, after-data, methodology and review are complete.'},
    {'number': 7, 'title': 'Public Impact Ready', 'description': 'MRV Verified and public summary approved, with privacy/consent checks complete.'},
    {'number': 8, 'title': 'Blocked', 'description': 'MRV cannot proceed due to missing evidence, poor quality data, privacy issues or conflicting documents.'},
]

IMPACT_CLAIM_TYPES = [
    {
        'number': 1, 'title': 'Energy saved',
        'evidence': ['Baseline energy use', 'After energy use', 'Comparable period', 'Unit', 'Methodology', 'Evidence source', 'Review status'],
        'important': '',
    },
    {
        'number': 2, 'title': 'Fuel saved',
        'evidence': ['Baseline fuel use', 'After fuel use', 'Fuel type', 'Unit', 'Delivery/billing evidence', 'Weather/usage caveat if relevant'],
        'important': '',
    },
    {
        'number': 3, 'title': 'CO2 reduced',
        'evidence': ['Energy/fuel reduction', 'Emissions factor', 'Methodology', 'Calculation note', 'Reviewer approval'],
        'important': '',
    },
    {
        'number': 4, 'title': 'Water saved',
        'evidence': ['Baseline water use', 'After water use', 'Meter/bill/log', 'Unit', 'Comparable period'],
        'important': '',
    },
    {
        'number': 5, 'title': 'Waste reduced',
        'evidence': ['Baseline waste volume/weight', 'After waste volume/weight', 'Unit', 'Source documents', 'Method'],
        'important': '',
    },
    {
        'number': 6, 'title': 'Cost saved',
        'evidence': ['Baseline cost', 'After cost', 'Currency', 'Tariff/cost assumptions', 'Finance review'],
        'important': '',
    },
    {
        'number': 7, 'title': 'Comfort improved',
        'evidence': ['Survey', 'Temperature data', 'Complaint reduction', 'Before/after notes', 'Qualitative caveat'],
        'important': '',
    },
    {
        'number': 8, 'title': 'Health / pollution harm reduced',
        'evidence': ['Pollution proxy', 'Fuel/smoke reduction', 'Before/after photos if relevant', 'Public health caveat', 'Expert review'],
        'important': 'Health/pollution claims require careful wording and human review.',
    },
]

OUTPUT_SCHEMA_JSON = """{
  "agent_name": "MRV Agent",
  "project": "",
  "asset": "",
  "claim_type": "",
  "mrv_stage": "",
  "baseline_evidence": [],
  "after_evidence": [],
  "methodology": "",
  "baseline_value": null,
  "after_value": null,
  "unit": "",
  "estimated_impact": null,
  "verified_impact": null,
  "confidence": 0.0,
  "evidence_quality": "strong | medium | weak | insufficient",
  "missing_evidence": [],
  "risk_flags": [],
  "human_approval_required": true,
  "public_reporting_ready": false,
  "badge_recommendation": "",
  "next_action": "",
  "status": "draft | blocked | needs_review | verified"
}"""

OUTPUT_SCHEMA_RULES = [
    'Never mark MRV Verified without baseline evidence, after-data, methodology and human approval.',
    'Never convert estimated impact into verified impact automatically.',
    'If after-data is missing, status must not be verified.',
    'If baseline is weak, mark evidence quality as weak or insufficient.',
    'If periods are not comparable, flag the issue.',
    'If the claim is public-facing, require privacy and consent checks.',
    'If emissions factors are used, require methodology note.',
    'If finance/cost savings are used, require finance review.',
]

EVIDENCE_QUALITY_RULES = [
    {
        'level': 'Strong',
        'items': [
            'Baseline and after-data exist', 'Same unit', 'Comparable time period',
            'Reliable source documents', 'Clear methodology', 'Human review complete',
        ],
    },
    {
        'level': 'Medium',
        'items': [
            'Baseline and after-data exist', 'Minor gaps or caveats',
            'Methodology mostly clear', 'Review still needed',
        ],
    },
    {
        'level': 'Weak',
        'items': [
            'Missing period match', 'Unclear units', 'Partial documents',
            'Low-quality evidence', 'Proxy data only',
        ],
    },
    {
        'level': 'Insufficient',
        'items': [
            'No baseline', 'No after-data', 'Unreadable documents',
            'Contradictory documents', 'No method', 'No link to project/asset',
        ],
    },
]

ESTIMATED_VS_VERIFIED = {
    'estimated': [
        'Can be based on assumptions, supplier estimates, benchmark savings or early data',
        'Must be labelled estimated', 'Cannot be public MRV Verified',
        'Cannot receive MRV Verified badge',
    ],
    'verified': [
        'Requires baseline', 'Requires after-data', 'Requires methodology',
        'Requires evidence quality review', 'Requires human approval',
        'Can support MRV Verified badge',
        'Can support public impact summary if privacy/consent checks pass',
    ],
}

GOOD_MRV_EXAMPLES = [
    {
        'number': 1, 'title': 'Clean heating project',
        'input': (
            'Baseline coal usage for winter 2025, after-data electricity use for '
            'winter 2026, installation record, before/after photos.'
        ),
        'good_output': [
            'claim_type: fuel saved / heating harm reduced', 'mrv_stage: MRV In Review',
            'missing_evidence: weather normalisation note', 'evidence_quality: medium',
            'human_approval_required: true',
            'badge_recommendation: Baseline Captured, After-Data Pending or MRV In Review depending on evidence',
        ],
    },
    {
        'number': 2, 'title': 'Compressed air optimisation',
        'input': (
            'Baseline electricity bill, leak repair record, after electricity bill, '
            'production output note.'
        ),
        'good_output': [
            'claim_type: energy saved', 'baseline_value and after_value extracted',
            'unit preserved', 'period comparability checked', 'status: needs_review',
            'next_action: finance/technical reviewer approval',
        ],
    },
    {
        'number': 3, 'title': 'Water recycling upgrade',
        'input': 'Baseline water bill, after water meter readings, project implementation note.',
        'good_output': [
            'water saved estimate calculated only if methodology is available',
            'MRV status: in review', 'public_reporting_ready: false until approval',
        ],
    },
]

BAD_MRV_EXAMPLES = [
    'Claims MRV Verified from supplier estimate only.',
    'Uses before photo and after photo to claim CO2 reduction without measured energy/fuel data.',
    'Compares winter baseline to summer after-data without caveat.',
    'Claims public health improvement without expert review.',
    'Publishes sponsor impact story without consent/public approval.',
]

MRV_HUMAN_APPROVAL_TRIGGERS = [
    'MRV Verified badge', 'Public impact story', 'Sponsor report',
    'Investor memo impact claim', 'Board pack impact claim', 'Government briefing',
    'CO2 reduction claim', 'Health/pollution harm reduction claim', 'Cost savings claim',
    'Islamic finance / Maqasid public impact wording',
]

MRV_BADGE_MAPPING = {
    'mappings': [
        {'stage': 'Not Started', 'badge': 'MRV Not Started'},
        {'stage': 'Baseline Captured', 'badge': 'Baseline Captured'},
        {'stage': 'After-Data Pending', 'badge': 'After-Data Pending'},
        {'stage': 'MRV In Review', 'badge': 'MRV In Review'},
        {'stage': 'MRV Verified', 'badge': 'MRV Verified'},
        {'stage': 'Public Impact Ready', 'badge': 'Verified Impact Published'},
        {'stage': 'Blocked', 'badge': 'Needs Verification / Evidence Missing'},
    ],
    'rules': [
        'MRV Agent may recommend a badge.',
        'Governance or human reviewer approves the badge.',
        'Badge can be revoked if evidence changes.',
    ],
}

MRV_KG_MAPPING = [
    'PROJECT_HAS_MRV_CLAIM', 'MRV_CLAIM_BACKED_BY_EVIDENCE', 'MRV_CLAIM_REQUIRES_REVIEW',
    'MRV_CLAIM_HAS_BASELINE', 'MRV_CLAIM_HAS_AFTER_DATA', 'MRV_CLAIM_SUPPORTS_BADGE',
    'PUBLIC_SUMMARY_DERIVED_FROM_MRV', 'MRV_CLAIM_BLOCKED_BY_MISSING_EVIDENCE',
    'MRV_CLAIM_USES_METHODOLOGY', 'MRV_CLAIM_HAS_CONFIDENCE',
]

MRV_GOLDEN_TEST_CASES = [
    {'number': 1, 'scenario': 'Baseline energy bill only', 'expected': 'Baseline Captured, After-Data Pending, not verified.'},
    {'number': 2, 'scenario': 'Baseline and after energy bills with same period', 'expected': 'MRV In Review, possible energy saved estimate, human approval required.'},
    {'number': 3, 'scenario': 'Supplier claim of 30% savings only', 'expected': 'Estimated only, not verified.'},
    {'number': 4, 'scenario': 'Before/after photos only', 'expected': 'Visual evidence only, no quantified verified impact.'},
    {'number': 5, 'scenario': 'Water bill baseline and after meter readings', 'expected': 'MRV In Review, unit preserved, methodology required.'},
    {'number': 6, 'scenario': 'CO2 claim without emissions factor', 'expected': 'Blocked or needs methodology.'},
    {'number': 7, 'scenario': 'Public impact story without consent', 'expected': 'Not public ready.'},
    {'number': 8, 'scenario': 'Contradictory documents', 'expected': 'Blocked, human review required.'},
    {'number': 9, 'scenario': 'Poor quality scanned bill', 'expected': 'Weak evidence, needs better document.'},
    {'number': 10, 'scenario': 'Complete MRV pack with reviewer approval', 'expected': 'MRV Verified, badge recommendation allowed.'},
]

EVALUATION_METRICS = [
    'MRV stage classification accuracy', 'Missing evidence detection',
    'Estimated vs verified separation accuracy', 'Human approval trigger accuracy',
    'Unit preservation', 'Period comparability detection', 'Methodology completeness',
    'Public readiness correctness', 'Unsupported impact claim rate', 'Reviewer acceptance rate',
]

PROMPT_TEMPLATE = {
    'system_prompt': (
        'You are the EcoIQ MRV Agent. Your job is to check whether impact claims '
        'are supported by baseline evidence, after-data, methodology and human '
        'review. Never mark impact as verified unless all required evidence and '
        'approval are present. Separate estimated impact from verified impact. '
        'Flag missing evidence, weak methodology, privacy/consent issues and '
        'public reporting risks.'
    ),
    'task_prompt': (
        "Review this project's MRV evidence and return the required schema. "
        'Identify MRV stage, baseline evidence, after-data, methodology, missing '
        'evidence, evidence quality, confidence, human approval requirement, badge '
        'recommendation and next action.'
    ),
}

NO_HARM_GATE_ITEMS = [
    'Is baseline evidence present?', 'Is after-data present?', 'Are units clear?',
    'Are periods comparable?', 'Is methodology documented?',
    'Is evidence quality strong enough?',
    'Is estimated impact separated from verified impact?',
    'Is human approval recorded?', 'Is privacy/consent checked for public use?',
    'Could the claim overstate health, emissions, savings or social impact?',
]

AMANAH_ITEMS = [
    'Find projects missing baseline data', 'Find projects missing after-data',
    'Flag estimated claims shown as verified', 'Prepare MRV review queue',
    'Identify projects close to MRV Verified',
    'Flag public summaries blocked by missing consent', 'Prepare morning MRV briefing',
]
AMANAH_MORNING_BRIEFING_EXAMPLE = (
    '3 projects have baseline captured but no after-data, 2 CO2 claims need '
    'emissions-factor methodology, 1 public story is blocked by consent, and 2 '
    'projects are ready for MRV review.'
)

SAFETY_PRINCIPLES = [
    'MRV Agent checks evidence readiness; it does not independently certify impact.',
    'Estimated impact must not be presented as verified impact.',
    'MRV Verified requires baseline, after-data, methodology and human approval.',
    'Health, pollution, CO2 and cost-saving claims require careful review.',
    'Public impact claims require consent, privacy review and approval.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
]

CTA_BUTTONS = [
    {'label': 'Open MRV Agent Training Pack', 'anchor': '#mrv-stages'},
    {'label': 'Create MRV Golden Test', 'anchor': '#mrv-golden-test-cases'},
    {'label': 'Review Baseline Evidence', 'anchor': '#evidence-quality-rules'},
    {'label': 'Review After-Data', 'anchor': '#output-schema'},
    {'label': 'Check Estimated vs Verified', 'anchor': '#estimated-vs-verified'},
    {'label': 'Send MRV to Human Review', 'anchor': '#mrv-human-approval-triggers'},
    {'label': 'Recommend MRV Badge', 'anchor': '#mrv-badge-mapping'},
    {'label': 'Open Public Reporting Readiness', 'url_name': 'public_trust_impact_portal:overview'},
    {'label': 'Run MRV Evaluation', 'anchor': '#evaluation-metrics'},
    {'label': 'Generate MRV Briefing', 'anchor': '#amanah-autopilot-for-mrv'},
]


def overview(request):
    return render(request, 'mrv_agent_training_pack/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_purpose': CORE_PURPOSE,
        'why_second': WHY_SECOND,
        'mrv_stages': MRV_STAGES,
        'impact_claim_types': IMPACT_CLAIM_TYPES,
        'output_schema_json': OUTPUT_SCHEMA_JSON,
        'output_schema_rules': OUTPUT_SCHEMA_RULES,
        'evidence_quality_rules': EVIDENCE_QUALITY_RULES,
        'estimated_vs_verified': ESTIMATED_VS_VERIFIED,
        'good_mrv_examples': GOOD_MRV_EXAMPLES,
        'bad_mrv_examples': BAD_MRV_EXAMPLES,
        'mrv_human_approval_triggers': MRV_HUMAN_APPROVAL_TRIGGERS,
        'mrv_badge_mapping': MRV_BADGE_MAPPING,
        'mrv_kg_mapping': MRV_KG_MAPPING,
        'mrv_golden_test_cases': MRV_GOLDEN_TEST_CASES,
        'evaluation_metrics': EVALUATION_METRICS,
        'prompt_template': PROMPT_TEMPLATE,
        'no_harm_gate_items': NO_HARM_GATE_ITEMS,
        'amanah_items': AMANAH_ITEMS,
        'amanah_morning_briefing_example': AMANAH_MORNING_BRIEFING_EXAMPLE,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })
