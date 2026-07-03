# Finance Modelling Agent

## Mission

Prepare draft financial logic — CAPEX/OPEX assumptions, payback estimates,
risk notes and funding gaps — for a matched playbook's actions, always
labelled "estimated" unless independently verified, and never claiming a
guaranteed saving.

## Position in the EcoIQ agent pipeline

```
Industrial Playbook Matching Agent → Finance Modelling Agent → MRV Agent →
Governance Agent → Report Generator Agent
```

## What it produces

A finance memo draft (see `outputs.md`) consumed by:

- **Institutional Finance Engine** — the draft CAPEX/OPEX model
- **Supplier & Funding Marketplace** — the funding gap and route needed
- **Governance Agent** — for financial review sign-off
- **Report Generator Agent** — investor memo and board pack finance content

## Files in this pack

| File | Purpose |
|---|---|
| `system_prompt.md` | Production system prompt |
| `role.md` | Mission, boundaries, what it must never invent |
| `inputs.md` | What data it can read |
| `outputs.md` | Required JSON output schema |
| `tools.md` | Tools and EcoIQ modules it calls |
| `safety_rules.md` | No Harm Gate, human approval triggers |
| `test_cases.json` | 5 realistic test cases + 3 failure cases |
| `evals.md` | Evaluation metrics and pass/fail criteria |
| `demo_scenarios.md` | Investor and enterprise/government demo scripts |
