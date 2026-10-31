---
name: ecoiq-khalifah-loop
description: Locate where a feature belongs in EcoIQ's DETECT-DIAGNOSE-GENERATE-SIMULATE-OPTIMIZE-MATCH-FINANCE-EXECUTE-VERIFY-MEASURE-LEARN-REPEAT loop, and which Django app already owns that stage. Use when creating a new app or service that sounds like an existing stage, when asked what happens after a given stage, or when checking whether a stage is really implemented. Not for changes wholly inside one app.
---

# The Khalifah loop → what actually exists

**Read this first: the twelve stage names are product vocabulary, not code.**
As of this audit no module, constant, enum, or state machine in the
repository is named `DETECT`, `DIAGNOSE`, `SIMULATE`, `OPTIMIZE`, or `REPEAT`.
Searching for them returns nothing. Do not write code that pretends a
`KhalifahLoop` orchestrator exists, and do not tell a user a stage "runs"
when the table below says otherwise.

The nearest real end-to-end pipeline is the LangGraph graph in
[`langgraph_orchestration/`](../../../langgraph_orchestration/), whose actual
nodes are:

```
classify_intent → retrieve_evidence_memory → gather_geo_intelligence
→ run_agent_analysis → recalculate_score_if_needed
→ run_intelligence_analytics → verify_output → finalize
```

It creates no second agent runtime — every node calls an existing Django
service. Extend that graph rather than building a parallel orchestrator.

## Stage → owner, with honest maturity

`BUILT` = models + migrations + tests. `PARTIAL` = real logic, thin or no
persistence. `SCAFFOLD` = views/templates only — no models, no migrations.

| Stage | Owning app(s) | Maturity |
|---|---|---|
| DETECT | `harvester` (8 models, 1281 test lines), `ingestion`, `geo_intelligence` | BUILT (`ingestion` has no tests) |
| DIAGNOSE | `ethics` (33 sub-formulas + 3 masters, `ethics/registry.py`), `hikma`, `audit` | BUILT (`ethics` has **no tests**) |
| GENERATE | `ai_gateway`, `good_agents` (20 models), `ai_agent_council` | BUILT |
| SIMULATE | `transition`, `decision_studio` | PARTIAL (`transition` has no tests) |
| OPTIMIZE | `pandas_scoring_engine`, `intelligence_analytics_engine` | PARTIAL (no models by design) |
| MATCH | `supplier_funding_marketplace`; specs in `docs/NEED_RESOURCE_MATCHING.md`, `docs/CIRCULAR_ECONOMY_MATCHING.md`, `docs/FUNDING_MATCHER.md` | SCAFFOLD |
| FINANCE | `capital_guardian` (7 models, 4183 test lines), `waste_to_value_capital_allocation_engine`, `financing`, `institutional_finance_engine` | MIXED — first two BUILT, last two thin/SCAFFOLD |
| EXECUTE | `projects`, `amanah_autopilot` | SCAFFOLD (`projects` has 0 models and 0 tests) |
| VERIFY | `audit`, `impact_mrv_layer`, `mrv_agent_training_pack` | MIXED — `audit` BUILT, MRV layer SCAFFOLD |
| MEASURE | `impact_mrv_layer`, `product_analytics_kpi_engine` | SCAFFOLD |
| LEARN | `agent_training_evaluation_lab`, `evidence_memory` | BUILT |
| REPEAT | No scheduler owns loop re-entry. Celery exists (`backend_intelligence_engine`), but no periodic task closes the loop. | NOT IMPLEMENTED |

## Rules when you touch the loop

1. **Check the table before creating an app.** 79 apps are already installed;
   most "new stage" requests are a service inside an existing one.
2. **A stage never promotes evidence.** Moving forward through the loop does
   not upgrade `confidence_tier` — see `ecoiq-evidence-audit`.
3. **FINANCE and EXECUTE outputs require human review.** Money and
   commitments are never an LLM's terminal decision
   (`docs/AI-QUALITY-GATES.md` §7).
4. **VERIFY is not "the model said it verified."** `verify_output` in
   `langgraph_orchestration/nodes.py` is a structural check on the assembled
   state, not an attestation. Say so when reporting.
5. **Report SCAFFOLD as SCAFFOLD.** If a request depends on MATCH, EXECUTE,
   or MEASURE persisting anything, that persistence has to be built first —
   name it as work, don't route around it silently.

## Gaps worth logging (not fixed here)

- `ethics/` — the scoring core of DIAGNOSE — has an empty `tests.py`.
- `transition/` and `ingestion/` likewise.
- No REPEAT/re-entry scheduler exists.
