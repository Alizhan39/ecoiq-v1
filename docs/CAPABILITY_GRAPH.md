# The Capability Graph (PR7)

## What this replaces

Before this PR, `good_agents.ResponsibleParty` was a flat organisation/
contact directory: every opportunity that mentioned a real-world
organisation created its own freestanding row — bare `name` string,
guessed `party_type`, no shared identity. PR6's own live demo exposed the
consequence directly: ten real earthquake opportunities produced **ten
separate "USGS" rows**, each independently guessed from the triggering
signal's `publisher` field, none of them referencing the same real
organisation or carrying any durable, reusable knowledge about what USGS
can actually do.

This PR replaces that flat pattern with the minimum real graph needed to
route an action:

```
REAL-WORLD NEED -> REQUIRED CAPABILITY -> ORGANISATION WITH
EVIDENCE-BACKED CAPABILITY -> VERIFIED PUBLIC ROUTE -> HUMAN-GOVERNED ACTION
```

## What it is NOT

This repo already has an app called `knowledge_graph_relationship_map` —
audited before writing any code here. It has **no models at all**: it's a
static marketing/vision page (`views.py` renders a list of aspirational
"node types" and CTA buttons like "Open Knowledge Graph" that lead
nowhere real). It is explicitly what this PR is told not to build. The
Capability Graph is the opposite of that: every row is real, every
capability claim requires cited evidence, and the scope is bounded to
exactly what routes a real Good Agents action — not a general entity/
relationship graph for arbitrary future use cases.

## The model (`capability_graph/models.py`)

- **`Organisation`** — the ONE deduplicated node for a real-world org.
  `dedupe_key` (a normalised `name::jurisdiction`) is enforced unique at
  the database level; `services/organisations.py`'s
  `get_or_create_organisation()` is the only sanctioned way to create or
  resolve one. An optional `linked_company` FK connects to
  `companies.CompanyProfile` when the org happens to be a real tracked
  company — never a hard dependency, since most capability-holding
  organisations relevant to Good Agents (government departments,
  regulators, charities, funds) are not companies at all.

- **`OrganisationCapability`** — the evidence-backed edge. `capability` is
  one of the 27 values from the brief (FUND, GRANT, LEND, DONATE,
  REGULATE, AUTHORISE, PERMIT, PROCURE, INSTALL, TRANSPORT, COLLECT,
  RECYCLE, REUSE, SUPPLY, MANUFACTURE, PROVIDE_TECHNOLOGY,
  PROVIDE_EXPERTISE, RESEARCH, VERIFY, AUDIT, MEASURE, HOST, TRAIN,
  EMPLOY, REFER, COORDINATE, RESPOND_TO_EMERGENCY). Every row also carries
  `jurisdiction`, `topic_domain`, `evidence_source`/`evidence_url`,
  `verification_state`, `last_verified_at`, and `limitations` — because a
  real capability claim is never just "this org does X" (see the brief's
  own examples: a local authority's regulatory authority may not extend
  to every jurisdiction; a charity supporting a cause may not fund it
  directly; a manufacturer may not install its own product; a fund may
  not accept unsolicited applications). `services/capabilities.py`'s
  `record_capability()` **refuses to create a row with no evidence at
  all** (`NoEvidenceError`) — the structural enforcement of "never infer
  that an organisation can perform a capability merely from its name or
  sector."

- **`PublicRoute`** — HOW a human actually engages a capability, kept
  deliberately separate from whether the capability exists: a real,
  evidence-backed capability can have zero known routes yet (an honest,
  valid state, not an error). `route_value` must come from real evidence
  — never inferred, per the brief's "no guessed contact details" rule.

## Verification discipline

`verification_state` mirrors the ESTIMATED/TARGET/MEASURED/VERIFIED
discipline used everywhere else in this project:

| State | Meaning |
|---|---|
| `unverified` | Not yet checked against any real source |
| `self_reported` | The organisation itself claims this, unconfirmed |
| `documented` | A real public source states this |
| `independently_verified` | A human confirmed this directly |

A capability can never reach `independently_verified` except through
`services/capabilities.py`'s `verify_capability(edge, actor=...)`, which
raises if `actor` is `None` — the same human-gate discipline as PR5's
`action_gate.transition()`/`responsible_party.confirm()`.

## "Need -> required capability" is code, not a table

