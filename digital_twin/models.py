"""
digital_twin/models.py — the Industrial Digital Twin & Modernisation Engine.

This app owns exactly the models that do not exist anywhere else in EcoIQ
(see docs/digital_twin_existing_system_audit.md and
docs/adr/ADR-digital-twin-foundation.md). It deliberately does NOT redefine:

- OperationalLoss / InterventionOption / InterventionScenario /
  CapitalAllocationDecision — these already exist in
  `waste_to_value_capital_allocation_engine` and are reused by hard FK
  (new app -> existing app, the same direction
  `financial_intelligence_cloud.PortfolioEntity.source_operational_loss`
  already uses) once a candidate has been human-approved.
- CouncilRun / AgentTask / CouncilDecision — these already exist in
  `ai_agent_council` and are reused unmodified.
- Evidence — `evidence_memory.EvidenceMemory` is the canonical evidence
  store. Every `evidence_references` field on models below is a list of
  soft `"digital_twin.<Model>:<pk>"`-style source_reference strings,
  matching the repo-wide convention (no GenericForeignKey exists anywhere
  in this codebase, confirmed by the audit).

Two pieces of shared infrastructure are new to the repo (called out
explicitly, not presented as "the existing pattern"):
- `TimeStampedModel` — no abstract base model existed anywhere before this.
- `AssetType` — the first extensible-choice-registry actually wired as a
  real FK constraint (`league.SectorRef`/`CountryRef` exist but are never
  used as FK targets anywhere in the repo).
"""
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

from waste_to_value_capital_allocation_engine.models import LOSS_TYPE_CHOICES


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ── Reference registries ─────────────────────────────────────────────────────

class UnitCategory(TimeStampedModel):
    """A dimension of measurement (energy, mass, volume, ...). Quantities of
    different categories are never compared/added — see services/units.py."""
    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=80)

    class Meta:
        ordering = ['name']
        verbose_name = 'Unit Category'
        verbose_name_plural = 'Unit Categories'

    def __str__(self):
        return self.name


class Unit(TimeStampedModel):
    """A concrete unit within a UnitCategory. `to_base_multiplier` converts a
    quantity in this unit to the category's base unit (multiply to convert
    up; divide to convert back) — see services/units.py::convert()."""
    category = models.ForeignKey(UnitCategory, on_delete=models.PROTECT, related_name='units')
    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=80)
    symbol = models.CharField(max_length=20, blank=True)
    to_base_multiplier = models.FloatField(default=1.0)
    is_base_unit = models.BooleanField(default=False)

    class Meta:
        ordering = ['category', 'name']
        verbose_name = 'Unit'
        verbose_name_plural = 'Units'
        constraints = [
            models.UniqueConstraint(
                fields=['category'], condition=Q(is_base_unit=True), name='uniq_base_unit_per_category',
            ),
        ]

    def __str__(self):
        return f'{self.name} ({self.symbol or self.code})'


ASSET_TYPE_SEED_CODES = [
    ('manufacturing_facility', 'Manufacturing Facility'),
    ('mine', 'Mine'),
    ('mineral_deposit_exploration', 'Mineral Deposit / Exploration Asset'),
    ('processing_plant', 'Processing Plant'),
    ('energy_asset', 'Energy Asset'),
    ('infrastructure_project', 'Infrastructure Project'),
    ('generic_industrial_asset', 'Generic Industrial Asset'),
    ('other', 'Other'),
]


class AssetType(TimeStampedModel):
    """Extensible asset-category registry — adding a new asset type is a data
    change (a new row), never a code change. Seeded with the 7 categories
    required at launch plus a generic 'other' escape hatch."""
    code = models.SlugField(max_length=60, unique=True)
    display_name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_name']
        verbose_name = 'Asset Type'
        verbose_name_plural = 'Asset Types'

    def __str__(self):
        return self.display_name


# ── Core domain: asset and twin ──────────────────────────────────────────────

LIFECYCLE_STAGE_CHOICES = [
    ('concept', 'Concept'),
    ('development', 'Development'),
    ('construction', 'Construction'),
    ('operational', 'Operational'),
    ('expansion', 'Expansion'),
    ('decommissioning', 'Decommissioning'),
    ('closed', 'Closed'),
]

ASSET_OPERATIONAL_STATUS_CHOICES = [
    ('active', 'Active'),
    ('idle', 'Idle'),
    ('under_maintenance', 'Under Maintenance'),
    ('curtailed', 'Curtailed'),
    ('decommissioned', 'Decommissioned'),
    ('unknown', 'Unknown'),
]


