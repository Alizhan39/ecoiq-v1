"""
geo_intelligence/models.py — EcoIQ Geo Intelligence (Phase 1).

Deliberately plain Django models: FloatField latitude/longitude, no
GeoDjango/PostGIS. The platform runs SQLite locally and Postgres in
production with neither extension enabled — adding one is real
infrastructure risk this MVP does not need yet. GeoPandas/Shapely build
GeoDataFrames from these plain fields at query time (see services/spatial.py)
rather than requiring a native geometry column.

Three models, not the five-model wishlist a first draft might reach for:
CompanyLocation and InfrastructureAsset are collapsed into one `GeoAsset`
(`asset_type` distinguishes them) because Phase 1 has no real per-company
geocoding to justify a separate table, and `ClimateObservation` is not
persisted at all — historical weather is fetched live from Meteostat and
cached (see services/weather.py), because Phase 1 has no defined refresh
strategy that would make a stored time-series table meaningful yet.

Every row carries `is_demo` — never let a seeded/demo marker be displayed
as if it were a verified real-world data point.
"""
from django.db import models


class GeoAsset(models.Model):
    """A company office, factory, stewardship site or reference city on the map."""

    ASSET_TYPE_CHOICES = [
        ('city', 'City / Reference Point'),
        ('company_office', 'Company Office'),
        ('factory', 'Factory'),
        ('power_plant', 'Power Plant'),
        ('cold_store', 'Cold Store'),
        ('heating_unit', 'Heating Unit'),
        ('stewardship_site', 'Stewardship Site'),
        ('other', 'Other'),
    ]
    MODERNISATION_PRIORITY_CHOICES = [
        ('not_assessed', 'Not Assessed'),
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    name = models.CharField(max_length=200)
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPE_CHOICES, default='other')
    latitude = models.FloatField()
    longitude = models.FloatField()
    city = models.CharField(max_length=150, blank=True)
    region = models.CharField(max_length=150, blank=True)
    country = models.ForeignKey(
        'countries.CountryProfile', null=True, blank=True, on_delete=models.SET_NULL, related_name='geo_assets',
    )
    sector = models.CharField(max_length=150, blank=True)

    # Never fabricated — null until a real computation (e.g. from Meteostat
    # extreme-heat trend) has actually produced a value for this asset.
    climate_exposure_score = models.FloatField(null=True, blank=True)
    modernisation_priority = models.CharField(
        max_length=20, choices=MODERNISATION_PRIORITY_CHOICES, default='not_assessed',
    )

    # Soft pointer into another app's real data (e.g. a CouncilRun slug or a
    # StewardshipTour slug) — deliberately a CharField, not a cross-app FK, so
    # this module never creates a hard migration dependency on other apps.
    source_reference = models.CharField(max_length=200, blank=True)
    workbench_case_slug = models.CharField(
        max_length=100, blank=True,
        help_text="ai_agent_workbench demo-case slug this asset can be analysed with, if any.",
    )
    workbench_agent_slug = models.CharField(max_length=100, blank=True)

    is_demo = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class GeoRiskZone(models.Model):
    """A climate/infrastructure risk zone, approximated as a centre point + radius."""

    RISK_TYPE_CHOICES = [
        ('extreme_heat', 'Extreme Heat'),
        ('flood', 'Flood'),
        ('drought', 'Drought'),
        ('water_stress', 'Water Stress'),
        ('infrastructure_exposure', 'Infrastructure Exposure'),
    ]
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    name = models.CharField(max_length=200)
    risk_type = models.CharField(max_length=30, choices=RISK_TYPE_CHOICES)
    country = models.ForeignKey(
        'countries.CountryProfile', null=True, blank=True, on_delete=models.SET_NULL, related_name='geo_risk_zones',
    )
    region = models.CharField(max_length=150, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    radius_km = models.FloatField(default=25.0)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    confidence = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=200, blank=True, help_text='e.g. "Meteostat historical analysis"')
    is_demo = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-severity', 'name']

    def __str__(self):
        return f'{self.name} ({self.get_risk_type_display()})'


class InvestmentGeoOpportunity(models.Model):
    """A capital-allocation opportunity anchored to a real map location."""

    OPPORTUNITY_TYPE_CHOICES = [
        ('modernisation', 'Modernisation'),
        ('renewable_energy', 'Renewable Energy'),
        ('grid_upgrade', 'Grid Upgrade'),
        ('cold_chain', 'Cold Chain'),
        ('heating_replacement', 'Heating Replacement'),
        ('other', 'Other'),
    ]
    RISK_LEVEL_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    title = models.CharField(max_length=200)
    country = models.ForeignKey(
        'countries.CountryProfile', null=True, blank=True, on_delete=models.SET_NULL, related_name='geo_opportunities',
    )
    region = models.CharField(max_length=150, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    opportunity_type = models.CharField(max_length=30, choices=OPPORTUNITY_TYPE_CHOICES, default='other')
    estimated_impact = models.CharField(max_length=200, blank=True)
    risk_level = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES, default='medium')
    investment_score = models.FloatField(null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    recommended_action = models.CharField(max_length=200, blank=True)

    source_reference = models.CharField(max_length=200, blank=True)
    workbench_case_slug = models.CharField(max_length=100, blank=True)
    workbench_agent_slug = models.CharField(max_length=100, blank=True)

    is_demo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-investment_score']

    def __str__(self):
        return self.title
