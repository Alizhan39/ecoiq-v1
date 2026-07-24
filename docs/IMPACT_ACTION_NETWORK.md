# Impact Action Network (PR5)

## What this is

PR2 built the 114 Good Agent lenses. PR3 built continuous discovery,
need/resource matching, and the Morning Brief. PR4 replaced fixture
signals with real, bounded public-source ingestion. None of those PRs let
a discovered opportunity turn into a real-world action — a `GoodOpportunity`
just sat there, evaluated but unactioned.

PR5 closes that gap with a **governed** pipeline:

```
GoodOpportunity (discovered)
  -> ActionGate (human review/approval — the ONE authoritative "what next" state)
  -> ActionPathway (the concrete next step a human chose)
  -> ResponsibleParty (who this is really about, provenance-only, never a guess)
  -> Outreach / Connection (AI drafts, human approves, human sends)
  -> ProjectCandidate -> real gold_intelligence.GoldProject
       -> the EXISTING, unmodified capital_guardian / MRV / Evidence Memory chain
  -> ActionTimelineEvent (append-only, one row per real event, never edited)
```

Every arrow above requires an explicit human decision except the first
one (`get_or_create_gate`, which just materialises the starting state
'discovered' — that's model instantiation, not a governed decision, and is
itself logged as the first `ActionGateTransition`). **Nothing in this app
can move an opportunity past `discovered` on its own.**

## Autonomy classes carried over from PR2

- GREEN — safe automation. Creating an `ActionGate` at 'discovered',
  suggesting a `ResponsibleParty` from a signal's own publisher field, and
  drafting outreach text are all GREEN: they never touch anything external
  and never imply agreement from anyone.
- YELLOW — human approval required before an external-facing action.
  Every `ActionGate.transition()` call, every `OutreachDraft.approve()`,
  every `ConnectionCandidate.approve_for_introduction()`, every
  `ProjectCandidate.approve_candidate()` is YELLOW: each one requires a
  real `actor` (several raise if `actor is None`) and is recorded in an
  append-only audit trail.
- RED — never auto-executed, structurally unreachable. Real email send
  (`outreach.send_outreach`) only runs from `status='approved'`, never
  from `'draft'` — there is no code path around it. Real `GoldProject`
  creation (`project_bridge.create_project_from_candidate`) only runs from
  `ProjectCandidate.status='approved'`. `mrv_status='verified'` can never
  be set through this app's own code at all — see the MRV section below.

## Action Gate

`good_agents.models.ActionGate` — one row per opportunity (`OneToOneField`),
`current_state` in `discovered / needs_review / approved_for_contact /
approved_for_research / approved_for_project_creation / rejected /
needs_more_evidence / duplicate / not_actionable`. `ALLOWED_TRANSITIONS` is
a hardcoded adjacency map; `services.action_gate.transition()` is the only
function that can change `current_state`, and raises
`IllegalTransitionError` for anything not in that map — never coerces.
Every transition creates an `ActionGateTransition` row (actor, previous
state, new state, reason, evidence_reviewed) and mirrors onto
`ActionTimelineEvent`.

This is deliberately a **different** system from PR3/4's
`HumanReviewDecision`: that model is an accumulating many-to-one feedback
signal that feeds `PrioritisationEngine`'s ranking adjustment (see
`_pattern_feedback` in `services/prioritisation.py`). `ActionGate` is the
single current authoritative "what happens next" governance state. They
serve genuinely different purposes despite similar-sounding labels, so
this PR keeps them separate rather than merging two systems that aren't
actually duplicates.

Every real discovered opportunity gets its `ActionGate` created
automatically the moment `discovery_engine.run_global_discovery` creates
it (Phase 1) — so it shows up in the Impact Action Centre's "awaiting
review" queue immediately, not only after someone happens to open its
detail page.

## Action Pathway

`services.action_pathway.create_pathway()` requires the opportunity's gate
to already be in one of `ActionGate.APPROVED_STATES` — raises
`PathwayNotAllowedError` otherwise. `ZERO_CAPITAL_ELIGIBLE_PATHWAY_TYPES`
(`information_request`, `introduction`, `resource_connection`,
`authority_alert`, `expert_review`, `data_request`, `zero_capital_action`)
auto-set `capital_required='no'` — deliberately excludes
`project_candidate` and `funding_referral`, since those always need an
explicit capital assessment from the caller, never an assumption.

## Responsible Party

