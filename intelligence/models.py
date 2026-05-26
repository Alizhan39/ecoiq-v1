"""
EcoIQ Environmental Intelligence OS — Models.

CountryIntelligence  — aggregated national metrics (recomputed nightly)
IntelligenceAlert    — anomaly detection: score drops, greenwashing, transparency loss
MonitorWatch         — autonomous website monitoring targets
StrategicSignal      — sector-specific signals: methane, coal, water, flares
ExecutiveBriefing    — AI-generated narrative briefings per company or country
"""
from decimal import Decimal
from django.db import models
from django.utils import timezone


# ── Country Intelligence ───────────────────────────────────────────────────────

class CountryIntelligence(models.Model):
    """
    Aggregated national environmental intelligence.
    Recomputed by the `compute_country_intelligence` management command.
    """
    country_code = models.CharField(max_length=3, unique=True,
                                    help_text='Lowercase ISO country name used as slug')
    country_name = models.CharField(max_length=100)
    region       = models.CharField(max_length=100, blank=True,
                                    help_text='e.g. Central Asia, Eastern Europe')
    flag_emoji   = models.CharField(max_length=10, blank=True)

    # Aggregate EcoIQ
    national_ecoiq_score   = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0.0'))
    company_count          = models.PositiveIntegerField(default=0)
    verified_company_count = models.PositiveIntegerField(default=0)

    # Pillar aggregates (weighted averages)
    avg_pollution    = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0.0'))
    avg_reduction    = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0.0'))
    avg_investment   = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0.0'))
    avg_transparency = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0.0'))
    avg_community    = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0.0'))

    # Environmental totals
    total_co2_reduction_tonnes = models.BigIntegerField(default=0)
    total_investment_usd       = models.BigIntegerField(default=0)
    total_households_helped    = models.BigIntegerField(default=0)
    total_projects             = models.PositiveIntegerField(default=0)

    # Sector breakdown (JSON: {sector_code: count})
    sector_distribution = models.JSONField(default=dict, blank=True)
    top_sector          = models.CharField(max_length=30, blank=True)

    # Transparency metrics
    reporting_pct    = models.FloatField(default=0.0,
                                          help_text='% of companies with public reports')
    transparency_rank = models.PositiveIntegerField(null=True, blank=True)

    # Trend (vs 6 months ago snapshot)
    score_6m_ago       = models.DecimalField(max_digits=5, decimal_places=1,
                                              null=True, blank=True)
    trend_direction    = models.CharField(
        max_length=12, default='stable',
        choices=[('improving','Improving'),('stable','Stable'),('declining','Declining')],
    )
    trend_delta        = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0.0'))

    # AI briefing
    ai_briefing = models.TextField(blank=True,
                                   help_text='AI-generated executive briefing (latest)')
    briefing_updated_at = models.DateTimeField(null=True, blank=True)

    last_computed = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-national_ecoiq_score', 'country_name']
        verbose_name        = 'Country Intelligence'
        verbose_name_plural = 'Country Intelligence'

    def __str__(self):
        return f'{self.country_name} — EcoIQ {self.national_ecoiq_score}'

    @property
    def trend_symbol(self):
        if self.trend_direction == 'improving':  return '▲'
        if self.trend_direction == 'declining':  return '▼'
        return '—'

    @property
    def trend_color(self):
        if self.trend_direction == 'improving':  return '#00e89a'
        if self.trend_direction == 'declining':  return '#e63946'
        return '#888'


# ── Intelligence Alerts ────────────────────────────────────────────────────────

