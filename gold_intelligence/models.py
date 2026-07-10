"""
gold_intelligence/models.py — EcoIQ's first flagship vertical: Kazakhstan
Gold Investment Intelligence (Phase 1).

Built entirely on top of existing engines, not a second geo/scoring/finance
stack:
  - map locations (deposits, mines, plants, transport, power, water) reuse
    geo_intelligence.GeoAsset directly (see the extended ASSET_TYPE_CHOICES
    in geo_intelligence/models.py) — no second location model here;
  - climate/water/infrastructure risk reuses geo_intelligence.GeoRiskZone;
  - country-level context (political/governance risk proxy) reuses
    countries.CountryProfile;
  - evidence for any claim reuses evidence_memory.EvidenceMemory via its
    existing source_reference soft-pointer convention.
Only five models are genuinely new here, because nothing in the platform
already represents a capital project's budget lines, timeline, equipment
specs or price/cost scenarios: GoldProject, CapitalBudgetLine,
MineTimelineMilestone, EquipmentSpec, ScenarioAssumption.

Every financial/technical field is nullable and carries no fabricated
default — see services/project_finance.py for how "Data source required"
is reported instead of a fake IRR/NPV/CAPEX number. `is_demo` follows the
exact convention already established by geo_intelligence's own models: a
demo/illustrative row must never be presented as a verified real-world claim.
"""
from django.db import models


