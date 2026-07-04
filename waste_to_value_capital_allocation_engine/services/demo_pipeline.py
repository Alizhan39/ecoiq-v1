"""
waste_to_value_capital_allocation_engine/services/demo_pipeline.py — the
Meat Cold-Chain Loss Prevention end-to-end demo.

Structurally mirrors agent_runtime_model_router/services/demo_pipeline.py's
Boiler House #3 demo: a DEDICATED CouncilRun (slug
'meat-cold-chain-loss-prevention-demo'), 9 agents run through the real
create_agent_run -> execute_agent -> submit_agent_position_to_council
pipeline (never hand-authored AgentTask rows), producing the exact
Finance/MRV/Governance disagreement and APPROVE WITH CONDITIONS decision
from the spec.

This app's own OperationalLoss/InterventionOption/FundingGap/
CapitalRouteMatch/CapitalAllocationDecision rows are created for the same
case, with CapitalAllocationDecision.council_case pointing at the new
CouncilRun. No VerifiedCapitalOutcome is created here — the Council's own
conditions require collecting after-data first, so an outcome genuinely
doesn't exist yet; creating one would silently turn a projected result into
a verified one.
"""
from ai_agent_council.models import (
    CouncilDecision, CouncilDisagreement, CouncilRun, CrossExaminationExchange,
    DecisionMemoryEntry,
)
from ai_agent_council.services.disagreement import classify_conflict
from agent_runtime_model_router.services.execution import (
    create_agent_run, execute_agent, submit_agent_position_to_council,
)
from waste_to_value_capital_allocation_engine.models import FundingGap, OperationalLoss
from waste_to_value_capital_allocation_engine.services.funding import (
    calculate_funding_gap, match_capital_routes,
)
from waste_to_value_capital_allocation_engine.services.governance import create_governed_investment_case
from waste_to_value_capital_allocation_engine.services.intervention_finance import model_interventions

DEMO_RUN_SLUG = 'meat-cold-chain-loss-prevention-demo'

