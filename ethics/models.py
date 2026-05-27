"""
EcoIQ Ethical Intelligence — Models.

FormulaDefinition    Registry of the 33 EcoIQ sub-formulas + 3 master formulas.
CompanyEthicsProfile Stores the 3 master-formula outputs for a company.
FormulaScore         Computed score per formula per company (auditability).
ImprovementMilestone KPI improvement roadmap milestone for a company.
AnalystNote          Structured analyst note for review/approval workflow.

Architecture
============
Three master formulas (public-facing):
  NEI  Net Ethical Impact          — benefit vs. harm balance
  TSS  Transition Stewardship Score — active harm reduction trajectory
  RVI  Regenerative Value Index    — long-term societal value creation

These compress a 33-formula internal framework across 8 categories,
internally mapped to five universal preservation principles.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


# ── Choice sets ────────────────────────────────────────────────────────────────

CATEGORY_CHOICES = [
    ('environmental_balance',    'Environmental Balance'),
    ('industrial_efficiency',    'Industrial Efficiency'),
    ('transparency_governance',  'Transparency & Governance'),
    ('public_benefit',           'Public Benefit'),
    ('restoration_regeneration', 'Restoration & Regeneration'),
    ('long_term_sustainability', 'Long-Term Sustainability'),
    ('ethical_capital',          'Ethical Capital Allocation'),
    ('anti_corruption',          'Anti-Corruption & Accountability'),
]

MASTER_FORMULA_CHOICES = [
    ('NEI', 'Net Ethical Impact'),
    ('TSS', 'Transition Stewardship Score'),
    ('RVI', 'Regenerative Value Index'),
    ('ALL', 'Cross-cutting / All Formulas'),
]

# Internal Maqasid-inspired mapping layer (not exposed in public UI)
MAQASID_CHOICES = [
    ('life',     'Preservation of Life & Health'),
    ('intellect','Preservation of Intellect & Knowledge'),
    ('wealth',   'Preservation of Real Wealth & Value'),
    ('society',  'Preservation of Society & Future Generations'),
    ('trust',    'Preservation of Trust & Ethical Integrity'),
]

MILESTONE_STATUS_CHOICES = [
    ('recommended', 'Recommended'),
    ('in_progress', 'In Progress'),
    ('completed',   'Completed'),
    ('deferred',    'Deferred'),
]

NOTE_TYPE_CHOICES = [
    ('observation',  'Observation'),
    ('flag',         'Flag for Review'),
    ('verification', 'Verification Note'),
    ('approval',     'Approval'),
    ('correction',   'Correction'),
]

EFFORT_CHOICES = [
    ('low',    'Low'),
    ('medium', 'Medium'),
    ('high',   'High'),
]


# ── FormulaDefinition ──────────────────────────────────────────────────────────

class FormulaDefinition(models.Model):
    """
    Registry of all EcoIQ scoring formulas.
    Defines the architecture for the full 33-formula framework
    (plus 3 master formulas = 36 entries total in production).

    The `is_public` flag controls which formulas appear on the
    public-facing methodology page.
    """
    code             = models.CharField(max_length=10, unique=True,
                        help_text='Short code, e.g. EB_01, NEI')
    name             = models.CharField(max_length=200)
    category         = models.CharField(max_length=30, choices=CATEGORY_CHOICES,
                        blank=True, help_text='Blank for master formulas')
    master_formula   = models.CharField(max_length=5, choices=MASTER_FORMULA_CHOICES,
                        default='ALL',
                        help_text='Which master formula this sub-formula feeds into')
    description      = models.TextField()
    methodology_notes= models.TextField(blank=True,
                        help_text='Technical implementation notes (internal)')

    # Input specification (for documentation and future automation)
    input_fields     = models.JSONField(default=list, blank=True,
                        help_text='List of {field, source, description} dicts')

    # Maqasid mapping (internal / methodology-level only)
    maqasid_principle= models.CharField(max_length=15, choices=MAQASID_CHOICES,
                        blank=True)
    maqasid_notes    = models.TextField(blank=True,
                        help_text='Internal mapping notes — do not expose in public UI')

    # Relative weight within its master formula (used for weighted aggregation)
    weight           = models.FloatField(default=1.0,
                        help_text='Relative weight within master formula (0-1)')

    # Visibility
    is_public        = models.BooleanField(default=False,
                        help_text='Show on public methodology page')
    is_active        = models.BooleanField(default=True)

    order            = models.PositiveSmallIntegerField(default=0)
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['category', 'order', 'code']
        verbose_name        = 'Formula Definition'
        verbose_name_plural = 'Formula Definitions'

    def __str__(self):
        return f'{self.code} — {self.name}'

    @property
    def category_display(self):
        return dict(CATEGORY_CHOICES).get(self.category, self.category)

    @property
    def maqasid_display(self):
        return dict(MAQASID_CHOICES).get(self.maqasid_principle, '')


# ── CompanyEthicsProfile ───────────────────────────────────────────────────────

class CompanyEthicsProfile(models.Model):
    """
    Stores computed master-formula outputs for a CompanyProfile.
    Created or updated whenever the scoring engine is run.

    The three master scores (NEI, TSS, RVI) are the public-facing
    ethical intelligence layer. The KPI fields power the improvement
    roadmap shown on company pages.
    """
    profile = models.OneToOneField(
        'companies.CompanyProfile',
        on_delete=models.CASCADE,
        related_name='ethics',
    )

    # ── Master scores (0-100) ──
    net_ethical_impact     = models.FloatField(default=0.0,
                             help_text='NEI: benefit minus harm balance (0-100)')
    transition_stewardship = models.FloatField(default=0.0,
                             help_text='TSS: active harm-reduction trajectory (0-100)')
    regenerative_value     = models.FloatField(default=0.0,
                             help_text='RVI: long-term societal value creation (0-100)')

    # ── NEI decomposition ──
    total_benefit_score    = models.FloatField(default=0.0,
                             help_text='Average of all benefit pillars (0-100)')
    total_harm_score       = models.FloatField(default=0.0,
                             help_text='Weighted harm composite (0-100)')

    # ── KPI improvement data ──
    key_harms              = models.JSONField(default=list, blank=True,
                             help_text='List of {label, detail, severity, maqasid}')
    key_benefits           = models.JSONField(default=list, blank=True,
                             help_text='List of {label, detail, strength, maqasid}')
    next_best_actions      = models.JSONField(default=list, blank=True,
                             help_text='Top 3 recommended action titles')
    expected_score_improvement = models.FloatField(null=True, blank=True,
                             help_text='Expected EcoIQ point gain if top 3 actions implemented')

    # ── Confidence ──
    data_confidence        = models.FloatField(default=0.5,
                             help_text='0-1: data completeness and analysis reliability')

    # ── Analyst workflow ──
    analyst_reviewed       = models.BooleanField(default=False)
    analyst_approved       = models.BooleanField(default=False)
    analyst_reviewed_at    = models.DateTimeField(null=True, blank=True)
    analyst_reviewer       = models.ForeignKey(
                             settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name='+',
                             help_text='Staff member who last reviewed this profile')
    analyst_notes_text     = models.TextField(blank=True,
                             help_text='Quick analyst notes (full notes in AnalystNote records)')

    last_computed          = models.DateTimeField(auto_now=True)
    formula_version        = models.CharField(max_length=10, default='1.0')

    class Meta:
        verbose_name        = 'Company Ethics Profile'
        verbose_name_plural = 'Company Ethics Profiles'

    def __str__(self):
        return (
            f'{self.profile.company.name} — '
            f'NEI:{self.net_ethical_impact:.1f} '
            f'TSS:{self.transition_stewardship:.1f} '
            f'RVI:{self.regenerative_value:.1f}'
        )

    # ── Derived properties ─────────────────────────────────────────────────────

    @property
    def composite_ethics_score(self):
        """Weighted composite of 3 master scores (internal summary)."""
        return round(
            self.net_ethical_impact     * 0.40 +
            self.transition_stewardship * 0.35 +
            self.regenerative_value     * 0.25,
            1,
        )

    @property
    def ethics_tier(self):
        s = self.composite_ethics_score
        if s >= 80: return 'exemplary'
        if s >= 65: return 'strong'
        if s >= 50: return 'developing'
        if s >= 35: return 'transitional'
        return 'remedial'

    @property
    def ethics_tier_display(self):
        return {
            'exemplary':    'Exemplary',
            'strong':       'Strong',
            'developing':   'Developing',
            'transitional': 'Transitional',
            'remedial':     'Remedial',
        }.get(self.ethics_tier, 'Unknown')

    @property
    def ethics_tier_color(self):
        return {
            'exemplary':    '#00e89a',
            'strong':       '#58a6ff',
            'developing':   '#8b5cf6',
            'transitional': '#f4a261',
            'remedial':     '#e63946',
        }.get(self.ethics_tier, '#888')

    @property
    def needs_review(self):
        return not self.analyst_reviewed

    def mark_reviewed(self, reviewer, approve=False):
        self.analyst_reviewed    = True
        self.analyst_approved    = approve
        self.analyst_reviewed_at = timezone.now()
        self.analyst_reviewer    = reviewer
        self.save(update_fields=[
            'analyst_reviewed', 'analyst_approved',
            'analyst_reviewed_at', 'analyst_reviewer',
        ])


# ── FormulaScore ───────────────────────────────────────────────────────────────

class FormulaScore(models.Model):
    """
    Computed score for one company on one formula definition.
    Stored for auditability, analyst review, and historical tracking.
    The `effective_score` property returns the analyst override if set.
    """
    ethics_profile   = models.ForeignKey(
                        CompanyEthicsProfile, on_delete=models.CASCADE,
                        related_name='formula_scores')
    formula          = models.ForeignKey(
                        FormulaDefinition, on_delete=models.CASCADE,
                        related_name='company_scores')

    raw_value        = models.FloatField(
                        help_text='Raw computed value before normalization')
    normalized_score = models.FloatField(
                        help_text='0-100 normalized score')
    confidence       = models.FloatField(default=0.5,
                        help_text='0-1 data confidence for this formula')

    # Evidence
    evidence_notes   = models.TextField(blank=True)
    evidence_verified= models.BooleanField(default=False,
                        help_text='Evidence has been independently verified')
    source_urls      = models.JSONField(default=list, blank=True,
                        help_text='URLs supporting this score')

    # Analyst override
    analyst_adjusted = models.BooleanField(default=False)
    analyst_override = models.FloatField(null=True, blank=True,
                        help_text='Analyst-adjusted score (0-100); overrides computed value')
    analyst_reason   = models.TextField(blank=True,
                        help_text='Rationale for analyst adjustment')

    computed_at      = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together     = [('ethics_profile', 'formula')]
        ordering            = ['formula__category', 'formula__order']
        verbose_name        = 'Formula Score'
        verbose_name_plural = 'Formula Scores'

    def __str__(self):
        return f'{self.formula.code}: {self.normalized_score:.1f}'

    @property
    def effective_score(self):
        """Returns analyst override if set, otherwise computed score."""
        if self.analyst_adjusted and self.analyst_override is not None:
            return self.analyst_override
        return self.normalized_score

    @property
    def confidence_pct(self):
        return round(self.confidence * 100)


# ── ImprovementMilestone ───────────────────────────────────────────────────────

class ImprovementMilestone(models.Model):
    """
    Recommended KPI improvement milestone for a company's improvement roadmap.
    Generated by the scoring engine and shown on public company pages.
    Analyst can update status and current/target values as company progresses.
    """
    ethics_profile     = models.ForeignKey(
                          CompanyEthicsProfile, on_delete=models.CASCADE,
                          related_name='milestones')

    title              = models.CharField(max_length=255)
    description        = models.TextField(blank=True)
    formula_category   = models.CharField(max_length=30, choices=CATEGORY_CHOICES, blank=True)
    pillar             = models.CharField(max_length=50, blank=True,
                          help_text='EcoIQ pillar this improvement targets')

    expected_score_gain= models.FloatField(default=0.0,
                          help_text='Expected EcoIQ total score improvement (points)')
    effort_level       = models.CharField(max_length=10, choices=EFFORT_CHOICES, default='medium')
    timeline_months    = models.PositiveSmallIntegerField(default=6)
    priority           = models.PositiveSmallIntegerField(default=5,
                          help_text='1=highest, 10=lowest priority')

    status             = models.CharField(max_length=15, choices=MILESTONE_STATUS_CHOICES,
                          default='recommended')
    completed_at       = models.DateTimeField(null=True, blank=True)

    # KPI tracking
    kpi_metric         = models.CharField(max_length=255, blank=True,
                          help_text='Measurable KPI to track progress')
    target_value       = models.CharField(max_length=100, blank=True)
    current_value      = models.CharField(max_length=100, blank=True)

    # Internal Maqasid link (shown in advanced methodology view only)
    maqasid_principle  = models.CharField(max_length=15, choices=MAQASID_CHOICES, blank=True)

    order              = models.PositiveSmallIntegerField(default=0)
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['priority', 'order']
        verbose_name        = 'Improvement Milestone'
        verbose_name_plural = 'Improvement Milestones'

    def __str__(self):
        return f'{self.ethics_profile.profile.company.name} — {self.title}'

    @property
    def effort_color(self):
        return {'low': '#00e89a', 'medium': '#f4a261', 'high': '#e63946'}.get(
            self.effort_level, '#888'
        )

    @property
    def status_color(self):
        return {
            'recommended': '#58a6ff',
            'in_progress': '#f4a261',
            'completed':   '#00e89a',
            'deferred':    '#666',
        }.get(self.status, '#888')

    @property
    def gain_display(self):
        g = self.expected_score_gain
        return f'+{g:.1f}' if g > 0 else str(round(g, 1))


# ── AnalystNote ────────────────────────────────────────────────────────────────

class AnalystNote(models.Model):
    """
    Structured analyst annotation for a CompanyEthicsProfile.
    Supports the analyst review, approval, and correction workflow.
    `is_public` notes can appear on the public company page under
    "Analyst Commentary" if enabled.
    """
    ethics_profile   = models.ForeignKey(
                        CompanyEthicsProfile, on_delete=models.CASCADE,
                        related_name='analyst_notes_set')
    formula_score    = models.ForeignKey(
                        FormulaScore, null=True, blank=True,
                        on_delete=models.SET_NULL, related_name='analyst_notes',
                        help_text='Optional: link note to a specific formula score')
    author           = models.ForeignKey(
                        settings.AUTH_USER_MODEL, null=True, blank=True,
                        on_delete=models.SET_NULL, related_name='+')

    note_type        = models.CharField(max_length=15, choices=NOTE_TYPE_CHOICES,
                        default='observation')
    note             = models.TextField()
    is_public        = models.BooleanField(default=False,
                        help_text='Show this note on the public company page')

    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Analyst Note'
        verbose_name_plural = 'Analyst Notes'

    def __str__(self):
        author_name = self.author.get_full_name() if self.author else 'System'
        return f'[{self.note_type}] {author_name} — {self.created_at:%Y-%m-%d}'

    @property
    def note_type_color(self):
        return {
            'observation':  '#58a6ff',
            'flag':         '#f4a261',
            'verification': '#8b5cf6',
            'approval':     '#00e89a',
            'correction':   '#e63946',
        }.get(self.note_type, '#888')
