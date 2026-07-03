# Photo / Visual Evidence Agent — Output Schema

```json
{
  "agent_name": "Photo / Visual Evidence Agent",
  "asset_reference": "",
  "site_name": "",
  "input_summary": "",
  "visible_risk_notes": [],
  "asset_components": [],
  "possible_issues": [],
  "missing_sensors": [],
  "safety_concerns": [],
  "needs_verification_labels": [],
  "image_quality": "clear | acceptable | poor | unreadable",
  "confidence": 0.0,
  "pii_detected": false,
  "pii_types": [],
  "risk_flags": [],
  "human_approval_required": true,
  "next_action": "",
  "status": "draft | needs_review | usable | blocked"
}
```

Every entry in `possible_issues` and `safety_concerns` must also appear (or be
referenced) in `needs_verification_labels` — nothing from this agent is a
final engineering conclusion.
