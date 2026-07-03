# Finance Modelling Agent — Inputs

| Input | Description |
|---|---|
| `capex_estimate` | Upfront cost estimate (from supplier quote or benchmark) |
| `opex` | Ongoing operating cost |
| `energy_bills` | Baseline energy/fuel/water bills |
| `savings_assumptions` | Stated assumptions behind any savings estimate |
| `supplier_quote` | Extracted supplier quote fields |
| `payback_target` | Investor/operator's stated payback requirement |

## Sector-specific finance notes

- **Heating/boilers, utilities**: tariff structure, seasonal demand variation
- **Manufacturing**: production output correlation with energy use
- **Oil and gas**: flaring cost/opportunity cost of captured gas
- **Mining, uranium, metals**: diesel price volatility, haul distance economics
- **Agriculture, food processing**: seasonal water/energy cost patterns
- **Energy**: grid tariff structure, feed-in/offtake assumptions

## What it does NOT accept as input

- A request to model finance with zero CAPEX/OPEX inputs and no stated
  assumptions (nothing to model — flagged as blocked)
