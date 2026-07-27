# Stewardship Agent — Safety Rules

- Every position must state that all seeded KPIs currently ship 'requires_scholarly_review' and are not yet approved for authoritative use.
- human_approval_required=True whenever the guardrail verdict is 'block' or 'requires_specialist_review'.
- This agent's output is never sufficient on its own to promote a scenario
  into `waste_to_value_capital_allocation_engine.CapitalAllocationDecision`
  — see `digital_twin.services.human_approval_gate`.
