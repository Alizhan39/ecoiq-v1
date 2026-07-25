# Real-World Pilot Launchpad (PR11)

## What this is

PR2-10 built the full canonical truth chain — signal, evidence, 114-principle
relevance, opportunity, human review, action pathway, Capability Graph,
partner participation, governed collaboration rooms, project promotion,
Capital Guardian, execution, MRV, Impact Receipt. Every stage already had a
real model, service, and (mostly) a staff-facing UI.

What did not exist was **one screen** that answers, for one real
opportunity, in under 60 seconds:

> What happened? Why does it matter? What evidence proves it? Which
> principles are relevant? What's the Better Way? Who could help? Why do we
> believe they can help? Have they actually agreed? What has EcoIQ actually
> done? What's blocking progress? What's the single next legitimate action?
> What would execution and measurement require? What impact is genuinely
> verified?

PR11 adds that screen — the **Pilot Launchpad** — plus the small set of
missing staff actions the walk-through revealed were genuinely needed to
answer those questions without Django admin or a shell.

## What this is NOT

- **Not a second project/mission model.** The Pilot Launchpad anchors to the
  existing `good_agents.GoodOpportunity` — the same object `mission_control`
  already features per-mission. No `PilotMission` model was created.
- **Not a second Command Centre.** `command_centre` (deprecated) and
  `capital_guardian.project_command_centre` (real, project-scoped) already
  exist; PR11 does not introduce a third page under that name. The
  opportunity-scoped queues live inside the existing Impact Action Centre.
- **Not a new telemetry system, matching engine, or MRV model.** Every
  function in `good_agents/services/pilot_launchpad.py` is a pure read or a
  thin composition of already-tested PR2-10 services.
- **Not an AI-drafted outreach system.** Outreach pack content is
  deterministic template composition, not a model-router call — see
  "AI boundary" below.

## Architecture

One new file, `good_agents/services/pilot_launchpad.py` — no new app, no new
models, no new migrations. It composes:

- `capability_graph` (Organisation, OrganisationCapability, PublicRoute)
- `partner_participation` (RoutingCandidate, onboarding readiness)
- `collaboration_rooms` (CollaborationRoom, RoomConsent — read-only)
- `capital_guardian.services.execution_monitoring` (capital_summary,
  expected_vs_actual — reused unchanged)
- `good_agents.services.mission_control` (`truth_chain`, extended
  additively, never replaced)

Six new staff-facing views were added, all in `good_agents/views.py`,
mounted under the existing `good_agents` app:

| View | Purpose |
|---|---|
| `pilot_launchpad_view` | The one flagship screen for one opportunity |
| `pilot_launchpad_redirect` | Deterministically selects the flagship pilot |
| `pilot_dossier_view` | Exportable, deterministic dossier |
| `pilot_launchpad_public_view` | Public-safe read view (no login required) |
| `resolve_responsible_party_view` | Closes a real "requires shell" gap (see below) |
| `add_contact_view` | Closes a real "requires admin" gap (see below) |
| `create_outreach_draft_view` | Closes a real "requires a demo script" gap (see below) |

## Flagship pilot selection (Phase 2)

`select_flagship_pilot()` scores every real (non-`[CONTROLLED TEST]`)
opportunity against `flagship_pilot_criteria()` — evidence-backed,
understandable, location known, multi-principle relevance, real organisation
identified, measurable eventually. An opportunity must clear a minimum bar
(evidence + a clear problem statement + at least one activated principle)
even to be scored. If nothing clears the bar, the redirect view shows
`NOT_READY_FOR_PILOT` — never a fabricated "best available" pick.

## Readiness scorecard (Phase 3)

`readiness_scorecard()` returns a fixed 15-item checklist, each item
independently derived from a real row's presence/absence. States are
`READY` / `PARTIAL` / `BLOCKED` / `UNKNOWN` / `NOT_APPLICABLE` — never a
numeric score.

## Truth chain provenance (Phase 5)

`truth_chain_with_provenance()` wraps `mission_control.truth_chain()`
additively — it adds a `provenance` key to each existing node dict without
changing `stage`/`reached`/`detail`, so `mission_control.html`'s existing
usage is unaffected. Provenance vocabulary: `MEASURED`, `VERIFIED`,
`PUBLIC_SOURCE`, `HUMAN_APPROVED`, `PARTNER_DECLARED`, `DETERMINISTIC`,
`ESTIMATED`, `MISSING`, `BLOCKED`, `NOT_YET_OCCURRED`. An unreached stage is
never labelled `MEASURED` or `VERIFIED`.