# (agent_name, task_type, collaboration_mode, fixture_output, evidence_provenance, calibration_signals)
PIPELINE_STEPS = [
    (
        'Document Reader Agent', 'inventory_and_bill_extraction', 'parallel',
        {
            'confidence': 85, 'human_approval_required': False, 'status': 'completed',
            'risk_flags': [], 'evidence_used': [
                'inventory_value_report', 'temperature_log', 'electricity_bill', 'supplier_quote_coldchain',
            ],
            'missing_data': [],
            'output_summary': 'Extracted inventory value, temperature log readings, electricity bill and supplier quote for cold-chain equipment.',
        },
        [
            {'evidence_id': 'inventory_value_report', 'source_document': 'Inventory Value Report.xlsx', 'source_ref': 'sheet 1', 'quality': 'strong', 'missing_data_warning': False, 'visibility': 'private'},
            {'evidence_id': 'temperature_log', 'source_document': 'Refrigeration Temperature Log.csv', 'source_ref': 'Jan-Jun 2026', 'quality': 'strong', 'missing_data_warning': False, 'visibility': 'private'},
            {'evidence_id': 'electricity_bill', 'source_document': 'Electricity Bill.pdf', 'source_ref': 'p1', 'quality': 'medium', 'missing_data_warning': False, 'visibility': 'private'},
            {'evidence_id': 'supplier_quote_coldchain', 'source_document': 'Cold-Chain Supplier Quote.pdf', 'source_ref': 'p1-2', 'quality': 'medium', 'missing_data_warning': False, 'visibility': 'private'},
        ],
        {'evidence_quality_score': 85, 'unresolved_disagreements': 0, 'contradiction_severity': 'none', 'reviewer_status': 'pending'},
    ),
    (
        'Photo / Visual Evidence Agent', 'cold_chain_site_review', 'parallel',
        {
            'confidence': 65, 'human_approval_required': True, 'status': 'needs_review',
            'risk_flags': ['unverified_visual_hypothesis'], 'evidence_used': ['cold_room_inspection_photos'],
            'missing_data': [],
            'output_summary': 'Cold room storage conditions and refrigeration equipment show visible seal wear; findings remain a hypothesis pending technical confirmation.',
        },
        [
            {'evidence_id': 'cold_room_inspection_photos', 'source_document': 'Cold Room Inspection Photos.zip', 'source_ref': 'photos 1-8', 'quality': 'weak', 'missing_data_warning': False, 'visibility': 'private'},
        ],
        {'evidence_quality_score': 50, 'unresolved_disagreements': 0, 'contradiction_severity': 'none', 'reviewer_status': 'pending'},
    ),
    (
        'Asset Passport Agent', 'cold_store_asset_record_creation', 'handoff',
        {
            'confidence': 84, 'human_approval_required': False, 'status': 'completed',
            'risk_flags': [], 'evidence_used': ['inventory_value_report', 'temperature_log', 'cold_room_inspection_photos'],
            'missing_data': [],
            'output_summary': 'Structured cold-store asset profile and refrigeration equipment record created.',
        },
        [],
        {'evidence_quality_score': 84, 'unresolved_disagreements': 0, 'contradiction_severity': 'none', 'reviewer_status': 'pending'},
    ),
    (
        'Industrial Playbook Matching Agent', 'cold_chain_playbook_matching', 'handoff',
        {
            'confidence': 80, 'human_approval_required': False, 'status': 'completed',
            'risk_flags': ['transition_risk_medium'], 'evidence_used': ['inventory_value_report', 'supplier_quote_coldchain'],
            'missing_data': [],
            'output_summary': 'Matched to cold-chain optimisation, inventory optimisation and equipment-upgrade playbooks.',
        },
        [],
        {'evidence_quality_score': 80, 'unresolved_disagreements': 0, 'contradiction_severity': 'none', 'reviewer_status': 'pending'},
    ),
    (
        'Finance Modelling Agent', 'cold_chain_capex_opex_modelling', 'council',
        {
            'confidence': 82, 'human_approval_required': True, 'status': 'completed',
            'risk_flags': [], 'evidence_used': ['inventory_value_report', 'electricity_bill', 'supplier_quote_coldchain'],
            'missing_data': [],
            'output_summary': 'Cold-chain improvement may recover enough value to support an estimated 9-month payback.',
        },
        [],
        {'evidence_quality_score': 78, 'unresolved_disagreements': 2, 'contradiction_severity': 'medium', 'reviewer_status': 'pending'},
    ),
    (
        'MRV Agent', 'savings_verification_check', 'council',
        {
            'confidence': 74, 'human_approval_required': True, 'status': 'needs_review',
            'risk_flags': ['after_data_missing'], 'evidence_used': [],
            'missing_data': ['post_intervention_temperature_data', 'post_intervention_spoilage_data'],
            'output_summary': 'The financial savings remain estimated because post-intervention evidence does not yet exist.',
        },
        [],
        {'evidence_quality_score': 50, 'unresolved_disagreements': 1, 'contradiction_severity': 'low', 'reviewer_status': 'pending'},
    ),
    (
        'Governance Agent', 'food_safety_and_wording_review', 'council',
        {
            'confidence': 88, 'human_approval_required': True, 'status': 'needs_review',
            'risk_flags': ['food_safety_review_required', 'investor_wording_conditional'],
            'evidence_used': ['inventory_value_report', 'supplier_quote_coldchain'],
            'missing_data': [],
            'output_summary': 'Investor-facing wording must remain conditional, and food-safety implications require review.',
        },
        [],
        {'evidence_quality_score': 82, 'unresolved_disagreements': 1, 'contradiction_severity': 'low', 'reviewer_status': 'pending'},
    ),
    (
        'Report Generator Agent', 'investment_memo_generation', 'handoff',
        {
            'confidence': 79, 'human_approval_required': True, 'status': 'completed',
            'risk_flags': [], 'evidence_used': ['inventory_value_report', 'electricity_bill', 'supplier_quote_coldchain'],
            'missing_data': [],
            'output_summary': 'Builds the investment memo, finance summary, conditions and evidence links; investor wording remains conditional.',
        },
        [],
        {'evidence_quality_score': 78, 'unresolved_disagreements': 0, 'contradiction_severity': 'none', 'reviewer_status': 'human_reviewed'},
    ),
    (
        'Amanah Autopilot Supervisor', 'overnight_loss_risk_supervision', 'solo',
        {
            'confidence': 70, 'human_approval_required': False, 'status': 'completed',
            'risk_flags': [], 'evidence_used': ['temperature_log'], 'missing_data': [],
            'output_summary': 'Overnight check confirms no new high-risk inventory alerts; this case is queued in the finance review queue.',
        },
        [],
        {'evidence_quality_score': 70, 'unresolved_disagreements': 0, 'contradiction_severity': 'none', 'reviewer_status': 'pending'},
    ),
]

