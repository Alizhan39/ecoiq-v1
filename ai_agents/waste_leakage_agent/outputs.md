# Waste & Leakage Agent — Output Schema

```json
{
  "agent_name": "Waste & Leakage Agent",
  "organisation": "",
  "asset": "",
  "loss_type": "",
  "classification": "actual | estimated | forecast",
  "capital_at_risk": null,
  "capital_already_lost": 0,
  "recoverable_value_estimate": "",
  "evidence_used": [],
  "missing_data": [],
  "confidence": 0,
  "risk_flags": [],
  "human_approval_required": false,
  "next_action": "",
  "status": "completed | blocked | needs_review"
}
```

## Field notes

- `classification` is mandatory and is exactly one of `actual`, `estimated`,
  `forecast` — never omitted, never a blend of the three.
- `capital_at_risk` is the projected/estimated financial exposure — computed
  by the real `calculate_capital_at_risk()` service in
  `waste_to_value_capital_allocation_engine/services/capital_risk.py`
  (`inventory_value * historical_loss_rate`), never re-derived independently
  by this agent.
- `capital_already_lost` defaults to `0` — it is only non-zero when there is
  actual, dated evidence that loss has already occurred, not merely that it
  might occur.
- `recoverable_value_estimate` is a short routing note (e.g. "Finance
  Modelling Agent to model recovery options"), not a second numeric figure —
  precise recoverable-value modelling belongs to Finance Modelling Agent once
  intervention options exist.
- `confidence` is 0-100, following the same convention as every other
  operational agent's output (`agent_training_evaluation_lab`'s canonical
  `AGENT_OUTPUT_SCHEMA_FIELDS`), not a qualitative label — "Medium" confidence
  is expressed as `60`.

This schema is consumed directly by
`agent_runtime_model_router.services.execution.execute_agent()`'s Structured
Output Validation step and, if trustworthy, becomes a real `AgentTask`
position on the AI Agent Council via `submit_agent_position_to_council()`.
