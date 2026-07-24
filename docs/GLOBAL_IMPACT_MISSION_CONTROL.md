# Global Impact Mission Control (PR6)

## What this is

PR2 built the 114 Good Agent lenses. PR3 built continuous discovery and
Need/Resource/Funding matching. PR4 replaced fixtures with real signal
ingestion. PR5 built the governed action pipeline (Action Gate → Pathway
→ Responsible Party → Outreach/Connection → Project Candidate → real
project). Each of those PRs shipped its own page. PR6 does not add a new
subsystem — it is a single flagship operating surface,
`/good-agents/mission-control/`, that reads across all of them and shows
one coherent, traceable truth chain:

```
real signal → evidence → 114 Good Agents → qualified opportunity
  → human review → action pathway → zero-capital/resource/funding option
  → responsible party → connection/outreach → project candidate → project
  → execution → MRV → verified outcome → Impact Receipt → Evidence Memory
```

Everything in `good_agents/services/mission_control.py` is a **read**:
it queries already-persisted rows or calls an already-existing, already-
tested pure function (`evidence_gate.evaluate_cluster`,
`orchestrator.count_shortlisted`, `capital_guardian.services
.execution_monitoring.expected_vs_actual`) purely for transparent display.
No discovery, agent activation, project creation, MRV recording, or
Evidence Memory write happens anywhere in this module.

**Mission Control shows evidence and governed action state. It does not
imply that every opportunity is feasible, funded, accepted, executed, or
impactful.**

## The flagship mission

One real, enabled `GoodMission` — `Global Real-Time Signal Monitoring
(Live Public Sources)` — the same mission PR4's `run_good_while_you_sleep`
already runs by default, now also anchoring PR6's Mission Control
(`mission_control.FLAGSHIP_MISSION_NAME`). Its description was updated to
state the flagship framing directly: "Find evidence-backed opportunities
where useful action can reduce avoidable harm or create measurable public
benefit, prioritising zero-capital and low-capital pathways first." No
second mission was created — reusing the real, already-scheduled one
avoids a confusing "which mission is the real one" split.

## Signal funnel — state honesty about what's mission-scoped

`GoodDiscoveryRun` rows are genuinely mission-scoped (`mission_config` FK,
so `signals_reviewed`/`duplicates_removed`/opportunity counts are exact).
`WorldSignal`/`SignalCluster`, however, are a shared global pool ALL
missions triage from — `discovery_engine.py` itself re-derives
`status='open'` clusters fresh on every run regardless of which mission is
running, specifically so a second mission can reconsider a cluster an
earlier mission's triage saw but didn't claim. Mission Control reports
signal/cluster-level counts honestly as **pool-wide**, not fabricating a
false per-mission boundary the schema doesn't actually have — with a
one-line disclosure directly in the Signal Funnel section.

## Noise visibility

A real sample of `SignalCluster` rows with `status='discarded'`, each
paired with the **same deterministic reason** `evidence_gate
.evaluate_cluster()` produced when it was triaged — recomputed purely for
display (a pure function over already-stored, unchanged fields; the real
decision already happened and is reflected in `status='discarded'`, this
just re-derives why in human-readable form rather than storing the string
twice).

## 114-principle transparency — never implies 114 LLM calls

For the featured opportunity: `114` principles available (a real count),
`shortlisted` (real — via a new `orchestrator.count_shortlisted()` helper
that reuses the exact same deterministic keyword-overlap scoring
`classify_relevant_agents()` already uses internally but discards after
slicing to `max_activated`), `activated` (the real, persisted
`AgentActivationRecord` count), and `useful_reasoning_outputs` (activations
that actually produced a reason/recommendation, not just a mechanical
match). Each activation is labelled `deterministic` or `model-assisted`
based on its real `cost_usd` (`>0` means a model call happened) — never a
guess.

## Zero-capital-first lane

Every real `ActionPathway` for the mission's opportunities, showing
`capital_required` in its own words ("No" / "Yes" / "Unknown" — never
collapsed to a boolean), the real rationale, the real next step, and that
human approval is always required (structural: `services.action_pathway
.create_pathway()` cannot run until the opportunity's `ActionGate` is
already in an approved state).

## Responsible party / outreach / connection truth states

Never shows "contacted" for a mere draft, never shows "accepted" for a
proposed connection. Every row prints the model's own real `status`/
`resolution_status` field — `OutreachDraft.status` stays `draft` /
`ready_for_review` / `approved` / `sent` / ... exactly as PR5 defined it;
`ConnectionCandidate.status` stays `candidate_match` /
`approved_for_introduction` / ... likewise. Mission Control adds no new
state vocabulary of its own.

## Project bridge / Execution / MRV

`project_bridge_chain()` walks originating signal → opportunity →
activated principles → review decision → action pathway → project
candidate → created project, all soft-linked, never a fabricated
provenance chain. `execution_mrv_for_project()` reuses
`capital_guardian.services.execution_monitoring.capital_decisions_for_project()`
and `expected_vs_actual()` — the exact same functions Capital Guardian's
own execution monitoring UI uses — so Mission Control's numbers can never
silently disagree with Capital Guardian's.

## Verified impact / Impact Receipt / Evidence Memory loop

