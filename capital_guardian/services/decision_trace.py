"""
capital_guardian/services/decision_trace.py — feat/explainability-layer
(PR 8): reconstructs "why did EcoIQ recommend this?" as a structured trace
over real, already-persisted EcoIQ records.

This module computes NOTHING new. It is a read/orchestration layer over the
exact same functions every other Capital Guardian page already calls:

- capital_guardian.services.command_centre (_current_loss, _primary_decision)
- capital_guardian.services.project_analysis.analyse_project (Mizan)
- capital_guardian.services.resource_purpose_review.review_resource_purpose
- capital_guardian.services.better_way.compare_interventions (ranking +
  safety/eligibility — the same function better_way_view and
  human_decision_gate_view already call; there is no persisted
  BetterWayResult to read instead, so calling it here is not "recomputing
  the pipeline", it's the existing read path every other page uses)
- capital_guardian.services.human_decision_gate (legal_actions_for) and
  waste_to_value_capital_allocation_engine.models.DecisionReviewEvent (the
  real, already-written audit trail — never re-derived)
- capital_guardian.services.execution_monitoring (expected_vs_actual,
  outcome_result_label, capital_summary, capital_decisions_for_project)
- capital_guardian.views._learning_feedback_context (Evidence Memory sync
  state)
- evidence_memory.services.retrieval_policy (is_record_accessible,
  score_and_explain) — every EvidenceMemory row shown here is checked
  against the current user's access policy first; nothing is exposed the
  policy would refuse on the record's own page.
- ai_observatory.models.AnalysisSession — project-level telemetry only;
  there is no FK from a session to a specific decision or loss (documented
  limitation, not glossed over — see the "observatory" node below).

No LLM is called anywhere in this module. Every string here is either a
literal built from real field values (an f-string over real data, not a
generated narrative) or a fixed label. Where a fact is genuinely
unavailable, the literal 'Not available' or 'Not yet measured' is used —
never inferred or guessed.
"""
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

NOT_AVAILABLE = 'Not available'
NOT_YET_MEASURED = 'Not yet measured'

# The fixed vocabulary the UI uses to visually distinguish where a fact
# came from — never invented per-node, always drawn from this set.
DATA_QUALITY_TAGS = (
    'measured', 'verified', 'estimated', 'deterministic', 'human_approved',
    'blocked', 'disputed', 'missing', 'demo',
)


@dataclass
class TraceNode:
    stage: str
    title: str
    status: str
    status_kind: str = 'na'          # one of DATA_QUALITY_TAGS-ish CSS keys, see explain_recommendation.html
    summary: str = NOT_AVAILABLE
    source_url: Optional[str] = None
    source_label: str = ''
    timestamp: Optional[object] = None   # datetime | date | None
    actor: Optional[str] = None
    warnings: list = field(default_factory=list)
    confidence: Optional[str] = None
    data_quality: list = field(default_factory=list)   # subset of DATA_QUALITY_TAGS
    extra: dict = field(default_factory=dict)
    available: bool = True


@dataclass
class DecisionTrace:
    project: object
    loss: object = None
    decision: object = None
    generated_at: object = None
    summary: dict = field(default_factory=dict)
    nodes: list = field(default_factory=list)
    data_gaps: list = field(default_factory=list)


def _url(name, *args):
    from django.urls import reverse
    try:
        return reverse(name, args=args)
    except Exception:
        return None


def _fmt_money(value):
    if value is None or value == 'NOT YET REPORTED':
        return NOT_YET_MEASURED
    return f'£{value:,.0f}'


def _actor_label(user):
    if user is None:
        return 'Not available'
    return getattr(user, 'username', None) or getattr(user, 'email', None) or f'User #{user.pk}'


def _capital_lifecycle_label(decision, governance, capital_summary):
    """Deterministic ladder of explicit labels — never implies money moved
    just because a decision or governance record exists."""
    if decision is None:
        return 'Recommendation only'
    if decision.approval_status not in ('approved', 'approved_with_conditions'):
        return f'Human decision: {decision.get_approval_status_display()}'
    if governance is None:
        return 'Human approved — not yet promoted to Capital Guardian'
    if capital_summary and (capital_summary['capital_committed_usd'] or capital_summary['capital_deployed_usd']):
        return 'Capital governed — execution started'
    return 'Capital governed — execution not yet started'


