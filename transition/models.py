"""
EcoIQ Industrial Transition Engine — Models.

TransitionRoadmap       AI-generated phase-by-phase transition plan
TransitionPhase         One phase within a roadmap (Quick Wins → Scale)
FinancingOpportunity    Pre-seeded registry of DFIs, climate funds, green bonds
FinancingMatch          Matched opportunity for a specific company
TechnologyRecommendation   Clean-tech recommendations for a company
FacilityRecord          Industrial facility (plant, mine, refinery, …)
GlobalDatasetSource     Registry of bulk import sources (Forbes G2000, etc.)
"""
from decimal import Decimal
from django.db import models


# ── Transition Roadmap ─────────────────────────────────────────────────────────

ROADMAP_TYPES = [
    ('coal_gas',       'Coal-to-Gas Transition'),
    ('methane',        'Methane Reduction Strategy'),
    ('electrification','Industrial Electrification'),
    ('district_heat',  'District Heating Modernisation'),
    ('water',          'Water Restoration Plan'),
    ('waste_heat',     'Waste Heat Recovery'),
    ('flare',          'Flare Reduction Programme'),
    ('renewable',      'Renewable Energy Integration'),
    ('circular',       'Circular Economy & Waste'),
    ('full',           'Full Transition Operating Plan'),
]

ROADMAP_STATUS = [
    ('draft',     'Draft'),
    ('active',    'Active'),
    ('submitted', 'Submitted to Financier'),
    ('funded',    'Funded'),
    ('completed', 'Completed'),
]


class TransitionRoadmap(models.Model):
    """
    AI-generated transition roadmap for a company.
    Contains phased plan, financial projections, and matched financing.
    """
    company      = models.ForeignKey(
        'league.Company', on_delete=models.CASCADE, related_name='roadmaps',
    )
    roadmap_type = models.CharField(max_length=25, choices=ROADMAP_TYPES, default='full')
    status       = models.CharField(max_length=15, choices=ROADMAP_STATUS, default='draft')
    title        = models.CharField(max_length=255)

    # Executive summary
    executive_summary   = models.TextField(blank=True)
    current_state_json  = models.JSONField(default=dict, blank=True,
                          help_text='Identified inefficiencies and baseline metrics')
    target_state_json   = models.JSONField(default=dict, blank=True,
                          help_text='Projected outcomes at roadmap completion')

    # Financial projections
    total_capex_usd          = models.BigIntegerField(null=True, blank=True)
    annual_opex_savings_usd  = models.BigIntegerField(null=True, blank=True)
    payback_years            = models.FloatField(null=True, blank=True)
    irr_pct                  = models.FloatField(null=True, blank=True,
                                help_text='Internal rate of return (%)')
    npv_usd                  = models.BigIntegerField(null=True, blank=True,
                                help_text='Net present value at 10% WACC')

    # Environmental projections
    co2_reduction_tonnes     = models.BigIntegerField(null=True, blank=True,
                                help_text='Annual CO₂ reduction at full implementation')
    co2_reduction_pct        = models.FloatField(null=True, blank=True)
    methane_reduction_pct    = models.FloatField(null=True, blank=True)
    energy_efficiency_gain_pct = models.FloatField(null=True, blank=True)

    # EcoIQ score projection
    projected_ecoiq          = models.DecimalField(max_digits=5, decimal_places=1,
                                null=True, blank=True)
    projected_ecoiq_delta    = models.DecimalField(max_digits=5, decimal_places=1,
                                null=True, blank=True)

    # Financing guidance
    recommended_structures_json = models.JSONField(default=list, blank=True,
                                   help_text='List of recommended financing structures')
    risks_json               = models.JSONField(default=list, blank=True)
    technology_options_json  = models.JSONField(default=list, blank=True)

    # Timeline
    total_duration_months    = models.PositiveIntegerField(null=True, blank=True)
    earliest_start_date      = models.DateField(null=True, blank=True)

    # Confidence & provenance
    confidence               = models.FloatField(default=0.5,
                               help_text='AI confidence 0-1 in projections')
    model_used               = models.CharField(max_length=100, blank=True)
    token_count              = models.PositiveIntegerField(default=0)
    data_quality             = models.CharField(max_length=10, default='medium',
                               choices=[('high','High'),('medium','Medium'),('low','Low')])

    created_at               = models.DateTimeField(auto_now_add=True)
    updated_at               = models.DateTimeField(auto_now=True)

    class Meta:
        ordering        = ['-created_at']
        verbose_name        = 'Transition Roadmap'
        verbose_name_plural = 'Transition Roadmaps'

    def __str__(self):
        return f'{self.company.name} — {self.get_roadmap_type_display()}'

    @property
    def phase_count(self):
        return self.phases.count()

    @property
    def roi_label(self):
        if self.payback_years is None:
            return '—'
        if self.payback_years <= 5:
            return 'Strong'
        if self.payback_years <= 10:
            return 'Viable'
        return 'Long-term'

    @property
    def roi_color(self):
        if self.payback_years is None:
            return '#888'
        if self.payback_years <= 5:
            return '#00e89a'
        if self.payback_years <= 10:
            return '#f4a261'
        return '#e63946'


