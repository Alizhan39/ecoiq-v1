# Waste & Leakage Agent — Inputs

| Input | Description |
|---|---|
| `organisation` / `asset` | The organisation/asset the loss relates to |
| `loss_type` | meat spoilage, food spoilage, cold-chain failure, excess inventory, overproduction, energy loss, heat loss, water leakage, material waste, idle machinery, idle buildings, unused warehouse capacity, and the other Waste-to-Value Capital Allocation Engine loss categories |
| `inventory_value` | Current value of the at-risk inventory or asset |
| `historical_loss_rate` | Historical spoilage/loss rate for this category, as a fraction (e.g. 0.15 for 15%) |
| `sensor_or_visual_indicator` | e.g. a refrigeration temperature excursion reading — a signal, not a confirmed failure |
| `intervention_window` | How much time is available before the loss becomes irreversible (e.g. "36 hours") |
| `utility_bill` | Electricity/water/fuel bill supporting an energy/water-loss claim |
| `maintenance_record` | Maintenance history for the relevant equipment |
| `supplier_quote` | A supplier's quote for a proposed intervention — a price offer, not independent verification |

## What it does NOT accept as input

- A "verified loss" figure supplied without underlying baseline and
  after-data evidence — if supplied, it is re-labelled `estimated` or
  `forecast` pending MRV Agent's own verification, never taken at face value
- A supplier's own claim of system failure or savings, treated as fact
  without independent confirmation
