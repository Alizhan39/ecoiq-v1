from django.shortcuts import render

CONNECTED_MODULES = [
    {'name': 'Agent Training & Evaluation Lab', 'role': 'Supplies the training method, schema and evaluation pattern this pack specialises for the Document Reader Agent.'},
    {'name': 'AI Agent Operations Console', 'role': 'Monitors Document Reader Agent task runs and confidence over time.'},
    {'name': 'Data Room & Evidence Vault', 'role': 'Stores the source documents this agent reads and links extractions back to.'},
    {'name': 'Asset Passport', 'role': 'Receives baseline fields extracted from bills, inspection reports and technical specs.'},
    {'name': 'Impact MRV Layer', 'role': 'Receives baseline and after-data extracted from MRV evidence documents.'},
    {'name': 'Institutional Finance Engine', 'role': 'Receives CAPEX/OPEX assumptions extracted from bills and supplier quotes.'},
    {'name': 'Executive Briefing & Board Pack Generator', 'role': 'Uses extracted evidence to support investor memo and board pack claims.'},
    {'name': 'Knowledge Graph & Relationship Map', 'role': 'Stores extracted facts as evidence nodes linked to assets and projects.'},
    {'name': 'Certification & Trust Badge Engine', 'role': 'Uses evidence quality and missing-field detection to issue evidence badges.'},
    {'name': 'Security, Privacy & Compliance Centre', 'role': 'Governs how detected PII and sensitive data are handled.'},
    {'name': 'Public Trust & Impact Portal', 'role': 'Only publishes extracted facts once approved and stripped of sensitive data.'},
    {'name': 'Amanah Autopilot', 'role': 'Flags overnight documents with weak evidence quality or missing fields for review.'},
    {'name': 'Microsoft Ecosystem Core Stack', 'role': 'Provides the document/storage building blocks this agent can be wired into.'},
]

CORE_PURPOSE = (
    'Make document extraction accurate, evidence-linked and safe for Asset '
    'Passports, MRV, finance models, reports and public summaries.'
)

WHY_FIRST = {
    'explanation': (
        'Document Reader Agent is the foundation for EcoIQ because most downstream '
        'outputs depend on extracted document facts.'
    ),
    'supports': [
        'Asset Passport baseline fields', 'Finance model assumptions',
        'MRV baseline and after-data', 'Supplier quote comparison',
        'Investor memo evidence', 'Board pack evidence',
        'Public impact verification', 'Knowledge Graph evidence nodes',
        'Trust Badge evidence requirements',
    ],
    'risk_note': (
        'If this agent guesses or misreads data, EcoIQ can overstate savings, '
        'impact, risk or finance readiness.'
    ),
}

DOCUMENT_TYPES = [
    {
        'number': 1, 'title': 'Energy bill',
        'fields': [
            'Supplier', 'Billing period', 'Account/site reference if present', 'kWh used',
            'Unit rate', 'Standing charge', 'Total cost', 'VAT/tax if present',
            'Meter number if present', 'Estimated vs actual reading', 'Currency', 'Missing fields',
        ],
    },
    {
        'number': 2, 'title': 'Fuel bill',
        'fields': [
            'Fuel type', 'Volume / weight', 'Unit', 'Cost', 'Billing period', 'Supplier',
            'Delivery date', 'Asset/site', 'Emissions factor required note', 'Missing fields',
        ],
    },
    {
        'number': 3, 'title': 'Water bill',
        'fields': [
            'Supplier', 'Billing period', 'Volume used', 'Unit', 'Total cost',
            'Meter reading', 'Estimated vs actual', 'Site reference', 'Missing fields',
        ],
    },
    {
        'number': 4, 'title': 'Annual report / ESG report',
        'fields': [
            'Company name', 'Reporting year', 'Emissions data', 'Energy use', 'Water use',
            'Waste data', 'Targets', 'Capex plans', 'Climate risks', 'Governance statements',
            'Source page/section', 'Confidence', 'Missing data',
        ],
    },
    {
        'number': 5, 'title': 'Maintenance log',
        'fields': [
            'Asset name', 'Service date', 'Issue', 'Action taken', 'Downtime',
            'Parts replaced', 'Engineer note', 'Recurring issue', 'Safety concern', 'Missing fields',
        ],
    },
    {
        'number': 6, 'title': 'Inspection report',
        'fields': [
            'Site', 'Inspector', 'Date', 'Asset condition', 'Observed risks',
            'Recommendations', 'Photos referenced', 'Measurements', 'Required follow-up', 'Missing evidence',
        ],
    },
    {
        'number': 7, 'title': 'Supplier quote',
        'fields': [
            'Supplier name', 'Quote date', 'Technology/equipment', 'Quantity', 'CAPEX',
            'Installation cost', 'Warranty', 'Lead time', 'Exclusions', 'Assumptions',
            'Validity period', 'Payment terms', 'Missing fields',
        ],
    },
    {
        'number': 8, 'title': 'Invoice',
        'fields': [
            'Vendor', 'Invoice date', 'Invoice number', 'Items', 'Quantities', 'Unit prices',
            'Total', 'VAT/tax', 'Currency', 'Project/site reference', 'Missing fields',
        ],
    },
    {
        'number': 9, 'title': 'Technical specification',
        'fields': [
            'Equipment type', 'Model', 'Capacity', 'Efficiency', 'Fuel/power requirement',
            'Operating range', 'Safety notes', 'Maintenance requirements', 'Standards referenced', 'Missing fields',
        ],
    },
    {
        'number': 10, 'title': 'MRV evidence document',
        'fields': [
            'Project', 'Baseline period', 'After period', 'Measured metric', 'Baseline value',
            'After value', 'Unit', 'Methodology', 'Evidence quality', 'Verification status', 'Missing data',
        ],
    },
]