class TransitionPhase(models.Model):
    """One discrete phase within a TransitionRoadmap."""
    roadmap         = models.ForeignKey(TransitionRoadmap, on_delete=models.CASCADE,
                                        related_name='phases')
    number          = models.PositiveSmallIntegerField()
    name            = models.CharField(max_length=100)
    duration_months = models.PositiveSmallIntegerField(default=6)
    description     = models.TextField(blank=True)
    activities      = models.JSONField(default=list)
    milestones      = models.JSONField(default=list)

    # Financials for this phase
    capex_usd            = models.BigIntegerField(null=True, blank=True)
    opex_change_usd      = models.BigIntegerField(null=True, blank=True,
                           help_text='Negative = savings')
    co2_reduction_tonnes = models.BigIntegerField(null=True, blank=True)

    # Status
    STATUS_CHOICES = [('pending','Pending'),('in_progress','In Progress'),('completed','Completed')]
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')

    class Meta:
        ordering = ['roadmap', 'number']
        verbose_name = 'Transition Phase'

    def __str__(self):
        return f'Phase {self.number}: {self.name}'

    @property
    def start_month(self):
        prev = self.roadmap.phases.filter(number__lt=self.number)
        return sum(p.duration_months for p in prev)

    @property
    def end_month(self):
        return self.start_month + self.duration_months


# ── Financing Intelligence ─────────────────────────────────────────────────────

FINANCING_SOURCE_TYPES = [
    ('dfi',             'Development Finance Institution'),
    ('climate_fund',    'Climate Fund'),
    ('green_bond',      'Green Bond Programme'),
    ('sovereign_fund',  'Sovereign Wealth Fund'),
    ('carbon_market',   'Carbon Market / Credit'),
    ('export_credit',   'Export Credit Agency'),
    ('infra_grant',     'Infrastructure Grant'),
    ('blended',         'Blended Finance Facility'),
    ('private_equity',  'Private Equity / VC'),
    ('commercial',      'Commercial Green Loan'),
]

FINANCING_INSTRUMENTS = [
    ('loan',       'Concessional Loan'),
    ('grant',      'Grant'),
    ('guarantee',  'Guarantee / Risk Cover'),
    ('equity',     'Equity Investment'),
    ('bond',       'Bond'),
    ('credit_line','Credit Line'),
    ('carbon_credit','Carbon Credits'),
]


