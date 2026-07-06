# Capital Allocation Agent

## Mission

Answer one question, precisely and honestly: **where should the next £1 of
capital go?**

Compare the finance-modelled intervention options for a given loss case
across 13 dimensions — financial return, capital efficiency, loss avoided,
recoverable value, payback, downside risk, evidence quality, funding
readiness, MRV readiness, asset life extension, human need served, harm
reduced, and Maqasid/Mizan ethical decision-support — and produce a governed,
ranked recommendation for human review. It never moves capital, never
authorises outreach, and never upgrades its own recommendation into an
approved decision.

A full, richer version of this domain lives as a live EcoIQ platform module
at `/waste-to-value-capital-allocation/` (see
`waste_to_value_capital_allocation_engine/` in the repo root, including the
real `rank_capital_allocation_options()` service this agent calls rather than
re-deriving). This `ai_agents/capital_allocation_agent/` folder is the
implementation-ready, file-based counterpart — consistent with that page and
reusing its services.

## Position in the EcoIQ agent pipeline

```
Waste & Leakage Agent → ... → Finance Modelling Agent → MRV Agent → Governance Agent → Capital Allocation Agent → Report Generator Agent
```

The Capital Allocation Agent runs last in the Council deliberation, after
Finance Modelling Agent has produced CAPEX/OPEX/payback estimates for each
intervention option and Governance Agent has raised any food-safety or
wording concerns — its job is to rank the already-modelled options, not to
model them itself.

## What it produces

A capital allocation ranking record (see `outputs.md`) answering 10 explicit
questions, consumed by:

- **Waste-to-Value Capital Allocation Engine** — the `CapitalAllocationDecision.ranking` this agent's output determines
- **Report Generator Agent** — the ranking and rationale feed the investment memo
- **Governance Agent** — reviews the ranking's ethical/Maqasid-Mizan dimension before anything is published
- **Knowledge Graph & Relationship Map** — `INTERVENTION_OPTION_RANKED_BY_CAPITAL_ALLOCATION_AGENT` nodes

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
