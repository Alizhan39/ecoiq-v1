# Report Generator Agent

## Mission

Generate investor memos, board packs, public summaries and country briefs
from Asset Passport, finance model, MRV status, evidence, governance review
and graph trace data — with every claim traceable back to evidence.

## Position in the EcoIQ agent pipeline

```
Governance Agent → Report Generator Agent
```

Report Generator Agent is the last agent in the core pipeline — it only
produces a report once governance approval exists for the claims it contains.

## What it produces

A report draft (see `outputs.md`) consumed by:

- **Executive Briefing & Board Pack Generator** — the platform module this agent's output feeds
- **Public Trust & Impact Portal** — for approved public summaries only
- **Data Room & Evidence Vault** — the evidence pack behind the report

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
