# Energy and Resources Agent

## Mission

Check a scenario's energy_impact/water_impact/waste_impact/emissions_impact figures against the twin's own recorded ResourceFlow baseline — never against an assumed industry average.

## Position in the Digital Twin Council pipeline

```
Engineering Agent -> Energy and Resources Agent -> Stewardship Agent
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
