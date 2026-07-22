# Good Created Ledger

## The distinction that must never be collapsed

**Potential Good** (an opportunity has been identified, evidence-checked,
and passed red-team review) is not the same thing as **Verified Good
Created** (a real-world outcome has actually been measured). This system
never calls the former the latter.

`GoodOpportunity.status` is the ledger:

```
potential -> qualified -> approved -> in_progress -> measured -> verified
                                 \-> rejected
```

- `potential` — freshly detected, not yet reviewed.
- `qualified` — passed `RedTeamReview` (no unresolved concerns, evidence
  not flagged insufficient).
- `approved` — a human approved the linked `CapitalAllocationDecision`
  (existing `capital_guardian`/`waste_to_value_capital_allocation_engine`
  mechanism, unmodified).
- `in_progress` / `measured` / `verified` — reserved for when real
  after-data exists (see `good_agents.services.pipeline.record_verified_outcome_and_sync`,
  fully wired and tested, but deliberately **not called** by the Almaty
  demo command, because no real after-data exists for that pilot yet).

## Where this shows up structurally, not just as a label

- `ImpactReceipt.expected_result` vs `ImpactReceipt.measured_result` — the
  latter stays `{}` until `record_verified_outcome_and_sync` is actually
  called with real figures.
- `waste_to_value_capital_allocation_engine.VerifiedCapitalOutcome.verified_status`
  defaults to `'estimated'` and is never flipped to `'verified'` by any code
  path in this app — that stays gated by the existing engine's own rules
  (`capital_guardian.services.execution_monitoring.record_monitoring_outcome`
  raises `VerificationNotAllowedHereError` if you try to pass
  `mrv_status='verified'` directly).
- The Almaty demo command's own final line prints: *"All financial figures
  in this demo are illustrative pilot-design assumptions, not measured
  data."* — this is not just a comment, it reflects that `measured_result`
  on the created `ImpactReceipt` is genuinely empty.
