"""Paid movement without evidence → task → internal request → score → review.

Each local transition and audit event commit together. External delivery is
not enabled: it needs a transactional outbox and destination idempotency.
"""
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from ai_observatory.models import AnalysisSession
from ai_observatory.services.governance import record_event, session_trace
from capital_guardian.models import RiskFollowUp
from capital_guardian.services.capital_protection import compute_capital_protection_score
from capital_guardian.services.red_flag_engine import detect_red_flags
from evidence_memory.models import EvidenceMemory
from evidence_memory.services.citations import capture_citation, resolve_citation, payload_digest
from evidence_memory.services.retrieval_policy import is_record_accessible
from gold_intelligence.access import require, READ, ANALYSE, APPROVE
from gold_intelligence.models import GoldProject

MAX_ATTEMPTS = 3


def _event(task, key, event, user, **metadata):
    return record_event(task.session, key, event, actor=user, metadata={'task_id': task.pk, **metadata})


@transaction.atomic
def start_followup(project, user, rule_key):
    require(user, project, ANALYSE)
    project = GoldProject.objects.select_for_update().get(pk=project.pk)
    existing = RiskFollowUp.objects.filter(project=project, rule_key=rule_key).order_by('-pk').first()
    if existing:
        return existing
    flag = next((f for f in detect_red_flags(project) if f.rule_key == rule_key and f.resolution_status == 'open'), None)
    if flag is None or not flag.rule_key.startswith('evidence_missing_') or not flag.related_trace_entry_id:
        raise ValueError('This workflow requires a detected paid-movement-without-evidence risk.')
    snapshot = {field: getattr(flag, field) for field in (
        'rule_key', 'description', 'severity', 'actual_value', 'threshold_value',
        'recommended_action', 'related_trace_entry_id', 'is_demo')}
    fingerprint = payload_digest(snapshot)
    session = AnalysisSession.objects.create(project=project, user=user, kind='other')
    task = RiskFollowUp.objects.create(project=project, session=session, created_by=user, rule_key=rule_key,
                                      risk_snapshot=snapshot, trigger_digest=fingerprint,
                                      document_request=flag.recommended_action)
    _event(task, 'risk', 'risk_detected', user, rule_key=rule_key, trigger_digest=fingerprint)
    _event(task, 'task', 'task_created', user)
    _event(task, 'request', 'document_requested', user, delivery='internal_project_task', sent_externally=False)
    return task


def _load(task_id, project, user, permission):
    require(user, project, permission)
    GoldProject.objects.select_for_update().get(pk=project.pk)
    return RiskFollowUp.objects.select_for_update().select_related('session', 'project').get(pk=task_id, project=project)


def _usable_citation(task, user):
    EvidenceMemory.objects.select_for_update().get(pk=task.citation['memory_id'])
    citation = resolve_citation(task.citation, user=user, project=task.project)
    if citation['source_changed'] or citation['expired'] or citation['is_demo']:
        raise ValueError('Evidence changed, expired or is demonstration material; submit a current source.')
    return citation


def _assessment_digest(task, score):
    return payload_digest({'score': score, 'source': task.citation['snapshot_sha256'],
                           'trigger': task.trigger_digest, 'document_revision': task.document_revision})


@transaction.atomic
def submit_document(task_id, project, user, memory_id):
    task = _load(task_id, project, user, ANALYSE)
    memory = EvidenceMemory.objects.select_for_update().get(pk=memory_id, project=project)
    if not is_record_accessible(memory, project, user) or memory.is_expired or memory.is_demo:
        raise PermissionDenied('A current, accessible project source is required.')
    expected_ref = f'capital_guardian.CapitalTraceEntry:{task.risk_snapshot["related_trace_entry_id"]}'
    if memory.source_reference != expected_ref:
        raise ValueError('Document must be attached to the capital movement that triggered this task.')
    citation = capture_citation(memory)
    if task.citation == citation:
        return task
    if task.state in ('approved', 'rejected'):
        raise ValueError('Reviewed tasks cannot be changed.')
    if task.attempts >= MAX_ATTEMPTS:
        raise ValueError('Retry budget exhausted; investigate the recorded failure.')
    task.citation, task.submitted_by = citation, user
    task.document_revision += 1
    task.state, task.score_snapshot, task.assessment_digest, task.last_error = 'ready', {}, '', ''
    task.save()
    _event(task, f'document:{task.document_revision}', 'document_received', user,
           snapshot_id=citation['snapshot_id'], snapshot_sha256=citation['snapshot_sha256'], memory_id=memory.pk)
    return task


