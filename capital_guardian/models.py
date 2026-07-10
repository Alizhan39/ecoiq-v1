"""
capital_guardian/models.py — Capital Guardian: institutional investor
transparency and capital intelligence (Phase 1).

This is NOT a fundraising platform, an investment marketplace, or a payment
processor — it is a governance, monitoring and decision-intelligence layer
over a real gold_intelligence.GoldProject.

Reused directly, never duplicated:
  - gold_intelligence.GoldProject is the project this whole app operates on
    (hard FK — Capital Guardian's entire purpose is governing one specific
    project, unlike geo_intelligence's looser soft-reference convention).
  - gold_intelligence.CapitalBudgetLine — the budget-category envelope each
    CapitalTraceEntry below rolls up into (no second budget-category model).
  - gold_intelligence.EquipmentSpec / MineTimelineMilestone — extended with
    Capital Guardian's lifecycle/verification/capital-release fields
    directly in gold_intelligence/models.py, not re-declared here.
  - evidence_memory.EvidenceMemory — "Evidence Documents"/"Evidence
    Coverage" for any trace entry, equipment item or milestone read this via
    the existing source_reference soft-pointer convention (e.g.
    "capital_guardian.CapitalTraceEntry:42"), never a new evidence model.

Four models are genuinely new, because nothing in the platform already
represents an SPV/governance structure, an individual evidenced capital
movement, a rule-detected red flag, or a daily operational snapshot:
ProjectGovernance, CapitalTraceEntry, RedFlag, OperationalSnapshot.

`is_demo` follows the exact convention already established by
geo_intelligence/gold_intelligence: a demo/illustrative row must never be
presented as a verified real-world claim.

--- Phase 2 additions ---

Two more models are genuinely new here, because nothing in the platform
already represents a configurable risk-rule threshold or a generic change-
history entry: RedFlagRuleConfig, AuditLogEntry. (An audit of the platform
for an existing history/versioning pattern found `audit` — an unrelated
facility-energy-audit app — and `legacy_safe.AuditLog` — a narrow AI
retrieval-decision log; neither is a change-history mechanism for arbitrary
model fields, and no django-simple-history-style package is installed, so a
small, purpose-built model is the right amount of new code here, not an
over-build.)

RedFlag/OperationalSnapshot are EXTENDED in place (actual_value/
threshold_value on RedFlag, confidence on OperationalSnapshot) rather than
duplicated, matching the same "extend, don't parallel-build" discipline
used on gold_intelligence's models in Phase 1.

--- Phase 3 additions ---

`SupplierProfile` is the one genuinely new model this phase — a project-
independent equipment-supplier reference/catalog row. Its `illustrative_*`
rating fields (risk, financial, ESG) are explicitly synthetic scores
attached to a real, named company for demonstration purposes only — every
template surfacing them carries a prominent "SYNTHETIC / ILLUSTRATIVE —
NOT A REAL ASSESSMENT" disclaimer (see templates/capital_guardian/
supplier_comparison.html), and the field names themselves are prefixed so
no future reader of this code mistakes them for a real rating feed.

Everything else is additive fields on already-existing models: a
dividend-policy note on ProjectGovernance, a commissioned date/expected
lifespan/spare-parts/maintenance-contract/country on EquipmentSpec (real
inputs a deterministic remaining-useful-life estimate can be computed
from — never a black-box ML prediction), and doré inventory/truck fleet/
tailings/water-stored readings on OperationalSnapshot.
"""
from django.conf import settings
from django.db import models

from gold_intelligence.models import CapitalBudgetLine, EquipmentSpec, GoldProject, MineTimelineMilestone


