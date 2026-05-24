from django.conf import settings
from django.db import models


SECTOR_CHOICES = [
    ('manufacturing', 'Manufacturing (General)'),
    ('automotive',    'Automotive'),
    ('food',          'Food & Beverage'),
    ('chemicals',     'Chemicals & Petrochemicals'),
    ('metals',        'Metals & Mining'),
    ('oil_gas',       'Oil & Gas / Refining'),
    ('utilities',     'Utilities / Energy'),
    ('pharma',        'Pharmaceuticals'),
    ('logistics',     'Logistics & Warehousing'),
    ('other',         'Other Heavy Industry'),
]

AUTOMATION_CHOICES = [
    ('manual',     'Mostly Manual'),
    ('semi',       'Semi-Automated'),
    ('automated',  'Highly Automated'),
]

MAINTENANCE_CHOICES = [
    ('reactive',    'Reactive (fix when broken)'),
    ('preventive',  'Preventive (scheduled)'),
    ('predictive',  'Predictive (condition-based)'),
]

STATUS_CHOICES = [
    ('draft',       'Draft'),
    ('ready',       'Ready'),
    ('processing',  'Processing'),
    ('complete',    'Complete'),
    ('error',       'Error'),
]

PRIORITY_CHOICES = [
    ('critical', 'Critical'),
    ('high',     'High'),
    ('medium',   'Medium'),
    ('low',      'Low'),
]

CATEGORY_CHOICES = [
    ('energy',          'Energy'),
    ('production',      'Production'),
    ('maintenance',     'Maintenance'),
    ('safety',          'Safety'),
    ('infrastructure',  'Infrastructure'),
    ('quality',         'Quality'),
    ('workforce',       'Workforce'),
]

COMPLEXITY_CHOICES = [
    ('low',    'Low'),
    ('medium', 'Medium'),
    ('high',   'High'),
]


class AuditSession(models.Model):
    """Top-level audit record — one per facility engagement."""
    facility_name   = models.CharField(max_length=255)
    sector          = models.CharField(max_length=50, choices=SECTOR_CHOICES, default='manufacturing')
    location        = models.CharField(max_length=255, blank=True)
    facility_age    = models.PositiveIntegerField(null=True, blank=True, help_text='Years since facility was built')
    headcount       = models.PositiveIntegerField(null=True, blank=True)
    annual_revenue  = models.BigIntegerField(null=True, blank=True, help_text='USD, optional — used to scale ROI estimates')

    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    uploaded_file   = models.FileField(upload_to='audit_uploads/', blank=True, null=True)
    extracted_text  = models.TextField(blank=True)
    notes           = models.TextField(blank=True)

    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.facility_name} [{self.get_sector_display()}] ({self.get_status_display()})"


class AuditResponse(models.Model):
    """One questionnaire answer per session."""
    session       = models.ForeignKey(AuditSession, on_delete=models.CASCADE, related_name='responses')
    question_key  = models.CharField(max_length=100)
    question_text = models.TextField()
    answer        = models.TextField(blank=True)

    class Meta:
        unique_together = ('session', 'question_key')
        ordering        = ['question_key']

    def __str__(self):
        return f"{self.session.facility_name} — {self.question_key}"


class Finding(models.Model):
    """An AI-identified inefficiency or operational issue."""
    session               = models.ForeignKey(AuditSession, on_delete=models.CASCADE, related_name='findings')
    area                  = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    severity              = models.CharField(max_length=20, choices=PRIORITY_CHOICES)
    title                 = models.CharField(max_length=255)
    description           = models.TextField()
    root_cause            = models.TextField(blank=True)
    recommended_action    = models.TextField(blank=True)
    loss_usd              = models.BigIntegerField(default=0, help_text='Estimated annual loss in USD')
    efficiency_gain_pct   = models.IntegerField(default=0, help_text='Estimated efficiency improvement if addressed (%)')
    sustainability_impact = models.TextField(blank=True)

    class Meta:
        ordering = ['-loss_usd']

    def __str__(self):
        return f"[{self.severity.upper()}] {self.title}"


