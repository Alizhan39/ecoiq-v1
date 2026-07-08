"""
backend_intelligence_engine/services/status.py — the read-only backend
connection point for surfacing real task status in the AI Agent Workbench.

Phase 1 does NOT change the Workbench template or add a status widget —
that's explicitly future UI work. This module only makes the real data
queryable, so that work has something honest to display later: no invented
"live progress" state, only what a BackgroundTaskRun row actually says.
"""
from backend_intelligence_engine.models import BackgroundTaskRun

# Maps a real BackgroundTaskRun.status onto the illustrative UI labels a
# future Workbench status widget would show. 'running' maps to 'analysing'
# rather than a literal "RUNNING" because, for an ai_analysis task
# specifically, that's what's actually happening — this mapping is only used
# for ai_analysis task rows.
_AI_ANALYSIS_DISPLAY_STATUS = {
    'queued': 'QUEUED',
    'running': 'ANALYSING',
    'retrying': 'ANALYSING',
    'completed': 'COMPLETED',
    'failed': 'FAILED',
}


def latest_task_run_for_agent_run(agent_run_id):
    """
    Returns the most recent BackgroundTaskRun whose result_summary references
    this AgentRun id (set by tasks.run_ai_analysis on completion/failure), or
    None if this AgentRun was never produced by a background task (e.g. it
    was created directly by a demo seed command, not queued through Celery).
    """
    return (
        BackgroundTaskRun.objects.filter(task_type='ai_analysis', result_summary__agent_run_id=agent_run_id)
        .order_by('-queued_at')
        .first()
    )


def display_status_for_agent_run(agent_run_id):
    """Real, never-fabricated status label for a given AgentRun, or None if untracked."""
    run = latest_task_run_for_agent_run(agent_run_id)
    if run is None:
        return None
    return _AI_ANALYSIS_DISPLAY_STATUS.get(run.status, run.status.upper())