## Blocker engine and next best action (Phase 13-14)

`blockers()` returns every currently-true blocker (`INSUFFICIENT_EVIDENCE`,
`HUMAN_REVIEW_PENDING`, `NO_VERIFIED_CONTACT_ROUTE`, `NO_PARTNER_RESPONSE`,
`CONSENT_PENDING`, `FUNDING_UNKNOWN`, `EXECUTION_NOT_STARTED`,
`MRV_NOT_AVAILABLE`), each with what's missing, why it matters, who can
resolve it, and — where a real governed action exists — a resolved URL to
take it.

`next_best_action()` walks the SAME canonical chain in priority order and
returns exactly one primary action plus optional secondary actions. It
never suggests an action whose prerequisites are unmet — e.g. it will never
suggest "Send outreach" while the draft is still unapproved, or before an
organisation has even been resolved. This is enforced by regression tests
(`BlockersAndNextBestActionTests`).

Every action link is resolved to a real URL **in Python** via `_link()`
(`django.urls.reverse()`), not as a dynamically-named `{% url %}` tag in the
template — the same lesson PR6 already learned the hard way (Django
templates can't cleanly vary both a URL name and its argument shape per
row). Every one-click action in the template is rendered as a POST form
with a CSRF token, not a plain `<a href>` — several target views are
POST-only mutations (`outreach_approve`, `outreach_send`,
`resolve_responsible_party`, `add_contact`, `project_candidate_approve`);
rendering them as bare GET links would silently do nothing.

## Honest contact/outreach state machine (Phase 11)

`contact_route_state()` computes (never stores) one of: `not_identified`,
`public_route_found`, `draft_prepared`, `human_approved`, `sent`,
`delivery_unknown`, `replied`, `declined`, `no_response`. It is derived
purely from the real `ActionContact`/`OutreachDraft` rows already governed
by PR5's `outreach.py` — no parallel mutable state was added. One explicit
simplification, documented rather than hidden: `READY_TO_SEND` is merged
into `human_approved`, because `OutreachDraft.status == 'approved'` **is**
this pipeline's only readiness gate — inventing a second, separate gate
would have been a fabricated distinction, not an honest one. `sent` always
maps to `delivery_unknown`, never `delivered` — this pipeline has no real
delivery-confirmation mechanism, so it never claims one.

## Real vs. controlled-test labelling (Phase 12/26)

`data_provenance_label(organisation)` returns exactly one of
`REAL_DISCOVERED_ORGANISATION`, `REAL_PARTICIPATING_ORGANISATION` (requires
a real `partner_participation.OrganisationMembership` with
`status='verified_member'` — never inferred from a capability-graph match
alone), or `CONTROLLED_TEST_ORGANISATION` (name starts with the existing
`[CONTROLLED TEST]` convention already used by PR9/PR10's demo commands).
The Pilot Launchpad template and dossier render this label next to every
organisation reference so a screenshot can never make test data look like
real-world participation.

## Three real "no admin/shell required" gaps closed (Phase 27)

The flagship pilot walk-through (see the final report) found three points
in the existing PR5/PR7 chain that could only be operated via Django admin
or a demo management command — never a staff-facing button. PR11 closes
all three with the smallest possible governed action, each staff-only and
POST-only:

1. **Resolving a responsible organisation.** `responsible_party
   .suggest_from_signal()` (PR5/PR7) existed but was never called from any
   view — only from demo commands. `resolve_responsible_party_view` calls
   it against the opportunity's own real originating signal. It still only
   ever produces a `possible_organisation` suggestion; a human must
   separately confirm it, exactly as before.
2. **Recording a verified public contact route.** `add_contact_view`
   creates a real `ActionContact` (public institutional channel + its
   source, never a scraped personal contact) for a `ResponsibleParty`.
3. **Creating an OutreachDraft.** `outreach.create_draft()` (PR5) existed
   but was only ever called from `run_impact_action_network_demo.py`.
   `create_outreach_draft_view` calls it with content pre-filled from the
   new deterministic `render_outreach_message()`, and immediately marks it
   `ready_for_review` — it lands in the existing `outreach_approve` /
   `outreach_send` governance ladder completely unchanged.

## A real regression found and fixed during the walk

`responsible_party.suggest_from_signal()` was passing the **triggering
signal's own per-event region** (e.g. one specific earthquake's epicentre
string) as the resolved organisation's overall `jurisdiction`. Since
`capability_graph.services.organisations.get_or_create_organisation()`
dedupes on `(name, jurisdiction)`, this created a fresh, capability-less
`Organisation` row *per event* instead of resolving to the one real,
evidence-backed USGS row — silently violating that function's own
documented "never duplicated" contract, and exactly the kind of bug PR6's
live demo had already been burned by once (ten separate "USGS" rows across
ten earthquake opportunities — the ORIGINAL bug that motivated
`get_or_create_organisation` in the first place).