class FinancingOpportunity(models.Model):
    """
    Registry entry for a financing institution, fund, or programme.
    Pre-seeded with real DFIs, climate funds, ECA programmes.
    Companies are matched against these via the Transition Engine.
    """
    institution_name = models.CharField(max_length=255)
    programme_name   = models.CharField(max_length=255, blank=True)
    acronym          = models.CharField(max_length=20, blank=True)
    source_type      = models.CharField(max_length=25, choices=FINANCING_SOURCE_TYPES)
    instrument       = models.CharField(max_length=20, choices=FINANCING_INSTRUMENTS,
                                        default='loan')

    # Eligibility
    eligible_sectors   = models.JSONField(default=list,
                          help_text='List of sector codes, empty=all')
    eligible_countries = models.JSONField(default=list,
                          help_text='List of country names, empty=all')
    eligible_regions   = models.JSONField(default=list,
                          help_text='e.g. ["Central Asia","South Asia"]')
    focus_areas        = models.JSONField(default=list,
                          help_text='e.g. ["coal_transition","methane","renewable"]')

    # Ticket size
    min_ticket_usd = models.BigIntegerField(null=True, blank=True)
    max_ticket_usd = models.BigIntegerField(null=True, blank=True)

    # Terms
    typical_tenor_years    = models.FloatField(null=True, blank=True)
    typical_interest_rate  = models.FloatField(null=True, blank=True,
                             help_text='Annual % — 0 for grants')
    grace_period_years     = models.FloatField(null=True, blank=True)
    co_financing_required  = models.BooleanField(default=False)
    co_financing_pct       = models.FloatField(null=True, blank=True,
                             help_text='% of project cost required from borrower / other sources')

    # Description
    description          = models.TextField(blank=True)
    eligibility_criteria = models.TextField(blank=True,
                           help_text='Key eligibility requirements in plain text')
    application_process  = models.TextField(blank=True)
    typical_timeline_days= models.PositiveIntegerField(null=True, blank=True,
                           help_text='Typical days from application to first disbursement')

    # Links
    url            = models.URLField(blank=True)
    contact_email  = models.EmailField(blank=True)
    hq_country     = models.CharField(max_length=100, blank=True)

    # Status
    is_active      = models.BooleanField(default=True)
    verified       = models.BooleanField(default=True,
                     help_text='Manually verified by EcoIQ team')
    last_verified  = models.DateField(null=True, blank=True)

    # Accent colour for UI cards
    brand_colour   = models.CharField(max_length=10, default='#333',
                     help_text='Hex colour for institution branding')

    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['source_type', 'institution_name']
        verbose_name        = 'Financing Opportunity'
        verbose_name_plural = 'Financing Opportunities'

    def __str__(self):
        return f'{self.institution_name} — {self.programme_name or self.get_source_type_display()}'

    @property
    def ticket_range_label(self):
        def fmt(v):
            if v >= 1_000_000_000:
                return f'${v/1_000_000_000:.0f}B'
            if v >= 1_000_000:
                return f'${v/1_000_000:.0f}M'
            return f'${v/1_000:.0f}K'
        if self.min_ticket_usd and self.max_ticket_usd:
            return f'{fmt(self.min_ticket_usd)} – {fmt(self.max_ticket_usd)}'
        if self.max_ticket_usd:
            return f'up to {fmt(self.max_ticket_usd)}'
        return 'Varies'


class FinancingMatch(models.Model):
    """
    A specific matched FinancingOpportunity for a company's roadmap.
    Created by the transition engine; shown in the transition dashboard.
    """
    roadmap      = models.ForeignKey(TransitionRoadmap, on_delete=models.CASCADE,
                                     related_name='financing_matches')
    opportunity  = models.ForeignKey(FinancingOpportunity, on_delete=models.CASCADE,
                                     related_name='matches')
    match_score  = models.FloatField(default=0.0, help_text='0-1 match quality')
    match_rationale = models.TextField(blank=True)

    # Suggested deal terms for this specific company
    suggested_amount_usd  = models.BigIntegerField(null=True, blank=True)
    suggested_pct_of_capex= models.FloatField(null=True, blank=True)
    notes                 = models.TextField(blank=True)

    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-match_score']
        verbose_name        = 'Financing Match'
        verbose_name_plural = 'Financing Matches'

    def __str__(self):
        return f'{self.roadmap.company.name} ↔ {self.opportunity.institution_name}'


# ── Technology Recommendations ─────────────────────────────────────────────────

TECH_CATEGORIES = [
    ('cems',          'Continuous Emissions Monitoring (CEMS)'),
    ('filters',       'Industrial Filtration Systems'),
    ('heat_recovery', 'Waste Heat Recovery'),
    ('gas_turbine',   'Gas Turbine / Combined Cycle'),
    ('solar_pv',      'Solar Photovoltaic'),
    ('wind',          'Wind Power'),
    ('methane_capture','Methane Capture & Utilisation'),
    ('ccs',           'Carbon Capture & Storage'),
    ('electrification','Industrial Electrification'),
    ('district_heat', 'District Heating Systems'),
    ('water_treatment','Advanced Water Treatment'),
    ('energy_storage','Battery / Energy Storage'),
    ('process_opt',   'Process Optimisation / AI'),
    ('hydrogen',      'Green Hydrogen'),
]


