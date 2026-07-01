"""
LegacySafe AI — full industrial modernisation planner.

MVP: a structured mock response built only from chunks retrieval already cleared for this
user. No LLM call yet — this is the seam where a real model call (see services/llm_provider.py)
plugs in later. When it does, the allowed chunk text must still be treated as inert evidence,
never as instructions: retrieval has already filtered it, but content (e.g. the seeded
prompt-injection demo document) can still contain text that *looks* like an instruction. The
system prompt for the real model must say so explicitly.

The plan covers the full EcoIQ industrial modernisation pathway — solar PV, battery storage,
heat pumps, boiler replacement, insulation, smart meters/IoT, grid optimisation, equipment
procurement, staged CAPEX/OPEX, worker/community transition, and a Justice & Maqasid review —
built from deterministic, per-document_type seed content, not real engineering calculations.
"""
from legacy_safe.models import MemoryChunk
from legacy_safe.services.retrieval import retrieve_allowed_chunks

# Each entry maps a SourceDocument.document_type onto one plan section. Several document types
# feed the same section (e.g. 'budget' and 'capex_opex' both feed 'finance'); their summaries
# are concatenated in the order chunks were encountered.
PLANNER_SECTIONS = {
    'solar_battery': {
        'section': 'energy_generation',
        'section_title': 'Energy Generation: Solar PV and Battery Storage',
        'summary': (
            'The engineering review covers rooftop and land-based solar PV opportunities, '
            'battery storage sizing, inverter selection, grid-connection constraints, and '
            'load-shifting potential for resilience.'
        ),
        'risk_note': 'Grid connection and inverter capacity constraints must be resolved before solar/battery sizing is finalised.',
        'action_30': 'Confirm solar PV site survey and battery sizing assumptions.',
        'action_60': 'Select inverter and battery suppliers; finalise grid connection application.',
        'action_90': 'Approve solar PV and battery storage procurement package.',
    },
    'heat_pump_boiler': {
        'section': 'clean_heat',
        'section_title': 'Clean Heat: Heat Pumps, Electric Boilers, Buffer Tanks and Boiler Replacement',
        'summary': (
            'Legacy coal boilers are replaced through a phased clean-heat architecture using '
            'industrial heat pumps, backup electric boilers, buffer tanks, upgraded controls, '
            'and staged commissioning.'
        ),
        'risk_note': 'Staged boiler decommissioning must avoid heat-supply interruption during commissioning.',
        'action_30': 'Finalise heat pump and electric boiler sizing with the engineering team.',
        'action_60': 'Schedule phased boiler decommissioning and buffer tank installation.',
        'action_90': 'Commission the clean-heat system and retire the legacy coal boiler.',
    },
    'insulation': {
        'section': 'efficiency',
        'section_title': 'Efficiency: Insulation, Heat-Loss Reduction, Leak Detection and Smart Controls',
        'summary': (
            'Pipe insulation, building envelope upgrades, heat network balancing, leak '
            'detection, valve upgrades, and improved temperature control reduce thermal losses.'
        ),
        'risk_note': 'Unaddressed heat-network leaks reduce the effectiveness of the clean-heat investment.',
        'action_30': 'Complete a heat-loss and leak-detection survey.',
        'action_60': 'Install pipe insulation and valve upgrades on priority heat-loss sites.',
        'action_90': 'Verify heat-network balancing and temperature control performance.',
    },
    'smart_meters_iot': {
        'section': 'smart_meters_iot_predictive_maintenance',
        'section_title': 'Smart Meters, IoT Sensors and Predictive Maintenance',
        'summary': (
            'Predictive-maintenance dashboards draw on smart meters, IoT sensors, vibration '
            'monitoring, temperature sensors, flow meters, and fault detection to reduce '
            'downtime and improve operational efficiency.'
        ),
        'risk_note': None,
        'action_30': 'Deploy smart meters and IoT sensors on priority equipment.',
        'action_60': 'Stand up predictive-maintenance dashboards and fault-detection alerts.',
        'action_90': 'Review the first predictive-maintenance cycle and adjust thresholds.',
    },
    'grid_optimisation': {
        'section': 'grid_load_optimisation',
        'section_title': 'Grid and Load Optimisation',
        'summary': (
            'Peak demand, demand response, flexible loads, battery dispatch, solar generation '
            'profiles, transformer capacity, power quality, and operational scheduling are '
            'assessed together.'
        ),
        'risk_note': 'Transformer capacity limits could constrain solar and battery dispatch if not assessed early.',
        'action_30': 'Assess peak demand and transformer capacity headroom.',
        'action_60': 'Design demand-response and battery-dispatch scheduling.',
        'action_90': 'Implement operational scheduling and validate power quality.',
    },
    'procurement': {
        'section': 'equipment_lifecycle_procurement',
        'section_title': 'Equipment Lifecycle and Procurement',
        'summary': (
            'Supplier comparison covers solar panels, inverters, batteries, heat pumps, '
            'electric boilers, sensors, smart meters, control systems, insulation materials, '
            'maintenance contracts, warranties, and lifecycle cost.'
        ),
        'risk_note': 'Warranty and lifecycle-cost gaps between suppliers can erode long-term savings if not compared explicitly.',
        'action_30': 'Issue supplier RFQs for priority equipment categories.',
        'action_60': 'Compare bids on warranty, lifecycle cost, and maintenance terms.',
        'action_90': 'Award procurement contracts for approved equipment.',
    },
    'budget': {
        'section': 'finance',
        'section_title': 'Finance: Staged CAPEX/OPEX and ROI',
        'summary': (
            'Staged capital expenditure covers solar PV, battery storage, heat pump '
            'integration, boiler replacement, insulation, grid upgrades, monitoring '
            'equipment, controls, process optimisation, and contingency reserves.'
        ),
        'risk_note': 'Underfunded contingency reserves increase the risk of stalled phases.',
        'action_30': 'Confirm staged CAPEX allocation across phases.',
        'action_60': 'Finalise financing terms and contingency reserve sizing.',
        'action_90': 'Secure board approval for the staged investment budget.',
    },
    'capex_opex': {
        'section': 'finance',
        'section_title': 'Finance: Staged CAPEX/OPEX and ROI',
        'summary': (
            'Financial evaluation compares upfront CAPEX, long-term OPEX savings, fuel '
            'displacement, maintenance reduction, carbon cost exposure, payback period, '
            'financing options, and risk-adjusted return.'
        ),
        'risk_note': 'Payback assumptions must account for carbon cost exposure and fuel-price volatility.',
        'action_30': 'Complete CAPEX/OPEX and payback-period modelling.',
        'action_60': 'Stress-test ROI against fuel-price and carbon-cost scenarios.',
        'action_90': 'Present risk-adjusted ROI to the board for financing sign-off.',
    },
    'strategy_memo': {
        'section': 'risk_and_dependency_map',
        'section_title': 'Risk and Dependency Map',
        'summary': (
            'The board strategy links clean energy generation, heat system replacement, '
            'operational efficiency, grid resilience, financing, worker transition, public '
            'communication, regulatory compliance, and investor confidence as interdependent '
            'workstreams.'
        ),
        'risk_note': 'Regulatory, financing, and worker-transition workstreams must be sequenced together, not treated as independent risks.',
        'action_30': 'Confirm the board-level sequencing of interdependent workstreams.',
        'action_60': 'Resolve cross-workstream dependencies flagged in the risk map.',
        'action_90': 'Secure board sign-off on the phased modernisation strategy.',
    },
    'worker_community': {
        'section': 'worker_community_transition',
        'section_title': 'Worker and Community Transition',
        'summary': (
            'The transition plan includes worker retraining, safety training, local '
            'supplier development, household affordability protection, community '
            'communication, regional transition support, and support for communities '
            'affected by coal phase-down.'
        ),
        'risk_note': 'Unmanaged worker or household affordability impacts can undermine public support for the transition.',
        'action_30': 'Launch worker and community communication on the transition timeline.',
        'action_60': 'Begin worker retraining and local supplier development programmes.',
        'action_90': 'Confirm household affordability protection measures are in place.',
    },
    'justice_maqasid': {
        'section': 'justice_maqasid_review',
        'section_title': 'Justice & Maqasid Review',
        'summary': (
            'Modernisation is reviewed for reduced harm to health, protection of public '
            'resources, transparency, support for families and workers, prevention of unfair '
            'cost transfer to vulnerable households, protection of natural resources, and '
            'benefit to future generations through emissions reduction.'
        ),
        'risk_note': None,
        'action_30': 'Run the Justice & Maqasid review against the draft modernisation plan.',
        'action_60': 'Address any red-flag findings from the Justice & Maqasid review.',
        'action_90': 'Confirm Justice & Maqasid sign-off before final approval.',
    },
}

