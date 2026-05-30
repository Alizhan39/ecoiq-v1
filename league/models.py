"""
EcoIQ Good Deeds League — data models.

Three core concerns:
  Company        — the rated entity, holds pillar scores + computed EcoIQ score
  EnvironmentalProject — discrete actions the company took
  Evidence       — documents proving the project happened
  ScoreHistory   — monthly snapshot so we can show trends
"""
from decimal import Decimal
from django.db import models
from django.utils.text import slugify


# ── Constants ──────────────────────────────────────────────────────────────────

SECTOR_CHOICES = [
    ('oil_gas',      'Oil & Gas'),
    ('mining',       'Mining'),
    ('energy',       'Energy / Power'),
    ('chemical',     'Chemical'),
    ('metallurgy',   'Metallurgy'),
    ('transport',    'Transport'),
    ('agriculture',  'Agriculture'),
    ('other',        'Other'),
]

PROJECT_TYPE_CHOICES = [
    ('coal_stove',     'Coal Stove Replacement'),
    ('gasification',   'Gasification'),
    ('power_modern',   'Power Plant Modernisation'),
    ('renewable',      'Renewable Energy'),
    ('water_cleanup',  'Water Clean-up'),
    ('waste',          'Waste Reduction'),
    ('tree_planting',  'Tree Planting'),
    ('filters',        'Industrial Filters'),
    ('methane',        'Methane Leak Reduction'),
    ('other',          'Other'),
]

PROJECT_STATUS_CHOICES = [
    ('planned',     'Planned'),
    ('active',      'Active'),
    ('completed',   'Completed'),
    ('cancelled',   'Cancelled'),
]

EVIDENCE_TYPE_CHOICES = [
    ('audit_report',      'Audit Report'),
    ('government_report', 'Government Report'),
    ('photo',             'Photo / Video'),
    ('satellite',         'Satellite Evidence'),
    ('invoice',           'Invoice / Contract'),
    ('permit',            'Environmental Permit'),
    ('engineering_audit', 'Engineering Audit'),
    ('press_release',     'Press Release'),
    ('other',             'Other'),
]

VERIFICATION_CHOICES = [
    ('pending',   'Pending'),
    ('verified',  'Verified'),
    ('rejected',  'Rejected'),
]


# ── Company ────────────────────────────────────────────────────────────────────

