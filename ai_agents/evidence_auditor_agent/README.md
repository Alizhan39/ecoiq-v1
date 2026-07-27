# Evidence Auditor

## Mission

Independently re-check that every claim underpinning a ResearchRecommendation has a real, resolvable evidence_id — refuse a recommendation containing an unreferenced factual statement.

## Position in the Global Research Council pipeline

```
Regulatory Agent -> Evidence Auditor -> Research Synthesis Agent
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
| `demo_scenarios.md` | Global Technology Search for Industrial Heat Modernisation demo script |
