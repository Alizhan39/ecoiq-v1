"""
collaboration_rooms/models.py — PR10: Governed Collaboration Rooms, the
narrow coordination layer between "an organisation expressed interest in
a routed opportunity" (PR9's RoutingCandidate) and "a governed next step
was actually created" (PR5/PR9's ActionPathway / ConnectionCandidate /
ProjectCandidate / NextStepAction machinery, all reused unchanged here).

This is explicitly NOT a generic messaging platform. There is no existing
comment/message/chat/thread model anywhere else in this repo to reuse
(audited in PR10 Phase 0), so RoomMessage below is genuinely new — but
kept deliberately minimal (no channels, reactions, or threads). Every
other primitive a room touches (organisation identity, membership,
routing state, project/connection creation, notifications, telemetry) is
reused from the existing PR7/PR8/PR9/PR5 apps, never duplicated.

Claim vs. evidence (Phase 7) is enforced structurally: a partner's own
declaration ("we can provide 50 units") is stored as a 'declared_claim'
RoomEvidenceItem — the SAME verification-ladder discipline
capability_graph.OrganisationCapability already established — and never
auto-promotes to 'verified' just because someone typed it.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

ROOM_ROLE_CHOICES = [
    ('coordinator', 'Coordinator (EcoIQ staff)'),
    ('organisation_representative', 'Organisation representative'),
    ('expert', 'Approved expert'),
    ('observer', 'Observer'),
]
# Roles that may propose/consent/answer on behalf of an organisation —
# mirrors partner_participation.models.EDITING_ROLES's own discipline of
# a narrower "can act" set than "can merely view".
ACTING_ROOM_ROLES = frozenset({'coordinator', 'organisation_representative', 'expert'})

ROOM_STATUS_CHOICES = [
    ('open', 'Open'),
    ('waiting_on_ecoiq', 'Waiting on EcoIQ'),
    ('waiting_on_partner', 'Waiting on partner'),
    ('waiting_on_evidence', 'Waiting on evidence'),
    ('next_step_proposed', 'Next step proposed'),
    ('next_step_agreed', 'Next step agreed'),
    ('promoted_to_action', 'Promoted to action'),
    ('promoted_to_project', 'Promoted to project'),
    ('closed', 'Closed'),
    ('archived', 'Archived'),
]
# A room's own creation gate (Phase 2) — never created merely because
# EcoIQ found a match. Only these real RoutingCandidate states (PR9) may
# trigger a room, and even then only via an explicit staff approval call.
ROOM_CREATION_ALLOWED_CANDIDATE_STATUSES = frozenset({
    'interested', 'needs_more_information', 'accepted_for_next_step',
})


class CollaborationRoom(models.Model):
    """
    Anchors to exactly one real coordination context — PR9's
    RoutingCandidate (a OneToOne: at most one room per interested
    organisation/opportunity pair, matching RoutingCandidate's own
    unique_together). No contextless rooms.
    """
    routing_candidate = models.OneToOneField(
        'partner_participation.RoutingCandidate', on_delete=models.CASCADE, related_name='collaboration_room',
    )
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=24, choices=ROOM_STATUS_CHOICES, default='open')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity_at = models.DateTimeField(default=timezone.now)

    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    close_reason = models.TextField(blank=True)

    # Set once a NextStepProposal from this room is actually promoted — a
    # soft pointer (same convention as evidence_memory.source_reference),
    # e.g. "good_agents.ProjectCandidate:123" or "partner_participation.NextStepAction:45".
    promoted_action_reference = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Room: {self.title} [{self.get_status_display()}]'

    def touch(self):
        self.last_activity_at = timezone.now()
        self.save(update_fields=['last_activity_at'])

    @property
    def anchor_organisation(self):
        return self.routing_candidate.organisation

    @property
    def opportunity(self):
        return self.routing_candidate.opportunity


class RoomParticipant(models.Model):
    """
    Every participant must have a reason to access the room (Phase 3) —
    never open membership. Access is checked purely via an active
    (non-revoked) row here; nothing else grants room access.
    """
    room = models.ForeignKey(CollaborationRoom, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='room_participations')
    # Null only for an EcoIQ staff coordinator with no organisational affiliation.
    organisation = models.ForeignKey(
        'capability_graph.Organisation', null=True, blank=True, on_delete=models.CASCADE, related_name='room_participations',
    )
    role = models.CharField(max_length=32, choices=ROOM_ROLE_CHOICES, default='observer')
    reason = models.CharField(max_length=255, blank=True, help_text='Why this participant has access — never blank for a non-anchor participant.')

    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    added_at = models.DateTimeField(default=timezone.now)

    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    revoked_reason = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = [('room', 'user')]
        ordering = ['added_at']

    def __str__(self):
        return f'{self.user} in {self.room_id} [{self.get_role_display()}]'

    @property
    def is_active(self):
        return self.revoked_at is None


EVIDENCE_TYPE_CHOICES = [
    ('existing_ecoiq_evidence', 'Existing EcoIQ evidence'),
    ('public_source_link', 'Public source link'),
    ('document', 'Document reference'),
    ('measurement', 'Measurement'),
    ('resource_information', 'Resource information'),
    ('funding_information', 'Funding information'),
    ('organisation_provided', 'Organisation-provided information'),
    ('other', 'Other'),
]
# The claim/evidence separation axis (Phase 7) — deliberately mirrors
# capability_graph's own verification-ladder discipline rather than
# inventing a second vocabulary. A statement never jumps straight to
# 'ecoiq_verified' — only a real EcoIQ staff verification call can do that.
EVIDENCE_VERIFICATION_CHOICES = [
    ('declared_claim', 'Declared claim — asserted by a participant, not yet verified'),
    ('linked_evidence', 'Linked evidence — points at a real external or EcoIQ source'),
    ('ecoiq_verified', 'EcoIQ verified — a real EcoIQ staff member confirmed this directly'),
]
VISIBILITY_CHOICES = [
    ('shared_with_room', 'Shared with all active room participants'),
    ('ecoiq_internal_only', 'EcoIQ internal only — never shown to any partner'),
    ('organisation_private', "Private to the sharing organisation's own members"),
]


class RoomEvidenceItem(models.Model):
    """
    Governed evidence sharing (Phase 6-7). `source_reference` is a soft
    pointer (e.g. "evidence_memory.EvidenceMemory:12", "good_agents.
    AvailableResource:5") when this item points at a real existing row;
    left blank for a plain declared claim with no backing record yet.
    Never auto-promoted to 'ecoiq_verified' by anything other than
    services.evidence.verify_item(actor=<real staff>).
    """
    room = models.ForeignKey(CollaborationRoom, on_delete=models.CASCADE, related_name='evidence_items')
    shared_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    organisation = models.ForeignKey(
        'capability_graph.Organisation', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    evidence_type = models.CharField(max_length=32, choices=EVIDENCE_TYPE_CHOICES, default='other')
    verification_state = models.CharField(max_length=20, choices=EVIDENCE_VERIFICATION_CHOICES, default='declared_claim')
    visibility = models.CharField(max_length=24, choices=VISIBILITY_CHOICES, default='shared_with_room')

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    source_url = models.URLField(max_length=2000, blank=True)
    source_reference = models.CharField(max_length=200, blank=True)

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.title} [{self.get_verification_state_display()}]'


INFO_REQUEST_TYPE_CHOICES = [
    ('document', 'Document'), ('measurement', 'Measurement'), ('eligibility_evidence', 'Eligibility evidence'),
    ('technical_specification', 'Technical specification'), ('authority_confirmation', 'Authority confirmation'),
    ('resource_availability', 'Resource availability'), ('funding_terms', 'Funding terms'),
    ('timeline', 'Timeline'), ('other', 'Other'),
]
INFO_REQUEST_STATUS_CHOICES = [
    ('open', 'Open'), ('answered', 'Answered'), ('partially_answered', 'Partially answered'),
    ('needs_evidence', 'Needs evidence'), ('closed', 'Closed'),
]


class InformationRequest(models.Model):
    """
    Structured question/information request (Phase 8-9) — deliberately
    NOT free-text chat. `directed_to_organisation` is null when the
    request is open to any participant. Answering never auto-closes the
    request (Phase 9's own "do not mark request complete merely because
    a text response exists") — only an explicit status change does.
    """
    room = models.ForeignKey(CollaborationRoom, on_delete=models.CASCADE, related_name='information_requests')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    requesting_organisation = models.ForeignKey(
        'capability_graph.Organisation', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    directed_to_organisation = models.ForeignKey(
        'capability_graph.Organisation', null=True, blank=True, on_delete=models.SET_NULL, related_name='information_requests_received',
    )
    request_type = models.CharField(max_length=32, choices=INFO_REQUEST_TYPE_CHOICES, default='other')
    question_text = models.TextField()
    status = models.CharField(max_length=20, choices=INFO_REQUEST_STATUS_CHOICES, default='open')

    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    closed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_request_type_display()}: {self.question_text[:50]} [{self.get_status_display()}]'


class InformationRequestResponse(models.Model):
    """
    A structured answer to an InformationRequest. `evidence_item` links a
    real RoomEvidenceItem when the answer is evidence-backed; when null,
    the answer is a plain declared claim (Phase 7) — `is_claim_only`
    reflects exactly that, never inferred from the free-text content.
    """
    request = models.ForeignKey(InformationRequest, on_delete=models.CASCADE, related_name='responses')
    responded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    responding_organisation = models.ForeignKey(
        'capability_graph.Organisation', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    answer_text = models.TextField()
    evidence_item = models.ForeignKey(
        RoomEvidenceItem, null=True, blank=True, on_delete=models.SET_NULL, related_name='information_responses',
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['created_at']

    @property
    def is_claim_only(self):
        return self.evidence_item_id is None

    def __str__(self):
        return f'Response to request {self.request_id} by {self.responded_by}'


class RoomMessage(models.Model):
    """
    Deliberately minimal free-text messaging (Phase 10) — no threads,
    reactions, or channels. `visibility` separates shared room content
    from EcoIQ-internal notes and an organisation's own private notes
    (Phase 31) so a partner-facing view can filter correctly by a single
    field rather than by convention.
    """
    room = models.ForeignKey(CollaborationRoom, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    organisation = models.ForeignKey(
        'capability_graph.Organisation', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    body = models.TextField()
    visibility = models.CharField(max_length=24, choices=VISIBILITY_CHOICES, default='shared_with_room')

    edited_at = models.DateTimeField(null=True, blank=True)
    # Append-only snapshots of every prior body — never silently overwritten.
    edit_history = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.author} in room {self.room_id}: {self.body[:40]}'


NEXT_STEP_PROPOSAL_TYPE_CHOICES = [
    ('technical_discussion', 'Schedule technical discussion'),
    ('share_dataset', 'Share missing dataset'),
    ('introduction', 'Make introduction'),
    ('verify_resource', 'Verify resource'),
    ('funding_eligibility_review', 'Review funding eligibility'),
    ('site_assessment', 'Conduct site assessment'),
    ('project_candidate', 'Create project candidate'),
    ('reject_close', 'Reject / close opportunity'),
]
NEXT_STEP_PROPOSAL_STATUS_CHOICES = [
    ('draft', 'Draft'), ('proposed', 'Proposed'), ('accepted', 'Accepted'),
    ('rejected', 'Rejected'), ('needs_modification', 'Needs modification'), ('completed', 'Completed'),
]
# Real, structural transition table — never a jump. Mirrors the
# ALLOWED_TRANSITIONS discipline every prior PR in this lineage uses.
NEXT_STEP_PROPOSAL_ALLOWED_TRANSITIONS = {
    'draft': {'proposed'},
    'proposed': {'accepted', 'rejected', 'needs_modification'},
    'needs_modification': {'proposed', 'rejected'},
    'accepted': {'completed'},
    'rejected': set(),
    'completed': set(),
}


class NextStepProposal(models.Model):
    """
    The structured heart of a room (Phase 11-12). `required_organisations`
    lists every real party (plus, via `requires_ecoiq_consent`, EcoIQ
    itself) whose explicit consent is required before this can become
    'accepted' — mutual consent is tracked in RoomConsent below, never
    inferred from silence or from a single party's approval.

    `linked_resource_match`/`linked_funding_match` are required before
    promoting a 'verify_resource'/'funding_eligibility_review' proposal —
    promotion reuses partner_participation.services.next_step's EXISTING
    functions, which themselves require a real ResourceMatch/FundingMatch;
    this app never fabricates one to make promotion "work".
    """
    room = models.ForeignKey(CollaborationRoom, on_delete=models.CASCADE, related_name='next_step_proposals')
    proposed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    proposing_organisation = models.ForeignKey(
        'capability_graph.Organisation', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    proposal_type = models.CharField(max_length=32, choices=NEXT_STEP_PROPOSAL_TYPE_CHOICES)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=NEXT_STEP_PROPOSAL_STATUS_CHOICES, default='draft')

    required_organisations = models.ManyToManyField('capability_graph.Organisation', blank=True, related_name='+')
    requires_ecoiq_consent = models.BooleanField(default=True)

    linked_resource_match = models.ForeignKey(
        'good_agents.ResourceMatch', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    linked_funding_match = models.ForeignKey(
        'good_agents.FundingMatch', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )

    # Set once promotion actually happens — soft pointer, same convention as CollaborationRoom.promoted_action_reference.
    promoted_reference = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_proposal_type_display()} [{self.get_status_display()}] — room {self.room_id}'


CONSENT_STATUS_CHOICES = [('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')]


class RoomConsent(models.Model):
    """
    The explicit consent matrix (Phase 13). One row per required party
    per proposal. `organisation` is null exactly when this row represents
    EcoIQ's own required consent (`NextStepProposal.requires_ecoiq_consent`).
    Never inferred, never defaulted to approved.
    """
    proposal = models.ForeignKey(NextStepProposal, on_delete=models.CASCADE, related_name='consents')
    organisation = models.ForeignKey(
        'capability_graph.Organisation', null=True, blank=True, on_delete=models.CASCADE, related_name='+',
    )
    status = models.CharField(max_length=10, choices=CONSENT_STATUS_CHOICES, default='pending')
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['organisation_id']

    def __str__(self):
        party = self.organisation.name if self.organisation_id else 'EcoIQ'
        return f'{party}: {self.get_status_display()} (proposal {self.proposal_id})'


ROOM_EVENT_TYPE_CHOICES = [
    ('room_created', 'Room created'), ('participant_added', 'Participant added'),
    ('participant_revoked', 'Participant revoked'), ('evidence_shared', 'Evidence shared'),
    ('evidence_verified', 'Evidence verified'), ('question_asked', 'Question asked'),
    ('answer_provided', 'Answer provided'), ('request_status_changed', 'Request status changed'),
    ('message_sent', 'Message sent'), ('next_step_proposed', 'Next step proposed'),
    ('consent_given', 'Consent given'), ('consent_rejected', 'Consent rejected'),
    ('next_step_agreed', 'Next step agreed'), ('action_created', 'Action created'),
    ('project_candidate_created', 'Project candidate created'), ('room_status_changed', 'Room status changed'),
    ('room_closed', 'Room closed'), ('stall_detected', 'Stall detected'),
    ('organisation_withdrew', 'Organisation withdrew'), ('ai_assistance_used', 'AI assistance used'),
]


class RoomActivityEvent(models.Model):
    """Append-only immutable timeline per room (Phase 20) — mirrors partner_participation.NetworkActivityEvent's own discipline."""
    room = models.ForeignKey(CollaborationRoom, on_delete=models.CASCADE, related_name='activity_events')
    event_type = models.CharField(max_length=32, choices=ROOM_EVENT_TYPE_CHOICES)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    organisation = models.ForeignKey(
        'capability_graph.Organisation', null=True, blank=True, on_delete=models.SET_NULL, related_name='+',
    )
    source_object_reference = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.get_event_type_display()} — room {self.room_id} ({self.created_at:%Y-%m-%d %H:%M})'