@transaction.atomic
def advance(task_id, project, user):
    task = _load(task_id, project, user, ANALYSE)
    if task.state in ('awaiting_document', 'awaiting_approval', 'approved', 'rejected'):
        return task
    if task.attempts >= MAX_ATTEMPTS:
        raise ValueError('Retry budget exhausted; investigate the recorded failure.')
    _usable_citation(task, user)
    task.attempts += 1
    _event(task, f'attempt:{task.attempts}', 'tool_started', user,
           tool='capital_guardian.compute_capital_protection_score', attempt=task.attempts)
    try:
        with transaction.atomic():
            detect_red_flags(project)
            score = compute_capital_protection_score(project)
            digest = _assessment_digest(task, score)
            _event(task, f'score:{task.attempts}', 'score_recalculated', user, assessment_digest=digest,
                   available=score['available'], score=score['score'])
    except Exception as exc:
        # Exception text may contain credentials; record only its type.
        task.state, task.last_error = 'failed', type(exc).__name__
        _event(task, f'failure:{task.attempts}', 'tool_failed', user, error_type=task.last_error, attempt=task.attempts)
        task.save()
        return task
    task.score_snapshot, task.assessment_digest = score, digest
    task.state, task.last_error = 'awaiting_approval', ''
    task.save()
    _event(task, f'approval-request:{task.attempts}', 'human_approval_requested', user, assessment_digest=digest)
    return task


@transaction.atomic
def review(task_id, project, user, decision, assessment_digest, notes):
    task = _load(task_id, project, user, APPROVE)
    if decision not in ('approved', 'rejected') or not isinstance(notes, str) or not notes.strip():
        raise ValueError('An explicit approve/reject decision and rationale are required.')
    if user.pk in (task.created_by_id, task.submitted_by_id):
        raise PermissionDenied('A different project reviewer must review this assessment.')
    if task.state in ('approved', 'rejected'):
        if (task.state, task.reviewed_by_id, task.assessment_digest, task.review_notes) == (decision, user.pk, assessment_digest, notes.strip()):
            return task
        raise ValueError('This task already has a different final review.')
    if task.state != 'awaiting_approval' or assessment_digest != task.assessment_digest:
        raise ValueError('Review requires the exact current assessment version.')
    _usable_citation(task, user)
    detect_red_flags(project)
    if _assessment_digest(task, compute_capital_protection_score(project)) != assessment_digest:
        raise ValueError('Project inputs changed; recalculate before review.')
    task.state, task.reviewed_by, task.review_notes = decision, user, notes.strip()
    task.reviewed_at = timezone.now()
    task.save()
    _event(task, 'review', 'human_review_recorded', user, decision=decision,
           assessment_digest=assessment_digest, rationale=notes.strip())
    task.session.status, task.session.finished_at = 'completed', timezone.now()
    task.session.human_review_completed = True
    task.session.final_recommendation_status = 'recorded' if decision == 'approved' else 'blocked'
    task.session.save()
    return task


@transaction.atomic
def recalculate(task_id, project, user):
    task = _load(task_id, project, user, ANALYSE)
    if task.state == 'awaiting_approval':
        _usable_citation(task, user)
        detect_red_flags(project)
        if _assessment_digest(task, compute_capital_protection_score(project)) == task.assessment_digest:
            return task
        task.state = 'ready'
        task.save(update_fields=['state', 'updated_at'])
    return advance(task_id, project, user)


def task_detail(task, user):
    require(user, task.project, READ)
    result = {'id': task.pk, 'state': task.state, 'risk': task.risk_snapshot,
              'document_request': task.document_request, 'attempts': task.attempts,
              'last_error': task.last_error, 'assessment_digest': task.assessment_digest,
              'score': task.score_snapshot, 'citation': None, 'reviewed_by': task.reviewed_by_id,
              'review_notes': task.review_notes, 'trace': session_trace(task.session)}
    if task.citation:
        try:
            result['citation'] = resolve_citation(task.citation, user=user, project=task.project)
        except PermissionDenied:
            result.update(score=None, trace=None, review_notes='', evidence_status='unavailable')
    return result
