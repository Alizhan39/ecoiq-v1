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