# The 7 candidate interventions from the spec's "PREVENT -> ... -> DISPOSE"
# hierarchy. Option E (equipment upgrade) is the one the Council actually
# deliberates over — its payback matches Finance Modelling Agent's own
# "estimated 9-month payback" quote exactly (capex=9000, annual_savings=12000
# -> 9000/(12000/12) = 9.0).
INTERVENTION_CANDIDATES = [
    {'title': 'Dynamic discount now', 'intervention_type': 'prevention',
     'capex_estimate': 200, 'estimated_value_recovered': 3000, 'estimated_loss_avoided': 3000,
     'risk_level': 'low', 'technical_readiness': 'ready'},
    {'title': 'Transfer to another branch (dynamic, discounted resale)', 'intervention_type': 'transfer_redistribution',
     'capex_estimate': 1200, 'estimated_value_recovered': 8500, 'estimated_loss_avoided': 8500,
     'risk_level': 'low', 'technical_readiness': 'ready'},
    {'title': 'Sell to processor', 'intervention_type': 'resale',
     'capex_estimate': 500, 'estimated_value_recovered': 6000, 'estimated_loss_avoided': 6000,
     'risk_level': 'low', 'technical_readiness': 'ready'},
    {'title': 'Safe donation where appropriate', 'intervention_type': 'transfer_redistribution',
     'capex_estimate': 300, 'estimated_value_recovered': 1500, 'estimated_loss_avoided': 1500,
     'risk_level': 'medium', 'technical_readiness': 'needs_review'},
    {'title': 'Freeze / reprocess', 'intervention_type': 'processing_recovery',
     'capex_estimate': 800, 'estimated_value_recovered': 4500, 'estimated_loss_avoided': 4500,
     'risk_level': 'low', 'technical_readiness': 'ready'},
    {'title': 'Cold-chain equipment intervention', 'intervention_type': 'equipment_upgrade',
     'capex_estimate': 9000, 'estimated_annual_savings': 12000, 'estimated_loss_avoided': 12000,
     'risk_level': 'medium', 'technical_readiness': 'ready', 'finance_readiness': 'needs_review',
     'mrv_readiness': 'draft', 'status': 'recommended'},
    {'title': 'Anaerobic digestion as last resort', 'intervention_type': 'disposal',
     'capex_estimate': 200, 'estimated_value_recovered': 300, 'estimated_loss_avoided': 300,
     'risk_level': 'low', 'technical_readiness': 'ready'},
]

DECISION_CONDITIONS = [
    'Confirm supplier quote exclusions.',
    'Collect post-intervention temperature and spoilage data.',
    'Keep savings labelled estimated.',
    'Require food-safety review.',
    'Require approval before external funder outreach.',
    'Block public verified-impact claims until MRV completion.',
]


