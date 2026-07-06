"""
financial_intelligence_cloud/services/demo_flagship_pipeline.py — the
FreshBridge Foods flagship Client Opportunity Radar case. Mirrors
waste_to_value_capital_allocation_engine/services/demo_pipeline.py's
build_meat_cold_chain_demo() structure: a DEDICATED CouncilRun, 5 agents run
through the real create_agent_run -> execute_agent ->
submit_agent_position_to_council pipeline (never hand-authored AgentTask
rows), producing the exact £240,000 capital-at-risk / £155,000 recoverable-
value golden-case conclusion required by the accounting-firm spec.

This is the ONE entity per Northstar Advisory that runs through the real
Council pipeline — the other 49 clients are deterministically generated
(see services/entity_generation.py) and never claim a real AgentRun.
"""
from ai_agent_council.models import CouncilRun
from agent_runtime_model_router.services.execution import (
    create_agent_run, execute_agent, submit_agent_position_to_council,
)
from financial_intelligence_cloud.services.accounts import add_portfolio_entity
from financial_intelligence_cloud.services.agent_bridge import (
    build_finance_modelling_fixture, build_waste_leakage_fixture,
)
from financial_intelligence_cloud.services.portfolio_ranking import rank_clients_to_call_today
from financial_intelligence_cloud.services.signals import detect_advisory_opportunity, generate_portfolio_signal
from waste_to_value_capital_allocation_engine.models import OperationalLoss

DEMO_RUN_SLUG = 'freshbridge-foods-advisory-demo'

# (agent_name, task_type, collaboration_mode, fixture_output, evidence_provenance, calibration_signals)
PIPELINE_STEPS = [
    (
        'Document Reader Agent', 'management_accounts_extraction', 'parallel',
        {
            'confidence': 85, 'human_approval_required': False, 'status': 'completed',
            'risk_flags': [],
            'evidence_used': ['management_accounts', 'inventory_report', 'energy_bill', 'maintenance_record', 'sales_trend'],
            'missing_data': [],
            'output_summary': 'Extracted management accounts, inventory report, energy bill, maintenance record and sales trend for FreshBridge Foods.',
        },
        [],
        {'evidence_quality_score': 85, 'unresolved_disagreements': 0, 'contradiction_severity': 'none', 'reviewer_status': 'pending'},
    ),
    (
        'Waste & Leakage Agent', 'operational_loss_detection', 'solo',
        build_waste_leakage_fixture(
            inventory_value=1_600_000, historical_loss_rate=0.15,
            evidence_used=['inventory_report', 'energy_bill', 'maintenance_record'],
            missing_data=['independent_technical_inspection_report'],
            classification='forecast', confidence=60,
            risk_flags=['inventory_ageing_detected', 'energy_cost_increase_detected'],
            next_action='Route to Finance Modelling Agent for recoverable-value modelling.',
            human_approval_required=False, status='completed',
        ),
        [],
        {'evidence_quality_score': 55, 'unresolved_disagreements': 0, 'contradiction_severity': 'none', 'reviewer_status': 'pending'},
    ),
    (
        'Finance Modelling Agent', 'operational_value_recovery_modelling', 'council',
        build_finance_modelling_fixture(
            expected_value_recovered=175_000, intervention_cost=20_000,
            evidence_used=['inventory_report', 'energy_bill', 'sales_trend'],
            missing_data=[], confidence=78,
            next_action='Route to MRV Agent and Governance Agent for evidence and wording review.',
        ),
        [],
        {'evidence_quality_score': 75, 'unresolved_disagreements': 1, 'contradiction_severity': 'low', 'reviewer_status': 'pending'},
    ),
    (
        'MRV Agent', 'savings_verification_check', 'council',
        {
            'confidence': 65, 'human_approval_required': True, 'status': 'needs_review',
            'risk_flags': ['after_data_missing'], 'evidence_used': [],
            'missing_data': ['post_intervention_margin_data'],
            'output_summary': 'The recoverable value remains estimated because post-intervention evidence does not yet exist.',
        },
        [],
        {'evidence_quality_score': 50, 'unresolved_disagreements': 1, 'contradiction_severity': 'low', 'reviewer_status': 'pending'},
    ),
    (
        'Governance Agent', 'advisory_wording_review', 'council',
        {
            'confidence': 88, 'human_approval_required': True, 'status': 'needs_review',
            'risk_flags': ['advisory_wording_conditional'], 'evidence_used': ['inventory_report'],
            'missing_data': [],
            'output_summary': 'Advisory-facing wording must remain conditional pending post-intervention evidence.',
        },
        [],
        {'evidence_quality_score': 82, 'unresolved_disagreements': 0, 'contradiction_severity': 'none', 'reviewer_status': 'pending'},
    ),
]


