# Worker Safety Agent

## Mission

Review a scenario's worker_impact narrative and operational_disruption level for safety risk, using the same deterministic harm-keyword screen as the Stewardship KPI engine.

## Position in the Digital Twin Council pipeline

```
Engineering Agent -> Worker Safety Agent -> Governance Agent
```

## Files in this pack

| File | Purpose |
|---|---|
| `system_prompt.md` | Production system prompt |
| `role.md` | Mission, boundaries, what it must never invent |
| `inputs.md` | What data it can read |
| `outputs.md` | Required JSON output schema |
| `tools.md` | Tools and EcoIQ modules it calls |
| `safety_rules.md` | Human-approval triggers |
| `test_cases.json` | Realistic test cases |
| `evals.md` | Evaluation metrics and pass/fail criteria |
| `demo_scenarios.md` | Industrial Heat Modernisation Pilot demo script |