class TechnologyRecommendation(models.Model):
    """
    A technology recommendation for a company or roadmap.
    Pre-seeded with global clean-tech providers; also AI-generated per roadmap.
    """
    roadmap         = models.ForeignKey(TransitionRoadmap, on_delete=models.CASCADE,
                                        related_name='tech_recs', null=True, blank=True)
    company         = models.ForeignKey('league.Company', on_delete=models.CASCADE,
                                        related_name='tech_recs', null=True, blank=True)
    category        = models.CharField(max_length=25, choices=TECH_CATEGORIES)
    priority        = models.PositiveSmallIntegerField(default=1, help_text='1=highest')

    # Provider info
    provider_name   = models.CharField(max_length=255, blank=True)
    technology_name = models.CharField(max_length=255)
    description     = models.TextField(blank=True)
    provider_origin = models.CharField(max_length=100, blank=True,
                      help_text='Country of provider')

    # Impact metrics
    capex_low_usd      = models.BigIntegerField(null=True, blank=True)
    capex_high_usd     = models.BigIntegerField(null=True, blank=True)
    co2_reduction_pct  = models.FloatField(null=True, blank=True)
    energy_saving_pct  = models.FloatField(null=True, blank=True)
    payback_years      = models.FloatField(null=True, blank=True)
    maturity           = models.CharField(max_length=15, default='proven',
                         choices=[('proven','Proven'),('commercial','Commercial'),
                                  ('emerging','Emerging'),('pilot','Pilot')])

    url           = models.URLField(blank=True)
    applicable_sectors = models.JSONField(default=list)

    class Meta:
        ordering = ['priority', 'category']
        verbose_name        = 'Technology Recommendation'
        verbose_name_plural = 'Technology Recommendations'

    def __str__(self):
        return f'{self.technology_name} ({self.get_category_display()})'

    @property
    def capex_range_label(self):
        def fmt(v):
            if v >= 1_000_000:  return f'${v/1_000_000:.1f}M'
            return f'${v/1_000:.0f}K'
        if self.capex_low_usd and self.capex_high_usd:
            return f'{fmt(self.capex_low_usd)} – {fmt(self.capex_high_usd)}'
        return '—'


# ── Facility Registry ──────────────────────────────────────────────────────────

FACILITY_TYPES = [
    ('power_plant',    'Power Plant'),
    ('refinery',       'Oil Refinery'),
    ('mine',           'Mine'),
    ('smelter',        'Smelter / Foundry'),
    ('chemical_plant', 'Chemical Plant'),
    ('cement',         'Cement Plant'),
    ('steel',          'Steel Mill'),
    ('gas_plant',      'Gas Processing Plant'),
    ('district_heat',  'District Heating Plant'),
    ('water_facility', 'Water Treatment Facility'),
    ('warehouse',      'Warehouse / Logistics'),
    ('other',          'Other'),
]

FUEL_TYPES = [
    ('coal',       'Coal'),
    ('gas',        'Natural Gas'),
    ('oil',        'Oil / Fuel Oil'),
    ('nuclear',    'Nuclear'),
    ('hydro',      'Hydroelectric'),
    ('solar',      'Solar'),
    ('wind',       'Wind'),
    ('biomass',    'Biomass'),
    ('mixed',      'Mixed'),
    ('electric',   'Electric (grid)'),
    ('other',      'Other'),
]


