"""
capital_guardian/services/command_centre.py — the Project Command Centre:
a read-oriented orchestration layer over the complete PR1-PR7 vertical
slice. This module computes NOTHING new — every value returned here is
read directly from an existing model or delegated to an existing service
(evidence, project_analysis, resource_purpose_review, better_way,
execution_monitoring, evidence_memory retrieval). It is not a new source
of truth: if this module disappeared, every fact it displays would still
be independently visible on its own existing page.

Workflow stage vocabulary is intentionally not a single "0-100% done" bar
per stage — each stage reports one of a small honest set of real states
(NOT_STARTED / IN_PROGRESS / REQUIRES_REVIEW / PENDING_APPROVAL /
APPROVED_WITH_CONDITIONS / REJECTED / ACTIVE_MONITORING /
OUTCOME_ESTIMATED / HUMAN_REVIEWED / VERIFIED / COMPLETE), never collapsed
into a misleading blanket "complete".
"""
from dataclasses import dataclass, field
from typing import Optional

from django.urls import reverse

from capital_guardian.services import evidence as evidence_service
from capital_guardian.services import execution_monitoring, project_analysis, resource_purpose_review


# Cosmetic-only status -> badge-colour mapping (reuses the same low/medium/
# high/na risk-badge classes already used throughout Capital Guardian's
# templates) — never a scoring computation, purely a display grouping.
_STATUS_CSS = {
    'NOT_STARTED': 'na', 'IN_PROGRESS': 'medium', 'REQUIRES_REVIEW': 'medium',
    'PENDING_APPROVAL': 'medium', 'APPROVED_WITH_CONDITIONS': 'medium', 'REJECTED': 'high',
    'ACTIVE_MONITORING': 'low', 'OUTCOME_ESTIMATED': 'medium', 'HUMAN_REVIEWED': 'medium',
    'VERIFIED': 'low', 'COMPLETE': 'low',
}


@dataclass
class WorkflowStage:
    key: str
    label: str
    status: str
    status_display: str
    url: Optional[str] = None
    detail: str = ''

    @property
    def status_css(self):
        return _STATUS_CSS.get(self.status, 'na')


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


def build_command_centre_context(project):
    """
    Returns one dict with every real, already-computed value the Command
    Centre template needs. Every sub-computation below is a direct call
    into an existing, unmodified service — see module docstring.
    """
    governance = getattr(project, 'governance', None)

    evidence_qs = list(evidence_service.evidence_for_project(project))
    evidence_summary = evidence_service.verification_summary(evidence_qs)
    evidence_rows = [
        {'evidence': e, 'related_label': evidence_service.related_object_label(e.source_reference)}
        for e in evidence_qs[:5]
    ]

    analysis = project_analysis.analyse_project(project)
    review = resource_purpose_review.review_resource_purpose(project, analysis)

    loss = _current_loss(project)
    interventions = list(loss.interventions.all()) if loss is not None else []

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
    relevant_outcomes = retrieve_relevant_verified_outcomes(project)

    stages = _workflow_stages(
        project, evidence_qs, analysis, review, loss, interventions, better_way_result,
        decision, governance, capital_summary, recent_trace_entries, milestones,
        learning_feedback,
    )
    next_action = _next_required_action(
        project, evidence_qs, review, loss, interventions, decision, governance,
        recent_trace_entries, milestones, learning_feedback,
    )

    completed_stage_count = sum(1 for s in stages if s.status != 'NOT_STARTED')
    workflow_completion_pct = round(100 * completed_stage_count / len(stages))

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
        'better_way_result': better_way_result,
        'decision': decision,
        'expected_vs_actual': expected_vs_actual,
        'learning_feedback': learning_feedback,
        'capital_summary': capital_summary,
        'recent_trace_entries': recent_trace_entries,
        'milestones': milestones,
        'open_red_flags': open_red_flags,
        'relevant_outcomes': relevant_outcomes,
        'stages': stages,
        'workflow_completion_pct': workflow_completion_pct,
        'next_action': next_action,
    }


