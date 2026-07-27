# Evidence Agent — Output Schema

```json
{
  "agent": "<agent name>",
  "position": "support | oppose | conditional | insufficient_evidence",
  "summary": "one-paragraph plain-language summary",
  "claims": ["specific, falsifiable claims this agent is making"],
  "evidence_ids": ["evidence_memory.EvidenceMemory source_reference strings this position relies on"],
  "confidence": 0,
  "conditions": ["conditions that would change this position, if any"],
  "risks": ["risk_flags"],
  "missing_data": ["what would need to exist for a stronger position"]
}
```
This is the same strict schema every EcoIQ Council agent uses
(`agent_training_evaluation_lab/views.py::AGENT_OUTPUT_SCHEMA_FIELDS`,
enforced by `agent_runtime_model_router/services/schema_validation.py`).
