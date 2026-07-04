"""
ai_agent_council/models.py — the Council Runtime.

These models back the "governed multi-agent runtime" behind the AI Agent
Council: a Council Run is one decision-making session in which selected
agents investigate (in parallel or solo), hand work to one another, disagree,
cross-examine each other, and reach an accountable decision with a preserved
audit trail and institutional memory.

Honesty note: there is no live LLM execution runtime anywhere in this
repository. Every CouncilRun currently in the database is seeded by
`ai_agent_council/services/seed_demo.py` from authored fixture facts, run
through the *real* deterministic services in `ai_agent_council/services/`
(routing, disagreement classification, confidence calibration) — the data
is genuinely persisted and genuinely computed, but the domain judgement that
seeds a demo scenario is not live AI inference. `CouncilRun.is_simulated` is
always True today and every simulated run must say so in the UI.
"""
from django.db import models
from django.utils import timezone

COLLABORATION_MODE_CHOICES = [
    ('solo',        'Solo'),
    ('parallel',    'Parallel'),
    ('handoff',     'Handoff'),
    ('council',     'Council'),
    ('escalation',  'Escalation'),
]

RUN_STATUS_CHOICES = [
    ('open',      'Open'),
    ('decided',   'Decided'),
    ('reopened',  'Reopened'),
    ('closed',    'Closed'),
]

TASK_STATUS_CHOICES = [
    ('pending',    'Pending'),
    ('running',    'Running'),
    ('completed',  'Completed'),
    ('failed',     'Failed'),
]

CONFLICT_TYPE_CHOICES = [
    ('factual',        'Factual disagreement'),
    ('assumption',      'Assumption disagreement'),
    ('evidence',        'Evidence disagreement'),
    ('risk_tolerance',   'Risk tolerance disagreement'),
    ('timing',          'Timing disagreement'),
    ('domain',          'Domain conflict'),
]

RESOLUTION_METHOD_CHOICES = [
    ('resolve_automatically',      'Resolve automatically'),
    ('request_more_evidence',      'Request more evidence'),
    ('ask_another_agent',          'Ask another agent'),
    ('require_human_review',       'Require human review'),
    ('preserve_minority_opinion',  'Preserve minority opinion'),
]

DECISION_STATUS_CHOICES = [
    ('draft',                    'Draft'),
    ('under_review',             'Under Review'),
    ('approved',                 'Approved'),
    ('approved_with_conditions', 'Approved with Conditions'),
    ('rejected',                 'Rejected'),
    ('suspended',                'Suspended'),
    ('reopened',                 'Reopened'),
    ('superseded',               'Superseded'),
]


class CouncilRun(models.Model):
    """One Council decision-making session for a single user goal/question."""
    slug          = models.SlugField(max_length=120, unique=True)
    title         = models.CharField(max_length=255)
    question      = models.TextField(help_text='The user goal this run was opened to answer.')
    task_category = models.CharField(max_length=60, help_text='Routing category used to select agents.')
    is_simulated  = models.BooleanField(
        default=True,
        help_text='Always True today: no live LLM execution runtime exists in this repository.',
    )
    status        = models.CharField(max_length=20, choices=RUN_STATUS_CHOICES, default='open')
    selected_agents = models.JSONField(
        default=list,
        help_text='List of {agent_name, selected, reason} — every agent considered, not just the chosen ones.',
    )
    created_at    = models.DateTimeField(default=timezone.now)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Council Run'
        verbose_name_plural = 'Council Runs'

    def __str__(self):
        return self.title


class AgentTask(models.Model):
    """
    One agent's contribution within a run: its task, its collaboration mode,
    and — once complete — its position (summary, confidence, confidence
    breakdown). Positions are modelled as fields on the task rather than a
    separate model: nothing in this system needs more than one position per
    task, and CouncilDisagreement simply references two AgentTask rows.
    """
    run                 = models.ForeignKey(CouncilRun, on_delete=models.CASCADE, related_name='tasks')
    agent_name          = models.CharField(max_length=100)
    collaboration_mode  = models.CharField(max_length=20, choices=COLLABORATION_MODE_CHOICES)
    status              = models.CharField(max_length=20, choices=TASK_STATUS_CHOICES, default='completed')
    input_summary       = models.TextField(blank=True)
    output_summary      = models.TextField(blank=True)
    position_summary    = models.TextField(blank=True, help_text='The agent\'s stated position/recommendation.')
    confidence          = models.FloatField(null=True, blank=True)
    confidence_breakdown = models.JSONField(
        default=dict, blank=True,
        help_text='Canonical shape from services.confidence.build_confidence_breakdown().',
    )
    evidence_refs   = models.JSONField(default=list, blank=True)
    missing_data    = models.JSONField(default=list, blank=True)
    risk_flags      = models.JSONField(default=list, blank=True)
    order           = models.PositiveIntegerField(default=0)

    class Meta:
        ordering            = ['run', 'order']
        verbose_name        = 'Agent Task'
        verbose_name_plural = 'Agent Tasks'

    def __str__(self):
        return f'{self.agent_name} ({self.get_collaboration_mode_display()}) — {self.run.title}'