OUTPUT_SCHEMA_JSON = """{
  "agent_name": "Document Reader Agent",
  "document_type": "",
  "input_summary": "",
  "extracted_fields": {},
  "tables": [],
  "key_figures": [],
  "dates": [],
  "units": [],
  "currency": "",
  "asset_or_project_links": [],
  "evidence_quality": "strong | medium | weak | unreadable",
  "missing_fields": [],
  "confidence": 0.0,
  "risk_flags": [],
  "human_approval_required": true,
  "next_action": "",
  "status": "draft | needs_review | usable | blocked"
}"""

OUTPUT_SCHEMA_RULES = [
    'Never guess missing values.',
    'Use null or "missing" where data is absent.',
    'Preserve units exactly.',
    'Preserve currency exactly.',
    'Do not convert units unless explicitly requested.',
    'If OCR/scan quality is poor, mark evidence quality as weak or unreadable.',
    'If a number is unclear, mark it as uncertain.',
    'If a table is present but not readable, flag it.',
    'If the document is not related to the project, flag mismatch.',
    'If personal data appears, flag PII risk.',
    'If the document supports finance or MRV, require human approval.',
]

CONFIDENCE_LEVELS = [
    {
        'level': 'Strong confidence',
        'items': [
            'Clear machine-readable text', 'Complete fields', 'Readable tables',
            'Clear dates and units', 'Document matches project/asset',
        ],
    },
    {
        'level': 'Medium confidence',
        'items': [
            'Most fields clear', 'Some missing data', 'Small formatting ambiguity',
            'Document likely matches project/asset',
        ],
    },
    {
        'level': 'Weak confidence',
        'items': [
            'Scanned/blurred document', 'Unclear numbers', 'Missing dates/units',
            'Document mismatch possible', 'Handwritten or low quality',
        ],
    },
    {
        'level': 'Unreadable',
        'items': [
            'Cannot reliably extract key information', 'Image too blurry',
            'Table unavailable', 'Wrong file type', 'Corrupted text',
        ],
    },
]

GOOD_EXTRACTION_EXAMPLES = [
    {
        'number': 1, 'input': 'Energy bill for Factory Line 2, March 2026.',
        'good_output': [
            'document_type: energy bill', 'billing_period: March 2026',
            'kWh_used: extracted exactly', 'total_cost: extracted exactly',
            'currency: GBP', 'estimated_reading: yes/no if shown',
            'missing_fields: meter number missing', 'evidence_quality: strong',
            'next_action: link to Asset Passport and Finance Modelling Agent',
        ],
    },
    {
        'number': 2, 'input': 'Supplier quote for heat pump installation.',
        'good_output': [
            'Supplier name', 'Quote date', 'Equipment', 'CAPEX', 'Installation cost',
            'Exclusions', 'Validity period', 'Warranty', 'Missing fields',
            'Human approval required before supplier recommendation',
        ],
    },
    {
        'number': 3, 'input': 'MRV after-data spreadsheet PDF.',
        'good_output': [
            'Baseline value', 'After value', 'Unit', 'Method', 'Evidence quality',
            'Missing reviewer approval', 'Status: needs_review',
        ],
    },
]

BAD_EXTRACTION_EXAMPLES = [
    'Inventing missing kWh because total cost is known.',
    'Changing litres to tonnes without conversion note.',
    'Treating supplier quote as approved supplier.',
    'Using annual report target as verified impact.',
    'Claiming MRV Verified without after-data and human approval.',
]

