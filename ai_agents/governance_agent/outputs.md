# Governance Agent — Output Schema

```json
{
  "agent_name": "Governance Agent",
  "project": "",
  "review_packet": {},
  "reviewer_type": [],
  "no_harm_checklist": [],
  "approval_status": "not_ready | ready_for_review | reviewer_approved | reviewer_rejected",
  "blockers": [],
  "human_approval_required": true,
  "next_action": "",
  "status": "draft | needs_review | usable | blocked"
}
```

`approval_status` may only be `reviewer_approved` or `reviewer_rejected` when
a real, recorded human reviewer decision exists — never set by the agent itself.
