"""
company_intelligence/models.py — feat/company-halal-intelligence (PR 9):
the FOUNDATION of EcoIQ's evidence-driven company research layer.

Two lenses over the same company, kept strictly separate and never
combined into one score:

1. Shariah eligibility screening (ShariahMethodology, CompanyListing,
   CompanyFinancialFacts, CompanyShariahScreen) — a methodology-versioned,
   deterministic business-activity + financial-ratio screen. A named
   methodology, never an invented "EcoIQ Islamic ruling." Distinct from
   qdf.DecisionAssessment's existing "halal" question, which is a coarse
   ethics-proxy derived from controversy/ethics signals, not a rigorous
   sector-and-ratio eligibility screen — see that app's own docstring.
   Neither model is touched or renamed by this PR.

2. EcoIQ 114-KPI stewardship alignment (CompanyKPIAssessment,
   CompanyKPIEvidenceLink) — mapped against the existing, canonical
   core.esg_principles_data.PRINCIPLES list (public name: "Capital Ethics
   Compendium"), reused verbatim, never a second 114-item taxonomy. Per
   docs/governance-principles-surah-map.md's internal-only firewall, no
   surface built by this app may reference the Quran/Surah origin mapping
   of that list — public language stays "114-KPI stewardship framework" /
   "Capital Ethics Compendium."

Every model here extends companies.CompanyProfile (the repo's real
company-intelligence extension point — see financing.CompanyFinancingProfile
and qdf.DecisionAssessment for the same pattern) rather than introducing a
new base Company model, and reuses evidence_memory.EvidenceMemory (which
already carries a `company` FK) as the one evidence store — no new evidence
model. This PR is explicitly research/stewardship intelligence, never
investment advice: no field anywhere on these models may express a
buy/sell/hold recommendation, a price target, or a return forecast.
"""
from django.conf import settings
from django.db import models


# ---------------------------------------------------------------------------
# Shared honest result vocabulary — uncertainty is never collapsed to a
# binary PASS/FAIL. INSUFFICIENT_DATA and NOT_SCREENED are first-class
# results, not error states.
# ---------------------------------------------------------------------------
SCREEN_RESULT_CHOICES = [
    ('pass', 'Pass'),
    ('fail', 'Fail'),
    ('conditional', 'Conditional'),
    ('insufficient_data', 'Insufficient Data'),
    ('not_screened', 'Not Screened'),
]

KPI_STATUS_CHOICES = [
    ('strong_support', 'Strong Support'),
    ('support', 'Support'),
    ('mixed', 'Mixed'),
    ('neutral_or_no_material_link', 'Neutral / No Material Link'),
    ('conflict', 'Conflict'),
    ('insufficient_evidence', 'Insufficient Evidence'),
    ('not_assessed', 'Not Assessed'),
]

REVIEW_STATUS_CHOICES = [
    ('automated_preliminary', 'Automated Preliminary Screen'),
    ('human_reviewed', 'Human Reviewed'),
    ('methodology_verified', 'Methodology Verified'),
    ('scholar_reviewed', 'Scholar Reviewed'),
]


