"""
agent_runtime_model_router/services/demo_pipeline.py — the Boiler House #3
end-to-end runtime demo (hardening requirement 8 / spec section 17).

Builds a DEDICATED CouncilRun (slug 'boiler-house-3-modernisation-runtime-demo'),
distinct from ai_agent_council's own seeded 'boiler-house-3-modernisation' run
(which has 45 tests asserting exact fixture content) — this demo proves the
full real pipeline (create_agent_run -> execute_agent ->
submit_agent_position_to_council) actually produces Council-ready positions,
rather than writing AgentTask rows by hand.

Idempotent: create_agent_run()'s own idempotency key means re-running this
twice returns the same AgentRun rows; AgentTask/CouncilDisagreement/
CouncilDecision/DecisionMemoryEntry creation is additionally guarded so a
second run never submits duplicate Council positions.
"""
from django.utils import timezone

from ai_agent_council.models import (
    CouncilDecision, CouncilDisagreement, CouncilRun, CrossExaminationExchange,
    DecisionMemoryEntry,
)
from ai_agent_council.services.disagreement import classify_conflict
from agent_runtime_model_router.services.execution import create_agent_run, execute_agent, submit_agent_position_to_council

DEMO_RUN_SLUG = 'boiler-house-3-modernisation-runtime-demo'

# (agent_name, task_type, collaboration_mode, fixture_output, evidence_provenance,
#  calibration_signals)
PIPELINE_STEPS = [
    (
        'Document Reader Agent', 'bill_extraction', 'parallel',
        {
            'confidence': 88, 'human_approval_required': False, 'status': 'completed',
            'risk_flags': [], 'evidence_used': ['fuel_bills_2024', 'supplier_quote_boiler3'],
            'missing_data': [],
            'output_summary': 'Extracted fuel bill totals and supplier CAPEX quote.',
        },
        [
            {'evidence_id': 'fuel_bills_2024', 'source_document': 'Fuel Bills 2024.pdf', 'source_ref': 'p1-12', 'quality': 'strong', 'missing_data_warning': False, 'visibility': 'private'},
            {'evidence_id': 'supplier_quote_boiler3', 'source_document': 'Supplier Quote Boiler3.pdf', 'source_ref': 'p1', 'quality': 'medium', 'missing_data_warning': False, 'visibility': 'private'},
        ],
        {'evidence_quality_score': 88, 'unresolved_disagreements': 0, 'contradiction_severity': 'none', 'reviewer_status': 'pending'},
    ),
    (
        'Photo / Visual Evidence Agent', 'site_photo_review', 'parallel',
        {
            'confidence': 70, 'human_approval_required': True, 'status': 'needs_review',
            'risk_flags': ['unverified_visual_hypothesis'], 'evidence_used': ['inspection_photos_boiler3'],
            'missing_data': [],
            'output_summary': 'Visible insulation gaps and soot appear present; findings remain a hypothesis pending technical confirmation.',
        },
        [
            {'evidence_id': 'inspection_photos_boiler3', 'source_document': 'Site Inspection Photos.zip', 'source_ref': 'photos 1-6', 'quality': 'weak', 'missing_data_warning': False, 'visibility': 'private'},
        ],
        {'evidence_quality_score': 55, 'unresolved_disagreements': 0, 'contradiction_severity': 'none', 'reviewer_status': 'pending'},
    ),
    (
        'Asset Passport Agent', 'asset_record_creation', 'handoff',
        {
            'confidence': 85, 'human_approval_required': False, 'status': 'completed',
            'risk_flags': [], 'evidence_used': ['fuel_bills_2024', 'supplier_quote_boiler3', 'inspection_photos_boiler3'],
            'missing_data': [],
            'output_summary': 'Structured asset record created for Boiler House #3.',
        },
        [],
        {'evidence_quality_score': 85, 'unresolved_disagreements': 0, 'contradiction_severity': 'none', 'reviewer_status': 'pending'},
    ),
    (
        'Industrial Playbook Matching Agent', 'modernisation_pathway_matching', 'handoff',
        {
            'confidence': 83, 'human_approval_required': False, 'status': 'completed',
            'risk_flags': ['transition_risk_medium'], 'evidence_used': ['fuel_bills_2024', 'supplier_quote_boiler3'],
            'missing_data': [],
            'output_summary': 'Matched to the Boiler Modernisation Playbook.',
        },
        [],
        {'evidence_quality_score': 83, 'unresolved_disagreements': 0, 'contradiction_severity': 'none', 'reviewer_status': 'pending'},
    ),
    (
        'Finance Modelling Agent', 'capex_opex_modelling', 'council',
        {
            'confidence': 82, 'human_approval_required': True, 'status': 'completed',
            'risk_flags': [], 'evidence_used': ['fuel_bills_2024', 'supplier_quote_boiler3'],
            'missing_data': [],
            'output_summary': 'Project may be finance-ready based on CAPEX and estimated savings.',
        },
        [],
        {'evidence_quality_score': 80, 'unresolved_disagreements': 2, 'contradiction_severity': 'medium', 'reviewer_status': 'pending'},
    ),
    (
        'MRV Agent', 'baseline_check', 'council',
        {
            'confidence': 76, 'human_approval_required': True, 'status': 'needs_review',
            'risk_flags': ['baseline_incomplete'], 'evidence_used': [],
            'missing_data': ['baseline_survey_boiler3'],
            'output_summary': 'Impact savings remain estimated because after-data is missing.',
        },
        [],
        {'evidence_quality_score': 55, 'unresolved_disagreements': 1, 'contradiction_severity': 'low', 'reviewer_status': 'pending'},
    ),
    (
        'Governance Agent', 'review_routing', 'council',
        {
            'confidence': 89, 'human_approval_required': True, 'status': 'needs_review',
            'risk_flags': ['procurement_transparency_gap'], 'evidence_used': ['fuel_bills_2024', 'supplier_quote_boiler3'],
            'missing_data': [],
            'output_summary': 'Investor wording must remain conditional.',
        },
        [],
        {'evidence_quality_score': 85, 'unresolved_disagreements': 1, 'contradiction_severity': 'low', 'reviewer_status': 'pending'},
    ),
    (
        'Report Generator Agent', 'investor_memo', 'handoff',
        {
            'confidence': 80, 'human_approval_required': True, 'status': 'completed',
            'risk_flags': [], 'evidence_used': ['fuel_bills_2024', 'supplier_quote_boiler3'],
            'missing_data': [],
            'output_summary': 'Builds the evidence-linked decision memo; conditions and human approval requirement preserved.',
        },
        [],
        {'evidence_quality_score': 80, 'unresolved_disagreements': 0, 'contradiction_severity': 'none', 'reviewer_status': 'human_reviewed'},
    ),
]


