# Governed Collaboration Rooms (PR10)

## What this adds

PR9 closed the loop from "opportunity routed" to "organisation responded
positively" (`interested` / `needs_more_information` /
`accepted_for_next_step`). PR10 adds the narrow coordination layer that
sits between that response and a real governed next step:

```
INTERESTED OPPORTUNITY -> GOVERNED COLLABORATION ROOM -> PARTIES + ROLES
  -> SHARED EVIDENCE -> QUESTIONS / INFORMATION REQUESTS -> PROPOSED NEXT
  STEP -> MUTUAL CONSENT -> ACTION / CONNECTION / PROJECT CANDIDATE ->
  EXISTING EXECUTION + MRV PIPELINE
```

## What a Collaboration Room is — and is not

A `CollaborationRoom` is a narrow, opportunity-scoped coordination
protocol. It is **not** Slack, Microsoft Teams, generic chat, a social
network, a CRM, autonomous negotiation, or contract/procurement
automation. There is no channel list, no reactions, no threads, no DMs,
and no file-attachment system — this PR's own Phase 0 audit found no
existing secure attachment infrastructure (content-type/virus
safeguards) anywhere in this repo, so evidence sharing is link/text-based
only, per the brief's own "do not build file infrastructure from scratch
unnecessarily" instruction.

## Reused vs. genuinely new

Reused, unchanged: `partner_participation.RoutingCandidate` (the room's
anchor and creation-gate signal), `capability_graph.Organisation` /
`OrganisationMembership`, `partner_participation.services.next_step`
(the ONLY code path that ever creates a real `NextStepAction` or proposes
a `ProjectCandidate` — this PR never duplicates it), PR5's
`project_bridge`/`connection_action` (still untouched, still the only
path to a real `GoldProject`), `notifications.AdminNotification`,
`ai_observatory`'s `AnalysisSession`/`PipelineStage` telemetry, and
`agent_runtime_model_router`'s `AnthropicCompatibleAdapter` for the
optional AI-assist layer.

Genuinely new (nothing in the repo covered this shape):
`CollaborationRoom`, `RoomParticipant`, `RoomEvidenceItem`,
`InformationRequest`/`InformationRequestResponse`, `RoomMessage`,
`NextStepProposal`/`RoomConsent`, `RoomActivityEvent`.

## The creation gate

A room is never created merely because EcoIQ found a routing match. Only
a real EcoIQ staff actor, calling `services.rooms.create_room()`, can
open one — and only for a `RoutingCandidate` already at `interested`,
`needs_more_information`, or `accepted_for_next_step`. One room per
candidate (a `OneToOneField`, idempotent). On creation, the staff actor
becomes the room's `coordinator`; every currently verified member of the
anchor organisation is auto-added as an `organisation_representative`
(they have an inherent reason — their own organisation responded). No
other organisation or expert is ever auto-added; each must be explicitly
added by staff with a stated `reason`.

## Access isolation

A user may access a room only via a real, non-revoked `RoomParticipant`
row — never inferred from organisation membership, staff status, or
anything else. An unauthorised authenticated user gets a flat 403 (never
a distinguishing 404 vs 403 that would let someone infer whether a room
ID exists). Revoking a participant immediately removes access; it never
deletes their past messages/evidence/consents.

## Claim vs. evidence

Every shared item carries a `verification_state`:
`declared_claim` (default — an organisation's own assertion, nothing
behind it), `linked_evidence` (a real source URL or soft-pointer
reference is attached), or `ecoiq_verified` (a real EcoIQ staff member
independently confirmed it via `services.evidence.verify_item()`). A
partner typing "we can provide 50 units" is stored and displayed as a
declared claim until a human verifies it — never auto-promoted.

## Structured questions, not chat

`InformationRequest` is deliberately not free-text: it carries a
`request_type` and tracks its own status (`open` / `answered` /
`partially_answered` / `needs_evidence` / `closed`). Answering
(`InformationRequestResponse`) never auto-closes the request — only an
explicit `services.questions.set_status()` call does. A response is
`is_claim_only` unless it links a real `RoomEvidenceItem`.

## Next-step proposals and mutual consent

`NextStepProposal` moves through a real, structurally-enforced state
machine (`draft -> proposed -> {accepted, rejected, needs_modification}`,
`accepted -> completed`). Proposing materialises one `RoomConsent` row
per required party (each organisation in `required_organisations`, plus
EcoIQ itself when `requires_ecoiq_consent`). `check_and_apply_consensus()`
only moves a proposal to `accepted` when **every** required consent is
`approved` — a single `pending` or `rejected` row is enough to withhold
consensus, and consensus is recomputed fresh on every consent change,
never cached or inferred from silence. Only a verified representative of
an organisation may consent on that organisation's behalf; only real
EcoIQ staff may consent as EcoIQ.

