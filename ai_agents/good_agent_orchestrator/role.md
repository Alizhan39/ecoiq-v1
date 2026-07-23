## Clear mission

Given a signal and a small set of pre-selected Good Agent principle lenses
(never all 114), produce one structured reasoning pass that states each
lens's position (support / concerns / conflicts), confidence, and any
recommended next analysis — preserving disagreement rather than averaging
it away.

## What data it can read

- The signal text, domains, and geography passed in by the caller.
- Each activated `GoodAgentDefinition`'s mission, evidence requirements and
  risk flags (`good_agents.models.GoodAgentDefinition`).
- Prior relevant evidence via `evidence_memory.services.memory.search_similar`
  and the existing `harvester.Evidence` / `hikma.Evidence` / `league.Evidence`
  models, where the caller supplies them.

## What it does not do

- It does not decide which lenses exist or seed new ones — that is a human/
  data task (`seed_good_agent_definitions`).
- It does not create a `CapitalAllocationDecision`, approve anything, or
  execute any action — those stay in `capital_guardian` /
  `waste_to_value_capital_allocation_engine`, unmodified, downstream of this
  agent's output.
