"""
institutional_finance_engine/views.py — DEPRECATED (Phase 1A). See
apps.py's module docstring: 100% static content, zero real functionality.
financial_intelligence_cloud is the real institutional intelligence
interface going forward. Not to be extended with new content or logic.
"""
from django.shortcuts import render

# Connected EcoIQ modules — the Finance Engine turns verified evidence into investable decisions
CONNECTED_MODULES = [
    {'name': 'Asset Passport', 'role': 'Supplies the asset record and baseline a finance case is built from.'},
    {'name': 'Industrial Playbook Library', 'role': 'Supplies the modernisation pathways compared as finance scenarios.'},
    {'name': 'Supplier & Funding Marketplace', 'role': 'Supplies supplier quotes and candidate funding routes.'},
    {'name': 'Impact MRV Layer', 'role': 'Supplies verified before/after results used to validate assumptions.'},
    {'name': 'Amanah Autopilot', 'role': 'Runs overnight finance-readiness checks and drafts investor memos for approval.'},
    {'name': 'Omnimodal Evidence Panel', 'role': 'Supplies the visual and document evidence a finance case is grounded in.'},
    {'name': 'Microsoft Ecosystem Core Stack', 'role': 'Provides the agent, data and dashboard building blocks a production finance engine would run on.'},
    {'name': 'Maqasid/Mizan ethical scoring', 'role': 'Scores whether a financed pathway actually protects health, wealth and resources.'},
    {'name': 'No Harm Gate', 'role': 'Blocks a project from financing until debt-burden and harm risks are checked.'},
    {'name': 'Power BI dashboards', 'role': 'Visualises the finance and investment committee pipeline.'},
    {'name': 'Digital Twins', 'role': 'Model the asset so financial scenarios can be simulated before capital commits.'},
    {'name': 'MRV verified impact', 'role': 'Grounds ROI, emissions and impact claims in verified rather than assumed results.'},
]

CORE_PURPOSE = (
    'Turn verified modernisation opportunities into finance-ready, risk-aware, ethically '
    'aligned investment cases.'
)

FINANCE_LAYERS = [
    {
        'number': 1,
        'title': 'Framing Layer',
        'purpose': 'Frame the correct investment question before modelling.',
        'capabilities': [
            'Investment question framing', 'Modernisation thesis development',
            'Risk identification', 'Catalyst identification', 'Evidence checklist',
            'Missing data list', 'Decision objective definition',
        ],
        'example_bad_question': 'Should we replace the boiler?',
        'example_good_question': 'Which modernisation pathway reduces energy waste, health '
                                  'harm, emissions and financial risk while improving '
                                  'Maqasid/Mizan score and investment readiness?',
        'example_sectors': [],
        'metrics': [],
        'formulas': [],
        'scenarios': [],
        'workflows': [],
        'outputs': [],
    },
    {
        'number': 2,
        'title': 'Intelligence Layer',
        'purpose': 'Understand the sector, asset, market and context.',
        'capabilities': [
            'Sector analysis', 'Supplier mapping', 'Benchmark comparison', 'Peer comparison',
            'Regulation tracking', 'Funding landscape', 'Technology maturity assessment',
            'Greenwashing risk check',
        ],
        'example_bad_question': '',
        'example_good_question': '',
        'example_sectors': [
            'Boilers', 'District heating', 'Manufacturing', 'Mining', 'Agriculture',
            'Solar + battery', 'Water recycling', 'Waste heat recovery', 'SMR feasibility',
        ],
        'metrics': [],
        'formulas': [],
        'scenarios': [],
        'workflows': [],
        'outputs': [],
    },
    {
        'number': 3,
        'title': 'Valuation Layer',
        'purpose': 'Calculate financial attractiveness.',
        'capabilities': [],
        'example_bad_question': '',
        'example_good_question': '',
        'example_sectors': [],
        'metrics': [
            'CAPEX', 'OPEX savings', 'Annual cash savings', 'Payback period', 'IRR', 'NPV',
            'Risk-adjusted return', 'Avoided fuel cost', 'Avoided maintenance cost',
            'Avoided emissions cost where relevant', 'Grant contribution', 'Funding gap',
            'Sensitivity to energy prices',
        ],
        'formulas': [
            'Payback = CAPEX / Annual Savings',
            'NPV = discounted future cash flows minus initial investment',
            'IRR = discount rate where NPV equals zero',
        ],
        'scenarios': [],
        'workflows': [],
        'outputs': [],
    },
    {
        'number': 4,
        'title': 'Modelling Layer',
        'purpose': 'Compare modernisation scenarios.',
        'capabilities': [],
        'example_bad_question': '',
        'example_good_question': '',
        'example_sectors': [],
        'metrics': [],
        'formulas': [],
        'scenarios': [
            'A. Do nothing', 'B. Efficiency first', 'C. Equipment upgrade',
            'D. Clean energy transition', 'E. Hybrid pathway',
            'F. SMR / major infrastructure feasibility where relevant',
        ],
        'workflows': [
            'Cash flow forecasting', 'Scenario analysis', 'Sensitivity analysis',
            'Grant/CSR contribution modelling', 'Islamic finance structure modelling',
            'Debt/leasing modelling', 'Supplier quote comparison', 'Risk-adjusted modelling',
            'Carbon/impact value modelling where evidence supports it',
        ],
        'outputs': [],
    },
    {
        'number': 5,
        'title': 'Decision Engine Layer',
        'purpose': 'Generate outputs for real decision-makers.',
        'capabilities': [],
        'example_bad_question': '',
        'example_good_question': '',
        'example_sectors': [],
        'metrics': [],
        'formulas': [],
        'scenarios': [],
        'workflows': [],
        'outputs': [
            'Investor memo', 'Credit/risk assessment', 'Grant application brief',
            'CSR sponsor memo', 'Islamic finance summary', 'Board memo',
            'Akimat/government memo', 'Supplier finance brief', 'Project readiness score',
            'Investment committee checklist',
        ],
    },
]

