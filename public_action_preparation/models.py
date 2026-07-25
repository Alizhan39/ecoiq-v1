"""
public_action_preparation/models.py — PR14: First Legitimate Public
Action. Takes ONE real public-need candidate that PR13's Actionability
Gate already found `actionable`/`actionable_needs_review` and prepares
the exact legitimate next action — never defaulting to email, never
executing anything externally.

Deliberately anchors on `good_agents.GoodOpportunity` (the same anchor
every governance layer in this lineage uses), reading PR13's
`public_need_discovery.PilotCandidateAssessment` /
`CandidateOrganisationRole` as real, already-verified inputs — never
duplicating jurisdiction, responsible-body, or role data those models
already hold. Where the chosen action type is `prepare_outreach`, this
app hands off to PR12's `outreach_readiness` governance rather than
building a second one.

`EXTERNAL_PUBLIC_ACTIONS_ENABLED = False` (ecoiq/settings.py) is
hardcoded; no code path in this app reads it to perform a real
submission, referral, application, or contact.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

# --- Phase 2: action type decision -------------------------------------------
# The 8 fine-grained outputs from Phase 1's "possible outputs" list, plus the
# explicit `no_action` outcome — a superset of Phase 2's simplified 7-value
# list (SUBMIT_CONSULTATION_RESPONSE/REQUEST_PROGRAMME_CLARIFICATION/
# REFER_TO_EXISTING_SERVICE/REQUEST_PUBLIC_DATA/SURFACE_FUNDING_ROUTE/
# PROPOSE_ZERO_CAPITAL_CONNECTION all specialise USE_OFFICIAL_PUBLIC_PROCESS
# or a narrower non-outreach action; kept explicit rather than collapsed so
# the exact action is never ambiguous).
ACTION_TYPE_CHOICES = [
    ('use_official_public_process', 'Use official public process'),
    ('submit_consultation_response', 'Submit consultation response'),
    ('request_programme_clarification', 'Request programme clarification'),
    ('refer_to_existing_service', 'Refer to existing service'),
    ('request_public_data', 'Request public data'),
    ('surface_funding_route', 'Surface funding route'),
    ('propose_zero_capital_connection', 'Propose zero-capital connection'),
    ('prepare_outreach', 'Prepare outreach (via outreach_readiness)'),
    ('no_action', 'No action'),
]
# Action types that require a real, evidenced beneficiary/referral mandate
# before they may be selected (Phase 13's own explicit rule) — never
# fabricated from the mere existence of a public need.
ACTION_TYPES_REQUIRING_REAL_BENEFICIARY = frozenset({'refer_to_existing_service'})
# Action types that imply a real official process (with a real name, owning
# organisation, and — usually — a deadline) must be verified first.
# `request_public_data`/`surface_funding_route` deliberately excluded: Phase
# 9's own examples treat these as a direct ask to a real organisation, not
# necessarily a formal process with an opening/closing date — a real
# official process CAN still be recorded for either (Phase 16's route
# types include grant_application/data_request), but is not required before
# readiness can progress, unlike a consultation with a real deadline.
ACTION_TYPES_REQUIRING_PROCESS_VERIFICATION = frozenset({
    'use_official_public_process', 'submit_consultation_response',
})


class ActionTypeDecision(models.Model):
    """
    ONE real opportunity's chosen action type (Phase 2) — a human decision,
    never auto-selected from a score. `has_real_beneficiary` is the
    structural guard behind Phase 13's fuel-poverty rule: `refer_to_
    existing_service` cannot be recorded true without it (see
    services/action_type.py).
    """
    opportunity = models.OneToOneField(
        'good_agents.GoodOpportunity', on_delete=models.CASCADE, related_name='action_type_decision',
    )
    action_type = models.CharField(max_length=40, choices=ACTION_TYPE_CHOICES, blank=True)
    rationale = models.TextField(blank=True)

    has_real_beneficiary = models.BooleanField(default=False)
    beneficiary_basis_notes = models.TextField(blank=True)

    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Action type — {self.opportunity_id} [{self.action_type or "undecided"}]'


# --- Phase 3: official process verification ----------------------------------

PROCESS_STATUS_CHOICES = [
    ('unknown', 'Unknown — not yet checked'), ('open', 'Open'), ('expired', 'Expired / closed'),
    ('not_applicable', 'Not applicable'),
]


class VerifiedOfficialProcess(models.Model):
    """
    Phase 3 — real, checked facts about the official process this action
    would use, when one exists. `status` is never 'open' unless a real
    human recorded a real `closing_date` in the future (or explicitly
    confirmed open-ended) at `last_checked_at` — see
    services/process_verification.py. Never invents a deadline or
    eligibility rule.
    """
    opportunity = models.OneToOneField(
        'good_agents.GoodOpportunity', on_delete=models.CASCADE, related_name='verified_official_process',
    )
    process_name = models.CharField(max_length=255, blank=True)
    owning_organisation = models.ForeignKey(
        'capability_graph.Organisation', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    official_url = models.URLField(blank=True)
    route_type = models.CharField(max_length=24, blank=True, help_text='capability_graph.ROUTE_TYPE_CHOICES value.')

    opening_date = models.DateField(null=True, blank=True)
    closing_date = models.DateField(null=True, blank=True)
    eligibility = models.TextField(blank=True)
    required_information = models.TextField(blank=True)
    submission_format = models.CharField(max_length=255, blank=True)
    evidence_allowed = models.TextField(blank=True)
    acknowledgement_semantics = models.TextField(blank=True)

    status = models.CharField(max_length=16, choices=PROCESS_STATUS_CHOICES, default='unknown')
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    checked_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.process_name or "Unnamed process"} — {self.opportunity_id} [{self.status}]'

    @property
    def is_open(self):
        return self.status == 'open'


# --- Phase 11: process-specific content drafting ------------------------------

CONTENT_TYPE_CHOICES = [
    ('consultation_response', 'Consultation response'), ('referral_brief', 'Referral brief'),
    ('clarification_question', 'Clarification question'), ('data_request', 'Data request'),
    ('connection_proposal', 'Connection proposal'), ('other', 'Other'),
]
CONTENT_APPROVAL_STATUS_CHOICES = [
    ('draft', 'Draft'), ('reviewed', 'Reviewed'), ('founder_approved', 'Founder approved'),
    ('invalidated', 'Invalidated'),
]


class ActionContentDraft(models.Model):
    """
    Phase 11, 15 — one immutable-once-approved content draft, versioned
    exactly like outreach_readiness.OutreachMessageVersion: editing after
    approval never mutates this row, it creates the next version and
    invalidates this one (services/content_draft.py). One consistent
    versioning discipline across every content type, but the actual
    fields rendered depend on `content_type` — a consultation response is
    never the same generic template as a data request.
    """
    decision = models.ForeignKey(ActionTypeDecision, on_delete=models.CASCADE, related_name='content_drafts')
    version_number = models.PositiveIntegerField()
    content_type = models.CharField(max_length=24, choices=CONTENT_TYPE_CHOICES)

    subject = models.CharField(max_length=255, blank=True)
    fact_points = models.JSONField(default=list, blank=True)
    inference_points = models.JSONField(default=list, blank=True)
    specific_recommendation = models.TextField(blank=True)
    limitations = models.TextField(blank=True)
    source_links = models.JSONField(default=list, blank=True)
    body_text = models.TextField(blank=True, help_text='The actual rendered content that would be submitted/sent.')
    required_fields_missing = models.JSONField(
        default=list, blank=True, help_text='Fields a referral/form needs that are not yet known — never silently omitted.',
    )

    editor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    created_at = models.DateTimeField(default=timezone.now)
    change_summary = models.TextField(blank=True)

    approval_status = models.CharField(max_length=16, choices=CONTENT_APPROVAL_STATUS_CHOICES, default='draft')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    founder_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    founder_approved_at = models.DateTimeField(null=True, blank=True)
    invalidated_at = models.DateTimeField(null=True, blank=True)
    invalidated_reason = models.TextField(blank=True)

    class Meta:
        ordering = ['-version_number']
        unique_together = [('decision', 'version_number')]

    def __str__(self):
        return f'{self.get_content_type_display()} v{self.version_number} — {self.decision_id} [{self.approval_status}]'

    def word_count(self):
        return len(self.body_text.split())


# --- Phase 14: sensitivity / ethics review ------------------------------------

class EthicsReview(models.Model):
    """
    Phase 14 — a stricter, action-specific ethics checklist than PR13's
    sensitivity gate (which stays upstream, unmodified). Every field
    defaults False; a review counts as passed only when every field is
    explicitly set True by a real reviewer (services/ethics_review.py).
    """
    opportunity = models.OneToOneField(
        'good_agents.GoodOpportunity', on_delete=models.CASCADE, related_name='ethics_review',
    )
    vulnerability_considered = models.BooleanField(default=False)
    health_or_financial_hardship_considered = models.BooleanField(default=False)
    personal_data_risk_checked = models.BooleanField(default=False)
    representation_risk_checked = models.BooleanField(default=False)
    consent_addressed = models.BooleanField(default=False)
    misrouting_risk_checked = models.BooleanField(default=False)
    wasted_public_resources_risk_checked = models.BooleanField(default=False)
    implied_authority_risk_checked = models.BooleanField(default=False)

    notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    CHECKLIST_FIELDS = [
        'vulnerability_considered', 'health_or_financial_hardship_considered', 'personal_data_risk_checked',
        'representation_risk_checked', 'consent_addressed', 'misrouting_risk_checked',
        'wasted_public_resources_risk_checked', 'implied_authority_risk_checked',
    ]

    def __str__(self):
        return f'Ethics review — {self.opportunity_id} ({"passed" if self.all_passed else "incomplete"})'

    @property
    def all_passed(self):
        return all(getattr(self, field) for field in self.CHECKLIST_FIELDS)

    @property
    def failed_items(self):
        return [field for field in self.CHECKLIST_FIELDS if not getattr(self, field)]


# --- Phase 16: human review roles ---------------------------------------------

class ActionReviewRole(models.Model):
    """Phase 16 — honest role tracking, same discipline as outreach_readiness.OutreachReviewRole."""
    ROLE_CHOICES = [('researcher', 'Researcher'), ('reviewer', 'Reviewer'), ('founder_approver', 'Founder approver')]

    opportunity = models.ForeignKey('good_agents.GoodOpportunity', on_delete=models.CASCADE, related_name='action_review_roles')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    assigned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [('opportunity', 'user', 'role')]

    def __str__(self):
        return f'{self.user} — {self.get_role_display()} ({self.opportunity_id})'


# --- Phase 17: Founder Action Review ------------------------------------------

class FounderActionDecision(models.Model):
    """
    Phase 17 — the one real decision this app exists to gate. `decision`
    is null until a founder genuinely records one; the system may
    compute and DISPLAY a recommendation (services/founder_review.py),
    but only a real human write here constitutes an actual decision —
    never inferred, never defaulted, never set by AI (Phase 16).
    """
    DECISION_CHOICES = [('proceed', 'Proceed'), ('revise', 'Revise'), ('do_not_proceed', 'Do not proceed')]

    opportunity = models.OneToOneField(
        'good_agents.GoodOpportunity', on_delete=models.CASCADE, related_name='founder_action_decision',
    )
    content_draft = models.ForeignKey(ActionContentDraft, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    decision = models.CharField(max_length=16, choices=DECISION_CHOICES, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    rationale = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Founder action decision — {self.opportunity_id} [{self.decision or "pending"}]'
