"""
agent_training_evaluation_lab/models.py — Agent Evaluation, Benchmarking &
Continuous Improvement (Phase 1).

This app existed before as a views-only prose page (its name always
promised this, never delivered it) — these are its first real models.

Five models, not more:
  GoldenDatasetCase        — a formalised, queryable mirror of the REAL
                             ai_agents/*/test_cases.json files (synced, not
                             duplicated by hand — see services/golden_dataset.py)
  AgentEvaluationRun       — one evaluation pass; ALSO the benchmark record
                             (previous_evaluation + score_delta), so no
                             separate "BenchmarkResult" model is needed
  AgentRegression          — a detected decline, human-observable, never
                             auto-remediated
  AgentHumanFeedback       — reviewer classification of one real AgentRun
  ImprovementRecommendation — a recommendation only; never applied by code

Every metric on AgentEvaluationRun is computed from real, already-persisted
agent_runtime_model_router.AgentRun fields (see services/metrics.py) — never
from a fabricated benchmark number. Where an agent genuinely has too few
runs to compute a metric, that metric's score is null and its explanation
says so, matching the "NOT YET MEASURED" convention already established
elsewhere on this platform (e.g. ai_agent_workbench's performance page).
"""
from django.conf import settings
from django.db import models


class GoldenDatasetCase(models.Model):
    CASE_TYPE_CHOICES = [('realistic', 'Realistic'), ('failure', 'Failure')]

    agent = models.ForeignKey(
        'agent_runtime_model_router.AgentRegistryEntry', on_delete=models.CASCADE, related_name='golden_cases',
    )
    case_id = models.CharField(max_length=40, help_text='e.g. "RA-01" — the id in the real test_cases.json file.')
    case_type = models.CharField(max_length=10, choices=CASE_TYPE_CHOICES)
    title = models.CharField(max_length=300, blank=True)
    input_summary = models.JSONField(default=dict, blank=True)
    # {'confidence': int, 'human_approval_required': bool, 'evidence_summary_includes': [...],
    #  'missing_data_includes': [...], 'expected_behaviour': str (failure cases)}
    expected_properties = models.JSONField(default=dict, blank=True)
    dataset_version = models.CharField(max_length=20, default='v1')
    is_active = models.BooleanField(default=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['agent', 'case_id']
        constraints = [models.UniqueConstraint(fields=['agent', 'case_id'], name='uniq_agent_case_id')]

    def __str__(self):
        return f'{self.case_id} ({self.agent.agent_name})'


class AgentEvaluationRun(models.Model):
    """
    One evaluation pass over an agent's real, already-persisted AgentRun
    history. previous_evaluation + score_delta make this row double as the
    "benchmark result" the spec asks for — a benchmark IS an evaluation
    compared against the prior one, not a different kind of record.
    """
    agent = models.ForeignKey(
        'agent_runtime_model_router.AgentRegistryEntry', on_delete=models.CASCADE, related_name='evaluation_runs',
    )
    evaluation_version = models.CharField(max_length=20, default='v1')

    # {'factual_grounding': {'score': float|None, 'explanation': str, 'sample_size': int}, ...}
    metrics = models.JSONField(default=dict, blank=True)
    overall_score = models.FloatField(null=True, blank=True)
    runs_evaluated_count = models.IntegerField(default=0)
    golden_cases_checked = models.IntegerField(default=0)
    golden_cases_passed = models.IntegerField(default=0)
    failure_reasons = models.JSONField(default=list, blank=True)

    previous_evaluation = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='next_evaluations',
    )
    # {'overall_score': +4.2, 'factual_grounding': -1.0, ...} — only populated when a previous_evaluation exists.
    score_delta = models.JSONField(default=dict, blank=True)

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        score = f'{self.overall_score:.1f}' if self.overall_score is not None else 'n/a'
        return f'{self.agent.agent_name} — {self.evaluation_version} ({score})'


class AgentRegression(models.Model):
    SEVERITY_CHOICES = [('low', 'Low'), ('medium', 'Medium'), ('high', 'High')]

    agent = models.ForeignKey(
        'agent_runtime_model_router.AgentRegistryEntry', on_delete=models.CASCADE, related_name='regressions',
    )
    evaluation_run = models.ForeignKey(AgentEvaluationRun, on_delete=models.CASCADE, related_name='regression_findings')
    metric_name = models.CharField(max_length=60)
    previous_value = models.FloatField(null=True, blank=True)
    current_value = models.FloatField(null=True, blank=True)
    threshold = models.FloatField()
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    detected_at = models.DateTimeField(auto_now_add=True)
    # Human acknowledgement only — the system never auto-remediates a regression.
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    acknowledged_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-detected_at']

    def __str__(self):
        return f'{self.agent.agent_name}: {self.metric_name} regressed ({self.previous_value} → {self.current_value})'


class AgentHumanFeedback(models.Model):
    CLASSIFICATION_CHOICES = [
        ('APPROVED', 'Approved'),
        ('NEEDS_IMPROVEMENT', 'Needs Improvement'),
        ('INCORRECT', 'Incorrect'),
        ('INSUFFICIENT_EVIDENCE', 'Insufficient Evidence'),
    ]

    agent_run = models.ForeignKey(
        'agent_runtime_model_router.AgentRun', on_delete=models.CASCADE, related_name='human_feedback',
    )
    evaluation_run = models.ForeignKey(
        AgentEvaluationRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='feedback_entries',
    )
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    classification = models.CharField(max_length=25, choices=CLASSIFICATION_CHOICES)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'AgentRun #{self.agent_run_id}: {self.get_classification_display()}'


class ImprovementRecommendation(models.Model):
    RECOMMENDATION_TYPE_CHOICES = [
        ('improve_evidence_retrieval', 'Improve Evidence Retrieval'),
        ('increase_evidence_threshold', 'Increase Minimum Evidence Threshold'),
        ('review_confidence_calibration', 'Review Confidence Calibration'),
        ('investigate_failure_category', 'Investigate Recurring Failure Category'),
        ('expand_golden_dataset', 'Expand Golden Dataset Coverage'),
        ('inspect_orchestration_failures', 'Inspect Orchestration Node Failures'),
    ]
    STATUS_CHOICES = [('OPEN', 'Open'), ('ACKNOWLEDGED', 'Acknowledged'), ('DISMISSED', 'Dismissed')]

    agent = models.ForeignKey(
        'agent_runtime_model_router.AgentRegistryEntry', on_delete=models.CASCADE, related_name='recommendations',
    )
    recommendation_type = models.CharField(max_length=40, choices=RECOMMENDATION_TYPE_CHOICES)
    description = models.TextField()
    # {'evaluation_run_ids': [...], 'regression_ids': [...], 'feedback_ids': [...]}
    based_on = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='OPEN')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.agent.agent_name}: {self.get_recommendation_type_display()}'
