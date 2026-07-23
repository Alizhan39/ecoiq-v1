"""
good_agents/tasks.py — Celery task wrapping run_discovery (Phase 12).

On-demand/triggered only, exactly like every other Celery task in this
repo — no django-celery-beat is installed here, so this is not literally a
cron job yet; see docs/GOOD_WHILE_YOU_SLEEP.md for what "Good While You
Sleep" means today vs. what real scheduling would require.

`opportunity_factory` callables aren't JSON-serialisable, so this task
cannot drive a domain-specific pipeline (e.g. the Almaty demo) across the
Celery wire — only the generic discovery/classification pass runs here.
Documented as a limitation, not silently worked around.
"""
from celery import shared_task


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=10, retry_backoff_max=60,
             max_retries=2, retry_jitter=True)
def run_good_discovery_task(self, mission, signal_dicts, geography='', themes=None,
                            cost_budget_usd=5.0, idempotency_key=None):
    """signal_dicts: list of {'text':..., 'domains':[...], 'geography':..., 'urgency_hint':...}."""
    from good_agents.services.discovery_run import run_discovery
    from good_agents.services.orchestrator import Signal

    signals = [Signal(**d) for d in signal_dicts]
    run = run_discovery(
        mission, signals, geography=geography, themes=themes, cost_budget_usd=cost_budget_usd,
        idempotency_key=idempotency_key,
    )
    run.celery_task_id = self.request.id or ''
    run.save(update_fields=['celery_task_id'])
    return {'status': run.status, 'run_id': run.pk, 'opportunities_detected': run.opportunities_detected}