`services.responsible_party.suggest_from_signal(opportunity, signal)`
never fabricates a party from free text — it only maps a real signal's
own `publisher` field through a small, hardcoded, real lookup
(`PUBLISHER_TO_PARTY_TYPE`, covering the actual publisher strings PR4's
real provider adapters emit: `GOV.UK`, `UK Environment Agency`, `USGS`).
No publisher on the signal → returns `None`, an honest unresolved case the
caller must surface, not paper over. Every suggestion starts at
`possible_organisation`; only `confirm()` (requires a real `actor`) can
move it to `known_organisation`.

## Contact safety

`ActionContact.public_contact_channel` is a plain string field with no
scraping logic anywhere in this app — every contact record is created by
an explicit service/admin call with a value a human supplied or confirmed.
`source_of_contact_info` always records where the channel came from. No
code path in `good_agents` fetches, scrapes, or infers a private personal
address.

## Outreach governance

`OutreachDraft.status`: `draft -> ready_for_review -> approved -> sent`
(plus `replied / no_response / declined / follow_up_required`).
`services.outreach.approve()` requires a real `actor` — raises
`OutreachNotApprovedError` if `actor is None`.
`services.outreach.send_outreach()` is **the only function in this app**
that can set `status='sent'`, and it refuses unless `status == 'approved'`
(no `'draft' -> 'sent'` shortcut exists) and unless the linked
`ActionContact.public_contact_channel` is real and email-shaped. It sends
through this repo's existing, already-configured `EMAIL_BACKEND` (the same
one `core/views.py`, `leads/views.py`, `heating/emails.py` already use) —
no second sending system.

## Connection lifecycle

`ConnectionCandidate.status`: `candidate_match -> approved_for_introduction
-> introduced -> {interest_confirmed | not_suitable | declined | expired}`.
Only `record_outcome()` can set a terminal status, and only from the
values in `TERMINAL_STATES` — never implies agreement was reached until a
human explicitly records it.

## Funding actions

`FundingAction.status` never defaults to `'awarded'`. Grant application
automation is explicitly out of scope for this PR — `update_status()` just
tracks state a human reports. `FundingMatch.save()` (PR3, unchanged)
already structurally prevents `waqf`/`islamic_finance` funder types from
ever landing on `eligibility_status='eligible'` — this PR adds one more
guard on top: `update_status()` raises if a caller tries to mark such a
match `'awarded'` while it still requires Sharia review.

## Project Candidate bridge

`services.project_bridge.create_project_from_candidate()` is **the only
function in this app that creates a real `gold_intelligence.GoldProject`**.
Requires `candidate.status == 'approved'` (set only by `approve_candidate`,
which itself requires a real `actor`). `is_demo` has no default — every
caller must state explicitly whether this is real or demo data, matching
`seed_clean_heating_pilot.py`'s own discipline. Every gold-specific/
technical/financial field (`ore_grade_g_per_tonne`, `total_capex_usd`,
`gold_price_assumption_usd_per_oz`, ...) is left `None` — this function
never fabricates a plausible-looking number for any of them. Idempotent:
the `created_project_id` check runs **before** the `status == 'approved'`
check, so a second call with the same candidate returns the existing
project rather than incorrectly raising (the first call already advanced
`status` to `'created'`, which is not `'approved'`).

Once created, the project flows through the existing, completely
unmodified `capital_guardian` / `waste_to_value_capital_allocation_engine`
pipeline exactly like any other `GoldProject` — this PR does not touch
that pipeline at all.

## Execution / MRV / Impact Receipt / Evidence Memory — closing the loop

`GoodOpportunity.status` has always had `measured` / `verified` choices
that nothing ever set (PR2/3/4 only ever left opportunities at `potential`
/ `qualified` / `approved` / `in_progress`). PR5 closes this:

