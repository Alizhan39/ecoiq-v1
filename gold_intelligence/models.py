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

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
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

    project = models.ForeignKey(GoldProject, on_delete=models.CASCADE, related_name='timeline_milestones')
    phase = models.CharField(max_length=20, choices=PHASE_CHOICES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='not_started')
    planned_start = models.DateField(null=True, blank=True)
    planned_end = models.DateField(null=True, blank=True)
    actual_start = models.DateField(null=True, blank=True)
    actual_end = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['planned_start', 'phase']

    def __str__(self):
        return f'{self.project.name}: {self.get_phase_display()}'


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

    class Meta:
        ordering = ['equipment_type']

    def __str__(self):
        return self.label or self.get_equipment_type_display()


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
