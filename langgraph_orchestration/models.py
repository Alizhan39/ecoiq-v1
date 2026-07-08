"""
langgraph_orchestration/models.py — the smallest model that gives node-level
observability the existing backend_intelligence_engine.BackgroundTaskRun
does not: BackgroundTaskRun tracks whether the Celery TASK succeeded;
OrchestrationRun tracks what the graph did INSIDE that task — which nodes
ran, in what order, which one (if any) failed, and the final structured
result. The two are complementary, not duplicates — a Celery-queued
orchestration run has both a BackgroundTaskRun row (task-level) and an
OrchestrationRun row (graph-level), linked by celery_task_id.
"""
from django.db import models


class OrchestrationRun(models.Model):
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('needs_human_review', 'Needs Human Review'),
        ('failed', 'Failed'),
    ]
    TARGET_TYPE_CHOICES = [
        ('company', 'Company'),
        ('country', 'Country'),
        ('location', 'Location'),
        ('unknown', 'Unknown'),
    ]

    user_request = models.TextField(blank=True)
    target_type = models.CharField(max_length=20, choices=TARGET_TYPE_CHOICES, default='unknown')
    target_repr = models.CharField(max_length=255, blank=True, help_text='Human-readable label, e.g. a company name.')
    # Soft reference, deliberately not a ForeignKey — mirrors backend_intelligence_engine's
    # own convention, e.g. "companies.CompanyProfile:12".
    target_reference = models.CharField(max_length=200, blank=True, db_index=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running', db_index=True)
    confidence = models.FloatField(null=True, blank=True)
    human_review_required = models.BooleanField(default=False)

    nodes_executed = models.JSONField(default=list, blank=True)
    failed_node = models.CharField(max_length=100, blank=True)
    error_summary = models.TextField(blank=True)

    # The full final OrchestratorState, JSON-serializable — this is the
    # "structured intelligence output" the Workbench/a future dashboard reads.
    result = models.JSONField(default=dict, blank=True)

    celery_task_id = models.CharField(max_length=155, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.target_repr or self.target_type} — {self.get_status_display()}'

    def mark_completed(self, final_state):
        from django.utils import timezone
        self.status = final_state.get('status', 'completed')
        self.confidence = final_state.get('confidence')
        self.human_review_required = final_state.get('human_review_required', False)
        self.nodes_executed = final_state.get('nodes_executed', [])
        self.failed_node = final_state.get('failed_node') or ''
        self.result = _json_safe(final_state)
        self.completed_at = timezone.now()
        self.save()

    def mark_failed(self, failed_node, error_summary, nodes_executed=None):
        from django.utils import timezone
        self.status = 'failed'
        self.failed_node = failed_node or ''
        self.error_summary = error_summary[:4000]
        self.nodes_executed = nodes_executed or self.nodes_executed
        self.completed_at = timezone.now()
        self.save()


def _json_safe(state):
    """Strips anything non-JSON-serializable before persisting (defensive —
    every node is expected to only put plain dict/list/str/int/float/bool/
    None into state, but this guards against a future node forgetting)."""
    import json

    try:
        json.dumps(state)
        return dict(state)
    except (TypeError, ValueError):
        return {k: v for k, v in state.items() if _is_json_safe(v)}


def _is_json_safe(value):
    import json

    try:
        json.dumps(value)
        return True
    except (TypeError, ValueError):
        return False
