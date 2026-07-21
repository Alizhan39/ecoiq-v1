"""
ai_observatory/models.py — feat/ai-observatory: transparent, reproducible
AI telemetry for EcoIQ's analysis pipelines.

CORE PRINCIPLE (from the PR4 brief): no exact electricity or carbon claims —
only transparent proxies with a documented methodology (see
services/proxies.py and the Methodology page). Every recorded value here is
either measured directly (timings, counts, real provider usage data) or
absent (NULL) — never invented. A NULL token count means "the provider did
not report it", not zero.

Three models, deliberately minimal:

- AnalysisSession       — one instrumented run of one EcoIQ pipeline for one
                          project (the brief's AnalysisSession; the
                          "Analysis ID" is its pk). Sessions belong to
                          projects; the observatory only ever shows a
                          project its own sessions.
- PipelineStageExecution — one timed step inside a session (the brief's
                          PipelineExecution / DeterministicStep /
                          RetrievalOperation, unified: they are the same
                          shape — a named, categorised, timed step — and
                          three near-identical tables would add nothing).
- ModelInvocation       — one real LLM call (the brief's ModelInvocation).
                          The Capital Guardian analysis pipeline is fully
                          deterministic and records ZERO of these — that is
                          a real, honest datum central to the efficiency
                          story, not an instrumentation gap. Rows are
                          created only where a model call actually happens
                          (see services/recorder.py.record_model_invocation
                          and the agent_runtime_model_router link below).

The brief's ExperimentRun/comparison is deliberately NOT a stored model:
the generic-LLM comparison is computed live from real session data plus
documented, configurable baseline assumptions (services/comparison.py) —
storing "experiment results" that are really estimates would blur the
measured/estimated line this app exists to keep sharp.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

# feat/company-discovery-ranking (PR 11), generalised by feat/evidence-
# review-workbench (PR 12): kinds whose sessions may anchor to NEITHER a
# project nor a company — a queue-wide review session (or a cross-company
# discovery/ranking run) genuinely has no single anchor. Module-level (not
# a class attribute) because AnalysisSession.Meta's CheckConstraint needs a
# bare name it can see — a nested class body cannot see its enclosing
# class's own attributes by bare name. "Both anchors" remains invalid for
# every kind, including these.
NO_ANCHOR_ALLOWED_KINDS = ('company_discovery', 'evidence_review_workbench')


class AnalysisSession(models.Model):
    KIND_CHOICES = [
        ('project_analysis', 'Project Analysis (Mizan + Resource Purpose + Retrieval)'),
        ('better_way_comparison', 'The Better Way Comparison'),
        ('capital_decision', 'Capital Decision Preparation'),
        ('outcome_recording', 'Outcome Recording / Expected-vs-Actual'),
        ('evidence_memory_sync', 'Evidence Memory Sync'),
        ('company_intelligence', 'Company Intelligence Analysis (Shariah Screen / 114-KPI Mapping)'),
        ('company_evidence_ingestion', 'Company Evidence Ingestion (Source Fetch / Extraction / KPI Candidate Matching)'),
        ('company_discovery', 'Company Discovery / Ranking (Filtering, Comparison, Explain Match)'),
        ('evidence_review_workbench', 'Evidence Review Workbench (Queue, Decision, Dispute, Re-Review)'),
        ('stewardship_refresh', 'Stewardship Universe Refresh (Source Discovery / Fetch / KPI Candidates)'),
        ('other', 'Other Instrumented Pipeline'),
    ]
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    # Final recommendation status — what the pipeline actually concluded,
    # recorded from real pipeline output, never summarised by an LLM.
    RECOMMENDATION_STATUS_CHOICES = [
        ('not_applicable', 'Not Applicable (no recommendation produced by this pipeline)'),
        ('produced', 'Recommendation Produced — Awaiting Human Review'),
        ('blocked', 'Blocked on Safety/Eligibility Grounds'),
        ('human_review_required', 'Human Review Explicitly Required'),
        ('recorded', 'Result Recorded'),
    ]

    # feat/company-halal-intelligence (PR 9): a session anchors to EITHER a
    # gold_intelligence.GoldProject OR a companies.CompanyProfile, never
    # both and never neither — enforced by the CheckConstraint below. This
    # is the one telemetry system for all EcoIQ pipelines (per that PR's
    # brief: "Do not create a second telemetry system"), so company
    # analysis reuses this same model rather than a parallel one.
    project = models.ForeignKey(
        'gold_intelligence.GoldProject', null=True, blank=True, on_delete=models.CASCADE,
        related_name='observatory_sessions',
    )
    company = models.ForeignKey(
        'companies.CompanyProfile', null=True, blank=True, on_delete=models.CASCADE,
        related_name='observatory_sessions',
    )
    kind = models.CharField(max_length=30, choices=KIND_CHOICES, default='other')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='observatory_sessions',
    )

    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='running')

    # Real counts recorded by the recorder at run time. NULL = not measured
    # for this session kind; 0 = measured and genuinely zero.
    evidence_retrieved_count = models.PositiveIntegerField(null=True, blank=True)
    evidence_reused_count = models.PositiveIntegerField(null=True, blank=True)

    human_review_required = models.BooleanField(default=True)
    human_review_completed = models.BooleanField(default=False)

    warnings = models.JSONField(default=list, blank=True)
    blocked_recommendation_count = models.PositiveIntegerField(default=0)
    final_recommendation_status = models.CharField(
        max_length=30, choices=RECOMMENDATION_STATUS_CHOICES, default='not_applicable',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-started_at']
        verbose_name = 'Analysis Session'
        constraints = [
            # feat/company-discovery-ranking (PR 11), generalised by feat/
            # evidence-review-workbench (PR 12): a discovery/ranking run or
            # a queue-wide review session spans MANY companies at once (or
            # none) — it genuinely has no single project or company to
            # anchor to. Rather than invent a placeholder anchor (which
            # would misrepresent what the session actually covered), the
            # constraint permits NEITHER anchor, but only for kinds in
            # NO_ANCHOR_ALLOWED_KINDS above — every other kind still
            # requires exactly one, unchanged. "Both anchors" remains
            # invalid for every kind, including these.
            models.CheckConstraint(
                check=(
                    models.Q(project__isnull=False, company__isnull=True)
                    | models.Q(project__isnull=True, company__isnull=False)
                    | models.Q(project__isnull=True, company__isnull=True, kind__in=NO_ANCHOR_ALLOWED_KINDS)
                ),
                name='observatory_session_exactly_one_anchor',
            ),
        ]

    def __str__(self):
        if self.project_id:
            anchor = self.project.name
        elif self.company_id:
            anchor = self.company.company.name
        else:
            anchor = 'cross-company'
        return f'{self.get_kind_display()} — {anchor} ({self.started_at:%Y-%m-%d %H:%M})'

    # Rollups over child rows — real aggregation, no cached copies to drift.
    @property
    def deterministic_stage_count(self):
        return self.stages.filter(category='deterministic').count()

    @property
    def retrieval_stage_count(self):
        return self.stages.filter(category='retrieval').count()

    @property
    def model_call_count(self):
        return self.model_invocations.count()

    @property
    def deterministic_step_ratio(self):
        """Deterministic + retrieval stages as a share of all recorded work
        units (stages + model calls). 1.0 means the entire pipeline ran
        without a single model generation. Documented on the Methodology
        page; returns None when nothing was recorded rather than faking 0."""
        stage_count = self.stages.count()
        total = stage_count + self.model_call_count
        if total == 0:
            return None
        return round(stage_count / total, 3)


class PipelineStageExecution(models.Model):
    CATEGORY_CHOICES = [
        ('deterministic', 'Deterministic Engine'),
        ('retrieval', 'Evidence Retrieval'),
        ('governance', 'Governance / Safety Check'),
        ('llm', 'Model-Backed Step'),
    ]

    session = models.ForeignKey(AnalysisSession, on_delete=models.CASCADE, related_name='stages')
    stage_key = models.CharField(max_length=60)
    label = models.CharField(max_length=120)
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES, default='deterministic')

    started_at = models.DateTimeField(default=timezone.now)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    success = models.BooleanField(default=True)
    # Real, stage-specific count (evidence rows loaded, options ranked,
    # candidates blocked, ...) — NULL when the stage has no natural count.
    items_processed = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['started_at', 'pk']
        verbose_name = 'Pipeline Stage Execution'

    def __str__(self):
        return f'{self.stage_key} ({self.category}, {self.duration_ms}ms)'


class ModelInvocation(models.Model):
    """One real LLM call. Token/streaming fields are nullable and stay NULL
    whenever the provider did not report them — values are never estimated
    into these columns (estimates live only in the proxy layer, labelled as
    such)."""
    session = models.ForeignKey(
        AnalysisSession, null=True, blank=True, on_delete=models.SET_NULL, related_name='model_invocations',
    )
    provider = models.CharField(max_length=40, blank=True)
    model_name = models.CharField(max_length=80, blank=True)
    model_version = models.CharField(max_length=80, blank=True)
    prompt_version = models.CharField(max_length=20, blank=True)

    input_tokens = models.PositiveIntegerField(null=True, blank=True)
    output_tokens = models.PositiveIntegerField(null=True, blank=True)
    cached_tokens = models.PositiveIntegerField(null=True, blank=True)
    streaming = models.BooleanField(null=True, blank=True)
    # feat/model-router-observatory: which attempt this physical provider
    # request was within its AgentRun, per provider (0 = first attempt,
    # 1 = the router's single bounded same-provider retry). One row exists
    # per PHYSICAL provider request — a retry is a second row, never a
    # mutation of the first.
    retry_count = models.PositiveIntegerField(default=0)
    # Measured wall-clock around the real adapter call, and whether that
    # call succeeded. Nullable: rows recorded through other paths that
    # didn't measure them stay honestly NULL.
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    succeeded = models.BooleanField(null=True, blank=True)

    # Soft link to the existing agent-runtime record when this invocation
    # came through the Model Router (which already stores real usage data) —
    # same soft-reference convention as evidence_memory.source_reference.
    agent_run_reference = models.CharField(max_length=120, blank=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Model Invocation'

    def __str__(self):
        return f'{self.provider}/{self.model_name} ({self.created_at:%Y-%m-%d %H:%M})'
