# Evidence Agent — Inputs

- ModernisationScenario.evidence_references/confidence
- evidence_memory.EvidenceMemory (via source_reference)

All inputs are read directly from already-persisted `digital_twin` (and, where
named, other EcoIQ app) rows — never inferred from absence, and never
supplied as free-form unstructured text without a source.