class ShariahMethodology(models.Model):
    """
    A named, versioned Shariah screening methodology — never an invented
    'EcoIQ Islamic ruling'. Every CompanyShariahScreen must cite exactly
    one of these, and every public result is labelled "Screened according
    to [name] v[version]", never "Islamically approved". Business-activity
    exclusions and financial-ratio thresholds are stored here, not
    hardcoded in the scoring service, so a methodology change is a new
    versioned row, never a silent code edit to past results.
    """
    name = models.CharField(max_length=200, help_text='e.g. "EcoIQ Reference Shariah Screen"')
    version = models.CharField(max_length=20, help_text='e.g. "1.0"')
    description = models.TextField(
        help_text='What this methodology screens for and how it was derived. Must state it is '
                   'methodology-based screening, not a religious ruling or individual fatwa.',
    )
    source_reference = models.CharField(
        max_length=300, blank=True,
        help_text='Named reference the thresholds/categories are derived from (e.g. an published '
                   'index methodology). Left blank only if genuinely unavailable — never fabricated.',
    )

    # Business-activity screen: list of {'category': str, 'label': str,
    # 'status': 'blocked'|'restricted', 'tolerance_pct': float|None,
    # 'notes': str}. 'restricted' categories fail only above tolerance_pct
    # of revenue (when that figure is known); 'blocked' categories always
    # fail regardless of magnitude. Never a free-text keyword denylist —
    # matched against the company's own structured sector/description.
    business_activity_rules = models.JSONField(default=list, blank=True)

    # Financial-ratio screen: {'debt_to_market_cap_max': float,
    # 'interest_bearing_securities_to_market_cap_max': float,
    # 'non_permissible_income_to_revenue_max': float}. Every threshold is
    # explicit and versioned here — the scoring service never hardcodes one.
    financial_ratio_rules = models.JSONField(default=dict, blank=True)

    effective_date = models.DateField()
    is_active = models.BooleanField(default=True, help_text='Available for new screens.')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-effective_date']
        verbose_name = 'Shariah Methodology'
        verbose_name_plural = 'Shariah Methodologies'
        constraints = [
            models.UniqueConstraint(fields=['name', 'version'], name='ci_unique_methodology_version'),
        ]

    def __str__(self):
        return f'{self.name} v{self.version}'


class CompanyListing(models.Model):
    """
    Company identity/listing facts — ticker, exchange, ISIN — none of
    which exist on league.Company today. A FK (not OneToOne) because a
    real company can have more than one listing (e.g. primary exchange +
    an ADR); `is_primary` marks the one the company page shows by default.
    Never invents an identifier: any field left blank means it genuinely
    isn't known, not that it was assumed empty.
    """
    company = models.ForeignKey('league.Company', on_delete=models.CASCADE, related_name='listings')
    ticker = models.CharField(max_length=20, blank=True)
    exchange = models.CharField(max_length=100, blank=True, help_text='e.g. "NASDAQ", "LSE"')
    isin = models.CharField(max_length=12, blank=True, help_text='ISO 6166 identifier where known.')
    currency = models.CharField(max_length=8, blank=True, help_text='e.g. "USD"')
    is_primary = models.BooleanField(default=True)
    source = models.CharField(max_length=200, blank=True)
    retrieved_at = models.DateTimeField(null=True, blank=True)
    is_demo = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_primary', 'exchange']
        verbose_name = 'Company Listing'

    def __str__(self):
        return f'{self.company.name} — {self.ticker or "no ticker"} ({self.exchange or "exchange unknown"})'


class CompanyFinancialFacts(models.Model):
    """
    Raw financial inputs for the Shariah financial-ratio screen — every
    field nullable, and null is NEVER treated as zero by the scoring
    service (see services/shariah_screening.py). A missing debt figure
    means "not screened for this ratio", not "zero debt".
    """
    company = models.ForeignKey(
        'companies.CompanyProfile', on_delete=models.CASCADE, related_name='financial_facts',
    )
    as_of_date = models.DateField()
    market_cap_usd = models.FloatField(null=True, blank=True)
    total_debt_usd = models.FloatField(null=True, blank=True, help_text='Interest-bearing debt.')
    cash_and_equivalents_usd = models.FloatField(null=True, blank=True)
    interest_bearing_securities_usd = models.FloatField(
        null=True, blank=True, help_text='Interest-bearing cash equivalents/securities held.',
    )
    non_permissible_income_usd = models.FloatField(
        null=True, blank=True, help_text='Interest income + other non-permissible income, where disclosed.',
    )
    revenue_usd = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=200, blank=True, help_text='Where these figures came from.')
    retrieved_at = models.DateTimeField(null=True, blank=True)
    is_demo = models.BooleanField(default=False)

    class Meta:
        ordering = ['-as_of_date']
        verbose_name = 'Company Financial Facts'
        verbose_name_plural = 'Company Financial Facts'

    def __str__(self):
        return f'{self.company.company.name} financial facts as of {self.as_of_date}'


