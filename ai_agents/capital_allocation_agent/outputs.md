# Capital Allocation Agent — Output Schema

```json
{
  "agent_name": "Capital Allocation Agent",
  "case_title": "",
  "ranked_options": [
    {"title": "", "composite_score": 0, "rank": 1}
  ],
  "top_ranked_option": "",
  "why_top_ranked": "",
  "evidence_supporting_ranking": [],
  "assumptions": [],
  "unresolved_risks": [],
  "highest_capital_efficiency_option": "",
  "fastest_value_recovery_option": "",
  "longest_term_capex_option": "",
  "human_approval_required_for": [],
  "mrv_measurement_recommendation": "",
  "output_summary": "",
  "evidence_used": [],
  "missing_data": [],
  "confidence": 0,
  "risk_flags": [],
  "human_approval_required": true,
  "next_action": "",
  "status": "completed | blocked | needs_review"
}
```

## Field notes

- `ranked_options` is the real output of
  `waste_to_value_capital_allocation_engine/services/ranking.py::rank_capital_allocation_options()`
  — each option's 13 sub-scores are computed by
  `services/capital_allocation_scoring.py::score_intervention_option()` from
  the real `InterventionOption` fields, never invented independently by this
  agent.
- `top_ranked_option` / `why_top_ranked` / `evidence_supporting_ranking` /
  `assumptions` / `unresolved_risks` / `highest_capital_efficiency_option` /
  `fastest_value_recovery_option` / `longest_term_capex_option` /
  `human_approval_required_for` / `mrv_measurement_recommendation` answer the
  10 required questions directly, in that order.
- `top_ranked_option` is a **recommendation for Council/human review**, never
  an autonomous investment decision — this distinction appears explicitly in
  `why_top_ranked` and `output_summary`.
- `human_approval_required` is always `true` for this agent's position —
  a capital allocation ranking always requires human review before any
  action follows from it.
- `confidence` is 0-100, following the same convention as every other
  operational agent's output — not a qualitative label.

This schema is consumed directly by
`agent_runtime_model_router.services.execution.execute_agent()`'s Structured
Output Validation step and, if trustworthy, becomes a real `AgentTask`
position on the AI Agent Council via `submit_agent_position_to_council()`.
