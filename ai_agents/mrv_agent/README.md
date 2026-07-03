# MRV Agent

## Mission

Check whether an impact claim (energy saved, fuel saved, CO2 reduced, water
saved, waste reduced, cost saved, comfort improved, health/pollution harm
reduced) is supported by baseline evidence, after-data, methodology and human
review — and keep estimated impact clearly separate from MRV Verified impact.

A full, richer version of this training pack is also published as a live
EcoIQ platform page at `/mrv-agent-training-pack/` (see
`mrv_agent_training_pack/` in the repo root for the Django app backing that
page). This `ai_agents/mrv_agent/` folder is the implementation-ready,
file-based counterpart — consistent with the published page.

## Position in the EcoIQ agent pipeline

```
Finance Modelling Agent → MRV Agent → Governance Agent → Report Generator Agent
```

## What it produces

An MRV status and impact assessment (see `outputs.md`) consumed by:

- **Certification & Trust Badge Engine** — badge recommendation
- **Public Trust & Impact Portal** — public reporting readiness gate
- **Knowledge Graph & Relationship Map** — MRV claim evidence nodes
- **Report Generator Agent** — impact claims for investor memos/board packs

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
