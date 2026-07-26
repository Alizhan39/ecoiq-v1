"""
global_research/models.py — the Global Research, Technology & Manufacturer
Discovery Engine.

Reuses (never redefines): `digital_twin`'s asset/twin/component/process/
loss/data-gap models as mission origins and `Unit` for quantities;
`capability_graph.Organisation`/`OrganisationCapability` as the
manufacturer/supplier identity and evidence-backed capability-claim graph;
`evidence_memory.EvidenceMemory` as the semantic-search layer (every
accepted ResearchSource/ResearchClaim writes a companion row there, keyed
by the same `source_reference` soft-pointer convention); `ai_agent_council`
for the Research Council; `backend_intelligence_engine.BackgroundTaskRun`
for job observability. See docs/global_research_existing_system_audit.md
and docs/adr/ADR-global-research-engine.md.

Thirteen distinct concepts, never collapsed into one generic "solution"
record: problem (ResearchMission) -> requirement (TechnicalRequirement) ->
technology category (TechnologyCategory) -> technology (TechnologyCandidate)
-> product (ProductCandidate) -> manufacturer (ManufacturerProfile) ->
distributor/integrator (SupplierOrIntegratorProfile) -> academic/research
source (ResearchSource, source_type) -> claimed result (ResearchClaim) ->
independently verified evidence (ClaimAssessment) -> EcoIQ recommendation
(ResearchRecommendation) -> human-approved decision (ResearchHumanDecision).
"""
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from digital_twin.models import TimeStampedModel

from global_research.constants import (
    COMPATIBILITY_STATUS_CHOICES, EVIDENCE_TIER_CHOICES, LANGUAGE_CHOICES,
    SOURCE_OWNER_TYPE_CHOICES, SOURCE_TYPE_CHOICES, VERIFICATION_STATUS_CHOICES,
)


# ── Research Mission ──────────────────────────────────────────────────────────

MISSION_STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('defining', 'Defining'),
    ('approved_for_research', 'Approved For Research'),
    ('searching', 'Searching'),
    ('extracting', 'Extracting'),
    ('evaluating', 'Evaluating'),
    ('incomplete', 'Incomplete'),
    ('ready_for_review', 'Ready For Review'),
    ('shortlisted', 'Shortlisted'),
    ('closed', 'Closed'),
    ('archived', 'Archived'),
]

RESEARCH_READY_STATUSES = {
    'approved_for_research', 'searching', 'extracting', 'evaluating',
    'incomplete', 'ready_for_review', 'shortlisted',
}

PRIORITY_CHOICES = [('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')]

EVIDENCE_LEVEL_CHOICES = [
    ('exploratory', 'Exploratory'),
    ('standard', 'Standard'),
    ('capital_grade', 'Capital-Grade'),
]


class ResearchMission(TimeStampedModel):
    """A structured research task. Must originate from a real, already-
    governed EcoIQ entity — never a bare free-text prompt. Enforced by
    `services.orchestrator.validate_mission_readiness()`, not just a UI
    convention: at least one origin FK below must be set."""
    asset = models.ForeignKey('digital_twin.IndustrialAsset', on_delete=models.SET_NULL, null=True, blank=True, related_name='research_missions')
    twin = models.ForeignKey('digital_twin.DigitalTwin', on_delete=models.SET_NULL, null=True, blank=True, related_name='research_missions')
    component = models.ForeignKey('digital_twin.TwinComponent', on_delete=models.SET_NULL, null=True, blank=True, related_name='research_missions')
    process_node = models.ForeignKey('digital_twin.ProcessNode', on_delete=models.SET_NULL, null=True, blank=True, related_name='research_missions')
    loss_detection = models.ForeignKey('digital_twin.LossDetection', on_delete=models.SET_NULL, null=True, blank=True, related_name='research_missions')
    data_gap = models.ForeignKey('digital_twin.TwinDataGap', on_delete=models.SET_NULL, null=True, blank=True, related_name='research_missions')

    title = models.CharField(max_length=255)
    problem_statement = models.TextField()
    desired_outcome = models.TextField(blank=True)
    scope = models.TextField(blank=True)
    industry = models.CharField(max_length=150, blank=True)
    country_of_deployment = models.CharField(max_length=100, blank=True)
    target_countries = models.JSONField(
        default=list, blank=True,
        help_text='ISO country codes to search for technology/manufacturers in. Empty = no default preference, search globally.',
    )
    technical_constraints = models.TextField(blank=True)
    financial_constraints = models.TextField(blank=True)
    environmental_constraints = models.TextField(blank=True)
    worker_safety_constraints = models.TextField(blank=True)
    stewardship_constraints = models.TextField(blank=True)
    required_evidence_level = models.CharField(max_length=15, choices=EVIDENCE_LEVEL_CHOICES, default='standard')

    status = models.CharField(max_length=25, choices=MISSION_STATUS_CHOICES, default='draft')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Research Mission'
        verbose_name_plural = 'Research Missions'

    def __str__(self):
        return self.title

    @property
    def has_valid_origin(self):
        return any([self.asset_id, self.twin_id, self.component_id, self.process_node_id,
                    self.loss_detection_id, self.data_gap_id])