class GoldProject(models.Model):
    """
    One investable gold project — the root of every other model here. Not
    a location (see GeoAsset for the map pin); this represents the project
    an investor is evaluating, its declared inputs, and its lifecycle status.
    """
    STATUS_CHOICES = [
        ('exploration', 'Exploration'),
        ('licensing', 'Licensing'),
        ('construction', 'Construction'),
        ('production', 'Production'),
        ('expansion', 'Expansion'),
    ]

    # Capital Guardian Phase 2 (capital_guardian app) — every field/service
    # written for "gold" already treats every number as an optional real
    # input rather than assuming gold-specific units, so a non-gold project
    # (copper, infrastructure, energy, agriculture) can reuse this exact
    # model for its portfolio-level identity rather than a second Project
    # model per commodity. Gold-specific fields below (ore_grade_g_per_tonne,
    # gold_price_assumption_usd_per_oz, etc.) simply stay null for those.
    COMMODITY_CHOICES = [
        ('gold', 'Gold'),
        ('copper', 'Copper'),
        ('infrastructure', 'Infrastructure'),
        ('energy', 'Energy'),
        ('agriculture', 'Agriculture'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    commodity = models.CharField(max_length=20, choices=COMMODITY_CHOICES, default='gold')
    country = models.ForeignKey(
        'countries.CountryProfile', null=True, blank=True, on_delete=models.SET_NULL, related_name='gold_projects',
    )
    region = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='exploration')
    description = models.TextField(blank=True)

    # Resource / technical inputs — every field null until a real, cited
    # source has actually provided a figure. Never defaulted to a plausible
    # number.
    ore_grade_g_per_tonne = models.FloatField(null=True, blank=True, help_text='Grams of gold per tonne of ore.')
    resource_tonnes = models.FloatField(null=True, blank=True, help_text='Total ore resource, tonnes.')
    recovery_rate_pct = models.FloatField(null=True, blank=True, help_text='% of contained gold recovered by processing.')
    mine_life_years = models.PositiveIntegerField(null=True, blank=True)
    expected_annual_production_oz = models.FloatField(null=True, blank=True, help_text='Expected steady-state annual production, troy oz.')

    # Financial inputs
    total_capex_usd = models.FloatField(null=True, blank=True, help_text='Total initial capital expenditure, USD.')
    annual_opex_usd = models.FloatField(null=True, blank=True, help_text='Total annual operating expenditure, USD.')
    cash_cost_usd_per_oz = models.FloatField(null=True, blank=True, help_text='Direct cash operating cost per oz produced.')
    aisc_usd_per_oz = models.FloatField(null=True, blank=True, help_text='All-in sustaining cost per oz produced (includes sustaining capex).')
    gold_price_assumption_usd_per_oz = models.FloatField(null=True, blank=True, help_text='Gold price assumption used for base-case economics.')
    discount_rate_pct = models.FloatField(null=True, blank=True, help_text='Discount rate used for NPV, %.')

    data_sources = models.TextField(blank=True, help_text='Citation string, e.g. "NI 43-101 technical report, 2024".')
    data_last_updated = models.DateField(null=True, blank=True)

    # Capital Guardian (capital_guardian app) — real investor-capital inputs.
    # Distinct from total_capex_usd (the capital-expenditure budget): this is
    # the total equity/debt actually committed by investors, which can
    # legitimately exceed or trail the CAPEX budget (e.g. it also funds
    # working capital, contingency, fees).
    total_committed_capital_usd = models.FloatField(null=True, blank=True, help_text='Total capital committed by investors, USD.')
    insurance_coverage_usd = models.FloatField(null=True, blank=True, help_text='Total insurance policy coverage for the project, USD.')
    insurance_expiry_date = models.DateField(null=True, blank=True)

    is_demo = models.BooleanField(default=True, help_text='Illustrative/demonstration project — never presented as verified real-world market data.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def geo_assets(self):
        """Real GeoAsset rows pointing at this project via the existing
        soft source_reference convention — no hard cross-app FK."""
        from geo_intelligence.models import GeoAsset
        return GeoAsset.objects.filter(source_reference=f'gold_intelligence.GoldProject:{self.slug}')

    @property
    def risk_zones(self):
        """
        GeoRiskZone has no project-level soft reference (only `country`/
        `region`) — climate/water/infrastructure risk is inherently a
        country/region-level signal in this platform already, so zones are
        scoped the same way the rest of geo_intelligence already treats them.
        """
        from geo_intelligence.models import GeoRiskZone
        if self.country_id is None:
            return GeoRiskZone.objects.none()
        return GeoRiskZone.objects.filter(country_id=self.country_id)


class CapitalBudgetLine(models.Model):
    """One line of the project's capital budget — planned vs. committed vs.
    spent are all independently real inputs; nothing here is derived."""
    CATEGORY_CHOICES = [
        ('mining_equipment', 'Mining Equipment'),
        ('processing_plant', 'Processing Plant'),
        ('infrastructure', 'Infrastructure'),
        ('permits_licensing', 'Permits & Licensing'),
        ('contingency', 'Contingency'),
        ('other', 'Other'),
    ]

    project = models.ForeignKey(GoldProject, on_delete=models.CASCADE, related_name='capital_budget_lines')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='other')
    label = models.CharField(max_length=200)
    planned_usd = models.FloatField(null=True, blank=True)
    committed_usd = models.FloatField(null=True, blank=True)
    spent_usd = models.FloatField(null=True, blank=True)
    notes = models.TextField(blank=True)
    data_source = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'label']

    def __str__(self):
        return f'{self.project.name}: {self.label}'

    @property
    def remaining_usd(self):
        """planned - spent — only computable when both real figures exist."""
        if self.planned_usd is None or self.spent_usd is None:
            return None
        return round(self.planned_usd - self.spent_usd, 2)

    @property
    def variance_usd(self):
        """committed - planned — only computable when both real figures exist."""
        if self.planned_usd is None or self.committed_usd is None:
            return None
        return round(self.committed_usd - self.planned_usd, 2)


