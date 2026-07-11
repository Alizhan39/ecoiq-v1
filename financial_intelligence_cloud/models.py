"""
financial_intelligence_cloud/models.py — the commercial subscription layer:
continuous risk, opportunity and capital intelligence for accounting firms,
financial institutions and investment portfolios.

Turns the existing governed AI-agent / Waste-to-Value / Capital Allocation
architecture into a product: Client Opportunity Radar (who should I call
today?), Portfolio Intelligence (where is value at risk?), Capital
Allocation (where should the next £1 go?).

Phase 1A (Canonical Architecture Decision Analysis): this app is the real
institutional intelligence interface for EcoIQ going forward —
institutional_finance_engine (a 100% static mock with no models) is
deprecated in its favour; see institutional_finance_engine/apps.py.

Honesty note, enforced throughout this app's services and templates:
- capital_at_risk != verified_recovered_value
- potential_recoverable_value != verified_recovered_value
- finance opportunity identified != credit approval
- investment ranking != investment advice
- recommended client call != guaranteed advisory revenue
- estimated payback != verified return
- funding route identified != funding secured

Security/isolation note: this repo has no real multi-tenant Django auth
anywhere. Every platform module, including this one, is public demo
content. Institutional-account/portfolio isolation here is enforced by
explicit queryset filtering (see services/qa_router.py) and proven by
tests, not by login-gated permissions — do not present this as a
production tenant-isolation system.

`PortfolioSignal.source_run` is the field that honestly distinguishes the
one real-agent-pipeline flagship case per demo portfolio (FreshBridge Foods,
ABC Engineering) from the deterministically generated bulk of entities:
populated only for the former, null for the latter.
"""
from django.db import models
from django.utils import timezone

ACCOUNT_TYPE_CHOICES = [
    ('accounting_firm',       'Accounting Firm'),
    ('advisory_firm',         'Advisory Firm'),
    ('bank',                  'Bank'),
    ('lender',                'Lender'),
    ('private_equity',        'Private Equity'),
    ('asset_manager',         'Asset Manager'),
    ('family_office',         'Family Office'),
    ('corporate',             'Corporate'),
    ('development_finance',   'Development Finance Institution'),
    ('sovereign_institution', 'Sovereign Institution'),
]

SUBSCRIPTION_TIER_CHOICES = [
    ('starter',       'Starter'),
    ('professional',  'Professional'),
    ('institutional', 'Institutional'),
]

PORTFOLIO_TYPE_CHOICES = [
    ('client_book',          'Client Book'),
    ('investment_portfolio', 'Investment Portfolio'),
    ('loan_book',            'Loan Book'),
]

ENTITY_TYPE_CHOICES = [
    ('sme_client',        'SME Client'),
    ('portfolio_company',  'Portfolio Company'),
    ('borrower',           'Borrower'),
]

RELATIONSHIP_STAGE_CHOICES = [
    ('active',  'Active'),
    ('at_risk', 'At Risk'),
    ('dormant', 'Dormant'),
    ('prospect', 'Prospect'),
]

SIGNAL_TYPE_CHOICES = [
    ('financial_risk',              'Financial Risk'),
    ('operational_loss',            'Operational Loss'),
    ('working_capital',             'Working Capital'),
    ('margin_erosion',              'Margin Erosion'),
    ('energy_cost',                 'Energy Cost'),
    ('asset_underperformance',      'Asset Underperformance'),
    ('finance_opportunity',         'Finance Opportunity'),
    ('capital_allocation',          'Capital Allocation'),
    ('evidence_gap',                'Evidence Gap'),
    ('governance_review',           'Governance Review'),
    ('MRV_update',                  'MRV Update'),
    ('client_advisory_opportunity', 'Client Advisory Opportunity'),
]

EVIDENCE_QUALITY_CHOICES = [
    ('strong',  'Strong'),
    ('medium',  'Medium'),
    ('weak',    'Weak'),
    ('missing', 'Missing'),
]

SIGNAL_STATUS_CHOICES = [
    ('open',     'Open'),
    ('reviewed', 'Reviewed'),
    ('actioned', 'Actioned'),
    ('dismissed', 'Dismissed'),
]

OPPORTUNITY_TYPE_CHOICES = [
    ('cost_recovery_advisory',    'Cost Recovery Advisory'),
    ('finance_readiness_advisory', 'Finance Readiness Advisory'),
    ('capital_raise_support',      'Capital Raise Support'),
    ('governance_advisory',        'Governance Advisory'),
]