class IndustrialAsset(TimeStampedModel):
    """The real-world industrial asset a Digital Twin represents."""
    company = models.ForeignKey(
        'league.Company', on_delete=models.SET_NULL, null=True, blank=True, related_name='industrial_assets',
        help_text='The real, rated EcoIQ company that owns/operates this asset, if one exists yet.',
    )
    name = models.CharField(max_length=255)
    asset_type = models.ForeignKey(AssetType, on_delete=models.PROTECT, related_name='assets')
    country = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=150, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    industry = models.CharField(max_length=150, blank=True)
    lifecycle_stage = models.CharField(max_length=20, choices=LIFECYCLE_STAGE_CHOICES, default='operational')
    operational_status = models.CharField(max_length=20, choices=ASSET_OPERATIONAL_STATUS_CHOICES, default='unknown')
    description = models.TextField(blank=True)
    owner = models.CharField(max_length=255, blank=True, help_text='Free-text operator/owner name when not a real Company row.')
    source_project_reference = models.CharField(
        max_length=200, blank=True, db_index=True,
        help_text='Soft pointer to a related finance/investment project record, e.g. "gold_intelligence.GoldProject:<slug>". Not a FK, to avoid a migration dependency on other verticals.',
    )
    source_system = models.CharField(
        max_length=100, blank=True, default='manual',
        help_text='System of record this asset was created/synced from, e.g. "manual", "geo_intelligence", "gold_intelligence".',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )
    is_demo = models.BooleanField(default=False)

    class Meta:
        ordering = ['name']
        verbose_name = 'Industrial Asset'
        verbose_name_plural = 'Industrial Assets'

    def __str__(self):
        return self.name

    @property
    def evidence_documents(self):
        from evidence_memory.models import EvidenceMemory
        if not self.pk:
            return EvidenceMemory.objects.none()
        return EvidenceMemory.objects.filter(source_reference=f'digital_twin.IndustrialAsset:{self.pk}')


TWIN_STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('ingesting', 'Ingesting'),
    ('incomplete', 'Incomplete'),
    ('baseline_ready', 'Baseline Ready'),
    ('active', 'Active'),
    ('stale', 'Stale'),
    ('under_review', 'Under Review'),
    ('archived', 'Archived'),
]


class DigitalTwin(TimeStampedModel):
    """One versioned baseline representation of an IndustrialAsset."""
    asset = models.ForeignKey(IndustrialAsset, on_delete=models.CASCADE, related_name='twins')
    name = models.CharField(max_length=255)
    version = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=TWIN_STATUS_CHOICES, default='draft')
    baseline_date = models.DateField(null=True, blank=True)
    last_observed_at = models.DateTimeField(null=True, blank=True)

    # Never fabricated — null until the baseline engine has actually run.
    confidence_score = models.FloatField(null=True, blank=True)
    completeness_score = models.FloatField(null=True, blank=True)
    data_freshness_score = models.FloatField(null=True, blank=True)

    model_version = models.CharField(
        max_length=20, default='1.0.0',
        help_text='Version of the deterministic baseline-engine formulas used to compute the scores above.',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['asset', '-version']
        verbose_name = 'Digital Twin'
        verbose_name_plural = 'Digital Twins'
        constraints = [
            models.UniqueConstraint(fields=['asset', 'version'], name='uniq_twin_asset_version'),
            # Only one active, human-approved baseline per asset at a time.
            models.UniqueConstraint(
                fields=['asset'], condition=Q(status='active', approved_at__isnull=False),
                name='uniq_active_approved_twin_per_asset',
            ),
        ]

    def __str__(self):
        return f'{self.name} v{self.version} ({self.asset.name})'

    @property
    def evidence_documents(self):
        from evidence_memory.models import EvidenceMemory
        if not self.pk:
            return EvidenceMemory.objects.none()
        return EvidenceMemory.objects.filter(source_reference=f'digital_twin.DigitalTwin:{self.pk}')


# ── Twin components ───────────────────────────────────────────────────────────

COMPONENT_TYPE_CHOICES = [
    ('production_line', 'Production Line'),
    ('machine', 'Machine'),
    ('crusher', 'Crusher'),
    ('boiler', 'Boiler'),
    ('kiln', 'Kiln'),
    ('haulage_fleet', 'Haulage Fleet'),
    ('processing_circuit', 'Processing Circuit'),
    ('laboratory', 'Laboratory'),
    ('water_system', 'Water System'),
    ('energy_system', 'Energy System'),
    ('warehouse', 'Warehouse'),
    ('tailings_facility', 'Tailings Facility'),
    ('research_programme', 'Research Programme'),
    ('infrastructure_segment', 'Infrastructure Segment'),
    ('other', 'Other'),
]

CONDITION_CHOICES = [
    ('excellent', 'Excellent'),
    ('good', 'Good'),
    ('fair', 'Fair'),
    ('poor', 'Poor'),
    ('unknown', 'Unknown'),
]

CRITICALITY_CHOICES = [
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
    ('critical', 'Critical'),
]

COMPONENT_OPERATIONAL_STATUS_CHOICES = [
    ('operational', 'Operational'),
    ('non_operational', 'Non-Operational'),
    ('maintenance', 'Under Maintenance'),
    ('standby', 'Standby'),
    ('retired', 'Retired'),
    ('unknown', 'Unknown'),
]


class TwinComponent(TimeStampedModel):
    """A physical or logical part of the asset."""
    twin = models.ForeignKey(DigitalTwin, on_delete=models.CASCADE, related_name='components')
    parent_component = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='child_components',
    )
    component_type = models.CharField(max_length=30, choices=COMPONENT_TYPE_CHOICES)
    name = models.CharField(max_length=255)
    manufacturer = models.CharField(max_length=150, blank=True)
    model_reference = models.CharField(max_length=150, blank=True)
    commissioning_date = models.DateField(null=True, blank=True)
    expected_useful_life_years = models.FloatField(null=True, blank=True)
    condition = models.CharField(max_length=15, choices=CONDITION_CHOICES, default='unknown')
    criticality = models.CharField(max_length=10, choices=CRITICALITY_CHOICES, default='medium')
    operational_status = models.CharField(max_length=20, choices=COMPONENT_OPERATIONAL_STATUS_CHOICES, default='unknown')
    metadata = models.JSONField(default=dict, blank=True)
    evidence_references = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['twin', 'name']
        verbose_name = 'Twin Component'
        verbose_name_plural = 'Twin Components'

    def __str__(self):
        return f'{self.name} ({self.get_component_type_display()})'