DOCUMENT_SAFETY_RULES = [
    {
        'category': 'Energy/fuel/water bills',
        'rules': [
            'Do not infer savings from one bill alone.',
            'Do not claim efficiency improvement without baseline comparison.',
            'Flag estimated meter readings.',
        ],
    },
    {
        'category': 'Annual/ESG reports',
        'rules': [
            'Separate targets from actual results.',
            'Separate company claims from verified data.',
            'Flag missing methodology.',
        ],
    },
    {
        'category': 'Supplier quotes',
        'rules': [
            'Quote is not endorsement.',
            'Supplier due diligence is required.',
            'Exclusions and assumptions must be extracted.',
        ],
    },
    {
        'category': 'MRV evidence',
        'rules': [
            'Baseline and after-data both required for verification.',
            'Estimated impact is not verified impact.',
            'Human approval required for MRV Verified label.',
        ],
    },
    {
        'category': 'Public summaries',
        'rules': [
            'No public claim unless approved through Public Trust Portal.',
            'Check consent and privacy before publication.',
        ],
    },
]

HUMAN_APPROVAL_TRIGGERS = [
    'Finance model', 'Investor memo', 'MRV Verified claim', 'Public impact story',
    'Board pack', 'Government brief', 'Supplier recommendation',
    'Islamic finance brief', 'Maqasid/Mizan public claim', 'External report',
]

PII_DETECTION = {
    'flag_items': [
        'Names', 'Phone numbers', 'Email addresses', 'Exact household address',
        'Signatures', 'Account numbers', 'Personal identifiers',
        'Faces in attached images', 'Private financial data', 'Confidential supplier pricing',
    ],
    'output_fields': ['pii_detected: true/false', 'pii_types: []', 'public_safe: true/false', 'redaction_required: true/false'],
}

KG_MAPPING = [
    'DOCUMENT_EXTRACTED_FACT', 'EVIDENCE_SUPPORTS_CLAIM', 'DOCUMENT_LINKED_TO_ASSET',
    'DOCUMENT_LINKED_TO_PROJECT', 'FACT_REQUIRES_REVIEW', 'FACT_HAS_CONFIDENCE',
    'DOCUMENT_HAS_PII_RISK', 'DOCUMENT_SUPPORTS_MRV', 'DOCUMENT_SUPPORTS_FINANCE_MODEL',
    'DOCUMENT_SUPPORTS_BADGE',
]

GOLDEN_TEST_CASES = [
    {
        'number': 1, 'input_type': 'Clear UK electricity bill',
        'expected_fields': 'Supplier, billing period, kWh, unit rate, total cost, currency',
        'expected_missing': 'Meter number (if not shown)',
        'expected_risk_flags': 'None',
        'expected_human_approval': 'Only if used for finance/MRV',
        'expected_status': 'usable',
    },
    {
        'number': 2, 'input_type': 'Poor-quality scanned fuel bill',
        'expected_fields': 'Fuel type, supplier (partial)',
        'expected_missing': 'Volume, cost, billing period',
        'expected_risk_flags': 'Low OCR quality',
        'expected_human_approval': 'Yes',
        'expected_status': 'needs_review',
    },
    {
        'number': 3, 'input_type': 'Supplier quote with exclusions',
        'expected_fields': 'Supplier, CAPEX, installation cost, exclusions, warranty',
        'expected_missing': 'Payment terms (if absent)',
        'expected_risk_flags': 'Endorsement risk',
        'expected_human_approval': 'Yes',
        'expected_status': 'needs_review',
    },
    {
        'number': 4, 'input_type': 'Annual report with target but no actual emissions',
        'expected_fields': 'Company name, reporting year, target',
        'expected_missing': 'Actual emissions data',
        'expected_risk_flags': 'Target vs actual confusion risk',
        'expected_human_approval': 'Yes',
        'expected_status': 'needs_review',
    },
    {
        'number': 5, 'input_type': 'Maintenance log with recurring fault',
        'expected_fields': 'Asset name, service date, issue, action taken',
        'expected_missing': 'Downtime duration (if absent)',
        'expected_risk_flags': 'Recurring issue, possible safety concern',
        'expected_human_approval': 'No',
        'expected_status': 'usable',
    },
    {
        'number': 6, 'input_type': 'Inspection report with missing measurements',
        'expected_fields': 'Site, inspector, date, observed risks',
        'expected_missing': 'Measurements',
        'expected_risk_flags': 'Missing evidence',
        'expected_human_approval': 'No',
        'expected_status': 'needs_review',
    },
    {
        'number': 7, 'input_type': 'MRV baseline but no after-data',
        'expected_fields': 'Project, baseline period, baseline value, unit',
        'expected_missing': 'After period, after value',
        'expected_risk_flags': 'Cannot verify impact yet',
        'expected_human_approval': 'Yes',
        'expected_status': 'blocked',
    },
    {
        'number': 8, 'input_type': 'Invoice with VAT and multiple line items',
        'expected_fields': 'Vendor, invoice number, items, VAT, total',
        'expected_missing': 'Project/site reference (if absent)',
        'expected_risk_flags': 'None',
        'expected_human_approval': 'No',
        'expected_status': 'usable',
    },
    {
        'number': 9, 'input_type': 'Technical spec with capacity and efficiency',
        'expected_fields': 'Equipment type, model, capacity, efficiency',
        'expected_missing': 'Standards referenced (if absent)',
        'expected_risk_flags': 'None',
        'expected_human_approval': 'No',
        'expected_status': 'usable',
    },
    {
        'number': 10, 'input_type': 'Wrong document uploaded to project',
        'expected_fields': 'Document type only',
        'expected_missing': 'All project-specific fields',
        'expected_risk_flags': 'Document/project mismatch',
        'expected_human_approval': 'Yes',
        'expected_status': 'blocked',
    },
]