class Company(models.Model):
    """
    An industrial company in the Good Deeds League.
    Pillar scores (0–100) are set manually or imported from audits.
    ecoiq_score is computed automatically on save.
    """

    name        = models.CharField(max_length=255)
    slug        = models.SlugField(max_length=255, unique=True, blank=True)
    sector      = models.CharField(max_length=30, choices=SECTOR_CHOICES, default='other')
    country     = models.CharField(max_length=100, default='Kazakhstan')
    city        = models.CharField(max_length=100, blank=True)
    founded_year = models.PositiveIntegerField(null=True, blank=True)
    description  = models.TextField(blank=True)
    website      = models.URLField(blank=True)
    logo_url     = models.URLField(blank=True, help_text='Public URL to company logo (SVG/PNG)')

    employee_count = models.PositiveIntegerField(null=True, blank=True,
                                                 help_text='Approximate headcount')
    annual_revenue_usd = models.BigIntegerField(null=True, blank=True,
                                                help_text='Annual revenue in USD')

    is_public  = models.BooleanField(default=False, help_text='Publicly listed company')
    verified   = models.BooleanField(default=False, help_text='Data independently verified')
    is_featured = models.BooleanField(default=False, help_text='Show on landing page')

    # ── Pillar scores 0-100 ──
    score_pollution_footprint = models.IntegerField(
        default=0,
        help_text='Lower emissions/waste = higher score (0-100)'
    )
    score_reduction_progress  = models.IntegerField(
        default=0,
        help_text='Year-on-year pollution reduction trend (0-100)'
    )
    score_investment          = models.IntegerField(
        default=0,
        help_text='Environmental investment relative to revenue (0-100)'
    )
    score_transparency        = models.IntegerField(
        default=0,
        help_text='Reporting quality, public disclosures (0-100)'
    )
    score_community_impact    = models.IntegerField(
        default=0,
        help_text='Measurable benefit to people & ecosystem (0-100)'
    )

    # Computed — updated by save() / recompute_scores management command
    ecoiq_score = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0.0'))
    rank        = models.PositiveIntegerField(null=True, blank=True)

    # ── ML fields ────────────────────────────────────────────────────────────
    ml_score                = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True,
        help_text='GBR model-predicted EcoIQ score')
    ml_score_confidence     = models.FloatField(
        null=True, blank=True,
        help_text='Model confidence (0–1); higher = more training data neighbours')
    ml_predicted_score_12m  = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True,
        help_text='12-month forward-projected score')
    ml_cluster              = models.IntegerField(
        null=True, blank=True,
        help_text='K-Means cluster index')
    ml_cluster_label        = models.CharField(
        max_length=80, blank=True,
        help_text='Human-readable cluster name')
    anomaly_score           = models.FloatField(
        null=True, blank=True,
        help_text='Isolation Forest anomaly score; negative = more anomalous')
    is_anomaly              = models.BooleanField(
        default=False,
        help_text='True if Isolation Forest flags this company as anomalous')
    ml_last_run             = models.DateTimeField(
        null=True, blank=True,
        help_text='When the ML pipeline last ran for this company')

    # ── Semantic search ───────────────────────────────────────────────────────
    search_text = models.TextField(
        blank=True,
        help_text='Pre-built rich text for keyword / semantic search (built by build_embeddings)'
    )
    # embedding field added dynamically when pgvector is installed (migration 0005)

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering  = ['-ecoiq_score', 'name']
        verbose_name        = 'Company'
        verbose_name_plural = 'Companies'

    def __str__(self):
        return self.name

    # ── Scoring ────────────────────────────────────────────────────────────────

    def compute_score(self) -> Decimal:
        """
        EcoIQ Score = Pollution × 35% + Reduction × 25% + Investment × 20%
                      + Transparency × 10% + Community × 10%
        """
        raw = (
            self.score_pollution_footprint * 0.35 +
            self.score_reduction_progress  * 0.25 +
            self.score_investment          * 0.20 +
            self.score_transparency        * 0.10 +
            self.score_community_impact    * 0.10
        )
        return Decimal(str(round(raw, 1)))

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        self.ecoiq_score = self.compute_score()
        super().save(*args, **kwargs)

    # ── Derived properties ─────────────────────────────────────────────────────

    @property
    def status_label(self) -> str:
        s = float(self.ecoiq_score)
        if s >= 85: return 'Restorative Leader'
        if s >= 70: return 'Transition Leader'
        if s >= 55: return 'Improving but Polluting'
        if s >= 40: return 'High Impact / Weak Repair'
        return 'Major Polluter'

    @property
    def status_css(self) -> str:
        """CSS class suffix for colour-coding (used in templates)."""
        s = float(self.ecoiq_score)
        if s >= 85: return 'restorative'
        if s >= 70: return 'transition'
        if s >= 55: return 'improving'
        if s >= 40: return 'high-impact'
        return 'polluter'

    @property
    def total_co2_reduced(self) -> int:
        return sum(
            p.co2_reduction_tonnes or 0
            for p in self.projects.filter(status='completed')
        )

    @property
    def total_investment_usd(self) -> int:
        return sum(
            p.investment_usd or 0
            for p in self.projects.all()
        )

    @property
    def total_households_helped(self) -> int:
        return sum(
            p.households_helped or 0
            for p in self.projects.filter(status='completed')
        )


# ── Environmental Project ──────────────────────────────────────────────────────

