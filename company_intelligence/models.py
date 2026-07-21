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

feat/company-evidence-ingestion (PR 10) additions — real evidence ingestion
for public companies, bridging the harvester app's existing acquisition
layer (Source/Evidence/dedup/verification, unchanged) into these consumer
models: CompanyKPIEvidenceLink.review_state (a deterministic KPI-candidate
matcher can PROPOSE a link from ingested evidence, never auto-CONFIRM one),
CompanyControversy.finding_type (allegation vs regulatory finding vs court
finding, never conflated), CompanyFinancialFactSource (per-metric
provenance — which real evidence backs each individual financial figure),
and EvidenceReviewAction (the minimal staff human-review audit trail).
Freshness, data-origin (DEMO/REAL_PUBLIC_DATA/MIXED), and evidence-quality
are deliberately NOT stored fields — they are computed at read time by
services/freshness.py, services/data_origin.py, services/evidence_quality.py,
since all three would otherwise silently go stale the moment they were
written.
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
    # feat/evidence-review-workbench (PR 12): 'insufficient_to_conclude' is a
    # genuine FOURTH relationship, not a synonym for 'context' — the evidence
    # really discusses the KPI (unlike 'context', which is topically adjacent
    # but not evaluative) but a reviewer determined it isn't enough on its
    # own to conclude support or conflict. Keeping it distinct from 'context'
    # is what lets a reviewer separate MATCH VALIDITY (does this evidence
    # really discuss this KPI?) from EVIDENCE RELATIONSHIP (what does it
    # conclude?) rather than collapsing every valid match into one bucket.
    RELATIONSHIP_CHOICES = [
        ('supports', 'Supports'),
        ('conflicts', 'Conflicts'),
        ('context', 'Context Only'),
        ('insufficient_to_conclude', 'Insufficient to Conclude'),
    ]
    # feat/company-evidence-ingestion (PR 10): a deterministic KPI-candidate
    # matcher (services/kpi_candidate_matching.py) may PROPOSE a link from
    # ingested evidence text — never auto-CONFIRM one. Only 'confirmed'
    # links count toward derive_status_from_evidence() (kpi_engine.py),
    # preserving PR9's "never generate an unsupported KPI assessment"
    # guarantee even as ingestion proposes candidates. Existing PR9 rows
    # (manually created, pre-dating this field) default to 'confirmed' —
    # a manually-added link was already a deliberate human action.
    #
    # feat/evidence-review-workbench (PR 12) adds 'needs_more_evidence' and
    # 'disputed' as REAL states (not just logged, no-op actions the way
    # PR10 first built mark_disputed/needs_more_evidence) — both are
    # deliberately excluded from the 'confirmed' filter
    # derive_status_from_evidence() already applies, so a disputed or
    # needs-more-evidence link stops counting toward a company's KPI status
    # the moment it leaves 'confirmed', with no engine change required.
    # "Confirmed" is not permanently unquestionable: MARK_DISPUTED can move
    # a confirmed link to 'disputed', and any of the confirm_*/reject
    # actions can re-review a disputed link back out of that state — the
    # full history is preserved as an immutable EvidenceReviewAction chain,
    # never overwritten.
    REVIEW_STATE_CHOICES = [
        ('proposed', 'Proposed — Awaiting Review'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
        ('needs_more_evidence', 'Needs More Evidence'),
        ('disputed', 'Disputed'),
    ]
    assessment = models.ForeignKey(CompanyKPIAssessment, on_delete=models.CASCADE, related_name='evidence_links')
    evidence = models.ForeignKey(
        'evidence_memory.EvidenceMemory', on_delete=models.CASCADE, related_name='kpi_links',
    )
    relationship = models.CharField(max_length=30, choices=RELATIONSHIP_CHOICES)
    review_state = models.CharField(max_length=25, choices=REVIEW_STATE_CHOICES, default='confirmed')
    match_basis = models.CharField(
        max_length=200, blank=True,
        help_text='For a proposed (ingestion-matched) link: the deterministic keyword/category match that '
                   'produced it — never an LLM claim. Blank for manually-created links.',
    )
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
    # feat/company-evidence-ingestion (PR 10) — an allegation is not proven
    # fact; a court finding is not the same evidentiary weight as a news
    # report. Never inferred automatically — set from what the linked
    # evidence's own document_category/source_type honestly supports, or
    # left at the conservative default.
    FINDING_TYPE_CHOICES = [
        ('allegation', 'Allegation'),
        ('investigation', 'Investigation (Ongoing)'),
        ('regulatory_finding', 'Regulatory Finding'),
        ('court_finding', 'Court Finding'),
        ('company_admission', 'Company Admission'),
        ('verified_event', 'Verified Event'),
    ]

    company = models.ForeignKey(
        'companies.CompanyProfile', on_delete=models.CASCADE, related_name='controversies',
    )
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='other')
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='unresolved')
    finding_type = models.CharField(max_length=25, choices=FINDING_TYPE_CHOICES, default='allegation')
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


