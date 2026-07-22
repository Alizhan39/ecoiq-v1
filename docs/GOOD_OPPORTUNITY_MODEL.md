# Good Opportunity Model

`good_agents.models.GoodOpportunity` is the canonical record of a candidate
"good that can be done" — problem/unmet-need/waste, evidence, and everything
needed to reason about it, evaluate it, and (if warranted) act on it.

## Impact fields never collapse into a fake universal score

`potential_benefit` is a `JSONField` keyed by dimension, each value carrying
its own unit and stage:

```python
opportunity.potential_benefit = {
    "people_helped": {"value": 200, "unit": "households", "stage": "target"},
    "coal_use_avoided": {"value": None, "unit": "tonnes/year", "stage": "estimated"},
}
```

Stage is always one of `estimated` / `target` / `measured` / `verified` —
never mixed, never averaged into one score. Incompatible dimensions (people
helped vs. money saved vs. emissions avoided) are never summed or weighted
into a single number; each stays in its own key with its own unit.

`ImpactReceipt.expected_result` and `ImpactReceipt.measured_result` follow
the same discipline: `measured_result` stays `{}` until a real
`VerifiedCapitalOutcome` exists (see `docs/GOOD_WHILE_YOU_SLEEP.md` and
`good_agents/services/pipeline.py`'s module docstring for why the demo
command never populates it with invented numbers).

## Evidence honesty

`insufficient_evidence` (boolean) is a first-class, honest conclusion —
Phase 22's "system must support INSUFFICIENT EVIDENCE as a valid
conclusion" requirement. When set, `good_agents.services.red_team.build_review`
will not clear the opportunity for qualification
(`RedTeamReview.cleared=False`), regardless of how positive the principle
lenses were. This was verified in the Almaty demo run itself: the
opportunity legitimately stays at `status='potential'` (not `'qualified'`)
because no real baseline measurement exists yet — the system does not
pretend otherwise.

## Zero-capital fields

`zero_capital_possible` / `zero_capital_action_plan` are first-class (Phase
6) — see `docs/RESOURCE_MATCHING_NETWORK.md`.

## Status ledger (Phase 14 — Good Created Ledger)

```
potential -> qualified -> approved -> in_progress -> measured -> verified
                                 \-> rejected
```

`good_agents.services.pipeline.qualify_opportunity` is the only place that
advances `potential -> qualified`, and only when `RedTeamReview.cleared`.
Nothing in this codebase calls potential/estimated impact "impact created"
— see `docs/GOOD_CREATED_LEDGER.md` for the full distinction.

## Privacy by design (Phase 19 — Global Good Map readiness)

`GoodOpportunity` carries only region-level geography
(`countries.CountryProfile` FK + free-text `region`) — never a precise
address, coordinate, or individual identifier. `affected_population` is a
free-text description ("~200 coal-heated households"), never a list of
named individuals. The model's filterable fields (`geography`, `region`,
`sector`, `theme`, `urgency`, `confidence`, `zero_capital_possible`,
`capital_required_usd`, `status`) are exactly what a future `/good/map`
would need — the map UI itself is not built in this slice (secondary per
Phase 19).