class EnvironmentalProject(models.Model):
    company  = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='projects')
    name     = models.CharField(max_length=255)
    project_type = models.CharField(max_length=30, choices=PROJECT_TYPE_CHOICES, default='other')
    status   = models.CharField(max_length=20, choices=PROJECT_STATUS_CHOICES, default='planned')

    start_date      = models.DateField(null=True, blank=True)
    completion_date = models.DateField(null=True, blank=True)

    investment_usd       = models.BigIntegerField(null=True, blank=True,
                                                   help_text='Total investment in USD')
    co2_reduction_tonnes = models.IntegerField(null=True, blank=True,
                                               help_text='Annual CO₂ reduction in tonnes')
    pm25_reduction_kg    = models.IntegerField(null=True, blank=True,
                                               help_text='Annual PM2.5 reduction in kg')
    households_helped    = models.IntegerField(null=True, blank=True,
                                               help_text='Households directly benefiting')

    description = models.TextField(blank=True)
    location    = models.CharField(max_length=255, blank=True)
    verified    = models.BooleanField(default=False)

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date', 'name']
        verbose_name        = 'Project'
        verbose_name_plural = 'Projects'

    def __str__(self):
        return f'{self.company.name} — {self.name}'


# ── Evidence ──────────────────────────────────────────────────────────────────

class Evidence(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='evidence')
    project = models.ForeignKey(
        EnvironmentalProject, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='evidence'
    )

    doc_type    = models.CharField(max_length=30, choices=EVIDENCE_TYPE_CHOICES)
    title       = models.CharField(max_length=255)
    file        = models.FileField(upload_to='league/evidence/', null=True, blank=True)
    url         = models.URLField(blank=True)
    date_issued = models.DateField(null=True, blank=True)
    issuer      = models.CharField(max_length=255, blank=True)

    verification_status = models.CharField(
        max_length=20, choices=VERIFICATION_CHOICES, default='pending'
    )
    notes = models.TextField(blank=True)

    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date_issued', 'title']
        verbose_name        = 'Document'
        verbose_name_plural = 'Documents'

    def __str__(self):
        return f'{self.company.name} — {self.title}'


# ── Score History ─────────────────────────────────────────────────────────────

class ScoreHistory(models.Model):
    """Monthly snapshot of a company's scores — used for trend charts."""
    company     = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='history')
    date        = models.DateField()

    ecoiq_score               = models.DecimalField(max_digits=5, decimal_places=1)
    score_pollution_footprint = models.IntegerField()
    score_reduction_progress  = models.IntegerField()
    score_investment          = models.IntegerField()
    score_transparency        = models.IntegerField()
    score_community_impact    = models.IntegerField()
    rank                      = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('company', 'date')
        ordering = ['date']
        verbose_name        = 'Score History'
        verbose_name_plural = 'Score Histories'

    def __str__(self):
        return f'{self.company.name} — {self.date} ({self.ecoiq_score})'


# ── Reference tables for ingestion ────────────────────────────────────────────

class SectorRef(models.Model):
    """Canonical sector list used by the AI ingestion pipeline."""
    code         = models.SlugField(max_length=30, unique=True)
    display_name = models.CharField(max_length=100)
    description  = models.TextField(blank=True, help_text='AI prompt hint for sector classification')

    class Meta:
        ordering        = ['display_name']
        verbose_name        = 'Sector'
        verbose_name_plural = 'Sectors'

    def __str__(self):
        return self.display_name


class CountryRef(models.Model):
    """Canonical country list used by the AI ingestion pipeline."""
    code   = models.CharField(max_length=3, unique=True, help_text='ISO-3166-1 alpha-2 or alpha-3')
    name   = models.CharField(max_length=100)
    region = models.CharField(max_length=100, blank=True, help_text='e.g. Central Asia, Europe')

    class Meta:
        ordering        = ['name']
        verbose_name        = 'Country'
        verbose_name_plural = 'Countries'

    def __str__(self):
        return self.name