class CompanyFinancialFactSource(models.Model):
    """
    feat/company-evidence-ingestion (PR 10) — per-metric provenance for one
    CompanyFinancialFacts row. A single `source` free-text string on the
    parent row (PR9) cannot honestly say WHICH of its six figures came from
    where, or whether each was directly reported or derived — this model
    gives each individual metric its own real evidence link and an explicit
    directly-reported/derived flag, so "Interest-bearing debt: $X — source:
    [this exact filing]" is a real, inspectable claim, never an aggregate
    guess. One row per metric per financial-facts snapshot.
    """
    METRIC_CHOICES = [
        ('market_cap_usd', 'Market Capitalisation'),
        ('total_debt_usd', 'Total Debt'),
        ('cash_and_equivalents_usd', 'Cash & Equivalents'),
        ('interest_bearing_securities_usd', 'Interest-Bearing Securities'),
        ('non_permissible_income_usd', 'Non-Permissible Income'),
        ('revenue_usd', 'Revenue'),
    ]
    financial_facts = models.ForeignKey(
        CompanyFinancialFacts, on_delete=models.CASCADE, related_name='metric_sources',
    )
    metric = models.CharField(max_length=40, choices=METRIC_CHOICES)
    evidence = models.ForeignKey(
        'evidence_memory.EvidenceMemory', null=True, blank=True, on_delete=models.SET_NULL, related_name='financial_fact_sources',
    )
    is_derived = models.BooleanField(
        default=False,
        help_text='True when this value was derived/interpreted from a reported figure (e.g. interest '
                   'income used as a proxy for non-permissible income), never for a value copied directly '
                   'from the filing.',
    )
    interpretation_note = models.TextField(
        blank=True, help_text='Required explanation when is_derived=True — how the value was derived.',
    )

    class Meta:
        ordering = ['metric']
        verbose_name = 'Company Financial Fact Source'
        constraints = [
            models.UniqueConstraint(fields=['financial_facts', 'metric'], name='ci_unique_factset_metric'),
        ]

    def __str__(self):
        basis = 'derived' if self.is_derived else 'reported'
        return f'{self.financial_facts} — {self.get_metric_display()} ({basis})'

    @property
    def value(self):
        """The real numeric value this row is provenance for, resolved here
        in Python — Django templates cannot look up a model field by a
        variable name (no `{{ obj|attr:field_name }}` filter exists), so
        this property exists precisely so templates never need one."""
        return getattr(self.financial_facts, self.metric, None)


