"""
khalifa_stewardship_tour_operating_system/services/demo_flagship_pipeline.py
— the Kazakhstan Clean Heat Stewardship Tour flagship case. Mirrors
waste_to_value_capital_allocation_engine/services/demo_pipeline.py's
build_meat_cold_chain_demo() structure: a DEDICATED CouncilRun, agents run
through the real create_agent_run -> execute_agent ->
submit_agent_position_to_council pipeline (never hand-authored AgentTask
rows) — but this is the first demo this session to exercise the FULL
12-agent roster in one run, in the exact order the spec's own tour-planning
workflow describes (Research -> Document Reader -> Photo/Visual Evidence ->
Waste & Leakage -> Asset Passport -> Industrial Playbook Matching -> Finance
Modelling -> Capital Allocation -> MRV -> Governance -> Report Generator ->
Amanah Autopilot).

Unlike the WTV/Financial Intelligence Cloud precedents, PIPELINE_STEPS is
built LOCALLY inside build_kazakhstan_clean_heat_demo() rather than as a
module-level constant — this lets the Capital Allocation Agent's step (order
8, not last) reference the real, already-persisted StewardshipIntervention
rows created earlier in the same function call, without needing the
"static list + dynamic step appended after the loop" workaround those
earlier apps needed.
"""
from ai_agent_council.models import (
    CouncilDecision, CouncilDisagreement, CouncilRun, CrossExaminationExchange,
    DecisionMemoryEntry,
)
from ai_agent_council.services.disagreement import classify_conflict
from agent_runtime_model_router.services.execution import (
    create_agent_run, execute_agent, submit_agent_position_to_council,
)
from khalifa_stewardship_tour_operating_system.services.agent_bridge import (
    build_finance_modelling_fixture, build_waste_leakage_fixture,
)
from khalifa_stewardship_tour_operating_system.services.capital_allocation_link import (
    rank_stewardship_interventions,
)
from khalifa_stewardship_tour_operating_system.services.tours import (
    add_local_partner, add_participant_role, create_funding_plan, create_mrv_plan,
    create_stewardship_intervention, create_stewardship_problem, create_stewardship_tour,
)

DEMO_RUN_SLUG = 'kazakhstan-clean-heat-stewardship-demo'
TOUR_SLUG = 'kazakhstan-clean-heat'

DECISION_CONDITIONS = [
    'Local technical inspection required.',
    'Household consent required.',
    'Supplier quote exclusions checked.',
    'Safety review required.',
    'MRV baseline collected.',
    'Public impact claim blocked until after-data verified.',
]

CAPITAL_AT_RISK_CEILING = 420
INVENTORY_VALUE_CEILING = 1200