class IntelligenceAlert(models.Model):
    """
    System-generated alert when a company's metrics change significantly.
    Displayed in the real-time alert feed on the intelligence hub.
    """
    ALERT_SCORE_DROP    = 'score_drop'
    ALERT_SCORE_SURGE   = 'score_surge'
    ALERT_GREENWASHING  = 'greenwashing'
    ALERT_TRANS_LOSS    = 'transparency_loss'
    ALERT_TRANS_GAIN    = 'transparency_gain'
    ALERT_NEW_REPORT    = 'new_report'
    ALERT_METHANE       = 'methane_spike'
    ALERT_VIOLATION     = 'violation'
    ALERT_PROJECT       = 'new_project'
    ALERT_RANK_CHANGE   = 'rank_change'
    ALERT_MONITOR       = 'monitor_change'

    ALERT_TYPE_CHOICES = [
        (ALERT_SCORE_DROP,   'Score Drop'),
        (ALERT_SCORE_SURGE,  'Score Surge'),
        (ALERT_GREENWASHING, 'Greenwashing Detected'),
        (ALERT_TRANS_LOSS,   'Transparency Loss'),
        (ALERT_TRANS_GAIN,   'Transparency Gain'),
        (ALERT_NEW_REPORT,   'New Report Available'),
        (ALERT_METHANE,      'Methane Spike'),
        (ALERT_VIOLATION,    'Regulatory Violation'),
        (ALERT_PROJECT,      'New Project Announced'),
        (ALERT_RANK_CHANGE,  'Rank Change'),
        (ALERT_MONITOR,      'Website Change Detected'),
    ]

    SEV_CRITICAL = 'critical'
    SEV_HIGH     = 'high'
    SEV_MEDIUM   = 'medium'
    SEV_LOW      = 'low'
    SEV_INFO     = 'info'

    SEVERITY_CHOICES = [
        (SEV_CRITICAL, 'Critical'),
        (SEV_HIGH,     'High'),
        (SEV_MEDIUM,   'Medium'),
        (SEV_LOW,      'Low'),
        (SEV_INFO,     'Info'),
    ]

    alert_type   = models.CharField(max_length=25, choices=ALERT_TYPE_CHOICES)
    severity     = models.CharField(max_length=10, choices=SEVERITY_CHOICES,
                                    default=SEV_MEDIUM)
    company      = models.ForeignKey(
        'league.Company', on_delete=models.CASCADE, related_name='alerts',
        null=True, blank=True,
    )
    country_intel = models.ForeignKey(
        CountryIntelligence, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='alerts',
    )
    title        = models.CharField(max_length=255)
    body         = models.TextField(blank=True)
    metric_before= models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    metric_after = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    metric_delta = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    source_url   = models.URLField(blank=True)
    is_read      = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name        = 'Intelligence Alert'
        verbose_name_plural = 'Intelligence Alerts'

    def __str__(self):
        return f'[{self.severity.upper()}] {self.title}'

    @property
    def severity_color(self):
        return {
            'critical': '#e63946',
            'high':     '#f4a261',
            'medium':   '#f59e0b',
            'low':      '#58a6ff',
            'info':     '#00e89a',
        }.get(self.severity, '#888')

    @property
    def severity_icon(self):
        return {
            'critical': '🔴',
            'high':     '🟠',
            'medium':   '🟡',
            'low':      '🔵',
            'info':     '🟢',
        }.get(self.severity, '⚪')

    @property
    def alert_icon(self):
        return {
            'score_drop':        '📉',
            'score_surge':       '📈',
            'greenwashing':      '⚠️',
            'transparency_loss': '🔒',
            'transparency_gain': '🔓',
            'new_report':        '📄',
            'methane_spike':     '☁️',
            'violation':         '🚨',
            'new_project':       '🏗️',
            'rank_change':       '🏆',
            'monitor_change':    '🔍',
        }.get(self.alert_type, '📊')


# ── Autonomous Monitoring ──────────────────────────────────────────────────────

class MonitorWatch(models.Model):
    """
    A URL to periodically check for new ESG content.
    The `monitor_companies` management command fetches these and compares hashes.
    """
    CHECK_WEBSITE  = 'website'
    CHECK_PDF_DIR  = 'pdf_directory'
    CHECK_NEWS     = 'news_feed'
    CHECK_REGULATOR= 'regulator'

    CHECK_TYPE_CHOICES = [
        (CHECK_WEBSITE,   'Company Website'),
        (CHECK_PDF_DIR,   'PDF/Report Directory'),
        (CHECK_NEWS,      'News Feed'),
        (CHECK_REGULATOR, 'Regulator / Gov Portal'),
    ]

    company    = models.ForeignKey(
        'league.Company', on_delete=models.CASCADE, related_name='monitors',
    )
    url        = models.URLField(max_length=2000)
    check_type = models.CharField(max_length=20, choices=CHECK_TYPE_CHOICES,
                                  default=CHECK_WEBSITE)
    label      = models.CharField(max_length=255, blank=True,
                                  help_text='Human-readable label for this watch target')
    is_active  = models.BooleanField(default=True)

    # Last check results
    last_checked_at     = models.DateTimeField(null=True, blank=True)
    last_content_hash   = models.CharField(max_length=64, blank=True,
                                           help_text='SHA-256 of fetched content')
    last_content_size   = models.PositiveIntegerField(default=0)
    change_detected     = models.BooleanField(default=False)
    change_detected_at  = models.DateTimeField(null=True, blank=True)
    ingestion_triggered = models.BooleanField(default=False)

    # Check frequency
    check_interval_hours = models.PositiveIntegerField(default=24)
    consecutive_errors   = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['company', 'url']
        verbose_name        = 'Monitor Watch'
        verbose_name_plural = 'Monitor Watches'

    def __str__(self):
        return f'{self.company.name} — {self.label or self.url[:60]}'

    @property
    def is_due(self):
        """Return True if this watch is past its check interval."""
        if not self.last_checked_at:
            return True
        from datetime import timedelta
        return (timezone.now() - self.last_checked_at) >= timedelta(hours=self.check_interval_hours)


