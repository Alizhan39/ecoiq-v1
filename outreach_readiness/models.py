"""
outreach_readiness/models.py — PR12: First Real Outreach Readiness.

A deliberately NEW, separate governance layer for "the first time EcoIQ
contacts a real external organisation." This is stricter than, and does
not replace, PR5's OutreachDraft (used for routine outreach once an
organisation is already an established real or controlled contact). Every
model here exists to make one thing structurally impossible: reaching a
real send without an explicit, evidenced, human-reviewed chain from
"is this even the right organisation?" through "did the founder actually
say send?".

Nothing in this app can send a real message. `EXTERNAL_OUTREACH_ENABLED`
(ecoiq/settings.py) is `False` and this PR does not add a code path that
reads it to perform a send — only a later, explicit PR may add that.

State-honesty discipline (matches every prior PR in this lineage): a
model's status field is never set to a stronger state than what actually
happened. `readiness_state` is deliberately NOT stored on
OutreachCandidateAssessment — it is always recomputed from the real rows
that exist (services/readiness.py), so it can never drift out of sync
with what has genuinely been completed.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from capability_graph.models import ROUTE_TYPE_CHOICES

# --- Phase 1: suitability review ---------------------------------------------

SUITABILITY_STATE_CHOICES = [
    ('not_ready', 'Not ready'),
    ('suitable', 'Suitable'),
    ('potentially_suitable', 'Potentially suitable'),
    ('wrong_organisation', 'Wrong organisation'),
    ('wrong_route', 'Wrong route'),
    ('no_clear_ask', 'No clear ask'),
    ('insufficient_evidence', 'Insufficient evidence'),
    ('too_sensitive', 'Too sensitive'),
    ('not_actionable', 'Not actionable'),
    ('rejected', 'Rejected'),
]
# States that mean "this candidate is closed — do not proceed further."
# Never ranked against the "still being assessed" states below; a rejected
# candidate cannot be nudged forward by adding more data to other fields.
SUITABILITY_TERMINAL_REJECTED_STATES = frozenset({
    'wrong_organisation', 'wrong_route', 'no_clear_ask', 'insufficient_evidence',
    'too_sensitive', 'not_actionable', 'rejected',
})
SUITABILITY_PROCEEDABLE_STATES = frozenset({'suitable', 'potentially_suitable'})

# --- Phase 4: recipient responsibility test ----------------------------------

RECIPIENT_ROLE_CHOICES = [
    ('source_of_information', 'Source of information'),
    ('responsible_authority', 'Responsible authority'),
    ('potential_implementer', 'Potential implementer'),
    ('funder', 'Funder'),
    ('resource_provider', 'Resource provider'),
    ('research_body', 'Research body'),
    ('referral_body', 'Referral body'),
]
# Roles that make an organisation a legitimate outreach recipient for a
# request FOR ACTION (as opposed to merely being where the evidence came
# from). "source_of_information" alone is explicitly NOT enough — Phase 2's
# own key acceptance test (never contact a publisher merely because its
# feed generated the signal).
ROLES_THAT_JUSTIFY_ACTION_OUTREACH = frozenset({
    'responsible_authority', 'potential_implementer', 'funder',
    'resource_provider', 'referral_body',
})

# --- Phase 13: sensitivity categories ----------------------------------------

SENSITIVITY_CATEGORY_CHOICES = [
    ('disaster', 'Disaster'), ('death_or_injury', 'Death / injury'), ('children', 'Children'),
    ('health', 'Health'), ('war_or_conflict', 'War / conflict'),
    ('vulnerable_communities', 'Vulnerable communities'), ('legal_disputes', 'Legal disputes'),
    ('religion', 'Religion'), ('personal_data', 'Personal data'), ('emergency_response', 'Emergency response'),
]


class OutreachCandidateAssessment(models.Model):
    """
    ONE real GoodOpportunity's outreach suitability review (Phases 1-4,
    6, 7, 13). Never plural per opportunity — re-assessing overwrites the
    same real row (with `assessed_at` bumped), so there is exactly one
    current, honest verdict per opportunity, never several contradictory
    historical ones sitting around looking current.
    """
    opportunity = models.OneToOneField(
        'good_agents.GoodOpportunity', on_delete=models.CASCADE, related_name='outreach_assessment',
    )
    # The organisation being assessed AS a potential recipient — may be
    # null if no organisation has been resolved at all yet (an honest
    # NEEDS_RECIPIENT state, not an error).
    organisation = models.ForeignKey(
        'capability_graph.Organisation', null=True, blank=True, on_delete=models.SET_NULL, related_name='outreach_assessments',
    )
    responsible_party = models.ForeignKey(
        'good_agents.ResponsibleParty', null=True, blank=True, on_delete=models.SET_NULL, related_name='outreach_assessments',
    )

    suitability_state = models.CharField(max_length=24, choices=SUITABILITY_STATE_CHOICES, default='not_ready')
    recipient_role = models.CharField(max_length=24, choices=RECIPIENT_ROLE_CHOICES, blank=True)

    # --- Phase 1 suitability review questions — every one answered
    # honestly as True/False/None(unknown), never inferred from a single
    # aggregate score.
    evidence_credible = models.BooleanField(null=True, blank=True)
    response_genuinely_useful = models.BooleanField(null=True, blank=True)
    within_recipient_remit = models.BooleanField(null=True, blank=True)
    route_available = models.BooleanField(null=True, blank=True)
    ask_small_and_proportionate = models.BooleanField(null=True, blank=True)
    plausibly_answerable = models.BooleanField(null=True, blank=True)
    plausible_next_governed_step = models.BooleanField(null=True, blank=True)
    risk_of_appearing_inappropriate = models.BooleanField(null=True, blank=True)
    more_value_than_public_info_alone = models.BooleanField(null=True, blank=True)
    assessment_notes = models.TextField(blank=True)

    # --- Phase 4 recipient responsibility test — every field a real,
    # evidenced claim, never inferred from the organisation's name/sector.
    identity_confirmed = models.BooleanField(default=False)
    jurisdiction = models.CharField(max_length=150, blank=True)
    remit_confirmed_for_this_issue = models.BooleanField(default=False)
    remit_rationale = models.TextField(blank=True)
    geographic_relevance_confirmed = models.BooleanField(default=False)
    capability_evidence_reference = models.CharField(
        max_length=300, blank=True,
        help_text='Soft pointer, e.g. capability_graph.OrganisationCapability:12 — never free-typed evidence.',
    )
    limitations = models.TextField(blank=True)

    # --- Phase 13 sensitivity gate
    is_sensitive = models.BooleanField(default=False)
    sensitivity_categories = models.JSONField(default=list, blank=True)
    sensitivity_notes = models.TextField(blank=True)
    # True only when evidence is real/important but outreach itself is
    # still inappropriate — the exact distinction Phase 13 requires never
    # be confused with "the evidence must be wrong."
    evidence_valid_but_outreach_inappropriate = models.BooleanField(default=False)

    # --- Phase 6/7 minimum viable ask + value offered
    minimum_viable_ask = models.TextField(blank=True)
    value_offered_to_recipient = models.TextField(blank=True)

    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    assessed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'Outreach assessment — {self.opportunity_id} [{self.get_suitability_state_display()}]'

    @property
    def is_rejected(self):
        return self.suitability_state in SUITABILITY_TERMINAL_REJECTED_STATES

    @property
    def may_proceed_to_message(self):
        return self.suitability_state in SUITABILITY_PROCEEDABLE_STATES and not self.evidence_valid_but_outreach_inappropriate


class OutreachRoute(models.Model):
    """
    Phase 5 — the SPECIFIC route chosen for THIS outreach candidate, with
    full provenance. Distinct from capability_graph.PublicRoute (a
    capability-level fact about an organisation in general) — this record
    additionally captures whether THIS route accepts THIS kind of request,
    when it was checked, and any published restriction, none of which
    belong on the more general capability-level route.
    """
    assessment = models.ForeignKey(OutreachCandidateAssessment, on_delete=models.CASCADE, related_name='routes')
    linked_capability_graph_route = models.ForeignKey(
        'capability_graph.PublicRoute', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    official_website = models.URLField(blank=True)
    contact_page_or_institutional_email = models.CharField(
        max_length=500, help_text='The real, published institutional channel — never a guessed or personal address.',
    )
    route_type = models.CharField(max_length=24, choices=ROUTE_TYPE_CHOICES)
    route_purpose = models.CharField(max_length=255, blank=True)
    source_reference = models.CharField(max_length=500, help_text='URL or reference where this route was published.')
    date_checked = models.DateField(null=True, blank=True)
    jurisdiction = models.CharField(max_length=150, blank=True)
    accepts_this_request_type = models.BooleanField(null=True, blank=True)
    published_restrictions = models.TextField(blank=True)
    superseded_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_route_type_display()} — {self.assessment_id}'


class OutreachMessageVersion(models.Model):
    """
    Phase 8-11, 15 — one immutable-once-approved message draft. Editing
    after approval NEVER mutates this row — it creates the next
    `version_number` and invalidates this one's approval (services/message.py),
    so "the founder-approved version" is always one exact, unambiguous row,
    never a moving target.
    """
    APPROVAL_STATUS_CHOICES = [
        ('draft', 'Draft'), ('reviewed', 'Reviewed'), ('approved', 'Approved'), ('invalidated', 'Invalidated'),
    ]
    assessment = models.ForeignKey(OutreachCandidateAssessment, on_delete=models.CASCADE, related_name='message_versions')
    version_number = models.PositiveIntegerField()

    subject = models.CharField(max_length=255, blank=True)
    # Phase 9 — fact/inference/request/unknown kept as separate structured
    # lists, never collapsed into one prose block, so the distinction
    # survives into the UI and the exported dossier verbatim.
    fact_points = models.JSONField(default=list, blank=True)
    inference_points = models.JSONField(default=list, blank=True)
    the_request = models.TextField(blank=True)
    unknowns = models.JSONField(default=list, blank=True)
    value_offered = models.TextField(blank=True)
    body_text = models.TextField(blank=True, help_text='The actual rendered message a recipient would read.')

    sender_name = models.CharField(max_length=150, blank=True)
    sender_role = models.CharField(max_length=150, blank=True)
    sender_organisation = models.CharField(max_length=150, blank=True)
    reply_to = models.CharField(max_length=255, blank=True)
    sender_website = models.URLField(blank=True)
    signature_block = models.TextField(blank=True)

    editor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    created_at = models.DateTimeField(default=timezone.now)
    change_summary = models.TextField(blank=True)

    approval_status = models.CharField(max_length=16, choices=APPROVAL_STATUS_CHOICES, default='draft')
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
        unique_together = [('assessment', 'version_number')]

    def __str__(self):
        return f'Message v{self.version_number} — {self.assessment_id} [{self.approval_status}]'

    def word_count(self):
        return len(self.body_text.split())


class OutreachRiskReview(models.Model):
    """
    Phase 12 — the mandatory 15-item checklist. One row per message
    version (a new version always needs its own fresh review — an old
    version's passing review says nothing about a newly edited one).
    Every field defaults False (never silently "passes" an unreviewed item).
    """
    message_version = models.OneToOneField(OutreachMessageVersion, on_delete=models.CASCADE, related_name='risk_review')

    correct_organisation = models.BooleanField(default=False)
    correct_institutional_role = models.BooleanField(default=False)
    correct_public_route = models.BooleanField(default=False)
    evidence_current = models.BooleanField(default=False)
    request_answerable = models.BooleanField(default=False)
    request_proportionate = models.BooleanField(default=False)
    no_sensitive_personal_data = models.BooleanField(default=False)
    no_unsupported_urgency = models.BooleanField(default=False)
    no_implied_partnership = models.BooleanField(default=False)
    no_implied_authority = models.BooleanField(default=False)
    no_financial_promise = models.BooleanField(default=False)
    no_legal_or_religious_claim = models.BooleanField(default=False)
    no_exploitative_framing = models.BooleanField(default=False)
    no_duplicate_prior_outreach = models.BooleanField(default=False)
    no_do_not_contact_status = models.BooleanField(default=False)

    notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    CHECKLIST_FIELDS = [
        'correct_organisation', 'correct_institutional_role', 'correct_public_route', 'evidence_current',
        'request_answerable', 'request_proportionate', 'no_sensitive_personal_data', 'no_unsupported_urgency',
        'no_implied_partnership', 'no_implied_authority', 'no_financial_promise', 'no_legal_or_religious_claim',
        'no_exploitative_framing', 'no_duplicate_prior_outreach', 'no_do_not_contact_status',
    ]

    def __str__(self):
        return f'Risk review — {self.message_version_id} ({"passed" if self.all_passed else "incomplete"})'

    @property
    def all_passed(self):
        return all(getattr(self, field) for field in self.CHECKLIST_FIELDS)

    @property
    def failed_items(self):
        return [field for field in self.CHECKLIST_FIELDS if not getattr(self, field)]


class OutreachDryRun(models.Model):
    """
    Phase 17, 26 — a safe, snapshotted rehearsal. NEVER sends anything;
    `transport_mode` records what WOULD be used, and every other field is
    a frozen snapshot of the message version at run time (not a live FK
    dereference), so a dry run stays an honest historical record even if
    the message is edited again afterwards.
    """
    TRANSPORT_MODE_CHOICES = [
        ('real_email_transport', 'Real email transport'), ('manual_email', 'Manual email'),
        ('public_contact_form_manual', 'Public contact form (manual)'),
        ('other_verified_public_channel', 'Other verified public channel'), ('no_transport', 'No transport available'),
    ]
    VALIDATION_RESULT_CHOICES = [('pass', 'Pass'), ('fail', 'Fail')]

    message_version = models.ForeignKey(OutreachMessageVersion, on_delete=models.CASCADE, related_name='dry_runs')
    recipient_route_snapshot = models.TextField(blank=True)
    subject_snapshot = models.CharField(max_length=255, blank=True)
    body_snapshot = models.TextField(blank=True)
    sender_identity_snapshot = models.TextField(blank=True)
    reply_to_snapshot = models.CharField(max_length=255, blank=True)
    links_snapshot = models.JSONField(default=list, blank=True)

    transport_mode = models.CharField(max_length=32, choices=TRANSPORT_MODE_CHOICES)
    validation_result = models.CharField(max_length=8, choices=VALIDATION_RESULT_CHOICES)
    validation_details = models.JSONField(default=list, blank=True)

    run_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    run_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-run_at']

    def __str__(self):
        return f'Dry run — {self.message_version_id} [{self.validation_result}]'


class FounderSendDecision(models.Model):
    """
    Phase 24 — the one real decision this whole app exists to gate.
    `decision` is null until a founder genuinely records one; the system
    may compute and DISPLAY a recommendation (services/founder_review.py),
    but only a real human write to this row constitutes an actual decision
    — never inferred, never defaulted, never set by AI (Phase 27).
    """
    DECISION_CHOICES = [('send', 'Send'), ('revise', 'Revise'), ('do_not_send', 'Do not send')]

    assessment = models.OneToOneField(OutreachCandidateAssessment, on_delete=models.CASCADE, related_name='founder_decision')
    message_version = models.ForeignKey(OutreachMessageVersion, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    decision = models.CharField(max_length=16, choices=DECISION_CHOICES, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    rationale = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Founder decision — {self.assessment_id} [{self.decision or "pending"}]'


class OutreachReviewRole(models.Model):
    """
    Phase 16 — honest role tracking. If the same real user holds more than
    one role on the same assessment, `has_single_reviewer_limitation()`
    (services/roles.py) reports it plainly rather than letting the UI
    imply independent review that didn't happen.
    """
    ROLE_CHOICES = [('drafter', 'Drafter'), ('reviewer', 'Reviewer'), ('founder_approver', 'Founder approver')]

    assessment = models.ForeignKey(OutreachCandidateAssessment, on_delete=models.CASCADE, related_name='review_roles')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    assigned_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [('assessment', 'user', 'role')]

    def __str__(self):
        return f'{self.user} — {self.get_role_display()} ({self.assessment_id})'
