# Trusted Partner Activation (PR9)

## What this adds

PR7 built the Capability Graph (discovery). PR8 built Partner
Participation (a two-sided consent gate: claim, declare, verify). PR9
closes the loop with a real, small-scale **activation**:

```
REAL ORGANISATION -> VERIFIED PARTICIPATION -> DECLARED/VERIFIED CAPABILITY
  -> OPPORTUNITY PREFERENCE -> REAL OPPORTUNITY -> ROUTING CANDIDATE
  -> HUMAN APPROVAL TO SHARE -> REAL DELIVERY THROUGH A VERIFIED ROUTE
  -> REAL RESPONSE STATE -> NEXT ACTION / PROJECT CANDIDATE
```

This is the first PR in this lineage where every step of the loop is
made to actually run against real data, not just be architecturally
possible. It adds no new discovery or matching logic — it adds
invitation, consent, human-approved sharing, honest delivery, response
capture, and governed next steps around the PR7/PR8 machinery.

## Invitation lifecycle

`PartnerInvitation` states: `draft -> sent -> accepted`, with `expired`
and `revoked` side-states. A token (`secrets.token_urlsafe(32)`, unique,
single-use) gates acceptance. An invitation is never marked `sent` unless
a real send event occurred — either a real outbound email, or a staff
member explicitly confirming they delivered it manually.

### Real send vs. manual delivery — never faked

`services/invitation.has_real_mail_transport()` checks the configured
`EMAIL_BACKEND` against the known non-real backends (console, locmem,
dummy, file-based). Locally, and in any environment without real SMTP
credentials configured, this is `False`.

- If real mail transport exists, `send_invitation()` calls Django's own
  `send_mail()` (the same infrastructure PR5's `outreach.send_outreach()`
  uses — no second communications stack) and marks the invitation `sent`
  with `send_status='sent_real_email'`.
- If it does not, `send_invitation()` raises `ManualDeliveryRequiredError`
  **without changing the invitation's status** — it never pretends a
  console-backend "send" was real. The caller (the Activation Dashboard)
  then surfaces the exact subject/body via
  `render_invitation_message()` so a human can deliver it themselves
  (email client, phone, in person), then calls `mark_manually_sent()` to
  record that a human takes responsibility for the real delivery having
  happened.

Accepting an invitation still only ever creates a `claim_requested`
`OrganisationMembership` — a real EcoIQ staff review is still required
before it becomes `verified_member`, exactly as PR8 requires for any
other membership claim. Being invited never bypasses review.

## Partner consent — explicit, never inferred

`ParticipationConsent` is a real, auditable row created only by
`services/consent.record_consent()`, which requires the acting user to
be the exact membership holder (never staff acting on their behalf, and
never inferred from account creation or from a membership merely
existing). A verified member with no consent record is not
routing-ready. Consent can be withdrawn by the same real holder at any
time, which immediately removes the organisation from routing
eligibility.

## Onboarding checklist and the eight trust states

`services/onboarding.onboarding_checklist()` returns real, per-step
booleans computed fresh on every call — never a stored, staleness-prone
"100% complete" flag, and never fabricated. Phase 18's eight distinct
trust states are kept genuinely separate, never collapsed into one
"trusted partner" badge:

1. Organisation identity verified
2. Membership verified
3. Capability self-declared
4. Capability evidence-supported
5. Capability human-reviewed
6. Public route verified
7. Participation consent active
8. Routing ready (the AND of specific minimum requirements below — see
   `services/onboarding.is_routing_ready()`)

`is_routing_ready()` requires, all simultaneously: a verified membership,
active consent, at least one usable (non-disputed, non-expired)
capability with a defined jurisdiction that is not entirely stale, an
opportunity preference in a routable acceptance mode, a currently-open
public route, and no unresolved capability conflict. It always returns
the exact list of what's missing when `False` — never a silent "not
ready."

## Routing candidate lifecycle (extended)

PR8's `RoutingCandidate.status` machine gains two states this PR
requires — `not_approved` (a real reviewer declined to share; terminal)
and `no_response` (an honest label for "shared, no reply yet", not an
assumption of disinterest) — and the full, extended, illegal-jump-blocked
transition table:

```
routing_candidate -> ready_for_ecoiq_review -> {approved_to_share | not_approved | not_interested}
approved_to_share -> shared
shared -> {no_response | viewed | not_interested}
no_response -> {viewed | interested | not_interested | needs_more_information}
viewed -> {interested | not_interested | needs_more_information}
interested -> {needs_more_information | accepted_for_next_step | not_interested}
needs_more_information -> {interested | not_interested}
not_approved / not_interested / accepted_for_next_step -> (terminal)
```

`approved_to_share` and `shared` may only be set by a real EcoIQ staff
actor — enforced in `services/routing.transition()`, not just by
convention.

## Human approval before any share

The Activation Dashboard's share-confirm screen
(`share_confirm_view`/`share_confirm.html`) is a GET-only inspection
step: it shows the real recipient route, the real capability match
reasons, the exact share package content (problem statement, source
evidence, location, relevant principles, why matched, requested next
step, known unknowns, confidentiality status — every field read from
already-persisted rows, nothing inferred or invented), and the exact
message that would be sent. Only after a real staff member inspects all
of this can they `approve_share()` or `reject_share()`. Nothing here is
ever auto-approved.

## Real delivery — never fabricated

`RoutingCandidate.status` never reaches `shared` without a real
`ShareDelivery` row backing it:

- `deliver_via_real_email()` requires both a real mail transport AND a
  real, currently-open, email-shaped public route for the organisation.
  If either is missing, it raises `DeliveryError` and leaves the
  candidate at `approved_to_share` — it never silently marks something
  shared.