FINANCIAL_DECISION_CARDS = [
    {
        'title': 'Project Readiness Score',
        'includes': [
            'Data quality', 'Supplier quote readiness', 'CAPEX clarity',
            'OPEX savings confidence', 'Payback attractiveness', 'Implementation risk',
            'MRV readiness', 'Maqasid/Mizan alignment',
        ],
    },
    {
        'title': 'Finance Fit Score',
        'includes': [
            'Grant fit', 'CSR fit', 'Green finance fit', 'Islamic finance fit',
            'Development bank fit', 'Investor fit', 'Municipal co-finance fit',
        ],
    },
    {
        'title': 'Risk-Adjusted Return',
        'includes': [
            'Technical risk', 'Execution risk', 'Supplier risk', 'Regulatory risk',
            'Community risk', 'Evidence risk', 'Greenwashing risk', 'No Harm Gate risk',
        ],
    },
    {
        'title': 'Islamic Finance Fit',
        'includes': [
            'Ijara / leasing suitability', 'Murabaha-style equipment financing suitability',
            'Sukuk suitability for larger infrastructure',
            'Waqf suitability for community assets',
            'Sadaqah jariyah suitability for clean heating and vulnerable households',
            'Transparency and fairness check', 'Debt burden warning',
            'Shariah review required where relevant',
        ],
    },
]

ISLAMIC_FINANCE_DISCLAIMER = (
    'EcoIQ does not present Islamic finance judgement as a fatwa. Qualified Islamic finance '
    'and Shariah review is required before any Islamic finance structure is used.'
)

EXAMPLE_CARDS = [
    {
        'project': 'Boiler House #3 Modernisation',
        'evidence': [
            'Old coal boiler', 'Uninsulated pipes', 'Visible soot', 'No smart meter',
            'High fuel bills', 'Maintenance risk',
        ],
        'scenarios': [
            {
                'letter': 'A',
                'title': 'Do nothing',
                'details': ['CAPEX: low', 'Risk: rising', 'Emissions: high', 'Maqasid/Mizan: weak'],
            },
            {
                'letter': 'B',
                'title': 'Efficiency first',
                'details': [
                    'Pipe insulation', 'Smart meters', 'Boiler servicing', 'Controls',
                    'CAPEX: low/medium', 'Payback: fast', 'MRV readiness: high',
                ],
            },
            {
                'letter': 'C',
                'title': 'Equipment upgrade',
                'details': [
                    'Modern boiler / pumps / controls', 'CAPEX: medium/high',
                    'Payback: medium', 'Funding needed',
                ],
            },
            {
                'letter': 'D',
                'title': 'Clean heat transition',
                'details': [
                    'Heat pump / electric boiler / district heating integration',
                    'CAPEX: high', 'Emissions reduction: higher',
                    'Requires feasibility and finance',
                ],
            },
        ],
        'finance_output': 'Start with Scenario B to reduce waste quickly and create verified '
                           'baseline data. Prepare Scenario C/D for staged financing.',
        'example_metrics': [
            'CAPEX estimate', 'Annual savings estimate', 'Payback estimate',
            'Emissions reduction estimate', 'Maqasid score improvement',
            'Mizan score improvement', 'Evidence quality', 'Funding gap',
            'Recommended finance route',
        ],
        'finance_logic': '',
        'finance_routes': [],
        'maqasid_mizan_meaning': '',
    },
    {
        'project': 'Factory Compressed Air Optimisation',
        'evidence': [
            'Compressor runs continuously', 'Pressure drops', 'No leak monitoring',
            'High electricity cost',
        ],
        'scenarios': [],
        'finance_output': '',
        'example_metrics': [],
        'finance_logic': 'Quick payback project funded through internal savings, energy '
                          'efficiency grant or equipment leasing.',
        'finance_routes': [],
        'maqasid_mizan_meaning': '',
    },
    {
        'project': 'Village Clean Heating Transition',
        'evidence': [
            'Coal stove use', 'Indoor air harm', 'Fuel burden', 'Vulnerable households',
        ],
        'scenarios': [],
        'finance_output': '',
        'example_metrics': [],
        'finance_logic': '',
        'finance_routes': [
            'CSR sponsor', 'Sadaqah jariyah fund', 'Municipal co-finance',
            'Climate adaptation grant', 'Islamic charitable fund',
        ],
        'maqasid_mizan_meaning': 'Protect health, reduce harm, reduce waste and restore '
                                  'balance in household heating.',
    },
]