class Recommendation(models.Model):
    """A concrete modernisation recommendation with ROI data."""
    session          = models.ForeignKey(AuditSession, on_delete=models.CASCADE, related_name='recommendations')
    priority         = models.CharField(max_length=20, choices=PRIORITY_CHOICES)
    category         = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    title            = models.CharField(max_length=255)
    problem          = models.TextField()
    solution         = models.TextField()
    implementation   = models.TextField(blank=True, help_text='Step-by-step implementation guidance')
    savings_usd      = models.BigIntegerField(default=0, help_text='Estimated annual savings in USD')
    cost_usd         = models.BigIntegerField(default=0, help_text='Estimated one-time implementation cost in USD')
    roi_months       = models.PositiveIntegerField(default=0, help_text='Payback period in months')
    complexity       = models.CharField(max_length=10, choices=COMPLEXITY_CHOICES, default='medium')
    is_quick_win     = models.BooleanField(default=False)
    order            = models.PositiveIntegerField(default=0, help_text='Display order')

    class Meta:
        ordering = ['order', '-savings_usd']

    def __str__(self):
        return f"[{self.priority.upper()}] {self.title} (${self.savings_usd:,}/yr)"


class ActionPlan(models.Model):
    """One phase of the 3-phase implementation roadmap."""
    session     = models.ForeignKey(AuditSession, on_delete=models.CASCADE, related_name='action_phases')
    phase       = models.PositiveSmallIntegerField()  # 1, 2, 3
    label       = models.CharField(max_length=100)    # e.g. "0–3 months: Quick Wins"
    items       = models.JSONField(default=list)       # list of action strings
    investment  = models.BigIntegerField(default=0)   # USD
    savings     = models.BigIntegerField(default=0)   # annual USD

    class Meta:
        ordering = ['phase']

    def __str__(self):
        return f"Phase {self.phase}: {self.label}"


class AuditReport(models.Model):
    """Aggregated AI output — the top-level report container."""
    session                 = models.OneToOneField(AuditSession, on_delete=models.CASCADE, related_name='report')
    created_at              = models.DateTimeField(auto_now_add=True)

    overall_efficiency_score    = models.IntegerField(default=0)   # 0–100 current state
    modernization_score         = models.IntegerField(default=0)   # 0–100 projected after recs
    total_savings_potential     = models.BigIntegerField(default=0) # USD/yr
    total_investment_required   = models.BigIntegerField(default=0) # USD
    blended_roi_months          = models.IntegerField(default=0)

    executive_summary       = models.TextField(blank=True)
    current_state_summary   = models.TextField(blank=True)
    future_state_summary    = models.TextField(blank=True)

    # Before/after by area — {area: {current: "...", future: "...", improvement_pct: 20}}
    before_after              = models.JSONField(default=dict)

    # Projected facility-wide improvements after all recommendations
    energy_reduction_pct      = models.IntegerField(default=0)
    downtime_reduction_pct    = models.IntegerField(default=0)
    production_efficiency_pct = models.IntegerField(default=0)
    emissions_reduction_pct   = models.IntegerField(default=0)

    raw_ai_response           = models.TextField(blank=True)

    def __str__(self):
        return f"Report — {self.session.facility_name} (score: {self.overall_efficiency_score}→{self.modernization_score})"


# ═══════════════════════════════════════════════════════════════════════════════
# AI FINDINGS ENGINE  —  ESG document analysis models
# ═══════════════════════════════════════════════════════════════════════════════

AI_JOB_STATUS = [
    ('pending',    'Pending'),
    ('processing', 'Processing'),
    ('completed',  'Completed'),
    ('failed',     'Failed'),
]

