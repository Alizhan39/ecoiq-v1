"""
agent_runtime_model_router/models.py — the governed execution layer.

This app connects the 10 operational training packs in `ai_agents/` to the
AI Agent Council v2 runtime (`ai_agent_council/`) via a real execution
pipeline: Council Case -> Agent Selection -> Training Pack Loader -> Model
Router -> Agent Execution -> Structured Output Validation -> Safety
Assertions -> Council Position -> Cross-Examination -> Council Decision ->
Human Approval -> Institutional Memory.

Honesty note: every AgentRun explicitly declares both the execution mode
that was requested and the one actually used (`execution_mode_requested` /
`execution_mode_used`). A failed `live` run is never silently relabelled as
`simulated_demo` — see `services/execution.py`.

This app makes zero changes to `ai_agent_council`. `AgentRun.council_position`
is a one-directional, nullable link to an existing `AgentTask` — once
`submit_agent_position_to_council()` creates that AgentTask, the Council's
own models carry the position; this app's `AgentRun` row keeps the full
execution provenance (routing explanation, fallback chain, evidence detail,
training pack content hash) reachable via `agent_task.agent_run`.
"""
from django.db import models
from django.utils import timezone

EXECUTION_MODE_CHOICES = [
    ('live',                'Live'),
    ('deterministic_test',  'Deterministic Test'),
    ('simulated_demo',      'Simulated Demo'),
]

RUN_STATUS_CHOICES = [
    ('pending',              'Pending'),
    ('running',              'Running'),
    ('completed',            'Completed'),
    ('failed',               'Failed'),
    ('blocked',              'Blocked'),
    ('needs_human_review',   'Needs Human Review'),
]

SAFETY_STATUS_CHOICES = [
    ('pass',          'Pass'),
    ('warning',       'Warning'),
    ('needs_review',  'Needs Review'),
    ('blocking',      'Blocking'),
]

FAILURE_REASON_CHOICES = [
    ('',                        '—'),
    ('missing_credentials',     'Missing Credentials'),
    ('timeout',                 'Timeout'),
    ('rate_limit',              'Rate Limit'),
    ('invalid_json',            'Invalid JSON'),
    ('schema_failure',          'Schema Failure'),
    ('empty_response',          'Empty Response'),
    ('unsupported_capability',  'Unsupported Capability'),
    ('safety_violation',        'Safety Violation'),
]


class AgentRegistryEntry(models.Model):
    """
    A real, DB-backed registry row per agent — not just the static Python
    constants in `ai_agent_council/agents.py`, because `enabled` and
    `last_evaluation_score` are meant to be mutable over time. Synced from
    disk (and from `ai_agent_council.agents`) by `services/registry.py`.
    """
    agent_id                = models.SlugField(max_length=80, unique=True)
    agent_name               = models.CharField(max_length=100)
    training_pack_path       = models.CharField(max_length=255, blank=True)
    training_pack_version    = models.CharField(
        max_length=20, default='v1',
        help_text='No real version file exists in ai_agents/ yet — honest static placeholder.',
    )
    content_hash             = models.CharField(
        max_length=64, blank=True,
        help_text='Real SHA-256 over the training pack\'s required files, computed at sync time.',
    )
    capabilities             = models.JSONField(default=list, blank=True)
    supported_task_types      = models.JSONField(default=list, blank=True)
    allowed_input_types       = models.JSONField(default=list, blank=True)
    expected_output_schema     = models.JSONField(default=dict, blank=True)
    required_reviewer_types    = models.JSONField(default=list, blank=True)
    maturity_stage            = models.PositiveSmallIntegerField(default=0)
    last_evaluation_score      = models.FloatField(
        null=True, blank=True,
        help_text='Stays null until a real evaluation-scoring run exists — never fabricated.',
    )
    enabled                   = models.BooleanField(default=True)
    is_next_stage              = models.BooleanField(
        default=False,
        help_text='True for the 4 agents with no operational training pack — never marked enabled.',
    )
    created_at                = models.DateTimeField(default=timezone.now)
    updated_at                = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['agent_name']
        verbose_name        = 'Agent Registry Entry'
        verbose_name_plural = 'Agent Registry Entries'

    def __str__(self):
        return self.agent_name


