# Evidence Agent — Safety Rules

- missing_data includes every claim whose confidence has no matching evidence_reference.
- This agent's output is never sufficient on its own to promote a scenario
  into `waste_to_value_capital_allocation_engine.CapitalAllocationDecision`
  — see `digital_twin.services.human_approval_gate`.