# Order the numbered/titled sections appear in the returned plan and on the Ask Agent page.
SECTION_ORDER = [
    'energy_generation',
    'clean_heat',
    'efficiency',
    'grid_load_optimisation',
    'smart_meters_iot_predictive_maintenance',
    'equipment_lifecycle_procurement',
    'process_optimisation',
    'finance',
    'risk_and_dependency_map',
    'worker_community_transition',
    'justice_maqasid_review',
]

# document_types that feed "process optimisation" as a derived, cross-cutting section rather
# than a section of their own.
_PROCESS_OPTIMISATION_SOURCES = {'insulation', 'smart_meters_iot', 'grid_optimisation'}


def generate_modernisation_plan(user, project, question):
    """Return a full industrial modernisation plan built only from evidence this user is allowed to see."""
    retrieval = retrieve_allowed_chunks(user, project, question)
    allowed = retrieval['allowed']
    blocked = retrieval['blocked']

    sections = {}
    section_titles = {}
    risk_notes = []
    next_actions = {'30_day': [], '60_day': [], '90_day': []}
    seen_doc_types = set()
    has_esg = False

    for entry in allowed:
        chunk = MemoryChunk.objects.select_related('source_document').get(id=entry['chunk_id'])
        doc_type = chunk.source_document.document_type
        if doc_type in seen_doc_types:
            continue
        seen_doc_types.add(doc_type)

        if doc_type == 'esg_report':
            has_esg = True
            continue

        spec = PLANNER_SECTIONS.get(doc_type)
        if not spec:
            continue

        key = spec['section']
        sections.setdefault(key, []).append(spec['summary'])
        section_titles[key] = spec['section_title']
        if spec.get('risk_note'):
            risk_notes.append(spec['risk_note'])
        if spec.get('action_30'):
            next_actions['30_day'].append(spec['action_30'])
        if spec.get('action_60'):
            next_actions['60_day'].append(spec['action_60'])
        if spec.get('action_90'):
            next_actions['90_day'].append(spec['action_90'])

    if any(k in sections for k in _PROCESS_OPTIMISATION_SOURCES):
        sections['process_optimisation'] = [
            'Insulation upgrades, smart metering and IoT monitoring, and grid and load '
            'scheduling together drive process optimisation across the facility.'
        ]
        section_titles['process_optimisation'] = 'Process Optimisation'

    if risk_notes:
        sections['risk_and_dependency_map'] = sections.get('risk_and_dependency_map', []) + risk_notes
        section_titles.setdefault('risk_and_dependency_map', 'Risk and Dependency Map')

    populated_titles = [section_titles[k] for k in SECTION_ORDER if k in sections]
    if populated_titles:
        executive_summary = (
            f'Based on {len(allowed)} allowed evidence item(s), the industrial modernisation '
            f'plan for "{project.name}" covers: ' + '; '.join(populated_titles) + '.'
        )
    else:
        executive_summary = 'No evidence was accessible for this role — no plan could be generated.'
    if has_esg:
        executive_summary += (
            ' ESG priorities frame the plan around emissions reduction, clean heat '
            'transition, and infrastructure resilience.'
        )
    if blocked:
        executive_summary += (
            f' {len(blocked)} additional source(s) exist but were excluded due to '
            'insufficient permissions.'
        )

    plan_sections = [
        {'key': key, 'title': section_titles[key], 'content': ' '.join(sections[key])}
        for key in SECTION_ORDER if key in sections
    ]

    return {
        'executive_summary': executive_summary,
        'sections': plan_sections,
        'evidence_used': [
            {'source_title': e['source_title'], 'access_level': e['access_level'], 'text': e['text']}
            for e in allowed
        ],
        'restricted_evidence_excluded': [
            {'source_title': e['source_title'], 'access_level': e['access_level'], 'reason': e['reason']}
            for e in blocked
        ],
        'next_actions': next_actions,
        'audit_log': retrieval['audit_log'],
    }
