"""
khalifa_stewardship_tour_operating_system/models.py — EcoIQ's mission layer:
AI-planned, human-led, financed and verified stewardship tours.

Turns "travel should leave a place better than you found it" into a real
operating pipeline: Problem -> Evidence -> AI Agents -> Intervention ->
Funding -> Tour -> Human Participation -> MRV -> Legacy -> Next Tour.

Honesty note, enforced throughout this app's services and templates:
- estimated_benefit != verified outcome
- funding plan != funding secured
- sponsor interest != confirmed sponsor
- tour approved != technical installation authorised
No TourLegacyRecord is created until a tour has actually run and MRV has
verified the outcome — creating one earlier would silently turn a
projection into a completed result.
"""
from django.db import models
from django.utils import timezone

PIPELINE_STATUS_CHOICES = [
    ('draft',                 'Draft'),
    ('evidence_needed',        'Evidence Needed'),
    ('under_ai_review',        'Under AI Review'),
    ('council_review',         'Council Review'),
    ('approved_with_conditions', 'Approved with Conditions'),
    ('funding_needed',          'Funding Needed'),
    ('partner_due_diligence',    'Partner Due Diligence'),
    ('ready_to_launch',          'Ready to Launch'),
    ('active',                  'Active'),
    ('completed',                'Completed'),
    ('mrv_pending',              'MRV Pending'),
    ('verified_legacy',          'Verified Legacy'),
    ('blocked',                  'Blocked'),
]

TOUR_TYPE_CHOICES = [
    ('clean_heat',  'Clean Heat Tour'),
    ('mountain',    'Mountain Stewardship Tour'),
    ('lake_water',  'Lake & Water Stewardship Tour'),
    ('food_surplus', 'Food & Surplus Stewardship Tour'),
    ('greenhouse',  'Community Greenhouse Tour'),
    ('wildlife',    'Wildlife & Nature Restoration Tour'),
]

SAFETY_LEVEL_CHOICES = [
    ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'),
]

PROBLEM_TYPE_CHOICES = [
    ('coal_heating',       'Coal heating'),
    ('inefficient_heating', 'Inefficient heating'),
    ('heat_loss',           'Heat loss'),
    ('household_air_quality_risk', 'Household air quality risk'),
    ('energy_cost_burden',    'Energy cost burden'),
    ('trail_waste',           'Trail waste'),
    ('trail_erosion',         'Trail erosion'),
    ('damaged_trails',        'Damaged trails'),
    ('nature_degradation',     'Nature degradation'),
    ('water_pollution',        'Water pollution'),
    ('unsafe_access',          'Unsafe access'),
    ('unmanaged_tourism_impact', 'Unmanaged tourism impact'),
    ('food_surplus',           'Food surplus'),
    ('cold_chain_loss',         'Cold-chain loss'),
    ('food_waste',              'Meat/food waste'),
    ('community_need',           'Community need'),
    ('food_insecurity',          'Food insecurity'),
    ('underused_land',           'Underused land'),
    ('habitat_loss',             'Habitat loss'),
    ('biodiversity_risk',        'Biodiversity risk'),
    ('animal_welfare_concern',    'Animal welfare concern'),
]

EVIDENCE_QUALITY_CHOICES = [
    ('strong', 'Strong'), ('medium', 'Medium'), ('weak', 'Weak'), ('missing', 'Missing'),
]

PROBLEM_STATUS_CHOICES = [
    ('nominated', 'Nominated'), ('evidence_collected', 'Evidence Collected'),
    ('under_review', 'Under Review'), ('resolved', 'Resolved'),
]

