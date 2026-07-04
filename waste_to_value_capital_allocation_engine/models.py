"""
waste_to_value_capital_allocation_engine/models.py — the fintech / capital-
allocation layer that turns operational waste into finance-ready investment
opportunities.

Lifecycle: Operational Waste -> Capital at Risk -> Recoverable Value ->
Intervention Options -> Investment Model -> Funding Gap -> Funding Match ->
Council Decision -> Implementation -> MRV -> Verified Value Recovered ->
Capital Reallocation.

Honesty note, enforced throughout this app's services and templates:
- estimated_savings != verified_savings
- funding_route_identified != funding_secured
- supplier_quote != supplier_endorsement
- finance_ready_recommended != finance_ready_approved
`organisation`/`asset`/`project` are plain text fields, not foreign keys —
no real Company/Asset model exists elsewhere in this repo with rows that
would honestly back this domain, so free text is more honest than a
fabricated relationship.
"""
from django.db import models
from django.utils import timezone

LOSS_TYPE_CHOICES = [
    ('food_spoilage',                  'Food spoilage'),
    ('meat_spoilage',                  'Meat spoilage'),
    ('cold_chain_failure',             'Cold-chain failure'),
    ('excess_inventory',               'Excess inventory'),
    ('overproduction',                 'Overproduction'),
    ('energy_loss',                    'Energy loss'),
    ('heat_loss',                      'Heat loss'),
    ('water_leakage',                  'Water leakage'),
    ('material_waste',                 'Material waste'),
    ('industrial_by_products',         'Industrial by-products'),
    ('idle_machinery',                 'Idle machinery'),
    ('idle_buildings',                 'Idle buildings'),
    ('unused_warehouse_capacity',      'Unused warehouse capacity'),
    ('empty_transport_capacity',       'Empty transport capacity'),
    ('production_downtime',           'Production downtime'),
    ('defect_rejection_losses',        'Defect and rejection losses'),
    ('maintenance_inefficiency',       'Maintenance inefficiency'),
    ('underused_renewable_generation', 'Underused renewable generation'),
    ('curtailed_energy',              'Curtailed energy'),
    ('unmatched_surplus',             'Unmatched surplus'),
]

EVIDENCE_QUALITY_CHOICES = [
    ('strong',  'Strong'),
    ('medium',  'Medium'),
    ('weak',    'Weak'),
    ('missing', 'Missing'),
]

READINESS_CHOICES = [
    ('not_ready',    'Not Ready'),
    ('draft',        'Draft'),
    ('needs_review', 'Needs Review'),
    ('ready',        'Ready'),
]

LOSS_STATUS_CHOICES = [
    ('detected',   'Detected'),
    ('quantified', 'Quantified'),
    ('modelled',   'Modelled'),
    ('actioned',   'Actioned'),
    ('closed',     'Closed'),
]

# The PREVENT -> REALLOCATE -> RESELL -> REDISTRIBUTE -> REPROCESS -> RECOVER
# -> DISPOSE (last resort) hierarchy, shared by InterventionOption and
# InterventionScenario so both use the same vocabulary.
INTERVENTION_TYPE_CHOICES = [
    ('do_nothing',              'Do nothing'),
    ('prevention',               'Prevention'),
    ('operational_optimisation', 'Operational optimisation'),
    ('transfer_redistribution',  'Transfer / redistribution'),
    ('resale',                   'Resale'),
    ('processing_recovery',      'Processing / recovery'),
    ('equipment_upgrade',        'Equipment upgrade'),
    ('infrastructure_upgrade',   'Infrastructure upgrade'),
    ('disposal',                 'Disposal (last resort)'),
]

RISK_LEVEL_CHOICES = [('low', 'Low'), ('medium', 'Medium'), ('high', 'High')]

INTERVENTION_STATUS_CHOICES = [
    ('proposed',   'Proposed'),
    ('modelled',   'Modelled'),
    ('recommended', 'Recommended'),
    ('approved',   'Approved'),
    ('rejected',   'Rejected'),
    ('implemented', 'Implemented'),
]

SENSITIVITY_CASE_CHOICES = [('base', 'Base'), ('upside', 'Upside'), ('downside', 'Downside')]

FUNDING_GAP_STATUS_CHOICES = [
    ('draft',        'Draft'),
    ('under_review', 'Under Review'),
    ('resolved',     'Resolved'),
    ('blocked',      'Blocked'),
]

