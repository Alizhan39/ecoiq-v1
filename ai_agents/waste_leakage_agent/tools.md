# Waste & Leakage Agent — Tools

## EcoIQ modules this agent reads from / writes to

- **Waste-to-Value Capital Allocation Engine** — the platform module this
  agent's detection populates (`OperationalLoss`, `LossEvidence`); calls its
  real `services/capital_risk.py::calculate_capital_at_risk()` and
  `predict_recoverable_value()` rather than re-implementing the arithmetic
- **Agent Runtime & Model Router** — the execution pipeline this agent runs
  through (`create_agent_run` → `execute_agent` →
  `submit_agent_position_to_council`); no separate execution path
- **AI Agent Council** — receives this agent's position as a real `AgentTask`
  (`collaboration_mode='solo'`, running first, before Document Reader Agent)
- **Data Room & Evidence Vault** — utility bills, maintenance records,
  supplier quotes, sensor logs
- **Knowledge Graph & Relationship Map** — loss evidence nodes
  (`ORGANISATION_HAS_OPERATIONAL_LOSS`, `LOSS_BACKED_BY_EVIDENCE`,
  `LOSS_QUANTIFIED_AS_FINANCIAL`)
- **Amanah Autopilot Supervisor** — overnight high-risk-inventory alerts
  triggered by this agent's `risk_flags`

## Explicit non-tools

- No automatic supplier or funder outreach
- No automatic public impact publication
- No automatic MRV verification — that is MRV Agent's exclusive role
- No automatic capital reallocation
