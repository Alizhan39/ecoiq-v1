from django.shortcuts import render

# Connected EcoIQ modules — the Knowledge Graph connects the data every one of them produces
CONNECTED_MODULES = [
    {'name': 'Asset Passport', 'role': 'Supplies the asset nodes at the centre of the graph.'},
    {'name': 'Data Room & Evidence Vault', 'role': 'Supplies the evidence nodes every claim traces back to.'},
    {'name': 'Impact MRV Layer', 'role': 'Supplies the MRV/impact nodes and verification status.'},
    {'name': 'Industrial Playbook Library', 'role': 'Supplies the playbook nodes matched to each asset.'},
    {'name': 'Supplier & Funding Marketplace', 'role': 'Supplies the supplier/funder nodes and relationships.'},
    {'name': 'Institutional Finance Engine', 'role': 'Supplies the finance nodes linked to each project.'},
    {'name': 'Command Centre', 'role': 'Surfaces graph completeness across the live project pipeline.'},
    {'name': 'Portfolio & Country Transition Atlas', 'role': 'Supplies the country/region nodes and clusters.'},
    {'name': 'Governance & Expert Review Board', 'role': 'Supplies the governance review nodes and approval decisions.'},
    {'name': 'Certification & Trust Badge Engine', 'role': 'Supplies the trust badge nodes shown on projects.'},
    {'name': 'AI Agent Operations Console', 'role': 'Supplies the agent trace nodes showing which agent generated which output.'},
    {'name': 'Product Analytics & KPI Engine', 'role': 'Consumes graph completeness as part of platform-wide KPIs.'},
    {'name': 'Public Trust & Impact Portal', 'role': 'Publishes only approved graph nodes as public claims.'},
    {'name': 'Microsoft Ecosystem Core Stack', 'role': 'Provides the agent, data and dashboard building blocks a production graph would run on.'},
    {'name': 'API & Integration Layer', 'role': 'Exposes graph queries and relationship data through the API.'},
    {'name': 'Security, Privacy & Compliance Centre', 'role': 'Enforces which graph nodes are permissioned for which viewer.'},
    {'name': 'Maqasid/Mizan ethical scoring', 'role': 'Supplies the ethical principle nodes linked to risks and actions.'},
    {'name': 'No Harm Gate', 'role': 'Blocks unresolved risk paths from being used externally.'},
]

CORE_PURPOSE = (
    'Make EcoIQ\'s intelligence connected, traceable and explainable across the full '
    'industrial modernisation lifecycle.'
)