def build_kazakhstan_clean_heat_demo():
    country = None
    try:
        from countries.models import CountryProfile
        country = CountryProfile.objects.filter(slug='kazakhstan').first()
    except Exception:
        country = None

    tour = create_stewardship_tour(
        TOUR_SLUG, 'Kazakhstan Clean Heat Stewardship Tour', 'clean_heat',
        country=country, region='Almaty Region / demo village',
        description=(
            'A household uses inefficient coal heating and loses heat through poor insulation. '
            'Built end-to-end through the real Agent Runtime & Model Router pipeline.'
        ),
        status='approved_with_conditions', participant_capacity=12,
        estimated_price_per_participant=350, total_budget_required=3200,
        safety_level='medium', local_partner_required=True, human_approval_required=True,
    )

    problem = create_stewardship_problem(
        tour, 'inefficient_heating', 'Household uses inefficient coal heating and loses heat through poor insulation',
        description='Cold-weather risk, high energy cost burden, household air quality risk from coal heating.',
        location='Almaty Region demo village', evidence_quality='medium',
        urgency_score=80, harm_score=65, confidence=60, status='under_review',
    )

    create_stewardship_intervention(
        problem, 'Clean heating + insulation package', 'clean_heating_upgrade',
        description='Full clean-heating unit plus insulation upgrade.',
        capex_estimate=1400, opex_estimate=0, estimated_benefit=700,
        implementation_complexity='medium', participant_role='Observe and assist with safe preparation.',
        professional_role='Technical installation and safety inspection.',
        local_partner_role='Household liaison and consent coordination.',
        status='recommended',
    )
    create_stewardship_intervention(
        problem, 'Insulation only', 'insulation_support',
        description='Insulation upgrade without heating system replacement.',
        capex_estimate=600, opex_estimate=0, estimated_benefit=250,
        implementation_complexity='low', status='modelled',
    )
    create_stewardship_intervention(
        problem, 'Smart controls only', 'smart_controls',
        description='Smart heating controls only, no structural change.',
        capex_estimate=250, opex_estimate=0, estimated_benefit=80,
        implementation_complexity='low', status='modelled',
    )

    council_run, _ = CouncilRun.objects.get_or_create(slug=DEMO_RUN_SLUG, defaults={'title': ''})
    council_run.title = 'Kazakhstan Clean Heat Stewardship Tour'
    council_run.question = (
        'Should EcoIQ approve the Kazakhstan Clean Heat Stewardship Tour, and under what conditions? '
        '(Built end-to-end through the real Agent Runtime & Model Router pipeline, exercising the full '
        '12-agent roster.)'
    )
    council_run.task_category = 'khalifa_stewardship_tour'
    council_run.is_simulated = True
    council_run.status = 'decided'
    council_run.save()

    ranked_interventions = rank_stewardship_interventions(problem, CAPITAL_AT_RISK_CEILING, INVENTORY_VALUE_CEILING)
    top_intervention = ranked_interventions[0]

    pipeline_steps = [
        (
            'Research Agent', 'kazakhstan_regional_context_research', 'solo',
            {
                'confidence': 82, 'human_approval_required': False, 'status': 'completed',
                'risk_flags': [], 'evidence_used': ['regional_energy_report', 'climate_data'],
                'missing_data': [],
                'output_summary': 'Almaty Region context gathered: cold-weather climate, common coal-heating reliance, regional clean-heat programmes.',
            },
            [], {'evidence_quality_score': 80, 'unresolved_disagreements': 0, 'contradiction_severity': 'none', 'reviewer_status': 'pending'},
        ),
        (
            'Document Reader Agent', 'household_document_extraction', 'parallel',
            {
                'confidence': 85, 'human_approval_required': False, 'status': 'completed',
                'risk_flags': [], 'evidence_used': ['heating_bill', 'supplier_quote', 'household_baseline_checklist'],
                'missing_data': [],
                'output_summary': 'Extracted heating bill, supplier quote and household baseline checklist for the demo household.',
            },
            [
                {'evidence_id': 'heating_bill', 'source_document': 'Household Heating Bill.pdf', 'source_ref': 'p1', 'quality': 'medium', 'missing_data_warning': False, 'visibility': 'private'},
                {'evidence_id': 'supplier_quote', 'source_document': 'Clean Heating Supplier Quote.pdf', 'source_ref': 'p1-2', 'quality': 'medium', 'missing_data_warning': False, 'visibility': 'private'},
            ],
            {'evidence_quality_score': 78, 'unresolved_disagreements': 0, 'contradiction_severity': 'none', 'reviewer_status': 'pending'},
        ),
        (
            'Photo / Visual Evidence Agent', 'household_site_review', 'parallel',
            {
                'confidence': 55, 'human_approval_required': True, 'status': 'needs_review',
                'risk_flags': ['unverified_visual_hypothesis'], 'evidence_used': ['household_photos'],
                'missing_data': [],
                'output_summary': 'Household photos show visible draughts and worn insulation; findings remain a hypothesis pending technical confirmation.',
            },
            [
                {'evidence_id': 'household_photos', 'source_document': 'Household Site Photos.zip', 'source_ref': 'photos 1-6', 'quality': 'weak', 'missing_data_warning': False, 'visibility': 'private'},
            ],
            {'evidence_quality_score': 50, 'unresolved_disagreements': 0, 'contradiction_severity': 'none', 'reviewer_status': 'pending'},
        ),
        (
            'Waste & Leakage Agent', 'household_heat_loss_detection', 'solo',
            build_waste_leakage_fixture(
                inventory_value=INVENTORY_VALUE_CEILING, historical_loss_rate=0.35,
                evidence_used=['heating_bill', 'household_baseline_checklist'],
                missing_data=['independent_technical_inspection_report'],
                classification='forecast', confidence=60,
                risk_flags=['cold_weather_risk'],
                next_action='Route to Asset Passport Agent and Finance Modelling Agent.',
            ),
            [], {'evidence_quality_score': 55, 'unresolved_disagreements': 0, 'contradiction_severity': 'none', 'reviewer_status': 'pending'},
        ),
        (
            'Asset Passport Agent', 'household_heating_asset_record_creation', 'handoff',
            {
                'confidence': 84, 'human_approval_required': False, 'status': 'completed',
                'risk_flags': [], 'evidence_used': ['heating_bill', 'household_baseline_checklist'],
                'missing_data': [],
                'output_summary': 'Structured household heating asset profile created.',
            },
            [], {'evidence_quality_score': 84, 'unresolved_disagreements': 0, 'contradiction_severity': 'none', 'reviewer_status': 'pending'},
        ),
        (
            'Industrial Playbook Matching Agent', 'clean_heat_playbook_matching', 'handoff',
            {
                'confidence': 78, 'human_approval_required': False, 'status': 'completed',
                'risk_flags': [], 'evidence_used': ['heating_bill', 'supplier_quote'],
                'missing_data': [],
                'output_summary': 'Matched to clean-heating, insulation and smart-controls playbooks.',
            },
            [], {'evidence_quality_score': 78, 'unresolved_disagreements': 0, 'contradiction_severity': 'none', 'reviewer_status': 'pending'},
        ),
        (
            'Finance Modelling Agent', 'household_intervention_finance_modelling', 'council',
            build_finance_modelling_fixture(
                expected_value_recovered=650, intervention_cost=150,
                evidence_used=['heating_bill', 'supplier_quote'],
                next_action='Route to Capital Allocation Agent for intervention ranking.',
            ),
            [], {'evidence_quality_score': 75, 'unresolved_disagreements': 1, 'contradiction_severity': 'low', 'reviewer_status': 'pending'},
        ),
        (
            'Capital Allocation Agent', 'stewardship_intervention_ranking', 'council',
            {
                'confidence': 72, 'human_approval_required': True, 'status': 'completed',
                'risk_flags': [], 'evidence_used': ['heating_bill', 'supplier_quote'], 'missing_data': [],
                'output_summary': (
                    f"Recommend {top_intervention['title']} first (rank 1 of {len(ranked_interventions)}, "
                    f"composite {top_intervention['composite_score']}). Recommendation for Council/human review "
                    f"only, never an autonomous investment decision."
                ),
            },
            [], {'evidence_quality_score': 72, 'unresolved_disagreements': 0, 'contradiction_severity': 'none', 'reviewer_status': 'pending'},
        ),
        (
            'MRV Agent', 'stewardship_savings_verification_check', 'council',
            {
                'confidence': 65, 'human_approval_required': True, 'status': 'needs_review',
                'risk_flags': ['after_data_missing'], 'evidence_used': [],
                'missing_data': ['post_intervention_heating_cost_data', 'post_intervention_comfort_survey'],
                'output_summary': 'The recoverable value remains estimated because post-intervention evidence does not yet exist.',
            },
            [], {'evidence_quality_score': 50, 'unresolved_disagreements': 1, 'contradiction_severity': 'low', 'reviewer_status': 'pending'},
        ),
        (
            'Governance Agent', 'stewardship_safety_and_wording_review', 'council',
            {
                'confidence': 88, 'human_approval_required': True, 'status': 'needs_review',
                'risk_flags': ['household_consent_required', 'vulnerable_person_protection_review'],
                'evidence_used': ['heating_bill', 'supplier_quote'], 'missing_data': [],
                'output_summary': (
                    'Household consent and vulnerable-person protection require review; public-facing wording '
                    'must remain conditional pending MRV verification.'
                ),
            },
            [], {'evidence_quality_score': 82, 'unresolved_disagreements': 1, 'contradiction_severity': 'low', 'reviewer_status': 'pending'},
        ),
        (
            'Report Generator Agent', 'tour_brief_generation', 'handoff',
            {
                'confidence': 79, 'human_approval_required': True, 'status': 'completed',
                'risk_flags': [], 'evidence_used': ['heating_bill', 'supplier_quote'], 'missing_data': [],
                'output_summary': 'Builds the tour brief, sponsor brief, participant brief and draft legacy report template; investor/public wording remains conditional.',
            },
            [], {'evidence_quality_score': 78, 'unresolved_disagreements': 0, 'contradiction_severity': 'none', 'reviewer_status': 'human_reviewed'},
        ),
        (
            'Amanah Autopilot Supervisor', 'overnight_tour_evidence_supervision', 'solo',
            {
                'confidence': 70, 'human_approval_required': False, 'status': 'completed',
                'risk_flags': [], 'evidence_used': ['heating_bill'], 'missing_data': [],
                'output_summary': 'Overnight check confirms no new high-risk alerts; this case is queued in the human review queue.',
            },
            [], {'evidence_quality_score': 70, 'unresolved_disagreements': 0, 'contradiction_severity': 'none', 'reviewer_status': 'pending'},
        ),
    ]

    tasks_by_agent = {}
    for order, (agent_name, task_type, collaboration_mode, fixture, evidence_provenance, signals) in enumerate(
        pipeline_steps, start=1,
    ):
        agent_run = create_agent_run(
            agent_name, task_type, council_case=council_run, execution_mode='simulated_demo',
            input_summary=f'Kazakhstan Clean Heat Stewardship Tour — {task_type}', evidence_provenance=evidence_provenance,
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
        disagreement_1.evidence_used = ['heating_bill', 'supplier_quote']
        disagreement_1.final_decision_summary = (
            "Governance's household-consent and vulnerable-person protection concerns are preserved as formal conditions."
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
        disagreement_2.evidence_used = ['heating_bill']
        disagreement_2.final_decision_summary = (
            "MRV's missing post-intervention evidence finding is escalated rather than overridden by Finance's confidence."
        )
        disagreement_2.minority_opinion_retained = True
        disagreement_2.save()

    if finance_task and governance_task:
        exchange, _ = CrossExaminationExchange.objects.get_or_create(run=council_run, sequence=1, defaults={})
        exchange.questioner_agent = 'Governance Agent'
        exchange.target_agent = 'Finance Modelling Agent'
        exchange.challenge_type = 'household_consent_and_safety_disclosure'
        exchange.reason = 'The finance-ready claim does not address household consent or vulnerable-person protection.'
        exchange.requested_evidence = ['household_consent_form']
        exchange.response_answer = (
            'Confirms household consent was out of scope for the finance model; recommends Governance track it separately.'
        )
        exchange.response_confidence = finance_task.confidence
        exchange.unresolved_uncertainty = 'Whether household consent affects the final launch decision remains open.'
        exchange.save()

    decision, _ = CouncilDecision.objects.get_or_create(run=council_run, defaults={})
    decision.status = 'approved_with_conditions'
    decision.summary = 'Proceed with the Kazakhstan Clean Heat Stewardship Tour, subject to conditions.'
    decision.majority_agents = [
        name for name in tasks_by_agent if name != 'Governance Agent' and tasks_by_agent[name]
    ]
    decision.minority_agents = ['Governance Agent']
    decision.minority_reason = (
        'Governance Agent maintains household consent and vulnerable-person protection require review before '
        'proceeding unconditionally.'
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
        'The finance case is attractive, but Governance and MRV concerns were preserved as formal conditions '
        'rather than resolved away.'
    )
    memory_entry.open_questions = [
        'Has household consent been obtained?',
        'Has post-intervention heating cost and comfort data been collected?',
    ]
    memory_entry.unresolved_risks = ['Post-intervention evidence incomplete — savings remain estimated, not verified.']
    memory_entry.review_trigger = (
        'Reopen once post-intervention heating cost/comfort data is collected and household consent is confirmed.'
    )
    memory_entry.reopened = False
    memory_entry.save()

    create_funding_plan(
        tour, total_required=3200, participant_contribution=600, sponsor_contribution=900,
        grant_contribution=500, local_partner_contribution=200, status='under_review',
    )

    add_participant_role(
        tour, 'Participant',
        description='General stewardship-tour participant.',
        allowed_actions=['observe', 'assist_safe_preparation', 'community_cleanup', 'learning_session', 'greenhouse_support_if_approved'],
        blocked_actions=['electrical_work', 'heating_installation', 'technical_repairs', 'work_without_supervision', 'filming_vulnerable_people_without_consent'],
        safety_requirements='Supervised at all times by a qualified professional.',
        supervision_required=True,
    )
    add_participant_role(
        tour, 'Professional',
        description='Technical professional responsible for installation and safety.',
        allowed_actions=['technical_installation', 'safety_inspection', 'household_consent_review'],
        blocked_actions=['unsupervised_public_impact_claims'],
        safety_requirements='Certified installer; food-safety/technical-safety sign-off required before work.',
        supervision_required=False,
    )

    add_local_partner(
        tour, 'Almaty Region Community Cooperative', partner_type='cooperative',
        role='Household liaison, consent coordination and local due diligence.',
        due_diligence_status='in_progress', approval_status='pending', contact_status='contacted',
    )

    create_mrv_plan(
        tour, baseline_required=True, after_data_required=True,
        methodology='Before/after household heating cost and comfort survey.',
        evidence_required=[
            'before_heating_cost', 'indoor_comfort_proxy', 'fuel_use_estimate',
            'after_data', 'household_feedback', 'evidence_quality',
        ],
        verification_status='not_started', public_reporting_ready=False,
    )

    return council_run