# ── Process graph ─────────────────────────────────────────────────────────────

PROCESS_NODE_TYPE_CHOICES = [
    ('extraction', 'Extraction'),
    ('crushing', 'Crushing'),
    ('heating', 'Heating'),
    ('mixing', 'Mixing'),
    ('assembly', 'Assembly'),
    ('treatment', 'Treatment'),
    ('transport', 'Transport'),
    ('storage', 'Storage'),
    ('quality_control', 'Quality Control'),
    ('other', 'Other'),
]


class ProcessNode(TimeStampedModel):
    """One stage in the asset's process graph."""
    twin = models.ForeignKey(DigitalTwin, on_delete=models.CASCADE, related_name='process_nodes')
    component = models.ForeignKey(
        TwinComponent, on_delete=models.SET_NULL, null=True, blank=True, related_name='process_nodes',
    )
    node_type = models.CharField(max_length=20, choices=PROCESS_NODE_TYPE_CHOICES)
    name = models.CharField(max_length=255)
    sequence_order = models.PositiveIntegerField(default=0)

    capacity = models.FloatField(null=True, blank=True)
    capacity_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    actual_throughput = models.FloatField(null=True, blank=True)
    cycle_time_seconds = models.FloatField(null=True, blank=True)
    utilisation_pct = models.FloatField(null=True, blank=True)
    downtime_hours = models.FloatField(null=True, blank=True)
    yield_pct = models.FloatField(null=True, blank=True)
    cost_per_unit = models.FloatField(null=True, blank=True)

    energy_use = models.FloatField(null=True, blank=True)
    energy_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    water_use = models.FloatField(null=True, blank=True)
    water_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    emissions = models.FloatField(null=True, blank=True)
    emissions_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    waste_output = models.FloatField(null=True, blank=True)
    waste_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, null=True, blank=True, related_name='+')

    safety_incident_count = models.PositiveIntegerField(null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    evidence_references = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['twin', 'sequence_order']
        verbose_name = 'Process Node'
        verbose_name_plural = 'Process Nodes'

    def __str__(self):
        return f'{self.name} ({self.get_node_type_display()})'


class ProcessEdge(TimeStampedModel):
    """A directed flow between two ProcessNodes in the same twin's graph."""
    twin = models.ForeignKey(DigitalTwin, on_delete=models.CASCADE, related_name='process_edges')
    source_node = models.ForeignKey(ProcessNode, on_delete=models.CASCADE, related_name='outgoing_edges')
    target_node = models.ForeignKey(ProcessNode, on_delete=models.CASCADE, related_name='incoming_edges')
    label = models.CharField(max_length=150, blank=True)
    sequence_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['twin', 'sequence_order']
        verbose_name = 'Process Edge'
        verbose_name_plural = 'Process Edges'
        constraints = [
            models.UniqueConstraint(fields=['source_node', 'target_node'], name='uniq_process_edge'),
        ]

    def __str__(self):
        return f'{self.source_node.name} -> {self.target_node.name}'


RESOURCE_TYPE_CHOICES = [
    ('material', 'Material'),
    ('energy', 'Energy'),
    ('fuel', 'Fuel'),
    ('water', 'Water'),
    ('heat', 'Heat'),
    ('waste', 'Waste'),
    ('emissions', 'Emissions'),
    ('financial_value', 'Financial Value'),
    ('information_data', 'Information / Data'),
]


class ResourceFlow(TimeStampedModel):
    """A quantified flow of material/energy/water/waste/etc. between two
    points in the twin's component or process graph."""
    twin = models.ForeignKey(DigitalTwin, on_delete=models.CASCADE, related_name='resource_flows')
    source_node = models.ForeignKey(
        ProcessNode, on_delete=models.SET_NULL, null=True, blank=True, related_name='outbound_flows',
    )
    destination_node = models.ForeignKey(
        ProcessNode, on_delete=models.SET_NULL, null=True, blank=True, related_name='inbound_flows',
    )
    source_component = models.ForeignKey(
        TwinComponent, on_delete=models.SET_NULL, null=True, blank=True, related_name='outbound_flows',
    )
    destination_component = models.ForeignKey(
        TwinComponent, on_delete=models.SET_NULL, null=True, blank=True, related_name='inbound_flows',
    )
    resource_type = models.CharField(max_length=20, choices=RESOURCE_TYPE_CHOICES)
    quantity = models.FloatField()
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='resource_flows')
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    loss_quantity = models.FloatField(null=True, blank=True)
    cost = models.FloatField(null=True, blank=True)
    currency = models.CharField(max_length=10, default='USD')
    confidence = models.FloatField(null=True, blank=True)
    evidence_references = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['twin', '-period_start']
        verbose_name = 'Resource Flow'
        verbose_name_plural = 'Resource Flows'

    def __str__(self):
        return f'{self.get_resource_type_display()}: {self.quantity} {self.unit.symbol or self.unit.code}'