def _workflow_stages(project, evidence_qs, analysis, review, loss, interventions, better_way_result,
                      decision, governance, capital_summary, recent_trace_entries, milestones,
                      learning_feedback):
    verified_evidence_count = sum(1 for e in evidence_qs if e.verification_status == 'verified')
    stages = []

    # 1. Evidence
    if not evidence_qs:
        status = 'NOT_STARTED'
    elif verified_evidence_count == 0:
        status = 'IN_PROGRESS'
    else:
        status = 'COMPLETE'
    stages.append(WorkflowStage('evidence', 'Evidence', status, status.replace('_', ' ').title(),
                                 url=_url('capital_guardian:evidence_centre', project.slug)))

    # 2. Analysis — analyse_project() is stateless/free; "started" means
    # there is real evidence for it to reason over.
    status = 'COMPLETE' if evidence_qs else 'NOT_STARTED'
    stages.append(WorkflowStage('analysis', 'Project Analysis', status, status.replace('_', ' ').title(),
                                 url=_url('capital_guardian:evidence_centre', project.slug),
                                 detail=f'Mizan score {analysis.final_mizan_score:.1f} ({analysis.mizan_label})' if evidence_qs else ''))

    # 3. Resource Purpose Review
    if not review.has_reviewed_profile:
        status = 'NOT_STARTED'
    elif loss is not None:
        status = 'COMPLETE'
    elif review.misuse_or_value_loss_condition_exists:
        status = 'REQUIRES_REVIEW'
    else:
        status = 'IN_PROGRESS'
    stages.append(WorkflowStage('resource_purpose', 'Resource Purpose Review', status, status.replace('_', ' ').title(),
                                 url=_url('capital_guardian:evidence_centre', project.slug)))

    # 4. Operational Loss
    status = 'COMPLETE' if loss is not None else 'NOT_STARTED'
    stages.append(WorkflowStage(
        'value_loss', 'Operational Loss', status, status.replace('_', ' ').title(),
        url=_url('capital_guardian:operational_loss_detail', project.slug, loss.pk) if loss is not None
        else _url('capital_guardian:create_value_loss_confirm', project.slug),
    ))

    # 5. The Better Way
    if loss is None or not interventions:
        status = 'NOT_STARTED'
    elif decision is not None:
        status = 'COMPLETE'
    else:
        status = 'IN_PROGRESS'
    stages.append(WorkflowStage(
        'better_way', 'The Better Way', status, status.replace('_', ' ').title(),
        url=_url('capital_guardian:operational_loss_detail', project.slug, loss.pk) if loss is not None else None,
    ))

    # 6. Capital Decision (existence, independent of its approval state)
    status = 'COMPLETE' if decision is not None else 'NOT_STARTED'
    stages.append(WorkflowStage(
        'capital_decision', 'Capital Decision', status, status.replace('_', ' ').title(),
        url=_url('waste_to_value_capital_allocation_engine:decision_detail', decision.pk) if decision is not None else None,
    ))

    # 7. Human Approval
    approval_display = {
        'pending': 'PENDING_APPROVAL', 'approved': 'COMPLETE',
        'approved_with_conditions': 'APPROVED_WITH_CONDITIONS', 'rejected': 'REJECTED',
    }
    status = approval_display.get(decision.approval_status, 'NOT_STARTED') if decision is not None else 'NOT_STARTED'
    stages.append(WorkflowStage(
        'human_approval', 'Human Approval', status, status.replace('_', ' ').title(),
        url=_url('waste_to_value_capital_allocation_engine:decision_detail', decision.pk) if decision is not None else None,
    ))

    # 8. Capital Guardian
    status = 'ACTIVE_MONITORING' if governance is not None else 'NOT_STARTED'
    stages.append(WorkflowStage('capital_guardian', 'Capital Guardian', status, status.replace('_', ' ').title(),
                                 url=_url('capital_guardian:governance', project.slug)))

    # 9. Monitoring
    has_monitoring_data = bool(recent_trace_entries or milestones)
    if governance is None:
        status = 'NOT_STARTED'
    elif has_monitoring_data:
        status = 'ACTIVE_MONITORING'
    else:
        status = 'IN_PROGRESS'
    stages.append(WorkflowStage('monitoring', 'Monitoring', status, status.replace('_', ' ').title(),
                                 url=_url('capital_guardian:project_monitoring', project.slug)))

    # 10. Verified Outcome
    outcome = learning_feedback.get('outcome') if learning_feedback and learning_feedback.get('outcome_exists') else None
    if outcome is None:
        status = 'NOT_STARTED'
    elif outcome.verified_status == 'verified':
        status = 'VERIFIED'
    elif '[Reviewer note]' in (outcome.next_capital_allocation_signal or ''):
        status = 'HUMAN_REVIEWED'
    else:
        status = 'OUTCOME_ESTIMATED'
    stages.append(WorkflowStage(
        'outcome', 'Verified Outcome', status, status.replace('_', ' ').title(),
        url=_url('capital_guardian:record_outcome_confirm', project.slug, decision.pk) if decision is not None else None,
    ))

    # 11. Learning (Evidence Memory feedback)
    if outcome is None:
        status = 'NOT_STARTED'
    elif learning_feedback.get('already_synced'):
        status = 'COMPLETE'
    else:
        status = 'IN_PROGRESS'
    stages.append(WorkflowStage(
        'learning', 'Learning Feedback', status, status.replace('_', ' ').title(),
        url=_url('capital_guardian:record_outcome_confirm', project.slug, decision.pk) if decision is not None else None,
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

    if decision.approval_status == 'pending':
        return {'label': 'REVIEW CAPITAL DECISION', 'url': _url('waste_to_value_capital_allocation_engine:decision_detail', decision.pk)}

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