class DiscoveredSource(models.Model):
    """
    feat/stewardship-universe (PR 13) — one candidate authoritative source
    found by services/source_discovery.py for a company, BEFORE (or after)
    it becomes a real, fetchable harvester.Source row. This is the missing
    layer PR9-12 never built: identity resolution today is 100% hardcoded
    CIK/company-number dicts plus a staff member manually typing a URL into
    the "Register Document Source" form — this model is the governed,
    inspectable record of HOW a source was found and whether it's trusted
    enough to register automatically or needs a human's approval first.

    Deliberately distinct from harvester.Source (the real, fetchable
    registration) and companies.CompanySource (a lightweight, informal
    citation list with no tier/provenance/status) — this is upstream of
    both: "EcoIQ found this URL via this method; is it authoritative
    enough to trust automatically, or does a reviewer need to look at it
    first?" A discovered source that's approved gets a harvester_source FK
    once registered; one is never deleted when superseded — old candidates
    stay on record even after rejection, so provenance is never erased.
    """
    DISCOVERY_METHOD_CHOICES = [
        ('sec_edgar_identity', 'SEC EDGAR CIK Mapping (Regulatory Filing)'),
        ('companies_house_identity', 'Companies House Number Mapping (UK Regulatory Filing)'),
        ('curated_official_domain', 'EcoIQ-Curated Official Domain Registry'),
        ('staff_registered_field', 'Existing Staff-Entered Company Profile Field'),
        ('manual', 'Manually Added by Staff'),
    ]
    STATUS_CHOICES = [
        ('candidate', 'Candidate — Awaiting Staff Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('registered', 'Registered as an Active Source'),
    ]
    # A domain being "official" is a real claim about provenance, not a
    # guess from the company's name — VERIFIED means EcoIQ has independently
    # curated/confirmed this exact domain for this exact company (see
    # services/known_sources.py); PROBABLE means it came from a field staff
    # typed in previously but was never independently cross-checked;
    # UNVERIFIED/CONFLICTING are honest states for anything less certain.
    # A PROBABLE/UNVERIFIED domain must never silently become a Tier-1
    # source — see source_discovery.py's tier assignment.
    DOMAIN_STATUS_CHOICES = [
        ('verified', 'Verified Official Domain'),
        ('probable', 'Probable — Staff-Entered, Not Independently Verified'),
        ('unverified', 'Unverified'),
        ('conflicting', 'Conflicting — Multiple Candidate Domains Found'),
    ]

    company = models.ForeignKey(
        'companies.CompanyProfile', on_delete=models.CASCADE, related_name='discovered_sources',
    )
    url = models.URLField(max_length=1000)
    domain = models.CharField(max_length=200, blank=True)
    publisher = models.CharField(max_length=200, blank=True)
    source_type = models.CharField(max_length=40, blank=True, help_text='harvester.constants.SOURCE_TYPES value.')
    # Tier 1 (highest authority) .. Tier 4 (self-reported) — same vocabulary
    # as harvester.verification.source_tier(), never a second tier scale.
    tier = models.PositiveSmallIntegerField(default=4)
    discovery_method = models.CharField(max_length=30, choices=DISCOVERY_METHOD_CHOICES)
    domain_status = models.CharField(max_length=15, choices=DOMAIN_STATUS_CHOICES, default='unverified')
    # 0-1 confidence in this candidate being genuinely useful, where the
    # discovery method itself provides a real basis for one (e.g. an exact
    # CIK/company-number match is 1.0; a staff-entered field carried over
    # with no independent check is left None — never a fabricated number).
    confidence = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default='candidate')
    discovered_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='discovered_sources_reviewed',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    harvester_source = models.ForeignKey(
        'harvester.Source', null=True, blank=True, on_delete=models.SET_NULL, related_name='discovered_from',
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-discovered_at']
        verbose_name = 'Discovered Source'
        constraints = [
            models.UniqueConstraint(fields=['company', 'url'], name='ci_unique_discovered_source_url'),
        ]

    def __str__(self):
        return f'{self.company.company.slug} — {self.url[:60]} ({self.get_status_display()})'


class CompanyRefreshRun(models.Model):
    """
    feat/stewardship-universe (PR 13) — the structured, per-company outcome
    of one services/refresh_orchestrator.py::refresh_company_intelligence()
    call. Distinct from ai_observatory.AnalysisSession (which stays generic
    across every EcoIQ pipeline and deliberately carries no
    stewardship-specific fields like "documents unchanged" or "duplicates
    ignored") — this model is the domain-specific structured result the
    brief's Section 25/11 asks for, linked back to its own Observatory
    session so raw stage timings/telemetry are never duplicated here, only
    referenced. One row per refresh attempt; never overwritten — refresh
    history is this table's own append-only log, matching harvester's
    IngestionRun/BatchHarvestRun precedent at the per-source/batch level.

    status is never optimistic: COMPLETE only when every checked source
    succeeded or was a genuine no-op; PARTIAL when at least one source
    succeeded but at least one failed; FAILED when nothing succeeded at
    all. A single failed source must never be allowed to make the whole
    run silently report COMPLETE.
    """
    TRIGGER_CHOICES = [
        ('manual', 'Manual (Staff-Triggered)'),
        ('scheduled', 'Scheduled'),
        ('management_command', 'Management Command'),
        ('other', 'Other'),
    ]
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('complete', 'Complete'),
        ('partial', 'Partial'),
        ('failed', 'Failed'),
    ]

    company = models.ForeignKey(
        'companies.CompanyProfile', on_delete=models.CASCADE, related_name='refresh_runs',
    )
    observatory_session = models.ForeignKey(
        'ai_observatory.AnalysisSession', null=True, blank=True, on_delete=models.SET_NULL, related_name='refresh_runs',
    )
    triggered_by = models.CharField(max_length=25, choices=TRIGGER_CHOICES, default='manual')
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='refresh_runs_triggered',
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='running')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    sources_checked = models.PositiveIntegerField(default=0)
    sources_failed = models.PositiveIntegerField(default=0)
    documents_new = models.PositiveIntegerField(default=0)
    documents_updated = models.PositiveIntegerField(default=0)
    documents_unchanged = models.PositiveIntegerField(default=0)
    evidence_created = models.PositiveIntegerField(default=0)
    duplicates_ignored = models.PositiveIntegerField(default=0)
    kpi_candidates_proposed = models.PositiveIntegerField(default=0)
    review_required_count = models.PositiveIntegerField(default=0)

    warnings = models.JSONField(default=list, blank=True)
    errors = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-started_at']
        verbose_name = 'Company Refresh Run'

    def __str__(self):
        return f'{self.company.company.slug} refresh — {self.get_status_display()} ({self.started_at:%Y-%m-%d %H:%M})'

    @property
    def duration_seconds(self):
        if self.started_at and self.completed_at:
            return round((self.completed_at - self.started_at).total_seconds(), 2)
        return None