class TechnicalRequirement(TimeStampedModel):
    """Translates the operational problem into a supplier-neutral,
    measurable requirement. Versioned: editing an approved requirement
    bumps `version` rather than silently mutating it (enforced in
    services/requirements.py)."""
    REQUIREMENT_TYPE_CHOICES = [
        ('capacity', 'Capacity'), ('temperature', 'Temperature'), ('efficiency', 'Efficiency'),
        ('material_compatibility', 'Material Compatibility'), ('electrical', 'Electrical'),
        ('certification', 'Certification'), ('throughput', 'Throughput'), ('service_life', 'Service Life'),
        ('spare_parts_availability', 'Spare-Parts Availability'), ('installation_downtime', 'Installation Downtime'),
        ('emissions', 'Emissions'), ('worker_exposure', 'Worker Exposure'), ('water_use', 'Water Use'),
        ('hazardous_area', 'Hazardous-Area Certification'), ('communications', 'Communications Protocol'),
        ('other', 'Other'),
    ]
    VERIFICATION_METHOD_CHOICES = [
        ('datasheet', 'Datasheet'), ('independent_test', 'Independent Test'),
        ('site_measurement', 'Site Measurement'), ('certification', 'Certification'),
        ('vendor_declaration', 'Vendor Declaration'), ('other', 'Other'),
    ]

    mission = models.ForeignKey(ResearchMission, on_delete=models.CASCADE, related_name='requirements')
    requirement_type = models.CharField(max_length=30, choices=REQUIREMENT_TYPE_CHOICES, default='other')
    description = models.TextField()
    metric = models.CharField(max_length=150, blank=True)
    minimum_value = models.FloatField(null=True, blank=True)
    preferred_value = models.FloatField(null=True, blank=True)
    maximum_value = models.FloatField(null=True, blank=True)
    unit = models.ForeignKey('digital_twin.Unit', on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    is_mandatory = models.BooleanField(default=True)
    verification_method = models.CharField(max_length=20, choices=VERIFICATION_METHOD_CHOICES, default='other')
    evidence_requirement = models.TextField(blank=True)
    rationale = models.TextField(blank=True)
    source_loss = models.ForeignKey('digital_twin.LossDetection', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    source_metric = models.ForeignKey('digital_twin.OperationalMetric', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    confidence = models.FloatField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    approved = models.BooleanField(default=False)

    class Meta:
        ordering = ['mission', '-is_mandatory', 'requirement_type']
        verbose_name = 'Technical Requirement'
        verbose_name_plural = 'Technical Requirements'

    def __str__(self):
        return f'{self.get_requirement_type_display()}: {self.description[:60]}'


class ResearchQueryPlan(TimeStampedModel):
    """How a mission will be researched — multilingual by design (languages
    is a list of codes, never assumed to be English-only)."""
    FRESHNESS_CHOICES = [('high', 'High'), ('medium', 'Medium'), ('stable', 'Stable')]

    mission = models.ForeignKey(ResearchMission, on_delete=models.CASCADE, related_name='query_plans')
    research_questions = models.JSONField(default=list, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    synonyms = models.JSONField(default=list, blank=True)
    industry_terminology = models.JSONField(default=list, blank=True)
    languages = models.JSONField(default=list, blank=True, help_text='e.g. ["en", "ru", "kk", "zh"].')
    country_filters = models.JSONField(default=list, blank=True)
    source_type_priorities = models.JSONField(default=list, blank=True)
    exclusion_rules = models.JSONField(default=list, blank=True)
    date_range_start = models.DateField(null=True, blank=True)
    date_range_end = models.DateField(null=True, blank=True)
    freshness_requirement = models.CharField(max_length=10, choices=FRESHNESS_CHOICES, default='medium')
    evidence_standard = models.CharField(max_length=15, choices=EVIDENCE_LEVEL_CHOICES, default='standard')
    generated_by = models.CharField(max_length=100, blank=True, default='system')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['mission', '-version']
        verbose_name = 'Research Query Plan'
        verbose_name_plural = 'Research Query Plans'

    def __str__(self):
        return f'Query plan v{self.version} for {self.mission.title}'


# ── Sources and claims ────────────────────────────────────────────────────────

class ResearchSource(TimeStampedModel):
    """A discovered source. Stores metadata + a bounded permitted extract —
    never full copyrighted source text (see docs/research_evidence_methodology.md §1)."""
    STATUS_CHOICES = [
        ('candidate', 'Candidate'), ('accepted', 'Accepted'),
        ('rejected', 'Rejected'), ('superseded', 'Superseded'),
    ]
    FRESHNESS_CLASS_CHOICES = [
        ('current', 'Current'), ('stable', 'Stable'), ('stale', 'Stale'), ('unknown', 'Unknown'),
    ]

    mission = models.ForeignKey(ResearchMission, on_delete=models.CASCADE, related_name='sources')
    title = models.CharField(max_length=500)
    source_type = models.CharField(max_length=30, choices=SOURCE_TYPE_CHOICES)
    publisher = models.CharField(max_length=255, blank=True)
    author = models.CharField(max_length=255, blank=True)
    publication_date = models.DateField(null=True, blank=True)
    jurisdiction = models.CharField(max_length=150, blank=True)
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    url = models.URLField(max_length=2000, blank=True)
    document_reference = models.CharField(max_length=255, blank=True, help_text='Non-URL identifier, e.g. patent number, standard code, DOI.')
    access_date = models.DateField(default=timezone.now)
    licence_or_usage_note = models.TextField(blank=True)
    source_owner_type = models.CharField(max_length=15, choices=SOURCE_OWNER_TYPE_CHOICES, default='unknown')
    vendor_affiliation = models.CharField(max_length=255, blank=True)
    evidence_tier = models.CharField(max_length=1, choices=EVIDENCE_TIER_CHOICES, default='D')
    freshness_classification = models.CharField(max_length=10, choices=FRESHNESS_CLASS_CHOICES, default='unknown')
    permitted_extract = models.TextField(blank=True, help_text='Short extract stored within licence limits — never the full source text.')
    content_hash = models.CharField(max_length=64, blank=True, editable=False)
    independently_reproduced = models.BooleanField(default=False)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='candidate')
    dedup_key = models.CharField(max_length=300, db_index=True, blank=True, editable=False)
    provider_name = models.CharField(max_length=100, blank=True, help_text='Which ResearchProvider discovered this source.')

    class Meta:
        ordering = ['mission', '-evidence_tier', '-publication_date']
        verbose_name = 'Research Source'
        verbose_name_plural = 'Research Sources'
        constraints = [
            models.UniqueConstraint(fields=['mission', 'dedup_key'], name='uniq_research_source_dedup_key'),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        import hashlib
        if not self.dedup_key:
            key_source = self.url or f'{self.title}::{self.publisher}'
            self.dedup_key = hashlib.sha1(slugify(key_source)[:250].encode('utf-8')).hexdigest()
        self.content_hash = hashlib.sha256(self.permitted_extract.encode('utf-8')).hexdigest() if self.permitted_extract else ''
        super().save(*args, **kwargs)

    @property
    def evidence_memory_reference(self):
        return f'global_research.ResearchSource:{self.pk}'


class ResearchClaim(TimeStampedModel):
    """A structured statement extracted from a source. Retains operating
    conditions — a claim without conditions is never treated as universally
    applicable (see docs/research_evidence_methodology.md §2)."""
    CLAIM_TYPE_CHOICES = [
        ('performance', 'Performance'), ('capability', 'Capability'), ('certification', 'Certification'),
        ('availability', 'Availability'), ('service_coverage', 'Service Coverage'), ('cost', 'Cost'),
        ('compliance', 'Compliance'), ('technology_readiness', 'Technology Readiness'), ('other', 'Other'),
    ]
    EXTRACTION_METHOD_CHOICES = [
        ('rule_based', 'Rule-Based'), ('manual', 'Manual'), ('provider_structured_field', 'Provider Structured Field'),
    ]
    CONTRADICTION_STATUS_CHOICES = [('none', 'None'), ('unresolved', 'Unresolved'), ('resolved', 'Resolved')]

    source = models.ForeignKey(ResearchSource, on_delete=models.CASCADE, related_name='claims')
    mission = models.ForeignKey(ResearchMission, on_delete=models.CASCADE, related_name='claims')
    claim_type = models.CharField(max_length=25, choices=CLAIM_TYPE_CHOICES, default='other')
    subject = models.CharField(max_length=255, help_text='e.g. "Heat Pump Model X".')
    predicate = models.CharField(max_length=255, help_text='e.g. "has_COP", "is_certified_for".')
    object_value = models.CharField(max_length=500, help_text='The claimed value as text.')
    numeric_value = models.FloatField(null=True, blank=True)
    unit = models.ForeignKey('digital_twin.Unit', on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    conditions = models.JSONField(default=dict, blank=True, help_text='Operating conditions this claim holds under, e.g. {"ambient_temp_c": 7}. Empty = not stated.')
    quoted_extract = models.TextField(blank=True)
    source_location = models.CharField(max_length=255, blank=True)
    extraction_method = models.CharField(max_length=30, choices=EXTRACTION_METHOD_CHOICES, default='rule_based')
    vendor_provided = models.BooleanField(default=False)
    verified = models.BooleanField(default=False)
    confidence = models.FloatField(null=True, blank=True)
    contradiction_status = models.CharField(max_length=12, choices=CONTRADICTION_STATUS_CHOICES, default='none')
    created_by_agent = models.CharField(max_length=100, blank=True, default='claim_extraction_service')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    class Meta:
        ordering = ['mission', 'subject', 'predicate']
        verbose_name = 'Research Claim'
        verbose_name_plural = 'Research Claims'

    def __str__(self):
        return f'{self.subject} {self.predicate} {self.object_value}'

    @property
    def has_conditions(self):
        return bool(self.conditions)

    @property
    def evidence_memory_reference(self):
        return f'global_research.ResearchClaim:{self.pk}'


class ClaimAssessment(TimeStampedModel):
    """Deterministic trustworthiness evaluation of one claim — see
    docs/research_evidence_methodology.md §3 for the exact formula."""
    claim = models.OneToOneField(ResearchClaim, on_delete=models.CASCADE, related_name='assessment')
    source_authority_score = models.FloatField()
    methodological_quality_score = models.FloatField()
    independence_score = models.FloatField()
    reproducibility_score = models.FloatField()
    recency_score = models.FloatField()
    applicability_score = models.FloatField()
    contradiction_penalty = models.FloatField(default=0.0)
    overall_evidence_score = models.FloatField()
    rationale = models.TextField(blank=True)
    formula_version = models.CharField(max_length=20, default='1.0.0')
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    status = models.CharField(max_length=15, choices=[('draft', 'Draft'), ('human_reviewed', 'Human Reviewed')], default='draft')

    class Meta:
        verbose_name = 'Claim Assessment'
        verbose_name_plural = 'Claim Assessments'

    def __str__(self):
        return f'Evidence score {self.overall_evidence_score} — {self.claim}'


# ── Technology, manufacturer, product ─────────────────────────────────────────

class TechnologyCategory(TimeStampedModel):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    taxonomy_parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')
    industry_applicability = models.JSONField(default=list, blank=True)
    process_applicability = models.JSONField(default=list, blank=True)
    maturity_range = models.CharField(max_length=100, blank=True, help_text='e.g. "TRL 6-9".')
    description = models.TextField(blank=True)
    known_risks = models.TextField(blank=True)
    stewardship_considerations = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Technology Category'
        verbose_name_plural = 'Technology Categories'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class TechnologyCandidate(TimeStampedModel):
    """A specific technical approach — not necessarily a commercial
    product. A ProductCandidate is a specific commercial instance of one."""
    STATUS_CHOICES = [
        ('discovered', 'Discovered'), ('under_evaluation', 'Under Evaluation'),
        ('insufficient_evidence', 'Insufficient Evidence'), ('technically_relevant', 'Technically Relevant'),
        ('incompatible', 'Incompatible'), ('shortlisted', 'Shortlisted'), ('rejected', 'Rejected'),
    ]
    MATURITY_CHOICES = [
        ('concept', 'Concept'), ('pilot', 'Pilot'),
        ('early_commercial', 'Early Commercial'), ('mature_commercial', 'Mature Commercial'),
    ]

    mission = models.ForeignKey(ResearchMission, on_delete=models.CASCADE, related_name='technology_candidates')
    category = models.ForeignKey(TechnologyCategory, on_delete=models.PROTECT, related_name='candidates')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    technology_readiness_level = models.PositiveSmallIntegerField(null=True, blank=True, help_text='TRL 1-9.')
    commercial_maturity = models.CharField(max_length=20, choices=MATURITY_CHOICES, default='pilot')
    relevant_process_node = models.ForeignKey('digital_twin.ProcessNode', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    technical_mechanism = models.TextField(blank=True)
    expected_benefits = models.TextField(blank=True)
    limitations = models.TextField(blank=True)
    required_infrastructure = models.TextField(blank=True)
    environmental_implications = models.TextField(blank=True)
    worker_implications = models.TextField(blank=True)
    deployment_complexity = models.CharField(max_length=10, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='medium')
    source_claims = models.ManyToManyField(ResearchClaim, blank=True, related_name='supported_technology_candidates')
    evidence_score = models.FloatField(null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='discovered')

    class Meta:
        ordering = ['mission', '-evidence_score']
        verbose_name = 'Technology Candidate'
        verbose_name_plural = 'Technology Candidates'

    def __str__(self):
        return self.name


class ManufacturerProfile(TimeStampedModel):
    """A thin companion profile on the real, deduplicated
    `capability_graph.Organisation` node — never a second organisation
    directory (see ADR decision 2)."""
    COMPANY_TYPE_CHOICES = [
        ('oem', 'OEM'), ('technology_developer', 'Technology Developer'),
        ('research_spinout', 'Research Spin-Out'), ('other', 'Other'),
    ]
    SANCTIONS_STATUS_CHOICES = [
        ('not_screened', 'Not Screened'), ('no_evidence_of_concern', 'No Evidence Of Concern'),
        ('unresolved_concern', 'Unresolved Concern'), ('confirmed_concern', 'Confirmed Concern'),
        ('blocked', 'Blocked'),
    ]

    organisation = models.OneToOneField('capability_graph.Organisation', on_delete=models.CASCADE, related_name='manufacturer_profile')
    headquarters_country = models.CharField(max_length=100, blank=True)
    operating_countries = models.JSONField(default=list, blank=True)
    company_type = models.CharField(max_length=25, choices=COMPANY_TYPE_CHOICES, default='oem')
    manufacturer_categories = models.ManyToManyField(TechnologyCategory, blank=True, related_name='manufacturers')
    ownership_information = models.TextField(blank=True)
    certifications = models.JSONField(default=list, blank=True, help_text='[{name, issuer, valid_until, evidence_reference}]')
    service_regions = models.JSONField(default=list, blank=True)
    languages = models.JSONField(default=list, blank=True)
    public_contact_channels = models.JSONField(default=list, blank=True)
    evidence_references = models.JSONField(default=list, blank=True)
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default='unverified')
    sanctions_screening_status = models.CharField(max_length=25, choices=SANCTIONS_STATUS_CHOICES, default='not_screened')

    class Meta:
        ordering = ['organisation__name']
        verbose_name = 'Manufacturer Profile'
        verbose_name_plural = 'Manufacturer Profiles'

    def __str__(self):
        return self.organisation.name


class SupplierOrIntegratorProfile(TimeStampedModel):
    """Distributor / reseller / engineering contractor / EPC / systems
    integrator / maintenance provider / research partner / university /
    laboratory — deliberately distinct from ManufacturerProfile even though
    both are companion profiles on the same Organisation model."""
    ROLE_TYPE_CHOICES = [
        ('distributor', 'Distributor'), ('reseller', 'Reseller'),
        ('engineering_contractor', 'Engineering Contractor'), ('epc_contractor', 'EPC Contractor'),
        ('systems_integrator', 'Systems Integrator'), ('maintenance_provider', 'Maintenance Provider'),
        ('research_partner', 'Research Partner'), ('university', 'University'), ('laboratory', 'Laboratory'),
    ]

    organisation = models.OneToOneField('capability_graph.Organisation', on_delete=models.CASCADE, related_name='supplier_integrator_profile')
    role_type = models.CharField(max_length=25, choices=ROLE_TYPE_CHOICES)
    region = models.CharField(max_length=150, blank=True)
    industries_served = models.JSONField(default=list, blank=True)
    capabilities = models.JSONField(default=list, blank=True)
    certifications = models.JSONField(default=list, blank=True)
    supported_manufacturers = models.ManyToManyField(ManufacturerProfile, blank=True, related_name='supporting_integrators')
    service_coverage = models.JSONField(default=list, blank=True)
    evidence_references = models.JSONField(default=list, blank=True)
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default='unverified')

    class Meta:
        ordering = ['organisation__name']
        verbose_name = 'Supplier / Integrator Profile'
        verbose_name_plural = 'Supplier / Integrator Profiles'

    def __str__(self):
        return f'{self.organisation.name} ({self.get_role_type_display()})'


COST_TYPE_CHOICES = [
    ('list_price', 'Published List Price'),
    ('budget_estimate', 'Budget Estimate'),
    ('supplier_quotation', 'Supplier Quotation'),
    ('historical_procurement_price', 'Historical Procurement Price'),
    ('analyst_estimate', 'Analyst Estimate'),
    ('ecoiq_assumption', 'EcoIQ Assumption'),
    ('unavailable', 'Unavailable'),
]


class ProductCandidate(TimeStampedModel):
    """A specific commercial product, model, or service offering."""
    STATUS_CHOICES = [('active', 'Active'), ('discontinued', 'Discontinued'), ('upcoming', 'Upcoming'), ('unknown', 'Unknown')]
    LIFECYCLE_CHOICES = [('new', 'New'), ('established', 'Established'), ('end_of_life', 'End Of Life'), ('unknown', 'Unknown')]

    manufacturer = models.ForeignKey(ManufacturerProfile, on_delete=models.CASCADE, related_name='products')
    technology_candidate = models.ForeignKey(TechnologyCandidate, on_delete=models.CASCADE, related_name='products')
    product_name = models.CharField(max_length=255)
    model = models.CharField(max_length=150, blank=True)
    product_category = models.ForeignKey(TechnologyCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='unknown')
    release_or_publication_date = models.DateField(null=True, blank=True)
    specification_version = models.CharField(max_length=50, blank=True)

    capacity_min = models.FloatField(null=True, blank=True)
    capacity_max = models.FloatField(null=True, blank=True)
    capacity_unit = models.ForeignKey('digital_twin.Unit', on_delete=models.PROTECT, null=True, blank=True, related_name='+')
    efficiency_values = models.JSONField(default=dict, blank=True)
    operating_limits = models.JSONField(default=dict, blank=True)
    input_requirements = models.JSONField(default=dict, blank=True)
    output_specifications = models.JSONField(default=dict, blank=True)
    dimensions = models.JSONField(default=dict, blank=True)

    # Commercial data — every amount carries its own provenance; nothing is
    # silently converted or presented as a number when it is actually a gap.
    indicative_cost = models.FloatField(null=True, blank=True)
    indicative_cost_type = models.CharField(max_length=30, choices=COST_TYPE_CHOICES, default='unavailable')
    cost_currency = models.CharField(max_length=10, blank=True)
    cost_date = models.DateField(null=True, blank=True)
    cost_tax_inclusive = models.BooleanField(null=True, blank=True)
    cost_delivery_inclusive = models.BooleanField(null=True, blank=True)
    cost_installation_inclusive = models.BooleanField(null=True, blank=True)
    cost_country = models.CharField(max_length=100, blank=True)
    cost_source = models.CharField(max_length=255, blank=True)
    cost_confidence = models.FloatField(null=True, blank=True)
    cost_assumptions = models.JSONField(default=list, blank=True, help_text='Explicit assumptions, only when indicative_cost_type is an estimate — never left implicit.')

    lead_time_claim = models.CharField(max_length=150, blank=True)
    warranty_claim = models.CharField(max_length=150, blank=True)
    certifications = models.JSONField(default=list, blank=True)
    service_requirements = models.TextField(blank=True)
    source_claims = models.ManyToManyField(ResearchClaim, blank=True, related_name='supported_product_candidates')
    evidence_score = models.FloatField(null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    lifecycle_status = models.CharField(max_length=15, choices=LIFECYCLE_CHOICES, default='unknown')
    geographical_availability = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['manufacturer', 'product_name']
        verbose_name = 'Product Candidate'
        verbose_name_plural = 'Product Candidates'

    def __str__(self):
        return f'{self.manufacturer.organisation.name} — {self.product_name}'


# ── Compatibility and comparison ──────────────────────────────────────────────

class CompatibilityAssessment(TimeStampedModel):
    """Deterministic mandatory/optional fit check. A candidate failing a
    mandatory requirement can never rank as recommended — enforced in
    services/comparison.py, not left to weight tuning."""
    mission = models.ForeignKey(ResearchMission, on_delete=models.CASCADE, related_name='compatibility_assessments')
    technology_candidate = models.ForeignKey(TechnologyCandidate, on_delete=models.CASCADE, null=True, blank=True, related_name='compatibility_assessments')
    product_candidate = models.ForeignKey(ProductCandidate, on_delete=models.CASCADE, null=True, blank=True, related_name='compatibility_assessments')
    target_asset = models.ForeignKey('digital_twin.IndustrialAsset', on_delete=models.CASCADE, related_name='+')
    target_component = models.ForeignKey('digital_twin.TwinComponent', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    target_process_node = models.ForeignKey('digital_twin.ProcessNode', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    mandatory_requirements_passed = models.JSONField(default=list, blank=True)
    mandatory_requirements_failed = models.JSONField(default=list, blank=True)
    optional_requirements_passed = models.JSONField(default=list, blank=True)
    infrastructure_changes_required = models.TextField(blank=True)
    local_standards_compatibility = models.CharField(max_length=20, choices=COMPATIBILITY_STATUS_CHOICES, default='insufficient_data')
    environmental_compatibility = models.CharField(max_length=20, choices=COMPATIBILITY_STATUS_CHOICES, default='insufficient_data')
    climate_compatibility = models.CharField(max_length=20, choices=COMPATIBILITY_STATUS_CHOICES, default='insufficient_data')
    feedstock_material_compatibility = models.CharField(max_length=20, choices=COMPATIBILITY_STATUS_CHOICES, default='insufficient_data')
    workforce_requirements = models.TextField(blank=True)
    maintenance_requirements = models.TextField(blank=True)
    spare_parts_considerations = models.TextField(blank=True)
    cybersecurity_implications = models.TextField(blank=True)
    data_integration_requirements = models.TextField(blank=True)
    estimated_integration_complexity = models.CharField(max_length=10, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='medium')

    mandatory_pass = models.BooleanField(default=False)
    optional_fit_score = models.FloatField(null=True, blank=True)
    evidence_quality = models.FloatField(null=True, blank=True)
    overall_status = models.CharField(max_length=20, choices=COMPATIBILITY_STATUS_CHOICES, default='insufficient_data')
    assessment_score = models.FloatField(null=True, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    blocking_issues = models.JSONField(default=list, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    evidence_references = models.JSONField(default=list, blank=True)
    formula_version = models.CharField(max_length=20, default='1.0.0')

    class Meta:
        ordering = ['mission', '-mandatory_pass', '-assessment_score']
        verbose_name = 'Compatibility Assessment'
        verbose_name_plural = 'Compatibility Assessments'

    def __str__(self):
        subject = self.product_candidate or self.technology_candidate
        return f'{subject} vs {self.target_asset.name}: {self.get_overall_status_display()}'


class ComparativeEvaluation(TimeStampedModel):
    """One candidate's scored row within a mission's comparison. Weights
    are versioned and stored per-row, never applied silently (see
    docs/research_evidence_methodology.md §5)."""
    mission = models.ForeignKey(ResearchMission, on_delete=models.CASCADE, related_name='comparative_evaluations')
    technology_candidate = models.ForeignKey(TechnologyCandidate, on_delete=models.CASCADE, null=True, blank=True, related_name='comparative_evaluations')
    product_candidate = models.ForeignKey(ProductCandidate, on_delete=models.CASCADE, null=True, blank=True, related_name='comparative_evaluations')
    compatibility_assessment = models.ForeignKey(CompatibilityAssessment, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    criteria_weights = models.JSONField(default=dict, blank=True)
    raw_scores = models.JSONField(default=dict, blank=True)
    normalised_scores = models.JSONField(default=dict, blank=True)
    evidence_score = models.FloatField(null=True, blank=True)
    missing_data = models.JSONField(default=list, blank=True)
    total_score = models.FloatField(null=True, blank=True)
    rank = models.PositiveIntegerField(null=True, blank=True)
    is_ranked = models.BooleanField(default=True, help_text='False when excluded from ranking due to a failed mandatory requirement.')
    formula_version = models.CharField(max_length=20, default='1.0.0')
    reviewer_status = models.CharField(max_length=15, choices=[('draft', 'Draft'), ('human_reviewed', 'Human Reviewed')], default='draft')

    class Meta:
        ordering = ['mission', 'rank']
        verbose_name = 'Comparative Evaluation'
        verbose_name_plural = 'Comparative Evaluations'

    def __str__(self):
        subject = self.product_candidate or self.technology_candidate
        return f'{subject}: score={self.total_score} rank={self.rank}'


class ResearchRecommendation(TimeStampedModel):
    """A governed conclusion — never itself a decision. See
    docs/research_evidence_methodology.md §6-7 for the AI/human boundary."""
    TYPE_CHOICES = [
        ('continue_research', 'Continue Research'), ('request_more_evidence', 'Request More Evidence'),
        ('run_technical_study', 'Run Technical Study'), ('request_quotation', 'Request Quotation'),
        ('conduct_site_visit', 'Conduct Site Visit'), ('run_pilot', 'Run Pilot'), ('reject', 'Reject'),
        ('shortlist_technology', 'Shortlist Technology'), ('shortlist_manufacturer', 'Shortlist Manufacturer'),
        ('create_supplier_neutral_scenario', 'Create Supplier-Neutral Scenario'),
    ]

    mission = models.ForeignKey(ResearchMission, on_delete=models.CASCADE, related_name='recommendations')
    recommendation_type = models.CharField(max_length=35, choices=TYPE_CHOICES)
    technology_candidate = models.ForeignKey(TechnologyCandidate, on_delete=models.SET_NULL, null=True, blank=True, related_name='recommendations')
    manufacturer = models.ForeignKey(ManufacturerProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='recommendations')
    product_candidate = models.ForeignKey(ProductCandidate, on_delete=models.SET_NULL, null=True, blank=True, related_name='recommendations')
    rationale = models.TextField()
    evidence_references = models.JSONField(default=list, blank=True)
    unresolved_questions = models.JSONField(default=list, blank=True)
    assumptions = models.JSONField(default=list, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    risk_flags = models.JSONField(default=list, blank=True)
    stewardship_flags = models.JSONField(default=list, blank=True)
    recommended_next_action = models.TextField(blank=True)
    human_approval_status = models.CharField(max_length=15, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending')
    created_scenario = models.ForeignKey('digital_twin.ModernisationScenario', on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    class Meta:
        ordering = ['mission', '-created_at']
        verbose_name = 'Research Recommendation'
        verbose_name_plural = 'Research Recommendations'

    def __str__(self):
        return f'{self.get_recommendation_type_display()} — {self.mission.title}'


# ── Contradictions, risk, job runs ─────────────────────────────────────────────

class ContradictionRecord(TimeStampedModel):
    """A detected disagreement between two claims — never averaged away
    (see docs/research_evidence_methodology.md §4)."""
    TYPE_CHOICES = [
        ('value_mismatch', 'Value Mismatch'), ('certification_conflict', 'Certification Conflict'),
        ('service_coverage_conflict', 'Service Coverage Conflict'), ('trl_conflict', 'TRL Conflict'),
        ('vendor_vs_independent', 'Vendor vs Independent'),
    ]
    RESOLUTION_CHOICES = [
        ('unresolved', 'Unresolved'), ('resolved_by_evidence', 'Resolved By Evidence'),
        ('resolved_by_human', 'Resolved By Human'),
    ]

    mission = models.ForeignKey(ResearchMission, on_delete=models.CASCADE, related_name='contradictions')
    claim_a = models.ForeignKey(ResearchClaim, on_delete=models.CASCADE, related_name='contradictions_as_a')
    claim_b = models.ForeignKey(ResearchClaim, on_delete=models.CASCADE, related_name='contradictions_as_b')
    contradiction_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    delta = models.FloatField(null=True, blank=True)
    explanation = models.TextField()
    resolution_status = models.CharField(max_length=25, choices=RESOLUTION_CHOICES, default='unresolved')
    resolution_notes = models.TextField(blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')

    class Meta:
        ordering = ['mission', '-created_at']
        verbose_name = 'Contradiction Record'
        verbose_name_plural = 'Contradiction Records'

    def __str__(self):
        return f'{self.claim_a} vs {self.claim_b} ({self.get_contradiction_type_display()})'


class SupplyChainRiskFlag(TimeStampedModel):
    RISK_TYPE_CHOICES = [
        ('supplier_concentration', 'Supplier Concentration'), ('single_country_dependency', 'Single-Country Dependency'),
        ('export_controls', 'Export Controls'), ('sanctions', 'Sanctions'),
        ('geopolitical_disruption', 'Geopolitical Disruption'), ('currency_risk', 'Currency Risk'),
        ('delivery_risk', 'Delivery Risk'), ('spare_parts_risk', 'Spare Parts Risk'),
        ('warranty_enforceability', 'Warranty Enforceability'), ('cybersecurity', 'Cybersecurity'),
        ('remote_access_risk', 'Remote-Access Risk'), ('data_sovereignty', 'Data Sovereignty'),
        ('ip_restrictions', 'IP Restrictions'), ('immature_technology', 'Immature Technology'),
        ('vendor_insolvency', 'Vendor Insolvency'), ('certification_gaps', 'Certification Gaps'),
        ('local_skills_shortage', 'Local Skills Shortage'),
    ]
    RESOLUTION_CHOICES = [
        ('open', 'Open'), ('acknowledged', 'Acknowledged'), ('mitigated', 'Mitigated'), ('accepted', 'Accepted'),
    ]

    mission = models.ForeignKey(ResearchMission, on_delete=models.CASCADE, related_name='risk_flags')
    manufacturer = models.ForeignKey(ManufacturerProfile, on_delete=models.CASCADE, null=True, blank=True, related_name='risk_flags')
    product_candidate = models.ForeignKey(ProductCandidate, on_delete=models.CASCADE, null=True, blank=True, related_name='risk_flags')
    risk_type = models.CharField(max_length=30, choices=RISK_TYPE_CHOICES)
    severity = models.CharField(max_length=10, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High')], default='medium')
    description = models.TextField()
    evidence_references = models.JSONField(default=list, blank=True)
    resolution_status = models.CharField(max_length=15, choices=RESOLUTION_CHOICES, default='open')

    class Meta:
        ordering = ['mission', '-severity']
        verbose_name = 'Supply Chain Risk Flag'
        verbose_name_plural = 'Supply Chain Risk Flags'

    def __str__(self):
        return f'{self.get_risk_type_display()} ({self.get_severity_display()})'


class ResearchRun(TimeStampedModel):
    """One orchestrator execution for a mission — mirrors
    `langgraph_orchestration.OrchestrationRun`, linked to
    `backend_intelligence_engine.BackgroundTaskRun` by `celery_task_id`
    rather than a hard FK (same soft-reference convention)."""
    STAGE_CHOICES = [
        ('validating', 'Validating'), ('planning', 'Planning'), ('searching', 'Searching'),
        ('deduplicating', 'Deduplicating'), ('extracting', 'Extracting'), ('evaluating', 'Evaluating'),
        ('comparing', 'Comparing'), ('completed', 'Completed'), ('failed', 'Failed'), ('cancelled', 'Cancelled'),
    ]

    mission = models.ForeignKey(ResearchMission, on_delete=models.CASCADE, related_name='runs')
    celery_task_id = models.CharField(max_length=155, blank=True, db_index=True)
    idempotency_key = models.CharField(max_length=64, db_index=True)
    stage = models.CharField(max_length=15, choices=STAGE_CHOICES, default='validating')
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    sources_found = models.PositiveIntegerField(default=0)
    sources_deduplicated = models.PositiveIntegerField(default=0)
    claims_extracted = models.PositiveIntegerField(default=0)
    contradictions_found = models.PositiveIntegerField(default=0)
    candidates_created = models.PositiveIntegerField(default=0)
    error_summary = models.TextField(blank=True)
    log = models.JSONField(default=list, blank=True, help_text='[{event, detail, ts}] structured event trail.')

    class Meta:
        ordering = ['-started_at']
        verbose_name = 'Research Run'
        verbose_name_plural = 'Research Runs'

    def __str__(self):
        return f'{self.mission.title} — {self.get_stage_display()}'


# ── Human governance ───────────────────────────────────────────────────────────

class ResearchDocumentDraft(TimeStampedModel):
    """A draft-only RFI/RFQ/etc. Follows `outreach_readiness`'s exact
    versioned-and-immutable-once-approved shape — no send/transport
    function is ever imported anywhere in this app."""
    DOCUMENT_TYPE_CHOICES = [
        ('rfi', 'Request For Information'), ('rfq', 'Request For Quotation'),
        ('technical_questionnaire', 'Technical Questionnaire'), ('site_data_request', 'Site Data Request'),
        ('supplier_evidence_checklist', 'Supplier Evidence Checklist'), ('pilot_proposal', 'Pilot Proposal'),
        ('comparison_matrix', 'Comparison Matrix'),
    ]

    mission = models.ForeignKey(ResearchMission, on_delete=models.CASCADE, related_name='document_drafts')
    document_type = models.CharField(max_length=30, choices=DOCUMENT_TYPE_CHOICES)
    version = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=255)
    shareable_context = models.TextField(blank=True, help_text='Only the asset context explicitly authorised to share — never raw Digital Twin data.')
    requirements_included = models.JSONField(default=list, blank=True)
    evidence_requested = models.JSONField(default=list, blank=True)
    commercial_questions = models.JSONField(default=list, blank=True)
    delivery_service_questions = models.JSONField(default=list, blank=True)
    cybersecurity_data_questions = models.JSONField(default=list, blank=True)
    certification_questions = models.JSONField(default=list, blank=True)
    stewardship_worker_safety_questions = models.JSONField(default=list, blank=True)
    body_text = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=[('draft', 'Draft'), ('approved', 'Approved'), ('superseded', 'Superseded')], default='draft')
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['mission', 'document_type', '-version']
        verbose_name = 'Research Document Draft'
        verbose_name_plural = 'Research Document Drafts'

    def __str__(self):
        return f'{self.get_document_type_display()} v{self.version} — {self.title}'


RESEARCH_DECISION_CHOICES = [
    ('approved', 'Approved'), ('approved_with_conditions', 'Approved with Conditions'),
    ('rejected', 'Rejected'), ('deferred', 'Deferred'),
]
REJECTION_REASON_CHOICES = [
    ('weak_evidence', 'Weak Evidence'), ('high_geopolitical_risk', 'High Geopolitical Risk'),
    ('no_local_maintenance', 'No Local Maintenance'), ('poor_compatibility', 'Poor Compatibility'),
    ('unacceptable_worker_impact', 'Unacceptable Worker Impact'), ('data_security_concern', 'Data Security Concern'),
    ('excessive_vendor_lock_in', 'Excessive Vendor Lock-In'), ('commercial_terms_unavailable', 'Commercial Terms Unavailable'),
    ('stewardship_concern', 'Stewardship Concern'), ('other', 'Other'),
]
DECISION_APPROVING_VALUES = {'approved', 'approved_with_conditions'}


class ResearchHumanDecision(TimeStampedModel):
    """A human's recorded decision at any of the 8 required review stages.
    `human_approved` is derived from `decision`, exactly like
    `digital_twin.HumanDecision` — never set independently."""
    STAGE_CHOICES = [
        ('mission_approval', 'Mission Approval'), ('requirements_approval', 'Requirements Approval'),
        ('candidate_review', 'Candidate Review'), ('technology_shortlist', 'Technology Shortlist'),
        ('manufacturer_shortlist', 'Manufacturer / Product Shortlist'),
        ('rfi_rfq_approval', 'RFI/RFQ Approval'), ('scenario_creation', 'Scenario Creation'),
        ('capital_allocation_promotion', 'Capital Allocation Promotion'),
    ]

    mission = models.ForeignKey(ResearchMission, on_delete=models.CASCADE, related_name='human_decisions')
    stage = models.CharField(max_length=30, choices=STAGE_CHOICES)
    technology_candidate = models.ForeignKey(TechnologyCandidate, on_delete=models.SET_NULL, null=True, blank=True, related_name='human_decisions')
    manufacturer = models.ForeignKey(ManufacturerProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='human_decisions')
    product_candidate = models.ForeignKey(ProductCandidate, on_delete=models.SET_NULL, null=True, blank=True, related_name='human_decisions')
    recommendation = models.ForeignKey(ResearchRecommendation, on_delete=models.SET_NULL, null=True, blank=True, related_name='human_decisions')
    document_draft = models.ForeignKey(ResearchDocumentDraft, on_delete=models.SET_NULL, null=True, blank=True, related_name='human_decisions')
    council_run = models.ForeignKey('ai_agent_council.CouncilRun', on_delete=models.SET_NULL, null=True, blank=True, related_name='global_research_decisions')

    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='global_research_decisions')
    reviewer_role = models.CharField(max_length=100, blank=True)
    decision = models.CharField(max_length=30, choices=RESEARCH_DECISION_CHOICES)
    rejection_reason = models.CharField(max_length=35, choices=REJECTION_REASON_CHOICES, blank=True)
    comments = models.TextField(blank=True)
    conditions = models.JSONField(default=list, blank=True)
    human_approved = models.BooleanField(null=True, blank=True, default=None)
    decided_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-decided_at']
        verbose_name = 'Research Human Decision'
        verbose_name_plural = 'Research Human Decisions'

    def __str__(self):
        return f'{self.get_stage_display()}: {self.get_decision_display()}'

    def save(self, *args, **kwargs):
        if self.decision in DECISION_APPROVING_VALUES:
            self.human_approved = True
        elif self.decision == 'rejected':
            self.human_approved = False
        else:
            self.human_approved = None
        super().save(*args, **kwargs)
