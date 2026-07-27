"""
ai_agent_council/agents.py — the real EcoIQ agent roster and repository scan.

Extracted from views.py so both views.py and the services/ package can import
agent metadata without a circular import (services/*.py need this data too).
"""
from pathlib import Path

from django.conf import settings

# The 10 files every operational agent training pack must contain.
REQUIRED_AGENT_FILES = [
    'README.md', 'system_prompt.md', 'role.md', 'inputs.md', 'outputs.md',
    'tools.md', 'safety_rules.md', 'test_cases.json', 'evals.md', 'demo_scenarios.md',
]

MASTER_INDEX_FILENAME = 'ai_agent_training_index.md'


def _scan_ai_agents_repo_state():
    """
    Read the real ai_agents/ directory on disk so the counts shown on this
    page always reflect the actual repository state rather than a hardcoded
    number that could go stale if the repo structure changes.
    """
    base = Path(settings.BASE_DIR) / 'ai_agents'
    operational_folder_names = []
    total_training_files = 0
    per_folder_files = {}

    if base.is_dir():
        for entry in sorted(base.iterdir()):
            if entry.is_dir():
                present = [f for f in REQUIRED_AGENT_FILES if (entry / f).is_file()]
                if present:
                    operational_folder_names.append(entry.name)
                    total_training_files += len(present)
                    per_folder_files[entry.name] = present

    master_index_exists = (base / MASTER_INDEX_FILENAME).is_file()

    return {
        'operational_folder_names': operational_folder_names,
        'operational_folder_count': len(operational_folder_names),
        'total_training_files': total_training_files,
        'master_index_exists': master_index_exists,
        'per_folder_files': per_folder_files,
    }


