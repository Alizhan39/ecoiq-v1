"""
capital_guardian/services/command_centre.py — the Project Command Centre:
a read-oriented orchestration layer over the complete evidence-to-outcome
vertical slice. This module computes NOTHING new — every value returned
here is read directly from an existing model or delegated to an existing
service (evidence, project_analysis, resource_purpose_review, better_way,
execution_monitoring, evidence_memory retrieval). It is not a new source
of truth: if this module disappeared, every fact it displays would still
be independently visible on its own existing page.

CANONICAL STAGE LIST (13 stages) — decided by reviewing each candidate
against one test: does it represent a genuinely different persisted
state, a different permission boundary, or a different real action, from
its neighbours? Two candidates that were considered and deliberately
folded into a neighbour are documented below, not silently dropped.

 1. Project              — GoldProject identity/status. Not a workflow
                            step (the project already exists by the time
                            this page is viewed), but a genuinely distinct
                            concern: is the project's own identity data
                            complete? Folds in the Mizan project-analysis
                            score as supporting detail — see "Analysis"
                            note below.
 2. Evidence              — EvidenceMemory rows for this project. Distinct
                            persisted model, distinct staff-only intake
                            action, distinct permission (add vs. view).
 3. Resource Purpose Review — a hand-reviewed pathway profile. Distinct
                            content, distinct "has this project been
                            reviewed at all" state from Evidence.
 4. Baseline / Operational Loss — OperationalLoss model. Distinct
                            persisted row, distinct creation action.
 5. Intervention Options  — InterventionOption rows. Previously folded
                            invisibly inside the "Better Way" stage; this
                            revision gives it its own row because it has
                            its own model, its own staff-only creation
                            action (create_intervention_option_execute),
                            and its own state ("no options yet" is a
                            meaningfully different situation from "options
                            exist but haven't been compared"). Carries the
                            safety/eligibility breakdown as a sub-detail
                            (see "Safety/Eligibility" note below).
 6. The Better Way        — the comparison/ranking action over existing
                            options. Stateless (computed live), but a
                            genuinely distinct action from creating options
                            in the first place.
 7. Capital Decision      — CapitalAllocationDecision existence. Distinct
                            persisted row, distinct creation action,
                            distinct from its own approval state (next).
 8. Human Approval        — decision.approval_status. Deliberately kept
                            separate from "Capital Decision exists" (a
                            decision can exist and be pending/approved/
                            rejected — a materially different axis of
                            state, and the subject of the next hardening
                            phase).
 9. Capital Guardian      — ProjectGovernance promotion. Distinct
                            persisted row, distinct staff-only action.
10. Execution             — CapitalTraceEntry / milestone monitoring data.
                            Distinct persisted data, distinct actions
                            (add trace entry, add/update milestone).
11. Outcome               — VerifiedCapitalOutcome. Distinct persisted
                            row, distinct recording action, distinct MRV
                            status axis from Execution.
12. Evidence Memory       — whether the outcome has been synced into
                            EvidenceMemory for future retrieval. Distinct
                            action (sync), distinct persisted check
                            (does a matching EvidenceMemory row exist).
13. Sustainable AI Telemetry — feat/ai-observatory: REAL now. Backed by
                            ai_observatory.AnalysisSession rows recorded
                            live around the actual pipelines; the stage
                            summarises the latest session and links to
                            the AI Observatory (which owns the detail —
                            this stage never duplicates the dashboard).
                            Shown as NOT_STARTED (not UNAVAILABLE) when a
                            project simply has no recorded sessions yet.

TWO CANDIDATES DELIBERATELY FOLDED IN, NOT MADE THEIR OWN STAGE:

- "Analysis" (Mizan project scoring): considered as its own stage (it
  was, in the previous revision of this module) but on inspection its
  status was ENTIRELY derived from whether evidence exists — it has no
  independent persisted state, no independent permission boundary, and
  no independent action/URL of its own (it's computed live, on the same
  page, as a side effect of viewing the Evidence Centre). It fails the
  three-part test above, so its real output (the Mizan score) is folded
  into the Project stage's summary instead of being a redundant row that
  would always show the same status as Evidence one line down.
- "Safety / Eligibility": a real, critical, and separately-tested gate
  (capital_guardian.services.intervention_safety_gate), but it has no
  persisted state of its own (nothing is stored — it's recomputed from
  each InterventionOption's fields on every view), no distinct permission
  boundary, and no distinct action/URL a human clicks ("review safety"
  is not a separate action from viewing Intervention Options or Resource
  Purpose Review). It is surfaced prominently as a sub-detail (an
  eligible/conditional/blocked breakdown) on the Intervention Options
  stage, rather than invented as a top-level row with nothing of its own
  to link to.

Workflow stage vocabulary distinguishes NOT_STARTED / MISSING_DATA /
IN_PROGRESS / REQUIRES_REVIEW / BLOCKED / PENDING_APPROVAL /
APPROVED_WITH_CONDITIONS / REJECTED / ACTIVE_MONITORING /
OUTCOME_ESTIMATED / HUMAN_REVIEWED / VERIFIED / COMPLETE / UNAVAILABLE —
never collapsed into a misleading blanket "complete", and MISSING_DATA is
used instead of a bare zero wherever showing zero would imply a real
measurement of "none" rather than "not recorded".
"""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional, Union