AI_FINDING_TYPE = [
    # Pollution metrics
    ('co2_metric',    'CO₂ Metric'),
    ('methane_metric','Methane Metric'),
    ('pm25_metric',   'PM2.5 Metric'),
    ('so2_metric',    'SO₂ Metric'),
    ('nox_metric',    'NOₓ Metric'),
    ('water_metric',  'Water Metric'),
    ('waste_metric',  'Waste Metric'),
    ('pollution_other','Pollution — Other'),
    # Projects & investments
    ('investment',      'Environmental Investment'),
    ('project',         'Environmental Project'),
    ('coal_replacement','Coal Replacement Initiative'),
    # Quality signals
    ('greenwashing',  'Greenwashing Signal'),
    ('transparency',  'Transparency Indicator'),
    ('recommendation','AI Recommendation'),
    ('other',         'Other Finding'),
]

AI_FINDING_STATUS = [
    ('pending',  'Pending Review'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('applied',  'Applied to Company'),
]

GREENWASHING_LEVEL = [
    ('low',      'Low Risk'),
    ('medium',   'Medium Risk'),
    ('high',     'High Risk'),
    ('critical', 'Critical Risk'),
]


class AIAnalysisJob(models.Model):
    """
    Queue item for an ESG/sustainability PDF to be AI-analyzed.
    One job per document upload.
    """

    # ── Input ─────────────────────────────────────────────────────────────────
    pdf_file          = models.FileField(upload_to='ai_analysis/%Y/%m/')
    original_filename = models.CharField(max_length=255)

    # Optionally linked to an existing league company
    company = models.ForeignKey(
        'league.Company', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='ai_jobs',
        help_text='Link to an existing company record (optional — can be set post-analysis)',
    )

    # ── Status ────────────────────────────────────────────────────────────────
    status       = models.CharField(max_length=20, choices=AI_JOB_STATUS, default='pending')
    created_at   = models.DateTimeField(auto_now_add=True)
    started_at   = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message= models.TextField(blank=True)

    # ── API telemetry ─────────────────────────────────────────────────────────
    model_used     = models.CharField(max_length=100, blank=True)
    pages_analyzed = models.IntegerField(default=0)
    chars_analyzed = models.IntegerField(default=0)
    input_tokens   = models.IntegerField(default=0)
    output_tokens  = models.IntegerField(default=0)

    # ── Extracted metadata (set after analysis) ───────────────────────────────
    detected_company_name = models.CharField(max_length=255, blank=True)
    detected_doc_type     = models.CharField(max_length=50, blank=True)
    detected_year         = models.IntegerField(null=True, blank=True)
    executive_summary     = models.TextField(blank=True)
    data_quality_notes    = models.TextField(blank=True)

    # ── Raw API response (for debugging / re-parse) ───────────────────────────
    raw_response = models.JSONField(null=True, blank=True)

    # ── Workflow ──────────────────────────────────────────────────────────────
    submitted_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='ai_jobs',
    )
    analyst_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name        = 'AI Analysis Job'
        verbose_name_plural = 'AI Analysis Jobs'

    def __str__(self):
        return f"[{self.get_status_display()}] {self.original_filename} ({self.created_at:%Y-%m-%d})"

    @property
    def finding_count(self):
        return self.findings.count()

    @property
    def pending_count(self):
        return self.findings.filter(status='pending').count()

    @property
    def approved_count(self):
        return self.findings.filter(status='approved').count()


