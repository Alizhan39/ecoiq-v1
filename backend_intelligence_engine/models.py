"""
backend_intelligence_engine/models.py — task observability for the EcoIQ
Backend Intelligence Engine.

`DataIngestionLog` (companies app) was considered and rejected as a reuse
target: it's hard-FK'd to `league.Company` specifically and its `source`
choices are ingestion-source-specific, so it can't honestly represent a
geo-intelligence refresh or an AI analysis run. `BackgroundTaskRun` is the
smallest model that can — a soft `target_reference` string (not a cross-app
FK) so this app never gains a hard migration dependency on companies/geo_
intelligence/ai_agent_workbench.

No background job is ever invisible: every Celery task in this app creates
exactly one row here before doing any real work, and updates it through
every status transition — this is what lets "EcoIQ worked while you were
away" be an honest claim rather than a marketing line.
"""
from django.db import models
from django.utils import timezone


class BackgroundTaskRun(models.Model):
    TASK_TYPE_CHOICES = [
        ('company_intelligence_refresh', 'Company Intelligence Refresh'),
        ('geo_intelligence_refresh', 'Geo Intelligence Refresh'),
        ('ai_analysis', 'AI Analysis'),
        ('evidence_memory_refresh', 'Evidence Memory Refresh'),
        ('intelligence_score_recalculation', 'Intelligence Score Recalculation'),
        ('langgraph_intelligence_workflow', 'LangGraph Intelligence Workflow'),
        ('ingest_source', 'Ingest Source'),
        ('ingest_enabled_sources', 'Ingest Enabled Sources'),
        ('refresh_entity_evidence', 'Refresh Entity Evidence'),
    ]
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
    ]

    task_type = models.CharField(max_length=40, choices=TASK_TYPE_CHOICES, db_index=True)
    celery_task_id = models.CharField(max_length=155, blank=True, db_index=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='queued', db_index=True)

    # Soft reference, deliberately not a ForeignKey — see module docstring.
    target_repr = models.CharField(max_length=255, help_text='Human-readable label, e.g. "Acme Ltd" or "Almaty".')
    target_reference = models.CharField(
        max_length=200, blank=True,
        help_text='e.g. "companies.CompanyProfile:42" — soft pointer, never a hard cross-app FK.',
    )
    # The exact kwargs the task was originally called with — lets the admin
    # "Retry" action re-dispatch the identical task generically, without
    # having to reverse-engineer a call from target_reference.
    task_kwargs = models.JSONField(default=dict, blank=True)

    queued_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)

    error_summary = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)

    # Small, structured, real values only — e.g. {"score_before": 61.2,
    # "score_after": 63.8} or {"agent_run_id": 512, "agent_status": "completed"}.
    # Never a substitute for the real target model's own fields.
    result_summary = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-queued_at']

    def __str__(self):
        return f'{self.get_task_type_display()} — {self.target_repr} ({self.status})'

    def mark_running(self):
        self.status = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])

    def mark_completed(self, result_summary=None):
        self.status = 'completed'
        self.completed_at = timezone.now()
        if self.started_at:
            self.duration_seconds = round((self.completed_at - self.started_at).total_seconds(), 3)
        if result_summary:
            self.result_summary = result_summary
        self.save(update_fields=['status', 'completed_at', 'duration_seconds', 'result_summary'])

    def mark_failed(self, error_summary):
        self.status = 'failed'
        self.failed_at = timezone.now()
        if self.started_at:
            self.duration_seconds = round((self.failed_at - self.started_at).total_seconds(), 3)
        self.error_summary = str(error_summary)[:5000]
        self.save(update_fields=['status', 'failed_at', 'duration_seconds', 'error_summary'])

    def mark_retrying(self, error_summary, retry_count):
        self.status = 'retrying'
        self.error_summary = str(error_summary)[:5000]
        self.retry_count = retry_count
        self.save(update_fields=['status', 'error_summary', 'retry_count'])