from django.urls import reverse

from capital_guardian.services import evidence as evidence_service
from capital_guardian.services import execution_monitoring, project_analysis, resource_purpose_review


# Cosmetic-only status -> badge-colour mapping (reuses the same low/medium/
# high/na risk-badge classes already used throughout Capital Guardian's
# templates) — never a scoring computation, purely a display grouping.
_STATUS_CSS = {
    'NOT_STARTED': 'na', 'MISSING_DATA': 'na', 'IN_PROGRESS': 'medium', 'REQUIRES_REVIEW': 'medium',
    'BLOCKED': 'high', 'PENDING_APPROVAL': 'medium', 'APPROVED_WITH_CONDITIONS': 'medium', 'REJECTED': 'high',
    'ACTIVE_MONITORING': 'low', 'OUTCOME_ESTIMATED': 'medium', 'HUMAN_REVIEWED': 'medium',
    'VERIFIED': 'low', 'COMPLETE': 'low', 'UNAVAILABLE': 'na',
}

_STATUS_LABELS = {
    'NOT_STARTED': 'Not Started', 'MISSING_DATA': 'Missing Data', 'IN_PROGRESS': 'In Progress',
    'REQUIRES_REVIEW': 'Requires Review', 'BLOCKED': 'Blocked', 'PENDING_APPROVAL': 'Pending Approval',
    'APPROVED_WITH_CONDITIONS': 'Approved (Conditions)', 'REJECTED': 'Rejected',
    'ACTIVE_MONITORING': 'Active Monitoring', 'OUTCOME_ESTIMATED': 'Outcome Estimated',
    'HUMAN_REVIEWED': 'Human Reviewed', 'VERIFIED': 'Verified', 'COMPLETE': 'Complete',
    'UNAVAILABLE': 'Not Available in This Release',
}


@dataclass
class WorkflowStage:
    key: str
    label: str
    status: str
    summary: str = ''
    action_label: str = ''
    action_url: Optional[str] = None
    blocked_reason: str = ''
    evidence_count: Optional[int] = None
    progress_current: Optional[int] = None
    progress_total: Optional[int] = None
    last_activity: Optional[Union[datetime, date]] = None
    is_available: bool = True

    @property
    def status_label(self):
        return _STATUS_LABELS.get(self.status, self.status.replace('_', ' ').title())

    @property
    def status_css(self):
        return _STATUS_CSS.get(self.status, 'na')

    @property
    def progress_label(self):
        if self.progress_current is not None and self.progress_total is not None:
            return f'{self.progress_current} of {self.progress_total}'
        return None


def _url(name, *args):
    try:
        return reverse(name, args=args)
    except Exception:
        return None


def _current_loss(project):
    """The most recently created OperationalLoss for this project — the
    vertical slice's flow is single-loss-at-a-time in practice; taking the
    latest is the same honest choice the monitoring page already makes
    implicitly by showing all decisions ordered by -created_at."""
    from waste_to_value_capital_allocation_engine.models import OperationalLoss
    return OperationalLoss.objects.filter(project=project.name).order_by('-created_at').first()


def _primary_decision(project):
    """The highest-ranked / most recent CapitalAllocationDecision for this
    project, reusing execution_monitoring's existing name-match query —
    never a second lookup mechanism."""
    return execution_monitoring.capital_decisions_for_project(project).first()


# feat/e2e-project-pipeline — the ONE ordered list of the 11 pipeline stages
# a reviewer walks through end-to-end (spec section 13's "suggested
# sections"). Every page in this journey renders this exact same list via
# templates/capital_guardian/_project_workflow_nav.html, so "what stage am I
# on and what's next" is answered identically everywhere — never a
# per-template ad hoc breadcrumb. This is presentation only: it resolves
# URLs from the SAME loss/decision _current_loss()/_primary_decision()
# already found elsewhere on this page; it stores no new state.
WORKFLOW_STAGE_KEYS = [
    'overview', 'investigation', 'evidence', 'interventions', 'better_way',
    'decision', 'capital_guardian', 'execution', 'outcome', 'evidence_memory',
    'observatory',
]


