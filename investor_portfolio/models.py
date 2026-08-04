"""
EcoIQ Portfolio & Watchlist Intelligence — models.

Builds on the existing companies.InvestmentRelevanceReport / league.Company
market-data architecture (see companies/investment_report.py) rather than
duplicating scoring or AI logic. This app adds three things on top of it:

  Watchlist / WatchlistItem   — a named, orderable list of companies a user
                                 follows. No financial data at all.
  Portfolio / Holding          — a user's actual holdings (shares, acquisition
                                 price/date, currency). See the "Holding
                                 model" note below for the aggregation choice.
  PortfolioSnapshot            — an immutable, versioned record of a
                                 deterministic portfolio calculation (value,
                                 EcoIQ exposure, distribution, concentration).
                                 Mirrors companies.CompanyScoreSnapshot /
                                 InvestmentRelevanceReport: never overwritten,
                                 always a new row per calculation.
  PortfolioBriefing             — an AI-generated *summary* of a snapshot's
                                 already-computed numbers (never itself does
                                 the math). Mirrors InvestmentRelevanceReport's
                                 draft/reviewed/published lifecycle, but stays
                                 owner+staff-only regardless of status — see
                                 the model's own docstring.

Holding model — aggregated-per-company, not acquisition lots
--------------------------------------------------------------
This project has no existing transaction/ledger model anywhere (no buy/sell
event log, no cost-basis lot tracking for anything else in the repo).
Introducing FIFO/LIFO lot accounting here would be new financial-accounting
machinery unrelated to what EcoIQ already does, for a feature whose stated
purpose is sustainability-exposure visibility, not tax-lot reporting. One
row per (portfolio, company) — average acquisition price, like most retail
portfolio trackers — is the simpler, cleanly-supported choice; enforced via
a unique_together constraint. A user who wants to track separate lots can
still do so as separate manual portfolios.
"""
from django.conf import settings
from django.db import models

from league.models import Company


# ── Watchlist ────────────────────────────────────────────────────────────────

class Watchlist(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='watchlists')
    companies = models.ManyToManyField(Company, through='WatchlistItem',
                                        related_name='watchlisted_by', blank=True)
    is_public = models.BooleanField(default=False, help_text='Private by default')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        unique_together = [('owner', 'name')]
        verbose_name = 'Watchlist'
        verbose_name_plural = 'Watchlists'

    def __str__(self):
        return f'{self.name} ({self.owner.get_username()})'


class WatchlistItem(models.Model):
    watchlist = models.ForeignKey(Watchlist, on_delete=models.CASCADE, related_name='items')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='+')
    order = models.PositiveIntegerField(default=0, help_text='Manual ordering within the watchlist')
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'added_at']
        unique_together = [('watchlist', 'company')]
        verbose_name = 'Watchlist Item'
        verbose_name_plural = 'Watchlist Items'

    def __str__(self):
        return f'{self.company.name} in {self.watchlist.name}'


# ── Portfolio ────────────────────────────────────────────────────────────────

class Portfolio(models.Model):
    """
    A user's personal holdings. Always private to its owner (+ staff) — see
    investor_portfolio/views.py:_portfolios_visible_to. There is
    intentionally no public-portfolio viewing path anywhere in this app:
    acquisition prices, share counts, total value, and notes must never be
    exposed publicly (see the module docstring in views.py).
    """
    name = models.CharField(max_length=150)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name='portfolios')
    base_currency = models.CharField(max_length=8, default='USD',
                                      help_text='Display/reporting currency for this portfolio')
    description = models.TextField(blank=True)
    cash_balance = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True,
                                        help_text='Optional uninvested cash, in base_currency')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        unique_together = [('owner', 'name')]
        verbose_name = 'Portfolio'
        verbose_name_plural = 'Portfolios'

    def __str__(self):
        return f'{self.name} ({self.owner.get_username()})'

    @property
    def latest_snapshot(self):
        return self.snapshots.order_by('-calculated_at').first()

    @property
    def latest_briefing(self):
        return self.briefings.order_by('-version').first()


class Holding(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='holdings')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='+')

    shares = models.DecimalField(max_digits=18, decimal_places=4)
    avg_acquisition_price = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True,
                                                 help_text='Average price paid per share, in acquisition_currency')
    acquisition_currency = models.CharField(max_length=8, blank=True, default='USD')
    acquisition_date = models.DateField(null=True, blank=True)

    manual_current_value = models.DecimalField(
        max_digits=16, decimal_places=2, null=True, blank=True,
        help_text='Manually entered total holding value — used only when the '
                   'company has no live EcoIQ market price')

    notes = models.TextField(blank=True)
    include_in_analytics = models.BooleanField(
        default=True, help_text='Uncheck to exclude this holding from portfolio-level EcoIQ analytics')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        unique_together = [('portfolio', 'company')]  # aggregated per company — see module docstring
        verbose_name = 'Holding'
        verbose_name_plural = 'Holdings'

    def __str__(self):
        return f'{self.shares} {self.company.ticker or self.company.name} in {self.portfolio.name}'