def build_boiler_house_runtime_demo():
    council_run, _ = CouncilRun.objects.get_or_create(slug=DEMO_RUN_SLUG, defaults={'title': ''})
    council_run.title = 'Boiler House #3 Modernisation — Runtime Demo'
    council_run.question = (
        'Should EcoIQ recommend proceeding with Boiler House #3 modernisation, and under what '
        'conditions? (Built end-to-end through the real Agent Runtime & Model Router pipeline.)'
    )
    council_run.task_category = 'industrial_asset_modernisation'
    council_run.is_simulated = True
    council_run.status = 'decided'
    council_run.save()

    tasks_by_agent = {}
    for order, (agent_name, task_type, collaboration_mode, fixture, evidence_provenance, signals) in enumerate(
        PIPELINE_STEPS, start=1,
    ):
        agent_run = create_agent_run(
            agent_name, task_type, council_case=council_run, execution_mode='simulated_demo',
            input_summary=f'Boiler House #3 — {task_type}', evidence_provenance=evidence_provenance,
        )
        if agent_run.status != 'completed':
            agent_run = execute_agent(agent_run, fixture_output=fixture, **signals)

        if agent_run.status == 'completed' and agent_run.schema_valid and not agent_run.council_position_id:
            submit_agent_position_to_council(agent_run, collaboration_mode=collaboration_mode, order=order)
            agent_run.refresh_from_db()

        tasks_by_agent[agent_name] = agent_run.council_position

    finance_task = tasks_by_agent.get('Finance Modelling Agent')
    mrv_task = tasks_by_agent.get('MRV Agent')
    governance_task = tasks_by_agent.get('Governance Agent')

    if finance_task and governance_task:
        conflict_type, resolution_method = classify_conflict(finance_task, governance_task)
        disagreement_1, _ = CouncilDisagreement.objects.get_or_create(
            run=council_run, position_a=finance_task, position_b=governance_task, defaults={},
        )
        disagreement_1.conflict_type = conflict_type
        disagreement_1.resolution_method = resolution_method
        disagreement_1.evidence_used = ['fuel_bills_2024', 'supplier_quote_boiler3']
        disagreement_1.final_decision_summary = (
            "Governance's procurement-transparency concern is preserved as a formal condition."
        )
        disagreement_1.minority_opinion_retained = True
        disagreement_1.save()

    if finance_task and mrv_task:
        conflict_type, resolution_method = classify_conflict(finance_task, mrv_task)
        disagreement_2, _ = CouncilDisagreement.objects.get_or_create(
            run=council_run, position_a=finance_task, position_b=mrv_task, defaults={},
        )
        disagreement_2.conflict_type = conflict_type
        disagreement_2.resolution_method = resolution_method
        disagreement_2.evidence_used = ['fuel_bills_2024', 'supplier_quote_boiler3']
        disagreement_2.final_decision_summary = (
            "MRV's missing-baseline finding is escalated rather than overridden by Finance's confidence."
        )
        disagreement_2.minority_opinion_retained = True
        disagreement_2.save()

    if finance_task and governance_task:
        exchange, _ = CrossExaminationExchange.objects.get_or_create(run=council_run, sequence=1, defaults={})
        exchange.questioner_agent = 'Governance Agent'
        exchange.target_agent = 'Finance Modelling Agent'
        exchange.challenge_type = 'risk_disclosure'
        exchange.reason = 'The financially-attractive claim does not address the procurement transparency risk.'
        exchange.requested_evidence = ['procurement_process_log']
        exchange.response_answer = (
            'Confirms procurement review was out of scope for the finance model; recommends Governance track it separately.'
        )
        exchange.response_confidence = finance_task.confidence
        exchange.unresolved_uncertainty = 'Whether the procurement transparency gap affects funding eligibility remains open.'
        exchange.save()

    decision, _ = CouncilDecision.objects.get_or_create(run=council_run, defaults={})
    decision.status = 'approved_with_conditions'
    decision.summary = 'Proceed with Boiler House #3 modernisation, subject to conditions.'
    decision.majority_agents = [
        name for name in tasks_by_agent if name != 'Governance Agent' and tasks_by_agent[name]
    ]
    decision.minority_agents = ['Governance Agent']
    decision.minority_reason = (
        'Governance Agent maintains investor wording must remain conditional until procurement '
        'transparency and baseline evidence are resolved.'
    )
    decision.conditions = [
        'Collect after-data.',
        'Technical reviewer confirms assumptions.',
        'Investor wording remains conditional.',
        'Public impact claim remains blocked.',
    ]
    decision.confidence = finance_task.confidence if finance_task else None
    decision.confidence_breakdown = finance_task.confidence_breakdown if finance_task else {}
    decision.human_approval_required = True
    decision.human_approved = True
    decision.save()

    memory_entry, _ = DecisionMemoryEntry.objects.get_or_create(decision=decision, defaults={})
    memory_entry.original_decision_summary = decision.summary
    memory_entry.reason = (
        'The finance case is attractive, but Governance and MRV concerns were preserved as formal '
        'conditions rather than resolved away.'
    )
    memory_entry.open_questions = [
        'Has procurement transparency been resolved?', 'Has the baseline survey been completed?',
    ]
    memory_entry.unresolved_risks = ['Baseline survey incomplete — verified impact cannot yet be claimed.']
    memory_entry.review_trigger = (
        'Reopen if procurement transparency documentation is submitted or the baseline survey completes.'
    )
    memory_entry.reopened = False
    memory_entry.save()

    return council_run
