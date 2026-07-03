# Report Generator Agent — Output Schema

```json
{
  "agent_name": "Report Generator Agent",
  "report_type": "investor_memo | board_pack | public_summary | country_brief",
  "project": "",
  "report_draft": "",
  "executive_summary": "",
  "risks": [],
  "assumptions": [],
  "next_action": "",
  "evidence_links": [],
  "governance_approval_confirmed": false,
  "human_approval_required": true,
  "status": "draft | needs_review | usable | blocked"
}
```

`governance_approval_confirmed` must be `true` before `status` can be
`"usable"` for any external audience.