class FacilityRecord(models.Model):
    """
    An industrial facility associated with a company.
    Provides the physical asset layer below the company level.
    """
    company        = models.ForeignKey('league.Company', on_delete=models.CASCADE,
                                       related_name='facilities')
    name           = models.CharField(max_length=255)
    facility_type  = models.CharField(max_length=25, choices=FACILITY_TYPES, default='other')
    primary_fuel   = models.CharField(max_length=15, choices=FUEL_TYPES, default='other')

    location       = models.CharField(max_length=255, blank=True)
    country        = models.CharField(max_length=100, blank=True)
    latitude       = models.FloatField(null=True, blank=True)
    longitude      = models.FloatField(null=True, blank=True)

    # Scale
    capacity_mw    = models.FloatField(null=True, blank=True,
                     help_text='Installed capacity in MW (power plants)')
    employees      = models.PositiveIntegerField(null=True, blank=True)
    commissioned_year = models.PositiveSmallIntegerField(null=True, blank=True)

    # Emissions
    annual_co2_tonnes     = models.BigIntegerField(null=True, blank=True)
    annual_methane_tonnes = models.FloatField(null=True, blank=True)
    emission_intensity    = models.FloatField(null=True, blank=True,
                            help_text='tCO₂ per unit output')

    # Status
    OPERATIONAL_STATUS = [
        ('operating',   'Operating'),
        ('mothballed',  'Mothballed'),
        ('decommission','Decommissioning'),
        ('retired',     'Retired'),
        ('under_const', 'Under Construction'),
    ]
    MODERNISATION_STATUS = [
        ('not_started', 'Not Started'),
        ('assessed',    'Assessed'),
        ('planned',     'Planned'),
        ('in_progress', 'In Progress'),
        ('completed',   'Completed'),
    ]
    operational_status    = models.CharField(max_length=15, choices=OPERATIONAL_STATUS,
                                             default='operating')
    modernisation_status  = models.CharField(max_length=15, choices=MODERNISATION_STATUS,
                                             default='not_started')
    notes       = models.TextField(blank=True)
    source_url  = models.URLField(blank=True)
    verified    = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['company', 'facility_type', 'name']
        verbose_name        = 'Facility'
        verbose_name_plural = 'Facilities'

    def __str__(self):
        return f'{self.company.name} — {self.name} ({self.get_facility_type_display()})'


# ── Global Dataset Source Registry ────────────────────────────────────────────

DATASET_SOURCE_TYPES = [
    ('forbes_g2000',    'Forbes Global 2000'),
    ('fortune500',      'Fortune 500'),
    ('msci_esg',        'MSCI ESG Database'),
    ('sovereign_fund',  'Sovereign Wealth Fund Portfolio'),
    ('stock_exchange',  'Stock Exchange Listing'),
    ('gov_registry',    'Government Industrial Registry'),
    ('esg_db',          'ESG Database'),
    ('sustainability',  'Sustainability Report Database'),
    ('custom',          'Custom Import'),
]


class GlobalDatasetSource(models.Model):
    """
    Registry of external data sources for bulk company ingestion.
    Tracks last fetch, success rate, and discovered companies.
    """
    name        = models.CharField(max_length=255)
    source_type = models.CharField(max_length=25, choices=DATASET_SOURCE_TYPES)
    url         = models.URLField(blank=True)
    description = models.TextField(blank=True)

    # Filter parameters
    focus_countries  = models.JSONField(default=list,
                        help_text='Limit ingestion to these countries')
    focus_sectors    = models.JSONField(default=list,
                        help_text='Limit ingestion to these sector codes')
    min_revenue_usd  = models.BigIntegerField(null=True, blank=True,
                        help_text='Minimum revenue threshold for inclusion')

    # Fetch tracking
    is_active         = models.BooleanField(default=True)
    last_fetched_at   = models.DateTimeField(null=True, blank=True)
    last_fetch_status = models.CharField(max_length=20, default='never',
                        choices=[('never','Never'),('success','Success'),
                                 ('partial','Partial'),('failed','Failed')])
    companies_found   = models.PositiveIntegerField(default=0)
    companies_ingested= models.PositiveIntegerField(default=0)
    error_log         = models.TextField(blank=True)
    notes             = models.TextField(blank=True)

    check_interval_days = models.PositiveIntegerField(default=30)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['source_type', 'name']
        verbose_name        = 'Global Dataset Source'
        verbose_name_plural = 'Global Dataset Sources'

    def __str__(self):
        return f'{self.name} ({self.get_source_type_display()})'
