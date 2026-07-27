# Commercial Intelligence Agent — Output Schema

```json
{
  "agent": "<agent name>",
  "mission_id": "",
  "findings": [],
  "claims": [],
  "source_ids": [],
  "candidate_ids": [],
  "confidence": 0,
  "limitations": [],
  "missing_information": [],
  "recommended_next_action": ""
}
```
No agent may create an unreferenced factual statement in its findings — every
finding must cite a real source_id/claim id it came from.
