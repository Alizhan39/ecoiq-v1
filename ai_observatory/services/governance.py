"""Durable governance events in the existing Observatory.

Business callers write in the same transaction as their state transition:
an audit failure rolls it back. Best-effort performance telemetry is unchanged.
"""
from ai_observatory.models import PipelineStageExecution


def record_event(session, key, event, *, actor=None, metadata=None, success=True):
    values = {'stage_key': event, 'label': event.replace('_', ' ').capitalize(),
              'category': 'governance', 'actor': actor, 'metadata': metadata or {}, 'success': success}
    entry, created = PipelineStageExecution.objects.get_or_create(session=session, event_key=key, defaults=values)
    if not created and (entry.stage_key != event or entry.metadata != values['metadata']
                        or entry.actor_id != getattr(actor, 'pk', None) or entry.success != success):
        raise ValueError('Audit event key reused with different content.')
    return entry


def session_trace(session):
    """Internal serializer; the API must enforce current project READ access."""
    return {
        'session_id': session.pk, 'project_id': session.project_id,
        'events': list(session.stages.order_by('pk').values('id', 'stage_key', 'actor_id', 'started_at', 'success', 'metadata')),
        'model_calls': list(session.model_invocations.order_by('pk').values(
            'id', 'agent_run_reference', 'provider', 'model_name', 'model_version', 'input_tokens',
            'output_tokens', 'cached_tokens', 'retry_count', 'duration_ms', 'succeeded')),
        'routes': list(session.agent_runs.values('id', 'model_provider', 'model_name', 'routing_reason',
                                               'estimated_cost_usd', 'execution_mode_used', 'status')),
        'actual_cost_usd': None,
        'cost_note': 'Provider billing is not reported here. Route costs are estimates; token usage is provider-reported.',
    }
