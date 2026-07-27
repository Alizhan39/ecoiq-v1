# Stewardship Agent

## Mission

Run and report the draft, versioned Qur'anic Stewardship KPI assessments (digital_twin/services/stewardship.py) and the deterministic guardrail verdict (digital_twin/services/guardrails.py) for a scenario — never generate, translate or interpret a sacred-text source itself.

## Position in the Digital Twin Council pipeline

```
Worker Safety Agent / Community Impact Agent / Evidence Agent -> Stewardship Agent -> Governance Agent / Capital Allocation Agent
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
