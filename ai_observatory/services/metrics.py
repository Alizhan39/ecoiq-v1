"""
ai_observatory/services/metrics.py — the AI quality metrics shown on the
Observatory dashboard. Every metric is a documented, reproducible
computation over REAL recorded data (sessions/stages/invocations plus the
project's own evidence and decision records). None of these are scientific
scales and none claim to be — each one's definition below is rendered
verbatim on the Methodology page (METRIC_DEFINITIONS), including what it
does NOT claim.

Metrics return None (rendered as an honest "not measured") whenever the
underlying data doesn't exist — never a fabricated 0 or 100.
"""
from django.db.models import Sum

METRIC_DEFINITIONS = [
    {
        'key': 'evidence_traceability',
        'label': 'Evidence Traceability',
        'measures': 'Share of this project\'s Evidence Memory records carrying a machine-readable integrity reference (SHA-256 of stored text) and a structured provenance link.',
        'calculation': 'traceable_records / total_records for the project\'s evidence memory rows; traceable = has integrity_reference AND (project link OR originating decision/outcome link).',
        'assumptions': 'Provenance links are as recorded at sync time.',
        'not_claimed': 'Not a claim that source documents are authentic, only that stored records are hash-referenced and linked to their origin.',
    },
    {
        'key': 'evidence_coverage',
        'label': 'Evidence Coverage',
        'measures': 'Share of the project\'s evidence records that have passed verification.',
        'calculation': 'verified_records / total_records for the project\'s evidence memory rows.',
        'assumptions': 'Verification statuses are as recorded by the existing review workflow.',
        'not_claimed': 'Not a completeness claim — a project can have high coverage over very little evidence; the raw counts are always shown alongside.',
    },
    {
        'key': 'evidence_reuse',
        'label': 'Evidence Reuse',
        'measures': 'How much previously recorded evidence the latest analysis session retrieved instead of regenerating from scratch.',
        'calculation': 'evidence_reused_count / evidence_retrieved_count on the latest completed session that measured retrieval; reused = records that already existed before the session started.',
        'assumptions': 'Counts recorded live by the retrieval stage.',
        'not_claimed': 'Not a cache-hit-rate for any model provider.',
    },
    {
        'key': 'human_oversight',
        'label': 'Human Oversight',
        'measures': 'Share of this project\'s recorded sessions that required an explicit human review step.',
        'calculation': 'sessions_with_human_review_required / total_sessions.',
        'assumptions': 'Sessions record the requirement at run time from the real pipeline flags.',
        'not_claimed': 'Not a claim that every review was completed — completion is tracked separately per session.',
    },
    {
        'key': 'governance_completion',
        'label': 'Governance Completion',
        'measures': 'Share of governance/safety stages recorded across sessions that completed successfully.',
        'calculation': 'successful_governance_stages / total_governance_stages across all of the project\'s sessions.',
        'assumptions': 'A governance stage is any recorded stage with category="governance".',
        'not_claimed': 'Not an audit opinion — it measures that checks ran, not that their configuration is sufficient for any particular regulatory regime.',
    },
    {
        'key': 'blocked_unsafe_outputs',
        'label': 'Blocked Unsafe Outputs',
        'measures': 'Count of recommendations the safety/eligibility gates refused across all recorded sessions.',
        'calculation': 'Sum of blocked_recommendation_count over the project\'s sessions.',
        'assumptions': 'Counts recorded at gate time from real gate outcomes.',
        'not_claimed': 'Not a measure of how many unsafe outputs a different system WOULD have produced.',
    },
    {
        'key': 'confidence_disclosure',
        'label': 'Confidence Disclosure',
        'measures': 'Whether the project\'s capital decisions carry an explicit confidence value rather than an implied certainty.',
        'calculation': 'decisions_with_confidence / total_decisions for this project\'s capital allocation decisions.',
        'assumptions': 'Confidence values are as stored on the decision records.',
        'not_claimed': 'Not a claim that the disclosed confidence values are well-calibrated.',
    },
    {
        'key': 'missing_data_disclosure',
        'label': 'Missing Data Disclosure',
        'measures': 'Whether the latest analysis surfaced its own evidence gaps instead of hiding them.',
        'calculation': 'Count of warnings recorded on the latest completed session (each warning is a real, user-visible disclosure).',
        'assumptions': 'Warnings recorded live from real pipeline output.',
        'not_claimed': 'A zero does not mean "no data is missing" — it means the pipeline reported no gaps for what it examined.',
    },
    {
        'key': 'deterministic_step_ratio',
        'label': 'Deterministic Step Ratio',
        'measures': 'Share of recorded work units (pipeline stages + model calls) that were deterministic or retrieval steps rather than model generations.',
        'calculation': 'stage_count / (stage_count + model_call_count) on the latest completed session. 1.0 = fully deterministic.',
        'assumptions': 'Each recorded stage and each model call counts as one work unit regardless of runtime.',
        'not_claimed': 'Not a runtime or energy share — see the Compute Proxies section for the weighted view.',
    },
    {
        'key': 'retrieval_usage',
        'label': 'Retrieval Usage',
        'measures': 'How many retrieval operations the project\'s sessions performed (using stored evidence instead of fresh generation).',
        'calculation': 'Count of stages with category="retrieval" across the project\'s sessions.',
        'assumptions': 'Retrieval stages recorded live by the instrumented pipelines.',
        'not_claimed': 'Retrieval count alone says nothing about retrieval quality; similarity/ranking explanations live in Evidence Memory.',
    },
]