The existing regression test for that original bug
(`test_suggest_from_signal_deduplicates_the_same_real_organisation`) used
the same region string for both test signals, so it never actually caught
this. Fixed by adding `PUBLISHER_TO_JURISDICTION`, a small deterministic
map from each KNOWN real publisher to the real, stable jurisdiction its
Capability Graph `Organisation` was actually seeded under (`'Global'` for
USGS, `'England'` for UK Environment Agency) — an unrecognised publisher
still falls back to the signal's own region, the best honest guess
available when the org's real jurisdiction isn't yet known. A new
regression test (`ResponsiblePartySignalJurisdictionRegressionTests`) uses
genuinely different regions per signal, matching real earthquake data.

## AI boundary

No new AI/model-router call was added in this PR. `outreach_pack()` and
`render_outreach_message()` are deterministic template composition over
real, already-persisted fields — a conscious scope decision, not an
oversight: PR11's own brief requires outreach content to be "grounded" and
requires "no unsupported LLM narrative," and every existing AI-assist
integration point in this codebase (`ai_observatory`) already exists for
apps that DO call a model. Since none of PR11's new functions do, no new
`AnalysisSession.kind` was needed.

## Privacy — public-safe view (Phase 24)

`pilot_launchpad_public_view` is deliberately narrow: problem statement,
principle relevance, Better Way rationale/decision-state only (no internal
notes), and the measurement plan's verified values. It never renders
organisation contact details, outreach content, blocker resolution notes,
or capability-graph route values — those exist only on the staff-only
`pilot_launchpad_view`. Verified by
`test_public_view_never_exposes_organisation_or_contact_content`.

## Known limitations

- **Cross-theme routing candidate leakage.** The existing PR8/9 routing
  engine can generate a `RoutingCandidate` for a REAL organisation against
  a `[CONTROLLED TEST]` opportunity if the theme/capability heuristics
  match (observed during the controlled cross-org verification: UK
  Environment Agency was auto-matched against a controlled flood-response
  test opportunity). The candidate stays in the unactioned
  `routing_candidate` state and no real action followed, so no real
  organisation was ever contacted or exposed — but this is a pre-existing
  PR8 routing-engine gap worth a future PR's attention, not something PR11
  introduced or fixed.
- **`capability_graph` still has no staff UI to add a NEW `PublicRoute`**
  for an organisation the way PR11 now lets staff add a good_agents-level
  `ActionContact`. If a future pilot's responsible organisation needs a
  capability-graph-level route recorded (not just an opportunity-scoped
  contact), that still requires Django admin. Left for a future PR.
- **USGS is a monitoring/research authority, not a disaster-response
  agency.** The real flagship pilot walk (an earthquake opportunity)
  legitimately resolves to USGS via its real, evidence-backed `measure`/
  `research` capabilities — an honest, accurate match, but not the same
  thing as "an organisation that can act on this disaster." EcoIQ's current
  real Capability Graph has no seeded disaster-response-capable
  organisation for this theme. UK Environment Agency's real
  `respond_to_emergency` capability (flood risk, England) is the one
  currently-seeded exception, but no real flood signal was available during
  this walk (`UK Environment Agency Real-Time Flood Monitoring: 0 signals`
  at the time it was run).

## Governance disclaimer

Every dossier and public-safe view carries the same statement: *"This
dossier/page does not constitute a partnership, funding commitment,
contract, or verified impact claim. Every field reflects the real, current
state of EcoIQ's records — missing information is shown as Missing, never
inferred."*