OPERATIONAL_AGENTS = [
    {
        'number': 1, 'name': 'Research Agent', 'folder': 'research_agent',
        'role': 'Finds, compares and summarises trusted evidence.',
        'handoffs': ['Document Reader Agent'], 'important': '',
    },
    {
        'number': 2, 'name': 'Document Reader Agent', 'folder': 'document_reader_agent',
        'role': 'Extracts facts from bills, PDFs, reports, technical documents and supplier quotes.',
        'handoffs': ['Asset Passport Agent', 'Finance Modelling Agent', 'MRV Agent'], 'important': '',
    },
    {
        'number': 3, 'name': 'Photo / Visual Evidence Agent', 'folder': 'photo_visual_evidence_agent',
        'role': 'Analyses inspection photos and videos while labelling findings as hypotheses until verified.',
        'handoffs': ['Asset Passport Agent', 'Governance Agent'], 'important': '',
    },
    {
        'number': 4, 'name': 'Asset Passport Agent', 'folder': 'asset_passport_agent',
        'role': 'Creates the structured digital record of each industrial asset.',
        'handoffs': ['Industrial Playbook Matching Agent'], 'important': '',
    },
    {
        'number': 5, 'name': 'Industrial Playbook Matching Agent', 'folder': 'industrial_playbook_matching_agent',
        'role': 'Matches assets to modernisation pathways, quick wins and deeper upgrades.',
        'handoffs': ['Finance Modelling Agent', 'Supplier / Funding Match Agent later'], 'important': '',
    },
    {
        'number': 6, 'name': 'Finance Modelling Agent', 'folder': 'finance_modelling_agent',
        'role': 'Prepares draft CAPEX, OPEX, payback, funding gap and finance-readiness logic.',
        'handoffs': ['Governance Agent', 'Report Generator Agent'], 'important': '',
    },
    {
        'number': 7, 'name': 'MRV Agent', 'folder': 'mrv_agent',
        'role': 'Separates estimated impact from verified impact and checks baseline/after-data readiness.',
        'handoffs': ['Governance Agent', 'Public Trust workflows'], 'important': '',
    },
    {
        'number': 8, 'name': 'Governance Agent', 'folder': 'governance_agent',
        'role': 'Routes high-impact outputs to technical, finance, MRV, safety, privacy and ethical review.',
        'handoffs': ['Report Generator Agent'], 'important': '',
    },
    {
        'number': 9, 'name': 'Report Generator Agent', 'folder': 'report_generator_agent',
        'role': 'Builds evidence-linked investor memos, board packs, country briefs and public summaries.',
        'handoffs': ['Human approval', 'External output'], 'important': '',
    },
    {
        'number': 10, 'name': 'Amanah Autopilot Supervisor', 'folder': 'amanah_autopilot_supervisor',
        'role': 'Runs overnight checks, finds missing evidence, prepares review queues and generates the morning briefing.',
        'handoffs': [],
        'important': (
            'Amanah Autopilot prepares actions for human review. It must not be '
            'presented as independently making high-impact decisions.'
        ),
    },
    {
        'number': 11, 'name': 'Waste & Leakage Agent', 'folder': 'waste_leakage_agent',
        'role': 'Detects operational loss, quantifies financial exposure, and keeps actual/estimated/forecast figures visibly separate.',
        'handoffs': ['Document Reader Agent', 'Finance Modelling Agent'], 'important': '',
    },
    {
        'number': 12, 'name': 'Capital Allocation Agent', 'folder': 'capital_allocation_agent',
        'role': 'Ranks finance-modelled intervention options across 13 dimensions to recommend where the next £1 of capital should go.',
        'handoffs': ['Report Generator Agent', 'Governance Agent'],
        'important': (
            'Capital Allocation Agent produces a governed ranking for human and '
            'Council review. It must not be presented as making an autonomous '
            'investment decision.'
        ),
    },
    {
        'number': 13, 'name': 'Good Agent Orchestrator', 'folder': 'good_agent_orchestrator',
        'role': (
            'Takes one observed signal, activates only the relevant subset of the 114 canonical '
            'principle lenses (never all of them), and produces one combined reasoning pass that '
            'preserves disagreement between lenses rather than averaging it into a fake consensus.'
        ),
        'handoffs': ['Waste & Leakage Agent', 'Capital Allocation Agent'],
        'important': (
            'Good Agent Orchestrator selects and reasons about relevant principle lenses for human/'
            'Council review. It must never activate all 114 lenses for one signal, never issue more '
            'than one reasoning call per signal, and never move a decision past human approval itself.'
        ),
    },

    # --- Industrial Digital Twin & Modernisation Engine council personas ---
    # Finance ("Finance Modelling Agent"), Risk ("Governance Agent") and
    # Capital Guardian ("Capital Allocation Agent") roles are deliberately
    # NOT re-added here — the Digital Twin council reuses those three
    # existing personas directly rather than duplicating near-identical
    # roles (see docs/adr/ADR-digital-twin-foundation.md).
    {
        'number': 18, 'name': 'Digital Twin Agent', 'folder': 'digital_twin_agent',
        'role': 'States the twin\'s current baseline completeness/confidence/freshness and flags when a scenario rests on stale or incomplete data.',
        'handoffs': ['Engineering Agent', 'Evidence Agent'], 'important': '',
    },
    {
        'number': 19, 'name': 'Engineering Agent', 'folder': 'engineering_agent',
        'role': 'Reviews a modernisation scenario\'s technical specification and implementation phases for feasibility and technical risk.',
        'handoffs': ['Finance Modelling Agent', 'Risk Agent (Governance Agent)'], 'important': '',
    },
    {
        'number': 20, 'name': 'Energy and Resources Agent', 'folder': 'energy_resources_agent',
        'role': 'Reviews a scenario\'s energy, water, waste and emissions impact figures against the twin\'s recorded resource flows.',
        'handoffs': ['Stewardship Agent'], 'important': '',
    },
    {
        'number': 21, 'name': 'Worker Safety Agent', 'folder': 'worker_safety_agent',
        'role': 'Reviews a scenario\'s worker_impact narrative and operational_disruption level for safety risk.',
        'handoffs': ['Governance Agent'],
        'important': (
            'Worker Safety Agent flags risk for human and Council review. It must never '
            'clear a scenario past a detected harm signal itself.'
        ),
    },
    {
        'number': 22, 'name': 'Community Impact Agent', 'folder': 'community_impact_agent',
        'role': 'Reviews a scenario\'s community_impact narrative for displacement, vulnerability or local-harm signals.',
        'handoffs': ['Governance Agent', 'Stewardship Agent'],
        'important': (
            'Community Impact Agent flags risk for human and specialist review. It must never '
            'clear a scenario past a detected vulnerability signal itself.'
        ),
    },
    {
        'number': 23, 'name': 'Evidence Agent', 'folder': 'evidence_agent',
        'role': 'Reviews whether a scenario\'s stated confidence is actually backed by evidence references, independent of who produced the confidence figure.',
        'handoffs': ['Digital Twin Agent'], 'important': '',
    },
    {
        'number': 24, 'name': 'Stewardship Agent', 'folder': 'stewardship_agent',
        'role': 'Runs the draft, versioned Qur\'anic Stewardship KPI assessments for a scenario and reports the deterministic guardrail verdict — never generates or interprets religious content itself.',
        'handoffs': ['Governance Agent', 'Capital Allocation Agent'],
        'important': (
            'Stewardship Agent reports pre-computed, deterministic KPI scores and guardrail '
            'verdicts. It must never author, translate, or interpret a sacred-text source, and '
            'every KPI it reports remains in draft/requires-scholarly-review status until a real '
            'scholarly review changes that.'
        ),
    },

    # --- Global Research, Technology & Manufacturer Discovery Engine
    # council personas --- Stewardship role is deliberately NOT re-added
    # here — the Research Council reuses the existing "Stewardship Agent"
    # persona directly (see docs/adr/ADR-global-research-engine.md).
    {
        'number': 25, 'name': 'Problem Definition Agent', 'folder': 'problem_definition_agent',
        'role': 'Checks that a ResearchMission\'s problem statement is supplier-neutral and traces to a real, verified Digital Twin origin before research begins.',
        'handoffs': ['Technical Requirements Agent'], 'important': '',
    },
    {
        'number': 26, 'name': 'Technical Requirements Agent', 'folder': 'technical_requirements_agent',
        'role': 'Reviews a mission\'s TechnicalRequirement set for measurability, unit correctness, and supplier-neutral wording before research is approved to run.',
        'handoffs': ['Scientific Research Agent', 'Manufacturer Discovery Agent'], 'important': '',
    },
    {
        'number': 27, 'name': 'Scientific Research Agent', 'folder': 'scientific_research_agent',
        'role': 'Reviews authoritative-layer sources (standards, regulators, peer-reviewed research, independent laboratories) for a mission.',
        'handoffs': ['Independent Evidence Agent'], 'important': '',
    },
    {
        'number': 28, 'name': 'Patent and Innovation Agent', 'folder': 'patent_innovation_agent',
        'role': 'Reviews early-innovation-layer sources (patents, university projects, pilots) and ensures they are never scored as mature commercial availability.',
        'handoffs': ['Compatibility Agent'],
        'important': 'Must always state a candidate\'s technology readiness level explicitly and never let an early-stage candidate be presented as commercially mature.',
    },
    {
        'number': 29, 'name': 'Manufacturer Discovery Agent', 'folder': 'manufacturer_discovery_agent',
        'role': 'Reports which manufacturers were found for a technology category, across which countries, and with what evidence — never inferring a manufacturer\'s legal identity from a brand name alone.',
        'handoffs': ['Product Specification Agent', 'Commercial Intelligence Agent'], 'important': '',
    },
    {
        'number': 30, 'name': 'Product Specification Agent', 'folder': 'product_specification_agent',
        'role': 'Reviews a ProductCandidate\'s specifications against its source claims, distinguishing vendor-provided values from independently confirmed ones.',
        'handoffs': ['Independent Evidence Agent', 'Compatibility Agent'], 'important': '',
    },
    {
        'number': 31, 'name': 'Independent Evidence Agent', 'folder': 'independent_evidence_agent',
        'role': 'Checks whether a claim has independent corroboration and reports the real ClaimAssessment evidence score — never treats a vendor-only claim as sufficient for a shortlist recommendation.',
        'handoffs': ['Evidence Auditor'],
        'important': 'Must flag any recommendation resting only on vendor-provided, uncorroborated claims.',
    },
    {
        'number': 32, 'name': 'Compatibility Agent', 'folder': 'compatibility_agent',
        'role': 'Reports the deterministic CompatibilityAssessment result for a candidate — never overrides a failed mandatory requirement with a favourable overall impression.',
        'handoffs': ['Comparative evaluation'], 'important': '',
    },
    {
        'number': 33, 'name': 'Commercial Intelligence Agent', 'folder': 'commercial_intelligence_agent',
        'role': 'Reviews a ProductCandidate\'s commercial data (cost type, currency, date, assumptions) and flags when a cost figure is missing rather than estimated.',
        'handoffs': ['Supply Chain Risk Agent'], 'important': '',
    },
    {
        'number': 34, 'name': 'Supply Chain Risk Agent', 'folder': 'supply_chain_risk_agent',
        'role': 'Reviews SupplyChainRiskFlag rows (sanctions, export controls, single-country dependency, geopolitical disruption) for a candidate before it can be shortlisted.',
        'handoffs': ['Regulatory Agent', 'Stewardship Agent'],
        'important': 'human_approval_required=True whenever an unresolved high-severity risk flag exists for the candidate under review.',
    },
    {
        'number': 35, 'name': 'Regulatory Agent', 'folder': 'regulatory_agent',
        'role': 'Reviews certification and regulatory-compatibility evidence for a candidate against the mission\'s target jurisdiction.',
        'handoffs': ['Stewardship Agent', 'Evidence Auditor'], 'important': '',
    },
    {
        'number': 36, 'name': 'Evidence Auditor', 'folder': 'evidence_auditor_agent',
        'role': 'Independently re-checks that every claim underpinning a ResearchRecommendation has a real, resolvable evidence_id — refuses a recommendation containing an unreferenced factual statement.',
        'handoffs': ['Research Synthesis Agent'],
        'important': 'This is the last deterministic check before a recommendation reaches a human — it never authors new claims, only audits existing ones.',
    },
    {
        'number': 37, 'name': 'Research Synthesis Agent', 'folder': 'research_synthesis_agent',
        'role': 'Synthesises the Council\'s positions into one explainable readiness verdict (ready to shortlist / request more research / pilot required / incompatible / rejected) — never a final decision itself.',
        'handoffs': ['Human review'],
        'important': 'Produces a recommended next step for human review. It must never mark a mission as shortlisted or approved itself.',
    },
]

NEXT_STAGE_AGENTS = [
    {'number': 14, 'name': 'Supplier / Funding Match Agent'},
    {'number': 15, 'name': 'Customer Success Agent'},
    {'number': 16, 'name': 'Sales CRM Agent'},
    {'number': 17, 'name': 'Analytics Agent'},
]

OPERATIONAL_STATUS_LABEL = 'Operational Training Pack Ready'
NEXT_STAGE_STATUS_LABEL = 'Next Training Pack'

# Derived lookups used by services/ modules (routing, maturity) so agent
# names/folders are declared exactly once, here.
OPERATIONAL_AGENT_NAMES = [a['name'] for a in OPERATIONAL_AGENTS]
OPERATIONAL_AGENT_FOLDERS = {a['folder']: a['name'] for a in OPERATIONAL_AGENTS}
AGENT_NAME_TO_FOLDER = {a['name']: a['folder'] for a in OPERATIONAL_AGENTS}
NEXT_STAGE_AGENT_NAMES = [a['name'] for a in NEXT_STAGE_AGENTS]
