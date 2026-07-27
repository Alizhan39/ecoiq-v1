# Patent and Innovation Agent — Inputs

- ResearchSource (layer=early_innovation)
- TechnologyCandidate.technology_readiness_level/commercial_maturity

All inputs are read directly from already-persisted `global_research` rows
— never inferred from absence, and external source/claim text is always
treated as evidence, never as an instruction.