INTERVENTION_TYPE_CHOICES = [
    ('clean_heating_upgrade',   'Clean heating upgrade'),
    ('insulation_support',       'Insulation support'),
    ('boiler_heat_pump_assessment', 'Boiler / heat pump / electric backup assessment'),
    ('smart_controls',           'Smart controls'),
    ('safety_review',            'Safety review'),
    ('guided_cleanup',            'Guided cleanup'),
    ('erosion_control_support',    'Erosion control support'),
    ('habitat_protection',          'Habitat protection'),
    ('ranger_expert_review',         'Local ranger / expert review'),
    ('shoreline_cleanup',             'Shoreline cleanup'),
    ('waste_mapping',                  'Waste mapping'),
    ('water_stewardship',               'Water stewardship'),
    ('community_awareness',              'Community awareness'),
    ('monitoring',                        'Monitoring'),
    ('surplus_prediction',                 'Surplus prediction'),
    ('safe_redistribution',                 'Safe redistribution where lawful'),
    ('cold_chain_support',                    'Cold-chain support'),
    ('community_kitchen_support',               'Community kitchen / food-bank support'),
    ('waste_to_value_routing',                    'Waste-to-value routing'),
    ('greenhouse_materials',                        'Greenhouse materials'),
    ('irrigation_support',                            'Irrigation support'),
    ('local_operator_setup',                            'Local operator setup'),
    ('training',                                          'Training'),
    ('production_monitoring',                               'Production monitoring'),
    ('habitat_restoration',                                   'Habitat restoration'),
    ('water_access_support',                                    'Water access support'),
    ('expert_guided_monitoring',                                  'Expert-guided monitoring'),
    ('no_harm_wildlife_protection',                                 'No-harm wildlife protection'),
]

COMPLEXITY_CHOICES = [
    ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'),
]

INTERVENTION_STATUS_CHOICES = [
    ('modelled', 'Modelled'), ('recommended', 'Recommended'),
    ('approved', 'Approved'), ('rejected', 'Rejected'),
]

FUNDING_STATUS_CHOICES = [
    ('draft', 'Draft'), ('under_review', 'Under Review'),
    ('funded', 'Funded'), ('gap_open', 'Gap Open'),
]

PARTNER_TYPE_CHOICES = [
    ('ngo', 'NGO'), ('cooperative', 'Cooperative'),
    ('municipality', 'Municipality'), ('business', 'Business'),
]

DUE_DILIGENCE_STATUS_CHOICES = [
    ('not_started', 'Not Started'), ('in_progress', 'In Progress'),
    ('passed', 'Passed'), ('failed', 'Failed'),
]

PARTNER_APPROVAL_STATUS_CHOICES = [
    ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
]

CONTACT_STATUS_CHOICES = [
    ('identified', 'Identified'), ('contacted', 'Contacted'), ('confirmed', 'Confirmed'),
]

MRV_VERIFICATION_STATUS_CHOICES = [
    ('not_started', 'Not Started'), ('baseline_collected', 'Baseline Collected'),
    ('after_data_pending', 'After-Data Pending'), ('verified', 'Verified'),
]

PUBLIC_PRIVATE_STATUS_CHOICES = [
    ('private', 'Private'), ('public', 'Public'),
]

# --- Real pilot readiness layer: TourBeneficiary / ConsentRecord / SupplierQuote
# / IncidentReport / LaunchChecklistItem, plus TourLocalPartner hardening fields. ---

BENEFICIARY_TYPE_CHOICES = [
    ('household', 'Household'), ('community', 'Community'),
    ('school', 'School'), ('other', 'Other'),
]

BENEFICIARY_CONSENT_STATUS_CHOICES = [
    ('not_started', 'Not Started'), ('partial', 'Partial'),
    ('complete', 'Complete'), ('withdrawn', 'Withdrawn'),
]

ELIGIBILITY_STATUS_CHOICES = [
    ('pending', 'Pending'), ('eligible', 'Eligible'), ('ineligible', 'Ineligible'),
]

INTAKE_STATUS_CHOICES = [
    ('identified', 'Identified'), ('contacted', 'Contacted'), ('intake_complete', 'Intake Complete'),
]

CONSENT_TYPE_CHOICES = [
    ('intervention',        'Intervention'),
    ('data_processing',      'Data Processing'),
    ('photography',           'Photography'),
    ('video',                  'Video'),
    ('public_story',            'Public Story'),
    ('follow_up_contact',         'Follow-up Contact'),
    ('mrv_data_collection',        'MRV Data Collection'),
]

CONSENT_STATUS_CHOICES = [
    ('not_requested', 'Not Requested'), ('requested', 'Requested'),
    ('granted', 'Granted'), ('declined', 'Declined'), ('withdrawn', 'Withdrawn'),
]

