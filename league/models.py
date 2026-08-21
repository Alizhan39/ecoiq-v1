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

    # ── Public markets ───────────────────────────────────────────────────────
    ticker                 = models.CharField(
        max_length=20, blank=True,
        help_text='Exchange ticker symbol, Yahoo Finance format (e.g. AAPL, SHEL.L, 2222.SR)')
    exchange               = models.CharField(
        max_length=30, blank=True,
        help_text='Explicit exchange code for chart links (e.g. NASDAQ, LSE, TADAWUL). '
                   'Preferred over guessing from the ticker suffix — set this whenever known.')
    stock_price            = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text='Latest share price, in stock_price_currency')
    stock_price_currency   = models.CharField(max_length=8, blank=True, default='USD')
    previous_close         = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    day_high               = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    day_low                = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    week52_high            = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    week52_low             = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    day_change_pct         = models.FloatField(null=True, blank=True,
                             help_text='Daily % price movement vs. previous close')
    market_status           = models.CharField(max_length=20, blank=True,
                             help_text='Exchange session state when last fetched, e.g. REGULAR, CLOSED, PRE, POST')
    market_cap_usd         = models.BigIntegerField(null=True, blank=True,
                             help_text='Market capitalisation in USD')
    stock_price_updated_at = models.DateTimeField(null=True, blank=True,
                             help_text='When stock_price / market_cap_usd were last refreshed '
                                       '— this is the last SUCCESSFUL fetch, never cleared just '
                                       'because a later fetch failed, so it always reflects the '
                                       'true age of the displayed price.')

    # ── Pillar scores 0-100 ──
    score_pollution_footprint = models.IntegerField(
        null=True, blank=True,
        help_text='Lower emissions/waste = higher score (0-100). NULL when unassessed — a 0 default '
                  'made an unassessed company the worst possible one.'
    )
    score_reduction_progress  = models.IntegerField(
        null=True, blank=True,
        help_text='Year-on-year pollution reduction trend (0-100). NULL when unassessed — a 0 default '
                  'made an unassessed company the worst possible one.'
    )
    score_investment          = models.IntegerField(
        null=True, blank=True,
        help_text='Environmental investment relative to revenue (0-100). NULL when unassessed — a 0 default '
                  'made an unassessed company the worst possible one.'
    )
    score_transparency        = models.IntegerField(
        null=True, blank=True,
        help_text='Reporting quality, public disclosures (0-100). NULL when unassessed — a 0 default '
                  'made an unassessed company the worst possible one.'
    )
    score_community_impact    = models.IntegerField(
        null=True, blank=True,
        help_text='Measurable benefit to people & ecosystem (0-100). NULL when unassessed — a 0 default '
                  'made an unassessed company the worst possible one.'
    )

    # Computed — updated by save() / recompute_scores management command
    # NULL when there is no score. The `default=Decimal('0.0')` this replaces
    # was the last surviving fabrication in the score chain: a company with
    # perfect evidence but no computed league score published 0.0 -- the
    # harshest possible statement, invented from a default. D4B/D4C covered
    # CompanyProfile and CompanyScoreSnapshot; league.Company was missed.
    ecoiq_score = models.DecimalField(max_digits=5, decimal_places=1,
                                      null=True, blank=True)
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
        from core.unknown import weighted_mean_of_known

        # Re-normalised across the pillars that are known, and None when none
        # of them is. The old expression multiplied a 0 default by its weight
        # and called the result a score.
        raw = weighted_mean_of_known(
            (self.score_pollution_footprint, 0.35),
            (self.score_reduction_progress,  0.25),
            (self.score_investment,          0.20),
            (self.score_transparency,        0.10),
            (self.score_community_impact,    0.10),
        )
        return None if raw is None else Decimal(str(round(raw, 1)))

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        self.ecoiq_score = self.compute_score()
        super().save(*args, **kwargs)

    # ── Derived properties ─────────────────────────────────────────────────────

    @property
    def status_label(self) -> str:
        if self.ecoiq_score is None:
            return 'Not yet scored'
        s = float(self.ecoiq_score)
        if s >= 85: return 'Restorative Leader'
        if s >= 70: return 'Transition Leader'
        if s >= 55: return 'Improving but Polluting'
        if s >= 40: return 'High Impact / Weak Repair'
        return 'Major Polluter'

    @property
    def status_css(self) -> str:
        """CSS class suffix for colour-coding (used in templates)."""
        if self.ecoiq_score is None:
            return 'unscored'
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

    # ── Public markets ─────────────────────────────────────────────────────────

    #: Fallback map of Yahoo Finance ticker suffix → TradingView exchange prefix,
    #: used ONLY when `exchange` hasn't been explicitly set. Covers the exchanges
    #: in ingest_yfinance's TICKER_MAP. Bare tickers (no suffix — US-listed) need
    #: no prefix on TradingView.
    _YAHOO_SUFFIX_TO_TRADINGVIEW = {
        '.L':  'LSE',
        '.SR': 'TADAWUL',
        '.PA': 'EURONEXT',
        '.DE': 'XETR',
        '.MI': 'MIL',
        '.MC': 'BME',
        '.CO': 'OMXCOP',
        '.AS': 'EURONEXT',
    }

    #: How long a fetched price is trusted before the UI should flag it as stale.
    STOCK_STALE_AFTER_HOURS = 48

    @property
    def tradingview_symbol(self) -> str:
        """
        TradingView symbol (EXCHANGE:TICKER). Prefers the explicit `exchange`
        field — set by ingestion whenever the source API provides it — and
        only falls back to guessing an exchange from the Yahoo ticker suffix
        when `exchange` is blank.
        """
        if not self.ticker:
            return ''
        if self.exchange:
            return f'{self.exchange.upper()}:{self.ticker.split(".")[0]}'
        for suffix, exchange in self._YAHOO_SUFFIX_TO_TRADINGVIEW.items():
            if self.ticker.endswith(suffix):
                return f'{exchange}:{self.ticker[:-len(suffix)]}'
        return self.ticker  # bare symbol — TradingView usually resolves these directly

    @property
    def tradingview_url(self) -> str:
        """Secondary external link to this company's live chart on TradingView, or '' if no ticker."""
        if not self.ticker:
            return ''
        return f'https://www.tradingview.com/symbols/{self.tradingview_symbol}/'

    @property
    def stock_profile_url(self):
        """Primary internal EcoIQ stock-profile destination for this company, or '' if not public."""
        if not self.ticker:
            return ''
        from django.urls import reverse
        return reverse('companies:stock', args=[self.slug])

    @property
    def stock_data_is_stale(self) -> bool:
        """True when the last successful price fetch is older than the trust window."""
        if not self.stock_price_updated_at:
            return bool(self.ticker)  # public + ticker but never fetched = treat as stale/unknown
        from django.utils import timezone
        age = timezone.now() - self.stock_price_updated_at
        return age.total_seconds() > self.STOCK_STALE_AFTER_HOURS * 3600

    @property
    def has_market_data(self) -> bool:
        """True only when we have a real, non-zero last-known price to show."""
        return bool(self.ticker) and self.stock_price is not None and self.stock_price > 0

    #: ISO currency code -> display symbol. 'GBp' (lowercase p) is Yahoo
    #: Finance's convention for LSE tickers quoted in pence, not pounds —
    #: handled separately below so a £27.42 headline never silently means
    #: 2,742 pence.
    _CURRENCY_SYMBOLS = {'USD': '$', 'GBP': '£', 'EUR': '€', 'JPY': '¥'}

    def normalized_price_and_currency(self):
        """
        Returns (price: Decimal, currency_code: str) normalized for both
        display AND arithmetic — converts Yahoo's GBp/GBX (pence) quoting to
        GBP. Public because investor_portfolio.calculations needs the raw
        numeric price (not just the formatted string) to compute holding
        market values.
        """
        price = self.stock_price
        currency = (self.stock_price_currency or 'USD')
        if currency in ('GBp', 'GBX'):  # pence sterling
            price = price / 100 if price is not None else None
            currency = 'GBP'
        return price, currency

    @property
    def stock_price_display(self) -> str:
        """Formatted current price, e.g. '£27.42' or '227.50 USD'. '' if unknown."""
        if not self.has_market_data:
            return ''
        price, currency = self.normalized_price_and_currency()
        symbol = self._CURRENCY_SYMBOLS.get(currency.upper())
        return f'{symbol}{price:,.2f}' if symbol else f'{price:,.2f} {currency}'

    @property
    def stock_day_change_display(self) -> str:
        """Formatted daily % move with sign, e.g. '+0.8%' or '-1.2%'. '' if unknown."""
        if self.day_change_pct is None:
            return ''
        return f'{self.day_change_pct:+.1f}%'

    @property
    def stock_day_change_direction(self) -> str:
        """'up' | 'down' | 'flat' | '' (unknown) — for CSS colour coding."""
        if self.day_change_pct is None:
            return ''
        if self.day_change_pct > 0:
            return 'up'
        if self.day_change_pct < 0:
            return 'down'
        return 'flat'


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
