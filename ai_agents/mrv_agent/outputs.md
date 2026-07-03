# MRV Agent — Output Schema

```json
{
  "agent_name": "MRV Agent",
  "project": "",
  "asset": "",
  "claim_type": "",
  "mrv_stage": "",
  "baseline_evidence": [],
  "after_evidence": [],
  "methodology": "",
  "baseline_value": null,
  "after_value": null,
  "unit": "",
  "estimated_impact": null,
  "verified_impact": null,
  "confidence": 0.0,
  "evidence_quality": "strong | medium | weak | insufficient",
  "missing_evidence": [],
  "risk_flags": [],
  "human_approval_required": true,
  "public_reporting_ready": false,
  "badge_recommendation": "",
  "next_action": "",
  "status": "draft | blocked | needs_review | verified"
}
```

This exactly mirrors the schema published on the live
`/mrv-agent-training-pack/` page — see that page's "MRV Stages" and
"Estimated vs Verified" sections for the full stage/evidence-quality rubric.