CONSENT_METHOD_CHOICES = [
    ('verbal', 'Verbal'), ('written', 'Written'), ('digital', 'Digital'),
]

QUOTE_VERIFICATION_STATUS_CHOICES = [
    ('not_started', 'Not Started'), ('in_progress', 'In Progress'), ('verified', 'Verified'),
]

QUOTE_APPROVAL_STATUS_CHOICES = [
    ('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'),
]

INCIDENT_TYPE_CHOICES = [
    ('participant_injury',    'Participant Injury'),
    ('community_concern',      'Community Concern'),
    ('safeguarding_concern',     'Safeguarding Concern'),
    ('technical_incident',        'Technical Incident'),
    ('environmental_harm',         'Environmental Harm'),
    ('food_safety_issue',            'Food Safety Issue'),
    ('data_privacy_incident',          'Data / Privacy Incident'),
    ('transport_issue',                  'Transport Issue'),
]

INCIDENT_SEVERITY_CHOICES = [
    ('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical'),
]

INCIDENT_STATUS_CHOICES = [
    ('reported', 'Reported'), ('investigating', 'Investigating'),
    ('resolved', 'Resolved'), ('closed', 'Closed'),
]

CHECKLIST_CATEGORY_CHOICES = [
    ('beneficiary',        'Beneficiary'),
    ('technical',           'Technical'),
    ('partner',              'Partner'),
    ('finance',                'Finance'),
    ('participant_safety',       'Participant Safety'),
    ('mrv',                        'MRV'),
    ('governance',                  'Governance'),
]

CHECKLIST_ITEM_STATUS_CHOICES = [
    ('missing', 'Missing'), ('in_review', 'In Review'),
    ('complete', 'Complete'), ('blocked', 'Blocked'),
]

SAFEGUARDING_REVIEW_STATUS_CHOICES = [
    ('not_started', 'Not Started'), ('in_progress', 'In Progress'),
    ('passed', 'Passed'), ('failed', 'Failed'),
]

INSURANCE_EVIDENCE_STATUS_CHOICES = [
    ('not_provided', 'Not Provided'), ('provided', 'Provided'), ('verified', 'Verified'),
]

CONFLICT_OF_INTEREST_STATUS_CHOICES = [
    ('not_assessed', 'Not Assessed'), ('clear', 'Clear'), ('flagged', 'Flagged'),
]