def build_project_workflow_nav(project, current_key, loss=None, decision=None):
    """
    Builds the 11-item project workflow nav for one project. `loss` and
    `decision` may be passed by callers that already resolved their own
    (e.g. a loss-scoped or decision-scoped page uses ITS OWN URL object,
    not a re-guessed one) — otherwise this falls back to the same
    _current_loss()/_primary_decision() helpers Command Centre uses, so
    "the current loss/decision" is never resolved two different ways.

    A stage with `available=False` renders with no href — never a link to
    a page that would immediately bounce/404 for lack of a loss or
    decision to scope to.
    """
    if loss is None:
        loss = _current_loss(project)
    if decision is None:
        decision = _primary_decision(project)
    has_interventions = loss is not None and loss.interventions.exists()

    items = [
        {'key': 'overview', 'label': 'Overview', 'available': True,
         'url': _url('capital_guardian:project_overview', project.slug)},
        {'key': 'investigation', 'label': 'Investigation', 'available': True,
         'url': _url('capital_guardian:investigation', project.slug)},
        {'key': 'evidence', 'label': 'Evidence', 'available': True,
         'url': _url('capital_guardian:evidence_centre', project.slug)},
        {'key': 'interventions', 'label': 'Interventions', 'available': loss is not None,
         'url': _url('capital_guardian:operational_loss_detail', project.slug, loss.pk) if loss is not None else None},
        {'key': 'better_way', 'label': 'Better Way', 'available': has_interventions,
         'url': _url('capital_guardian:better_way_view', project.slug, loss.pk) if has_interventions else None},
        {'key': 'decision', 'label': 'Decision', 'available': decision is not None,
         'url': _url('capital_guardian:human_decision_gate', project.slug, decision.pk) if decision is not None else None},
        {'key': 'capital_guardian', 'label': 'Capital Guardian', 'available': True,
         'url': _url('capital_guardian:governance', project.slug)},
        {'key': 'execution', 'label': 'Execution', 'available': True,
         'url': _url('capital_guardian:project_monitoring', project.slug)},
        {'key': 'outcome', 'label': 'Outcome', 'available': decision is not None,
         'url': _url('capital_guardian:record_outcome_confirm', project.slug, decision.pk) if decision is not None else None},
        {'key': 'evidence_memory', 'label': 'Evidence Memory', 'available': decision is not None,
         'url': (_url('capital_guardian:record_outcome_confirm', project.slug, decision.pk) + '#evidence-memory') if decision is not None else None},
        {'key': 'observatory', 'label': 'Observatory', 'available': True,
         'url': _url('ai_observatory:observatory', project.slug)},
    ]
    for item in items:
        item['is_current'] = item['key'] == current_key
    return items