class AgentHandoff(models.Model):
    """An explicit transfer of work from one agent to another within a run."""
    run                    = models.ForeignKey(CouncilRun, on_delete=models.CASCADE, related_name='handoffs')
    sender_agent           = models.CharField(max_length=100)
    receiver_agent         = models.CharField(max_length=100)
    reason                 = models.TextField()
    evidence_attached      = models.JSONField(default=list, blank=True)
    unresolved_questions   = models.JSONField(default=list, blank=True)
    confidence_at_handoff  = models.FloatField(null=True, blank=True)
    required_output        = models.TextField(blank=True)
    order                  = models.PositiveIntegerField(default=0)

    class Meta:
        ordering            = ['run', 'order']
        verbose_name        = 'Agent Handoff'
        verbose_name_plural = 'Agent Handoffs'

    def __str__(self):
        return f'{self.sender_agent} → {self.receiver_agent} ({self.run.title})'


class CouncilDisagreement(models.Model):
    """
    A classified disagreement between two agent positions within a run.
    Disagreements are never hidden — every one created here is shown on the
    run-detail page's Disagreement panel, including whichever position is
    the minority one.
    """
    run                     = models.ForeignKey(CouncilRun, on_delete=models.CASCADE, related_name='disagreements')
    position_a              = models.ForeignKey(AgentTask, on_delete=models.CASCADE, related_name='disagreements_as_a')
    position_b              = models.ForeignKey(AgentTask, on_delete=models.CASCADE, related_name='disagreements_as_b')
    conflict_type           = models.CharField(max_length=20, choices=CONFLICT_TYPE_CHOICES)
    evidence_used           = models.JSONField(default=list, blank=True)
    resolution_method       = models.CharField(max_length=30, choices=RESOLUTION_METHOD_CHOICES)
    final_decision_summary  = models.TextField(blank=True)
    minority_opinion_retained = models.BooleanField(default=True)

    class Meta:
        ordering            = ['run', 'id']
        verbose_name        = 'Council Disagreement'
        verbose_name_plural = 'Council Disagreements'

    def __str__(self):
        return f'{self.position_a.agent_name} vs {self.position_b.agent_name} ({self.get_conflict_type_display()})'


class CrossExaminationExchange(models.Model):
    """One question-and-response exchange in a Council Debate timeline."""
    run                     = models.ForeignKey(CouncilRun, on_delete=models.CASCADE, related_name='cross_examinations')
    questioner_agent        = models.CharField(max_length=100)
    target_agent            = models.CharField(max_length=100)
    challenge_type          = models.CharField(max_length=60)
    reason                  = models.TextField()
    requested_evidence       = models.JSONField(default=list, blank=True)
    response_answer          = models.TextField(blank=True)
    response_evidence        = models.JSONField(default=list, blank=True)
    response_confidence      = models.FloatField(null=True, blank=True)
    unresolved_uncertainty    = models.TextField(blank=True)
    sequence                = models.PositiveIntegerField(default=0)

    class Meta:
        ordering            = ['run', 'sequence']
        verbose_name        = 'Cross-Examination Exchange'
        verbose_name_plural = 'Cross-Examination Exchanges'

    def __str__(self):
        return f'{self.questioner_agent} asks {self.target_agent}: {self.challenge_type}'


class CouncilDecision(models.Model):
    """The final, accountable decision for one Council Run."""
    run                     = models.OneToOneField(CouncilRun, on_delete=models.CASCADE, related_name='decision')
    status                  = models.CharField(max_length=30, choices=DECISION_STATUS_CHOICES, default='draft')
    summary                 = models.TextField()
    majority_agents         = models.JSONField(default=list, blank=True)
    minority_agents         = models.JSONField(default=list, blank=True)
    minority_reason         = models.TextField(blank=True)
    conditions              = models.JSONField(default=list, blank=True)
    confidence              = models.FloatField(null=True, blank=True)
    confidence_breakdown    = models.JSONField(default=dict, blank=True)
    human_approval_required = models.BooleanField(default=True)
    human_approved          = models.BooleanField(null=True, blank=True)

    class Meta:
        verbose_name        = 'Council Decision'
        verbose_name_plural = 'Council Decisions'

    def __str__(self):
        return f'{self.run.title} — {self.get_status_display()}'


class DecisionMemoryEntry(models.Model):
    """
    Institutional memory for one Council Decision: why it was made, what
    remains open, and — if applicable — how/why it was reopened.
    """
    decision                 = models.OneToOneField(CouncilDecision, on_delete=models.CASCADE, related_name='memory_entry')
    original_decision_summary = models.TextField()
    reason                   = models.TextField()
    open_questions           = models.JSONField(default=list, blank=True)
    unresolved_risks         = models.JSONField(default=list, blank=True)
    review_trigger           = models.TextField(blank=True, help_text='What new evidence/event would justify reopening this decision.')
    reopened                 = models.BooleanField(default=False)
    reopened_reason          = models.TextField(blank=True)
    new_evidence_summary     = models.TextField(blank=True)
    updated_decision_summary = models.TextField(blank=True)
    reopened_at              = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name        = 'Decision Memory Entry'
        verbose_name_plural = 'Decision Memory Entries'

    def __str__(self):
        return f'Memory for {self.decision}'
