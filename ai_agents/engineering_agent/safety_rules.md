# Engineering Agent — Safety Rules

- Must flag conditional/insufficient_evidence, not support, when technical_specification is empty.
- Must never clear a scenario touching a component with condition=poor and criticality=critical without a risk flag.
- This agent's output is never sufficient on its own to promote a scenario
  into `waste_to_value_capital_allocation_engine.CapitalAllocationDecision`
  — see `digital_twin.services.human_approval_gate`.
