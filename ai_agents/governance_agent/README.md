# Governance Agent

## Mission

Prepare expert review and approval workflows — assembling a review packet
from project risks, evidence, finance memo, MRV claim, public summary and
supplier match, routing it to the right reviewer type, and tracking approval
status and blockers. Governance Agent organises human review; it does not
replace it.

## Position in the EcoIQ agent pipeline

```
Finance Modelling Agent + MRV Agent → Governance Agent → Report Generator Agent
```

Governance Agent is the human-in-the-loop checkpoint before a claim, finance
model or public summary can move forward.

## What it produces

A review packet (see `outputs.md`) consumed by:

- **Governance & Expert Review Board** — the platform module this agent's output feeds
- **Certification & Trust Badge Engine** — approval status feeding badge decisions
- **Report Generator Agent** — only proceeds once governance approval is recorded

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