NODE_TYPES = [
    {
        'number': 1,
        'title': 'Asset Nodes',
        'examples': [
            'Boiler house', 'Factory line', 'Compressor', 'Mine', 'Farm',
            'Water system', 'Public building', 'Solar + battery site',
            'District heating network', 'Village heating project',
        ],
        'fields': [
            'Asset name', 'Asset type', 'Location', 'Owner', 'Sector', 'Condition',
            'Risk level', 'Evidence quality', 'Linked project', 'Maqasid/Mizan score',
            'MRV status',
        ],
    },
    {
        'number': 2,
        'title': 'Company / Organisation Nodes',
        'examples': [
            'Industrial company', 'Municipality / akimat', 'Supplier', 'Funder',
            'Investor', 'CSR sponsor', 'Islamic finance provider', 'Government agency',
            'NGO', 'Microsoft ecosystem partner',
        ],
        'fields': [
            'Organisation name', 'Type', 'Country', 'Sector', 'Relationship role',
            'Opportunity status', 'Due diligence status', 'Linked projects',
            'Permissions',
        ],
    },
    {
        'number': 3,
        'title': 'Evidence Nodes',
        'examples': [
            'Photo', 'Video', 'Energy bill', 'Fuel bill', 'Water bill', 'Sensor log',
            'Inspection report', 'Supplier quote', 'Finance memo', 'Expert approval',
            'MRV report', 'Public summary',
        ],
        'fields': [
            'Evidence type', 'Source', 'Upload date', 'Evidence quality',
            'Linked claim', 'Linked asset', 'Permission level', 'Public-safe status',
            'Expiry / review date',
        ],
    },
    {
        'number': 4,
        'title': 'Risk Nodes',
        'examples': [
            'Heat loss', 'Fuel waste', 'Air pollution', 'Water waste', 'Safety risk',
            'Debt burden', 'Weak evidence', 'Missing consent', 'Unverified supplier',
            'Unsupported impact claim', 'Public reporting risk',
        ],
        'fields': [
            'Risk type', 'Severity', 'Probability', 'Owner', 'Evidence link',
            'Mitigation', 'No Harm Gate status',
        ],
    },
    {
        'number': 5,
        'title': 'Project Nodes',
        'examples': [
            'Boiler House #3 Modernisation', 'Factory Compressed Air Optimisation',
            'Village Clean Heating Pilot', 'Water Recycling Upgrade',
            'Country Transition Atlas project',
        ],
        'fields': [
            'Project name', 'Stage', 'Country', 'Sector', 'CAPEX estimate',
            'Funding status', 'Governance status', 'MRV status', 'Trust badges',
            'Next action',
        ],
    },
    {
        'number': 6,
        'title': 'Playbook Nodes',
        'examples': [
            'Boiler Modernisation Playbook', 'Factory Energy Efficiency Playbook',
            'Mining Diesel Reduction Playbook', 'Water Recycling Playbook',
            'Solar + Battery Industrial Playbook', 'Waste Heat Recovery Playbook',
            'SMR Feasibility Playbook',
        ],
        'fields': [
            'Playbook name', 'Sector', 'Asset types', 'Evidence required',
            'Quick wins', 'Deep upgrades', 'MRV metrics', 'No Harm risks',
        ],
    },
    {
        'number': 7,
        'title': 'Finance Nodes',
        'examples': [
            'CAPEX model', 'OPEX savings', 'Payback estimate', 'IRR / NPV note',
            'Investor memo', 'Funding gap', 'Grant route', 'CSR route',
            'Islamic finance route', 'Supplier quote',
        ],
        'fields': [
            'Finance type', 'Amount / estimate', 'Confidence', 'Assumptions',
            'Review status', 'Linked evidence', 'Linked project', 'No Harm notes',
        ],
    },
    {
        'number': 8,
        'title': 'Supplier / Funder Nodes',
        'examples': [
            'Heat pump supplier', 'Smart meter provider', 'Insulation contractor',
            'CSR sponsor', 'Islamic finance provider', 'Development bank',
            'Grant programme', 'Impact investor',
        ],
        'fields': [
            'Role', 'Region', 'Technology / funding type', 'Fit score',
            'Due diligence status', 'Linked projects', 'Approved outreach status',
        ],
    },
    {
        'number': 9,
        'title': 'Governance Review Nodes',
        'examples': [
            'Technical review', 'Financial review', 'Environmental review',
            'Safety review', 'Maqasid/Mizan review', 'Islamic finance review',
            'Public summary approval',
        ],
        'fields': [
            'Reviewer role', 'Status', 'Comments', 'Timestamp', 'Evidence version',
            'Approval decision', 'Unresolved risks',
        ],
    },
    {
        'number': 10,
        'title': 'MRV / Impact Nodes',
        'examples': [
            'Baseline captured', 'After-data collected', 'MRV in review',
            'MRV verified', 'Verified impact report', 'Public impact story',
        ],
        'fields': [
            'Impact metric', 'Baseline value', 'After value', 'Verification status',
            'Evidence quality', 'Public status', 'Linked report',
        ],
    },
    {
        'number': 11,
        'title': 'Country / Region Nodes',
        'examples': [
            'Kazakhstan', 'United Kingdom', 'Saudi Arabia', 'Türkiye',
            'Almaty Region', 'Karaganda Region', 'London', 'Riyadh', 'Istanbul',
        ],
        'fields': [
            'Country / region', 'Assets mapped', 'Projects discovered',
            'Finance-ready projects', 'Highest-harm clusters',
            'Verified impact projects', 'CAPEX pipeline', 'Funding gap',
        ],
    },
    {
        'number': 12,
        'title': 'Maqasid / Mizan Principle Nodes',
        'examples': [
            'Protect health', 'Reduce harm', 'Protect wealth/resources',
            'Reduce waste', 'Community benefit',
            'Balance between input and useful output', 'Stewardship / amanah',
            'Justice / adl', 'No harm / la darar',
        ],
        'fields': [
            'Principle', 'Diagnostic question', 'Linked risks', 'Linked actions',
            'Linked impact metrics', 'Reviewer status',
        ],
    },
    {
        'number': 13,
        'title': 'Trust Badge Nodes',
        'examples': [
            'Evidence Strong', 'Finance Ready', 'MRV Verified', 'Expert Reviewed',
            'Public Summary Approved', 'No Harm Gate Passed', 'Data Room Complete',
            'Microsoft Ecosystem Ready',
        ],
        'fields': [
            'Badge name', 'Category', 'Status', 'Issue date', 'Expiry/review date',
            'Evidence requirements', 'Public visibility', 'Revocation risk',
        ],
    },
]