MEMO_STRUCTURE = [
    'Executive summary', 'Asset and baseline', 'Problem and evidence',
    'Modernisation options', 'Financial model', 'Risk assessment',
    'Maqasid/Mizan assessment', 'No Harm Gate', 'Funding route', 'MRV plan',
    'Decision recommendation', 'Human approval checklist',
]

FINANCE_WORKFLOW = [
    'Asset Passport', 'Evidence Review', 'Playbook Match', 'Supplier/Funding Match',
    'Scenario Model', 'Risk Assessment', 'Maqasid/Mizan Scoring', 'Finance Fit Score',
    'Investment Memo', 'Human Approval', 'Implementation', 'MRV Verified Impact',
]

AMANAH_INTEGRATION_INTRO = 'Amanah Autopilot can run overnight and prepare:'
AMANAH_INTEGRATION_ITEMS = [
    'New finance opportunities', 'Funding matches', 'Missing document list',
    'Draft investor memos', 'Grant readiness checks',
    'Projects with strong quick-payback potential',
    'Projects with high Maqasid/Mizan benefit',
]
AMANAH_MORNING_BRIEFING_EXAMPLE = (
    '2 finance-ready projects identified, 3 funding routes matched, 1 CSR memo drafted, '
    '4 missing documents flagged.'
)

MICROSOFT_INTEGRATION = [
    {'component': 'Microsoft Fabric', 'role': 'Financial/project data.'},
    {'component': 'Power BI', 'role': 'Dashboards and investment committee views.'},
    {'component': 'Azure AI / Agent Framework', 'role': 'Finance agents.'},
    {'component': 'Azure Digital Twins', 'role': 'Asset relationships.'},
    {'component': 'Power Automate', 'role': 'Approval workflows.'},
    {'component': 'Teams', 'role': 'Investment committee collaboration.'},
    {'component': 'SharePoint', 'role': 'Memo storage.'},
    {'component': 'Dynamics 365', 'role': 'Investor/funder pipeline tracking.'},
]

SAFETY_PRINCIPLES = [
    'EcoIQ financial outputs are decision-support, not investment advice.',
    'High-impact financial decisions require qualified financial, legal, tax and technical review.',
    'Islamic finance suitability requires qualified Shariah review.',
    'Maqasid/Mizan is ethical decision-support, not a fatwa.',
    'If evidence or assumptions are incomplete, the system must show "Needs verification".',
    'Do not allow unsupported ROI, emissions or impact claims.',
]

NO_HARM_GATE_FINANCE = [
    'Is the project technically justified?',
    'Is the debt burden fair?',
    'Are vulnerable households protected?',
    'Are workers or communities harmed?',
    'Is environmental impact properly assessed?',
    'Are assumptions transparent?',
    'Is evidence strong enough?',
    'Is human approval recorded?',
    'Is Shariah/Islamic finance review required?',
]

CTA_BUTTONS = [
    {'label': 'Run Finance Model', 'anchor': '#valuation-layer'},
    {'label': 'Generate Investor Memo', 'url_name': 'legacy_safe:ask'},
    {'label': 'Assess Finance Fit', 'anchor': '#financial-decision-cards'},
    {'label': 'Calculate Payback', 'anchor': '#valuation-layer'},
    {'label': 'Prepare Grant Brief', 'url_name': 'leads:request_review'},
    {'label': 'Check Islamic Finance Fit', 'anchor': '#islamic-finance-fit'},
    {'label': 'Export to Power BI', 'anchor': '#microsoft-integration'},
    {'label': 'Start MRV Tracking', 'url_name': 'impact_mrv_layer:overview'},
]


def overview(request):
    return render(request, 'institutional_finance_engine/overview.html', {
        'connected_modules': CONNECTED_MODULES,
        'core_purpose': CORE_PURPOSE,
        'finance_layers': FINANCE_LAYERS,
        'financial_decision_cards': FINANCIAL_DECISION_CARDS,
        'islamic_finance_disclaimer': ISLAMIC_FINANCE_DISCLAIMER,
        'example_cards': EXAMPLE_CARDS,
        'memo_structure': MEMO_STRUCTURE,
        'finance_workflow': FINANCE_WORKFLOW,
        'amanah_integration_intro': AMANAH_INTEGRATION_INTRO,
        'amanah_integration_items': AMANAH_INTEGRATION_ITEMS,
        'amanah_morning_briefing_example': AMANAH_MORNING_BRIEFING_EXAMPLE,
        'microsoft_integration': MICROSOFT_INTEGRATION,
        'safety_principles': SAFETY_PRINCIPLES,
        'no_harm_gate_finance': NO_HARM_GATE_FINANCE,
        'cta_buttons': CTA_BUTTONS,
    })
