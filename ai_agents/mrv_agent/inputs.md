# MRV Agent — Inputs

| Input | Description |
|---|---|
| `project` / `asset` | The project/asset the claim relates to |
| `claim_type` | energy saved, fuel saved, CO2 reduced, water saved, waste reduced, cost saved, comfort improved, health/pollution harm reduced |
| `baseline_evidence` | Baseline documents/readings |
| `after_evidence` | Post-implementation documents/readings |
| `methodology` | Stated calculation method (e.g. emissions factor used) |

## Required evidence per claim type

- **Energy saved**: baseline/after energy use, comparable period, unit, methodology, evidence source
- **Fuel saved**: baseline/after fuel use, fuel type, unit, delivery/billing evidence, weather/usage caveat
- **CO2 reduced**: energy/fuel reduction, emissions factor, methodology, calculation note, reviewer approval
- **Water saved**: baseline/after water use, meter/bill/log, unit, comparable period
- **Waste reduced**: baseline/after waste volume/weight, unit, source documents, method
- **Cost saved**: baseline/after cost, currency, tariff/cost assumptions, finance review
- **Comfort improved**: survey, temperature data, complaint reduction, before/after notes, qualitative caveat
- **Health/pollution harm reduced**: pollution proxy, fuel/smoke reduction, before/after photos if relevant, public health caveat, expert review

## What it does NOT accept as input

- A claim type with zero baseline or after evidence supplied at all (routed to `Not Started`)