ROUTE_TYPE_CHOICES = [
    ('owner_funded',            'Owner-funded'),
    ('equipment_finance',       'Equipment finance'),
    ('working_capital_finance', 'Working-capital finance'),
    ('green_loan',              'Green loan'),
    ('impact_investment',       'Impact investment'),
    ('supplier_finance',        'Supplier finance'),
    ('grant',                   'Grant'),
    ('csr_sponsorship',         'CSR sponsorship'),
    ('revenue_share',           'Revenue-share'),
    ('islamic_finance_review',  'Islamic finance review'),
]

ELIGIBILITY_STATUS_CHOICES = [
    ('eligible',     'Eligible'),
    ('not_eligible', 'Not Eligible'),
    ('needs_review', 'Needs Review'),
]

DUE_DILIGENCE_STATUS_CHOICES = [
    ('not_started', 'Not Started'),
    ('in_progress', 'In Progress'),
    ('passed',      'Passed'),
    ('failed',      'Failed'),
]

OUTREACH_STATUS_CHOICES = [
    ('not_started',          'Not Started'),
    ('pending_approval',     'Pending Approval'),
    ('approved_for_outreach', 'Approved for Outreach'),
    ('contacted',            'Contacted'),
    ('declined',             'Declined'),
]

APPROVAL_STATUS_CHOICES = [
    ('pending',                 'Pending'),
    ('approved',                'Approved'),
    ('approved_with_conditions', 'Approved with Conditions'),
    ('rejected',                'Rejected'),
]

MRV_STATUS_CHOICES = [
    ('not_started',       'Not Started'),
    ('baseline_only',     'Baseline Only'),
    ('after_data_pending', 'After-Data Pending'),
    ('verified',          'Verified'),
    ('disputed',          'Disputed'),
]

VERIFIED_STATUS_CHOICES = [('estimated', 'Estimated'), ('verified', 'Verified')]

PUBLIC_PRIVATE_CHOICES = [('public', 'Public'), ('private', 'Private')]


class OperationalLoss(models.Model):
    """One identified pocket of operational waste, treated as lost economic value."""
    organisation = models.CharField(max_length=200, blank=True)
    asset        = models.CharField(max_length=200, blank=True)
    project      = models.CharField(max_length=200, blank=True)
    location     = models.CharField(max_length=200, blank=True)
    country      = models.CharField(max_length=100, blank=True)
    sector       = models.CharField(max_length=100, blank=True)

    loss_type    = models.CharField(max_length=40, choices=LOSS_TYPE_CHOICES)
    title        = models.CharField(max_length=255)
    description  = models.TextField(blank=True)

    quantity_lost = models.FloatField(null=True, blank=True)
    unit          = models.CharField(max_length=40, blank=True)

    financial_loss_amount  = models.FloatField(help_text='Current, already-incurred financial loss.')
    projected_future_loss   = models.FloatField(null=True, blank=True, help_text='Forecast, not yet incurred — must be labelled "projected", never "actual".')
    currency               = models.CharField(max_length=10, default='GBP')
    period                  = models.CharField(max_length=60, blank=True, help_text='e.g. "2026 Q1", "trailing 12 months".')

    evidence_quality = models.CharField(max_length=10, choices=EVIDENCE_QUALITY_CHOICES, default='medium')
    confidence       = models.FloatField(default=50.0)

    avoidability_score = models.FloatField(default=50.0)
    urgency_score      = models.FloatField(default=50.0)
    time_horizon       = models.CharField(max_length=60, blank=True)

    human_impact        = models.TextField(blank=True)
    environmental_impact = models.TextField(blank=True)

    intervention_readiness = models.CharField(max_length=15, choices=READINESS_CHOICES, default='not_ready')
    finance_readiness       = models.CharField(max_length=15, choices=READINESS_CHOICES, default='not_ready')
    mrv_readiness           = models.CharField(max_length=15, choices=READINESS_CHOICES, default='not_ready')

    status     = models.CharField(max_length=15, choices=LOSS_STATUS_CHOICES, default='detected')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering            = ['-created_at']
        verbose_name        = 'Operational Loss'
        verbose_name_plural = 'Operational Losses'

    def __str__(self):
        return f'{self.title} ({self.get_loss_type_display()})'