class MineTimelineMilestone(models.Model):
    """One phase of the project's real lifecycle timeline."""
    PHASE_CHOICES = [
        ('exploration', 'Exploration'),
        ('licensing', 'Licensing'),
        ('construction', 'Construction'),
        ('processing_plant', 'Processing Plant'),
        ('production', 'Production'),
        ('expansion', 'Expansion'),
    ]
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('complete', 'Complete'),
        ('delayed', 'Delayed'),
    ]
    VERIFICATION_STATUS_CHOICES = [
        ('not_required', 'Not Required'),
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('failed', 'Failed'),
    ]
    DELAY_RISK_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    project = models.ForeignKey(GoldProject, on_delete=models.CASCADE, related_name='timeline_milestones')
    phase = models.CharField(max_length=20, choices=PHASE_CHOICES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='not_started')
    planned_start = models.DateField(null=True, blank=True)
    planned_end = models.DateField(null=True, blank=True)
    actual_start = models.DateField(null=True, blank=True)
    actual_end = models.DateField(null=True, blank=True)
    # Only set when a real, reported completion figure exists — 'complete'/
    # 'not_started' status alone already implies 100%/0% (see completion_pct
    # property below); this field is for a real reported in-progress %.
    completion_pct_override = models.FloatField(null=True, blank=True)

    # Capital Guardian (capital_guardian app) — milestone-based capital release.
    capital_required_usd = models.FloatField(null=True, blank=True, help_text='Capital required to complete this milestone, USD.')
    capital_released_usd = models.FloatField(null=True, blank=True, help_text='Capital actually released against this milestone, USD.')
    verification_required = models.BooleanField(default=False)
    verification_status = models.CharField(max_length=15, choices=VERIFICATION_STATUS_CHOICES, default='not_required')
    delay_risk = models.CharField(max_length=10, choices=DELAY_RISK_CHOICES, blank=True)
    responsible_party = models.CharField(max_length=200, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['planned_start', 'phase']

    def __str__(self):
        return f'{self.project.name}: {self.get_phase_display()}'

    @property
    def completion_pct(self):
        """Honest completion: a real reported override if one exists,
        otherwise only the unambiguous 0%/100% implied by status — never an
        invented in-between percentage."""
        if self.completion_pct_override is not None:
            return self.completion_pct_override
        if self.status == 'complete':
            return 100.0
        if self.status == 'not_started':
            return 0.0
        return None


# Capital Guardian (capital_guardian app) — one shared lifecycle-status
# vocabulary reused across every equipment lifecycle stage field below,
# rather than a bespoke choices list per field.
LIFECYCLE_STATUS_CHOICES = [
    ('not_started', 'Not Started'),
    ('in_progress', 'In Progress'),
    ('complete', 'Complete'),
    ('passed', 'Passed'),
    ('failed', 'Failed'),
    ('not_applicable', 'Not Applicable'),
]


class EquipmentSpec(models.Model):
    """One piece of major process equipment planned or installed for the
    project. Every technical/cost figure is a real declared estimate or
    actual spec — never a fabricated default."""
    EQUIPMENT_TYPE_CHOICES = [
        ('crusher', 'Crusher'),
        ('mill', 'Mill'),
        ('cil', 'CIL (Carbon-in-Leach)'),
        ('heap_leach', 'Heap Leach'),
        ('gravity', 'Gravity Concentration'),
        ('flotation', 'Flotation'),
        ('autoclave', 'Autoclave'),
        ('thickener', 'Thickener'),
        ('filter_press', 'Filter Press'),
        ('tailings', 'Tailings Storage Facility'),
        ('power_plant', 'Power Plant'),
        ('conveyor', 'Conveyor'),
        ('electrowinning', 'Electrowinning Cells'),
        ('smelting_furnace', 'Smelting Furnace'),
        ('haul_truck', 'Haul Truck'),
        ('excavator', 'Hydraulic Excavator'),
    ]

    project = models.ForeignKey(GoldProject, on_delete=models.CASCADE, related_name='equipment_specs')
    equipment_type = models.CharField(max_length=20, choices=EQUIPMENT_TYPE_CHOICES)
    label = models.CharField(max_length=200, blank=True)
    capex_usd = models.FloatField(null=True, blank=True)
    lead_time_months = models.PositiveIntegerField(null=True, blank=True)
    power_usage_kw = models.FloatField(null=True, blank=True)
    water_usage_m3_per_hour = models.FloatField(null=True, blank=True)
    recovery_pct = models.FloatField(null=True, blank=True, help_text='Recovery contribution of this equipment stage, %, if known.')
    notes = models.TextField(blank=True)
    data_source = models.CharField(max_length=200, blank=True)

    # Capital Guardian (capital_guardian app) — supplier/lifecycle tracking.
    # `manufacturer`/`supplier` are illustrative labels only in demo data —
    # never a claim that a named real manufacturer is actually involved.
    manufacturer = models.CharField(max_length=150, blank=True)
    supplier = models.CharField(max_length=150, blank=True)
    deposit_paid_usd = models.FloatField(null=True, blank=True)

    manufacturing_status = models.CharField(max_length=20, choices=LIFECYCLE_STATUS_CHOICES, default='not_started')
    fat_status = models.CharField(max_length=20, choices=LIFECYCLE_STATUS_CHOICES, default='not_started', help_text='Factory Acceptance Test status.')
    shipping_status = models.CharField(max_length=20, choices=LIFECYCLE_STATUS_CHOICES, default='not_started')
    delivery_status = models.CharField(max_length=20, choices=LIFECYCLE_STATUS_CHOICES, default='not_started')
    installation_status = models.CharField(max_length=20, choices=LIFECYCLE_STATUS_CHOICES, default='not_started')
    commissioning_status = models.CharField(max_length=20, choices=LIFECYCLE_STATUS_CHOICES, default='not_started')
    warranty_status = models.CharField(max_length=20, choices=LIFECYCLE_STATUS_CHOICES, default='not_applicable')
    performance_guarantee_status = models.CharField(max_length=20, choices=LIFECYCLE_STATUS_CHOICES, default='not_applicable')
    insurance_status = models.CharField(max_length=20, choices=LIFECYCLE_STATUS_CHOICES, default='not_started')
    maintenance_status = models.CharField(max_length=20, choices=LIFECYCLE_STATUS_CHOICES, default='not_applicable')
    inspection_status = models.CharField(max_length=20, choices=LIFECYCLE_STATUS_CHOICES, default='not_started')

    # Capital Guardian Phase 3 — real inputs a deterministic remaining-
    # useful-life / "recommended service window" estimate can be computed
    # from (see capital_guardian/services/equipment_health.py). Never an ML
    # prediction — both fields are null until a real commissioning date and
    # a real declared expected lifespan exist.
    country = models.CharField(max_length=100, blank=True, help_text='Illustrative label in demo data — not a claim of real involvement.')
    commissioned_date = models.DateField(null=True, blank=True)
    expected_lifespan_years = models.FloatField(null=True, blank=True)
    spare_parts_available = models.BooleanField(default=False)
    maintenance_contract_active = models.BooleanField(default=False)

    class Meta:
        ordering = ['equipment_type']

    def __str__(self):
        return self.label or self.get_equipment_type_display()

    @property
    def remaining_balance_usd(self):
        if self.capex_usd is None or self.deposit_paid_usd is None:
            return None
        return round(self.capex_usd - self.deposit_paid_usd, 2)


class ScenarioAssumption(models.Model):
    """One named scenario to re-run project economics under (e.g. 'Gold
    price -20%'). Any field left null means that input is NOT overridden
    for this scenario — the base-case value is used instead, never a
    fabricated substitute."""

    project = models.ForeignKey(GoldProject, on_delete=models.CASCADE, related_name='scenarios')
    name = models.CharField(max_length=200)
    gold_price_usd_per_oz = models.FloatField(null=True, blank=True)
    capex_multiplier = models.FloatField(null=True, blank=True, help_text='e.g. 1.15 for a 15% CAPEX overrun. Null = base case CAPEX.')
    opex_multiplier = models.FloatField(null=True, blank=True, help_text='e.g. 1.10 for a 10% OPEX increase. Null = base case OPEX.')
    recovery_rate_pct_override = models.FloatField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.project.name}: {self.name}'
