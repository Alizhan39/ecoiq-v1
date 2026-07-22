## EcoIQ modules this agent reads from / writes to

- Reads: `good_agents.models.GoodAgentDefinition` (the activated lenses),
  `evidence_memory.services.memory.search_similar` (prior relevant evidence).
- Writes: `good_agents.models.AgentActivationRecord` (one row per activated
  lens, via `good_agents.services.orchestrator.record_activations` — the
  agent itself does not write to the database; the calling service does).
- Routed via `agent_runtime_model_router.services.model_router.select_model_route`,
  `agent_runtime_model_router.services.model_adapters.get_adapter`,
  `agent_runtime_model_router.services.cost_policy.check_cost_policy`,
  `agent_runtime_model_router.services.safety_assertions.run_safety_assertions` —
  the same runtime stack every other operational agent in this repo uses;
  no second router, no second cost policy.

## External tool concepts (not yet wired to a live runtime)

- A live web/document search tool for signal sourcing (the Observatory's
  ingestion layer) — not implemented in this vertical slice; signals are
  supplied by the caller today. See `docs/GOOD_WHILE_YOU_SLEEP.md`.
