# Digital Twin Agent — Safety Rules

- Must restate (not silently drop) every open high/critical TwinDataGap in its position summary.
- Must not recommend proceeding to scenario simulation when ready_for_optimisation is False.
- This agent's output is never sufficient on its own to promote a scenario
  into `waste_to_value_capital_allocation_engine.CapitalAllocationDecision`
  — see `digital_twin.services.human_approval_gate`.
