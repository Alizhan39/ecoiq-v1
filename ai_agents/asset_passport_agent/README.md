# Asset Passport Agent

## Mission

Create structured, evidence-linked asset records — the single "one asset, one
story" record that Playbook Matching, Finance Modelling, MRV and Report
Generator all build on.

## Position in the EcoIQ agent pipeline

```
Research Agent + Document Reader Agent + Photo/Visual Evidence Agent →
Asset Passport Agent → Industrial Playbook Matching Agent →
Finance Modelling Agent → MRV Agent → Governance Agent → Report Generator Agent
```

## What it produces

An Asset Passport draft (see `outputs.md`) consumed by:

- **Industrial Playbook Matching Agent** — asset type, condition, risks, constraints
- **Finance Modelling Agent** — baseline energy/fuel/water use
- **MRV Agent** — baseline evidence for measurement/verification
- **Knowledge Graph & Relationship Map** — the asset node other evidence links to
- **Certification & Trust Badge Engine** — evidence completeness for badge decisions

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
