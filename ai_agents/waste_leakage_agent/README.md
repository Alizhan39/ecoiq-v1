# Waste & Leakage Agent

## Mission

Answer one question, precisely and honestly: what value is being lost, where,
how much, how certain are we, what evidence supports it, what is missing, and
what should happen next?

Detect operational loss (spoilage, cold-chain failure, energy/water/material
loss, idle assets and the other categories the platform recognises), quantify
the financial exposure, and — critically — keep `actual`, `estimated` and
`forecast` figures visibly separate at every step.

A full, richer version of this domain lives as a live EcoIQ platform module
at `/waste-to-value-capital-allocation/` (see
`waste_to_value_capital_allocation_engine/` in the repo root for the Django
app backing that page, including the real `calculate_capital_at_risk()`
formula this agent calls rather than re-deriving). This
`ai_agents/waste_leakage_agent/` folder is the implementation-ready,
file-based counterpart — consistent with that page and reusing its services.

## Position in the EcoIQ agent pipeline

```
Waste & Leakage Agent → Document Reader Agent → Finance Modelling Agent → MRV Agent → Governance Agent
```

The Waste & Leakage Agent runs first, solo — before any other agent begins
gathering supporting evidence — because its job is to decide *whether there
is something worth the Council's attention at all*, and how urgently.

## What it produces

A loss detection and quantification record (see `outputs.md`) consumed by:

- **Waste-to-Value Capital Allocation Engine** — the `OperationalLoss` record this agent's output corresponds to
- **Finance Modelling Agent** — starting point for CAPEX/OPEX/payback modelling
- **MRV Agent** — the baseline this agent's `classification` must eventually be verified against
- **Amanah Autopilot Supervisor** — overnight high-risk-inventory alerts
- **Knowledge Graph & Relationship Map** — `ORGANISATION_HAS_OPERATIONAL_LOSS`, `LOSS_BACKED_BY_EVIDENCE` nodes

## Files in this pack

| File | Purpose |
|---|---|
| `system_prompt.md` | Production system prompt |
| `role.md` | Mission, boundaries, what it must never invent |
| `inputs.md` | What data it can read |
| `outputs.md` | Required JSON output schema |
| `tools.md` | Tools and EcoIQ modules it calls |
| `safety_rules.md` | No Harm Gate, human approval triggers |
| `test_cases.json` | Realistic test cases + failure cases |
| `evals.md` | Evaluation metrics and pass/fail criteria |
| `demo_scenarios.md` | Investor and enterprise demo scripts, including the Meat Cold-Chain golden case |
