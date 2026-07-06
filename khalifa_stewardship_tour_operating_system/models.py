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