OPPORTUNITY_STATUS_CHOICES = [
    ('identified', 'Identified'),
    ('queued',     'Queued'),
    ('contacted',  'Contacted'),
    ('declined',   'Declined'),
    ('converted',  'Converted'),
]

FEED_ITEM_TYPE_CHOICES = [
    ('new_signal',            'New Signal'),
    ('new_opportunity',        'New Opportunity'),
    ('evidence_gap_flagged',    'Evidence Gap Flagged'),
    ('human_approval_needed',   'Human Approval Needed'),
    ('status_change',           'Status Change'),
]


class InstitutionalAccount(models.Model):
    """One subscribing firm — an accounting firm, bank, PE fund, etc."""
    account_type = models.CharField(max_length=30, choices=ACCOUNT_TYPE_CHOICES)
    firm_name    = models.CharField(max_length=200)
    slug         = models.SlugField(max_length=220, unique=True)

    subscription_tier        = models.CharField(max_length=15, choices=SUBSCRIPTION_TIER_CHOICES, default='starter')
    subscription_price_label = models.CharField(max_length=60, default='Contact / Custom')

    is_demo = models.BooleanField(default=True, help_text='Every account seeded by this build is a labelled demo, never a real customer.')
    relationship_owner = models.CharField(max_length=150, blank=True)

    # White-label fields — rendering these must never hide evidence status,
    # uncertainty, or estimated-vs-verified labels (enforced in templates + tests).
    report_title             = models.CharField(max_length=200, blank=True)
    logo_reference            = models.CharField(max_length=300, blank=True, help_text='Text/URL reference only — no file upload.')
    approved_brand_accent     = models.CharField(max_length=20, blank=True, help_text='e.g. "#00e89a"')
    client_facing_disclaimer  = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['firm_name']

    def __str__(self):
        return self.firm_name


class Portfolio(models.Model):
    institutional_account = models.ForeignKey(InstitutionalAccount, on_delete=models.CASCADE, related_name='portfolios')
    name            = models.CharField(max_length=200)
    portfolio_type  = models.CharField(max_length=25, choices=PORTFOLIO_TYPE_CHOICES)
    description     = models.TextField(blank=True)

    assets_under_analysis          = models.FloatField(default=0.0, help_text='Analysed exposure, not an audited/verified AUM figure.')
    assets_under_analysis_currency = models.CharField(max_length=10, default='GBP')

    entity_count      = models.PositiveIntegerField(default=0, help_text='Denormalized, kept in sync by add_portfolio_entity().')
    last_refreshed_at = models.DateTimeField(null=True, blank=True)
    status            = models.CharField(max_length=20, default='active')

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [models.Index(fields=['institutional_account'])]

    def __str__(self):
        return f'{self.name} ({self.institutional_account.firm_name})'


