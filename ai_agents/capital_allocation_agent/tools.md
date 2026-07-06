# Capital Allocation Agent — Tools

## EcoIQ modules this agent reads from / writes to

- **Waste-to-Value Capital Allocation Engine** — reads the real
  `InterventionOption` rows for a case; calls
  `services/capital_allocation_scoring.py::score_intervention_option()` and
  `services/ranking.py::rank_capital_allocation_options()` rather than
  re-implementing the scoring or ranking arithmetic; writes
  `CapitalAllocationDecision.ranking` via `services/governance.py::create_governed_investment_case()`
- **Agent Runtime & Model Router** — the execution pipeline this agent runs
  through (`create_agent_run` → `execute_agent` →
  `submit_agent_position_to_council`); no separate execution path
- **AI Agent Council** — receives this agent's position as a real `AgentTask`
  (`collaboration_mode='council'`), running after Finance Modelling Agent,
  MRV Agent and Governance Agent have already submitted their positions
- **Institutional Finance Engine** — presentational context for how a ranked
  option maps to real-world funding routes (no separate models; read-only
  cross-reference)
- **Impact MRV Layer** — presentational context for what "verified" means
  downstream of this agent's ranking
- **Knowledge Graph & Relationship Map** — ranking evidence nodes
  (`INTERVENTION_OPTION_RANKED_BY_CAPITAL_ALLOCATION_AGENT`)

## Explicit non-tools

- No autonomous movement of capital
- No automatic supplier outreach
- No automatic funder outreach
- No automatic investor communication
- No automatic approval-status changes — `approval_status` is only ever set
  by a governed Council/human decision, never by this agent's own ranking
