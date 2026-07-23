# Circular Economy Matching

`good_agents.services.circular_economy.match_circular_economy` answers one
question: *is someone's waste, surplus, or idle capacity someone else's
resource?*

## What it actually does

It is a thin wrapper over `services/matcher.match_need` (see
`docs/NEED_RESOURCE_MATCHING.md`), restricted to candidate resources of
type `waste_heat`, `food_surplus`, `material_surplus`, `energy_surplus`,
`equipment`, or `building`. Every match it returns already passed the same
real type-compatibility, geography, expiry, and evidence scoring as any
other match — this module does not invent a second scoring system.

What it adds on top:

- `ResourceMatch.is_circular_economy_match = True`
- An enrichment note covering **technical feasibility** (only
  `'evidence-supported'` if the resource itself has real `evidence_refs`,
  otherwise explicitly `'unverified'` — never inferred from the pairing
  concept alone), **logistics** (same-region vs. cross-region, no real
  distance/routing calculation exists), **regulatory constraints**
  (explicitly flagged as unassessed, for human review), and an
  **environmental benefit framing** per resource type (a one-line prompt
  for what a human should go verify, e.g. "requires a real energy-balance
  study to quantify" for waste heat — never a fabricated tonnes-CO2 number).

## Status: DONE (as a real, tested specialisation) / MISSING (real feasibility data)

- **DONE**: type restriction, enrichment fields, flagging, tests
  (`good_agents.tests.CircularEconomyMatcherTests`).
- **MISSING**: no real geospatial distance calculation, no real regulatory
  database, no real environmental quantification — every one of these
  dimensions is honestly labelled as unassessed/unverified rather than
  guessed. Building real versions of these would each be a substantial
  future PR (a routing/logistics API integration, a regulatory rules
  engine, an environmental-impact calculator) — not attempted here.