def build_freshbridge_foods_demo(portfolio):
    council_run, _ = CouncilRun.objects.get_or_create(slug=DEMO_RUN_SLUG, defaults={'title': ''})
    council_run.title = 'FreshBridge Foods Advisory Opportunity'
    council_run.question = (
        'Should Northstar Advisory call FreshBridge Foods today, and what advisory service should it recommend? '
        '(Built end-to-end through the real Agent Runtime & Model Router pipeline.)'
    )
    council_run.task_category = 'financial_intelligence_cloud_advisory'
    council_run.is_simulated = True
    council_run.status = 'decided'
    council_run.save()

    tasks_by_agent = {}
    for order, (agent_name, task_type, collaboration_mode, fixture, evidence_provenance, signals) in enumerate(
        PIPELINE_STEPS, start=1,
    ):
        agent_run = create_agent_run(
            agent_name, task_type, council_case=council_run, execution_mode='simulated_demo',
            input_summary=f'FreshBridge Foods Advisory Opportunity — {task_type}', evidence_provenance=evidence_provenance,
        )
        if agent_run.status != 'completed':
            agent_run = execute_agent(agent_run, fixture_output=fixture, **signals)

        if agent_run.status == 'completed' and agent_run.schema_valid and not agent_run.council_position_id:
            submit_agent_position_to_council(agent_run, collaboration_mode=collaboration_mode, order=order)
            agent_run.refresh_from_db()

        tasks_by_agent[agent_name] = agent_run

    finance_run = tasks_by_agent.get('Finance Modelling Agent')

    loss, _ = OperationalLoss.objects.get_or_create(
        title='FreshBridge Foods Operational Loss',
        defaults={'loss_type': 'excess_inventory', 'financial_loss_amount': 0},
    )
    loss.loss_type = 'excess_inventory'
    loss.organisation = 'FreshBridge Foods'
    loss.financial_loss_amount = 0
    loss.projected_future_loss = 240000
    loss.currency = 'GBP'
    loss.evidence_quality = 'medium'
    loss.confidence = 60
    loss.status = 'modelled'
    loss.save()

    entity = add_portfolio_entity(
        portfolio, 'FreshBridge Foods', 'sme_client', sector='Food & Beverage', is_flagship=True,
        source_operational_loss=loss, relationship_stage='active',
    )

    signal = generate_portfolio_signal(
        entity, 'client_advisory_opportunity',
        'FreshBridge Foods: potential operational loss and working-capital opportunity',
        description=(
            'Inventory ageing, energy cost increase, margin deterioration and potential cold-chain '
            'exposure detected.'
        ),
        capital_at_risk=240000, potential_recoverable_value=155000, currency='GBP',
        urgency_score=90, evidence_quality='medium', confidence=60, human_approval_required=True,
        source_run=finance_run,
    )

    ranked = rank_clients_to_call_today([{
        'name': 'FreshBridge Foods', 'urgency': 90, 'capital_at_risk_normalised': 100,
        'recoverable_value_normalised': 100, 'evidence_quality': 60, 'relationship_importance': 80,
        'data_freshness': 100,
    }])
    priority_score = ranked[0]['composite_score']

    detect_advisory_opportunity(
        entity, 'cost_recovery_advisory', 'Call this client today',
        linked_signal=signal,
        rationale=(
            'Potential operational loss and working-capital opportunity. Projected capital at risk: '
            '£240,000/year. Potential recoverable value: £155,000/year. Evidence quality: Medium. '
            'Recommended advisory service: Operational Value Recovery Review.'
        ),
        estimated_capital_at_risk=240000, estimated_recoverable_value=155000, currency='GBP',
        priority_score=priority_score, requires_human_review=True, status='identified',
    )

    return council_run
