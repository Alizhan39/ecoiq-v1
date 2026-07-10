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
        ('open', 'Open'), ('acknowledged', 'Acknowledged'), ('resolved', 'Resolved'),
    ]

    project = models.ForeignKey(GoldProject, on_delete=models.CASCADE, related_name='red_flags')
    rule_key = models.CharField(max_length=60, help_text='Which deterministic rule created this row (for idempotent re-detection).')
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    category = models.CharField(max_length=60)
    description = models.TextField()
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

    is_demo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        constraints = [models.UniqueConstraint(fields=['project', 'date'], name='uniq_project_snapshot_date')]

    def __str__(self):
        return f'{self.project.name}: {self.date}'