# ── Governed metric catalog ───────────────────────────────────────────────────

class MetricDefinition(TimeStampedModel):
    """The governed catalog entry for a metric (e.g. 'energy_intensity').
    Instances/observations live on OperationalMetric — this is definition,
    not value, matching the ethics.FormulaDefinition/FormulaScore split."""
    code = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    unit_category = models.ForeignKey(UnitCategory, on_delete=models.PROTECT, null=True, blank=True, related_name='metric_definitions')
    default_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    higher_is_better = models.BooleanField(
        null=True, blank=True,
        help_text='None when direction is not universally meaningful for this metric.',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Metric Definition'
        verbose_name_plural = 'Metric Definitions'

    def __str__(self):
        return self.name


VERIFICATION_STATUS_CHOICES = [
    ('unverified', 'Unverified'),
    ('system_checked', 'System Checked'),
    ('human_reviewed', 'Human Reviewed'),
    ('independently_verified', 'Independently Verified'),
]


class OperationalMetric(TimeStampedModel):
    """One observed/derived value of a MetricDefinition for a twin."""
    definition = models.ForeignKey(MetricDefinition, on_delete=models.PROTECT, related_name='observations')
    twin = models.ForeignKey(DigitalTwin, on_delete=models.CASCADE, related_name='metrics')
    component = models.ForeignKey(
        TwinComponent, on_delete=models.SET_NULL, null=True, blank=True, related_name='metrics',
    )
    process_node = models.ForeignKey(
        ProcessNode, on_delete=models.SET_NULL, null=True, blank=True, related_name='metrics',
    )
    value = models.FloatField()
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='+')
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    source = models.CharField(max_length=255, blank=True, help_text='e.g. "meter reading", "supplier invoice", "SCADA export".')
    confidence = models.FloatField(null=True, blank=True)
    verification_status = models.CharField(max_length=25, choices=VERIFICATION_STATUS_CHOICES, default='unverified')
    evidence_references = models.JSONField(default=list, blank=True)
    calculation_method = models.TextField(blank=True, help_text='Formula/derivation, if this value is not a direct observation.')
    recorded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['twin', '-recorded_at']
        verbose_name = 'Operational Metric'
        verbose_name_plural = 'Operational Metrics'

    def __str__(self):
        return f'{self.definition.name}: {self.value} {self.unit.symbol or self.unit.code}'


# ── Data gaps ──────────────────────────────────────────────────────────────────

DATA_GAP_SEVERITY_CHOICES = [
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
    ('critical', 'Critical'),
]

DATA_GAP_STATUS_CHOICES = [
    ('open', 'Open'),
    ('collection_planned', 'Collection Planned'),
    ('in_progress', 'In Progress'),
    ('resolved', 'Resolved'),
    ('accepted_risk', 'Accepted Risk'),
]


class TwinDataGap(TimeStampedModel):
    """A named, honest admission of missing or unreliable data. A Digital
    Twin must not pretend to know values that are absent — this is where
    that absence is recorded instead."""
    twin = models.ForeignKey(DigitalTwin, on_delete=models.CASCADE, related_name='data_gaps')
    affected_area = models.CharField(max_length=255)
    required_data = models.TextField()
    why_it_matters = models.TextField()
    severity = models.CharField(max_length=10, choices=DATA_GAP_SEVERITY_CHOICES, default='medium')
    recommended_collection_method = models.TextField(blank=True)
    responsible_role = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=20, choices=DATA_GAP_STATUS_CHOICES, default='open')
    evidence_requirement = models.TextField(blank=True)

    class Meta:
        ordering = ['twin', '-severity']
        verbose_name = 'Twin Data Gap'
        verbose_name_plural = 'Twin Data Gaps'

    def __str__(self):
        return f'{self.affected_area} ({self.get_severity_display()})'