def build_command_centre_context(project, user=None):
    """
    Returns one dict with every real, already-computed value the Command
    Centre template needs. Every sub-computation below is a direct call
    into an existing, unmodified service — see module docstring.

    feat/evidence-memory-hardening: `user` is the requesting user, passed
    through to the Evidence Memory retrieval policy — with no user (or a
    non-staff one) historical-evidence retrieval returns nothing rather
    than everything.
    """
    governance = getattr(project, 'governance', None)

    evidence_qs = list(evidence_service.evidence_for_project(project).select_related('reviewer'))
    evidence_summary = evidence_service.verification_summary(evidence_qs)
    evidence_rows = [
        {'evidence': e, 'related_label': evidence_service.related_object_label(e.source_reference)}
        for e in evidence_qs[:5]
    ]

    analysis = project_analysis.analyse_project(project)
    review = resource_purpose_review.review_resource_purpose(project, analysis)

    loss = _current_loss(project)
    interventions = list(loss.interventions.all()) if loss is not None else []

    safety_breakdown = None
    if interventions:
        from capital_guardian.services.better_way import extract_classification
        from capital_guardian.services.intervention_safety_gate import classify_intervention_safety
        safety_breakdown = {'eligible': 0, 'conditional': 0, 'blocked': 0}
        for option in interventions:
            classification = extract_classification(option.description)
            safety = classify_intervention_safety(project, option, classification=classification)
            safety_breakdown[safety['status']] += 1

    better_way_result = None
    if loss is not None and interventions:
        from capital_guardian.services.better_way import compare_interventions
        better_way_result = compare_interventions(project, loss)

    decision = _primary_decision(project)
    expected_vs_actual = execution_monitoring.expected_vs_actual(decision) if decision is not None else None

    learning_feedback = None
    if decision is not None:
        from capital_guardian.views import _learning_feedback_context
        learning_feedback = _learning_feedback_context(decision)

    capital_summary = execution_monitoring.capital_summary(project) if governance is not None else None
    recent_trace_entries = list(project.capital_trace_entries.order_by('-date')[:5]) if governance is not None else []
    milestones = list(project.timeline_milestones.all()) if governance is not None else []
    open_red_flags = list(project.red_flags.filter(resolution_status='open'))

    from evidence_memory.services.memory import retrieve_relevant_verified_outcomes
    relevant_outcomes = retrieve_relevant_verified_outcomes(project, user=user)
    memory_counts = _evidence_memory_counts(project)

    # feat/ai-observatory — latest real telemetry session for this project
    # only (never another project's), summarised in stage 13 and the
    # template's telemetry section; the Observatory page owns the detail.
    from ai_observatory.models import AnalysisSession
    latest_observatory_session = AnalysisSession.objects.filter(project=project).first()

    stages = _workflow_stages(
        project, evidence_qs, evidence_summary, analysis, review, loss, interventions, safety_breakdown,
        better_way_result, decision, governance, capital_summary, recent_trace_entries, milestones,
        learning_feedback, memory_counts,
    )
    next_action = _next_required_action(
        project, evidence_qs, review, loss, interventions, decision, governance,
        recent_trace_entries, milestones, learning_feedback,
    )

    started_stage_count = sum(1 for s in stages if s.is_available and s.status not in ('NOT_STARTED', 'MISSING_DATA'))
    available_stage_count = sum(1 for s in stages if s.is_available)

    return {
        'project': project,
        'governance': governance,
        'evidence_qs': evidence_qs,
        'evidence_summary': evidence_summary,
        'evidence_rows': evidence_rows,
        'analysis': analysis,
        'review': review,
        'loss': loss,
        'interventions': interventions,
        'safety_breakdown': safety_breakdown,
        'better_way_result': better_way_result,
        'decision': decision,
        'expected_vs_actual': expected_vs_actual,
        'learning_feedback': learning_feedback,
        'capital_summary': capital_summary,
        'recent_trace_entries': recent_trace_entries,
        'milestones': milestones,
        'open_red_flags': open_red_flags,
        'relevant_outcomes': relevant_outcomes,
        'memory_counts': memory_counts,
        'latest_observatory_session': latest_observatory_session,
        'stages': stages,
        'started_stage_count': started_stage_count,
        'available_stage_count': available_stage_count,
        'next_action': next_action,
    }


def _evidence_memory_counts(project):
    """
    feat/evidence-memory-hardening — honest, PROJECT-SCOPED Evidence Memory
    counts for the Command Centre stage. Counts only this project's own
    outcome-derived memory rows (via the structured project FK) plus its
    unresolved rows reachable through its own decisions' provenance links —
    never a platform-wide count, so no other project's volume of evidence
    leaks through this page.
    """
    from evidence_memory.models import EvidenceMemory

    own = EvidenceMemory.objects.filter(project=project, source_reference__startswith=_OUTCOME_PREFIX)
    # Unresolved rows have no project FK by definition; reach them through
    # this project's own decisions so a genuinely unattributable row (whose
    # decision matched nothing) is never claimed by anyone's count.
    unresolved = EvidenceMemory.objects.filter(
        visibility='restricted_unresolved',
        originating_decision__project=project.name,
        source_reference__startswith=_OUTCOME_PREFIX,
    )
    return {
        'total': own.count(),
        'verified': own.filter(verification_status='verified').count(),
        'human_reviewed': own.filter(review_tier='human_reviewed').count(),
        'demo': own.filter(is_demo=True).count(),
        'shared': own.filter(visibility__in=('platform_learning_demo', 'platform_learning_verified', 'organisation_shared')).count(),
        'unresolved': unresolved.count(),
    }


_OUTCOME_PREFIX = 'waste_to_value_capital_allocation_engine.VerifiedCapitalOutcome:'


