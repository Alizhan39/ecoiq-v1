# Research Agent — Output Schema

Every research run must return this JSON schema:

```json
{
  "agent_name": "Research Agent",
  "subject": "",
  "subject_type": "company | asset | sector | country",
  "task_type": "public_research",
  "input_summary": "",
  "evidence_summary": [],
  "source_list": [
    {
      "title": "",
      "source_type": "filing | report | news | website | registry",
      "publication_date": "",
      "url_or_reference": ""
    }
  ],
  "missing_data": [],
  "outdated_information_flags": [],
  "confidence": 0.0,
  "risk_flags": [],
  "human_approval_required": true,
  "next_action": "",
  "status": "draft | needs_review | usable | blocked"
}
```

## Field notes

- `evidence_summary`: list of short, source-attributed statements, not a
  single narrative paragraph — each one traceable to `source_list`
- `confidence`: 0.0–1.0, must be lowered whenever sources conflict, are old,
  or are single-sourced
- `human_approval_required`: `true` whenever the output will support a public
  claim, an investor memo, or a government briefing (see `safety_rules.md`)
- `status`: `"blocked"` if the subject cannot be identified or no reliable
  source exists at all
