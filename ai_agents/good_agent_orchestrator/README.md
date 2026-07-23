# Good Agent Orchestrator

## Mission

Take one observed real-world signal (a reported problem, waste, or unmet
need) and decide which of the 114 canonical EcoIQ principles — re-expressed
as "Good Agent" lenses — are actually relevant to it, then produce a
structured, evidence-checked reasoning pass across only those lenses.

This agent never activates all 114 lenses for a signal. It runs a layered
filter (deterministic keyword/domain match, then a single combined
reasoning call covering every activated lens together) so cost stays
bounded regardless of how many principles are eventually seeded.

## Position in the pipeline

```
Signal -> Good Agent Orchestrator -> relevant principle lenses -> GoodOpportunity
       -> (existing capital_guardian / waste_to_value_capital_allocation_engine
          pipeline: OperationalLoss -> Better Way -> Capital Decision -> MRV)
```

See `good_agents/services/orchestrator.py` for the real implementation and
`docs/114_GOOD_AGENTS.md` for the full architecture writeup.
