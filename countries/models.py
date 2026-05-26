"""
EcoIQ Country Intelligence — Models.

CountryProfile     National-level ethical industrial intelligence page.
"""
from django.db import models
from django.utils.text import slugify


# ── Choice sets ────────────────────────────────────────────────────────────────

TRANSITION_READINESS = [
    ('leading',   'Transition Leader'),
    ('advancing', 'Advancing'),
    ('developing','Developing'),
    ('lagging',   'Lagging'),
    ('critical',  'Critical — Urgent Need'),
]

REGION_CHOICES = [
    ('western_europe', 'Western Europe'),
    ('eastern_europe', 'Eastern Europe'),
    ('north_america',  'North America'),
    ('latin_america',  'Latin America'),
    ('middle_east',    'Middle East'),
    ('central_asia',   'Central Asia'),
    ('east_asia',      'East Asia'),
    ('south_asia',     'South Asia'),
    ('southeast_asia', 'Southeast Asia'),
    ('africa',         'Africa'),
    ('oceania',        'Oceania'),
]


# ── CountryProfile ─────────────────────────────────────────────────────────────

class CountryProfile(models.Model):
    """
    National-level EcoIQ intelligence snapshot.
    Aggregates company data + policy environment + transition financing.
    """
    # Identity
    name       = models.CharField(max_length=100, unique=True)
    slug       = models.SlugField(max_length=100, unique=True, blank=True)
    iso_code   = models.CharField(max_length=3, blank=True,
                 help_text='ISO 3166-1 alpha-2 code (e.g. GB, US, DE)')
    flag_emoji = models.CharField(max_length=10, blank=True)
    region     = models.CharField(max_length=20, choices=REGION_CHOICES,
                 default='western_europe')

    # Status
    is_published = models.BooleanField(default=False)
    featured     = models.BooleanField(default=False,
                   help_text='Show on homepage / featured countries section')

    # EcoIQ National Scores (0–100)
    national_ecoiq_index           = models.FloatField(default=0.0,
                                     help_text='Weighted avg EcoIQ score of tracked companies')
    transition_readiness_score     = models.FloatField(default=0.0,
                                     help_text='0-100: Readiness for industrial transition')
    policy_environment_score       = models.FloatField(default=0.0,
                                     help_text='0-100: Quality and ambition of industrial/climate policy')
    investment_climate_score       = models.FloatField(default=0.0,
                                     help_text='0-100: Attractiveness for ethical investment')
    transparency_score             = models.FloatField(default=0.0,
                                     help_text='0-100: National transparency baseline')
    industrial_modernization_score = models.FloatField(default=0.0,
                                     help_text='0-100: How modernized is the industrial base')

    # Transition readiness label
    transition_readiness_label = models.CharField(
        max_length=20, choices=TRANSITION_READINESS, default='developing'
    )

    # Macro context
    gdp_usd                = models.BigIntegerField(null=True, blank=True,
                             help_text='GDP in USD (latest year)')
    industrial_gdp_share   = models.FloatField(null=True, blank=True,
                             help_text='% of GDP from industrial/extractive sectors')
    co2_megatonnes         = models.FloatField(null=True, blank=True,
                             help_text='Annual CO₂ in megatonnes')
    renewable_energy_share = models.FloatField(null=True, blank=True,
                             help_text='% of electricity from renewables')
    fossil_fuel_dependency = models.FloatField(null=True, blank=True,
                             help_text='% of energy from fossil fuels')
    companies_tracked      = models.PositiveIntegerField(default=0)

    # Financing
    estimated_transition_gap_usd = models.BigIntegerField(null=True, blank=True,
                                   help_text='Annual financing gap for transition (USD)')
    green_finance_available_usd  = models.BigIntegerField(null=True, blank=True,
                                   help_text='Available green finance (USD)')

    # AI-generated content
    ai_overview             = models.TextField(blank=True,
                              help_text='2-3 paragraph country intelligence overview')
    ai_transition_narrative = models.TextField(blank=True,
                              help_text='Transition story and opportunities')
    ai_risk_summary         = models.TextField(blank=True,
                              help_text='Transition risks and barriers')
    ai_investment_thesis    = models.TextField(blank=True,
                              help_text='Investment thesis for this country')

    # Structured data (JSON)
    industrial_sectors = models.JSONField(default=list, blank=True,
                         help_text='[{name, ecoiq_score, pollution_level, transition_status}]')
    pollution_hotspots = models.JSONField(default=list, blank=True,
                         help_text='[{name, description, severity}]')
    financing_gaps     = models.JSONField(default=list, blank=True,
                         help_text='[{sector, gap_usd, opportunity}]')
    policy_highlights  = models.JSONField(default=list, blank=True,
                         help_text='[{title, description, year, status}]')
    upcoming_deadlines = models.JSONField(default=list, blank=True,
                         help_text='[{event, date, relevance}]')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-national_ecoiq_index', 'name']
        verbose_name        = 'Country Profile'
        verbose_name_plural = 'Country Profiles'

    def __str__(self):
        return f'{self.flag_emoji} {self.name} — EcoIQ {self.national_ecoiq_index:.1f}'

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    # ── Properties ─────────────────────────────────────────────────────────────

    @property
    def transition_label_color(self):
        return {
            'leading':   '#00e89a',
            'advancing': '#58a6ff',
            'developing':'#f4a261',
            'lagging':   '#e63946',
            'critical':  '#b91c1c',
        }.get(self.transition_readiness_label, '#888')

    @property
    def top_risk(self):
        """Return first severe hotspot, or first hotspot."""
        severe = [h for h in self.pollution_hotspots if h.get('severity') == 'severe']
        return severe[0] if severe else (self.pollution_hotspots[0] if self.pollution_hotspots else None)
