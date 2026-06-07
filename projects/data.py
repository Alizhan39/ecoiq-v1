"""
EcoIQ Projects — Phase 1 static data source.

Single source of truth for the Projects section. No database, no models, no
migrations — each project is a plain dict. This schema deliberately mirrors the
fields a future `Project` model (Phase 2, Wagtail-backed) would carry, so the
section can be promoted to a CMS-managed model without changing URLs, view names
or templates.

ALL financial, KPI and timeline figures are INDICATIVE pilot estimates unless a
project is explicitly confirmed. They are labelled as such in the templates.
"""

# Status vocabulary (key → display label). Keys map to CSS badge classes.
STATUS_LABELS = {
    'concept':   'Concept',
    'scoping':   'Scoping',
    'design':    'In Design',
    'pilot':     'Pilot',
    'scaling':   'Scaling',
}


PROJECTS = [
    {
        'slug': 'almaty-clean-air',
        'name': 'Almaty Clean Air Pilot',
        'tagline': 'Replacing coal heating in one of the world’s most polluted winter cities.',
        'icon': '🏭',
        'accent': 'green',
        'status_key': 'design',
        'location': 'Almaty, Kazakhstan',
        'sector': 'Air Quality · Clean Heating',
        'timeline_label': '2025–2026 (indicative)',

        'overview': (
            'A neighbourhood-scale pilot to replace coal-fired household heating with cleaner '
            'alternatives in Almaty’s highest-pollution districts, paired with EcoIQ measurement '
            'of air-quality and public-health outcomes.'
        ),
        'problem': (
            'Almaty experiences severe winter air pollution driven largely by coal heating in '
            'private households. Residents face elevated PM2.5 exposure, respiratory illness and '
            'limited visibility into where interventions would have the greatest health impact.'
        ),
        'solution': (
            'EcoIQ identifies priority households, supports a transition to cleaner heating, and '
            'measures the before/after impact on local air quality and health. The pilot establishes '
            'a repeatable, evidence-based model for clean-heating transitions across the city.'
        ),
        'expected_impact': [
            {'value': '↓ PM2.5', 'label': 'Lower winter particulate exposure in pilot zone'},
            {'value': 'Health', 'label': 'Measurable reduction in respiratory risk'},
            {'value': 'Model', 'label': 'Repeatable clean-heating transition blueprint'},
        ],
        'kpis': [
            {'code': 'MQV', 'label': 'Maqasid Value Added', 'note': 'Health + environmental value created'},
            {'code': 'FHI', 'label': 'Fasad Harm Index', 'note': 'Reduction in pollution harm'},
            {'code': 'RPI', 'label': 'Rahma Performance Index', 'note': 'Benefit to vulnerable households'},
        ],
        'timeline_phases': [
            {'phase': 'Phase 1', 'window': 'Design', 'detail': 'Map priority households and baseline air quality.'},
            {'phase': 'Phase 2', 'window': 'Pilot', 'detail': 'Deploy cleaner heating in selected homes.'},
            {'phase': 'Phase 3', 'window': 'Measure', 'detail': 'Quantify air-quality and health outcomes; publish.'},
        ],
        'partnership_opportunities': [
            'Municipal and public-health authorities',
            'Clean-heating technology suppliers',
            'Air-quality monitoring and academic partners',
        ],
        'funding_amount': '£15,000',
        'funding_label': 'pilot (indicative)',
        'funding_note': 'Indicative pilot budget — covers priority-household transition and impact measurement.',
    },
    {
        'slug': 'lake-restoration',
        'name': 'Lake Restoration Initiative',
        'tagline': 'Restoring a degraded lake ecosystem and the livelihoods around it.',
        'icon': '💧',
        'accent': 'blue',
        'status_key': 'scoping',
        'location': 'Kazakhstan (site scoping)',
        'sector': 'Water · Ecosystem Restoration',
        'timeline_label': '2025–2027 (indicative)',

        'overview': (
            'An ecosystem-recovery initiative to restore a degraded lake and its surrounding '
            'watershed, reviving biodiversity, water security and local livelihoods.'
        ),
        'problem': (
            'Many regional lakes have been degraded by over-extraction, pollution and habitat loss, '
            'undermining water security, fisheries and the communities that depend on them.'
        ),
        'solution': (
            'EcoIQ scopes a restoration programme covering water quality, habitat recovery and '
            'community co-management, with transparent measurement of ecological and social recovery '
            'against a clear baseline.'
        ),
        'expected_impact': [
            {'value': 'Biodiversity', 'label': 'Recovered habitat and species'},
            {'value': 'Water', 'label': 'Improved water security and quality'},
            {'value': 'Livelihoods', 'label': 'Restored local economic activity'},
        ],
        'kpis': [
            {'code': 'KHI', 'label': 'Khalifah Impact Index', 'note': 'Restoration relative to resources used'},
            {'code': 'MBI', 'label': 'Mizan Balance Index', 'note': 'Regeneration vs consumption'},
            {'code': 'RPI', 'label': 'Rahma Performance Index', 'note': 'Benefit to dependent communities'},
        ],
        'timeline_phases': [
            {'phase': 'Phase 1', 'window': 'Scoping', 'detail': 'Select site; establish ecological baseline.'},
            {'phase': 'Phase 2', 'window': 'Restore', 'detail': 'Water-quality and habitat interventions.'},
            {'phase': 'Phase 3', 'window': 'Sustain', 'detail': 'Community co-management and monitoring.'},
        ],
        'partnership_opportunities': [
            'Environmental agencies and regulators',
            'Hydrology and ecology research institutions',
            'Local community and fishery cooperatives',
        ],
        'funding_amount': '£10,000',
        'funding_label': 'pilot (indicative)',
        'funding_note': 'Indicative pilot budget — covers site scoping, baseline and initial restoration.',
    },
    {
        'slug': 'community-greenhouses',
        'name': 'Community Greenhouse Program',
        'tagline': 'Food-resilience infrastructure for communities facing supply shocks.',
        'icon': '🌾',
        'accent': 'gold',
        'status_key': 'design',
        'location': 'Kazakhstan (multi-site)',
        'sector': 'Food Security · Resilience',
        'timeline_label': '2025–2026 (indicative)',

        'overview': (
            'A programme to deploy community greenhouse infrastructure enabling year-round local food '
            'production and reducing dependence on fragile supply chains.'
        ),
        'problem': (
            'Communities in harsh-climate regions face seasonal food insecurity, price volatility and '
            'long, fragile supply chains for fresh produce.'
        ),
        'solution': (
            'EcoIQ supports community-operated greenhouses that produce fresh food locally year-round, '
            'building resilience and local economic capacity, with impact measured per site.'
        ),
        'expected_impact': [
            {'value': 'Food', 'label': 'Year-round local fresh produce'},
            {'value': 'Resilience', 'label': 'Reduced supply-chain fragility'},
            {'value': 'Jobs', 'label': 'Local economic participation'},
        ],
        'kpis': [
            {'code': 'MQV', 'label': 'Maqasid Value Added', 'note': 'Food, health and economic value'},
            {'code': 'RZQ', 'label': 'Rizq Distribution Coefficient', 'note': 'Fair distribution of value locally'},
            {'code': 'RPI', 'label': 'Rahma Performance Index', 'note': 'Benefit to food-insecure households'},
        ],
        'timeline_phases': [
            {'phase': 'Phase 1', 'window': 'Design', 'detail': 'Select sites; design community model.'},
            {'phase': 'Phase 2', 'window': 'Pilot', 'detail': 'Build and operate first greenhouses.'},
            {'phase': 'Phase 3', 'window': 'Scale', 'detail': 'Replicate across additional communities.'},
        ],
        'partnership_opportunities': [
            'Agricultural and food-security organisations',
            'Local authorities and community groups',
            'Greenhouse technology and agronomy partners',
        ],
        'funding_amount': '£25,000',
        'funding_label': 'pilot (indicative)',
        'funding_note': 'Indicative pilot budget — covers initial greenhouse build-out and operations.',
    },
    {
        'slug': 'khalifah-living',
        'name': 'Khalifah Living Experience',
        'tagline': 'An immersive leadership, service and sustainability programme.',
        'icon': '🧭',
        'accent': 'purple',
        'status_key': 'concept',
        'location': 'Kazakhstan (pilot cohort)',
        'sector': 'Leadership · Capacity Building',
        'timeline_label': '2026 (indicative)',

        'overview': (
            'An immersive programme developing a pipeline of practitioners trained in real-world '
            'stewardship — combining leadership, service and hands-on sustainability work.'
        ),
        'problem': (
            'The transition to a regenerative economy is constrained by a shortage of people who can '
            'lead and deliver real-world stewardship projects on the ground.'
        ),
        'solution': (
            'EcoIQ designs an immersive cohort experience pairing leadership development with practical '
            'service on live stewardship projects, creating capable, values-driven practitioners.'
        ),
        'expected_impact': [
            {'value': 'Talent', 'label': 'Trained stewardship practitioners'},
            {'value': 'Delivery', 'label': 'Hands-on contribution to live projects'},
            {'value': 'Network', 'label': 'A growing community of practice'},
        ],
        'kpis': [
            {'code': 'AMN', 'label': 'Amanah Trust Score', 'note': 'Ethical stewardship and accountability'},
            {'code': 'KHI', 'label': 'Khalifah Impact Index', 'note': 'Real-world improvement delivered'},
            {'code': 'MQV', 'label': 'Maqasid Value Added', 'note': 'Human-capacity value created'},
        ],
        'timeline_phases': [
            {'phase': 'Phase 1', 'window': 'Concept', 'detail': 'Design curriculum and cohort model.'},
            {'phase': 'Phase 2', 'window': 'Pilot', 'detail': 'Run first immersive cohort.'},
            {'phase': 'Phase 3', 'window': 'Iterate', 'detail': 'Refine and expand the programme.'},
        ],
        'partnership_opportunities': [
            'Universities and leadership institutions',
            'Foundations supporting capacity building',
            'Host sites across the EcoIQ project portfolio',
        ],
        'funding_amount': '£10,000',
        'funding_label': 'pilot (indicative)',
        'funding_note': 'Indicative pilot budget — covers first cohort design and delivery.',
    },
    {
        'slug': 'future-ecoiq-villages',
        'name': 'Future EcoIQ Villages',
        'tagline': 'An integrated, regenerative community model combining every pilot.',
        'icon': '🏘️',
        'accent': 'teal',
        'status_key': 'concept',
        'location': 'To be determined',
        'sector': 'Integrated Regenerative Development',
        'timeline_label': 'Long-term vision',

        'overview': (
            'A long-term vision integrating clean air, water restoration, food resilience, community '
            'economy and stewardship leadership into a single replicable, low-harm settlement model.'
        ),
        'problem': (
            'Individual interventions help, but lasting change needs integrated communities designed '
            'around regeneration, resilience and equitable value — a model that can be replicated.'
        ),
        'solution': (
            'EcoIQ brings its pilots together into an integrated village blueprint — measured end-to-end '
            'across all EcoIQ KPIs — to demonstrate what a regenerative community can achieve at scale.'
        ),
        'expected_impact': [
            {'value': 'Integrated', 'label': 'All stewardship pilots in one model'},
            {'value': 'Replicable', 'label': 'A blueprint others can adopt'},
            {'value': 'Regenerative', 'label': 'Net-positive community by design'},
        ],
        'kpis': [
            {'code': 'MBI', 'label': 'Mizan Balance Index', 'note': 'Whole-system regeneration vs consumption'},
            {'code': 'MQV', 'label': 'Maqasid Value Added', 'note': 'Total community value created'},
            {'code': 'AMN', 'label': 'Amanah Trust Score', 'note': 'Governance and accountability of the model'},
        ],
        'timeline_phases': [
            {'phase': 'Phase 1', 'window': 'Vision', 'detail': 'Define the integrated village blueprint.'},
            {'phase': 'Phase 2', 'window': 'Feasibility', 'detail': 'Site, partners and funding model.'},
            {'phase': 'Phase 3', 'window': 'Build', 'detail': 'Deliver the first integrated community.'},
        ],
        'partnership_opportunities': [
            'Development finance institutions and impact funds',
            'Government and regional development partners',
            'Foundations and long-horizon investors',
        ],
        'funding_amount': 'Concept stage',
        'funding_label': '',
        'funding_note': 'Funding model to be defined as the concept matures.',
    },
]

# Fast slug lookup for the detail view.
PROJECTS_BY_SLUG = {p['slug']: p for p in PROJECTS}


def status_label(status_key):
    return STATUS_LABELS.get(status_key, status_key.title())