# ── Strategic Intelligence Signals ────────────────────────────────────────────

class StrategicSignal(models.Model):
    """
    A tagged environmental intelligence signal for a specific strategic module.
    Populated by the AI ingestion pipeline and the monitor command.
    """
    MODULE_METHANE   = 'methane'
    MODULE_COAL      = 'coal_transition'
    MODULE_WATER     = 'water_restoration'
    MODULE_FLARE     = 'flare_reduction'
    MODULE_MODERNISE = 'modernisation'
    MODULE_INVEST    = 'ethical_investment'

    MODULE_CHOICES = [
        (MODULE_METHANE,   'Methane Leakage'),
        (MODULE_COAL,      'Coal-to-Gas Transition'),
        (MODULE_WATER,     'Water Restoration'),
        (MODULE_FLARE,     'Flare Reduction'),
        (MODULE_MODERNISE, 'Industrial Modernisation'),
        (MODULE_INVEST,    'Ethical Investment'),
    ]

    POLARITY_RISK     = 'risk'
    POLARITY_POSITIVE = 'positive'
    POLARITY_NEUTRAL  = 'neutral'

    module      = models.CharField(max_length=25, choices=MODULE_CHOICES)
    company     = models.ForeignKey(
        'league.Company', on_delete=models.CASCADE, related_name='signals',
    )
    polarity    = models.CharField(max_length=10,
                                   choices=[('risk','Risk'),('positive','Positive'),('neutral','Neutral')],
                                   default='neutral')
    title       = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    metric_value= models.FloatField(null=True, blank=True)
    metric_unit = models.CharField(max_length=50, blank=True)
    source_url  = models.URLField(blank=True)
    year        = models.PositiveSmallIntegerField(null=True, blank=True)
    confidence  = models.FloatField(default=0.5, help_text='0-1 AI confidence')
    detected_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-detected_at', '-confidence']
        verbose_name        = 'Strategic Signal'
        verbose_name_plural = 'Strategic Signals'

    def __str__(self):
        return f'[{self.module}] {self.company.name}: {self.title}'

    @property
    def polarity_color(self):
        return {'risk': '#e63946', 'positive': '#00e89a', 'neutral': '#888'}.get(self.polarity, '#888')


# ── Executive Briefings ────────────────────────────────────────────────────────

class ExecutiveBriefing(models.Model):
    """
    AI-generated executive intelligence briefing.
    One per company (or country) per week — never more than necessary.
    """
    SCOPE_COMPANY = 'company'
    SCOPE_COUNTRY = 'country'
    SCOPE_SECTOR  = 'sector'
    SCOPE_GLOBAL  = 'global'

    scope        = models.CharField(max_length=10,
                                    choices=[('company','Company'),('country','Country'),
                                             ('sector','Sector'),('global','Global')],
                                    default='company')
    company      = models.ForeignKey(
        'league.Company', on_delete=models.CASCADE, related_name='briefings',
        null=True, blank=True,
    )
    country_intel= models.ForeignKey(
        CountryIntelligence, on_delete=models.CASCADE, related_name='briefings',
        null=True, blank=True,
    )
    sector_code  = models.CharField(max_length=30, blank=True)
    title        = models.CharField(max_length=255)
    headline     = models.CharField(max_length=500, blank=True,
                                    help_text='One-line AI verdict')
    body         = models.TextField(help_text='Full AI-generated briefing (Markdown)')
    key_risks    = models.JSONField(default=list, blank=True)
    key_drivers  = models.JSONField(default=list, blank=True)
    action_items = models.JSONField(default=list, blank=True)
    model_used   = models.CharField(max_length=100, blank=True)
    token_count  = models.PositiveIntegerField(default=0)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name        = 'Executive Briefing'
        verbose_name_plural = 'Executive Briefings'

    def __str__(self):
        label = self.company.name if self.company else self.sector_code or 'Global'
        return f'{label} — {self.created_at:%Y-%m-%d}'
