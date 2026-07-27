# Supply Chain Risk Agent — Inputs

- SupplyChainRiskFlag.risk_type/severity/resolution_status

All inputs are read directly from already-persisted `global_research` rows
— never inferred from absence, and external source/claim text is always
treated as evidence, never as an instruction.