RELATIONSHIP_TYPES = [
    'ASSET_HAS_EVIDENCE', 'EVIDENCE_SUPPORTS_CLAIM', 'ASSET_HAS_RISK',
    'RISK_TRIGGERED_BY_EVIDENCE', 'ASSET_MATCHES_PLAYBOOK',
    'PLAYBOOK_RECOMMENDS_ACTION', 'ACTION_REQUIRES_SUPPLIER',
    'PROJECT_HAS_FINANCE_MODEL', 'PROJECT_HAS_FUNDING_ROUTE',
    'PROJECT_REQUIRES_REVIEW', 'REVIEW_APPROVES_ACTION', 'PROJECT_HAS_MRV_CLAIM',
    'MRV_CLAIM_BACKED_BY_EVIDENCE', 'PROJECT_HAS_BADGE', 'BADGE_REQUIRES_EVIDENCE',
    'PROJECT_LOCATED_IN_COUNTRY', 'COUNTRY_HAS_PROJECT_CLUSTER',
    'PROJECT_ALIGNS_WITH_MAQASID', 'PROJECT_SUPPORTS_MIZAN', 'ORGANISATION_OWNS_ASSET',
    'SUPPLIER_CAN_DELIVER_ACTION', 'FUNDER_CAN_SUPPORT_PROJECT',
    'PUBLIC_SUMMARY_DERIVED_FROM_MRV', 'AI_AGENT_GENERATED_OUTPUT',
    'OUTPUT_REQUIRES_HUMAN_APPROVAL',
]

GRAPH_VIEWS = [
    {
        'number': 1,
        'title': 'Project Graph View',
        'description': 'Shows one project and all linked evidence, risks, playbooks, '
                        'suppliers, funders, finance memos, reviews, MRV claims and badges.',
    },
    {
        'number': 2,
        'title': 'Asset Graph View',
        'description': 'Shows one asset and its owner, evidence, condition, risks, '
                        'recommended playbook, modernisation actions and MRV status.',
    },
    {
        'number': 3,
        'title': 'Country Graph View',
        'description': 'Shows country-level clusters: assets, regions, sectors, '
                        'finance-ready projects, high-harm zones and verified impact projects.',
    },
    {
        'number': 4,
        'title': 'Supplier / Funder Graph View',
        'description': 'Shows which suppliers/funders connect to which project types, '
                        'countries, playbooks and due diligence status.',
    },
    {
        'number': 5,
        'title': 'Evidence Trace Graph',
        'description': 'Shows how one public claim or investor memo statement traces '
                        'back to evidence, review and approval.',
    },
    {
        'number': 6,
        'title': 'Maqasid/Mizan Graph',
        'description': 'Shows how a project connects to ethical principles, risks '
                        'reduced, actions taken and verified impact.',
    },
    {
        'number': 7,
        'title': 'No Harm Gate Graph',
        'description': 'Shows unresolved risk paths: weak evidence, missing consent, '
                        'supplier risk, debt burden, safety risk and public reporting risk.',
    },
    {
        'number': 8,
        'title': 'AI Agent Trace Graph',
        'description': 'Shows which agent generated an output, what evidence it used, '
                        'which model/task status it had and whether human approval is required.',
    },
]