class PortfolioEntity(models.Model):
    """One client / portfolio company / borrower inside a portfolio."""
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='entities')
    name      = models.CharField(max_length=200)
    sector    = models.CharField(max_length=100, blank=True)
    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPE_CHOICES)
    country   = models.CharField(max_length=100, blank=True)

    relationship_stage = models.CharField(max_length=15, choices=RELATIONSHIP_STAGE_CHOICES, default='active')

    is_flagship = models.BooleanField(
        default=False,
        help_text='True only for the one entity per demo portfolio that runs through the real Council agent pipeline (e.g. FreshBridge Foods, ABC Engineering).',
    )
    source_operational_loss = models.ForeignKey(
        'waste_to_value_capital_allocation_engine.OperationalLoss', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='+',
        help_text='Populated only for the flagship entity — links this entity to the real OperationalLoss row its signal was derived from.',
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [models.Index(fields=['portfolio', 'relationship_stage'])]
        verbose_name_plural = 'Portfolio entities'

    def __str__(self):
        return self.name


class PortfolioSignal(models.Model):
    """The atomic unit that client-radar, portfolio-risk and finance-opportunity ranking all run over."""
    portfolio_entity = models.ForeignKey(PortfolioEntity, on_delete=models.CASCADE, related_name='signals')
    signal_type = models.CharField(max_length=30, choices=SIGNAL_TYPE_CHOICES)
    title       = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    capital_at_risk             = models.FloatField(null=True, blank=True, help_text='Projected/estimated exposure. Never the same as verified_recovered_value.')
    potential_recoverable_value = models.FloatField(null=True, blank=True, help_text='Estimated. Never the same as verified_recovered_value.')
    verified_recovered_value    = models.FloatField(null=True, blank=True, help_text='Stays null until a real MRV-style verification exists — never fabricated.')
    currency = models.CharField(max_length=10, default='GBP')

    urgency_score    = models.FloatField(default=50.0)
    evidence_quality = models.CharField(max_length=10, choices=EVIDENCE_QUALITY_CHOICES, default='medium')
    confidence       = models.FloatField(default=50.0)

    human_approval_required = models.BooleanField(default=False)

    source_run = models.ForeignKey(
        'agent_runtime_model_router.AgentRun', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
        help_text='Populated ONLY for the flagship, real-agent-pipeline case. Null for every deterministically generated signal.',
    )

    detected_at = models.DateTimeField(default=timezone.now)
    status      = models.CharField(max_length=15, choices=SIGNAL_STATUS_CHOICES, default='open')

    class Meta:
        ordering = ['-urgency_score', '-detected_at']
        indexes = [models.Index(fields=['portfolio_entity', 'signal_type', 'status'])]

    def __str__(self):
        return self.title


class AdvisoryOpportunity(models.Model):
    """The 'who to call' / 'what to pitch' object — never carries a monetary 'expected fee' field, deliberately."""
    portfolio_entity = models.ForeignKey(PortfolioEntity, on_delete=models.CASCADE, related_name='advisory_opportunities')
    opportunity_type = models.CharField(max_length=30, choices=OPPORTUNITY_TYPE_CHOICES)
    headline  = models.CharField(max_length=255)
    rationale = models.TextField(blank=True)

    estimated_capital_at_risk    = models.FloatField(null=True, blank=True)
    estimated_recoverable_value  = models.FloatField(null=True, blank=True)
    finance_readiness_score      = models.FloatField(null=True, blank=True)
    funding_gap                  = models.FloatField(null=True, blank=True)
    currency = models.CharField(max_length=10, default='GBP')

    priority_score = models.FloatField(default=0.0, help_text='Output of rank_clients_to_call_today()/rank_finance_opportunities() — stored, not recomputed per-request.')
    requires_human_review = models.BooleanField(default=True)
    human_approved = models.BooleanField(null=True, blank=True, default=None, help_text='Explicit human sign-off, read by services/human_approval_gate.py — never inferred.')
    status = models.CharField(max_length=15, choices=OPPORTUNITY_STATUS_CHOICES, default='identified')

    linked_signal = models.ForeignKey(PortfolioSignal, null=True, blank=True, on_delete=models.SET_NULL, related_name='opportunities')

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority_score']
        indexes = [models.Index(fields=['portfolio_entity', 'status'])]

    def __str__(self):
        return self.headline


class OpportunityFeedItem(models.Model):
    """The daily activity stream — 'what changed since yesterday'."""
    institutional_account = models.ForeignKey(InstitutionalAccount, on_delete=models.CASCADE, related_name='feed_items')
    portfolio = models.ForeignKey(Portfolio, null=True, blank=True, on_delete=models.SET_NULL, related_name='feed_items')
    item_type = models.CharField(max_length=25, choices=FEED_ITEM_TYPE_CHOICES)
    headline  = models.CharField(max_length=255)
    detail    = models.TextField(blank=True)

    related_signal      = models.ForeignKey(PortfolioSignal, null=True, blank=True, on_delete=models.SET_NULL, related_name='feed_items')
    related_opportunity  = models.ForeignKey(AdvisoryOpportunity, null=True, blank=True, on_delete=models.SET_NULL, related_name='feed_items')

    occurred_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-occurred_at']
        indexes = [models.Index(fields=['institutional_account', 'occurred_at'])]

    def __str__(self):
        return self.headline


class PortfolioDailyBrief(models.Model):
    """A dated, point-in-time snapshot — JSON snapshot lists so it never silently drifts as underlying rows change."""
    institutional_account = models.ForeignKey(InstitutionalAccount, on_delete=models.CASCADE, related_name='daily_briefs')
    brief_date = models.DateField(default=timezone.now)

    headline_summary = models.TextField(blank=True)
    top_clients_to_call        = models.JSONField(default=list, blank=True)
    top_portfolio_risks         = models.JSONField(default=list, blank=True)
    top_finance_opportunities    = models.JSONField(default=list, blank=True)

    new_signals_count        = models.PositiveIntegerField(default=0)
    human_approvals_pending  = models.PositiveIntegerField(default=0)
    verified_value_recovered_to_date = models.FloatField(default=0.0)
    currency = models.CharField(max_length=10, default='GBP')

    generated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-brief_date']
        unique_together = [('institutional_account', 'brief_date')]

    def __str__(self):
        return f'{self.institutional_account.firm_name} — {self.brief_date}'
