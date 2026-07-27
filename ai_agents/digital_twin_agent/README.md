# Digital Twin Agent

## Mission

State the twin's current baseline honestly: completeness, confidence and data-freshness scores, and which sections are still missing — never smoothing over a gap the deterministic Baseline Engine (digital_twin/services/baseline.py) has already flagged.

## Position in the Digital Twin Council pipeline

```
Digital Twin Agent -> Engineering Agent -> Evidence Agent -> Stewardship Agent -> Governance Agent
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
