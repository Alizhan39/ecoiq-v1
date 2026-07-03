# Finance Modelling Agent — Output Schema

```json
{
  "agent_name": "Finance Modelling Agent",
  "asset_or_project_reference": "",
  "finance_memo_draft": "",
  "capex_logic": {},
  "opex_logic": {},
  "payback_estimate": null,
  "assumptions": [],
  "risk_notes": [],
  "funding_gap": null,
  "currency": "",
  "confidence": 0.0,
  "human_approval_required": true,
  "next_action": "",
  "status": "draft | needs_review | usable | blocked"
}
```

All monetary figures must be labelled `"estimated"` in `finance_memo_draft`
unless MRV Agent has independently verified the underlying impact.
