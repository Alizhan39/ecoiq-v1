"""
ai_agent_council/services/seed_demo.py — Council Runtime demo fixtures.

Two seeded Council Runs, both idempotent (get_or_create + explicit field
sync, never delete-then-recreate):

- `create_boiler_house_demo()` — a rich run covering all 5 collaboration
  modes, a real 3-way disagreement (Finance / Governance / MRV), two
  cross-examination exchanges, and a final Approved with Conditions
  decision that preserves Governance's minority dissent.
- `create_grid_capacity_reopened_demo()` — a simpler run whose entire
  purpose is demonstrating a decision reopening when new evidence arrives.

Every run created here has `is_simulated=True`: this is authored fixture
data run through the real deterministic services in this package (routing,
disagreement classification, confidence calibration), not live agent
output.
"""
from django.utils import timezone

from ai_agent_council.models import (
    AgentHandoff, AgentTask, CouncilDecision, CouncilDisagreement, CouncilRun,
    CrossExaminationExchange, DecisionMemoryEntry,
)
from ai_agent_council.services import routing
from ai_agent_council.services.confidence import build_confidence_breakdown
from ai_agent_council.services.disagreement import classify_conflict


def _sync(obj, **fields):
    for key, value in fields.items():
        setattr(obj, key, value)
    obj.save()
    return obj


def _sync_task(run, order, **fields):
    task, _ = AgentTask.objects.get_or_create(run=run, order=order, defaults=fields)
    return _sync(task, **fields)