class AgentRun(models.Model):
    """One execution of one agent, from routing through to Council submission."""
    council_case  = models.ForeignKey(
        'ai_agent_council.CouncilRun', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='agent_runs',
    )
    council_position = models.OneToOneField(
        'ai_agent_council.AgentTask', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='agent_run',
    )
    agent          = models.ForeignKey(AgentRegistryEntry, on_delete=models.PROTECT, related_name='runs')
    task_type      = models.CharField(max_length=80)

    # Execution mode honesty (hardening requirement 1): what was asked for
    # vs. what actually happened. A live request can only ever resolve to
    # execution_mode_used='live' (possibly via a fallback provider) or a
    # blocked/needs_human_review status — never a silent 'simulated_demo'.
    execution_mode_requested = models.CharField(max_length=20, choices=EXECUTION_MODE_CHOICES)
    execution_mode_used      = models.CharField(max_length=20, choices=EXECUTION_MODE_CHOICES, blank=True)

    model_provider  = models.CharField(max_length=40, blank=True)
    model_name      = models.CharField(max_length=80, blank=True)

    # Model Router decision explainability (hardening requirement 3)
    routing_reason      = models.TextField(blank=True)
    sensitivity_level   = models.CharField(max_length=20, default='standard')
    required_capability = models.CharField(max_length=40, blank=True)
    cost_class          = models.CharField(max_length=20, blank=True)
    rejected_routes     = models.JSONField(default=list, blank=True)
    fallback_route      = models.CharField(max_length=80, blank=True)
    fallback_reason      = models.TextField(blank=True)
    fallback_chain       = models.JSONField(default=list, blank=True)

    # Training pack version provenance (hardening requirement 2)
    training_pack_path           = models.CharField(max_length=255, blank=True)
    training_pack_version         = models.CharField(max_length=20, blank=True)
    prompt_version                = models.CharField(max_length=20, blank=True)
    schema_version                = models.CharField(max_length=20, blank=True)
    safety_rules_version           = models.CharField(max_length=20, blank=True)
    golden_test_version            = models.CharField(max_length=20, blank=True)
    training_pack_content_hash     = models.CharField(max_length=64, blank=True)

    input_summary   = models.TextField(blank=True)
    raw_output      = models.TextField(blank=True)
    parsed_output    = models.JSONField(default=dict, blank=True)
    schema_valid     = models.BooleanField(null=True, blank=True)
    validation_errors = models.JSONField(default=list, blank=True)

    evidence_used        = models.JSONField(default=list, blank=True, help_text='Simple string tags, same shape ai_agent_council.AgentTask expects.')
    evidence_provenance   = models.JSONField(
        default=list, blank=True,
        help_text='Rich per-evidence records: {evidence_id, source_document, source_ref, quality, missing_data_warning, visibility}.',
    )
    missing_data          = models.JSONField(default=list, blank=True)

    raw_confidence        = models.FloatField(null=True, blank=True)
    calibrated_confidence  = models.FloatField(null=True, blank=True)
    confidence_calibration_explanation = models.JSONField(default=list, blank=True)

    risk_flags       = models.JSONField(default=list, blank=True)
    safety_findings   = models.JSONField(default=list, blank=True)
    safety_status     = models.CharField(max_length=20, choices=SAFETY_STATUS_CHOICES, default='pass')

    human_approval_required = models.BooleanField(default=True)
    human_approved            = models.BooleanField(null=True, blank=True)

    # Cost control (hardening requirement 4) — always labelled estimated;
    # actual_usage is only populated if a provider returns real usage data.
    estimated_input_tokens   = models.PositiveIntegerField(null=True, blank=True)
    estimated_output_tokens  = models.PositiveIntegerField(null=True, blank=True)
    estimated_cost_usd        = models.FloatField(null=True, blank=True)
    actual_usage              = models.JSONField(default=dict, blank=True)
    budget_exceeded           = models.BooleanField(default=False)

    # Idempotency / duplicate-run protection (hardening requirement 5)
    idempotency_key = models.CharField(max_length=64, blank=True, db_index=True)
    rerun_of         = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='reruns',
    )
    rerun_reason     = models.TextField(blank=True)

    failure_reason = models.CharField(max_length=40, choices=FAILURE_REASON_CHOICES, blank=True, default='')
    audit_trail     = models.JSONField(default=list, blank=True, help_text='[{ts, event, detail}, ...]')

    status       = models.CharField(max_length=20, choices=RUN_STATUS_CHOICES, default='pending')
    started_at    = models.DateTimeField(null=True, blank=True)
    completed_at  = models.DateTimeField(null=True, blank=True)
    created_at    = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Agent Run'
        verbose_name_plural = 'Agent Runs'

    def __str__(self):
        return f'{self.agent.agent_name} run #{self.pk} ({self.get_status_display()})'