- `services.pipeline.record_verified_outcome_and_sync()` (PR3, extended)
  now also advances `opportunity.status` to `'measured'` and records an
  `outcome_measured` timeline event + notification whenever a human
  records real after-data. It can **never** reach `'verified'` through
  this path: `capital_guardian.services.execution_monitoring
  .record_monitoring_outcome()` structurally refuses
  `mrv_status='verified'` (a deliberate PR6-era safety gate — "the same
  user entering a result does not automatically make it independently
  verified").
- The **only** real path to independent verification in this whole repo is
  a staff member editing the existing `VerifiedCapitalOutcome` admin
  change form directly. `good_agents/signals.py` listens for that exact
  event (`post_save` on `VerifiedCapitalOutcome` where `mrv_status ==
  'verified'`) and, only then, advances the linked `GoodOpportunity.status`
  to `'verified'`, records `outcome_verified` + `evidence_memory_updated`
  timeline events, and fires the `verified_impact_achieved` notification.
  It never fires twice for the same opportunity (checks
  `opportunity.status == 'verified'` first) and never fires on the
  ordinary monitoring path, since that path is structurally prevented from
  ever setting `mrv_status='verified'` in the first place.

This means the loop genuinely closes onto the Evidence Memory system PR2
already wired (`create_memory_from_verified_outcome`) — no second
verification workflow, no second "mark as verified" button anywhere in
`good_agents`.

## Action Timeline

`ActionTimelineEvent` — one append-only row per opportunity per real
event (`discovered`, `human_reviewed`, `action_approved`, `owner_assigned`,
`outreach_drafted`, `outreach_approved`, `sent`, `reply_received`,
`connection_made`, `project_created`, `execution_started`,
`outcome_measured`, `outcome_verified`, `evidence_memory_updated`). Never
edited, never deleted, ordered by `created_at`. `actor=None` means the
event was system-recorded (e.g. the initial `discovered` event), never a
fabricated human action.

## Impact Action Centre

`/good-agents/action-centre/` (staff-only) — ten live queries, no static
mockup sections: awaiting review, approved actions in progress,
zero-capital actions ready, connections in play, funding candidates,
project candidates, outreach awaiting approval, active real-world
projects, outcome verification pending, recent verified impact. Every
count and every row comes straight from the database at request time.

## Morning Brief — Top 3 Actions upgrade

`services.morning_brief.top_3_actions()` (PR3/4, extended) now returns,
per action: why now (the same urgency/evidence-gap/leverage labels
`PrioritisationEngine` already computes), evidence quality, relevant
principles, the opportunity's current `ActionPathway` (type, capital
required, owner, next step, due date, progress state), and human approval
status straight from its `ActionGate`. An opportunity whose gate is still
`discovered`/`needs_review` is labelled **"Needs human review"**, never
shown as though it were already actionable.

## Learning from real action outcomes

`services.prioritisation._action_outcome_feedback()` (new, alongside the
PR4 `_pattern_feedback` human-review feedback) applies the same
deterministic, fully-documented, ranking-only adjustment discipline to
real ACTION outcomes sharing an opportunity's theme: 2+ prior
rejected/not-actionable `ActionGate`s reduce ranking confidence by 10;
2+ prior completed zero-capital `ActionPathway`s boost it by 5; 2+ prior
declined `ConnectionCandidate`s reduce it by 8 (a proxy for "matches for
this theme keep turning out to be poor-fit — require stronger
compatibility"). Every adjustment and its exact reason is visible in
`PrioritisationResult.feedback_reasons` — never an opaque learned score.

## Notifications

`services/notify.py` (PR4, extended) adds real, per-mutation, deduplicated
notifications for: a zero-capital pathway becoming ready, a connection
candidate being created, an outreach draft reaching `ready_for_review`, a
reply being recorded, a project candidate being proposed, an outcome being
measured, and verified impact being achieved. `sweep_funding_deadlines()`
is the one time-based (not event-based) check — it's meant to be called
periodically (wired into `run_good_while_you_sleep`) since "a deadline is
approaching" depends on the passage of time, not a discrete mutation.

## External communication safety

Nothing in this app ever impersonates an individual, makes a financial,
legal, or religious promise on EcoIQ's behalf, or claims EcoIQ represents
a government or funder. `OutreachDraft.body` is free text a human reviews
and approves before send — this PR does not validate its content
semantically, but no code path can send it without that human approval
step.

## Required disclaimers

Every real discovery/action page in this pipeline inherits PR2/3/4's own
disclaimer discipline:

- Demo/fixture data is always labelled `is_demo=True` on the created
  `GoldProject`, and demo command output always states plainly that the
  underlying signals/figures are fixtures, never real disclosures.
- Impact figures stay namespaced ESTIMATED / TARGET / MEASURED / VERIFIED
  (`ImpactReceipt.measured_result['stage']`, `GoodOpportunity.status`) —
  never collapsed into a single unqualified number.
- `run_impact_action_network_demo`'s real half (Part A) never claims a
  human reviewed anything it didn't actually route to a human; its
  simulated half (Part B) labels every approval `[SIMULATED APPROVAL]`.

## Demo command

```bash
python manage.py run_impact_action_network_demo
```

Part A fetches real live signals from the same bounded providers PR4
wired up, runs real discovery, and shows the real `ActionGate` this repo
now creates automatically — then stops, honestly, at the human-review
boundary. Part B walks the rest of the pipeline (approve → pathway →
responsible party → outreach draft → project candidate) against clearly
labelled `[DEMO]` data, with every approval printed as
`[SIMULATED APPROVAL]`, and stops one step short of outreach send / project
creation even for demo data.