EVALUATION_METRICS = [
    'Field extraction accuracy', 'Missing field detection', 'Unit preservation accuracy',
    'Document type classification accuracy', 'Table extraction quality',
    'PII detection rate', 'Unsupported claim rate', 'Human approval trigger accuracy',
    'JSON/schema validity', 'Reviewer acceptance rate',
]

PROMPT_TEMPLATE = {
    'system_prompt': (
        'You are the EcoIQ Document Reader Agent. Extract only facts that are '
        'visible in the provided document. Do not guess missing values. Preserve '
        'units, dates and currency. Label uncertainty clearly. Separate targets '
        'from actual results. Separate estimates from verified data. Flag PII and '
        'sensitive information. Require human approval when extracted data '
        'supports finance, MRV, public reporting, supplier recommendation or '
        'high-impact decisions.'
    ),
    'task_prompt': (
        'Read this document and return structured extraction using the required '
        'schema. Identify document type, extracted fields, missing fields, '
        'evidence quality, PII risk, confidence, human approval requirement and '
        'next action.'
    ),
}

NO_HARM_GATE_ITEMS = [
    'Is the document type correctly identified?', 'Are units preserved?',
    'Are missing fields clearly marked?', 'Are unclear numbers flagged?',
    'Is PII detected?', 'Is the document linked to the correct asset/project?',
    'Is evidence quality strong enough?', 'Are targets separated from actuals?',
    'Is estimated data separated from verified data?',
    'Is human approval required before downstream use?',
]

SAFETY_PRINCIPLES = [
    'Document Reader Agent extracts facts; it does not verify truth by itself.',
    'Missing data must not be guessed.',
    'Extracted values need human review when used for finance, MRV, public '
    'reporting or high-impact recommendations.',
    'Supplier quotes are not supplier endorsements.',
    'Annual report targets are not verified impact.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
    'Sensitive and personal data must be protected.',
]

CTA_BUTTONS = [
    {'label': 'Open Document Reader Training Pack', 'anchor': '#document-types'},
    {'label': 'Create Golden Test Case', 'anchor': '#golden-test-cases'},
    {'label': 'Run Extraction Evaluation', 'anchor': '#evaluation-metrics'},
    {'label': 'Review Failed Extraction', 'anchor': '#bad-extraction-examples'},
    {'label': 'Open Required Output Schema', 'anchor': '#output-schema'},
    {'label': 'Check PII Risk', 'anchor': '#pii-detection'},
    {'label': 'Link Document to Asset Passport', 'url_name': 'asset_passport:overview'},
    {'label': 'Send to Human Review', 'anchor': '#human-approval-triggers'},
    {'label': 'Train on Energy Bill', 'anchor': '#doc-type-1'},
    {'label': 'Train on Supplier Quote', 'anchor': '#doc-type-7'},
    {'label': 'Train on MRV Evidence', 'anchor': '#doc-type-10'},
]


def overview(request):
    return render(request, 'document_reader_agent_training_pack/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_purpose': CORE_PURPOSE,
        'why_first': WHY_FIRST,
        'document_types': DOCUMENT_TYPES,
        'output_schema_json': OUTPUT_SCHEMA_JSON,
        'output_schema_rules': OUTPUT_SCHEMA_RULES,
        'confidence_levels': CONFIDENCE_LEVELS,
        'good_extraction_examples': GOOD_EXTRACTION_EXAMPLES,
        'bad_extraction_examples': BAD_EXTRACTION_EXAMPLES,
        'document_safety_rules': DOCUMENT_SAFETY_RULES,
        'human_approval_triggers': HUMAN_APPROVAL_TRIGGERS,
        'pii_detection': PII_DETECTION,
        'kg_mapping': KG_MAPPING,
        'golden_test_cases': GOLDEN_TEST_CASES,
        'evaluation_metrics': EVALUATION_METRICS,
        'prompt_template': PROMPT_TEMPLATE,
        'no_harm_gate_items': NO_HARM_GATE_ITEMS,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })
