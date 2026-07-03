# Asset Passport Agent — Output Schema

```json
{
  "agent_name": "Asset Passport Agent",
  "asset_name": "",
  "location": "",
  "owner": "",
  "asset_type": "",
  "sector": "",
  "condition": "",
  "baseline_fields": {},
  "evidence_links": [],
  "risks": [],
  "missing_data": [],
  "confidence": 0.0,
  "risk_flags": [],
  "human_approval_required": true,
  "recommended_next_step": "",
  "status": "draft | needs_review | usable | blocked"
}
```

`condition` must be one of: `"unknown"`, `"poor"`, `"fair"`, `"good"` — and
must always be paired with the evidence in `evidence_links` that supports it.
