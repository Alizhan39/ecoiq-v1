# Document Reader Agent

## Mission

Extract reliable structured facts from uploaded documents — energy bills, fuel
bills, water bills, annual/ESG reports, maintenance logs, inspection reports,
supplier quotes, invoices, technical specifications and MRV evidence — without
guessing missing data or creating unsupported claims.

This is the foundation agent: most downstream EcoIQ outputs (Asset Passport
baseline fields, finance model assumptions, MRV baseline/after-data, investor
memo evidence) depend on facts this agent extracts correctly. If it guesses or
misreads data, EcoIQ can overstate savings, impact, risk or finance readiness.

A full, richer version of this training pack is also published as a live
EcoIQ platform page at `/document-reader-agent-training-pack/` (see
`document_reader_agent_training_pack/` in the repo root for the Django app
backing that page). This `ai_agents/document_reader_agent/` folder is the
implementation-ready, file-based counterpart of the same agent — consistent
with the published page, formatted for direct use by an agent runtime.

## Position in the EcoIQ agent pipeline

```
Research Agent → Document Reader Agent → Asset Passport Agent →
Industrial Playbook Matching Agent → Finance Modelling Agent → MRV Agent →
Governance Agent → Report Generator Agent
```

## What it produces

A structured extraction (see `outputs.md`) consumed by:

- **Asset Passport Agent** — baseline fields (condition, location, energy use)
- **Finance Modelling Agent** — CAPEX/OPEX assumptions from bills and quotes
- **MRV Agent** — baseline and after-data extracted from bills/meters
- **Knowledge Graph & Relationship Map** — evidence nodes linked to assets/projects
- **Certification & Trust Badge Engine** — evidence-quality input to badge decisions

## Files in this pack

| File | Purpose |
|---|---|
| `system_prompt.md` | Production system prompt |
| `role.md` | Mission, boundaries, what it must never invent |
| `inputs.md` | Document types and fields it reads |
| `outputs.md` | Required JSON output schema |
| `tools.md` | Tools and EcoIQ modules it calls |
| `safety_rules.md` | No Harm Gate, human approval triggers |
| `test_cases.json` | 5 realistic test cases + 3 failure cases |
| `evals.md` | Evaluation metrics and pass/fail criteria |
| `demo_scenarios.md` | Investor and enterprise/government demo scripts |
