# Research Agent

## Mission

Find and summarise public evidence about a company, asset, sector or country from
reports, filings, websites, news and other trusted public sources — cautiously,
with sources attached, and without inventing anything that isn't in the source
material.

Research Agent is the entry point for EcoIQ's company- and country-level
intelligence. It runs before Document Reader Agent gets involved with a specific
project, and its output seeds Asset Passport, Governance Agent and
Report Generator Agent with an initial, source-linked evidence base.

## Position in the EcoIQ agent pipeline

```
Research Agent → Document Reader Agent → Asset Passport Agent →
Industrial Playbook Matching Agent → Finance Modelling Agent → MRV Agent →
Governance Agent → Report Generator Agent
```

Amanah Autopilot Supervisor runs overnight across all of the above.

## What it produces

A structured evidence summary (see `outputs.md`) with a source list, missing-data
flags, a confidence level, and outdated-information flags — consumed by:

- **Asset Passport Agent** — public company/asset context for a new passport
- **Governance Agent** — public disclosures relevant to a review packet
- **Report Generator Agent** — background evidence for investor memos and briefs
- **Knowledge Graph & Relationship Map** — evidence nodes linked to companies/assets

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

## Status

Training pack complete. Implementation is not yet wired to a live LLM orchestration
runtime — see `ai_agents/ai_agent_training_index.md` for the current rollout phase.