class ProjectGovernance(models.Model):
    """
    Conceptual demo governance/SPV structure for one GoldProject. Explicitly
    NOT legal advice or a substitute for professional legal structuring —
    see the disclaimer surfaced on every governance page.
    """
    project = models.OneToOneField(GoldProject, on_delete=models.CASCADE, related_name='governance')

    founder_holdco_pct = models.FloatField(null=True, blank=True)
    investor_spv_pct = models.FloatField(null=True, blank=True)
    founder_board_seats = models.PositiveIntegerField(null=True, blank=True)
    investor_board_seats = models.PositiveIntegerField(null=True, blank=True)
    independent_chair_seats = models.PositiveIntegerField(null=True, blank=True)

    reserved_matters_active = models.BooleanField(default=False)
    escrow_account_active = models.BooleanField(default=False)
    investor_first_waterfall_active = models.BooleanField(default=False)
    quarterly_audit_active = models.BooleanField(default=False)
    independent_technical_adviser_active = models.BooleanField(default=False)
    insurance_monitoring_active = models.BooleanField(default=False)
    milestone_based_capital_release_active = models.BooleanField(default=False)

    notes = models.TextField(blank=True)
    # Phase 3 — real, if informal, free-text description of how distributions
    # are intended to work. Left blank (never a fabricated policy) unless a
    # real one has actually been recorded.
    dividend_policy_notes = models.TextField(blank=True)
    is_demo = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.project.name}: Governance'

    @property
    def active_controls_count(self):
        flags = [
            self.reserved_matters_active, self.escrow_account_active, self.investor_first_waterfall_active,
            self.quarterly_audit_active, self.independent_technical_adviser_active,
            self.insurance_monitoring_active, self.milestone_based_capital_release_active,
        ]
        return sum(1 for f in flags if f)