def create_boiler_house_demo():
    run, _ = CouncilRun.objects.get_or_create(slug='boiler-house-3-modernisation', defaults={'title': ''})
    _sync(
        run,
        title='Boiler House #3 Modernisation',
        question='Should EcoIQ recommend proceeding with Boiler House #3 modernisation, and under what conditions?',
        task_category='industrial_asset_modernisation',
        is_simulated=True,
        status='decided',
        selected_agents=routing.select_agents_for_task('industrial_asset_modernisation'),
    )

    # Task 1 carries the spec's own worked confidence example verbatim
    # (90/86/82 inputs, -9/-7 penalties, +3 adjustment -> 79 final).
    research_breakdown = build_confidence_breakdown(90, 86, 82, 9, 7, 3)
    research_task = _sync_task(
        run, 1,
        agent_name='Research Agent', collaboration_mode='solo', status='completed',
        input_summary='Public/site context request for Boiler House #3.',
        output_summary='No material public-record risk flags found for this site.',
        position_summary='Confirms Boiler House #3 site context; no material public-record risk flags.',
        confidence=research_breakdown['final'], confidence_breakdown=research_breakdown,
        evidence_refs=['public_site_context_boiler3'], missing_data=[], risk_flags=[],
    )

    doc_reader_task = _sync_task(
        run, 2,
        agent_name='Document Reader Agent', collaboration_mode='parallel', status='completed',
        input_summary='Fuel bills and supplier quote for Boiler House #3.',
        output_summary='Extracted 12 months of fuel bill totals and supplier CAPEX quote.',
        position_summary='Extracts fuel bill totals and supplier quote figures.',
        confidence=88, confidence_breakdown={},
        evidence_refs=['fuel_bills_2024', 'supplier_quote_boiler3'], missing_data=[], risk_flags=[],
    )

    visual_task = _sync_task(
        run, 3,
        agent_name='Photo / Visual Evidence Agent', collaboration_mode='parallel', status='completed',
        input_summary='Site inspection photos of Boiler House #3.',
        output_summary='Visible insulation gaps and soot noted as hypotheses.',
        position_summary='Flags visible insulation gaps and soot as hypotheses, not verified findings.',
        confidence=70, confidence_breakdown={},
        evidence_refs=['inspection_photos_boiler3'], missing_data=[], risk_flags=['unverified_visual_hypothesis'],
    )

    asset_passport_task = _sync_task(
        run, 4,
        agent_name='Asset Passport Agent', collaboration_mode='handoff', status='completed',
        input_summary='Extracted facts and visual hypotheses for Boiler House #3.',
        output_summary='Structured asset record created for Boiler House #3.',
        position_summary='Builds the structured digital asset record.',
        confidence=85, confidence_breakdown={},
        evidence_refs=['fuel_bills_2024', 'supplier_quote_boiler3', 'inspection_photos_boiler3'],
        missing_data=[], risk_flags=[],
    )

    playbook_task = _sync_task(
        run, 5,
        agent_name='Industrial Playbook Matching Agent', collaboration_mode='handoff', status='completed',
        input_summary='Boiler House #3 asset record.',
        output_summary='Matched to the Boiler Modernisation Playbook.',
        position_summary='Matches Boiler House #3 to the Boiler Modernisation Playbook.',
        confidence=83, confidence_breakdown={},
        evidence_refs=['fuel_bills_2024', 'supplier_quote_boiler3'],
        missing_data=[], risk_flags=['transition_risk_medium'],
    )

    finance_breakdown = build_confidence_breakdown(85, 80, 80, 3, 0, 0)
    finance_task = _sync_task(
        run, 6,
        agent_name='Finance Modelling Agent', collaboration_mode='council', status='completed',
        input_summary='Boiler Modernisation Playbook match and supplier quote.',
        output_summary='Draft CAPEX/OPEX/payback model.',
        position_summary='Financially attractive: estimated payback of approximately 3.2 years.',
        confidence=finance_breakdown['final'], confidence_breakdown=finance_breakdown,
        evidence_refs=['fuel_bills_2024', 'supplier_quote_boiler3'], missing_data=[], risk_flags=[],
    )

    governance_breakdown = build_confidence_breakdown(92, 88, 88, 3, 0, 0)
    governance_task = _sync_task(
        run, 7,
        agent_name='Governance Agent', collaboration_mode='council', status='completed',
        input_summary='Finance model and playbook match for Boiler House #3.',
        output_summary='Routes finance and procurement review.',
        position_summary='Should not proceed until procurement transparency is improved.',
        confidence=governance_breakdown['final'], confidence_breakdown=governance_breakdown,
        evidence_refs=['fuel_bills_2024', 'supplier_quote_boiler3'],
        missing_data=[], risk_flags=['procurement_transparency_gap'],
    )

    mrv_breakdown = build_confidence_breakdown(80, 75, 75, 4, 0, 0)
    mrv_task = _sync_task(
        run, 8,
        agent_name='MRV Agent', collaboration_mode='council', status='completed',
        input_summary='Boiler House #3 modernisation claim.',
        output_summary='Baseline survey is incomplete; cannot yet verify impact.',
        position_summary='Cannot verify impact — baseline survey is incomplete.',
        confidence=mrv_breakdown['final'], confidence_breakdown=mrv_breakdown,
        evidence_refs=['baseline_survey_boiler3_incomplete'], missing_data=['baseline_survey_boiler3'],
        risk_flags=['baseline_incomplete'],
    )

    report_task = _sync_task(
        run, 9,
        agent_name='Report Generator Agent', collaboration_mode='handoff', status='completed',
        input_summary='Finance, Governance and MRV positions for Boiler House #3.',
        output_summary='Decision memo drafted for human approval.',
        position_summary='Builds the evidence-linked decision memo for human approval.',
        confidence=84, confidence_breakdown={},
        evidence_refs=['fuel_bills_2024', 'supplier_quote_boiler3'], missing_data=[], risk_flags=[],
    )

    mrv_escalation_task = _sync_task(
        run, 10,
        agent_name='MRV Agent', collaboration_mode='escalation', status='completed',
        input_summary='Missing baseline survey for Boiler House #3.',
        output_summary='Escalated to human review before any verified impact claim is made.',
        position_summary='Escalates missing baseline evidence to human review.',
        confidence=None, confidence_breakdown={},
        evidence_refs=[], missing_data=['baseline_survey_boiler3'], risk_flags=['baseline_incomplete'],
    )

    used_orders = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    AgentTask.objects.filter(run=run).exclude(order__in=used_orders).delete()

    handoff, _ = AgentHandoff.objects.get_or_create(run=run, order=1, defaults={})
    _sync(
        handoff,
        sender_agent='Document Reader Agent', receiver_agent='Asset Passport Agent',
        reason='Delivers extracted fuel bill and supplier quote facts for the structured asset record.',
        evidence_attached=['fuel_bills_2024', 'supplier_quote_boiler3'],
        unresolved_questions=['Baseline before-data completeness is unconfirmed.'],
        confidence_at_handoff=doc_reader_task.confidence,
        required_output='Structured asset record with linked evidence.',
    )
    AgentHandoff.objects.filter(run=run).exclude(order__in=[1]).delete()

    finance_vs_governance_type, finance_vs_governance_method = classify_conflict(finance_task, governance_task)
    disagreement_1, _ = CouncilDisagreement.objects.get_or_create(
        run=run, position_a=finance_task, position_b=governance_task, defaults={},
    )
    _sync(
        disagreement_1,
        conflict_type=finance_vs_governance_type,
        evidence_used=['fuel_bills_2024', 'supplier_quote_boiler3'],
        resolution_method=finance_vs_governance_method,
        final_decision_summary=(
            'Governance\'s procurement-transparency concern is preserved as a formal '
            'condition rather than resolved away.'
        ),
        minority_opinion_retained=True,
    )

    finance_vs_mrv_type, finance_vs_mrv_method = classify_conflict(finance_task, mrv_task)
    disagreement_2, _ = CouncilDisagreement.objects.get_or_create(
        run=run, position_a=finance_task, position_b=mrv_task, defaults={},
    )
    _sync(
        disagreement_2,
        conflict_type=finance_vs_mrv_type,
        evidence_used=['fuel_bills_2024', 'supplier_quote_boiler3'],
        resolution_method=finance_vs_mrv_method,
        final_decision_summary='MRV\'s missing-baseline finding is escalated rather than overridden by Finance\'s confidence.',
        minority_opinion_retained=True,
    )

    kept_pairs = {(finance_task.id, governance_task.id), (finance_task.id, mrv_task.id)}
    for disagreement in CouncilDisagreement.objects.filter(run=run):
        if (disagreement.position_a_id, disagreement.position_b_id) not in kept_pairs:
            disagreement.delete()

    exchange_1, _ = CrossExaminationExchange.objects.get_or_create(run=run, sequence=1, defaults={})
    _sync(
        exchange_1,
        questioner_agent='Governance Agent', target_agent='Finance Modelling Agent',
        challenge_type='risk_disclosure',
        reason='The financially-attractive claim does not address the procurement transparency risk.',
        requested_evidence=['procurement_process_log'],
        response_answer='Confirms the procurement review was out of scope for the finance model; recommends Governance track it separately.',
        response_evidence=[],
        response_confidence=finance_task.confidence,
        unresolved_uncertainty='Whether the procurement transparency gap affects funding eligibility remains open.',
    )

    exchange_2, _ = CrossExaminationExchange.objects.get_or_create(run=run, sequence=2, defaults={})
    _sync(
        exchange_2,
        questioner_agent='MRV Agent', target_agent='Industrial Playbook Matching Agent',
        challenge_type='baseline_availability',
        reason='The playbook match assumes measurable after-data; the baseline evidence is incomplete.',
        requested_evidence=['baseline_survey_boiler3'],
        response_answer='Confirms the playbook selection does not depend on baseline completeness; recommends MRV resolve it directly with the site operator.',
        response_evidence=['boiler_modernisation_playbook_v2'],
        response_confidence=playbook_task.confidence,
        unresolved_uncertainty='Baseline survey completion date is not yet confirmed.',
    )
    CrossExaminationExchange.objects.filter(run=run).exclude(sequence__in=[1, 2]).delete()

    decision_breakdown = build_confidence_breakdown(88, 85, 80, 5, 3, 2)
    decision, _ = CouncilDecision.objects.get_or_create(run=run, defaults={})
    _sync(
        decision,
        status='approved_with_conditions',
        summary='Proceed with Boiler House #3 modernisation, subject to conditions.',
        majority_agents=[
            'Research Agent', 'Document Reader Agent', 'Photo / Visual Evidence Agent',
            'Asset Passport Agent', 'Industrial Playbook Matching Agent',
            'Finance Modelling Agent', 'Report Generator Agent',
        ],
        minority_agents=['Governance Agent'],
        minority_reason=(
            'Governance Agent maintains procurement transparency has not been sufficiently '
            'resolved and dissents from unconditional approval.'
        ),
        conditions=[
            'Procurement transparency review completed before funding release.',
            'Baseline survey completed before any verified impact claim is made.',
        ],
        confidence=decision_breakdown['final'], confidence_breakdown=decision_breakdown,
        human_approval_required=True, human_approved=True,
    )

    memory_entry, _ = DecisionMemoryEntry.objects.get_or_create(decision=decision, defaults={})
    _sync(
        memory_entry,
        original_decision_summary=decision.summary,
        reason=(
            'The finance case is strong, but Governance\'s procurement-transparency concern '
            'was preserved as a formal condition rather than resolved away.'
        ),
        open_questions=[
            'Has procurement transparency been resolved?',
            'Has the baseline survey been completed?',
        ],
        unresolved_risks=['Baseline survey incomplete — verified impact cannot yet be claimed.'],
        review_trigger=(
            'Reopen if procurement transparency documentation is submitted or the baseline '
            'survey is completed.'
        ),
        reopened=False, reopened_reason='', new_evidence_summary='', updated_decision_summary='',
        reopened_at=None,
    )

    return run