DASHBOARD_CARDS = [
    'Total nodes', 'Total relationships', 'Assets linked', 'Evidence nodes',
    'Projects with complete graph', 'Projects missing evidence links',
    'Projects with unresolved risk paths', 'Finance-ready graph clusters',
    'MRV verified graph clusters', 'Supplier/funder relationships',
    'Maqasid/Mizan principle links', 'No Harm Gate unresolved paths',
    'Orphan evidence nodes', 'Orphan project nodes',
    'Public claims with full trace', 'Graph completeness average',
]

COMPLETENESS_SCORE_CHECKS = [
    'Asset linked to project', 'Project linked to evidence',
    'Evidence linked to claim', 'Project linked to playbook',
    'Project linked to finance model', 'Project linked to supplier/funding route',
    'Project linked to governance review', 'Project linked to MRV status',
    'Project linked to trust badges', 'Risks linked to mitigations',
    'Public claims linked to approved evidence',
]
COMPLETENESS_LABELS = [
    'Complete graph', 'Strong graph', 'Partial graph', 'Weak graph',
    'Broken trace', 'Needs linking',
]

PROCESS_IMPROVEMENT_CATEGORIES = [
    {
        'number': 1,
        'title': 'Missing Links',
        'examples': [
            'Project has finance memo but no evidence link', 'MRV claim has no after-data',
            'Public summary has no approval', 'Supplier match has no due diligence',
            'Badge issued without required evidence',
        ],
    },
    {
        'number': 2,
        'title': 'Bottlenecks',
        'examples': [
            'Many projects stuck at missing baseline',
            'Many supplier matches stuck at due diligence',
            'Many finance memos awaiting review',
            'Many public summaries blocked by consent',
        ],
    },
    {
        'number': 3,
        'title': 'Duplicate Work',
        'examples': [
            'Same supplier quote uploaded twice', 'Same asset created twice',
            'Same evidence linked to wrong project',
            'Same country brief created from stale data',
        ],
    },
    {
        'number': 4,
        'title': 'Risk Propagation',
        'examples': [
            'Weak evidence affects finance memo, trust badge and public summary',
            'Missing consent blocks public portal and sponsor reporting',
            'Supplier due diligence failure affects implementation and badge status',
        ],
    },
    {
        'number': 5,
        'title': 'High-Value Next Actions',
        'examples': [
            'One missing document can unlock finance-ready status',
            'One review can unlock public summary approval',
            'One supplier quote can unlock board pack',
            'One MRV after-data upload can unlock verified impact badge',
        ],
    },
]

PROCESS_IMPROVEMENT_RECOMMENDATIONS = [
    'Link missing fuel bill to Boiler House #3 to improve MRV readiness.',
    'Request technical review to unlock Finance Ready badge.',
    'Remove public summary until consent is recorded.',
    'Merge duplicate asset records for Factory Line #2.',
    'Update stale evidence before investor pack export.',
    'Prioritise projects where one missing link unlocks funding readiness.',
]