class StewardshipTour(models.Model):
    title = models.CharField(max_length=200)
    slug  = models.SlugField(max_length=220, unique=True)
    country = models.ForeignKey(
        'countries.CountryProfile', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    region = models.CharField(max_length=150, blank=True)
    tour_type = models.CharField(max_length=15, choices=TOUR_TYPE_CHOICES)
    status = models.CharField(max_length=25, choices=PIPELINE_STATUS_CHOICES, default='draft')
    description = models.TextField(blank=True)

    start_date = models.DateField(null=True, blank=True)
    end_date   = models.DateField(null=True, blank=True)
    participant_capacity = models.PositiveIntegerField(default=0)

    estimated_price_per_participant = models.FloatField(null=True, blank=True)
    total_budget_required            = models.FloatField(default=0.0)
    currency = models.CharField(max_length=10, default='GBP')

    safety_level = models.CharField(max_length=10, choices=SAFETY_LEVEL_CHOICES, default='medium')
    local_partner_required   = models.BooleanField(default=True)
    human_approval_required   = models.BooleanField(default=True)
    human_approved = models.BooleanField(null=True, blank=True, default=None, help_text='Explicit human sign-off, read by services/human_approval_gate.py — never inferred.')

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class StewardshipProblem(models.Model):
    tour = models.ForeignKey(StewardshipTour, on_delete=models.CASCADE, related_name='problems')
    problem_type = models.CharField(max_length=30, choices=PROBLEM_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)

    evidence_quality = models.CharField(max_length=10, choices=EVIDENCE_QUALITY_CHOICES, default='medium')
    urgency_score = models.FloatField(default=50.0)
    harm_score    = models.FloatField(default=50.0)
    confidence    = models.FloatField(default=50.0)
    status = models.CharField(max_length=20, choices=PROBLEM_STATUS_CHOICES, default='nominated')

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-urgency_score']

    def __str__(self):
        return self.title


class StewardshipIntervention(models.Model):
    problem = models.ForeignKey(StewardshipProblem, on_delete=models.CASCADE, related_name='interventions')
    title = models.CharField(max_length=255)
    intervention_type = models.CharField(max_length=35, choices=INTERVENTION_TYPE_CHOICES)
    description = models.TextField(blank=True)

    capex_estimate = models.FloatField(default=0.0)
    opex_estimate  = models.FloatField(default=0.0)
    estimated_benefit = models.FloatField(null=True, blank=True, help_text='Estimated, never labelled a verified outcome.')
    currency = models.CharField(max_length=10, default='GBP')

    implementation_complexity = models.CharField(max_length=10, choices=COMPLEXITY_CHOICES, default='medium')
    participant_role   = models.TextField(blank=True, help_text='Short summary — full detail lives on TourParticipantRole.')
    professional_role   = models.TextField(blank=True)
    local_partner_role   = models.TextField(blank=True)

    mrv_required        = models.BooleanField(default=True)
    governance_required  = models.BooleanField(default=True)
    status = models.CharField(max_length=15, choices=INTERVENTION_STATUS_CHOICES, default='modelled')

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['title']

    def __str__(self):
        return self.title


class TourFundingPlan(models.Model):
    tour = models.OneToOneField(StewardshipTour, on_delete=models.CASCADE, related_name='funding_plan')
    total_required = models.FloatField(default=0.0)
    participant_contribution   = models.FloatField(default=0.0)
    sponsor_contribution         = models.FloatField(default=0.0)
    grant_contribution            = models.FloatField(default=0.0)
    recovered_value_contribution   = models.FloatField(default=0.0)
    local_partner_contribution      = models.FloatField(default=0.0)
    funding_gap = models.FloatField(default=0.0, help_text='Computed — never asserted as secured.')
    currency = models.CharField(max_length=10, default='GBP')
    status = models.CharField(max_length=15, choices=FUNDING_STATUS_CHOICES, default='draft')

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Funding plan — {self.tour.title}'


class TourParticipantRole(models.Model):
    tour = models.ForeignKey(StewardshipTour, on_delete=models.CASCADE, related_name='participant_roles')
    role_name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    allowed_actions = models.JSONField(default=list, blank=True)
    blocked_actions  = models.JSONField(default=list, blank=True)
    safety_requirements = models.TextField(blank=True)
    supervision_required = models.BooleanField(default=True)

    class Meta:
        ordering = ['role_name']

    def __str__(self):
        return f'{self.role_name} — {self.tour.title}'


class TourLocalPartner(models.Model):
    tour = models.ForeignKey(StewardshipTour, on_delete=models.CASCADE, related_name='local_partners')
    partner_name = models.CharField(max_length=200)
    partner_type = models.CharField(max_length=15, choices=PARTNER_TYPE_CHOICES, default='ngo')
    role = models.TextField(blank=True)
    due_diligence_status = models.CharField(max_length=15, choices=DUE_DILIGENCE_STATUS_CHOICES, default='not_started')
    approval_status        = models.CharField(max_length=10, choices=PARTNER_APPROVAL_STATUS_CHOICES, default='pending')
    contact_status           = models.CharField(max_length=10, choices=CONTACT_STATUS_CHOICES, default='identified')

    # Real pilot readiness hardening — operational contact/verification data.
    # Partners are businesses/NGOs/municipalities, not private beneficiaries,
    # so real contact info here is legitimate operational data, not PII
    # requiring redaction (unlike TourBeneficiary's reference-only fields).
    legal_name = models.CharField(max_length=200, blank=True)
    local_registration_reference = models.CharField(max_length=200, blank=True)
    named_contact = models.CharField(max_length=150, blank=True)
    contact_role = models.CharField(max_length=100, blank=True)
    email_or_phone_reference = models.CharField(max_length=200, blank=True)
    safeguarding_review_status = models.CharField(max_length=15, choices=SAFEGUARDING_REVIEW_STATUS_CHOICES, default='not_started')
    insurance_evidence_status = models.CharField(max_length=15, choices=INSURANCE_EVIDENCE_STATUS_CHOICES, default='not_provided')
    conflict_of_interest_status = models.CharField(max_length=15, choices=CONFLICT_OF_INTEREST_STATUS_CHOICES, default='not_assessed')
    human_approved = models.BooleanField(null=True, blank=True, default=None, help_text='Explicit human sign-off, read by services/human_approval_gate.py — never inferred.')

    class Meta:
        ordering = ['partner_name']

    def __str__(self):
        return self.partner_name


class TourMRVPlan(models.Model):
    tour = models.OneToOneField(StewardshipTour, on_delete=models.CASCADE, related_name='mrv_plan')
    baseline_required   = models.BooleanField(default=True)
    after_data_required   = models.BooleanField(default=True)
    methodology = models.TextField(blank=True)
    evidence_required = models.JSONField(default=list, blank=True)
    verification_status = models.CharField(max_length=20, choices=MRV_VERIFICATION_STATUS_CHOICES, default='not_started')
    public_reporting_ready = models.BooleanField(default=False)

    def __str__(self):
        return f'MRV plan — {self.tour.title}'


class TourLegacyRecord(models.Model):
    """Never created until a tour has actually run and MRV has verified the outcome — see module docstring."""
    tour = models.OneToOneField(StewardshipTour, on_delete=models.CASCADE, related_name='legacy_record')
    verified_outcome_summary = models.TextField(blank=True)
    participants_count = models.PositiveIntegerField(default=0)
    community_benefit = models.TextField(blank=True)
    environmental_benefit = models.TextField(blank=True)
    financial_value_recovered = models.FloatField(null=True, blank=True, help_text='Stays null until MRV has actually verified a figure.')
    evidence_quality = models.CharField(max_length=10, choices=EVIDENCE_QUALITY_CHOICES, default='medium')
    mrv_status = models.CharField(max_length=20, choices=MRV_VERIFICATION_STATUS_CHOICES, default='not_started')
    public_private_status = models.CharField(max_length=10, choices=PUBLIC_PRIVATE_STATUS_CHOICES, default='private')

    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f'Legacy record — {self.tour.title}'


class TourBeneficiary(models.Model):
    """
    A real household/community/school benefiting from an intervention.
    Privacy: private_contact_reference / address_reference /
    vulnerability_notes_private are NEVER passed to public templates — see
    views.py::_public_beneficiary_view(), the concrete whitelist mechanism
    that enforces this (not just a naming convention).
    """
    stewardship_problem = models.ForeignKey(StewardshipProblem, on_delete=models.CASCADE, related_name='beneficiaries')
    display_reference = models.CharField(max_length=150, help_text='Safe public label, e.g. "Demo Household A — Almaty Region".')
    household_or_beneficiary_type = models.CharField(max_length=15, choices=BENEFICIARY_TYPE_CHOICES, default='household')
    country = models.ForeignKey('countries.CountryProfile', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    region = models.CharField(max_length=150, blank=True)
    locality = models.CharField(max_length=150, blank=True)

    private_contact_reference = models.CharField(max_length=255, blank=True, help_text='A pointer to where real contact info lives off-platform (e.g. local partner file) — never raw PII.')
    address_reference = models.CharField(max_length=255, blank=True, help_text='Same reference-only pattern as private_contact_reference.')
    household_size = models.PositiveIntegerField(null=True, blank=True)
    vulnerability_notes_private = models.TextField(blank=True, help_text='Never rendered in any public view.')
    language_preference = models.CharField(max_length=100, blank=True)

    consent_status = models.CharField(max_length=15, choices=BENEFICIARY_CONSENT_STATUS_CHOICES, default='not_started', help_text='Rollup convenience only — the real granular state lives on ConsentRecord rows.')
    eligibility_status = models.CharField(max_length=15, choices=ELIGIBILITY_STATUS_CHOICES, default='pending')
    intake_status = models.CharField(max_length=20, choices=INTAKE_STATUS_CHOICES, default='identified')

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_reference']

    def __str__(self):
        return self.display_reference


class ConsentRecord(models.Model):
    """
    One row per (beneficiary, tour, consent_type) — structurally enforces
    that consent is specific: consent to intervention != consent to
    photography != consent to public storytelling.
    """
    beneficiary = models.ForeignKey(TourBeneficiary, on_delete=models.CASCADE, related_name='consent_records')
    tour = models.ForeignKey(StewardshipTour, on_delete=models.CASCADE, related_name='consent_records')
    consent_type = models.CharField(max_length=25, choices=CONSENT_TYPE_CHOICES)
    status = models.CharField(max_length=15, choices=CONSENT_STATUS_CHOICES, default='not_requested')
    consent_method = models.CharField(max_length=10, choices=CONSENT_METHOD_CHOICES, blank=True)
    witnessed_by = models.CharField(max_length=150, blank=True)
    evidence_reference = models.CharField(max_length=255, blank=True)
    granted_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [('beneficiary', 'tour', 'consent_type')]
        ordering = ['consent_type']

    def __str__(self):
        return f'{self.get_consent_type_display()} — {self.beneficiary.display_reference}'


class SupplierQuote(models.Model):
    """
    A supplier quote is never an approved project cost, a quote received is
    never a supplier selected, and a supplier selected is never technical
    authorization — see services/launch_readiness.py::is_technical_work_authorized().
    """
    intervention = models.ForeignKey(StewardshipIntervention, on_delete=models.CASCADE, related_name='supplier_quotes')
    supplier_name = models.CharField(max_length=200)
    quote_reference = models.CharField(max_length=150, blank=True)
    amount = models.FloatField(help_text='The quoted amount — never an approved cost.')
    currency = models.CharField(max_length=10, default='GBP')
    issue_date = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    inclusions = models.JSONField(default=list, blank=True)
    exclusions = models.JSONField(default=list, blank=True)
    assumptions = models.TextField(blank=True)
    technical_scope = models.TextField(blank=True)
    warranty_information = models.TextField(blank=True)
    evidence_reference = models.CharField(max_length=255, blank=True)
    verification_status = models.CharField(max_length=15, choices=QUOTE_VERIFICATION_STATUS_CHOICES, default='not_started')
    approval_status = models.CharField(max_length=10, choices=QUOTE_APPROVAL_STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.supplier_name} — {self.intervention.title}'


class IncidentReport(models.Model):
    """Minimal incident log. Escalation is a real validation rule — see services/pilot_readiness_records.py::report_incident()."""
    tour = models.ForeignKey(StewardshipTour, on_delete=models.CASCADE, related_name='incident_reports')
    incident_type = models.CharField(max_length=25, choices=INCIDENT_TYPE_CHOICES)
    severity = models.CharField(max_length=10, choices=INCIDENT_SEVERITY_CHOICES, default='low')
    occurred_at = models.DateTimeField(default=timezone.now)
    description = models.TextField(blank=True)
    immediate_action = models.TextField(blank=True)
    escalated_to = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=15, choices=INCIDENT_STATUS_CHOICES, default='reported')
    evidence_reference = models.CharField(max_length=255, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-occurred_at']

    def __str__(self):
        return f'{self.get_incident_type_display()} — {self.tour.title}'


class LaunchChecklistItem(models.Model):
    """
    One row per required launch item. The Governance category's
    human_approval_complete item's own reviewed_by/reviewed_at/evidence_reference
    IS where the sign-off's approver/timestamp/evidence detail is recorded —
    no separate sign-off model needed.
    """
    tour = models.ForeignKey(StewardshipTour, on_delete=models.CASCADE, related_name='launch_checklist_items')
    checklist_category = models.CharField(max_length=20, choices=CHECKLIST_CATEGORY_CHOICES)
    item_key = models.CharField(max_length=50)
    label = models.CharField(max_length=255)
    required = models.BooleanField(default=True)
    status = models.CharField(max_length=10, choices=CHECKLIST_ITEM_STATUS_CHOICES, default='missing')
    evidence_reference = models.CharField(max_length=255, blank=True)
    reviewed_by = models.CharField(max_length=150, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    blocking_reason = models.TextField(blank=True)

    class Meta:
        unique_together = [('tour', 'item_key')]
        ordering = ['checklist_category', 'item_key']

    def __str__(self):
        return f'{self.label} — {self.tour.title}'
