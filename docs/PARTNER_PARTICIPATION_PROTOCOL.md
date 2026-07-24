# Partner Participation Protocol (PR8)

## What this adds

PR7's Capability Graph let EcoIQ **discover** an organisation's
capabilities from external public evidence. This PR adds the reciprocal
half — a real organisation **participating**:

```
ORGANISATION -> CLAIMS/CONFIRMS CAPABILITIES -> DECLARES WHERE IT OPERATES
  -> DECLARES WHAT OPPORTUNITIES IT ACCEPTS -> DECLARES RESOURCE/FUNDING/
  SERVICE AVAILABILITY -> HUMAN/ORGANISATIONAL VERIFICATION -> ROUTING
  ELIGIBILITY -> OPPORTUNITY DELIVERY READINESS
```

This is **not** a marketplace, lead-generation tool, or autonomous
outreach system. Every state that matters — membership, capability
claims, routing candidates — requires an explicit human action to
progress, and nothing here can reach "accepted"/"partnered" on its own.

## Discovered vs participating vs accepting — never conflated

Four distinct, never-blurred states (Phase 17's consent gate):

| State | What it means | How it's determined |
|---|---|---|
| Discovered organisation | Exists in the Capability Graph (PR7) | An `Organisation` row exists |
| Verified organisation | Has at least one independently-verified capability | `OrganisationCapability.verification_state='independently_verified'` |
| Participating organisation | A real user holds a verified membership | `OrganisationMembership.status='verified_member'` exists |
| Accepting opportunities | Has an active preference for this theme | `OpportunityPreference.acceptance_mode` in the routable set |

None of these is ever inferred from another — a real, independently
verified public authority can be "verified" without ever being
"participating" (see Phase 18 below), and a participating organisation is
never automatically "accepting" without its own explicit preference.

## Self-declared vs verified — never conflated

`capability_graph.OrganisationCapability.verification_state` is now a
6-rung ladder (extended, not replaced, from PR7's 4-rung one — no data
migration for existing rows):

```
unverified -> self_reported -> evidence_supported -> documented
  -> human_reviewed -> independently_verified
```

plus two side-states, `disputed` and `expired`, that are never ranked as
"weaker" or "stronger" — they mean "do not treat this claim as reliable
right now," full stop (a real bugfix this PR made to
`capability_graph.services.matcher._VERIFICATION_RANK`, discovered by
this PR's own routing-engine smoke test — see Known Limitations).

A new, orthogonal `provenance` field records WHO originated a claim
(`external_public_evidence` — PR7's original mechanism; `organisation_declared`
— submitted via the partner portal; `ecoiq_reviewed` — a staff member
entered it manually) — never blurred with `verification_state`. An
organisation can self-declare a capability (`organisation_declared`,
`self_reported`) and that fact stays visible even after EcoIQ
independently verifies it.

A bare self-declaration with **no** external evidence is never rejected
outright: it is recorded with `evidence_source` pointing at the real,
attributable `OrganisationMembership` that made the claim (a real
person, a real organisation, a real timestamp — not nothing), but
`verification_state` stays `self_reported` and is never displayed as
verified until a human (the organisation attaching real evidence, or
EcoIQ reviewing/verifying) moves it further.

## Organisation claims — never inferred, always human-gated

`partner_participation.OrganisationMembership` links a real, authenticated
Django user to a real `capability_graph.Organisation`. `request_membership()`
always starts at `claim_requested`; only `review_membership()` — which
raises if the actor isn't real EcoIQ staff — can move it to
`verified_member` or `rejected`. There is no email-domain matching, no
organisation-name matching, no auto-approval path anywhere in this code.

Roles (`admin`/`editor`/`routing_manager`/`reviewer`/`viewer`) are a plain
frozenset check, not a permissions framework (Phase 3's own
"do not overengineer RBAC" instruction) — only `admin` can manage
critical declarations; `admin`/`editor` can edit; `routing_manager` can
additionally respond to routing candidates.

## Opportunity preferences — a signal, never a guarantee

`OpportunityPreference` reuses `good_agents`' own theme taxonomy (never a
second one) and never implies acceptance of any specific opportunity —
only a real acceptance-mode signal (`open_to_relevant_opportunities` /
`limited` / `invitation_only` / `application_required` / `not_accepting`
/ `paused`). Routing requirements (min evidence quality, eligible
beneficiary type, deadline, project-size range, Sharia-review flag,
regulatory prerequisites) live on the same row — real, optional, never
invented for an organisation that hasn't stated them.

## Resources and funding — reuse, not a parallel system

Per the brief's own explicit instruction: `good_agents.AvailableResource`
gained nullable `organisation`/`declared_by` fields rather than a new
resource model. `FundingProgrammeDeclaration` is new (a durable programme
record `good_agents.FundingMatch` — scoped to one opportunity — has no
room for), but it never claims a programme is halal; it only ever sets
`requires_sharia_review`, structurally forced `True` for waqf/Islamic-finance
funder types exactly like `FundingMatch.save()` already does.

## Public routes — history, never silent overwrite

`propose_route_update()` logs a `PublicRouteRevision` (previous value, new
value, who, why) **before** mutating the live `PublicRoute` row — every
prior value survives. A partner-proposed edit never sets `verified_at`
on its own; only a separate EcoIQ action can.

## Conflicting evidence — never silently overwritten