EXAMPLE_GRAPHS = [
    {
        'label': 'Project',
        'name': 'Boiler House #3 Modernisation',
        'graph_links': [
            'Asset: coal-fired boiler house',
            'Evidence: 8 photos, 1 fuel bill, 1 meter reading',
            'Risks: heat loss, soot, missing smart meter, fuel waste',
            'Playbook: Boiler Modernisation Playbook',
            'Actions: pipe insulation, smart meters, boiler servicing',
            'Finance: draft CAPEX/OPEX model',
            'Supplier: insulation contractor, smart meter provider',
            'Governance: technical review required',
            'MRV: baseline partial',
            'Badges: Evidence Medium, Finance Model Drafted, No Harm Gate Needs Review',
            'Maqasid/Mizan: protect health, reduce waste, restore balance',
        ],
        'process_improvement': 'Collect 12 months of fuel bills and request technical '
                                'review to unlock Finance Ready.',
    },
    {
        'label': 'Project',
        'name': 'Factory Compressed Air Optimisation',
        'graph_links': [
            'Asset: compressor system',
            'Evidence: energy bill, compressor photo, downtime note',
            'Risk: compressed air leaks, high electricity use',
            'Playbook: Compressed Air Optimisation',
            'Finance: quick payback estimate',
            'Supplier: compressed air audit provider',
            'Governance: finance review pending',
            'MRV: after-data pending',
            'Badges: Finance Ready, Supplier Shortlisted, MRV In Review',
        ],
        'process_improvement': 'Complete after-data collection to unlock MRV Verified '
                                'and public impact story.',
    },
    {
        'label': 'Project',
        'name': 'Village Clean Heating Pilot',
        'graph_links': [
            'Asset: household heating system',
            'Evidence: before photos, consent record, installation photo',
            'Risk: indoor air harm, fuel burden',
            'Playbook: Boiler / Clean Heating Modernisation',
            'Funder: CSR sponsor, sadaqah jariyah route',
            'Governance: public summary approval required',
            'MRV: baseline captured, after-data pending',
            'Badges: Sponsor Ready, Needs Consent, Public Summary Drafted',
            'Maqasid/Mizan: protect health, reduce harm, community benefit',
        ],
        'process_improvement': 'Record consent and after-data before publishing public '
                                'impact story.',
    },
    {
        'label': 'Country',
        'name': 'Kazakhstan Clean Heating Cluster',
        'graph_links': [
            'Country: Kazakhstan',
            'Regions: Almaty Region, Karaganda Region',
            'Assets: boiler houses, village heating, public buildings',
            'Risks: coal smoke, fuel burden, heat loss',
            'Playbooks: Boiler Modernisation, District Heating Upgrade, Clean Heating',
            'Funders: CSR sponsors, municipal co-finance, Islamic charitable funds',
            'MRV: pilot projects in progress',
            'Badges: Sponsor Ready, Finance Ready, Needs Verification',
        ],
        'process_improvement': 'Prioritise finance-ready heating projects with strong '
                                'evidence and high Maqasid/Mizan uplift.',
    },
]

UI_PANELS = [
    {
        'position': 'Left panel',
        'label': 'Graph filter controls',
        'items': [
            'Country', 'Sector', 'Asset type', 'Project stage', 'Evidence quality',
            'Risk type', 'Badge status', 'MRV status', 'Supplier/funder',
            'Maqasid/Mizan principle',
        ],
        'description': '',
    },
    {
        'position': 'Centre panel',
        'label': '',
        'items': [],
        'description': 'Interactive relationship graph with nodes and links.',
    },
    {
        'position': 'Right panel',
        'label': 'Selected node details',
        'items': [
            'Summary', 'Linked evidence', 'Risks', 'Next action', 'Evidence quality',
            'No Harm Gate status', 'Human approval status',
        ],
        'description': '',
    },
    {
        'position': 'Bottom panel',
        'label': '',
        'items': [],
        'description': 'Process improvement recommendations and missing link alerts.',
    },
]

GRAPH_FILTERS = [
    'Country', 'Region', 'Sector', 'Asset type', 'Project', 'Organisation', 'Supplier',
    'Funder', 'Risk type', 'Playbook', 'Evidence type', 'Evidence quality',
    'MRV status', 'Badge status', 'Public status', 'Maqasid principle',
    'Mizan principle', 'No Harm Gate status',
]

MICROSOFT_GRAPHRAG_ITEMS = [
    'Microsoft GraphRAG concept for relationship-based retrieval',
    'Microsoft Fabric for graph metadata and analytics',
    'Power BI for relationship dashboards',
    'Azure Digital Twins for asset relationships',
    'Azure AI Search for evidence retrieval',
    'SharePoint/Data Room for document links',
    'Teams for missing-link and approval alerts',
    'Power Automate for graph-triggered workflows',
]
MICROSOFT_GRAPHRAG_WORDING_NOTE = (
    'Use careful wording: "can use" / "designed to integrate with", not "already certified".'
)

AI_AGENT_INTEGRATION_ITEMS = [
    'Retrieve only relevant evidence', 'Avoid unsupported claims',
    'Find missing links', 'Trace recommendations to sources',
    'Identify next best action', 'Detect duplicate projects/assets',
    'Route reviews to the right expert', 'Build investor memos with evidence trace',
    'Generate public summaries only from approved nodes',
]