def build_meat_cold_chain_demo():
    council_run, _ = CouncilRun.objects.get_or_create(slug=DEMO_RUN_SLUG, defaults={'title': ''})
    council_run.title = 'Meat Cold-Chain Loss Prevention'
    council_run.question = (
        'Should EcoIQ recommend proceeding with the cold-chain equipment intervention for this meat '
        'inventory, and under what conditions? (Built end-to-end through the real Agent Runtime & '
        'Model Router pipeline.)'
    )
    council_run.task_category = 'waste_to_value_capital_allocation'
    council_run.is_simulated = True
    council_run.status = 'decided'
    council_run.save()

    tasks_by_agent = {}
    for order, (agent_name, task_type, collaboration_mode, fixture, evidence_provenance, signals) in enumerate(
        PIPELINE_STEPS, start=1,
    ):
        agent_run = create_agent_run(
            agent_name, task_type, council_case=council_run, execution_mode='simulated_demo',
            input_summary=f'Meat Cold-Chain Loss Prevention — {task_type}', evidence_provenance=evidence_provenance,
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
        disagreement_1.evidence_used = ['inventory_value_report', 'supplier_quote_coldchain']
        disagreement_1.final_decision_summary = (
            "Governance's food-safety and investor-wording concerns are preserved as formal conditions."
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
        disagreement_2.evidence_used = ['inventory_value_report']
        disagreement_2.final_decision_summary = (
            "MRV's missing post-intervention evidence finding is escalated rather than overridden by Finance's confidence."
        )
        disagreement_2.minority_opinion_retained = True
        disagreement_2.save()

    if finance_task and governance_task:
        exchange, _ = CrossExaminationExchange.objects.get_or_create(run=council_run, sequence=1, defaults={})
        exchange.questioner_agent = 'Governance Agent'
        exchange.target_agent = 'Finance Modelling Agent'
        exchange.challenge_type = 'food_safety_and_wording_disclosure'
        exchange.reason = 'The finance-ready claim does not address food-safety implications or investor wording risk.'
        exchange.requested_evidence = ['food_safety_review_log']
        exchange.response_answer = (
            'Confirms food-safety review was out of scope for the finance model; recommends Governance track it separately.'
        )
        exchange.response_confidence = finance_task.confidence
        exchange.unresolved_uncertainty = 'Whether food-safety review affects the final funding decision remains open.'
        exchange.save()

    decision, _ = CouncilDecision.objects.get_or_create(run=council_run, defaults={})
    decision.status = 'approved_with_conditions'
    decision.summary = 'Proceed with the meat cold-chain loss prevention intervention, subject to conditions.'
    decision.majority_agents = [
        name for name in tasks_by_agent if name != 'Governance Agent' and tasks_by_agent[name]
    ]
    decision.minority_agents = ['Governance Agent']
    decision.minority_reason = (
        'Governance Agent maintains investor-facing wording must remain conditional and food-safety '
        'implications require review before proceeding unconditionally.'
    )
    decision.conditions = DECISION_CONDITIONS
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
        'Has the food-safety review been completed?',
        'Has post-intervention temperature and spoilage data been collected?',
    ]
    memory_entry.unresolved_risks = ['Post-intervention evidence incomplete — savings remain estimated, not verified.']
    memory_entry.review_trigger = (
        'Reopen once post-intervention temperature/spoilage data is collected and the food-safety review is complete.'
    )
    memory_entry.reopened = False
    memory_entry.save()

    # This app's own domain models for the same case.
    loss, _ = OperationalLoss.objects.get_or_create(
        title='Meat Cold-Chain Spoilage Risk',
        defaults={'loss_type': 'meat_spoilage', 'financial_loss_amount': 0},
    )
    loss.loss_type = 'meat_spoilage'
    loss.asset = 'Cold Store Unit 3'
    loss.project = 'Meat Cold-Chain Loss Prevention'
    loss.description = 'Perishable meat inventory at risk of spoilage within a 36-hour intervention window.'
    loss.quantity_lost = None
    loss.unit = ''
    loss.financial_loss_amount = 0  # nothing has actually been lost yet — this is a projected risk, not an incurred loss.
    loss.projected_future_loss = 12000
    loss.currency = 'GBP'
    loss.period = 'Current inventory cycle'
    loss.evidence_quality = 'medium'
    loss.confidence = 60
    loss.avoidability_score = 70
    loss.urgency_score = 90
    loss.time_horizon = '36 hours'
    loss.intervention_readiness = 'ready'
    loss.finance_readiness = 'needs_review'
    loss.mrv_readiness = 'draft'
    loss.status = 'modelled'
    loss.save()

    options = model_interventions(loss, INTERVENTION_CANDIDATES)
    equipment_option = next(o for o in options if o.title == 'Cold-chain equipment intervention')

    funding_gap_figures = calculate_funding_gap(
        total_capital_required=equipment_option.capex_estimate,
        owner_contribution=3000, supplier_finance_potential=6000,
    )
    funding_gap, _ = FundingGap.objects.get_or_create(intervention=equipment_option, defaults={})
    for field, value in funding_gap_figures.items():
        setattr(funding_gap, field, value)
    funding_gap.currency = 'GBP'
    funding_gap.status = 'under_review'
    funding_gap.save()
    match_capital_routes(funding_gap)

    decision_record = create_governed_investment_case(
        equipment_option, council_case=council_run,
        decision_text='APPROVE WITH CONDITIONS',
        scores={
            'financial_return_score': 78, 'loss_avoidance_score': 82, 'capital_efficiency_score': 80,
            'risk_score': 55, 'verified_impact_score': 20, 'maqasid_mizan_score': 65,
        },
        conditions=DECISION_CONDITIONS,
        confidence=finance_task.confidence if finance_task else None,
        human_approval_required=True, approval_status='approved_with_conditions',
    )
    decision_record.ranking = 1
    decision_record.save()

    return council_run
