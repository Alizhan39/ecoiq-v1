# Digital Twin Agent — Inputs

- DigitalTwin.completeness_score/confidence_score/data_freshness_score
- TwinDataGap rows
- ProcessNode/ResourceFlow/OperationalMetric counts

All inputs are read directly from already-persisted `digital_twin` (and, where
named, other EcoIQ app) rows — never inferred from absence, and never
supplied as free-form unstructured text without a source.
