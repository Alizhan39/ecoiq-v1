# Industrial Playbook Matching Agent

## Mission

Match an asset to the modernisation playbook(s) that actually fit its sector,
condition, risks and constraints — surfacing quick wins and deep upgrades with
their MRV metrics and supplier needs, not a generic one-size-fits-all plan.

## Position in the EcoIQ agent pipeline

```
Asset Passport Agent → Industrial Playbook Matching Agent →
Finance Modelling Agent → MRV Agent → Governance Agent → Report Generator Agent
```

## What it produces

A best-fit playbook recommendation (see `outputs.md`) consumed by:

- **Finance Modelling Agent** — the actions/upgrades to cost out
- **Impact MRV Layer** — the MRV metrics the playbook implies tracking
- **Supplier & Funding Marketplace** — the supplier needs the playbook implies

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
