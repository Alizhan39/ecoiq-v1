# Resource Matching Network

## Status: architecture only (Phase 5) — not a full implementation

Phase 5 asks for a NEED ↔ AVAILABLE RESOURCE matching network (grants,
government programmes, unused assets, waste heat, impact investors, waqf,
Islamic finance, etc.) supporting circular-economy reasoning ("waste from A
may be a resource for B").

This vertical slice implements the **zero-capital half** of this concept as
first-class fields on `GoodOpportunity` (Phase 6):

```python
zero_capital_possible = models.BooleanField(default=False)
zero_capital_action_plan = models.TextField(blank=True)
```

And the matching *action types* exist in the Good Deeds Engine
(`find_resource`, `find_funding`, `find_partner`, `match`, `connect` — see
`docs/GOOD_DEEDS_ENGINE.md`), all GREEN/YELLOW, none auto-executing.

## What is genuinely NOT built

- No `Resource` model (grant/programme/asset/supplier/investor/waqf/etc.) —
  Phase 14's global opportunity finder audit found no cross-cutting
  "resource" concept anywhere in the existing repo either (only
  finance-scoped ones: `geo_intelligence.InvestmentGeoOpportunity`,
  `transition.FinancingOpportunity`, `financial_intelligence_cloud.AdvisoryOpportunity`).
  Building a real `Resource` catalogue and matching engine is future work,
  not attempted here — inventing one now, with no real data to populate it,
  would be exactly the kind of premature scaffolding this task's own
  instructions warn against ("Do not build all 114 agents deeply... Do not
  invent Quranic mappings... smallest safe vertical slice").
- No `CircularEconomyMatcher`, `FundingMatcher`, `ResourceMatcher`,
  `GrantFinder`, or `IdleAssetAgent` implementation — these are listed as
  architecture stubs in `docs/GOOD_AGENT_SAFETY.md` §Specialist Agents
  (Phase 18), status `NOT_IMPLEMENTED`, with a one-line description each so
  a future PR has a named slot to fill rather than starting from nothing.

## Why the demo doesn't name a specific real grant/investor

The Almaty demo's `zero_capital_action_plan` deliberately describes the
*kind* of resource to look for ("existing municipal/government
energy-efficiency or heating-transition programmes and impact investors
already active in the region") rather than naming a specific real
programme — no such programme has actually been identified or verified for
this pilot yet. Naming one without evidence would violate this whole
system's evidence-honesty discipline.