def _workflow_stages(project, evidence_qs, evidence_summary, analysis, review, loss, interventions,
                      safety_breakdown, better_way_result, decision, governance, capital_summary,
                      recent_trace_entries, milestones, learning_feedback, memory_counts=None):
    stages = []

    # 1. Project — identity completeness, not a sequential "step". Never
    # NOT_STARTED (the project exists by definition on this page); shows
    # MISSING_DATA when core identity fields are genuinely unset, and folds
    # in the Mizan project-analysis score (see module docstring's "Analysis"
    # note) as supporting detail rather than a redundant stage.
    missing_identity = []
    if not project.country_id:
        missing_identity.append('country')
    if not project.region:
        missing_identity.append('region')
    status = 'MISSING_DATA' if missing_identity else 'COMPLETE'
    summary = (
        f"Missing: {', '.join(missing_identity)}." if missing_identity
        else f'{project.get_status_display()} · {project.country.name}.'
    )
    if evidence_qs:
        summary += f' Mizan score {analysis.final_mizan_score:.1f} ({analysis.mizan_label}).'
    stages.append(WorkflowStage(
        key='project', label='Project', status=status, summary=summary,
        action_label='View Project Dashboard',
        action_url=_url('capital_guardian:investor_dashboard', project.slug),
        last_activity=project.updated_at,
    ))

    # 2. Evidence — the one and only stage that shows the project-level
    # EvidenceMemory count (see module docstring / founder instruction:
    # never repeat this same total against every other stage).
    verified_evidence_count = evidence_summary['by_status'].get('verified', 0)
    if not evidence_qs:
        status = 'NOT_STARTED'
        summary = 'No evidence recorded for this project yet.'
    elif verified_evidence_count == 0:
        status = 'IN_PROGRESS'
        summary = f"{evidence_summary['total']} evidence item(s) recorded; none independently verified yet."
    else:
        status = 'COMPLETE'
        summary = f"{verified_evidence_count} of {evidence_summary['total']} evidence item(s) verified."
    last_activity = max((e.updated_at for e in evidence_qs), default=None)
    stages.append(WorkflowStage(
        key='evidence', label='Evidence', status=status, summary=summary,
        action_label='Add Evidence' if not evidence_qs else 'Open Evidence Centre',
        action_url=_url('capital_guardian:evidence_centre', project.slug),
        evidence_count=evidence_summary['total'],
        progress_current=verified_evidence_count if evidence_qs else None,
        progress_total=evidence_summary['total'] if evidence_qs else None,
        last_activity=last_activity,
    ))

    # 3. Resource Purpose Review
    review_evidence_count = len(review.evidence_used) if review.has_reviewed_profile else None
    gaps = len(review.evidence_gaps)
    # Denominator is "real evidence items used" + "categories still missing"
    # — both are real, already-computed lists (evidence_used, evidence_gaps).
    # Only shown once evidence_used is non-empty, so this never presents a
    # 0-of-0 as if it were a real measurement.
    progress_current = review_evidence_count if review_evidence_count else None
    progress_total = (review_evidence_count + gaps) if review_evidence_count else None
    if not review.has_reviewed_profile:
        status = 'NOT_STARTED'
        summary = 'No reviewed resource-purpose profile exists yet for this project.'
    elif loss is not None:
        status = 'COMPLETE'
        summary = f'Reviewed. {gaps} evidence gap(s) noted.' if gaps else 'Reviewed. No evidence gaps noted.'
    elif review.misuse_or_value_loss_condition_exists:
        status = 'REQUIRES_REVIEW'
        summary = 'A potential value-loss condition is indicated — human confirmation required before creating a loss record.'
    else:
        status = 'IN_PROGRESS'
        summary = 'Reviewed; no clear value-loss condition indicated yet.'
    stages.append(WorkflowStage(
        key='resource_purpose', label='Resource Purpose Review', status=status, summary=summary,
        action_label='Open Evidence Centre', action_url=_url('capital_guardian:evidence_centre', project.slug),
        evidence_count=review_evidence_count,
        progress_current=progress_current, progress_total=progress_total,
    ))

    # 4. Baseline / Operational Loss
    if loss is None:
        status = 'NOT_STARTED'
        summary = 'No operational loss recorded for this project yet.'
    else:
        status = 'COMPLETE'
        summary = f'{loss.title} — {loss.get_evidence_quality_display()} evidence quality.'
    stages.append(WorkflowStage(
        key='value_loss', label='Baseline / Operational Loss', status=status, summary=summary,
        action_label='View Operational Loss' if loss is not None else 'Create Value Loss Record',
        action_url=(
            _url('capital_guardian:operational_loss_detail', project.slug, loss.pk) if loss is not None
            else _url('capital_guardian:create_value_loss_confirm', project.slug)
        ),
        last_activity=loss.updated_at if loss is not None else None,
    ))

    # 5. Intervention Options — carries the safety/eligibility breakdown as
    # a sub-detail (see module docstring's "Safety/Eligibility" note) rather
    # than as its own top-level stage with nothing of its own to link to.
    if loss is None:
        status = 'NOT_STARTED'
        summary = 'No operational loss to attach intervention options to yet.'
    elif not interventions:
        status = 'NOT_STARTED'
        summary = 'No intervention options created yet.'
    elif safety_breakdown['eligible'] == 0:
        status = 'BLOCKED'
        summary = f"{len(interventions)} option(s) created; none currently eligible."
    else:
        status = 'COMPLETE'
        summary = f"{len(interventions)} option(s): {safety_breakdown['eligible']} eligible, {safety_breakdown['conditional']} conditional, {safety_breakdown['blocked']} blocked."
    blocked_reason = ''
    if safety_breakdown and safety_breakdown['eligible'] == 0 and interventions:
        blocked_reason = 'All current options are conditional or blocked on safety/eligibility grounds — see Resource Purpose Review.'
    stages.append(WorkflowStage(
        key='intervention_options', label='Intervention Options', status=status, summary=summary,
        action_label='Add Intervention Option' if loss is not None else 'Create Baseline First',
        action_url=(
            _url('capital_guardian:operational_loss_detail', project.slug, loss.pk) if loss is not None else None
        ),
        blocked_reason=blocked_reason,
        progress_current=safety_breakdown['eligible'] if safety_breakdown else None,
        progress_total=len(interventions) if interventions else None,
    ))

    # 6. The Better Way
    if loss is None or not interventions:
        status = 'NOT_STARTED'
        summary = 'Needs at least one intervention option before a comparison can run.'
    elif decision is not None:
        status = 'COMPLETE'
        summary = 'Comparison complete; a capital decision has been created from it.'
    else:
        status = 'IN_PROGRESS'
        top = better_way_result.ranked[0] if better_way_result and better_way_result.ranked else None
        summary = f'{len(interventions)} option(s) compared.' + (f' Top-ranked: {top["option"].title}.' if top else '')
    stages.append(WorkflowStage(
        key='better_way', label='The Better Way', status=status, summary=summary,
        action_label='Compare Options',
        action_url=_url('capital_guardian:operational_loss_detail', project.slug, loss.pk) if loss is not None else None,
    ))

    # 7. Capital Decision (existence, independent of its approval state)
    status = 'COMPLETE' if decision is not None else 'NOT_STARTED'
    summary = f'{decision.intervention.title} selected.' if decision is not None else 'No capital allocation decision created yet.'
    stages.append(WorkflowStage(
        key='capital_decision', label='Capital Allocation Decision', status=status, summary=summary,
        action_label='View Capital Decision' if decision is not None else 'Compare Options First',
        action_url=_url('waste_to_value_capital_allocation_engine:decision_detail', decision.pk) if decision is not None else None,
        last_activity=decision.created_at if decision is not None else None,
    ))

    # 8. Human Approval — deliberately distinct from Capital Decision (see
    # module docstring). feat/human-decision-gate: this stage now links to
    # the real Human Decision Gate review page
    # (capital_guardian:human_decision_gate) instead of a raw Django admin
    # edit, and surfaces the latest DecisionReviewEvent — reviewer,
    # reviewed-date, rationale — when one exists. Admin remains available
    # as an emergency fallback only (see that app's admin.py); it is no
    # longer the primary or labelled workflow here.
    approval_display = {
        'pending': 'PENDING_APPROVAL', 'approved': 'COMPLETE',
        'approved_with_conditions': 'APPROVED_WITH_CONDITIONS', 'rejected': 'REJECTED',
        'evidence_requested': 'BLOCKED', 'modification_requested': 'BLOCKED',
    }
    status = approval_display.get(decision.approval_status, 'NOT_STARTED') if decision is not None else 'NOT_STARTED'
    latest_review = decision.review_events.select_related('actor').first() if decision is not None else None
    blocked_reason = ''
    if decision is None:
        summary = 'No decision awaiting approval yet.'
    elif decision.approval_status == 'pending':
        summary = 'Awaiting first human review.' if latest_review is None else 'Resubmitted — awaiting re-review.'
    elif latest_review is not None:
        reviewer = latest_review.actor.get_username() if latest_review.actor else 'Unknown reviewer'
        summary = f'{decision.get_approval_status_display()} by {reviewer} on {latest_review.created_at:%Y-%m-%d}.'
        if latest_review.notes:
            summary += f' Rationale: {latest_review.notes[:120]}'
    else:
        summary = f'{decision.get_approval_status_display()}.'
    if decision is not None and decision.approval_status in ('evidence_requested', 'modification_requested'):
        blocked_reason = f'{decision.get_approval_status_display()} — awaiting resubmission before this can proceed.'
    if decision is None:
        action_label, review_url = '', None
    else:
        from capital_guardian.services import human_decision_gate
        review_url = _url('capital_guardian:human_decision_gate', project.slug, decision.pk)
        action_label = 'Open Human Decision Gate' if human_decision_gate.legal_actions_for(decision) else 'View Decision Review'
    stages.append(WorkflowStage(
        key='human_approval', label='Human Approval', status=status, summary=summary,
        action_label=action_label,
        action_url=review_url,
        blocked_reason=blocked_reason,
        last_activity=latest_review.created_at if latest_review is not None else None,
        is_available=True,
    ))

    # 9. Capital Guardian
    status = 'ACTIVE_MONITORING' if governance is not None else 'NOT_STARTED'
    summary = 'Governance record active.' if governance is not None else 'Not yet promoted to Capital Guardian.'
    stages.append(WorkflowStage(
        key='capital_guardian', label='Capital Guardian', status=status, summary=summary,
        action_label='View Governance' if governance is not None else 'Promote to Capital Guardian',
        action_url=(
            _url('capital_guardian:governance', project.slug) if governance is not None
            else (_url('waste_to_value_capital_allocation_engine:decision_detail', decision.pk) if decision is not None else None)
        ),
        last_activity=governance.updated_at if governance is not None else None,
    ))

    # 10. Execution — CapitalTraceEntry + milestone monitoring data.
    has_monitoring_data = bool(recent_trace_entries or milestones)
    complete_milestones = sum(1 for m in milestones if m.status == 'complete') if milestones else None
    if governance is None:
        status = 'NOT_STARTED'
        summary = 'Not yet under active monitoring.'
    elif has_monitoring_data:
        status = 'ACTIVE_MONITORING'
        summary = f'{len(recent_trace_entries)} recent capital trace entr(y/ies), {len(milestones)} milestone(s).'
    else:
        status = 'IN_PROGRESS'
        summary = 'Under Capital Guardian governance; no monitoring data recorded yet.'
    last_activity = recent_trace_entries[0].date if recent_trace_entries else None
    stages.append(WorkflowStage(
        key='monitoring', label='Execution', status=status, summary=summary,
        action_label='Open Monitoring' if governance is not None else 'Promote to Capital Guardian First',
        action_url=_url('capital_guardian:project_monitoring', project.slug) if governance is not None else None,
        progress_current=complete_milestones, progress_total=len(milestones) if milestones else None,
        last_activity=last_activity,
    ))

    # 11. Outcome
    outcome = learning_feedback.get('outcome') if learning_feedback and learning_feedback.get('outcome_exists') else None
    if outcome is None:
        status = 'NOT_STARTED'
        summary = 'No outcome recorded for this project yet.'
    elif outcome.verified_status == 'verified':
        status = 'VERIFIED'
        summary = 'Independently verified.'
    elif '[Reviewer note]' in (outcome.next_capital_allocation_signal or ''):
        status = 'HUMAN_REVIEWED'
        summary = 'Human-reviewed — not independently verified.'
    else:
        status = 'OUTCOME_ESTIMATED'
        summary = 'Estimated outcome recorded — not yet reviewed.'
    stages.append(WorkflowStage(
        key='outcome', label='Outcome', status=status, summary=summary,
        action_label='Record Outcome' if decision is not None else 'Create Capital Decision First',
        action_url=_url('capital_guardian:record_outcome_confirm', project.slug, decision.pk) if decision is not None else None,
    ))

    # 12. Evidence Memory (sync + retrieval for future decisions).
    # feat/evidence-memory-hardening: the summary now reports honest,
    # project-scoped counts (verified / human-reviewed / demo / shared /
    # unresolved) from _evidence_memory_counts() — never platform-wide
    # totals, so no other project's evidence volume leaks through here.
    counts = memory_counts or {}
    if outcome is None:
        status = 'NOT_STARTED'
        summary = 'No outcome to sync into Evidence Memory yet.'
    elif learning_feedback.get('already_synced'):
        status = 'COMPLETE'
        summary = (
            f"{counts.get('total', 0)} memory record(s) for this project: "
            f"{counts.get('verified', 0)} verified, {counts.get('human_reviewed', 0)} human-reviewed, "
            f"{counts.get('demo', 0)} demo, {counts.get('shared', 0)} shared for learning."
        )
    else:
        status = 'IN_PROGRESS'
        summary = 'Outcome recorded; not yet synced into Evidence Memory.'
    blocked_reason = ''
    if counts.get('unresolved'):
        blocked_reason = (
            f"{counts['unresolved']} record(s) have unresolved project provenance and are "
            f"restricted from all cross-project retrieval until manually reviewed."
        )
    memory = learning_feedback.get('memory') if learning_feedback else None
    stages.append(WorkflowStage(
        key='learning', label='Evidence Memory', status=status, summary=summary,
        action_label='Sync to Evidence Memory' if outcome is not None else 'Record Outcome First',
        action_url=_url('capital_guardian:record_outcome_confirm', project.slug, decision.pk) if decision is not None else None,
        blocked_reason=blocked_reason,
        progress_current=counts.get('verified') if counts.get('total') else None,
        progress_total=counts.get('total') or None,
        last_activity=memory.created_at if memory is not None else None,
    ))

    # 13. Sustainable AI Telemetry — feat/ai-observatory: real now, backed
    # by ai_observatory.AnalysisSession rows (see module docstring). This
    # stage only SUMMARISES the latest session and links to the Observatory,
    # which owns the detail — no dashboard content is duplicated here.
    from ai_observatory.models import AnalysisSession

    latest_session = AnalysisSession.objects.filter(project=project).first()
    session_count = AnalysisSession.objects.filter(project=project).count()
    if latest_session is None:
        status = 'NOT_STARTED'
        summary = 'No telemetry sessions recorded yet — run a project analysis to record one.'
    else:
        status = 'ACTIVE_MONITORING'
        det_ratio = latest_session.deterministic_step_ratio
        summary = (
            f'{session_count} session(s) recorded. Latest: {latest_session.get_kind_display()} '
            f'({latest_session.get_status_display()}, {latest_session.model_call_count} model call(s)'
            + (f', deterministic ratio {det_ratio}' if det_ratio is not None else '')
            + ').'
        )
    telemetry_blocked_reason = ''
    if latest_session is not None and latest_session.warnings:
        telemetry_blocked_reason = f'{len(latest_session.warnings)} warning(s) on the latest session — see Observatory.'
    stages.append(WorkflowStage(
        key='telemetry', label='Sustainable AI Telemetry', status=status,
        summary=summary,
        action_label='Open Observatory',
        action_url=_url('ai_observatory:observatory', project.slug),
        blocked_reason=telemetry_blocked_reason,
        last_activity=latest_session.started_at if latest_session is not None else None,
        is_available=True,
    ))

    return stages