# ── PortfolioSnapshot ────────────────────────────────────────────────────────

class PortfolioSnapshot(models.Model):
    """
    Immutable, point-in-time result of a deterministic portfolio calculation
    (investor_portfolio/calculations.py). NEVER updated in place — recompute
    creates a new row, exactly like companies.CompanyScoreSnapshot. This is
    what change-tracking (spec §8) diffs against.
    """
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='snapshots')
    calculated_at = models.DateTimeField(auto_now_add=True)
    methodology_version = models.CharField(max_length=20, default='v1')

    # ── Value ──
    total_market_value = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True,
        help_text='Null when fx_incomplete — see currency_subtotals instead')
    total_value_currency = models.CharField(max_length=8, blank=True)
    fx_incomplete = models.BooleanField(
        default=False, help_text='True when holdings span >1 currency and no FX conversion was applied')
    currency_subtotals = models.JSONField(default=dict, blank=True,
                                           help_text='{currency: subtotal} — authoritative when fx_incomplete')

    # ── EcoIQ exposure (deterministic — see methodology.py) ──
    exposure_score = models.FloatField(null=True, blank=True,
                                        help_text='0-100 weighted exposure score across analytics-included holdings')
    known_exposure_pct = models.FloatField(null=True, blank=True,
                                            help_text='% of analytics-included value with a published classification')
    unknown_exposure_pct = models.FloatField(null=True, blank=True,
                                              help_text='% of analytics-included value with NO published '
                                                        'classification — never folded into "low risk"')
    evidence_coverage_pct = models.FloatField(null=True, blank=True,
                                               help_text='% of analytics-included value backed by verified or '
                                                          'company-reported evidence (vs. AI-interpretation only)')
    stale_analysis_pct = models.FloatField(null=True, blank=True,
                                            help_text='% of analytics-included value whose report is >90 days old')

    distribution = models.JSONField(
        default=dict, blank=True,
        help_text='{lower_exposure/moderate_exposure/elevated_exposure/high_exposure/insufficient_evidence: pct}')
    concentration = models.JSONField(
        default=dict, blank=True,
        help_text='sector/country/exchange/classification concentration breakdowns')
    holding_snapshots = models.JSONField(
        default=list, blank=True,
        help_text='Per-holding computed data: weight_pct, market_value, classification, confidence, '
                   'report_version, report_date, stale flag, exposure_contribution')

    class Meta:
        ordering = ['-calculated_at']
        verbose_name = 'Portfolio Snapshot'
        verbose_name_plural = 'Portfolio Snapshots'

    def __str__(self):
        return f'{self.portfolio.name} snapshot @ {self.calculated_at:%Y-%m-%d %H:%M}'


# ── PortfolioBriefing ────────────────────────────────────────────────────────

BRIEFING_STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('reviewed', 'Reviewed'),
    ('published', 'Published'),
]


class PortfolioBriefing(models.Model):
    """
    AI-generated narrative *summary* of a PortfolioSnapshot's already-computed
    numbers — see investor_portfolio/briefing.py. The AI never calculates
    anything here; it explains stored numbers and is checked against the same
    prohibited-recommendation-language filter used for company reports
    (companies.investment_report.check_prohibited_language).

    status mirrors InvestmentRelevanceReport's draft/reviewed/published
    lifecycle for consistency, but — unlike a company report — a portfolio
    briefing is NEVER shown to anyone but its owner (+ staff), regardless of
    status. "Published" here means "the user has finalized it for their own
    records", not "visible on the public internet". There is intentionally
    no public-briefing view anywhere in this app.
    """
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name='briefings')
    snapshot = models.ForeignKey(PortfolioSnapshot, on_delete=models.CASCADE, related_name='briefings')
    version = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=BRIEFING_STATUS_CHOICES, default='draft')

    content = models.JSONField(default=dict, blank=True)

    model_name = models.CharField(max_length=80, blank=True)
    model_provider = models.CharField(max_length=30, blank=True)
    routing_reason = models.TextField(blank=True)
    prompt_version = models.CharField(max_length=20, default='v1')
    methodology_version = models.CharField(max_length=20, default='v1')

    prohibited_language_flags = models.JSONField(default=list, blank=True)

    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name='+')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name='+')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-version']
        unique_together = [('portfolio', 'version')]
        verbose_name = 'Portfolio Briefing'
        verbose_name_plural = 'Portfolio Briefings'

    def __str__(self):
        return f'{self.portfolio.name} briefing v{self.version} ({self.status})'

    @property
    def is_publishable(self) -> bool:
        return not self.prohibited_language_flags