# ── Loss detection (candidate, pre-promotion) ────────────────────────────────

LOSS_DETECTION_STATUS_CHOICES = [
    ('candidate', 'Candidate'),
    ('under_review', 'Under Review'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('promoted', 'Promoted'),
]


class LossDetection(TimeStampedModel):
    """An AI-computed, UNAPPROVED candidate operational loss. Never
    auto-approved: only on explicit human approval does
    services/loss_detection.py promote this into a real
    waste_to_value_capital_allocation_engine.OperationalLoss row (see
    `promoted_loss`)."""
    twin = models.ForeignKey(DigitalTwin, on_delete=models.CASCADE, related_name='loss_detections')
    component = models.ForeignKey(
        TwinComponent, on_delete=models.SET_NULL, null=True, blank=True, related_name='loss_detections',
    )
    process_node = models.ForeignKey(
        ProcessNode, on_delete=models.SET_NULL, null=True, blank=True, related_name='loss_detections',
    )
    loss_type = models.CharField(max_length=40, choices=LOSS_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    metrics_used = models.ManyToManyField(OperationalMetric, blank=True, related_name='loss_detections')
    calculation_notes = models.TextField(blank=True, help_text='Formula, inputs and assumptions behind this detection.')
    estimated_annual_impact = models.FloatField(null=True, blank=True)
    currency = models.CharField(max_length=10, default='USD')
    confidence = models.FloatField(default=50.0)
    evidence_references = models.JSONField(default=list, blank=True)

    status = models.CharField(max_length=15, choices=LOSS_DETECTION_STATUS_CHOICES, default='candidate')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)
    promoted_loss = models.ForeignKey(
        'waste_to_value_capital_allocation_engine.OperationalLoss',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='digital_twin_detections',
    )

    class Meta:
        ordering = ['twin', '-estimated_annual_impact']
        verbose_name = 'Loss Detection'
        verbose_name_plural = 'Loss Detections'

    def __str__(self):
        return f'{self.title} ({self.get_status_display()})'

    @property
    def human_approved(self):
        """Duck-typed for services/human_approval_gate.py: derived from
        `status`, never a second independent field that could disagree with it."""
        if self.status in ('approved', 'promoted'):
            return True
        if self.status == 'rejected':
            return False
        return None


# ── Modernisation scenarios ───────────────────────────────────────────────────

SCENARIO_TYPE_CHOICES = [
    ('no_change', 'No-Change Baseline'),
    ('low_cost', 'Low-Cost Optimisation'),
    ('strategic', 'Strategic Modernisation'),
]

DISRUPTION_LEVEL_CHOICES = [
    ('none', 'None'),
    ('low', 'Low'),
    ('medium', 'Medium'),
    ('high', 'High'),
]


class ModernisationScenario(TimeStampedModel):
    """Twin-specific context for one InterventionOption. A thin OneToOne
    companion, not a duplicate: CAPEX/OPEX/payback/status/risk_level already
    live on `intervention`; this table adds only the fields that don't exist
    upstream. `scenario_type` is a coarser, twin-facing tier grouping — it
    maps onto (does not duplicate) `intervention.intervention_type`:
    no_change -> do_nothing, low_cost -> operational_optimisation,
    strategic -> equipment_upgrade / infrastructure_upgrade."""
    intervention = models.OneToOneField(
        'waste_to_value_capital_allocation_engine.InterventionOption',
        on_delete=models.CASCADE, related_name='digital_twin_scenario',
    )
    twin = models.ForeignKey(DigitalTwin, on_delete=models.CASCADE, related_name='scenarios')
    component = models.ForeignKey(
        TwinComponent, on_delete=models.SET_NULL, null=True, blank=True, related_name='scenarios',
    )
    process_node = models.ForeignKey(
        ProcessNode, on_delete=models.SET_NULL, null=True, blank=True, related_name='scenarios',
    )
    loss_detection = models.ForeignKey(
        LossDetection, on_delete=models.SET_NULL, null=True, blank=True, related_name='scenarios',
    )
    scenario_type = models.CharField(max_length=15, choices=SCENARIO_TYPE_CHOICES)
    technology_category = models.CharField(max_length=150, blank=True)
    technical_specification = models.TextField(blank=True, help_text='Supplier-neutral technical description.')
    implementation_phases = models.JSONField(default=list, blank=True, help_text='List of {phase, description, duration}.')

    energy_impact = models.FloatField(null=True, blank=True, help_text='Positive = increase, negative = reduction.')
    energy_impact_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    water_impact = models.FloatField(null=True, blank=True)
    water_impact_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    waste_impact = models.FloatField(null=True, blank=True)
    waste_impact_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    emissions_impact = models.FloatField(null=True, blank=True)
    emissions_impact_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    production_impact_pct = models.FloatField(null=True, blank=True)
    downtime_impact_hours = models.FloatField(null=True, blank=True)

    worker_impact = models.TextField(blank=True)
    community_impact = models.TextField(blank=True)
    operational_disruption = models.CharField(max_length=10, choices=DISRUPTION_LEVEL_CHOICES, default='low')
    dependencies = models.JSONField(default=list, blank=True)
    technical_risks = models.JSONField(default=list, blank=True)
    regulatory_requirements = models.JSONField(default=list, blank=True)

    confidence = models.FloatField(null=True, blank=True)
    evidence_references = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['twin', 'scenario_type']
        verbose_name = 'Modernisation Scenario'
        verbose_name_plural = 'Modernisation Scenarios'

    def __str__(self):
        return f'{self.intervention.title} ({self.get_scenario_type_display()})'


# ── Qur'anic Stewardship KPI Engine ───────────────────────────────────────────
# Four distinct governance levels, never collapsed into one LLM-generated
# statement: sacred source -> scholarly interpretation -> operational rule ->
# numerical KPI -> (separately) the human governance decision on HumanDecision.

REVIEW_STATUS_CHOICES = [
    ('draft_reflection', 'Draft Reflection'),
    ('source_needed', 'Source Needed'),
    ('translation_pending', 'Translation Pending'),
    ('tafsir_pending', 'Tafsir Pending'),
    ('scholar_review_pending', 'Scholar Review Pending'),
    ('wellbeing_review_required', 'Wellbeing Review Required'),
    ('approved_for_preview', 'Approved for Preview'),
    ('approved_for_public', 'Approved for Public'),
    ('archived', 'Archived'),
]

SOURCE_TRADITION_CHOICES = [
    ('quran', "Qur'an"),
    ('hadith', 'Hadith'),
    ('other', 'Other'),
]

REQUIRES_SCHOLARLY_REVIEW_NOTE = 'Requires scholarly review before use in any principle or KPI.'


class SacredSourceReference(TimeStampedModel):
    """A versioned, reviewable pointer to a sacred-text source. No verse
    text or translation is authored by this application — every field below
    is either a citation locator or left blank pending real scholarly input."""
    source_tradition = models.CharField(max_length=10, choices=SOURCE_TRADITION_CHOICES, default='quran')
    source_book = models.CharField(max_length=150, blank=True, help_text='e.g. "Sahih al-Bukhari", for hadith sources.')
    surah_number = models.PositiveIntegerField(null=True, blank=True)
    surah_name = models.CharField(max_length=100, blank=True)
    ayah_range = models.CharField(max_length=40, blank=True, help_text='e.g. "2:275-276".')
    canonical_reference = models.CharField(max_length=255, help_text='Human-readable canonical citation.')
    approved_translation = models.TextField(
        blank=True, help_text='Left blank until a scholar-approved published translation is entered here verbatim.',
    )
    translation_source = models.CharField(max_length=255, blank=True, help_text='Which published translation this is drawn from.')
    source_url = models.URLField(blank=True)
    version = models.PositiveIntegerField(default=1)
    review_status = models.CharField(max_length=30, choices=REVIEW_STATUS_CHOICES, default='source_needed')
    reviewed_by = models.CharField(max_length=255, blank=True, help_text='Named scholar/reviewer (free text — no user account required for external scholars).')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default=REQUIRES_SCHOLARLY_REVIEW_NOTE)

    class Meta:
        ordering = ['source_tradition', 'surah_number']
        verbose_name = "Sacred Source Reference"
        verbose_name_plural = "Sacred Source References"

    def __str__(self):
        return self.canonical_reference

    def save(self, *args, **kwargs):
        # Any edit to the source/translation/wording reopens review — the
        # same rule Tazkiyah 114's content-schema uses.
        if self.pk:
            previous = SacredSourceReference.objects.filter(pk=self.pk).first()
            if previous and (
                previous.canonical_reference != self.canonical_reference
                or previous.approved_translation != self.approved_translation
                or previous.ayah_range != self.ayah_range
            ):
                self.version += 1
                if self.review_status in ('approved_for_preview', 'approved_for_public'):
                    self.review_status = 'scholar_review_pending'
        super().save(*args, **kwargs)