- `record_manual_delivery()` is the honest alternative: it requires a
  real, non-empty recipient and channel description (phone call, hand
  delivery, referral) — a human explicitly asserting responsibility for
  a real delivery that happened outside this system.

## Response capture — real states only

`services/response_capture.record_response()` (any channel, EcoIQ staff)
and `partner_self_service_response()` (the organisation's own verified
editor/admin/routing-manager member, through the Partner Portal) both
move a candidate through the *same* real state machine. Neither can ever
reach `approved_to_share`/`shared` — those stay exclusively staff/
delivery-service actions. Partner self-service is deliberately narrow:
Interested / Not interested / Needs more information / Accept for next
step only — never approving funding or claiming impact, which remain
Capital Guardian/EcoIQ-staff-governed elsewhere in this repo.
`mark_no_response_if_stale()` only ever applies an honest label ("no
reply yet after N days") — never a fabricated reply.

## Next-step creation — governed, never auto-escalating

`services/next_step.py` requires the organisation to have already
expressed real interest (`interested` or `accepted_for_next_step`)
before any next step can be created. `propose_project_candidate()` never
creates an active project directly — it calls the exact same
human-approval-gated `good_agents.services.project_bridge.propose_candidate()`
PR5 already built, which itself still requires a further explicit
approval and creation step before any real `gold_intelligence.GoldProject`
exists (see
[`docs/adr-0001-canonical-project-architecture.md`](adr-0001-canonical-project-architecture.md)).
`create_connection_action()`/`create_resource_match_followup()`/
`create_funding_eligibility_review()` similarly only ever create a
soft-pointer record referencing the real, existing PR3/5 mechanisms —
never a duplicate of them.

## Network activity timeline

`NetworkActivityEvent` is append-only (`Meta.ordering=['created_at']`;
the service layer only ever calls `.objects.create()`, never mutates or
deletes an existing row) and records every real state change this PR
introduces — invitations sent/accepted, consent recorded/withdrawn,
shares approved/declined/delivered, responses, next steps — giving a
real, auditable history per organisation.

## Feedback to routing — deterministic, never opaque

`services/feedback.historical_feedback_adjustment()` looks at an
organisation's own real prior `RoutingCandidate` outcomes for the same
theme and nudges a NEW candidate's confidence label up or down by simple,
explainable, rule-based thresholds (repeated `not_interested` lowers it;
repeated `interested` raises it, within the existing tier ladder) —
never machine-learned, never opaque, and always reproducible from the
same inputs.

## Activation Dashboard and Mission Control

The Activation Dashboard (`/partner-network/staff/activation-dashboard/`)
shows only real, live counts — pending invitations, verified
memberships, participating and routing-ready organisations, candidates
awaiting share review, delivered shares, pending responses, interested/
declined counts, and open next-step actions — never vanity metrics. It
sits alongside (not in place of) PR8's Network Overview.

Mission Control's existing partner-participation section (PR8 Phase 26)
gains, for the featured opportunity's resolved organisation: whether it
is genuinely routing-ready and why not if not, and — where a real
routing candidate exists for that exact opportunity — its live share/
delivery/response state and most recent next action, each linking
through to the real record rather than duplicating its state.

## Privacy and security

- Invitation tokens are `secrets.token_urlsafe(32)` (256 bits of entropy),
  unique, single-use (`accept_invitation()` requires `status == 'sent'`
  and immediately flips to `accepted`), and time-limited (`expires_at`,
  swept by `sweep_expire_invitations()`).
- Accepting an invitation requires a real login; the acceptance view
  never trusts a `next`/redirect parameter from the request — every
  redirect target in this PR's views is a hardcoded named URL.
- Every mutation view that changes real state is either
  `@staff_member_required` or membership-role-gated
  (`@editor_required`/`@any_member_required`, PR8's own decorators) —
  never open to an unauthenticated or unrelated user.
- Cross-organisation isolation: a routing candidate, membership, or
  consent row is always scoped to its own organisation; a verified
  member of Organisation A can never respond to, view review notes for,
  or otherwise act on Organisation B's records (see
  `partner_participation/tests_pr9.py::CrossOrganisationIsolationPR9Tests`).
- Internal EcoIQ review/rejection notes are never exposed on any
  partner-facing (non-staff) template — the same rule PR8 established.
- No unsolicited mass outreach: invitations are created one at a time by
  a real staff member for a real organisation; there is no bulk-invite or
  scheduled-blast mechanism anywhere in this PR.

## Required disclaimers

Every partner-facing share, portal, and dashboard surface in this PR
carries, verbatim, both of the following:

> EcoIQ routing an opportunity to an organisation does not create a
> partnership, obligation, endorsement, or commitment.

> Interest in an opportunity does not mean funding, implementation, or
> impact is guaranteed.

## Known limitations

- No real external representative from an existing real organisation
  (e.g. USGS, UK Environment Agency) was available during this PR to
  complete an actual outbound invitation and acceptance. The full loop
  was verified end-to-end using one internal `[CONTROLLED TEST]`
  organisation created solely for verification — the real organisation
  records seeded in PR7/PR8 were left untouched. See the demo command
  (`manage.py run_trusted_partner_activation_demo`) for exactly what ran
  and what did not.
- This environment's `EMAIL_BACKEND` defaults to the console backend
  locally with no real SMTP credentials configured — `send_invitation()`
  and `deliver_via_real_email()` both correctly refuse to claim a real
  send under these conditions rather than fabricate one. In a deployed
  environment with real SMTP configured, both functions send for real
  without any code change.
- Routing still depends entirely on PR7/PR8's deterministic
  keyword/capability-overlap scoring — no ML/embeddings were introduced
  by this PR, by design.
