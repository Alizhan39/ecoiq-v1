"""
decision_studio/models.py — one new model, justified because nothing
existing stores "a natural-language question and its synthesized answer":
- backend_intelligence_engine.BackgroundTaskRun tracks a Celery task's
  lifecycle, not a question's resolved intent/entities/result.
- langgraph_orchestration.OrchestrationRun tracks one graph execution's
  internal state, keyed by a single target_id/target_type — not a free-text
  question, and not multi-entity comparisons/rankings.
DecisionQuery sits above both, optionally pointing at an OrchestrationRun
when the capability plan invoked the agent+Council path for one entity.
"""
from django.conf import settings
from django.db import models


class DecisionQuery(models.Model):
    INTENT_CHOICES = [
        ('COMPARE', 'Compare'),
        ('RANK', 'Rank'),
        ('ASSESS', 'Assess'),
        ('INVESTIGATE', 'Investigate'),
        ('PRIORITISE', 'Prioritise'),
        ('FIND_RISK', 'Find Risk'),
        ('FIND_OPPORTUNITY', 'Find Opportunity'),
        ('EXPLAIN', 'Explain'),
        ('RECOMMEND', 'Recommend'),
        ('UNKNOWN', 'Unknown'),
    ]
    DATA_AVAILABILITY_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('PARTIAL', 'Partial'),
        ('INSUFFICIENT', 'Insufficient'),
        ('UNKNOWN', 'Unknown'),
    ]
    CONFIDENCE_CHOICES = [
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
        ('INSUFFICIENT_EVIDENCE', 'Insufficient Evidence'),
    ]

    question_text = models.TextField()
    session_key = models.CharField(max_length=64, blank=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    intent = models.CharField(max_length=20, choices=INTENT_CHOICES, default='UNKNOWN')
    # [{'type': 'company'|'country'|'sector', 'id': int|None, 'name': str, 'match_type': 'exact'|'partial'|'multiple'|'none'}, ...]
    resolved_entities = models.JSONField(default=list, blank=True)
    # {'country': str|None, 'sector': str|None, 'time_horizon': str|None, 'decision_context': str|None, 'requested_dimensions': [str, ...]}
    scope = models.JSONField(default=dict, blank=True)
    # [{'capability': str, 'reason': str, 'executed': bool}, ...]
    capability_plan = models.JSONField(default=list, blank=True)

    data_availability_status = models.CharField(max_length=15, choices=DATA_AVAILABILITY_CHOICES, default='UNKNOWN')
    confidence_label = models.CharField(max_length=25, choices=CONFIDENCE_CHOICES, default='INSUFFICIENT_EVIDENCE')
    confidence_score = models.FloatField(null=True, blank=True)

    # The full Decision Result: executive_answer, key_findings, ranking,
    # recommendation, rationale, supporting_evidence, counter_evidence,
    # risks, opportunities, uncertainty_notes, data_gaps, sources,
    # modules_used, agents_used, visualizations, follow_up_questions.
    result = models.JSONField(default=dict, blank=True)

    orchestration_run = models.ForeignKey(
        'langgraph_orchestration.OrchestrationRun', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='decision_queries',
    )
    parent_query = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='follow_ups',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.intent}] {self.question_text[:60]}'
