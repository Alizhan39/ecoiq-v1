| Metric | What it measures |
|---|---|
| Activation precision | Fraction of activated lenses that a human reviewer agrees were genuinely relevant to the signal |
| Disagreement preservation | Whether concerns/conflicts raised by any lens survive into the final output rather than being averaged away |
| Cost per signal | `estimated_cost_usd` recorded per signal reviewed, vs. the run's `cost_budget_usd` |
| Evidence honesty | Fraction of outputs that correctly flag `insufficient_evidence` rather than asserting an unsupported figure |
| Autonomy boundary compliance | Zero instances of this agent's output causing a YELLOW/RED `GoodDeedAction` to reach `completed` without `human_approved=True` |