class LossEvidence(models.Model):
    """Evidence backing one OperationalLoss record."""
    operational_loss       = models.ForeignKey(OperationalLoss, on_delete=models.CASCADE, related_name='evidence')
    evidence_reference      = models.CharField(max_length=120)
    evidence_type           = models.CharField(max_length=80, blank=True)
    source_document         = models.CharField(max_length=255, blank=True)
    source_page_or_section  = models.CharField(max_length=80, blank=True)
    public_private_status    = models.CharField(max_length=10, choices=PUBLIC_PRIVATE_CHOICES, default='private')
    evidence_quality        = models.CharField(max_length=10, choices=EVIDENCE_QUALITY_CHOICES, default='medium')
    confidence               = models.FloatField(default=50.0)

    class Meta:
        ordering            = ['operational_loss', 'id']
        verbose_name        = 'Loss Evidence'
        verbose_name_plural = 'Loss Evidence'

    def __str__(self):
        return f'{self.evidence_reference} ({self.operational_loss.title})'


class InterventionOption(models.Model):
    """One candidate action against an OperationalLoss (e.g. one of several lettered options in a demo case)."""
    operational_loss = models.ForeignKey(OperationalLoss, on_delete=models.CASCADE, related_name='interventions')
    title            = models.CharField(max_length=255)
    intervention_type = models.CharField(max_length=30, choices=INTERVENTION_TYPE_CHOICES)
    description      = models.TextField(blank=True)

    capex_estimate            = models.FloatField(default=0.0)
    opex_change                = models.FloatField(default=0.0, help_text='Positive = OPEX increases, negative = OPEX decreases.')
    estimated_loss_avoided      = models.FloatField(default=0.0)
    estimated_value_recovered   = models.FloatField(default=0.0)
    estimated_annual_savings    = models.FloatField(default=0.0)
    estimated_payback_months    = models.FloatField(null=True, blank=True)
    implementation_time        = models.CharField(max_length=60, blank=True)

    technical_readiness = models.CharField(max_length=15, choices=READINESS_CHOICES, default='not_ready')
    finance_readiness    = models.CharField(max_length=15, choices=READINESS_CHOICES, default='not_ready')
    mrv_readiness        = models.CharField(max_length=15, choices=READINESS_CHOICES, default='not_ready')
    risk_level           = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES, default='medium')
    status               = models.CharField(max_length=15, choices=INTERVENTION_STATUS_CHOICES, default='proposed')

    class Meta:
        ordering            = ['operational_loss', 'id']
        verbose_name        = 'Intervention Option'
        verbose_name_plural = 'Intervention Options'

    def __str__(self):
        return f'{self.title} ({self.get_intervention_type_display()})'


class InterventionScenario(models.Model):
    """A sensitivity variant (base/upside/downside) of one InterventionOption."""
    intervention    = models.ForeignKey(InterventionOption, on_delete=models.CASCADE, related_name='scenarios')
    scenario_name   = models.CharField(max_length=120)
    scenario_type   = models.CharField(max_length=30, choices=INTERVENTION_TYPE_CHOICES)

    capex           = models.FloatField(default=0.0)
    opex            = models.FloatField(default=0.0)
    annual_savings  = models.FloatField(default=0.0)
    loss_avoided    = models.FloatField(default=0.0)
    value_recovered  = models.FloatField(default=0.0)
    payback          = models.FloatField(null=True, blank=True)
    sensitivity_case = models.CharField(max_length=10, choices=SENSITIVITY_CASE_CHOICES, default='base')
    assumptions      = models.JSONField(default=list, blank=True)
    risk_flags        = models.JSONField(default=list, blank=True)

    class Meta:
        ordering            = ['intervention', 'id']
        verbose_name        = 'Intervention Scenario'
        verbose_name_plural = 'Intervention Scenarios'

    def __str__(self):
        return f'{self.scenario_name} ({self.get_sensitivity_case_display()}) — {self.intervention.title}'


class FundingGap(models.Model):
    """The capital-required-vs-available analysis for one InterventionOption."""
    intervention = models.OneToOneField(InterventionOption, on_delete=models.CASCADE, related_name='funding_gap')

    total_capital_required            = models.FloatField(default=0.0)
    owner_contribution                = models.FloatField(default=0.0)
    committed_capital                  = models.FloatField(default=0.0)
    grant_potential                    = models.FloatField(default=0.0)
    debt_potential                     = models.FloatField(default=0.0)
    equity_potential                   = models.FloatField(default=0.0)
    supplier_finance_potential          = models.FloatField(default=0.0)
    impact_finance_potential            = models.FloatField(default=0.0)
    islamic_finance_review_potential     = models.FloatField(default=0.0)
    remaining_gap                      = models.FloatField(default=0.0)
    currency                          = models.CharField(max_length=10, default='GBP')
    status                            = models.CharField(max_length=15, choices=FUNDING_GAP_STATUS_CHOICES, default='draft')

    class Meta:
        verbose_name        = 'Funding Gap'
        verbose_name_plural = 'Funding Gaps'

    def __str__(self):
        return f'Funding gap for {self.intervention.title}'