class AIFinding(models.Model):
    """
    Individual finding extracted from a document by the AI engine.
    Analysts review, annotate, approve or reject each finding.
    """

    job          = models.ForeignKey(AIAnalysisJob, on_delete=models.CASCADE,
                                     related_name='findings')
    finding_type = models.CharField(max_length=30, choices=AI_FINDING_TYPE)

    # ── Core content ──────────────────────────────────────────────────────────
    title       = models.CharField(max_length=255)
    description = models.TextField()

    # Quantitative value (when applicable)
    numeric_value = models.FloatField(null=True, blank=True)
    unit          = models.CharField(max_length=50, blank=True)
    year          = models.IntegerField(null=True, blank=True)

    # ── Source attribution (extraction highlighting) ───────────────────────────
    source_quote    = models.TextField(
        blank=True,
        help_text='Exact verbatim text from the document where this was found',
    )
    source_location = models.CharField(
        max_length=200, blank=True,
        help_text='Page number or section reference',
    )

    # ── AI confidence ─────────────────────────────────────────────────────────
    confidence_score = models.FloatField(
        default=0.5,
        help_text='AI confidence 0.0 (low) → 1.0 (high)',
    )

    # ── Review workflow ───────────────────────────────────────────────────────
    status        = models.CharField(max_length=20, choices=AI_FINDING_STATUS, default='pending')
    analyst_notes = models.TextField(blank=True)
    reviewed_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='reviewed_ai_findings',
    )
    reviewed_at   = models.DateTimeField(null=True, blank=True)

    # Extra structured data (project details, sdg numbers, etc.)
    extra_data = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-confidence_score', 'finding_type', 'title']
        verbose_name        = 'AI Finding'
        verbose_name_plural = 'AI Findings'

    def __str__(self):
        return f"[{self.get_finding_type_display()}] {self.title}"

    @property
    def confidence_pct(self):
        return round(self.confidence_score * 100)

    @property
    def confidence_label(self):
        s = self.confidence_score
        if s >= 0.85: return 'High'
        if s >= 0.60: return 'Medium'
        return 'Low'

    @property
    def confidence_color(self):
        s = self.confidence_score
        if s >= 0.85: return '#2d6a4f'
        if s >= 0.60: return '#f4a261'
        return '#e63946'


class AIScoreEstimate(models.Model):
    """
    AI-generated EcoIQ score estimate for the analyzed document.
    Analysts can approve and optionally apply it to the linked company.
    """

    job = models.OneToOneField(
        AIAnalysisJob, on_delete=models.CASCADE,
        related_name='score_estimate',
    )

    # ── Estimated pillar scores (0–100) ───────────────────────────────────────
    est_pollution    = models.IntegerField(null=True, blank=True)
    est_reduction    = models.IntegerField(null=True, blank=True)
    est_investment   = models.IntegerField(null=True, blank=True)
    est_transparency = models.IntegerField(null=True, blank=True)
    est_community    = models.IntegerField(null=True, blank=True)
    est_ecoiq        = models.FloatField(null=True, blank=True)

    confidence = models.FloatField(default=0.0, help_text='Overall scoring confidence 0.0–1.0')
    reasoning  = models.TextField(blank=True, help_text='AI explanation for each pillar score')
    data_gaps  = models.JSONField(default=list, help_text='List of missing data points')

    # ── Greenwashing risk ─────────────────────────────────────────────────────
    greenwashing_level   = models.CharField(max_length=20, choices=GREENWASHING_LEVEL, blank=True)
    greenwashing_score   = models.IntegerField(null=True, blank=True,
                                                help_text='0=clean, 100=critical greenwashing')
    greenwashing_signals = models.JSONField(default=list)
    greenwashing_verdict = models.TextField(blank=True)

    # ── Analyst review ────────────────────────────────────────────────────────
    approved      = models.BooleanField(default=False)
    approved_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='approved_score_estimates',
    )
    applied_at    = models.DateTimeField(null=True, blank=True)
    analyst_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'AI Score Estimate'
        verbose_name_plural = 'AI Score Estimates'

    def __str__(self):
        return f"Score estimate for {self.job.original_filename} — EcoIQ≈{self.est_ecoiq}"

    @property
    def computed_ecoiq(self):
        """Recompute from pillar estimates using league formula."""
        vals = [self.est_pollution, self.est_reduction, self.est_investment,
                self.est_transparency, self.est_community]
        if any(v is None for v in vals):
            return self.est_ecoiq
        return round(
            vals[0] * 0.35 + vals[1] * 0.25 + vals[2] * 0.20
            + vals[3] * 0.10 + vals[4] * 0.10, 1
        )
