"""
good_agents/models.py — the 114 Good Agent principle lenses and the
opportunity-discovery pipeline they feed:

    Signal -> GoodAgentOrchestrator -> relevant GoodAgentDefinition lenses
    -> GoodOpportunity -> (existing OperationalLoss / Better Way / Capital
    decision pipeline in capital_guardian + waste_to_value_capital_allocation_engine,
    reused unchanged) -> OpportunityCostAssessment -> RedTeamReview ->
    GoodDeedAction -> ImpactReceipt -> evidence_memory (existing)

This app deliberately does NOT create a fourth Evidence model, a second
Project model, or a competing MRV/Command Centre app — see
docs/114_GOOD_AGENTS.md and docs/GOOD_AGENTS_PROGRESS.md for the audit
that ruled those out. Every FK below points at an existing model
(gold_intelligence.GoldProject, waste_to_value_capital_allocation_engine's
OperationalLoss/CapitalAllocationDecision/VerifiedCapitalOutcome,
countries.CountryProfile) and is additive-only per docs/adr-0001.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

# ---------------------------------------------------------------------------
# Global Good Taxonomy (Phase 17) — a plain choice list, not a model: the
# spec explicitly asks for room to grow, which an editable CharField with
# choices gives us without a lookup table nobody is populating yet.
# ---------------------------------------------------------------------------
GOOD_TAXONOMY_CHOICES = [
    ('energy', 'Energy'), ('water', 'Water'), ('food', 'Food'), ('housing', 'Housing'),
    ('health', 'Health'), ('education', 'Education'), ('employment', 'Employment'),
    ('poverty', 'Poverty'), ('justice', 'Justice'), ('environment', 'Environment'),
    ('biodiversity', 'Biodiversity'), ('waste', 'Waste'), ('circular_economy', 'Circular Economy'),
    ('climate_adaptation', 'Climate Adaptation'), ('infrastructure', 'Infrastructure'),
    ('government_efficiency', 'Government Efficiency'), ('financial_inclusion', 'Financial Inclusion'),
    ('digital_access', 'Digital Access'), ('community_resilience', 'Community Resilience'),
]


class GoodAgentDefinition(models.Model):
    """
    One of the 114 canonical EcoIQ principles, re-expressed as a specialised
    "Good Agent" lens for opportunity discovery.

    `principle_id` refers to the `id` (1-114) in
    core.esg_principles_data.PRINCIPLES — the single public, English,
    DB-independent canonical source. Two other "114" datasets exist
    elsewhere in this repo (core/views.py's hardcoded _SURAHS list and
    content/tazkiyah114/surah_seeds.json); both were audited and rejected
    as canonical for this app because neither is scholar-reviewed and both
    disagree with each other — see docs/114_GOOD_AGENTS.md. Not all 114
    need a row here; only principles actually wired into the orchestrator
    get one (see management command seed_good_agent_definitions).
    """
    ARABIC_REVIEW_STATUS_CHOICES = [
        ('not_applicable', 'Not applicable (no Arabic/Surah name attached)'),
        ('needs_scholar_review', 'Needs scholar review'),
        ('scholar_reviewed', 'Scholar reviewed'),
    ]
    # Distinguishes the original 6 hand-tuned lenses (real search_questions/
    # evidence_requirements/risk_flags written by a human) from the other
    # 108, auto-generated straight from core.esg_principles_data.PRINCIPLES
    # with minimal derived fields (PR3 Phase 23) — never fabricated
    # interpretation, just the canonical title/category/question restated.
    DEFINITION_QUALITY_CHOICES = [
        ('hand_tuned', 'Hand-tuned (curated domains/signal_types/evidence_requirements)'),
        ('auto_generated', 'Auto-generated from canonical source (minimal, requires human review)'),
    ]
    ACTIVATION_STATUS_CHOICES = [
        ('dormant', 'Dormant — never activated'),
        ('watching', 'Watching — eligible, no recent activation'),
        ('activated', 'Activated — currently attached to at least one live opportunity'),
        ('investigating', 'Investigating — deep reasoning in progress'),
        ('waiting_for_evidence', 'Waiting for evidence'),
    ]

    principle_id = models.PositiveSmallIntegerField(unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=40, blank=True)
    definition_quality = models.CharField(
        max_length=16, choices=DEFINITION_QUALITY_CHOICES, default='hand_tuned',
    )
    requires_human_review = models.BooleanField(default=False)
    activation_status = models.CharField(
        max_length=24, choices=ACTIVATION_STATUS_CHOICES, default='dormant',
    )
    last_activated_at = models.DateTimeField(null=True, blank=True)

    # Never surfaced publicly as verified religious authority — see Phase 23
    # safety rule and docs/GOOD_AGENT_SAFETY.md.
    arabic_name = models.CharField(max_length=200, blank=True)
    arabic_name_review_status = models.CharField(
        max_length=24, choices=ARABIC_REVIEW_STATUS_CHOICES, default='not_applicable',
    )

    mission = models.TextField()
    domains = models.JSONField(default=list, blank=True)
    signal_types = models.JSONField(default=list, blank=True)
    search_questions = models.JSONField(default=list, blank=True)
    evidence_requirements = models.JSONField(default=list, blank=True)
    risk_flags = models.JSONField(default=list, blank=True)
    default_priority = models.PositiveSmallIntegerField(default=50)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['principle_id']

    def __str__(self):
        return f'#{self.principle_id} {self.name}'

    def save(self, *args, **kwargs):
        if self.arabic_name and self.arabic_name_review_status == 'not_applicable':
            self.arabic_name_review_status = 'needs_scholar_review'
        super().save(*args, **kwargs)

    def mark_activated(self):
        self.activation_status = 'activated'
        self.last_activated_at = timezone.now()
        self.save(update_fields=['activation_status', 'last_activated_at', 'updated_at'])

    def mark_watching(self):
        if self.activation_status not in ('activated', 'investigating'):
            self.activation_status = 'watching'
            self.save(update_fields=['activation_status', 'updated_at'])

    @property
    def current_opportunities_count(self):
        """Real count, computed live — never a stored/stale number (Phase 22 status must be real, not decorative)."""
        return self.activations.filter(
            opportunity__status__in=['potential', 'qualified', 'approved', 'in_progress'],
        ).values('opportunity_id').distinct().count()

    @property
    def verified_impact_links_count(self):
        return self.activations.filter(
            opportunity__impact_receipt__verified_outcome__isnull=False,
        ).values('opportunity_id').distinct().count()


class GoodDiscoveryRun(models.Model):
    """
    One bounded, resumable "Good While You Sleep" discovery pass (Phase 12 /
    the Observatory's unit of work). Deliberately NOT a true cron job — this
    repo runs no scheduler (see docs/GOOD_WHILE_YOU_SLEEP.md) — it is
    triggered on demand (management command or, later, a Celery beat entry)
    following the same idempotent-row pattern as
    backend_intelligence_engine.BackgroundTaskRun /
    langgraph_orchestration.OrchestrationRun.
    """
    STATUS_CHOICES = [
        ('queued', 'Queued'), ('running', 'Running'),
        ('completed', 'Completed'), ('failed', 'Failed'),
    ]
    # PR3 Phase 13 — staged, checkpointed execution so a run can resume
    # after a crash/timeout instead of relying on one long-running request.
    STAGE_CHOICES = [
        ('fetch_signals', 'Fetch signals'), ('normalise', 'Normalise'),
        ('deduplicate', 'Deduplicate'), ('cluster', 'Cluster'), ('triage', 'Triage'),
        ('activate_agents', 'Activate agents'), ('verify_evidence', 'Verify evidence'),
        ('create_candidates', 'Create candidates'), ('match_resources', 'Match resources'),
        ('run_better_way', 'Run Better Way'), ('rank', 'Rank'),
        ('generate_brief', 'Generate brief'), ('done', 'Done'),
    ]
    STAGE_ORDER = [key for key, _ in STAGE_CHOICES]

    mission = models.CharField(max_length=255)
    mission_config = models.ForeignKey(
        'GoodMission', null=True, blank=True, on_delete=models.SET_NULL, related_name='runs',
    )
    geography = models.CharField(max_length=150, blank=True)
    themes = models.JSONField(default=list, blank=True)
    capital_budget_usd = models.FloatField(null=True, blank=True)
    cost_budget_usd = models.FloatField(default=5.0)

    idempotency_key = models.CharField(max_length=200, blank=True, null=True, unique=True)
    celery_task_id = models.CharField(max_length=64, blank=True)

    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='queued')
    current_stage = models.CharField(max_length=24, choices=STAGE_CHOICES, blank=True)
    # {"fetch_signals": "2026-07-22T10:00:00Z", ...} — one entry per completed
    # stage, so a resumed run skips work it already finished rather than
    # redoing it (and re-spending LLM budget) from scratch.
    stage_checkpoints = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    signals_reviewed = models.PositiveIntegerField(default=0)
    agents_activated = models.PositiveIntegerField(default=0)
    opportunities_detected = models.PositiveIntegerField(default=0)
    qualified_opportunities = models.PositiveIntegerField(default=0)
    rejected_opportunities = models.PositiveIntegerField(default=0)
    zero_capital_opportunities = models.PositiveIntegerField(default=0)
    duplicates_removed = models.PositiveIntegerField(default=0)
    insufficient_evidence_count = models.PositiveIntegerField(default=0)
    estimated_run_cost_usd = models.FloatField(default=0.0)
    errors = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.mission} [{self.status}]'

    def mark_running(self):
        self.status = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])

    def mark_completed(self):
        self.status = 'completed'
        self.current_stage = 'done'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'current_stage', 'completed_at'])

    def mark_failed(self, error_message):
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.errors = [*self.errors, str(error_message)]
        self.save(update_fields=['status', 'completed_at', 'errors'])

    def over_budget(self):
        return self.estimated_run_cost_usd > self.cost_budget_usd

    def checkpoint(self, stage):
        """Records a stage as complete. Idempotent — re-checkpointing the same stage just updates the timestamp."""
        self.current_stage = stage
        self.stage_checkpoints = {**self.stage_checkpoints, stage: timezone.now().isoformat()}
        self.save(update_fields=['current_stage', 'stage_checkpoints'])

    def stage_done(self, stage):
        return stage in self.stage_checkpoints

    def remaining_stages(self):
        """Stages not yet checkpointed, in canonical order — what a resumed run still has to do."""
        return [s for s in self.STAGE_ORDER if s != 'done' and s not in self.stage_checkpoints]


class GoodOpportunity(models.Model):
    """
    A candidate "good that can be done" — problem/unmet-need/waste plus
    everything needed to reason about it. Impact numbers are namespaced by
    stage (estimated/target/measured/verified) inside `potential_benefit`
    rather than collapsed into a single score — see Phase 3's explicit ban
    on a fake universal score.
    """
    STATUS_CHOICES = [
        ('potential', 'Potential'), ('qualified', 'Qualified'), ('approved', 'Approved'),
        ('in_progress', 'In progress'), ('measured', 'Measured'), ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]

    title = models.CharField(max_length=255)
    theme = models.CharField(max_length=32, choices=GOOD_TAXONOMY_CHOICES, blank=True)
    problem_statement = models.TextField()
    unmet_need_or_waste = models.TextField(blank=True)

    # Geography kept region-level only — never a precise address or
    # individual identifier (Phase 19 privacy-by-design).
    geography = models.ForeignKey(
        'countries.CountryProfile', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='good_opportunities',
    )
    region = models.CharField(max_length=150, blank=True)
    sector = models.CharField(max_length=100, blank=True)
    affected_population = models.CharField(max_length=255, blank=True)

    project = models.ForeignKey(
        'gold_intelligence.GoldProject', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='good_opportunities',
    )
    operational_loss = models.ForeignKey(
        'waste_to_value_capital_allocation_engine.OperationalLoss', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='good_opportunities',
    )
    discovery_run = models.ForeignKey(
        GoodDiscoveryRun, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='opportunities',
    )

    detected_signals = models.JSONField(default=list, blank=True)
    relevant_principle_ids = models.JSONField(default=list, blank=True)
    evidence_refs = models.JSONField(default=list, blank=True)
    insufficient_evidence = models.BooleanField(default=False)

    baseline = models.TextField(blank=True)
    potential_intervention = models.TextField(blank=True)
    # {"people_helped": {"value": 200, "unit": "households", "stage": "estimated"}, ...}
    potential_benefit = models.JSONField(default=dict, blank=True)

    risk = models.TextField(blank=True)
    confidence = models.FloatField(default=0.0)
    urgency = models.FloatField(default=0.0)
    feasibility = models.FloatField(default=0.0)
    scalability = models.TextField(blank=True)

    capital_required_usd = models.FloatField(null=True, blank=True)
    zero_capital_possible = models.BooleanField(default=False)
    zero_capital_action_plan = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='potential')

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Good Opportunity'
        verbose_name_plural = 'Good Opportunities'

    def __str__(self):
        return self.title

    IMPACT_STAGE_ORDER = ['estimated', 'target', 'measured', 'verified']

    def impact_dimension(self, key):
        """Return the {value, unit, stage} dict for one impact dimension, or None."""
        return self.potential_benefit.get(key)


class AgentActivationRecord(models.Model):
    """
    Observability row (Phase 20) recording why one GoodAgentDefinition lens
    activated for one GoodOpportunity, and its position — preserving
    disagreement between lenses rather than averaging it away (Phase 10).
    """
    POSITION_CHOICES = [
        ('support', 'Support'), ('concerns', 'Concerns'), ('conflicts', 'Conflicts'),
    ]

    opportunity = models.ForeignKey(GoodOpportunity, on_delete=models.CASCADE, related_name='agent_activations')
    agent = models.ForeignKey(GoodAgentDefinition, on_delete=models.PROTECT, related_name='activations')

    reason_activated = models.TextField()
    evidence_considered = models.JSONField(default=list, blank=True)
    position = models.CharField(max_length=20, choices=POSITION_CHOICES, default='support')
    confidence = models.FloatField(default=0.0)
    concern = models.TextField(blank=True)
    recommended_next_analysis = models.TextField(blank=True)

    cost_usd = models.FloatField(default=0.0)
    latency_ms = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['opportunity_id', 'agent__principle_id']
        unique_together = [('opportunity', 'agent')]

    def __str__(self):
        return f'{self.agent} -> {self.opportunity} ({self.position})'


class OpportunityCostAssessment(models.Model):
    """
    Output of the system-level OpportunityCostAgent (Phase 8) — explicitly
    NOT one of the 114 principle lenses. Answers "could this same capital/
    time/attention create materially more good elsewhere?"
    """
    opportunity = models.OneToOneField(
        GoodOpportunity, on_delete=models.CASCADE, related_name='opportunity_cost_assessment',
    )
    alternatives_considered = models.JSONField(default=list, blank=True)
    preferred_option = models.TextField()
    best_alternative = models.TextField(blank=True)
    trade_offs = models.JSONField(default=dict, blank=True)
    confidence = models.FloatField(default=0.0)
    evidence_that_would_change_recommendation = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'Opportunity cost — {self.opportunity_id}'


class RedTeamReview(models.Model):
    """
    Harm-prevention challenge (Phase 9) that every significant recommendation
    must pass through. A "good" intention alone is not sufficient.
    """
    opportunity = models.OneToOneField(GoodOpportunity, on_delete=models.CASCADE, related_name='red_team_review')

    who_benefits = models.TextField(blank=True)
    who_bears_cost = models.TextField(blank=True)
    who_may_be_harmed = models.TextField(blank=True)
    hidden_externalities = models.TextField(blank=True)
    dependency_risk = models.TextField(blank=True)
    misleading_impact_risk = models.TextField(blank=True)
    greenwashing_risk = models.TextField(blank=True)
    conflict_of_interest = models.TextField(blank=True)
    contradicting_evidence = models.TextField(blank=True)

    cleared = models.BooleanField(default=False)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'Red team review — {self.opportunity_id}'


# ---------------------------------------------------------------------------
# GoodDeedAction autonomy classification (Phase 4). RED is deliberately
# unreachable through this action-type enum today: none of the 17 action
# types represents moving money, signing an agreement, or executing physical
# works, because this repo has no real execution layer (see the Phase 0
# audit, area 11 — Execution is a confirmed dead end: the existing capital
# pipeline stops at "decision approved", then a human enters what happened
# later). Adding a real execution capability in future must add its new
# action type to RED_ACTION_TYPES, never assume GREEN/YELLOW by default.
# ---------------------------------------------------------------------------
GREEN_ACTION_TYPES = frozenset({
    'research', 'verify', 'analyse', 'compare', 'find_resource', 'find_funding',
    'find_partner', 'draft', 'recommend', 'prepare_application', 'prepare_policy_brief',
    'prepare_pilot', 'prepare_investment_memo', 'monitor',
})
YELLOW_ACTION_TYPES = frozenset({'match', 'connect', 'alert'})
RED_ACTION_TYPES = frozenset()  # no action type in this system reaches RED — see docstring above


def classify_autonomy(action_type):
    if action_type in RED_ACTION_TYPES:
        return 'red'
    if action_type in YELLOW_ACTION_TYPES:
        return 'yellow'
    if action_type in GREEN_ACTION_TYPES:
        return 'green'
    raise ValueError(f'Unknown action_type: {action_type!r}')


class GoodDeedAction(models.Model):
    """A next-step action the GoodDeedsEngine proposed for one GoodOpportunity."""
    ACTION_TYPE_CHOICES = [
        ('research', 'Research'), ('verify', 'Verify'), ('analyse', 'Analyse'), ('compare', 'Compare'),
        ('find_resource', 'Find resource'), ('find_funding', 'Find funding'), ('find_partner', 'Find partner'),
        ('match', 'Match'), ('connect', 'Connect'), ('draft', 'Draft'), ('recommend', 'Recommend'),
        ('alert', 'Alert'), ('prepare_application', 'Prepare application'),
        ('prepare_policy_brief', 'Prepare policy brief'), ('prepare_pilot', 'Prepare pilot'),
        ('prepare_investment_memo', 'Prepare investment memo'), ('monitor', 'Monitor'),
    ]
    AUTONOMY_CLASS_CHOICES = [
        ('green', 'GREEN — safe autonomous preparation'),
        ('yellow', 'YELLOW — human approval before external action'),
        ('red', 'RED — capital/legal/contractual/physical execution, never auto-executed'),
    ]
    STATUS_CHOICES = [
        ('proposed', 'Proposed'), ('awaiting_approval', 'Awaiting human approval'),
        ('approved', 'Approved'), ('completed', 'Completed'), ('blocked', 'Blocked'),
    ]

    opportunity = models.ForeignKey(GoodOpportunity, on_delete=models.CASCADE, related_name='actions')
    action_type = models.CharField(max_length=32, choices=ACTION_TYPE_CHOICES)
    autonomy_class = models.CharField(max_length=10, choices=AUTONOMY_CLASS_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='proposed')
    human_approved = models.BooleanField(null=True, blank=True)
    blocked_reason = models.TextField(blank=True)
    output_summary = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_action_type_display()} [{self.autonomy_class}] — {self.opportunity_id}'

    def clean(self):
        expected = classify_autonomy(self.action_type)
        if self.autonomy_class != expected:
            raise ValidationError(
                f'{self.action_type} must be autonomy_class={expected!r}, got {self.autonomy_class!r}'
            )
        if self.autonomy_class in ('yellow', 'red') and self.status == 'completed' and not self.human_approved:
            raise ValidationError(
                f'A {self.autonomy_class.upper()} action cannot be marked completed without human_approved=True'
            )
        if self.autonomy_class == 'red':
            # Structural guarantee: this codebase has no execution capability
            # for RED actions, so RED can never legitimately reach 'completed'.
            raise ValidationError('RED actions must never be auto-executed by this system.')

    def save(self, *args, **kwargs):
        if not self.autonomy_class:
            self.autonomy_class = classify_autonomy(self.action_type)
        self.full_clean()
        super().save(*args, **kwargs)


class ImpactReceipt(models.Model):
    """
    The closing artifact of one completed intervention (Phase 15) — feeds
    evidence_memory (existing app, unchanged) via
    evidence_memory.services.memory.create_memory_from_verified_outcome,
    called against the linked VerifiedCapitalOutcome.
    """
    opportunity = models.OneToOneField(GoodOpportunity, on_delete=models.CASCADE, related_name='impact_receipt')
    decision = models.ForeignKey(
        'waste_to_value_capital_allocation_engine.CapitalAllocationDecision', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='good_agent_impact_receipts',
    )
    verified_outcome = models.OneToOneField(
        'waste_to_value_capital_allocation_engine.VerifiedCapitalOutcome', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='impact_receipt',
    )

    problem = models.TextField()
    baseline = models.TextField(blank=True)
    evidence_summary = models.JSONField(default=list, blank=True)
    principles_applied = models.JSONField(default=list, blank=True)
    decision_summary = models.TextField(blank=True)
    alternative_considered = models.TextField(blank=True)
    better_way_summary = models.TextField(blank=True)
    capital_resources_used = models.TextField(blank=True)
    partners = models.TextField(blank=True)
    action_taken = models.TextField(blank=True)
    expected_result = models.JSONField(default=dict, blank=True)
    measured_result = models.JSONField(default=dict, blank=True)
    mrv_methodology = models.TextField(blank=True)
    evidence_after_implementation = models.JSONField(default=list, blank=True)
    lessons_learned = models.TextField(blank=True)
    confidence = models.FloatField(default=0.0)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Impact receipt — {self.opportunity_id}'


# ===========================================================================
# PR3 — Global Good Discovery + Good While You Sleep + Need/Resource Matching
#
# Everything below is additive to the PR2 models above. Nothing here rewrites
# or duplicates the PR2 pipeline (GoodOpportunity, Better Way, Capital
# Guardian, MRV, ImpactReceipt, Evidence Memory) — a qualified opportunity
# still flows through exactly those unmodified services. This layer's job is
# only to get a GoodOpportunity created without a human submitting the
# problem by hand, and to attach matched resources to it before Better Way
# runs. See docs/GLOBAL_GOOD_DISCOVERY.md.
# ===========================================================================


class GoodMission(models.Model):
    """
    A standing discovery configuration a human defines once and re-runs
    (PR3 Phase 12) — e.g. "Find zero-capital opportunities to reduce energy
    poverty." Not itself scheduled by a cron — see
    docs/GOOD_WHILE_YOU_SLEEP.md for why no real scheduler exists yet;
    `schedule` here is a human-readable description a future beat entry
    would read, not an enforced cadence.
    """
    RISK_TOLERANCE_CHOICES = [('low', 'Low'), ('medium', 'Medium'), ('high', 'High')]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    geographies = models.JSONField(default=list, blank=True)
    themes = models.JSONField(default=list, blank=True)
    principle_ids = models.JSONField(default=list, blank=True)  # empty = orchestrator picks from all seeded lenses
    capital_budget_usd = models.FloatField(null=True, blank=True)
    run_cost_budget_usd = models.FloatField(default=5.0)
    risk_tolerance = models.CharField(max_length=10, choices=RISK_TOLERANCE_CHOICES, default='medium')
    min_confidence = models.FloatField(default=40.0)
    max_opportunities = models.PositiveIntegerField(default=10)
    schedule = models.CharField(max_length=120, blank=True)
    enabled = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class SignalProvider(models.Model):
    """
    Provider/adaptor registry entry (PR3 Phase 1) — describes WHERE a signal
    could come from without this app scraping the internet itself. No
    provider here has a live `fetchMethod` implementation; `fetch_method` is
    a human-readable description of the intended mechanism. Real ingestion
    (an actual HTTP client hitting a real dataset) is explicitly out of
    scope for this PR — see docs/GLOBAL_GOOD_DISCOVERY.md.
    """
    TYPE_CHOICES = [
        ('public_dataset', 'Public dataset'), ('government_publication', 'Government publication'),
        ('regulatory_announcement', 'Regulatory announcement'), ('company_disclosure', 'Company disclosure'),
        ('ngo_report', 'NGO report'), ('news', 'News'), ('research', 'Research'),
        ('climate_environmental_dataset', 'Climate/environmental dataset'), ('energy_data', 'Energy data'),
        ('procurement_data', 'Procurement data'), ('grant_database', 'Grant database'),
        ('user_submitted', 'User-submitted evidence'), ('existing_project', 'Existing EcoIQ project'),
        ('observatory_feed', 'Observatory feed'),
    ]
    TRUST_TIER_CHOICES = [('high', 'High'), ('medium', 'Medium'), ('low', 'Low')]
    STATUS_CHOICES = [
        ('active', 'Active'), ('inactive', 'Inactive'), ('failed', 'Failed'), ('stale', 'Stale'),
    ]

    slug = models.SlugField(max_length=120, unique=True)
    name = models.CharField(max_length=200)
    provider_type = models.CharField(max_length=32, choices=TYPE_CHOICES)
    geographies = models.JSONField(default=list, blank=True)
    domains = models.JSONField(default=list, blank=True)
    trust_tier = models.CharField(max_length=10, choices=TRUST_TIER_CHOICES, default='medium')
    fetch_method = models.TextField(blank=True)
    refresh_cadence = models.CharField(max_length=80, blank=True)
    cost_usd_per_refresh = models.FloatField(default=0.0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='inactive')
    last_refresh_at = models.DateTimeField(null=True, blank=True)
    last_failure_at = models.DateTimeField(null=True, blank=True)
    last_failure_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def mark_refreshed(self):
        self.status = 'active'
        self.last_refresh_at = timezone.now()
        self.save(update_fields=['status', 'last_refresh_at', 'updated_at'])

    def mark_failed(self, reason):
        self.status = 'failed'
        self.last_failure_at = timezone.now()
        self.last_failure_reason = reason
        self.save(update_fields=['status', 'last_failure_at', 'last_failure_reason', 'updated_at'])

    def is_stale(self, max_age_hours=168):
        if self.last_refresh_at is None:
            return self.status == 'active'
        return (timezone.now() - self.last_refresh_at).total_seconds() > max_age_hours * 3600


class SignalCluster(models.Model):
    """
    Groups WorldSignals that likely describe the same real-world situation
    (PR3 Phase 3) — a heating-cost news story and a government energy-poverty
    report about the same region should strengthen one cluster's confidence,
    not become two separate opportunities.
    """
    STATUS_CHOICES = [('open', 'Open'), ('triaged', 'Triaged'), ('discarded', 'Discarded')]

    representative_title = models.CharField(max_length=255)
    signal_type = models.CharField(max_length=24, blank=True)
    geography = models.CharField(max_length=150, blank=True)
    sector = models.CharField(max_length=100, blank=True)
    confidence_boost = models.FloatField(default=0.0)
    contradiction_notes = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.representative_title

    @property
    def corroboration_count(self):
        return self.signals.values('provider_id').distinct().count()


class WorldSignal(models.Model):
    """
    Canonical normalised signal (PR3 Phase 2). Every raw signal a
    SignalProvider (or a human) supplies is normalised into one of these
    before anything downstream sees it — the orchestrator's
    `Signal` dataclass (services/orchestrator.py) is now built FROM a
    WorldSignal, not a free-floating dict, once a signal has been persisted.
    """
    TYPE_CHOICES = [
        ('need', 'Need'), ('harm', 'Harm'), ('waste', 'Waste'), ('risk', 'Risk'),
        ('resource', 'Resource'), ('funding', 'Funding'), ('policy_change', 'Policy change'),
        ('technology_change', 'Technology change'), ('price_change', 'Price change'),
        ('opportunity', 'Opportunity'), ('emergency', 'Emergency'),
    ]
    CLASSIFICATION_CHOICES = [('fact', 'Fact'), ('claim', 'Claim'), ('inference', 'Inference')]
    STATUS_CHOICES = [
        ('new', 'New'), ('clustered', 'Clustered'), ('triaged', 'Triaged'), ('discarded', 'Discarded'),
    ]

    signal_type = models.CharField(max_length=24, choices=TYPE_CHOICES)
    title = models.CharField(max_length=255)
    summary = models.TextField(blank=True)
    geography = models.ForeignKey(
        'countries.CountryProfile', null=True, blank=True, on_delete=models.SET_NULL, related_name='world_signals',
    )
    region = models.CharField(max_length=150, blank=True)
    sector = models.CharField(max_length=100, blank=True)
    entities = models.JSONField(default=list, blank=True)

    provider = models.ForeignKey(
        SignalProvider, null=True, blank=True, on_delete=models.SET_NULL, related_name='signals',
    )
    source_url = models.URLField(blank=True, max_length=2000)
    publisher = models.CharField(max_length=200, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    retrieved_at = models.DateTimeField(default=timezone.now)
    # Soft pointer, same pattern as evidence_memory.EvidenceMemory.source_reference
    # — never a hard FK, since raw evidence can live in any of the 3
    # existing Evidence models (harvester/hikma/league) or be manual.
    raw_evidence_ref = models.CharField(max_length=200, blank=True)

    confidence = models.FloatField(default=0.0)
    freshness = models.FloatField(default=0.0)
    severity = models.FloatField(default=0.0)
    potential_affected_population = models.CharField(max_length=255, blank=True)
    tags = models.JSONField(default=list, blank=True)
    content_classification = models.CharField(max_length=10, choices=CLASSIFICATION_CHOICES, default='claim')

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='new')
    # sha256 of (signal_type, geography/region, sector, normalised title) —
    # the anti-duplication key (Phase 27). Not unique at the DB level
    # (duplicates are expected to arrive and get clustered, not rejected at
    # insert time) but indexed for fast lookup.
    dedup_key = models.CharField(max_length=64, blank=True, db_index=True)
    cluster = models.ForeignKey(
        SignalCluster, null=True, blank=True, on_delete=models.SET_NULL, related_name='signals',
    )

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Need(models.Model):
    """Global Need model (PR3 Phase 6) — the demand side of the matching network."""
    NEED_TYPE_CHOICES = [(v, v.replace('_', ' ').title()) for v in [
        'energy', 'water', 'food', 'housing', 'health', 'education', 'employment', 'justice',
        'environment', 'biodiversity', 'waste', 'climate', 'infrastructure', 'digital_access',
        'financial_inclusion', 'community_resilience',
    ]]
    STATUS_CHOICES = [
        ('open', 'Open'), ('matched', 'Matched'), ('resolved', 'Resolved'), ('monitoring', 'Monitoring'),
    ]

    need_type = models.CharField(max_length=32, choices=NEED_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    geography = models.ForeignKey(
        'countries.CountryProfile', null=True, blank=True, on_delete=models.SET_NULL, related_name='needs',
    )
    region = models.CharField(max_length=150, blank=True)
    # Deliberately a short description, never a list of named individuals —
    # privacy-by-design (Phase 19), same discipline as GoodOpportunity.affected_population.
    affected_group = models.CharField(max_length=255, blank=True)
    urgency = models.FloatField(default=0.0)
    severity = models.FloatField(default=0.0)
    evidence_refs = models.JSONField(default=list, blank=True)
    required_capabilities = models.JSONField(default=list, blank=True)
    resource_requirements = models.JSONField(default=list, blank=True)
    constraints = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')

    opportunity = models.ForeignKey(
        GoodOpportunity, null=True, blank=True, on_delete=models.SET_NULL, related_name='needs',
    )
    signal = models.ForeignKey(
        WorldSignal, null=True, blank=True, on_delete=models.SET_NULL, related_name='needs',
    )
    dedup_key = models.CharField(max_length=64, blank=True, db_index=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-urgency', '-created_at']

    def __str__(self):
        return self.title


class AvailableResource(models.Model):
    """Global Resource model (PR3 Phase 7) — the supply side. Never claims availability without an evidence reference."""
    RESOURCE_TYPE_CHOICES = [(v, v.replace('_', ' ').title()) for v in [
        'capital', 'grant', 'subsidy', 'government_programme', 'waqf', 'philanthropy',
        'impact_investment', 'islamic_finance', 'asset', 'building', 'land', 'equipment',
        'food_surplus', 'energy_surplus', 'waste_heat', 'material_surplus', 'technology',
        'expertise', 'labour', 'data', 'logistics', 'supplier', 'ngo', 'implementer',
        'public_infrastructure',
    ]]
    AVAILABILITY_CHOICES = [
        ('available', 'Available'), ('limited', 'Limited'), ('unknown', 'Unknown'), ('expired', 'Expired'),
    ]
    STATUS_CHOICES = [('active', 'Active'), ('expired', 'Expired'), ('withdrawn', 'Withdrawn')]

    resource_type = models.CharField(max_length=32, choices=RESOURCE_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    geography = models.ForeignKey(
        'countries.CountryProfile', null=True, blank=True, on_delete=models.SET_NULL, related_name='available_resources',
    )
    region = models.CharField(max_length=150, blank=True)
    availability = models.CharField(max_length=10, choices=AVAILABILITY_CHOICES, default='unknown')
    eligibility = models.TextField(blank=True)
    capacity = models.TextField(blank=True)
    constraints = models.TextField(blank=True)
    source = models.CharField(max_length=255, blank=True)
    evidence_refs = models.JSONField(default=list, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    confidence = models.FloatField(default=0.0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    dedup_key = models.CharField(max_length=64, blank=True, db_index=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-confidence', '-created_at']

    def __str__(self):
        return self.title

    def is_expired(self):
        return bool(self.expiry_date and self.expiry_date < timezone.now().date())


class ResourceStatusChange(models.Model):
    """
    Append-only history (PR3 Phase 28 — temporal memory): world conditions
    change (a grant closes, a price shifts) and this app must never silently
    overwrite what it previously believed — it records what changed, when.
    """
    resource = models.ForeignKey(AvailableResource, on_delete=models.CASCADE, related_name='status_history')
    previous_status = models.CharField(max_length=10, blank=True)
    new_status = models.CharField(max_length=10)
    previous_availability = models.CharField(max_length=10, blank=True)
    new_availability = models.CharField(max_length=10)
    reason = models.TextField(blank=True)
    changed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f'{self.resource_id}: {self.previous_status} -> {self.new_status}'


class ResourceMatch(models.Model):
    """Output of NeedResourceMatcher / CircularEconomyMatcher (PR3 Phase 8-9)."""
    need = models.ForeignKey(Need, on_delete=models.CASCADE, related_name='matches')
    resource = models.ForeignKey(AvailableResource, on_delete=models.CASCADE, related_name='matches')
    match_reason = models.TextField()
    constraints = models.TextField(blank=True)
    confidence = models.FloatField(default=0.0)
    missing_evidence = models.JSONField(default=list, blank=True)
    next_action = models.TextField(blank=True)
    is_circular_economy_match = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-confidence']
        unique_together = [('need', 'resource')]

    def __str__(self):
        return f'{self.need_id} <-> {self.resource_id} ({self.confidence:.0f}%)'


class FundingMatch(models.Model):
    """
    FundingMatcher output (PR3 Phase 11). Deliberately conservative: never
    sets `eligible` without real evidence, and always routes Islamic-finance/
    waqf funder types to REQUIRES_SHARIA_REVIEW rather than assessing
    Sharia compliance itself (see docs/GOOD_AGENT_SAFETY.md — this system
    never determines Sharia compliance).
    """
    FUNDER_TYPE_CHOICES = [(v, v.replace('_', ' ').title()) for v in [
        'government_programme', 'grant', 'development_finance', 'impact_investor',
        'family_office', 'philanthropy', 'waqf', 'islamic_finance', 'green_finance', 'corporate',
    ]]
    ELIGIBILITY_STATUS_CHOICES = [
        ('potentially_relevant', 'Potentially relevant'), ('eligibility_unknown', 'Eligibility unknown'),
        ('eligible', 'Eligible'), ('not_eligible', 'Not eligible'),
        ('requires_sharia_review', 'Requires Sharia review'),
    ]
    SHARIA_SENSITIVE_FUNDER_TYPES = frozenset({'waqf', 'islamic_finance'})

    opportunity = models.ForeignKey(GoodOpportunity, on_delete=models.CASCADE, related_name='funding_matches')
    resource = models.ForeignKey(
        AvailableResource, null=True, blank=True, on_delete=models.SET_NULL, related_name='funding_matches',
    )
    funder_type = models.CharField(max_length=24, choices=FUNDER_TYPE_CHOICES)
    eligibility_status = models.CharField(max_length=24, choices=ELIGIBILITY_STATUS_CHOICES, default='eligibility_unknown')
    notes = models.TextField(blank=True)
    evidence_refs = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_funder_type_display()} — {self.get_eligibility_status_display()}'

    def save(self, *args, **kwargs):
        if self.funder_type in self.SHARIA_SENSITIVE_FUNDER_TYPES and self.eligibility_status == 'eligible':
            # Structural guarantee — never let this model itself assert Sharia compliance.
            self.eligibility_status = 'requires_sharia_review'
        super().save(*args, **kwargs)


class ZeroCapitalStrategyAction(models.Model):
    """Ranked zero-capital-first actions for an opportunity (PR3 Phase 10)."""
    ACTION_TYPE_CHOICES = [(v, v.replace('_', ' ').title()) for v in [
        'connect', 'introduce', 'redirect', 'inform', 'analyse', 'prepare', 'match', 'reuse',
        'share', 'identify_programme', 'identify_subsidy', 'identify_grant', 'identify_idle_asset',
        'identify_existing_budget', 'reduce_waste',
    ]]

    opportunity = models.ForeignKey(GoodOpportunity, on_delete=models.CASCADE, related_name='zero_capital_actions')
    action_type = models.CharField(max_length=32, choices=ACTION_TYPE_CHOICES)
    rank = models.PositiveSmallIntegerField(default=1)
    rationale = models.TextField(blank=True)
    resource_match = models.ForeignKey(
        ResourceMatch, null=True, blank=True, on_delete=models.SET_NULL, related_name='zero_capital_actions',
    )

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['opportunity_id', 'rank']
        unique_together = [('opportunity', 'action_type')]

    def __str__(self):
        return f'{self.get_action_type_display()} (#{self.rank}) — {self.opportunity_id}'


class HumanReviewDecision(models.Model):
    """Feedback loop (PR3 Phase 29) — tracks human review outcomes on an opportunity, never overwritten."""
    DECISION_CHOICES = [
        ('approved', 'Approved'), ('rejected', 'Rejected'),
        ('deferred', 'Deferred'), ('needs_more_evidence', 'Needs more evidence'),
    ]

    opportunity = models.ForeignKey(GoodOpportunity, on_delete=models.CASCADE, related_name='review_decisions')
    decision = models.CharField(max_length=24, choices=DECISION_CHOICES)
    rationale = models.TextField(blank=True)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_decision_display()} — {self.opportunity_id}'


class CrossBorderAssessment(models.Model):
    """
    Architecture for cross-border discovery (PR3 Phase 25) — a need in one
    country may be solved by a resource/pattern from another. This model
    holds the structured assessment; no automated transferability scoring
    is implemented (would require real comparative data this repo doesn't
    have) — fields are populated by a human/analyst, not computed.
    """
    opportunity = models.OneToOneField(GoodOpportunity, on_delete=models.CASCADE, related_name='cross_border_assessment')
    origin_geography = models.CharField(max_length=150, blank=True)
    candidate_geography = models.CharField(max_length=150, blank=True)
    regulation_notes = models.TextField(blank=True)
    logistics_notes = models.TextField(blank=True)
    currency_notes = models.TextField(blank=True)
    cultural_fit_notes = models.TextField(blank=True)
    climate_notes = models.TextField(blank=True)
    transferability_notes = models.TextField(blank=True)
    local_implementation_notes = models.TextField(blank=True)
    confidence = models.FloatField(default=0.0)

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'Cross-border assessment — {self.opportunity_id}'
