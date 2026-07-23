# Need ↔ Resource Matching

## Models

- `good_agents.models.Need` — demand side. `need_type` from the same 16-item
  taxonomy as `GOOD_TAXONOMY_CHOICES` (minus a few UI-only themes).
  `affected_group` is a short free-text description, never a list of named
  individuals (privacy-by-design, same discipline as
  `GoodOpportunity.affected_population`).
- `good_agents.models.AvailableResource` — supply side, 24 resource types
  from the spec's list (capital, grant, waqf, waste_heat, expertise, ...).
  `availability='available'` can never be set without at least one
  `evidence_refs` entry — enforced in `services/need_resource.create_resource`,
  not just documented (tested).
- `good_agents.models.ResourceStatusChange` — append-only history; a
  resource's status/availability is only ever changed via
  `services/need_resource.update_resource_status`, which always logs the
  change (Phase 28 temporal memory).
- `good_agents.models.ResourceMatch` — the output.

## NeedResourceMatcher (`services/matcher.py`)

Deterministic multi-factor scoring, not semantic similarity:

1. **Type compatibility** — a fixed `NEED_TYPE_TO_RESOURCE_TYPES` map. A
   resource type not listed for a need type scores **0 and is never
   persisted**, regardless of textual similarity between titles.
2. **Geography** — exact/substring match on region scores highest; a
   mismatch still scores (cross-border candidate) but lower.
3. **Timing/expiry** — `AvailableResource.is_expired()` is a **hard
   exclusion**: an expired resource can never be matched again (Phase 28 —
   "grant was open → now closed" must never still be recommended). This
   was caught and fixed during PR3 development itself (an earlier draft
   only soft-penalised expired resources; the fix hard-rejects them in
   `score_match`).
4. **Capacity specified** and **evidence-backed confidence** each
   contribute a smaller amount.

`missing_evidence` and `next_action` are always populated on the
`ResourceMatch` — a human reviewing a match sees exactly what's still
unverified, never an unexplained "AI recommends this."

## CircularEconomyMatcher (`services/circular_economy.py`)

A thin specialisation, not a second scoring system: reuses
`matcher.match_need` restricted to 6 resource types (`waste_heat`,
`food_surplus`, `material_surplus`, `energy_surplus`, `equipment`,
`building`), then enriches the resulting `ResourceMatch.match_reason` with
feasibility/logistics/regulatory/environmental framing —
`feasibility_signal` stays `'unverified'` unless the resource itself
carries real `evidence_refs`. Never claims feasibility from conceptual
similarity alone.

## Status: DONE / PARTIAL

- **DONE**: type-compatibility matrix, geography scoring, expiry exclusion,
  evidence-backed confidence, circular-economy enrichment, all tested.
- **PARTIAL**: matching is deterministic keyword/type logic, not a learned
  or semantic model — acceptable for this PR's scope (a quality-first, not
  volume-first, matcher) but a future PR could add a real embedding-based
  candidate pre-filter before this scoring runs.
- **MISSING**: no real `AvailableResource` data source exists yet (see
  `docs/GLOBAL_GOOD_DISCOVERY.md`'s SignalProvider section) — every
  resource in this repo today is either test data or the overnight demo's
  labelled fixtures.
