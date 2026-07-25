"""
public_need_discovery/models.py — PR13: Actionable Public-Need Discovery.

Sits BETWEEN discovery (good_agents.GoodOpportunity — already qualified by
the existing evidence gate) and PR12's outreach_readiness (which governs
whether/how to actually contact a real organisation). This layer answers
one question PR12 assumes has already been answered: "is this genuinely
an actionable need, and who really has the remit to act on it?" — never
"is this worth telling someone about?" (that's discovery) and never "is
this safe to email?" (that's outreach_readiness).

Two things this layer is explicitly NOT allowed to do:
  1. Weaken outreach_readiness's recipient-responsibility test. Promoting
     a candidate here only ever creates/pre-fills an
     outreach_readiness.OutreachCandidateAssessment for a human to
     independently confirm via the SAME real functions PR12 built — never
     bypasses record_recipient_responsibility_test()/set_suitability_state().
  2. Perform any external action. No send, no form submission, no
     application. This app only ever recommends USE_EXISTING_PUBLIC_PROCESS
     or CONTACT_ORGANISATION as a state a human reads and acts on
     elsewhere.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

# --- Phase 1: signal/actionability classes -----------------------------------

ACTIONABILITY_CLASS_CHOICES = [
    ('informational_event', 'Informational event'),
    ('public_need', 'Public need'),
    ('service_gap', 'Service gap'),
    ('resource_available', 'Resource available'),
    ('funding_available', 'Funding available'),
    ('public_consultation', 'Public consultation'),
    ('data_request_opportunity', 'Data request opportunity'),
    ('policy_implementation_gap', 'Policy implementation gap'),
    ('local_environmental_issue', 'Local environmental issue'),
    ('infrastructure_maintenance_need', 'Infrastructure maintenance need'),
    ('community_support_need', 'Community support need'),
    ('regulatory_or_compliance_notice', 'Regulatory or compliance notice'),
]

# --- Phase 2: actionability gate states --------------------------------------

ACTIONABILITY_STATE_CHOICES = [
    ('informational_only', 'Informational only'),
    ('potentially_actionable', 'Potentially actionable'),
    ('actionable_needs_review', 'Actionable — needs review'),
    ('actionable', 'Actionable'),
    ('wrong_recipient', 'Wrong recipient'),
    ('no_responsible_body_identified', 'No responsible body identified'),
    ('no_clear_action', 'No clear action'),
    ('insufficient_evidence', 'Insufficient evidence'),
    ('sensitive_review_required', 'Sensitive — review required'),
]
ACTIONABILITY_TERMINAL_REJECTED_STATES = frozenset({
    'wrong_recipient', 'no_responsible_body_identified', 'no_clear_action',
    'insufficient_evidence', 'sensitive_review_required',
})
ACTIONABILITY_PROCEEDABLE_STATES = frozenset({'actionable_needs_review', 'actionable'})

# --- Phase 6: organisation roles ---------------------------------------------
# Deliberately richer than outreach_readiness.RECIPIENT_ROLE_CHOICES (which
# has exactly ONE role per assessment): a real organisation can genuinely
# hold several of these for the SAME candidate, each independently
# evidenced — e.g. a local authority can be both the jurisdiction authority
# AND the responsible authority, while a national department is only the
# funder. Never collapsed into one field.
ORGANISATION_ROLE_CHOICES = [
    ('evidence_publisher', 'Evidence publisher'),
    ('jurisdiction_authority', 'Jurisdiction authority'),
    ('responsible_authority', 'Responsible authority'),
    ('potential_implementer', 'Potential implementer'),
    ('funder', 'Funder'),
    ('resource_provider', 'Resource provider'),
    ('referral_body', 'Referral body'),
]
# Mirrors outreach_readiness.ROLES_THAT_JUSTIFY_ACTION_OUTREACH exactly —
# evidence_publisher/jurisdiction_authority alone are not enough to promote
# a candidate as actionable; the same discipline PR12 already enforces
# downstream, applied one stage earlier.
ROLES_THAT_JUSTIFY_ACTIONABILITY = frozenset({
    'responsible_authority', 'potential_implementer', 'funder', 'resource_provider', 'referral_body',
})

# --- Phase 9: small action types ---------------------------------------------

SMALL_ACTION_TYPE_CHOICES = [
    ('submit_evidence_to_consultation', 'Submit evidence to an open consultation'),
    ('ask_for_referral_route', 'Ask for the correct referral route'),
    ('clarify_programme_eligibility', 'Clarify programme eligibility'),
    ('surface_matching_grant', 'Surface a matching public grant'),
    ('request_missing_dataset', 'Request a missing public dataset'),
    ('notify_data_inconsistency', 'Notify an authority of a clearly evidenced data inconsistency'),
    ('refer_to_existing_programme', 'Refer a public need to an existing official programme'),
    ('connect_resource_to_need', 'Connect an available resource to a published need'),
    ('other', 'Other (specify)'),
]

# --- Phase 16: official public process types ---------------------------------
# Orthogonal to capability_graph.PublicRoute.route_type (which is the
# CHANNEL — email/online form/phone/...). This is the PURPOSE of that
# channel for THIS specific candidate.
PUBLIC_PROCESS_TYPE_CHOICES = [
    ('general_contact', 'General contact'),
    ('official_application', 'Official application'),
    ('consultation_submission', 'Consultation submission'),
    ('incident_report', 'Incident report'),
    ('referral_form', 'Referral form'),
    ('grant_application', 'Grant application'),
    ('data_request', 'Data request'),
    ('procurement_portal', 'Procurement portal'),
    ('public_feedback', 'Public feedback'),
]

# --- Phase 13: sensitivity categories (same vocabulary as outreach_readiness,
# applied one stage earlier so a sensitive case can be flagged before any
# organisation is even contacted about it in the outreach layer) -------------
SENSITIVITY_CATEGORY_CHOICES = [
    ('disaster', 'Disaster'), ('death_or_injury', 'Death / injury'), ('children', 'Children'),
    ('health', 'Health'), ('war_or_conflict', 'War / conflict'),
    ('vulnerable_communities', 'Vulnerable communities'), ('legal_disputes', 'Legal disputes'),
    ('religion', 'Religion'), ('personal_data', 'Personal data'), ('emergency_response', 'Emergency response'),
]

# --- Phase 12: evidence sufficiency ladder -----------------------------------
EVIDENCE_SUFFICIENCY_CHOICES = ['directly_stated', 'structured_inference', 'human_confirmed', 'missing']
EVIDENCE_SUFFICIENCY_FIELDS = ['need', 'location', 'timing', 'responsible_org', 'requested_action', 'route']

CAPITAL_REQUIRED_NOW_CHOICES = [('no', 'No'), ('yes', 'Yes'), ('unknown', 'Unknown')]


class PilotCandidateAssessment(models.Model):
    """
    ONE real GoodOpportunity's actionability review. Anchors to the SAME
    canonical opportunity Pilot Launchpad and outreach_readiness already
    use — no parallel "candidate" object competing with GoodOpportunity
    as the real anchor (mirrors outreach_readiness.OutreachCandidateAssessment's
    own precedent exactly).
    """
    opportunity = models.OneToOneField(
        'good_agents.GoodOpportunity', on_delete=models.CASCADE, related_name='pilot_candidate_assessment',
    )

    actionability_class = models.CharField(max_length=40, choices=ACTIONABILITY_CLASS_CHOICES, blank=True)
    actionability_state = models.CharField(max_length=40, choices=ACTIONABILITY_STATE_CHOICES, default='informational_only')
    assessment_notes = models.TextField(blank=True)

    # --- Phase 14: qualification tri-state — deliberately three separate
    # booleans, never collapsed. A signal can be discovery-worthy without
    # being actionable, and actionable without yet being outreach-suitable.
    discovery_qualified = models.BooleanField(default=False)
    actionability_qualified = models.BooleanField(default=False)
    outreach_suitable = models.BooleanField(default=False)

    # --- Phase 7: jurisdiction resolution — free text, same convention as
    # capability_graph.Organisation.jurisdiction/OutreachCandidateAssessment
    # .jurisdiction (deliberately not a new FK model — Phase 0 audit found
    # jurisdiction is free-text everywhere in this repo already; a
    # competing structured model would fragment matching, not improve it).
    jurisdiction = models.CharField(max_length=150, blank=True)
    jurisdiction_resolved = models.BooleanField(default=False)
    jurisdiction_resolution_notes = models.TextField(blank=True)

    # --- Phase 12: per-fact evidence sufficiency, e.g.
    # {"need": "directly_stated", "location": "directly_stated",
    #  "timing": "directly_stated", "responsible_org": "structured_inference",
    #  "requested_action": "missing", "route": "missing"}
    evidence_sufficiency = models.JSONField(default=dict, blank=True)

    # --- Phase 11: zero-capital-first
    capital_required_now = models.CharField(max_length=10, choices=CAPITAL_REQUIRED_NOW_CHOICES, default='unknown')

    # --- Phase 13: sensitivity gate (same discipline as outreach_readiness)
    is_sensitive = models.BooleanField(default=False)
    sensitivity_categories = models.JSONField(default=list, blank=True)
    sensitivity_notes = models.TextField(blank=True)
    evidence_valid_but_outreach_inappropriate = models.BooleanField(default=False)

    # --- Phase 9: small action generator
    suggested_action_type = models.CharField(max_length=40, choices=SMALL_ACTION_TYPE_CHOICES, blank=True)
    suggested_action_description = models.TextField(blank=True)

    # --- Phase 10/16: official process preference
    use_official_process = models.BooleanField(
        default=False,
        help_text='True when the correct action is an existing official process, not EcoIQ outreach.',
    )
    official_process_type = models.CharField(max_length=32, choices=PUBLIC_PROCESS_TYPE_CHOICES, blank=True)
    official_process_route_reference = models.CharField(
        max_length=500, blank=True,
        help_text='URL or soft pointer (e.g. capability_graph.PublicRoute:12) to the real official process.',
    )

    # --- Phase 15: explanation fields — no field is ever filled with
    # invented prose; blank stays blank and renders as "Not recorded."
    why_real_need = models.TextField(blank=True)
    why_action_useful = models.TextField(blank=True)
    what_ecoiq_does_not_know = models.TextField(blank=True)

    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    assessed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'Pilot candidate assessment — {self.opportunity_id} [{self.get_actionability_state_display()}]'

    @property
    def is_rejected(self):
        return self.actionability_state in ACTIONABILITY_TERMINAL_REJECTED_STATES

    @property
    def may_proceed_to_outreach_readiness(self):
        return self.actionability_state in ACTIONABILITY_PROCEEDABLE_STATES and not self.evidence_valid_but_outreach_inappropriate


class CandidateOrganisationRole(models.Model):
    """
    Phase 6 — one independently-evidenced role claim for one organisation
    on one candidate. The SAME organisation may have several rows here
    (e.g. a local authority as both jurisdiction_authority AND
    responsible_authority) — never one field forced to pick a single role.
    """
    candidate = models.ForeignKey(PilotCandidateAssessment, on_delete=models.CASCADE, related_name='organisation_roles')
    organisation = models.ForeignKey('capability_graph.Organisation', on_delete=models.CASCADE, related_name='+')
    role = models.CharField(max_length=32, choices=ORGANISATION_ROLE_CHOICES)

    evidence_reference = models.CharField(
        max_length=300, blank=True,
        help_text='Soft pointer, e.g. capability_graph.OrganisationCapability:12 — never inferred from the org\'s name alone.',
    )
    rationale = models.TextField(blank=True)
    confirmed = models.BooleanField(default=False, help_text='True once a human has checked this claim, not merely suggested it.')
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['role']
        unique_together = [('candidate', 'organisation', 'role')]

    def __str__(self):
        return f'{self.organisation} — {self.get_role_display()} ({self.candidate_id})'


class ProviderRunMetrics(models.Model):
    """
    Phase 23 — per-provider, per-run observability. Reuses
    GoodDiscoveryRun as the real anchor (not a second run/session
    concept) and SignalProvider for identity. One row per
    (provider, run) — historical, never overwritten, so a provider's
    metrics over time stay inspectable.
    """
    provider = models.ForeignKey('good_agents.SignalProvider', on_delete=models.CASCADE, related_name='run_metrics')
    run = models.ForeignKey('good_agents.GoodDiscoveryRun', on_delete=models.CASCADE, related_name='provider_metrics')

    records_fetched = models.PositiveIntegerField(default=0)
    duplicates = models.PositiveIntegerField(default=0)
    informational_only = models.PositiveIntegerField(default=0)
    potentially_actionable = models.PositiveIntegerField(default=0)
    actionability_qualified = models.PositiveIntegerField(default=0)
    rejected = models.PositiveIntegerField(default=0)
    missing_jurisdiction = models.PositiveIntegerField(default=0)
    missing_responsible_body = models.PositiveIntegerField(default=0)
    official_routes_found = models.PositiveIntegerField(default=0)
    errors = models.PositiveIntegerField(default=0)
    error_detail = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']
        unique_together = [('provider', 'run')]

    def __str__(self):
        return f'{self.provider.name} — run {self.run_id}'
