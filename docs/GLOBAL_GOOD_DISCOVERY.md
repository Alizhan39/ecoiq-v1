# Global Good Discovery

## What changed vs. PR2

PR2 proved ONE complete path: a human-authored signal → 6 principle lenses
→ evidence → GoodOpportunity → OperationalLoss → Better Way → Capital
Guardian → Human Approval → MRV → ImpactReceipt → Evidence Memory. That
path is **unchanged** — `good_agents/services/pipeline.py`,
`good_agents/services/discovery_run.py` (PR2's `run_discovery`), and
`run_almaty_good_agent_demo` still work exactly as before (93 tests
including all 36 original PR2 tests still pass).

PR3 adds a NEW front door — `good_agents.services.discovery_engine.run_global_discovery`
— that gets a `GoodOpportunity` created from raw signals nobody submitted
by hand:

```
raw signal dicts
  -> WorldSignal (normalise, dedup_key, fact/claim/inference)      [services/signals.py]
  -> deduplicate + cluster into SignalCluster                       [services/clustering.py]
  -> triage: problem / resource / noise                             [discovery_engine._triage_cluster]
  -> classify_relevant_agents + run_deep_reasoning (PR2, unchanged)  [services/orchestrator.py]
  -> evaluate_cluster: qualify / reject / monitor / insufficient_evidence  [services/evidence_gate.py]
  -> GoodOpportunity + Need                                         [discovery_engine, services/need_resource.py]
  -> NeedResourceMatcher / CircularEconomyMatcher                   [services/matcher.py, services/circular_economy.py]
  -> ZeroCapitalStrategy + FundingMatcher                           [services/zero_capital_strategy.py, services/funding_matcher.py]
  -> PrioritisationEngine labels                                    [services/prioritisation.py]
  -> MorningImpactBrief + Top 3 Actions                             [services/morning_brief.py]
```

Better Way / Capital Guardian / MRV / ImpactReceipt remain a **separate,
opt-in step** a caller runs afterwards on a qualified opportunity that has
a real capital angle — exactly PR2's pattern. The discovery engine does
not force every discovered opportunity through OperationalLoss; a
zero-capital NGO/waste-heat match never touches it at all.

## SignalProvider architecture (Phase 1)

`good_agents.models.SignalProvider` is a registry row describing WHERE a
signal could come from — it has no live fetch implementation.
`fetch_method` is a human-readable description, not code. **No network
request is made by this app.** Real ingestion (an HTTP client hitting an
actual government/NGO/news API) is explicitly out of scope for this PR —
see "What remains incomplete" in `docs/GOOD_AGENTS_PROGRESS.md`.

## Triage rule (noise rejection)

A `SignalCluster` is triaged as:
- **problem** — contains a `need`/`harm`/`waste`/`risk`/`emergency`/`opportunity`
  signal → proceeds to evidence gate → candidate `GoodOpportunity`.
- **resource** — contains a `resource`/`funding` signal → registers an
  `AvailableResource`, no opportunity created.
- **noise** — only `policy_change`/`technology_change`/`price_change`
  signals below a severity escalation threshold → discarded.

The first overnight demo (`run_overnight_good_discovery_demo`) proves this:
4 signals in, 1 opportunity out, 1 resource registered from a second
signal, 1 resource registered from a third, and the 4th (irrelevant market
news) correctly produces nothing.

## Evidence Gate (Phase 5)

`good_agents.services.evidence_gate.evaluate_cluster` is a quality check,
not a reasoning step — deterministic thresholds on confidence, source
diversity, freshness, contradictions, and missing geography/sector. It can
and does conclude `insufficient_evidence` and stop — this is tracked on
`GoodDiscoveryRun.insufficient_evidence_count`, never silently dropped.

## Cost controls at scale (Phase 14, 22-23)

Scaling `GoodAgentDefinition` from 6 to all 114 principles
(`seed_all_good_agent_definitions`) does NOT increase LLM cost per signal:
`classify_relevant_agents` still caps activation at `max_activated` (6 by
default) regardless of how many rows exist to score against — proven in
`good_agents.tests.DiscoveryEngineTests.test_never_activates_more_than_max_activated_even_with_all_114_seeded`.
Layer 4 remains one combined reasoning call per signal, never one per lens.

## Staged, resumable runs (Phase 13)

`GoodDiscoveryRun.stage_checkpoints` records completion of each of the 12
stages (`fetch_signals` → ... → `generate_brief`). A second call with the
same `idempotency_key` on an already-`completed` run returns immediately;
a crashed/failed run's already-checkpointed stages are re-derived from
already-persisted rows (new `WorldSignal`/`SignalCluster` rows) rather than
redone from scratch — see `discovery_engine.run_global_discovery`'s
`if not run.stage_done(...)` branches.