def _next_required_action(project, evidence_qs, review, loss, interventions, decision, governance,
                           recent_trace_entries, milestones, learning_feedback):
    """Deterministic — walks the exact same real workflow state used by
    _workflow_stages() above and returns the single next honest human
    action. Never executes anything; only points at an existing page."""
    if not evidence_qs:
        return {'label': 'ADD PROJECT EVIDENCE', 'url': _url('capital_guardian:evidence_centre', project.slug)}

    if loss is None:
        if review.has_reviewed_profile and review.misuse_or_value_loss_condition_exists:
            return {'label': 'CREATE HUMAN-REVIEWED VALUE LOSS', 'url': _url('capital_guardian:create_value_loss_confirm', project.slug)}
        return {'label': 'RUN PROJECT ANALYSIS', 'url': _url('capital_guardian:evidence_centre', project.slug)}

    if not interventions:
        return {'label': 'CREATE INTERVENTION OPTIONS', 'url': _url('capital_guardian:operational_loss_detail', project.slug, loss.pk)}

    if decision is None:
        return {'label': 'COMPARE THE BETTER WAY', 'url': _url('capital_guardian:operational_loss_detail', project.slug, loss.pk)}

    if decision.approval_status in ('pending', 'evidence_requested', 'modification_requested'):
        return {'label': 'REVIEW CAPITAL DECISION', 'url': _url('capital_guardian:human_decision_gate', project.slug, decision.pk)}

    if decision.approval_status == 'rejected':
        return {'label': 'COMPARE THE BETTER WAY', 'url': _url('capital_guardian:operational_loss_detail', project.slug, loss.pk)}

    if governance is None:
        return {'label': 'PROMOTE TO CAPITAL GUARDIAN', 'url': _url('waste_to_value_capital_allocation_engine:decision_detail', decision.pk)}

    if not (recent_trace_entries or milestones):
        return {'label': 'ADD MONITORING DATA', 'url': _url('capital_guardian:project_monitoring', project.slug)}

    outcome_exists = bool(learning_feedback and learning_feedback.get('outcome_exists'))
    if not outcome_exists:
        return {'label': 'RECORD OUTCOME', 'url': _url('capital_guardian:record_outcome_confirm', project.slug, decision.pk)}

    if not learning_feedback.get('already_synced'):
        return {'label': 'ADD OUTCOME TO EVIDENCE MEMORY', 'url': _url('capital_guardian:record_outcome_confirm', project.slug, decision.pk)}

    return {'label': 'CONTINUE MONITORING', 'url': _url('capital_guardian:project_monitoring', project.slug)}