`verified_impact_list()` only ever returns opportunities whose real
`status == 'verified'` — set only by the PR5 signal reacting to a staff
member editing the `VerifiedCapitalOutcome` admin form directly (the one
real path to independent verification in this repo; see PR5's own
documentation). `evidence_memory_for_receipt()` looks up
`EvidenceMemory` by the exact `source_reference` string
`create_memory_from_verified_outcome()` already writes — reusing the real
provenance link, never guessing which memory row belongs to which
opportunity.

## Impact velocity — missing stages are labelled, never zero

`impact_velocity()` reads real `ActionTimelineEvent` timestamps and
returns a real `datetime.timedelta` for a stage genuinely reached, or one
of three honest labels — `"Not reached"`, `"Not measured"`, `"Not
verified"` — for a stage that hasn't happened yet. A missing stage is
never silently rendered as `0`.

## Mission health / comparison

Real counts only: providers active/failed, signals pending, reviews
pending, outreach awaiting approval, projects blocked, outcomes awaiting
verification. Mission comparison lists every `GoodMission` with its real
signal/opportunity/action/project/verified-outcome counts — no computed
"mission score" of any kind (the brief's own instruction).

## Demo Story Mode

A 16-step guided walkthrough built entirely from the same real fields the
Truth Chain section already reads — no separate narration model, no
unsupported claims. Steps that haven't happened yet say so plainly
("No project created.", "Not independently verified.").

## Global Good Map

Reuses `good_map_api`'s exact region-level field set (never a precise
coordinate, never an individual identifier) via a new
`geographic_opportunity_list()` read — rendered as a plain list, not a
globe/Cesium/3D renderer, per this PR's explicit scope.

## Morning Brief / notification integration

Every Top-3-Actions card on the Morning Brief now links "Open in Mission
Control →" straight to the featured-opportunity view
(`?opportunity=<pk>`), without duplicating any of Mission Control's own
content. `services/notify.py`'s opportunity-scoped notifications
(zero-capital pathway ready, connection ready, outreach awaiting
approval, reply received, project candidate ready, outcome measured,
verified impact) now set `admin_url` to the same Mission Control deep
link instead of the generic Django admin change form.

## Observatory

A compact summary — deterministic stages, model calls, evidence
retrieved/reused, human review required/completed, warnings, blocked
recommendations, latency — read straight from the same `AnalysisSession`
PR4 already records (`morning_brief.observatory_summary_for_run()`,
extracted into a shared helper so Morning Brief and Mission Control read
from exactly one computation, never two). A link to the full Observatory
in Django admin sits alongside it — no new telemetry architecture.

## The flagship live demo (this session)

Ran against real live signals: **33 real signals** fetched from USGS
(earthquakes), GOV.UK (grants/policy), and UK Environment Agency (flood
warnings); **10 real qualifying opportunities** detected, all real
earthquakes; **2 real noise clusters** correctly rejected as irrelevant
policy pages, not silently turned into opportunities.

The highest-urgency real opportunity — *"M 7.5 - 20 km ESE of Yumare,
Venezuela"* — was reviewed live by a real logged-in staff user through
the real Impact Action Network UI (the same governed pipeline PR5 built):
`discovered → needs_review → approved_for_research`, then a real
zero-capital `data_request` `ActionPathway` was created ("request
confirmed casualty/damage assessment data from official channels before
considering any further action — zero capital required"). The review was
**not** progressed further: no `ResponsibleParty` was confirmed, no
outreach was drafted, and no project candidate was proposed, because no
real, verified contact channel exists for a specific disaster-relief
organisation on this signal alone — outreach or a project candidate at
that point would have meant fabricating a contact or a project, which
this PR's own brief explicitly forbids. **Approved zero-capital action**
is the legitimate, honest furthest stage this real opportunity reached
today — exactly the kind of stopping point the brief's Phase 22
anticipates ("If the furthest state is 'outreach draft awaiting approval'
stop there. That is valid.").

## Security

- `mission_control_view` is `@staff_member_required` — no anonymous
  access (tested).
- No new mutation endpoints — Mission Control is entirely read-only; every
  action it links to (gate transition, pathway creation, outreach
  approve/send, project candidate approve/create) is a PR5 endpoint
  already staff-gated, POST-only, and CSRF-protected.
- No private contact channel is ever rendered — only
  `ActionContact.get_status_display()`, never the raw
  `public_contact_channel` value.
- Cross-mission/cross-opportunity isolation is enforced at the query
  level everywhere (`discovery_run__in=mission.runs.all()`), never by
  convention — tested directly.
- Evidence Memory rows shown are always scoped to the featured
  opportunity's own `ImpactReceipt.verified_outcome` via the real
  `source_reference` — never a cross-project leak.

## Known limitations

- Signal/cluster-level funnel counts are pool-wide, not per-mission — an
  honest limitation of the current schema (see "State honesty" above),
  disclosed directly in the UI rather than hidden.
- `shortlisted` in the 114-agent transparency section is only computed
  when the featured opportunity's originating `WorldSignal` can be found
  by title match (`opportunity.detected_signals` stores titles, not IDs,
  per PR3's own design) — shows as `—` when it can't, never a fabricated
  number.
- Mission comparison only has one real mission to compare today (the
  flagship); the comparison table itself is fully general and will show
  more rows the moment a second `GoodMission` is enabled.