class StewardshipPrinciple(TimeStampedModel):
    """A named stewardship principle inspired by (never asserted as
    identical to) its source references. `approved_interpretation` is only
    ever populated by a real scholarly review process — never generated by
    an LLM."""
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(help_text='Plain-language statement of the principle.')
    source_references = models.ManyToManyField(SacredSourceReference, blank=True, related_name='principles')
    approved_interpretation = models.TextField(
        blank=True, help_text='Left blank until scholar-approved; never LLM-authored.',
    )
    operational_meaning = models.TextField(
        blank=True,
        help_text='How this principle translates into an operational rule, e.g. "avoid waste" -> "reduce preventable loss of useful resources".',
    )
    domain = models.CharField(max_length=100, blank=True, help_text='e.g. environmental, safety, financial, community.')
    version = models.PositiveIntegerField(default=1)
    review_status = models.CharField(max_length=30, choices=REVIEW_STATUS_CHOICES, default='draft_reflection')
    is_approved_for_use = models.BooleanField(
        default=False,
        help_text='Must be explicitly set True by a real scholarly review process before any KPI using this principle can be marked approved.',
    )
    reviewed_by = models.CharField(max_length=255, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Stewardship Principle'
        verbose_name_plural = 'Stewardship Principles'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


SCORING_DIRECTION_CHOICES = [
    ('higher_is_better', 'Higher is Better'),
    ('lower_is_better', 'Lower is Better'),
    ('target_range', 'Target Range'),
]

KPI_APPROVAL_STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('requires_scholarly_review', 'Requires Scholarly Review'),
    ('approved', 'Approved'),
    ('retired', 'Retired'),
]