AMANAH_ITEMS = [
    'Find orphan evidence', 'Detect broken claim traces',
    'Flag public summaries without approvals',
    'Identify projects one step away from Finance Ready',
    'Identify MRV claims missing after-data', 'Suggest supplier/funder links',
    'Detect duplicate assets', 'Prepare graph health briefing',
]
AMANAH_MORNING_BRIEFING_EXAMPLE = (
    'Overnight, EcoIQ found 6 orphan evidence files, 3 public claims without full '
    'trace, 4 projects one link away from Finance Ready and 2 duplicate asset records '
    'requiring review.'
)

NO_HARM_GATE_ITEMS = [
    'Is every claim linked to evidence?',
    'Is every public claim approved?',
    'Are sensitive nodes hidden from public view?',
    'Are supplier/funder links approved?',
    'Are Maqasid/Mizan links reviewed where needed?',
    'Are MRV claims verified or labelled estimated?',
    'Are weak evidence paths clearly marked?',
    'Are graph relationships current and not stale?',
    'Is human approval required before action?',
    'Can the user trace every recommendation?',
]

SAFETY_PRINCIPLES = [
    'The Knowledge Graph is an explainability and relationship-mapping layer, not a '
    'replacement for technical, financial, legal, environmental or religious review.',
    'Graph relationships must be evidence-backed and permissioned.',
    'Public graph views must hide sensitive data.',
    'AI-generated links should be treated as draft until verified where needed.',
    'MRV and impact claims require evidence and approval.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
    'Do not infer relationships that are not supported by evidence.',
]

CTA_BUTTONS = [
    {'label': 'Open Knowledge Graph', 'anchor': '#node-types'},
    {'label': 'View Project Relationship Map', 'anchor': '#graph-view-1'},
    {'label': 'Trace Evidence to Claim', 'anchor': '#graph-view-5'},
    {'label': 'Find Missing Links', 'anchor': '#process-improvement-engine'},
    {'label': 'Show Finance-Ready Clusters', 'anchor': '#dashboard-cards'},
    {'label': 'Show No Harm Risk Paths', 'anchor': '#graph-view-7'},
    {'label': 'Open Maqasid/Mizan Graph', 'anchor': '#graph-view-6'},
    {'label': 'Run Graph Health Check', 'anchor': '#graph-completeness-score'},
    {'label': 'Send Missing Link Alert to Teams', 'anchor': '#microsoft-graphrag-integration'},
    {'label': 'Export Relationship Map', 'url_name': 'data_room_evidence_vault:overview'},
]


def overview(request):
    return render(request, 'knowledge_graph_relationship_map/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_purpose': CORE_PURPOSE,
        'node_types': NODE_TYPES,
        'relationship_types': RELATIONSHIP_TYPES,
        'graph_views': GRAPH_VIEWS,
        'dashboard_cards': DASHBOARD_CARDS,
        'completeness_score_checks': COMPLETENESS_SCORE_CHECKS,
        'completeness_labels': COMPLETENESS_LABELS,
        'process_improvement_categories': PROCESS_IMPROVEMENT_CATEGORIES,
        'process_improvement_recommendations': PROCESS_IMPROVEMENT_RECOMMENDATIONS,
        'example_graphs': EXAMPLE_GRAPHS,
        'ui_panels': UI_PANELS,
        'graph_filters': GRAPH_FILTERS,
        'microsoft_graphrag_items': MICROSOFT_GRAPHRAG_ITEMS,
        'microsoft_graphrag_wording_note': MICROSOFT_GRAPHRAG_WORDING_NOTE,
        'ai_agent_integration_items': AI_AGENT_INTEGRATION_ITEMS,
        'amanah_items': AMANAH_ITEMS,
        'amanah_morning_briefing_example': AMANAH_MORNING_BRIEFING_EXAMPLE,
        'no_harm_gate_items': NO_HARM_GATE_ITEMS,
        'safety_principles': SAFETY_PRINCIPLES,
        'cta_buttons': CTA_BUTTONS,
    })