def build_decision_trace(project, decision=None, user=None):
    """
    project: gold_intelligence.GoldProject — the one hard scope boundary;
    every lookup below is either scoped through `project` directly or
    through a decision/loss already confirmed to belong to it by the
    caller (see capital_guardian.views._decision_or_404_for_project).
    decision: a waste_to_value_capital_allocation_engine.models.
    CapitalAllocationDecision already confirmed to belong to `project`, or
    None to fall back to the project's primary decision.
    user: the requesting Django user — required to apply the Evidence
    Memory access policy; a memory record the policy would refuse is never
    included in the trace, matching what that user would see on the
    Evidence Centre/Command Centre pages themselves.
    """
    from django.utils import timezone

    from capital_guardian.services import execution_monitoring
    from capital_guardian.services import evidence as evidence_service
    from capital_guardian.services.better_way import compare_interventions
    from capital_guardian.services.command_centre import _current_loss, _primary_decision
    from capital_guardian.services.human_decision_gate import legal_actions_for
    from capital_guardian.services.project_analysis import analyse_project
    from capital_guardian.services.resource_purpose_review import review_resource_purpose
    from evidence_memory.services.retrieval_policy import is_record_accessible, score_and_explain
    from ai_observatory.models import AnalysisSession

    if decision is None:
        decision = _primary_decision(project)

    loss = decision.intervention.operational_loss if decision is not None else _current_loss(project)

    nodes = []
    data_gaps = []
    warnings_all = []

    # ---- shared reads used by more than one node -------------------------
    evidence_qs = list(evidence_service.evidence_for_project(project).select_related('reviewer'))
    evidence_summary = evidence_service.verification_summary(evidence_qs)

    analysis = analyse_project(project)
    review = review_resource_purpose(project, analysis)

    comparison = compare_interventions(project, loss) if loss is not None else None
    candidate = None
    blocked_entry = None
    if comparison is not None and decision is not None:
        candidate = next((c for c in comparison.ranked if c['option'].pk == decision.intervention_id), None)
        blocked_entry = next((b for b in comparison.blocked if b['option'].pk == decision.intervention_id), None)

    review_events = list(decision.review_events.select_related('actor').all()) if decision is not None else []
    latest_review = review_events[0] if review_events else None

    governance = getattr(project, 'governance', None)
    capital_summary = execution_monitoring.capital_summary(project)
    milestones = list(project.timeline_milestones.all())

    expected_vs_actual = execution_monitoring.expected_vs_actual(decision) if decision is not None else None
    result_key = execution_monitoring.outcome_result_label(expected_vs_actual) if expected_vs_actual else None
    result_label = execution_monitoring.RESULT_LABELS[result_key] if result_key else NOT_AVAILABLE

    from capital_guardian.views import _learning_feedback_context
    learning_feedback = _learning_feedback_context(decision) if decision is not None else {'outcome_exists': False}
    memory_record = learning_feedback.get('memory')
    memory_accessible = (
        memory_record is not None and is_record_accessible(memory_record, project, user=user)
    )
    memory_retrieval = (
        score_and_explain(memory_record, project) if memory_accessible else None
    )

    latest_session = AnalysisSession.objects.filter(project=project).order_by('-started_at').first()

    # ---- 1. PROBLEM DETECTED — Operational Loss ---------------------------
    if loss is not None:
        nodes.append(TraceNode(
            stage='problem', title='Problem Detected — Operational Loss', status=loss.get_status_display(),
            status_kind='measured',
            summary=(
                f'{loss.title} — £{loss.financial_loss_amount:,.0f} financial loss recorded'
                f'{f", £{loss.projected_future_loss:,.0f} projected" if loss.projected_future_loss else ""}. '
                f'Evidence quality: {loss.get_evidence_quality_display()}.'
            ),
            source_url=_url('capital_guardian:operational_loss_detail', project.slug, loss.pk),
            source_label='View Operational Loss →',
            timestamp=loss.created_at, actor=None,
            confidence=loss.get_evidence_quality_display(),
            data_quality=['measured'],
            extra={
                'loss_type': loss.get_loss_type_display(), 'quantity_lost': loss.quantity_lost, 'unit': loss.unit,
                'urgency_score': loss.urgency_score, 'confidence': loss.confidence,
            },
        ))
    else:
        data_gaps.append('No Operational Loss recorded for this project yet.')
        nodes.append(TraceNode(
            stage='problem', title='Problem Detected — Operational Loss', status='Not Started',
            status_kind='missing', summary=NOT_AVAILABLE, available=False,
        ))

    # ---- 2. EVIDENCE USED ---------------------------------------------------
    evidence_rows = [
        {
            'title': e.text_chunk[:120], 'source_type': e.get_source_type_display(),
            'source_reference': e.source_reference, 'verification_status': e.get_verification_status_display(),
            'review_tier': e.get_review_tier_display(), 'date_collected': e.date_collected,
            'is_demo': e.is_demo, 'visibility': e.get_visibility_display(),
        }
        for e in evidence_qs
    ]
    if evidence_qs:
        nodes.append(TraceNode(
            stage='evidence', title='Evidence Used', status=f"{evidence_summary['total']} item(s)",
            status_kind='measured',
            summary=(
                f"{evidence_summary['by_status'].get('verified', 0)} verified, "
                f"{evidence_summary['by_status'].get('pending', 0)} pending, "
                f"{evidence_summary['by_status'].get('rejected', 0)} rejected/expired, "
                f"{evidence_summary['by_status'].get('requires_review', 0)} requiring review."
            ),
            source_url=_url('capital_guardian:evidence_centre', project.slug),
            source_label='View Evidence Centre →',
            data_quality=['measured'],
            warnings=(review.evidence_gaps if review else []),
            extra={'rows': evidence_rows},
        ))
    else:
        data_gaps.append('No evidence recorded for this project yet.')
        nodes.append(TraceNode(
            stage='evidence', title='Evidence Used', status='None Recorded', status_kind='missing',
            summary=NOT_AVAILABLE, available=False,
        ))

    # ---- 3. OPTIONS CONSIDERED — Intervention Options -----------------------
    if loss is not None:
        options = list(loss.interventions.all())
        option_rows = []
        for option in options:
            is_selected = decision is not None and option.pk == decision.intervention_id
            row_candidate = next((c for c in (comparison.ranked if comparison else []) if c['option'].pk == option.pk), None)
            row_blocked = next((b for b in (comparison.blocked if comparison else []) if b['option'].pk == option.pk), None)
            if row_candidate is not None:
                status = row_candidate['safety_status']
            elif row_blocked is not None:
                status = 'blocked'
            else:
                status = 'unclassified'
            option_rows.append({
                'option': option, 'is_selected': is_selected, 'status': status,
                'reason': row_blocked['reason'] if row_blocked else (row_candidate['safety_reason'] if row_candidate else ''),
                'composite_score': row_candidate.get('composite_score') if row_candidate else None,
            })
        nodes.append(TraceNode(
            stage='options', title='Options Considered', status=f'{len(options)} option(s)',
            status_kind='deterministic',
            summary=(
                f"{len(comparison.ranked) if comparison else 0} eligible/conditional, "
                f"{len(comparison.blocked) if comparison else 0} blocked."
            ),
            source_url=_url('capital_guardian:operational_loss_detail', project.slug, loss.pk),
            source_label='View Intervention Options →',
            data_quality=['deterministic'],
            extra={'rows': option_rows},
            available=bool(options),
        ))
        if not options:
            data_gaps.append('No Intervention Options have been added for this loss yet.')
    else:
        nodes.append(TraceNode(
            stage='options', title='Options Considered', status='Not Started', status_kind='missing',
            summary=NOT_AVAILABLE, available=False,
        ))

    # ---- 4. WHY THIS OPTION RANKED HIGHER — Better Way factor breakdown ----
    if comparison is not None and candidate is not None:
        from waste_to_value_capital_allocation_engine.services.ranking import RANKING_WEIGHTS

        factors = [
            {'key': k, 'value': candidate.get(k), 'weight': w}
            for k, w in RANKING_WEIGHTS.items() if k in candidate
        ]
        alternatives = [
            {'option': c['option'], 'composite_score': c['composite_score'], 'rank': c['rank']}
            for c in comparison.ranked if c is not candidate
        ]
        nodes.append(TraceNode(
            stage='better_way', title='Why This Option Ranked Higher',
            status=f"Rank {candidate['rank']} of {len(comparison.ranked)}",
            status_kind='deterministic',
            summary=comparison.why_top_ranked or comparison.baseline_warning or NOT_AVAILABLE,
            source_url=_url('capital_guardian:better_way_view', project.slug, loss.pk),
            source_label='View Better Way Comparison →',
            data_quality=['deterministic', 'estimated'],
            warnings=([comparison.baseline_warning] if comparison.baseline_warning else []) + list(comparison.limitations),
            extra={
                'composite_score': candidate.get('composite_score'), 'factors': factors,
                'alternatives': alternatives, 'blocked': comparison.blocked, 'trade_offs': comparison.trade_offs,
            },
        ))
    elif decision is not None:
        nodes.append(TraceNode(
            stage='better_way', title='Why This Option Ranked Higher', status='Not Available',
            status_kind='missing', summary=NOT_AVAILABLE, available=False,
        ))
        data_gaps.append('This decision\'s selected option could not be matched against the current Better Way comparison (it may have been blocked since).')
    else:
        nodes.append(TraceNode(
            stage='better_way', title='Why This Option Ranked Higher', status='Not Started',
            status_kind='missing', summary=NOT_AVAILABLE, available=False,
        ))

    # ---- 5. SAFETY / ELIGIBILITY CHECK --------------------------------------
    if candidate is not None or blocked_entry is not None:
        safety_status = candidate['safety_status'] if candidate else 'blocked'
        safety_reason = candidate['safety_reason'] if candidate else blocked_entry['reason']
        nodes.append(TraceNode(
            stage='safety', title='Safety / Eligibility Check', status=safety_status.upper(),
            status_kind=('blocked' if safety_status == 'blocked' else 'deterministic'),
            summary=safety_reason or f'Classified {safety_status} by the deterministic safety/eligibility gate.',
            source_url=_url('capital_guardian:operational_loss_detail', project.slug, loss.pk) if loss else None,
            source_label='View Eligibility Detail →',
            data_quality=['deterministic'] + (['blocked'] if safety_status == 'blocked' else []),
            extra={
                'produced_by': 'Deterministic rule-based safety/eligibility gate (capital_guardian.services.intervention_safety_gate) — not an AI or model output.',
                'human_override_possible': False,
                'override_note': (
                    'A blocked option cannot be approved through the Human Decision Gate — approval re-verifies '
                    'safety status and is refused if still blocked, regardless of reviewer notes.'
                ),
            },
        ))
    else:
        nodes.append(TraceNode(
            stage='safety', title='Safety / Eligibility Check', status='Not Available', status_kind='missing',
            summary=NOT_AVAILABLE, available=False,
        ))

    # ---- 6. HUMAN DECISION ---------------------------------------------------
    if decision is not None:
        nodes.append(TraceNode(
            stage='human_decision', title='Human Decision', status=decision.get_approval_status_display(),
            status_kind=('human_approved' if decision.approval_status in ('approved', 'approved_with_conditions') else (
                'blocked' if decision.approval_status == 'rejected' else 'deterministic'
            )),
            summary=(
                f'Reviewed by {_actor_label(latest_review.actor) if latest_review else "Not yet reviewed"}. '
                f'{latest_review.notes if latest_review and latest_review.notes else "No rationale recorded."}'
            ),
            source_url=_url('capital_guardian:human_decision_gate', project.slug, decision.pk),
            source_label='Open Human Decision Gate →',
            timestamp=latest_review.created_at if latest_review else None,
            actor=_actor_label(latest_review.actor) if latest_review else None,
            data_quality=['human_approved'] if decision.approval_status.startswith('approved') else ['deterministic'],
            extra={
                'conditions': decision.conditions or [], 'legal_actions': legal_actions_for(decision),
                'review_events': [
                    {
                        'action': ev.get_action_display(), 'previous_status': ev.previous_status,
                        'new_status': ev.new_status, 'notes': ev.notes, 'actor': _actor_label(ev.actor),
                        'created_at': ev.created_at,
                    }
                    for ev in review_events
                ],
            },
        ))
    else:
        data_gaps.append('No Capital Allocation Decision has been created for this project yet — nothing has reached human review.')
        nodes.append(TraceNode(
            stage='human_decision', title='Human Decision', status='Not Started', status_kind='missing',
            summary=NOT_AVAILABLE, available=False,
        ))

    # ---- 7. CAPITAL GUARDIAN --------------------------------------------------
    lifecycle_label = _capital_lifecycle_label(decision, governance, capital_summary)
    nodes.append(TraceNode(
        stage='capital_guardian', title='Capital Guardian', status=lifecycle_label,
        status_kind=('human_approved' if governance is not None else 'deterministic'),
        summary=(
            f'{governance.active_controls_count} governance control(s) active.' if governance is not None
            else 'Not yet promoted to Capital Guardian governance.'
        ),
        source_url=_url('capital_guardian:governance', project.slug),
        source_label='View Governance →',
        data_quality=['human_approved'] if governance is not None else ['deterministic'],
        available=governance is not None or decision is not None,
        extra={
            'capital_committed_usd': capital_summary['capital_committed_usd'],
            'capital_deployed_usd': capital_summary['capital_deployed_usd'],
            'capital_remaining_usd': capital_summary['capital_remaining_usd'],
        },
    ))

    # ---- 8. EXECUTION -----------------------------------------------------
    complete_count = sum(1 for m in milestones if m.status == 'complete')
    nodes.append(TraceNode(
        stage='execution', title='Execution', status=(f'{complete_count} of {len(milestones)} milestone(s) complete' if milestones else 'No Milestones Recorded'),
        status_kind='measured' if milestones else 'missing',
        summary=(
            f'Capital committed £{capital_summary["capital_committed_usd"]:,.0f}, '
            f'deployed £{capital_summary["capital_deployed_usd"]:,.0f}.'
        ),
        source_url=_url('capital_guardian:project_monitoring', project.slug),
        source_label='Open Execution Monitoring →',
        data_quality=['measured'],
        available=bool(milestones) or capital_summary['entry_count'] > 0,
        extra={'milestones': milestones},
    ))
    if not milestones:
        data_gaps.append('No implementation milestones have been recorded yet.')

    # ---- 9. EXPECTED VS ACTUAL OUTCOME -------------------------------------
    if expected_vs_actual is not None:
        nodes.append(TraceNode(
            stage='outcome', title='Expected vs Actual Outcome', status=result_label,
            status_kind=(
                'disputed' if result_key == 'disputed' else
                'verified' if result_key == 'achieved' else
                'estimated' if result_key == 'partially_achieved' else
                'missing' if result_key == 'insufficient_evidence' else 'estimated'
            ),
            summary=(
                f'Expected loss avoided {_fmt_money(expected_vs_actual["expected_loss_avoided"])}, '
                f'actual {_fmt_money(expected_vs_actual["actual_loss_avoided"])}. '
                f'MRV status: {expected_vs_actual["mrv_status"]}.'
            ),
            source_url=_url('capital_guardian:record_outcome_confirm', project.slug, decision.pk),
            source_label='View Outcome / MRV →',
            data_quality=(['disputed'] if result_key == 'disputed' else ['estimated']),
            extra={'expected_vs_actual': expected_vs_actual, 'result_key': result_key},
            available=expected_vs_actual['outcome'] is not None,
        ))
        if expected_vs_actual['outcome'] is None:
            data_gaps.append('No outcome has been recorded for this decision yet.')
    else:
        nodes.append(TraceNode(
            stage='outcome', title='Expected vs Actual Outcome', status='Not Started', status_kind='missing',
            summary=NOT_AVAILABLE, available=False,
        ))

    # ---- 10. LEARNING LOOP — Evidence Memory --------------------------------
    if learning_feedback.get('outcome_exists'):
        if memory_accessible:
            nodes.append(TraceNode(
                stage='evidence_memory', title='Learning Loop — Evidence Memory',
                status=('Synced' if learning_feedback['already_synced'] else 'Not Yet Synced'),
                status_kind=('demo' if memory_record.is_demo else 'verified' if memory_record.verification_status == 'verified' else 'estimated'),
                summary=(
                    f'{memory_record.get_verification_status_display()} · {memory_record.get_visibility_display()} · '
                    f'{"Demo/Illustrative" if memory_record.is_demo else "Real evidence"}.'
                ),
                source_url=_url('capital_guardian:evidence_centre', project.slug),
                source_label='View in Evidence Centre →',
                timestamp=memory_record.updated_at,
                data_quality=(['demo'] if memory_record.is_demo else ['verified' if memory_record.verification_status == 'verified' else 'estimated']),
                extra={
                    'memory': memory_record, 'retrieval': memory_retrieval,
                    'blockers': learning_feedback.get('blockers', []),
                },
            ))
        else:
            nodes.append(TraceNode(
                stage='evidence_memory', title='Learning Loop — Evidence Memory',
                status=('Synced (restricted)' if learning_feedback['already_synced'] else 'Not Yet Synced'),
                status_kind='missing',
                summary=(
                    'A memory record exists but is not visible to the current user under Evidence Memory '
                    'access policy.' if learning_feedback['already_synced']
                    else 'This measured outcome has not yet been added to Evidence Memory — the learning loop is incomplete.'
                ),
                source_url=_url('capital_guardian:record_outcome_confirm', project.slug, decision.pk) if decision else None,
                source_label='Open Outcome / Evidence Memory →',
                data_quality=['missing'],
                extra={'blockers': learning_feedback.get('blockers', [])},
            ))
    else:
        nodes.append(TraceNode(
            stage='evidence_memory', title='Learning Loop — Evidence Memory', status='Not Applicable',
            status_kind='missing', summary='No measured outcome exists yet for this decision to enter the learning loop.',
            available=False,
        ))

    # ---- 11. SYSTEM OPERATION — AI Observatory ------------------------------
    if latest_session is not None:
        session_warnings = list(latest_session.warnings or [])
        warnings_all += session_warnings
        nodes.append(TraceNode(
            stage='observatory', title='System Operation — AI Observatory', status=latest_session.get_status_display(),
            status_kind='measured',
            summary=(
                f'{latest_session.get_kind_display()} — {latest_session.deterministic_stage_count} deterministic '
                f'stage(s), {latest_session.model_call_count} model call(s), {latest_session.retrieval_stage_count} '
                f'retrieval operation(s).'
            ),
            source_url=_url('ai_observatory:observatory', project.slug),
            source_label='Open Full AI Observatory →',
            timestamp=latest_session.started_at,
            warnings=session_warnings,
            data_quality=['measured'],
            extra={
                'session': latest_session,
                'association_note': (
                    'Associated with this project by recency only — AnalysisSession has no foreign key to a '
                    'specific decision or operational loss, so this is the latest telemetry for the project as '
                    'a whole, not a guaranteed record of the exact pipeline run that produced this recommendation.'
                ),
            },
        ))
    else:
        nodes.append(TraceNode(
            stage='observatory', title='System Operation — AI Observatory', status='No Linked Telemetry Session Available',
            status_kind='missing', summary='No linked telemetry session available.', available=False,
        ))

    # ---- structured summary (deterministic, no prose generation) -----------
    alternatives_considered = []
    why_lower = []
    if comparison is not None:
        for c in comparison.ranked:
            if candidate is not None and c is candidate:
                continue
            alternatives_considered.append(c['option'].title)
            why_lower.append(f"{c['option'].title}: composite score {c['composite_score']} (vs {candidate['composite_score'] if candidate else NOT_AVAILABLE} selected)")
        for b in comparison.blocked:
            alternatives_considered.append(b['option'].title)
            why_lower.append(f"{b['option'].title}: blocked — {b['reason']}")

    confidence_warnings = list(warnings_all)
    if analysis is not None:
        confidence_warnings += list(analysis.warnings)
    if review is not None:
        confidence_warnings += list(review.evidence_gaps)
    if comparison is not None:
        confidence_warnings += list(comparison.limitations)
        if comparison.baseline_warning:
            confidence_warnings.append(comparison.baseline_warning)
    confidence_warnings += data_gaps

    summary = {
        'recommended_intervention': decision.intervention.title if decision is not None else NOT_AVAILABLE,
        'current_status': decision.get_approval_status_display() if decision is not None else 'No decision yet',
        'why_recommended': comparison.why_top_ranked if (comparison is not None and comparison.why_top_ranked) else NOT_AVAILABLE,
        'key_evidence': [row['title'] for row in evidence_rows[:5]] or [NOT_AVAILABLE],
        'alternatives_considered': alternatives_considered or [NOT_AVAILABLE],
        'why_alternatives_lower': why_lower or [NOT_AVAILABLE],
        'human_approval_status': decision.get_approval_status_display() if decision is not None else 'Not started',
        'capital_governance_status': lifecycle_label,
        'execution_status': (f'{complete_count} of {len(milestones)} milestone(s) complete' if milestones else NOT_YET_MEASURED),
        'outcome_status': result_label,
        'confidence_warnings': confidence_warnings or ['No warnings recorded.'],
    }

    return DecisionTrace(
        project=project, loss=loss, decision=decision, generated_at=timezone.now(),
        summary=summary, nodes=nodes, data_gaps=data_gaps,
    )
