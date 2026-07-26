# Energy and Resources Agent — Safety Rules

- Must flag missing_data when a scenario claims an energy/water impact but the twin has no corresponding baseline ResourceFlow to compare against.
- This agent's output is never sufficient on its own to promote a scenario
  into `waste_to_value_capital_allocation_engine.CapitalAllocationDecision`
  — see `digital_twin.services.human_approval_gate`.