class StewardshipKPI(TimeStampedModel):
    """The governed, versioned DEFINITION of one operational KPI derived
    from a StewardshipPrinciple. The formula itself is plain deterministic
    Python in services/stewardship.py — this row documents and governs it,
    it does not execute code. Ships `requires_scholarly_review` by default;
    nothing here is presented as divine judgement."""
    principle = models.ForeignKey(StewardshipPrinciple, on_delete=models.PROTECT, related_name='kpis')
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(blank=True)
    applicable_asset_types = models.ManyToManyField(AssetType, blank=True, related_name='stewardship_kpis')
    metric_inputs = models.ManyToManyField(MetricDefinition, blank=True, related_name='stewardship_kpis')
    formula_definition = models.TextField(
        help_text='Plain-language + pseudocode description of the deterministic formula. '
                   'The real implementation lives in services/stewardship.py.',
    )
    formula_version = models.CharField(max_length=20, default='1.0.0')
    scoring_direction = models.CharField(max_length=20, choices=SCORING_DIRECTION_CHOICES, default='higher_is_better')
    target_min = models.FloatField(null=True, blank=True)
    target_max = models.FloatField(null=True, blank=True)
    warning_threshold = models.FloatField(null=True, blank=True)
    blocking_threshold = models.FloatField(null=True, blank=True)
    evidence_requirements = models.TextField(blank=True)
    blocking_rule = models.TextField(blank=True, help_text='Plain-language description of when this KPI blocks promotion outright.')
    warning_rule = models.TextField(blank=True)
    version = models.PositiveIntegerField(default=1)
    approval_status = models.CharField(max_length=30, choices=KPI_APPROVAL_STATUS_CHOICES, default='requires_scholarly_review')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['principle', 'name']
        verbose_name = 'Stewardship KPI'
        verbose_name_plural = 'Stewardship KPIs'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def is_approved_for_use(self):
        """A KPI can only be treated as approved if BOTH the KPI row and its
        parent principle have been explicitly approved — approval never
        propagates upward from a KPI to bless an unreviewed principle."""
        return self.approval_status == 'approved' and self.principle.is_approved_for_use


