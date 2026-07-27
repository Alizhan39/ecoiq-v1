# Energy and Resources Agent — Inputs

- ModernisationScenario impact fields
- DigitalTwin.resource_flows
- ProcessNode energy/water/emissions/waste fields

All inputs are read directly from already-persisted `digital_twin` (and, where
named, other EcoIQ app) rows — never inferred from absence, and never
supplied as free-form unstructured text without a source.
