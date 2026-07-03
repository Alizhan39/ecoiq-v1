# Photo / Visual Evidence Agent

## Mission

Analyse inspection photos and videos of industrial assets — boilers,
compressors, meters, tanks, flare stacks, tailings dams, agricultural
equipment — and produce cautious, labelled visual observations that
downstream agents and human reviewers can act on. Photo findings are
**hypotheses, not engineering conclusions.**

## Position in the EcoIQ agent pipeline

```
Document Reader Agent + Photo / Visual Evidence Agent → Asset Passport Agent →
Industrial Playbook Matching Agent → Finance Modelling Agent → MRV Agent →
Governance Agent → Report Generator Agent
```

Photo / Visual Evidence Agent typically runs alongside Document Reader Agent,
feeding the same Asset Passport with complementary visual evidence.

## What it produces

Visible risk notes, identified asset components, possible issues, missing
sensors, safety concerns and "Needs verification" labels — consumed by:

- **Asset Passport Agent** — photo-derived condition notes
- **Industrial Playbook Matching Agent** — visible risk signals affecting playbook fit
- **Governance Agent** — safety concerns requiring expert sign-off
- **Knowledge Graph & Relationship Map** — evidence nodes linked to assets

## Files in this pack

| File | Purpose |
|---|---|
| `system_prompt.md` | Production system prompt |
| `role.md` | Mission, boundaries, what it must never invent |
| `inputs.md` | What imagery it can read |
| `outputs.md` | Required JSON output schema |
| `tools.md` | Tools and EcoIQ modules it calls |
| `safety_rules.md` | No Harm Gate, human approval triggers |
| `test_cases.json` | 5 realistic test cases + 3 failure cases |
| `evals.md` | Evaluation metrics and pass/fail criteria |
| `demo_scenarios.md` | Investor and enterprise/government demo scripts |
