# Capital Allocation Agent — Inputs

| Input | Description |
|---|---|
| `case_title` / `capital_at_risk` / `inventory_value` | The loss case's own materiality figures, from Waste & Leakage Agent's detection |
| `intervention_window` | How much time is available before the loss becomes irreversible (e.g. "36 hours") |
| `intervention_options` | The real, already-persisted `InterventionOption` rows for this case: `title`, `intervention_type`, `capex_estimate`, `estimated_loss_avoided`, `estimated_value_recovered`, `estimated_annual_savings`, `estimated_payback_months`, `risk_level`, `technical_readiness`, `finance_readiness`, `mrv_readiness` |
| `finance_modelling_position` | Finance Modelling Agent's own CAPEX/OPEX/payback conclusions for context |
| `governance_position` | Governance Agent's food-safety and wording concerns, if any |

## What it does NOT accept as input

- A "verified return" figure supplied without MRV Agent's own verification —
  if supplied, it is treated as `estimated`, never taken at face value
- A funding-secured claim without independent confirmation evidence — treated
  as "funding route identified" until confirmed
- A supplier-quote-derived cost presented as "approved" — treated as a quote,
  never an approved cost