class EvidenceReviewAction(models.Model):
    """
    feat/company-evidence-ingestion (PR 10), extended by feat/evidence-
    review-workbench (PR 12) — the staff human-review workflow's one
    immutable, timestamped audit row per decision (never edited/deleted),
    attributing exactly who made the call, what state it moved from/to, and
    why. This is the ONLY thing that ever moves a KPI link's review_state —
    never a silent field flip with no reviewer/timestamp/reason on record.

    PR 12 replaces the single generic 'verify' action with four explicit
    confirm_* actions, so a reviewer's decision separates MATCH VALIDITY
    (was a real KPI relationship even proposed?) from EVIDENCE RELATIONSHIP
    (does the evidence support, conflict, merely provide context, or is it
    insufficient to conclude?) — never collapsing every valid match into
    'supports' by default. mark_disputed/needs_more_evidence are upgraded
    from PR10's audit-log-only, no-op actions to REAL review_state
    mutations (see CompanyKPIEvidenceLink's REVIEW_STATE_CHOICES docstring)
    — a dispute now genuinely stops a link counting toward a company's KPI
    status, and can be resolved by any later confirm_*/reject action
    (re-review), with the full chain of PRIOR decisions preserved here,
    never overwritten.

    At least one of `evidence`/`kpi_evidence_link` must be set (enforced by
    the service layer, mirroring this app's existing convention of
    ownership checks in services rather than DB CheckConstraints across
    nullable FKs to different apps).
    """
    ACTION_CHOICES = [
        ('confirm_supports', 'Confirm — Supports'),
        ('confirm_conflicts', 'Confirm — Conflicts'),
        ('confirm_context', 'Confirm — Context Only'),
        ('confirm_insufficient', 'Confirm — Insufficient to Conclude'),
        ('reject', 'Reject Match'),
        ('needs_more_evidence', 'Needs More Evidence'),
        ('mark_disputed', 'Mark Disputed'),
    ]
    evidence = models.ForeignKey(
        'evidence_memory.EvidenceMemory', null=True, blank=True, on_delete=models.CASCADE, related_name='review_actions',
    )
    kpi_evidence_link = models.ForeignKey(
        CompanyKPIEvidenceLink, null=True, blank=True, on_delete=models.CASCADE, related_name='review_actions',
    )
    action = models.CharField(max_length=25, choices=ACTION_CHOICES)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='evidence_review_actions')
    reason = models.TextField(blank=True)

    # feat/evidence-review-workbench (PR 12) — explicit before/after
    # snapshots on the audit row itself, so the history is readable without
    # having to replay the whole action sequence to know what actually
    # changed at each step.
    previous_review_state = models.CharField(max_length=25, blank=True)
    new_review_state = models.CharField(max_length=25, blank=True)
    # The relationship this specific decision set (blank for
    # reject/needs_more_evidence/mark_disputed, which don't assert one).
    relationship_decision = models.CharField(
        max_length=30, blank=True, choices=CompanyKPIEvidenceLink.RELATIONSHIP_CHOICES,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Evidence Review Action'

    def __str__(self):
        target = self.kpi_evidence_link_id and f'KPI link #{self.kpi_evidence_link_id}' or f'Evidence #{self.evidence_id}'
        return f'{self.get_action_display()} — {target} by {self.reviewer}'
