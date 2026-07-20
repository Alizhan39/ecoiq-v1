"""
ai_observatory/services/recorder.py — the one write path for observatory
telemetry. Instrumented product code uses these helpers; nothing else in
the app writes telemetry rows.

DESIGN RULE: telemetry must never break the product. Every public helper
here swallows its own failures (logged, never raised) so a telemetry bug
can never take down an analysis that would otherwise have succeeded. The
timing measurements themselves are real perf_counter deltas around the real
work — nothing is sampled, modelled or invented.
"""
import logging
import time
from contextlib import contextmanager

from django.utils import timezone

logger = logging.getLogger(__name__)


def start_session(project=None, kind='other', user=None, human_review_required=True, company=None):
    """Creates a running AnalysisSession, anchored to EITHER `project` OR
    `company` (feat/company-halal-intelligence, PR 9 — AnalysisSession's
    own CheckConstraint requires exactly one). Callers pass whichever
    anchor their pipeline has; passing both or neither is a caller bug and
    is logged, not silently coerced. Returns None (and logs) on failure —
    callers must treat a None session as "telemetry off"."""
    from ai_observatory.models import AnalysisSession

    if (project is None) == (company is None):
        logger.error('Observatory: start_session requires exactly one of project/company for kind %s', kind)
        return None
    try:
        return AnalysisSession.objects.create(
            project=project, company=company, kind=kind,
            user=user if getattr(user, 'is_authenticated', False) else None,
            human_review_required=human_review_required,
        )
    except Exception:
        anchor = getattr(project, 'pk', None) or getattr(company, 'pk', '?')
        logger.exception('Observatory: failed to start %s session for anchor %s', kind, anchor)
        return None


def finish_session(session, *, status='completed', evidence_retrieved=None, evidence_reused=None,
                   warnings=None, blocked_recommendations=0, final_recommendation_status=None,
                   human_review_completed=False):
    if session is None:
        return None
    try:
        now = timezone.now()
        session.finished_at = now
        session.duration_ms = max(0, int((now - session.started_at).total_seconds() * 1000))
        session.status = status
        if evidence_retrieved is not None:
            session.evidence_retrieved_count = evidence_retrieved
        if evidence_reused is not None:
            session.evidence_reused_count = evidence_reused
        if warnings:
            session.warnings = list(warnings)
        session.blocked_recommendation_count = blocked_recommendations
        if final_recommendation_status is not None:
            session.final_recommendation_status = final_recommendation_status
        session.human_review_completed = human_review_completed
        session.save()
        return session
    except Exception:
        logger.exception('Observatory: failed to finish session %s', getattr(session, 'pk', '?'))
        return None


@contextmanager
def record_stage(session, stage_key, label, category='deterministic'):
    """Times one real pipeline stage. Yields a mutable dict the caller can
    fill with items_processed / metadata / success. If the wrapped work
    raises, the stage is recorded as success=False and the exception
    propagates to the product code untouched."""
    info = {'items_processed': None, 'metadata': {}, 'success': True}
    started_wall = timezone.now()
    started = time.perf_counter()
    try:
        yield info
    except Exception:
        info['success'] = False
        raise
    finally:
        _save_stage(session, stage_key, label, category, started_wall, started, info)


def _save_stage(session, stage_key, label, category, started_wall, started, info):
    if session is None:
        return
    from ai_observatory.models import PipelineStageExecution

    try:
        PipelineStageExecution.objects.create(
            session=session, stage_key=stage_key, label=label, category=category,
            started_at=started_wall,
            duration_ms=max(0, int((time.perf_counter() - started) * 1000)),
            success=info.get('success', True),
            items_processed=info.get('items_processed'),
            metadata=info.get('metadata') or {},
        )
    except Exception:
        logger.exception('Observatory: failed to record stage %s', stage_key)


def mark_human_review_completed(project, decision_id):
    """Flags the project's capital_decision sessions whose preparation stage
    recorded this decision_id as now human-reviewed. Real linkage only —
    sessions with no recorded decision_id are never guessed at."""
    from ai_observatory.models import AnalysisSession

    try:
        sessions = AnalysisSession.objects.filter(
            project=project, kind='capital_decision',
            stages__metadata__decision_id=decision_id,
        ).distinct()
        sessions.update(human_review_completed=True)
    except Exception:
        logger.exception('Observatory: failed to mark human review completed for decision %s', decision_id)


def record_model_invocation(session, *, provider='', model_name='', model_version='',
                            prompt_version='', input_tokens=None, output_tokens=None,
                            cached_tokens=None, streaming=None, retry_count=0,
                            duration_ms=None, succeeded=None, agent_run=None):
    """Records one REAL model call — one row per PHYSICAL provider request.
    Token fields default to None — pass a value only when the provider
    actually reported one; this function never estimates. `duration_ms` is
    a measured wall-clock value from the caller; `succeeded` is the real
    request outcome; both stay NULL when not measured. `agent_run` may be
    an agent_runtime_model_router.AgentRun, linked via the soft-reference
    convention."""
    from ai_observatory.models import ModelInvocation

    try:
        return ModelInvocation.objects.create(
            session=session, provider=provider, model_name=model_name,
            model_version=model_version, prompt_version=prompt_version,
            input_tokens=input_tokens, output_tokens=output_tokens,
            cached_tokens=cached_tokens, streaming=streaming, retry_count=retry_count,
            duration_ms=duration_ms, succeeded=succeeded,
            agent_run_reference=(
                f'agent_runtime_model_router.AgentRun:{agent_run.pk}' if agent_run is not None else ''
            ),
        )
    except Exception:
        logger.exception('Observatory: failed to record model invocation')
        return None