The brief's second node (REQUIRED CAPABILITY) is a deterministic mapping
over `good_agents.Need.need_type` / `GoodOpportunity.theme` values
(`services/needs.py`) — plain Python dicts, exactly like PR3's own
keyword-overlap scoring discipline, not a new persisted "requirement"
table. Anything not explicitly mapped falls back to a conservative
default (`coordinate`, `refer` — "route this to someone who can figure
out what's needed") rather than crashing or fabricating a specific
capability for an unrecognised need type.

## The reusable query (`services/matcher.py`)

`find_organisations_for_capability(capability, *, jurisdiction=None,
topic_domain=None, min_verification='unverified')` is the ONE function
any consumer should call — a pure, deterministic read over
`OrganisationCapability`, with substring jurisdiction/topic matching
(real-world jurisdiction strings are inconsistent — "England" vs "UK" —
and a human still reviews every result before any action is taken) and a
verification floor so a caller can refuse to act on anything weaker than
it's willing to trust.

## The fifth node ("HUMAN-GOVERNED ACTION") is already built

This PR does not duplicate PR5's governed action pipeline
(`ActionGate`/`ActionPathway`/`OutreachDraft`/`ConnectionCandidate`). The
Capability Graph feeds candidates INTO that existing pipeline — see
`good_agents.services.responsible_party.suggest_from_capability_graph()`
below — it never creates a second decision/approval mechanism.

## First real consumer: good_agents

- **`ResponsibleParty.organisation`** (nullable FK, additive) —
  `suggest_from_signal()` now resolves through
  `get_or_create_organisation()` instead of storing a bare name per
  opportunity. `suggest_from_capability_graph(opportunity, capability,
  jurisdiction=None, topic_domain=None)` is new: it suggests
  `ResponsibleParty` candidates from real, evidence-backed
  `OrganisationCapability` rows rather than a guess from the triggering
  signal's publisher field — every candidate stays `possible_organisation`
  until a human confirms it, and the suggestion's `notes` cite the real
  capability's evidence and limitations so a reviewer can see exactly why
  it was suggested.

- **`FundingMatch.organisation`** (nullable FK, additive) —
  `funding_matcher.enrich_with_capability_graph(funding_match)` resolves
  a real organisation ONLY when exactly one evidence-backed match exists
  for the mapped capability (FUND/GRANT/LEND/DONATE); leaves it `None`
  when zero or several candidates exist, never guessing among them. Since
  no real funder database is connected in this repo (unchanged from
  PR3's own finding), this is null for almost every FundingMatch today —
  an honest reflection of the graph's current real coverage, not a bug.

## Seeded real data

`seed_capability_graph_from_real_providers` seeds exactly two
conservative, real, well-documented capability edges — using the EXACT
endpoint URLs PR4's already-verified `provider_adapters.py` calls (`USGS_URL`,
`EA_FLOODS_URL`), not new/unverified citations:

- **USGS (US Geological Survey)** — `measure` + `research`, "seismic
  activity", jurisdiction "Global". Limitation stated explicitly:
  publishes measurement data; does not coordinate emergency response or
  fund anything.
- **UK Environment Agency** — `regulate` + `respond_to_emergency`, "flood
  risk", jurisdiction "England" *only*. Limitation stated explicitly:
  England-only statutory authority (Scotland/Wales/NI each have separate
  bodies); does not itself fund household flood defences.

Both start at `verification_state='documented'`, never
`'independently_verified'`, since no human has confirmed them yet in this
session (browser-verified live: a staff user can promote UK Environment
Agency's `regulate` capability to `'independently_verified'` through the
real UI, and it correctly requires a real login + CSRF-protected POST).

## Staff UI

`/capability-graph/` — organisation list (filterable by capability) and
detail (capabilities, evidence, limitations, routes, verify action).
Minimal by design: not a general graph explorer, just enough for a human
to review and verify what the graph already knows.

## Deferred to a future PR

Capital Guardian and company intelligence are explicitly named as future
consumers in the brief but are NOT wired in this PR — `find_organisations_for_capability()`
is generic infrastructure either can call without any change to this app,
and forcing that integration now would have gone well beyond "the
minimum evidence-backed capability graph required to route real EcoIQ
actions." The same incremental-adoption pattern PR2→PR6 already followed
(build the real thing, wire one grounded consumer, defer broader
adoption to the PR that actually needs it).
