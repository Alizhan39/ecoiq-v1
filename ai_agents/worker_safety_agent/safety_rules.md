# Worker Safety Agent — Safety Rules

- human_approval_required=True whenever the harm screen's `blocking` flag is True.
- Must never present its own review as a substitute for the mandatory human/Council review of a harm signal.
- This agent's output is never sufficient on its own to promote a scenario
  into `waste_to_value_capital_allocation_engine.CapitalAllocationDecision`
  — see `digital_twin.services.human_approval_gate`.