class CapitalTraceEntry(models.Model):
    """One evidenced, workflow-tracked capital movement — the individual
    transaction underneath a gold_intelligence.CapitalBudgetLine category
    rollup. Rolls up MONEY → APPROVAL → PAYMENT → EVIDENCE → ASSET →
    MILESTONE into one auditable row."""
    APPROVAL_STATUS_CHOICES = [
        ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ]
    INVESTOR_APPROVAL_STATUS_CHOICES = [
        ('not_required', 'Not Required'), ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ]
    VERIFICATION_STATUS_CHOICES = [
        ('unverified', 'Unverified'), ('pending', 'Pending'), ('verified', 'Verified'),
    ]
    INSURANCE_STATUS_CHOICES = [
        ('not_applicable', 'Not Applicable'), ('insured', 'Insured'), ('uninsured', 'Uninsured'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'), ('paid', 'Paid'), ('failed', 'Failed'),
    ]

    project = models.ForeignKey(GoldProject, on_delete=models.CASCADE, related_name='capital_trace_entries')
    trace_id = models.CharField(max_length=40, unique=True, blank=True)
    date = models.DateField()
    amount_usd = models.FloatField()
    currency = models.CharField(max_length=10, default='USD')
    purpose = models.CharField(max_length=250)
    budget_category = models.ForeignKey(
        CapitalBudgetLine, null=True, blank=True, on_delete=models.SET_NULL, related_name='trace_entries',
    )
    supplier = models.CharField(max_length=200, blank=True)

    approval_status = models.CharField(max_length=15, choices=APPROVAL_STATUS_CHOICES, default='pending')
    investor_approval_status = models.CharField(max_length=15, choices=INVESTOR_APPROVAL_STATUS_CHOICES, default='not_required')
    verification_status = models.CharField(max_length=15, choices=VERIFICATION_STATUS_CHOICES, default='unverified')
    insurance_status = models.CharField(max_length=15, choices=INSURANCE_STATUS_CHOICES, default='not_applicable')
    payment_status = models.CharField(max_length=15, choices=PAYMENT_STATUS_CHOICES, default='pending')

    related_equipment = models.ForeignKey(
        EquipmentSpec, null=True, blank=True, on_delete=models.SET_NULL, related_name='capital_trace_entries',
    )
    related_milestone = models.ForeignKey(
        MineTimelineMilestone, null=True, blank=True, on_delete=models.SET_NULL, related_name='capital_trace_entries',
    )

    is_demo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f'{self.trace_id}: {self.purpose}'

    def save(self, *args, **kwargs):
        if not self.trace_id:
            # Idempotent, human-readable, project-scoped sequence — never a
            # random/fabricated identifier standing in for a real reference.
            existing = CapitalTraceEntry.objects.filter(project=self.project).count()
            self.trace_id = f'CT-{self.project_id or "0"}-{existing + 1:04d}'
        super().save(*args, **kwargs)

    @property
    def evidence_documents(self):
        from evidence_memory.models import EvidenceMemory
        return EvidenceMemory.objects.filter(source_reference=f'capital_guardian.CapitalTraceEntry:{self.pk}')


class RedFlag(models.Model):
    """A rule-detected warning — never a fabricated AI prediction. See
    capital_guardian/services/red_flag_engine.py for the deterministic rules
    that create these rows from real, already-stored data."""
    SEVERITY_CHOICES = [('low', 'Low'), ('medium', 'Medium'), ('high', 'High')]
    RESOLUTION_STATUS_CHOICES = [
        ('open', 'Open'), ('acknowledged', 'Acknowledged'), ('under_review', 'Under Review'),
        ('resolved', 'Resolved'), ('false_positive', 'False Positive'),
    ]

    project = models.ForeignKey(GoldProject, on_delete=models.CASCADE, related_name='red_flags')
    rule_key = models.CharField(max_length=60, help_text='Which deterministic rule created this row (for idempotent re-detection).')
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    category = models.CharField(max_length=60)
    description = models.TextField()
    # Phase 2 — the real measured value and the configured threshold it was
    # compared against (see services/red_flag_engine.py), so the UI can show
    # "Actual Value" / "Threshold" honestly instead of only prose.
    actual_value = models.FloatField(null=True, blank=True)
    threshold_value = models.FloatField(null=True, blank=True)
    capital_exposure_usd = models.FloatField(null=True, blank=True)
    recommended_action = models.TextField(blank=True)
    responsible_party = models.CharField(max_length=200, blank=True)
    resolution_status = models.CharField(max_length=15, choices=RESOLUTION_STATUS_CHOICES, default='open')

    related_equipment = models.ForeignKey(
        EquipmentSpec, null=True, blank=True, on_delete=models.SET_NULL, related_name='red_flags',
    )
    related_milestone = models.ForeignKey(
        MineTimelineMilestone, null=True, blank=True, on_delete=models.SET_NULL, related_name='red_flags',
    )
    related_trace_entry = models.ForeignKey(
        CapitalTraceEntry, null=True, blank=True, on_delete=models.SET_NULL, related_name='red_flags',
    )

    detected_at = models.DateTimeField(auto_now_add=True)
    is_demo = models.BooleanField(default=True)
    acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    acknowledged_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-severity', '-detected_at']
        constraints = [models.UniqueConstraint(fields=['project', 'rule_key'], name='uniq_project_rule_key')]

    def __str__(self):
        return f'{self.project.name}: {self.category} ({self.get_severity_display()})'

    @property
    def evidence_documents(self):
        from evidence_memory.models import EvidenceMemory
        if not self.pk:
            return EvidenceMemory.objects.none()
        return EvidenceMemory.objects.filter(source_reference=f'capital_guardian.RedFlag:{self.pk}')


class RedFlagRuleConfig(models.Model):
    """
    A configurable warning/critical threshold for one red-flag rule —
    genuinely new (Phase 1's thresholds were hardcoded module constants in
    red_flag_engine.py). `project=None` is a platform-wide default row;
    a project-scoped row overrides it. Resolution order (see
    services/red_flag_engine.get_thresholds): project row → platform-default
    row → the rule's hardcoded fallback constant — so the engine always has
    a real, explainable number to compare against, never an unconfigured gap.
    """
    RULE_KEY_CHOICES = [
        ('capex_variance', 'CAPEX Variance'),
        ('insurance_renewal_due', 'Insurance Expiry'),
        ('equipment_availability', 'Equipment Availability'),
        ('recovery_rate', 'Recovery Rate vs. Target'),
        ('water_recycled', 'Water Recycling'),
    ]

    project = models.ForeignKey(
        GoldProject, null=True, blank=True, on_delete=models.CASCADE, related_name='red_flag_rule_configs',
        help_text='Leave blank for a platform-wide default applied to every project without its own override.',
    )
    rule_key = models.CharField(max_length=40, choices=RULE_KEY_CHOICES)
    enabled = models.BooleanField(default=True)
    warning_threshold = models.FloatField(null=True, blank=True)
    critical_threshold = models.FloatField(null=True, blank=True)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ['rule_key']
        constraints = [models.UniqueConstraint(fields=['project', 'rule_key'], name='uniq_project_rule_config')]

    def __str__(self):
        scope = self.project.name if self.project_id else 'Platform default'
        return f'{scope}: {self.get_rule_key_display()}'


class AuditLogEntry(models.Model):
    """
    An investor-facing change-history entry — "Audit History"/"Change
    History", explicitly NOT claimed to be cryptographically immutable or
    blockchain-verified (see the disclaimer on the Audit History page).
    Rows are created automatically by capital_guardian/signals.py whenever a
    tracked field changes on ProjectGovernance, MineTimelineMilestone,
    EquipmentSpec, CapitalBudgetLine, GoldProject's capital/insurance fields,
    RedFlag.resolution_status, or EvidenceMemory.verification_status for
    evidence scoped to this project — never hand-authored, so the log can't
    silently omit a real change.
    """
    EVENT_TYPE_CHOICES = [
        ('governance', 'Governance'),
        ('milestone', 'Milestone'),
        ('capex', 'CAPEX Budget'),
        ('capital', 'Capital / Insurance'),
        ('equipment', 'Equipment'),
        ('red_flag', 'Red Flag Status'),
        ('evidence', 'Evidence Verification'),
        ('capital_trace', 'Capital Trace Entry'),
    ]

    project = models.ForeignKey(GoldProject, on_delete=models.CASCADE, related_name='audit_log_entries')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    object_description = models.CharField(max_length=250, help_text='e.g. "Milestone: Construction", "Governance: Escrow Account".')
    field_name = models.CharField(max_length=100)
    previous_value = models.CharField(max_length=250, blank=True)
    new_value = models.CharField(max_length=250, blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    reason = models.TextField(blank=True)
    # Best-effort, only ever a real derived value (e.g. a RedFlag's own
    # resolution_status) — left blank when there is nothing honest to show.
    approval_status = models.CharField(max_length=100, blank=True)
    # Soft pointer to the changed row, e.g. "gold_intelligence.MineTimelineMilestone:12".
    source_reference = models.CharField(max_length=200, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.project.name}: {self.object_description} — {self.field_name}'

    @property
    def evidence_documents(self):
        from evidence_memory.models import EvidenceMemory
        if not self.pk:
            return EvidenceMemory.objects.none()
        return EvidenceMemory.objects.filter(source_reference=f'capital_guardian.AuditLogEntry:{self.pk}')


class OperationalSnapshot(models.Model):
    """One day's real (or, for the demo project, clearly-flagged synthetic)
    operational readout — the data behind the Mining Digital Twin. Distinct
    from GoldProject's lifetime/reserve-level assumptions (ore_grade_g_per_tonne
    etc.): this is a point-in-time actual."""
    ENVIRONMENTAL_STATUS_CHOICES = [('green', 'Green'), ('amber', 'Amber'), ('red', 'Red')]

    project = models.ForeignKey(GoldProject, on_delete=models.CASCADE, related_name='operational_snapshots')
    date = models.DateField()

    ore_mined_tonnes = models.FloatField(null=True, blank=True)
    plant_throughput_tph = models.FloatField(null=True, blank=True, help_text='Tonnes per hour.')
    gold_grade_g_per_tonne = models.FloatField(null=True, blank=True)
    recovery_rate_pct = models.FloatField(null=True, blank=True)
    dore_produced_kg = models.FloatField(null=True, blank=True)
    equipment_availability_pct = models.FloatField(null=True, blank=True)
    energy_use_mwh = models.FloatField(null=True, blank=True)
    water_recycled_pct = models.FloatField(null=True, blank=True)
    environmental_status = models.CharField(max_length=10, choices=ENVIRONMENTAL_STATUS_CHOICES, blank=True)

    # Phase 3 — additional real readings for the Live Digital Twin production view.
    dore_inventory_kg = models.FloatField(null=True, blank=True, help_text='Doré held in the gold vault, not yet shipped/refined.')
    truck_fleet_utilization_pct = models.FloatField(null=True, blank=True)
    tailings_stored_tonnes = models.FloatField(null=True, blank=True)
    water_stored_m3 = models.FloatField(null=True, blank=True)

    # Phase 2 — a real per-reading quality/confidence score, only ever
    # populated by an actual telemetry/QA source. Null (never a fabricated
    # 100%) for every demo snapshot below, since a synthetic reading has no
    # real sensor-confidence to report — the field exists so a future SCADA
    # integration can populate it without a schema change.
    confidence = models.FloatField(null=True, blank=True)

    is_demo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        constraints = [models.UniqueConstraint(fields=['project', 'date'], name='uniq_project_snapshot_date')]

    def __str__(self):
        return f'{self.project.name}: {self.date}'

    @property
    def evidence_documents(self):
        from evidence_memory.models import EvidenceMemory
        if not self.pk:
            return EvidenceMemory.objects.none()
        return EvidenceMemory.objects.filter(source_reference=f'capital_guardian.OperationalSnapshot:{self.pk}')


class SupplierProfile(models.Model):
    """
    Phase 3 — a project-independent equipment-supplier reference/catalog
    row for the Supplier Comparison page.

    IMPORTANT: `name` is a real, named company used as a clearly-labelled
    illustrative example (same convention as EquipmentSpec.manufacturer) —
    never a claim that the company is actually involved in any real project.
    The `illustrative_*` rating fields are SYNTHETIC scores invented for
    demonstration purposes only, NOT a real assessment of that company's
    actual risk, financial standing, or ESG performance — every template
    that displays them carries a prominent disclaimer, and the field names
    themselves are prefixed so this is unmistakable in code too.
    """
    name = models.CharField(max_length=150, unique=True)
    country = models.CharField(max_length=100, blank=True)
    equipment_specialty = models.CharField(max_length=200, blank=True, help_text='e.g. "Crushers, Mills", illustrative.')

    # Illustrative specs (same convention as EquipmentSpec's existing fields).
    typical_lead_time_weeks = models.PositiveIntegerField(null=True, blank=True)
    typical_warranty_years = models.PositiveIntegerField(null=True, blank=True)
    performance_guarantee_years = models.PositiveIntegerField(null=True, blank=True)
    insurance_backed = models.BooleanField(default=False)

    # Synthetic ratings — 0-100, never a real assessment (see docstring).
    illustrative_price_index = models.FloatField(null=True, blank=True, help_text='Relative price positioning, 0-100 (lower = cheaper). Synthetic.')
    illustrative_service_rating = models.FloatField(null=True, blank=True)
    illustrative_availability_rating = models.FloatField(null=True, blank=True)
    illustrative_energy_efficiency_rating = models.FloatField(null=True, blank=True)
    illustrative_co2_rating = models.FloatField(null=True, blank=True, help_text='Higher = lower relative emissions. Synthetic.')
    illustrative_risk_rating = models.FloatField(null=True, blank=True, help_text='Higher = lower relative risk. Synthetic.')
    illustrative_financial_rating = models.FloatField(null=True, blank=True)
    illustrative_esg_rating = models.FloatField(null=True, blank=True)
    why_selected_notes = models.TextField(blank=True)

    is_demo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def rating_pairs(self):
        """(label, value) for each synthetic rating — a real None passes
        through untouched so the template shows 'Data source required'
        rather than a fabricated bar."""
        return [
            ('Price Index', self.illustrative_price_index),
            ('Service', self.illustrative_service_rating),
            ('Availability', self.illustrative_availability_rating),
            ('Energy Efficiency', self.illustrative_energy_efficiency_rating),
            ('CO2', self.illustrative_co2_rating),
            ('Risk', self.illustrative_risk_rating),
            ('Financial', self.illustrative_financial_rating),
            ('ESG', self.illustrative_esg_rating),
        ]