def quality_metrics(project):
    """All dashboard quality metrics for one project, computed live from
    real rows. Returns {key: {'value': float|int|None, 'display': str, ...definition}}."""
    from ai_observatory.models import AnalysisSession, PipelineStageExecution
    from evidence_memory.models import EvidenceMemory
    from waste_to_value_capital_allocation_engine.models import CapitalAllocationDecision

    sessions = AnalysisSession.objects.filter(project=project)
    completed = sessions.filter(status='completed')
    latest = completed.first()  # ordering is -started_at

    memories = EvidenceMemory.objects.filter(project=project)
    memory_total = memories.count()
    traceable = memories.exclude(integrity_reference='').exclude(
        project=None, originating_decision=None, originating_outcome=None,
    ).count() if memory_total else 0
    verified = memories.filter(verification_status='verified').count()

    decisions = CapitalAllocationDecision.objects.filter(project=project.name)
    decision_total = decisions.count()
    with_confidence = decisions.exclude(confidence=None).count()

    governance_stages = PipelineStageExecution.objects.filter(session__project=project, category='governance')
    governance_total = governance_stages.count()
    governance_ok = governance_stages.filter(success=True).count()

    session_total = sessions.count()
    review_required = sessions.filter(human_review_required=True).count()

    latest_retrieval = completed.exclude(evidence_retrieved_count=None).first()

    values = {
        'evidence_traceability': _ratio(traceable, memory_total),
        'evidence_coverage': _ratio(verified, memory_total),
        'evidence_reuse': _ratio(
            latest_retrieval.evidence_reused_count if latest_retrieval else None,
            latest_retrieval.evidence_retrieved_count if latest_retrieval else None,
        ),
        'human_oversight': _ratio(review_required, session_total),
        'governance_completion': _ratio(governance_ok, governance_total),
        'blocked_unsafe_outputs': sessions.aggregate(n=Sum('blocked_recommendation_count'))['n'] or 0,
        'confidence_disclosure': _ratio(with_confidence, decision_total),
        'missing_data_disclosure': len(latest.warnings) if latest is not None else None,
        'deterministic_step_ratio': latest.deterministic_step_ratio if latest is not None else None,
        'retrieval_usage': PipelineStageExecution.objects.filter(session__project=project, category='retrieval').count(),
    }

    out = {}
    for definition in METRIC_DEFINITIONS:
        value = values[definition['key']]
        out[definition['key']] = {**definition, 'value': value, 'display': _display(definition['key'], value)}
    return out


def _ratio(numerator, denominator):
    if not denominator or numerator is None:
        return None
    return round(numerator / denominator, 3)


_COUNT_METRICS = {'blocked_unsafe_outputs', 'missing_data_disclosure', 'retrieval_usage'}


def _display(key, value):
    if value is None:
        return 'Not measured yet'
    if key in _COUNT_METRICS:
        return str(int(value))
    return f'{value * 100:.0f}%'