class StewardshipAssessment(TimeStampedModel):
    """One INSTANCE of a StewardshipKPI computed against a
    ModernisationScenario. This is an operational indicator inspired by an
    approved principle — never presented as a divine judgement."""
    scenario = models.ForeignKey(ModernisationScenario, on_delete=models.CASCADE, related_name='stewardship_assessments')
    kpi = models.ForeignKey(StewardshipKPI, on_delete=models.PROTECT, related_name='assessments')
    input_metrics = models.JSONField(default=dict, blank=True, help_text='{metric_code: value} snapshot used in this calculation.')
    calculated_score = models.FloatField(null=True, blank=True)
    evidence_references = models.JSONField(default=list, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    warning = models.BooleanField(default=False)
    warning_reason = models.TextField(blank=True)
    blocking = models.BooleanField(default=False)
    blocking_reason = models.TextField(blank=True)
    explanation = models.TextField(blank=True, help_text='Human-readable trace of the calculation.')
    formula_version = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['scenario', 'kpi']
        verbose_name = 'Stewardship Assessment'
        verbose_name_plural = 'Stewardship Assessments'

    def __str__(self):
        return f'{self.kpi.name} — {self.scenario.intervention.title}'


# ── Human governance ───────────────────────────────────────────────────────────

HUMAN_DECISION_CHOICES = [
    ('approved', 'Approved'),
    ('approved_with_conditions', 'Approved with Conditions'),
    ('rejected', 'Rejected'),
    ('deferred', 'Deferred'),
]

DECISION_APPROVING_VALUES = {'approved', 'approved_with_conditions'}


class HumanDecision(TimeStampedModel):
    """A human's recorded, auditable decision on a ModernisationScenario.
    `human_approved` is the exact duck-typed boolean convention
    `agent_runtime_model_router.services.human_approval_gate` reads — never
    inferred anywhere else in this app."""
    scenario = models.ForeignKey(ModernisationScenario, on_delete=models.CASCADE, related_name='human_decisions')
    council_run = models.ForeignKey(
        'ai_agent_council.CouncilRun', on_delete=models.SET_NULL, null=True, blank=True, related_name='digital_twin_decisions',
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='digital_twin_decisions',
    )
    reviewer_role = models.CharField(max_length=100, blank=True)
    decision = models.CharField(max_length=30, choices=HUMAN_DECISION_CHOICES)
    comments = models.TextField(blank=True)
    conditions = models.JSONField(default=list, blank=True)
    rejected_alternatives = models.ManyToManyField(
        ModernisationScenario, blank=True, related_name='rejected_by_decisions',
    )
    human_approved = models.BooleanField(
        null=True, blank=True, default=None,
        help_text='Explicit human sign-off, read by services/human_approval_gate.py — never inferred.',
    )
    capital_allocation_decision = models.ForeignKey(
        'waste_to_value_capital_allocation_engine.CapitalAllocationDecision',
        on_delete=models.SET_NULL, null=True, blank=True, related_name='digital_twin_source_decision',
    )
    decided_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-decided_at']
        verbose_name = 'Human Decision'
        verbose_name_plural = 'Human Decisions'

    def __str__(self):
        return f'{self.get_decision_display()} — {self.scenario.intervention.title}'

    def save(self, *args, **kwargs):
        # human_approved is derived from decision, never set independently,
        # so the gate function and the UI can never disagree about intent.
        if self.decision in DECISION_APPROVING_VALUES:
            self.human_approved = True
        elif self.decision == 'rejected':
            self.human_approved = False
        else:
            self.human_approved = None
        super().save(*args, **kwargs)


# ── Implementation tracking ───────────────────────────────────────────────────

IMPLEMENTATION_STATUS_CHOICES = [
    ('planned', 'Planned'),
    ('in_progress', 'In Progress'),
    ('completed', 'Completed'),
    ('delayed', 'Delayed'),
    ('cancelled', 'Cancelled'),
]


class ImplementationAction(TimeStampedModel):
    """One concrete action implementing an approved ModernisationScenario."""
    scenario = models.ForeignKey(ModernisationScenario, on_delete=models.CASCADE, related_name='implementation_actions')
    human_decision = models.ForeignKey(
        HumanDecision, on_delete=models.SET_NULL, null=True, blank=True, related_name='implementation_actions',
    )
    title = models.CharField(max_length=255)
    owner = models.CharField(max_length=150, blank=True)
    owner_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )
    planned_start_date = models.DateField(null=True, blank=True)
    planned_end_date = models.DateField(null=True, blank=True)
    actual_start_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=IMPLEMENTATION_STATUS_CHOICES, default='planned')
    budget = models.FloatField(null=True, blank=True)
    currency = models.CharField(max_length=10, default='USD')
    expected_outcome = models.TextField(blank=True)
    evidence_references = models.JSONField(default=list, blank=True)
    deviation_from_plan = models.TextField(blank=True)
    lessons_learned = models.TextField(blank=True)

    class Meta:
        ordering = ['scenario', 'planned_start_date']
        verbose_name = 'Implementation Action'
        verbose_name_plural = 'Implementation Actions'

    def __str__(self):
        return self.title


class MeasuredOutcome(TimeStampedModel):
    """A real, post-implementation measurement compared against what was
    predicted. Variance is always recomputed from the stored values — never
    hand-entered — so it can't silently drift from the numbers it describes.
    No autonomous model retraining occurs anywhere in this app."""
    action = models.ForeignKey(ImplementationAction, on_delete=models.CASCADE, related_name='measured_outcomes')
    metric_definition = models.ForeignKey(
        MetricDefinition, on_delete=models.SET_NULL, null=True, blank=True, related_name='measured_outcomes',
    )
    predicted_value = models.FloatField(null=True, blank=True)
    actual_value = models.FloatField(null=True, blank=True)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    variance = models.FloatField(null=True, blank=True, editable=False)
    variance_pct = models.FloatField(null=True, blank=True, editable=False)
    confidence_impact_note = models.TextField(blank=True)
    model_learning_note = models.TextField(blank=True, help_text='Manual note only — no autonomous model retraining occurs.')
    measured_at = models.DateField(default=timezone.now)
    evidence_references = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-measured_at']
        verbose_name = 'Measured Outcome'
        verbose_name_plural = 'Measured Outcomes'

    def __str__(self):
        label = self.metric_definition.name if self.metric_definition_id else 'outcome'
        return f'{label}: predicted {self.predicted_value}, actual {self.actual_value}'

    def save(self, *args, **kwargs):
        if self.predicted_value is not None and self.actual_value is not None:
            self.variance = round(self.actual_value - self.predicted_value, 4)
            if self.predicted_value != 0:
                self.variance_pct = round((self.variance / abs(self.predicted_value)) * 100, 2)
            else:
                self.variance_pct = None
        else:
            self.variance = None
            self.variance_pct = None
        super().save(*args, **kwargs)