`services/conflicts.py` detects when an organisation's own declaration
disagrees with existing evidence for the same capability (different
jurisdiction or materially different limitations) and creates a real
`CapabilityConflict` row — both claims stay real, distinct rows. Only
`resolve_conflict()`, staff-gated, can close it, with a permanent audit
trail (`resolution`, `resolved_by`, `resolved_at`, `resolution_notes`).

## Staleness — nothing is current forever

`reconfirmation_due_at` with no value set means "no schedule exists yet,"
never "permanently fresh." `staleness_of()` reports `no_schedule_set` /
`current` / `stale` / `expired` honestly; `reconfirm()` requires a real
actor; `sweep_expire_stale()` is the one time-based function in this
module (mirrors `good_agents.services.notify.sweep_funding_deadlines`'s
own precedent) — meant to run periodically, not from a request handler.

## The routing engine (Phase 18-20)

`services/routing.generate_routing_candidates(opportunity)` composes
PR7's `find_organisations_for_capability()` with the new participation
signals (verified membership, opportunity preference, open public route)
into `RoutingCandidate` rows — real, deterministic, no ML/embeddings.
Every candidate carries `match_reasons` (real facts: capability +
verification state, jurisdiction, topic, limitations, preference match,
participation state, route availability — Phase 19's own routing
explanation requirement) and a `confidence_label` from a fixed, honest
vocabulary — never a numeric "AI confidence" score:

```
strong_verified_match > verified_capability_match > participation_match
  > possible_responsible_party ; needs_review ; no_verified_route
```

**Participation is one signal, not universal authority** (Phase 18): a
real, independently-verified public authority with zero partner-portal
engagement still ranks `verified_capability_match` — never unfairly
excluded for not participating. Organisations whose preference is
`not_accepting`/`paused` are never created as routing candidates at all
(Phase 8) — they appear in a `skipped` list with the real reason instead
of a silent drop.

`RoutingCandidate.status` is a 9-state, transition-validated state
machine mirroring PR5's `ActionGate` discipline —
`approved_to_share`/`shared` require a real EcoIQ staff actor (visibility
to the organisation is always an explicit EcoIQ decision); an org's own
response path (`viewed` → `interested`/`needs_more_information` →
`accepted_for_next_step`, or `not_interested` at any point) can never
skip a step. `accepted_for_next_step` still means only that the
**organisation** expressed interest — never that EcoIQ or the
organisation has partnered, committed capital, or executed anything.

## Partner Portal — the first non-staff-facing surface in this lineage

Every prior good_agents/capability_graph view was `@staff_member_required`.
`/partner-network/<org_pk>/portal/` is gated by a new
`membership_required()` decorator requiring a real, authenticated user
with a `verified_member` row — never staff-only, never public. Internal
EcoIQ review notes (`review_notes`, `resolution_notes`) are never
rendered in any partner-facing template (Phase 15/29's own privacy rule;
tested directly).

## Mission Control integration

A new compact section shows, per the featured opportunity's resolved
organisation: capability verified?, participating?, accepting this class
of opportunity?, verified route?, resource/funding available?, connection
consent state — a pure read, never a recomputed decision, linking to the
full Capability Graph organisation record.

## Observatory

`generate_routing_candidates()` is instrumented via the SAME
`ai_observatory` session/stage/finish helpers PR4/6 already built (a new
`partner_routing` `AnalysisSession` kind, added to
`NO_ANCHOR_ALLOWED_KINDS` since one routing run spans an opportunity
against many candidate organisations, not one project/company) — no
second telemetry architecture.

## Security

- Every partner-facing view requires login; every mutation additionally
  requires a real `verified_member` role check (`editor_required`) —
  tested for 403s on non-members, wrong roles, and cross-organisation
  access.
- Every mutation is CSRF-protected (tested with `enforce_csrf_checks=True`).
- No arbitrary organisation takeover: membership can only reach
  `verified_member` through a real staff review call, never through
  request data alone.
- `evidence_url`/`route_value`/`official_source_url` are stored as plain
  strings/`URLField`s — this app never fetches them server-side (no
  `requests`/`urllib` calls anywhere in `partner_participation` or the
  extended `capability_graph` code), so there is no SSRF surface to
  defend in this PR; they are only ever rendered as `<a href>` links for
  a human to click.
- No external send without approval: outreach/connection sending remains
  PR5's existing, unmodified, human-approved mechanism — this PR only
  ever creates a `RoutingCandidate`, never sends anything itself.

## Known limitations / deferred

- **A real bug in PR7's matcher was found and fixed during this PR's own
  work**: `capability_graph.services.matcher._VERIFICATION_RANK` didn't
  know about the four new `verification_state` values this PR adds, so
  `find_organisations_for_capability()` silently returned zero matches
  for any `evidence_supported`/`human_reviewed` capability regardless of
  `min_verification` — caught by this PR's own routing-engine smoke test
  before it shipped, not by a user report.
- `RoutingCandidate` has no dedicated per-transition audit log the way
  `ActionGate` does (`ActionGateTransition`) — status + timestamps
  (`shared_at`, `responded_at`) + notifications provide today's audit
  trail; a full transition log is a reasonable next PR if routing volume
  grows.
- Capital Guardian and company intelligence remain named-but-deferred
  consumers of the Capability Graph (as in PR7) — this PR does not wire
  them; `find_organisations_for_capability()`/`generate_routing_candidates()`
  are generic enough for either to call without changes here.
