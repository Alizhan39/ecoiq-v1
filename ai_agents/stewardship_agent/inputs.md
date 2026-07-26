# Stewardship Agent — Inputs

- StewardshipAssessment rows
- StewardshipKPI.approval_status
- StewardshipPrinciple.is_approved_for_use

All inputs are read directly from already-persisted `digital_twin` (and, where
named, other EcoIQ app) rows — never inferred from absence, and never
supplied as free-form unstructured text without a source.
