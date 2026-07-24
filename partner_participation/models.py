"""
partner_participation/models.py — PR8: the reciprocal half of the
Capability Graph. PR7 let EcoIQ DISCOVER an organisation's capabilities
from external evidence; this app lets a real organisation PARTICIPATE —
claim its own identity, declare its own capabilities/service areas/
opportunity preferences/resources/funding programmes/routes, and receive
(never automatically accept) routed opportunity candidates.

    ORGANISATION -> CLAIMS/CONFIRMS CAPABILITIES -> DECLARES WHERE IT
    OPERATES -> DECLARES WHAT OPPORTUNITIES IT ACCEPTS -> DECLARES
    RESOURCE/FUNDING/SERVICE AVAILABILITY -> HUMAN/ORGANISATIONAL
    VERIFICATION -> ROUTING ELIGIBILITY -> OPPORTUNITY DELIVERY READINESS

This is NOT a marketplace, lead-generation tool, or autonomous outreach
system — every state that matters (membership, capability claims, routing
candidates) requires an explicit human action to progress, and nothing
here can reach "accepted"/"partnered" on its own.

Does not duplicate organisation identity: every model below references
`capability_graph.Organisation`, the ONE node PR7 already built.
"Service Area" (the brief's own candidate concept) is NOT a new model —
it's the existing `OrganisationCapability.jurisdiction`/`topic_domain`
fields, now settable through a partner declaration instead of only an
EcoIQ-authored one (see `services/capability_declarations.py`).
"Resource Declaration" also is NOT a new model — `good_agents
.AvailableResource` already exists and gained `organisation`/
`declared_by` fields in this same PR (see good_agents/models.py) per the
brief's explicit "reuse AvailableResource, do not create a parallel
resource system" instruction.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from good_agents.models import GOOD_TAXONOMY_CHOICES
from good_agents.models import FundingMatch as _FundingMatch

ORG_ROLE_CHOICES = [
    ('admin', 'Admin — full control of this organisation\'s participation data'),
    ('editor', 'Editor — can create/edit declarations, cannot manage members'),
    ('routing_manager', 'Routing manager — can respond to routing candidates'),
    ('reviewer', 'Reviewer — read + comment, cannot edit declarations'),
    ('viewer', 'Viewer — read-only'),
]
# Only these roles may manage membership/critical declarations (Phase 3's
# own "only organisation admins should manage critical participation
# declarations" instruction) — kept as a plain frozenset, not a permission
# framework, per this PR's repeated "do not overengineer RBAC" instruction.
CRITICAL_MANAGEMENT_ROLES = frozenset({'admin'})
EDITING_ROLES = frozenset({'admin', 'editor'})

MEMBERSHIP_STATUS_CHOICES = [
    ('claim_requested', 'Claim requested — awaiting EcoIQ review'),
    ('under_review', 'Under review'),
    ('verified_member', 'Verified member'),
    ('rejected', 'Rejected'),
    ('suspended', 'Suspended'),
]
# "UNCLAIMED" (Phase 2) is not a stored state — it's simply the absence of
# any OrganisationMembership row for an Organisation, exactly like PR6's
# derived (never separately stored) participation states.


class OrganisationMembership(models.Model):
    """
    Links a real, authenticated Django user to a capability_graph
    .Organisation with a role and a review-gated status. A row here is
    NEVER created already verified — `services/membership.py
    .request_membership()` always starts at 'claim_requested'; only
    `review_membership()`, called by real EcoIQ staff, can move it to
    'verified_member' or 'rejected'. Never inferred from an email domain
    matching the organisation's website — see that service's own
    docstring for why.
    """
    organisation = models.ForeignKey(
        'capability_graph.Organisation', on_delete=models.CASCADE, related_name='memberships',
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organisation_memberships')
    role = models.CharField(max_length=20, choices=ORG_ROLE_CHOICES, default='viewer')
    status = models.CharField(max_length=20, choices=MEMBERSHIP_STATUS_CHOICES, default='claim_requested')

    justification = models.TextField(blank=True, help_text='Why the claimant says they represent this organisation.')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    # Internal EcoIQ notes — never exposed to the partner portal (Phase 15/29's own privacy rule).
    review_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [('organisation', 'user')]

    def __str__(self):
        return f'{self.user} @ {self.organisation} [{self.get_role_display()} / {self.get_status_display()}]'


ACCEPTANCE_MODE_CHOICES = [
    ('open_to_relevant_opportunities', 'Open to relevant opportunities'),
    ('limited', 'Limited — some conditions apply'),
    ('invitation_only', 'Invitation only'),
    ('application_required', 'Application required'),
    ('not_accepting', 'Not accepting'),
    ('paused', 'Paused'),
]
# Only these count as "ready" during routing (Phase 8's own instruction —
# never route to NOT_ACCEPTING or PAUSED as ready).
ROUTABLE_ACCEPTANCE_MODES = frozenset({
    'open_to_relevant_opportunities', 'limited', 'invitation_only', 'application_required',
})

MIN_EVIDENCE_QUALITY_CHOICES = [
    ('any', 'Any evidence quality'),
    ('documented_or_better', 'Documented or better'),
    ('independently_verified_only', 'Independently verified only'),
]


class OpportunityPreference(models.Model):
    """
    A routing preference, NOT a guarantee (Phase 7's own instruction): "we
    would like to be routed relevant opportunities in this theme, under
    these conditions" — never "we will accept any specific opportunity
    matching this." `theme` reuses good_agents' own taxonomy rather than
    inventing a second one.
    """
    organisation = models.ForeignKey(
        'capability_graph.Organisation', on_delete=models.CASCADE, related_name='opportunity_preferences',
    )
    theme = models.CharField(max_length=32, choices=GOOD_TAXONOMY_CHOICES)
    acceptance_mode = models.CharField(max_length=32, choices=ACCEPTANCE_MODE_CHOICES, default='limited')

    # Routing requirements (Phase 9) — real, structured fields; never
    # invented for an organisation that hasn't stated them (all optional).
    min_evidence_quality = models.CharField(max_length=32, choices=MIN_EVIDENCE_QUALITY_CHOICES, default='any')
    eligible_beneficiary_type = models.TextField(blank=True)
    application_deadline = models.DateField(null=True, blank=True)
    min_project_size_usd = models.FloatField(null=True, blank=True)
    max_project_size_usd = models.FloatField(null=True, blank=True)
    requires_sharia_review = models.BooleanField(default=False)
    regulatory_prerequisites = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    set_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['organisation__name', 'theme']
        unique_together = [('organisation', 'theme')]

    def __str__(self):
        return f'{self.organisation} — {self.get_theme_display()} [{self.get_acceptance_mode_display()}]'


class FundingProgrammeDeclaration(models.Model):
    """
    A real, durable funding programme an organisation runs — distinct
    from good_agents.FundingMatch, which is scoped to ONE opportunity.
    Reuses FundingMatch's own funder_type vocabulary and Sharia-sensitivity
    rule (Phase 13's own "reuse FundingMatch/related infrastructure").
    `good_agents.FundingMatch.organisation` (added in PR7) is how a real
    opportunity match links back to the programme that justified it —
    this model never creates a second "matched to this opportunity"
    mechanism.
    """
    FUNDER_TYPE_CHOICES = _FundingMatch.FUNDER_TYPE_CHOICES
    SHARIA_SENSITIVE_FUNDER_TYPES = _FundingMatch.SHARIA_SENSITIVE_FUNDER_TYPES

    STATUS_CHOICES = [
        ('self_declared', 'Self-declared'), ('human_reviewed', 'Human reviewed'),
        ('independently_verified', 'Independently verified'), ('expired', 'Expired'),
    ]

    organisation = models.ForeignKey(
        'capability_graph.Organisation', on_delete=models.CASCADE, related_name='funding_programmes',
    )
    programme_name = models.CharField(max_length=255)
    funder_type = models.CharField(max_length=24, choices=FUNDER_TYPE_CHOICES)
    official_source_url = models.URLField(blank=True)
    amount_min_usd = models.FloatField(null=True, blank=True)
    amount_max_usd = models.FloatField(null=True, blank=True)
    deadline = models.DateField(null=True, blank=True)
    geography = models.CharField(max_length=150, blank=True)
    eligibility = models.TextField(blank=True)
    application_route_url = models.URLField(blank=True)
    # Never claims a programme is halal — this is only ever a flag that
    # Sharia review is required, structurally enforced below exactly like
    # FundingMatch.save() already does (see good_agents/models.py).
    requires_sharia_review = models.BooleanField(default=False)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default='self_declared')

    declared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.programme_name} — {self.organisation} [{self.get_status_display()}]'

    def save(self, *args, **kwargs):
        if self.funder_type in self.SHARIA_SENSITIVE_FUNDER_TYPES:
            self.requires_sharia_review = True
        super().save(*args, **kwargs)


ROUTING_STATUS_CHOICES = [
    ('routing_candidate', 'Routing candidate'),
    ('ready_for_ecoiq_review', 'Ready for EcoIQ review'),
    ('approved_to_share', 'Approved to share'),
    ('shared', 'Shared'),
    ('viewed', 'Viewed'),
    ('interested', 'Interested'),
    ('not_interested', 'Not interested'),
    ('needs_more_information', 'Needs more information'),
    ('accepted_for_next_step', 'Accepted for next step'),
]
# Governed like PR5's ActionGate — illegal jumps (e.g. straight to
# 'shared' without EcoIQ ever approving it) are structurally impossible.
ROUTING_ALLOWED_TRANSITIONS = {
    'routing_candidate': {'ready_for_ecoiq_review', 'not_interested'},
    'ready_for_ecoiq_review': {'approved_to_share', 'not_interested'},
    'approved_to_share': {'shared'},
    'shared': {'viewed', 'not_interested'},
    'viewed': {'interested', 'not_interested', 'needs_more_information'},
    'interested': {'needs_more_information', 'accepted_for_next_step', 'not_interested'},
    'needs_more_information': {'interested', 'not_interested'},
    'not_interested': set(),
    'accepted_for_next_step': set(),
}

CONFIDENCE_LABEL_CHOICES = [
    ('strong_verified_match', 'Strong verified match'),
    ('verified_capability_match', 'Verified capability match'),
    ('participation_match', 'Participation match'),
    ('possible_responsible_party', 'Possible responsible party'),
    ('needs_review', 'Needs review'),
    ('no_verified_route', 'No verified route'),
]


class RoutingCandidate(models.Model):
    """
    "This opportunity might suit this organisation" — never an assignment,
    never a send. `match_reasons` is the real routing explanation (Phase
    19): every entry is a real fact this candidate was scored on, never an
    opaque numeric confidence. Progression is fully human-gated: EcoIQ
    staff must move it to 'approved_to_share' before 'shared' is even
    reachable (see ROUTING_ALLOWED_TRANSITIONS above), and reaching
    'accepted_for_next_step' still means only that the ORGANISATION
    expressed interest — not that EcoIQ or the organisation has
    partnered, committed capital, or executed anything.
    """
    organisation = models.ForeignKey(
        'capability_graph.Organisation', on_delete=models.CASCADE, related_name='routing_candidates',
    )
    opportunity = models.ForeignKey(
        'good_agents.GoodOpportunity', on_delete=models.CASCADE, related_name='routing_candidates',
    )
    status = models.CharField(max_length=32, choices=ROUTING_STATUS_CHOICES, default='routing_candidate')
    confidence_label = models.CharField(max_length=32, choices=CONFIDENCE_LABEL_CHOICES, default='needs_review')
    match_reasons = models.JSONField(default=list, blank=True)

    shared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    shared_at = models.DateTimeField(null=True, blank=True)
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    responded_at = models.DateTimeField(null=True, blank=True)
    response_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [('organisation', 'opportunity')]

    def __str__(self):
        return f'{self.organisation} <- {self.opportunity} [{self.get_status_display()}]'