def create_grid_capacity_reopened_demo():
    run, _ = CouncilRun.objects.get_or_create(slug='grid-capacity-evidence-review', defaults={'title': ''})
    _sync(
        run,
        title='Grid Capacity Evidence Review',
        question='Does new grid capacity evidence change the earlier decision on site electrification readiness?',
        task_category='decision_reopening_review',
        is_simulated=True,
        status='reopened',
        selected_agents=routing.select_agents_for_task('decision_reopening_review'),
    )

    research_task = _sync_task(
        run, 1,
        agent_name='Research Agent', collaboration_mode='solo', status='completed',
        input_summary='Check for updated regional grid capacity data.',
        output_summary='Regional grid operator has published updated capacity figures.',
        position_summary='Confirms updated public grid capacity data is now available for the region.',
        confidence=88, confidence_breakdown={},
        evidence_refs=['grid_capacity_notice_2026'], missing_data=[], risk_flags=[],
    )

    doc_reader_task = _sync_task(
        run, 2,
        agent_name='Document Reader Agent', collaboration_mode='handoff', status='completed',
        input_summary='Regional grid operator capacity notice.',
        output_summary='Extracted updated feeder headroom figures.',
        position_summary='Extracts new grid capacity figures from the regional operator\'s published notice.',
        confidence=85, confidence_breakdown={},
        evidence_refs=['grid_capacity_notice_2026'], missing_data=[], risk_flags=[],
    )

    mrv_task = _sync_task(
        run, 3,
        agent_name='MRV Agent', collaboration_mode='council', status='completed',
        input_summary='Updated grid capacity evidence.',
        output_summary='Verification status upgraded: capacity evidence supports after-data baseline.',
        position_summary='Verification status upgraded: capacity evidence now supports the after-data baseline.',
        confidence=80, confidence_breakdown={},
        evidence_refs=['grid_capacity_notice_2026'], missing_data=[], risk_flags=[],
    )

    governance_task = _sync_task(
        run, 4,
        agent_name='Governance Agent', collaboration_mode='council', status='completed',
        input_summary='Updated grid capacity evidence and MRV re-assessment.',
        output_summary='Confirms the review trigger conditions are met.',
        position_summary='Confirms review conditions are met and recommends reopening the prior decision.',
        confidence=90, confidence_breakdown={},
        evidence_refs=['grid_capacity_notice_2026'], missing_data=[], risk_flags=[],
    )

    used_orders = [1, 2, 3, 4]
    AgentTask.objects.filter(run=run).exclude(order__in=used_orders).delete()

    conflict_type, resolution_method = classify_conflict(doc_reader_task, governance_task)
    disagreement, _ = CouncilDisagreement.objects.get_or_create(
        run=run, position_a=doc_reader_task, position_b=governance_task, defaults={},
    )
    _sync(
        disagreement,
        conflict_type=conflict_type,
        evidence_used=['grid_capacity_notice_2026'],
        resolution_method=resolution_method,
        final_decision_summary='Both readings of the same evidence are recorded; Governance\'s framing is kept alongside the extraction.',
        minority_opinion_retained=True,
    )
    for stale in CouncilDisagreement.objects.filter(run=run).exclude(
        position_a=doc_reader_task, position_b=governance_task,
    ):
        stale.delete()

    decision_breakdown = build_confidence_breakdown(84, 82, 82, 4, 2, 0)
    decision, _ = CouncilDecision.objects.get_or_create(run=run, defaults={})
    _sync(
        decision,
        status='reopened',
        summary=(
            'Decision reopened: grid capacity is no longer a blocking constraint; proceed to '
            're-run Finance and Governance review.'
        ),
        majority_agents=['Research Agent', 'Document Reader Agent', 'MRV Agent'],
        minority_agents=['Governance Agent'],
        minority_reason=(
            'Governance Agent flags that reopening still requires a fresh procurement/finance '
            'review before any new commitment is made.'
        ),
        conditions=[
            'Original grid capacity concern resolved by new evidence.',
            'Finance and Governance must re-review before proceeding.',
        ],
        confidence=decision_breakdown['final'], confidence_breakdown=decision_breakdown,
        human_approval_required=True, human_approved=None,
    )

    memory_entry, _ = DecisionMemoryEntry.objects.get_or_create(decision=decision, defaults={})
    _sync(
        memory_entry,
        original_decision_summary=(
            'Approved with conditions: proceed with site electrification once grid capacity '
            'is confirmed by the regional operator.'
        ),
        reason='Electrification was conditionally approved pending confirmation of grid capacity headroom.',
        open_questions=['Has the regional operator published updated capacity data?'],
        unresolved_risks=[],
        review_trigger='Reopen once the regional grid operator publishes updated capacity figures.',
        reopened=True,
        reopened_reason=(
            'New grid capacity evidence (regional operator notice, 2026) satisfies the review '
            'trigger set in the original decision.'
        ),
        new_evidence_summary=(
            'Regional grid operator published updated capacity figures confirming feeder '
            'headroom is sufficient for site electrification.'
        ),
        updated_decision_summary=decision.summary,
        reopened_at=timezone.now(),
    )

    return run