class CompanyShariahScreen(models.Model):
    """
    One Shariah screening result for one company under one named
    methodology. Distinguishes business-activity result from
    financial-ratio result from the combined overall result — never
    reduces the two to one number. `data_completeness_pct` is computed
    honestly from how many of the required inputs were actually available,
    never assumed to be 100%.
    """
    company = models.ForeignKey(
        'companies.CompanyProfile', on_delete=models.CASCADE, related_name='shariah_screens',
    )
    methodology = models.ForeignKey(ShariahMethodology, on_delete=models.PROTECT, related_name='screens')
    financial_facts = models.ForeignKey(
        CompanyFinancialFacts, null=True, blank=True, on_delete=models.SET_NULL, related_name='screens',
    )

    business_activity_result = models.CharField(max_length=20, choices=SCREEN_RESULT_CHOICES, default='not_screened')
    business_activity_reason = models.TextField(blank=True)
    business_activity_evidence_refs = models.JSONField(
        default=list, blank=True, help_text='List of EvidenceMemory source_reference strings cited.',
    )

    financial_ratio_result = models.CharField(max_length=20, choices=SCREEN_RESULT_CHOICES, default='not_screened')
    financial_ratio_detail = models.JSONField(
        default=dict, blank=True,
        help_text='Computed ratios, thresholds compared against, and which inputs were missing. '
                   'Never silently substitutes a missing value with zero.',
    )

    overall_result = models.CharField(max_length=20, choices=SCREEN_RESULT_CHOICES, default='not_screened')
    data_completeness_pct = models.FloatField(default=0.0)

    review_status = models.CharField(max_length=25, choices=REVIEW_STATUS_CHOICES, default='automated_preliminary')
    screened_at = models.DateTimeField(auto_now_add=True)
    screened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='shariah_screens_performed',
    )
    notes = models.TextField(blank=True)
    is_demo = models.BooleanField(default=False)

    class Meta:
        ordering = ['-screened_at']
        verbose_name = 'Company Shariah Screen'

    def __str__(self):
        return f'{self.company.company.name} — {self.methodology} — {self.get_overall_result_display()}'


class CompanyKPIAssessment(models.Model):
    """
    One company's assessment against one of the 114 principles in
    core.esg_principles_data.PRINCIPLES (kpi_id 1-114 — validated against
    that list at write time, not a separate DB-copied taxonomy). At most
    one row per (company, kpi_id): a real update overwrites the previous
    assessment, it does not accumulate duplicate rows. Missing evidence
    keeps a KPI at NOT_ASSESSED — 114 rows are never force-created for a
    company that has no evidence for most of them.
    """
    company = models.ForeignKey(
        'companies.CompanyProfile', on_delete=models.CASCADE, related_name='kpi_assessments',
    )
    kpi_id = models.PositiveSmallIntegerField(help_text='1-114, matches core.esg_principles_data.PRINCIPLES id.')
    status = models.CharField(max_length=30, choices=KPI_STATUS_CHOICES, default='not_assessed')
    rationale = models.TextField(
        blank=True,
        help_text='Why this status was assigned, in terms of the linked evidence — never an '
                   'unsupported model-generated claim.',
    )
    confidence = models.CharField(
        max_length=10, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='low',
    )
    last_assessed_at = models.DateTimeField(auto_now=True)
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='kpi_assessments_made',
    )
    is_demo = models.BooleanField(default=False)

    class Meta:
        ordering = ['kpi_id']
        verbose_name = 'Company KPI Assessment'
        constraints = [
            models.UniqueConstraint(fields=['company', 'kpi_id'], name='ci_unique_company_kpi'),
        ]

    def __str__(self):
        return f'{self.company.company.name} — KPI {self.kpi_id} — {self.get_status_display()}'