class CapitalRouteMatch(models.Model):
    """One candidate capital route matched against a FundingGap. Matching is not approval."""
    funding_gap  = models.ForeignKey(FundingGap, on_delete=models.CASCADE, related_name='route_matches')
    route_type    = models.CharField(max_length=30, choices=ROUTE_TYPE_CHOICES)
    organisation  = models.CharField(max_length=200, blank=True)
    suitability_score = models.FloatField(default=50.0)
    match_reason  = models.TextField(blank=True)

    eligibility_status      = models.CharField(max_length=15, choices=ELIGIBILITY_STATUS_CHOICES, default='needs_review')
    due_diligence_status     = models.CharField(max_length=15, choices=DUE_DILIGENCE_STATUS_CHOICES, default='not_started')
    human_approval_required  = models.BooleanField(default=True)
    human_approved            = models.BooleanField(null=True, blank=True)
    outreach_status          = models.CharField(max_length=25, choices=OUTREACH_STATUS_CHOICES, default='not_started')

    class Meta:
        ordering            = ['funding_gap', '-suitability_score']
        verbose_name        = 'Capital Route Match'
        verbose_name_plural = 'Capital Route Matches'

    def __str__(self):
        return f'{self.get_route_type_display()} for {self.funding_gap.intervention.title}'


class CapitalAllocationDecision(models.Model):
    """A governed, ranked capital-allocation candidate — the output of rank_capital_allocation_options()."""
    organisation = models.CharField(max_length=200, blank=True)
    project      = models.CharField(max_length=200, blank=True)
    intervention  = models.ForeignKey(InterventionOption, on_delete=models.CASCADE, related_name='allocation_decisions')
    council_case  = models.ForeignKey('ai_agent_council.CouncilRun', on_delete=models.SET_NULL, null=True, blank=True, related_name='waste_to_value_decisions')

    decision = models.TextField(blank=True)
    ranking  = models.PositiveIntegerField(null=True, blank=True)

    financial_return_score   = models.FloatField(default=0.0)
    loss_avoidance_score      = models.FloatField(default=0.0)
    capital_efficiency_score  = models.FloatField(default=0.0)
    risk_score                = models.FloatField(default=0.0)
    verified_impact_score      = models.FloatField(default=0.0)
    maqasid_mizan_score        = models.FloatField(default=0.0)
    confidence                = models.FloatField(null=True, blank=True)

    conditions               = models.JSONField(default=list, blank=True)
    human_approval_required   = models.BooleanField(default=True)
    approval_status           = models.CharField(max_length=25, choices=APPROVAL_STATUS_CHOICES, default='pending')
    created_at                = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering            = ['ranking', '-created_at']
        verbose_name        = 'Capital Allocation Decision'
        verbose_name_plural = 'Capital Allocation Decisions'

    def __str__(self):
        return f'{self.intervention.title} — {self.get_approval_status_display()}'


class VerifiedCapitalOutcome(models.Model):
    """The real, MRV-verified outcome of an implemented CapitalAllocationDecision."""
    decision      = models.OneToOneField(CapitalAllocationDecision, on_delete=models.CASCADE, related_name='verified_outcome')
    intervention   = models.ForeignKey(InterventionOption, on_delete=models.CASCADE, related_name='verified_outcomes')

    capex_actual         = models.FloatField(null=True, blank=True)
    opex_actual           = models.FloatField(null=True, blank=True)
    loss_avoided_actual    = models.FloatField(null=True, blank=True)
    value_recovered_actual = models.FloatField(null=True, blank=True)
    savings_actual        = models.FloatField(null=True, blank=True)
    payback_actual        = models.FloatField(null=True, blank=True)

    mrv_status        = models.CharField(max_length=20, choices=MRV_STATUS_CHOICES, default='not_started')
    evidence_quality   = models.CharField(max_length=10, choices=EVIDENCE_QUALITY_CHOICES, default='medium')
    verified_status    = models.CharField(max_length=10, choices=VERIFIED_STATUS_CHOICES, default='estimated')
    public_reporting_ready = models.BooleanField(default=False)
    next_capital_allocation_signal = models.TextField(blank=True)

    class Meta:
        verbose_name        = 'Verified Capital Outcome'
        verbose_name_plural = 'Verified Capital Outcomes'

    def __str__(self):
        return f'Verified outcome for {self.intervention.title} ({self.get_verified_status_display()})'