## Promotion — never a parallel action system

`services.promotion.promote_proposal()` requires `status == 'accepted'`
and a real staff actor, then dispatches by `proposal_type` into PR9's
existing `partner_participation.services.next_step` functions
(`create_meeting_request`, `create_data_exchange_request`,
`create_resource_match_followup`, `create_funding_eligibility_review`,
`propose_project_candidate`) — the same functions PR9's own Partner
Portal next-step UI calls. `verify_resource`/`funding_eligibility_review`
proposals require a real linked `ResourceMatch`/`FundingMatch` before
promotion; this module never fabricates one to make promotion "succeed".
A `project_candidate` promotion still only ever reaches PR5's
`ProjectCandidate` in `proposed` state — a further, separate approval is
still required before any real `GoldProject` exists.

## Timeline, notifications, and Mission Control

`RoomActivityEvent` is append-only (mirrors
`partner_participation.NetworkActivityEvent`'s own discipline).
Notifications reuse `notifications.create_notification` with the same
dedupe-by-reason pattern PR8/PR9 established — no second notification
system. An optional `services.notify.send_room_email_notification()`
sends a minimal room-title + action-required + secure-deep-link email
using the exact same real-vs-non-real transport honesty check PR9's
`has_real_mail_transport()` established — it never claims a send that
didn't happen, and never includes evidence/message content. Mission
Control's existing partner-participation section gains a compact
collaboration-room status line and a link — it never duplicates room
content.

## Privacy

`RoomMessage`/`RoomEvidenceItem.visibility` distinguishes
`shared_with_room`, `ecoiq_internal_only`, and `organisation_private`.
Every partner-facing view filters by this field before rendering — never
by convention. Verified in tests: an EcoIQ-internal note or another
organisation's private note is never present in a non-staff response
body.

## Withdrawal and stall detection

An organisation may withdraw (`services.rooms.withdraw_organisation()`):
future access is revoked, but every past message, evidence item, and
consent decision is preserved untouched. Any `RoomConsent` still pending
from the withdrawn organisation stays `pending` — never silently
approved or rejected on their behalf; the proposal simply can never
reach consensus. `services.rooms.detect_stalled_rooms()` labels a room
`POSSIBLY_STALLED` in its timeline after a configurable grace period of
no activity — it never auto-closes anything, and repeated sweeps never
duplicate the flag.

## AI assistance — tightly bounded

`services/ai_assist.py` can only ever read room state and return text
(summary, open-questions extraction, a neutral meeting brief). It has no
import of any mutating service — it is structurally incapable of giving
consent, accepting a step, verifying a claim, or creating an action or
project. Every call is instrumented via `ai_observatory` (`kind=
'collaboration_room_ai_assist'`) and reuses the existing
`AnthropicCompatibleAdapter`, which honestly reports unavailability
rather than fabricating a result when no real API credentials are
configured (the same honesty discipline as PR9's `has_real_mail_transport()`).

## Required disclaimers

> A Collaboration Room does not create a partnership, contract, funding
> commitment, procurement commitment, or obligation.

> Agreement to a next step means only that authorised participants
> consented to that specific recorded next step.

Both appear verbatim on every room detail page.

## Known limitations

- No real external representative from an existing real organisation was
  available during this PR to exercise a genuinely cross-organisation
  room (two real, independent companies coordinating). The full loop —
  including a two-organisation introduction with a real consent matrix —
  was verified end-to-end using one internal `[CONTROLLED TEST]`
  organisation for one party and an EcoIQ-coordinator-only room for the
  other, per this PR's own "use controlled organisations for technical
  verification unless real external representatives are genuinely
  available" instruction.
- `verify_resource`/`funding_eligibility_review` proposal types require a
  real, pre-existing `ResourceMatch`/`FundingMatch` row; this PR does not
  add UI to create one from inside a room (that remains the existing
  PR3 need-resource-matching / funding-matching pipeline's job).
- AI assistance requires a real `ANTHROPIC_API_KEY`; this environment has
  none configured, so `services.ai_assist` honestly raises
  `AIAssistanceUnavailableError` rather than fabricating a summary — the
  same pattern already proven for real-email sending in PR9.
