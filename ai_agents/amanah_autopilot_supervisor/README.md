# Amanah Autopilot Supervisor

## Mission

Run overnight checks across every EcoIQ project and agent — finding missing
evidence, blocked MRV claims, finance-ready opportunities and unresolved No
Harm alerts — and prepare a morning briefing and human approval queue.
Amanah Autopilot prepares actions for human review; it does not
independently make high-impact decisions.

"Amanah" (trust/stewardship) names the role deliberately: this supervisor
holds nothing back from human reviewers and never quietly resolves a
high-impact decision on its own.

## Position in the EcoIQ agent pipeline

Amanah Autopilot Supervisor does not sit in the linear pipeline — it runs
**across** all other agents, overnight, checking their outputs and
preparing the next day's review queue:

```
Research Agent, Document Reader Agent, Photo/Visual Evidence Agent,
Asset Passport Agent, Industrial Playbook Matching Agent,
Finance Modelling Agent, MRV Agent, Governance Agent, Report Generator Agent
                              ↓
                  Amanah Autopilot Supervisor
                  (overnight checks + morning briefing)
```

See `ai_agents/ai_agent_training_index.md` for the full supervision model.

## What it produces

A morning briefing and review queue (see `outputs.md`) consumed by:

- **Command Centre** — the morning briefing panel
- **Governance & Expert Review Board** — the human approval queue
- **AI Agent Operations Console** — agent task health across the whole pipeline

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