class CompanyKPIEvidenceLink(models.Model):
    """
    Links one CompanyKPIAssessment to one real evidence_memory.EvidenceMemory
    row, with an explicit relationship type set by whoever created the
    link (a human reviewer or a deterministic ingestion rule) — never
    inferred by an LLM. An assessment's status is derived from the
    aggregate of its linked evidence relationships and their quality
    (see services/kpi_engine.py), not asserted independently of them.
    """
    RELATIONSHIP_CHOICES = [
        ('supports', 'Supports'),
        ('conflicts', 'Conflicts'),
        ('context', 'Context Only'),
    ]
    assessment = models.ForeignKey(CompanyKPIAssessment, on_delete=models.CASCADE, related_name='evidence_links')
    evidence = models.ForeignKey(
        'evidence_memory.EvidenceMemory', on_delete=models.CASCADE, related_name='kpi_links',
    )
    relationship = models.CharField(max_length=10, choices=RELATIONSHIP_CHOICES)
    added_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='kpi_evidence_links_added',
    )

    class Meta:
        ordering = ['-added_at']
        verbose_name = 'Company KPI Evidence Link'
        constraints = [
            models.UniqueConstraint(fields=['assessment', 'evidence'], name='ci_unique_assessment_evidence'),
        ]

    def __str__(self):
        return f'{self.assessment} ← {self.get_relationship_display()} ({self.evidence_id})'


class CompanyControversy(models.Model):
    """
    A structured, evidence-backed negative-evidence record — distinct
    from companies.CompanyProfile.controversy_risk_score (an aggregate
    heatmap component) by being per-incident and evidence-linked, so a
    reviewer can see exactly what happened and what proves it, not just a
    risk number. Positive-appearing companies are never exempted from
    having controversies recorded here.
    """
    CATEGORY_CHOICES = [
        ('labour', 'Labour'),
        ('environmental', 'Environmental'),
        ('governance', 'Governance'),
        ('community', 'Community'),
        ('safety', 'Safety'),
        ('other', 'Other'),
    ]
    SEVERITY_CHOICES = [
        ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical'),
    ]
    STATUS_CHOICES = [
        ('unresolved', 'Unresolved'), ('disputed', 'Disputed'), ('resolved', 'Resolved'),
    ]

    company = models.ForeignKey(
        'companies.CompanyProfile', on_delete=models.CASCADE, related_name='controversies',
    )
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='unresolved')
    evidence = models.ForeignKey(
        'evidence_memory.EvidenceMemory', null=True, blank=True, on_delete=models.SET_NULL, related_name='controversies',
    )
    reported_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    is_demo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-reported_date', '-created_at']
        verbose_name = 'Company Controversy'
        verbose_name_plural = 'Company Controversies'

    def __str__(self):
        return f'{self.company.company.name} — {self.title} ({self.get_severity_display()})'


class ResearchWatchlistEntry(models.Model):
    """
    A user's personal research watchlist — the first such feature in the
    repo (audited: no prior watchlist/saved-companies concept existed).
    Status labels are deliberately research-oriented; this model must
    never carry a BUY/SELL/HOLD/target-price field. Strictly per-user:
    one user's watchlist is never visible to another user.
    """
    STATUS_CHOICES = [
        ('researching', 'Researching'),
        ('high_kpi_alignment', 'High KPI Alignment'),
        ('needs_review', 'Needs Review'),
        ('shariah_data_incomplete', 'Shariah Data Incomplete'),
        ('controversy_review', 'Controversy Review'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='research_watchlist')
    company = models.ForeignKey('companies.CompanyProfile', on_delete=models.CASCADE, related_name='watchlist_entries')
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='researching')
    notes = models.TextField(blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-added_at']
        verbose_name = 'Research Watchlist Entry'
        constraints = [
            models.UniqueConstraint(fields=['user', 'company'], name='ci_unique_user_company_watchlist'),
        ]

    def __str__(self):
        return f'{self.user} watching {self.company.company.name} ({self.get_status_display()})'
