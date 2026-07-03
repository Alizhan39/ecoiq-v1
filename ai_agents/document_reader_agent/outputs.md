# Document Reader Agent — Output Schema

```json
{
  "agent_name": "Document Reader Agent",
  "document_type": "",
  "input_summary": "",
  "extracted_fields": {},
  "tables": [],
  "key_figures": [],
  "dates": [],
  "units": [],
  "currency": "",
  "asset_or_project_links": [],
  "evidence_quality": "strong | medium | weak | unreadable",
  "missing_fields": [],
  "confidence": 0.0,
  "risk_flags": [],
  "human_approval_required": true,
  "next_action": "",
  "status": "draft | needs_review | usable | blocked"
}
```

## Evidence quality rubric

- **Strong**: clear machine-readable text, complete fields, readable tables,
  clear dates/units, document matches project/asset
- **Medium**: most fields clear, some missing data, small formatting
  ambiguity, document likely matches project/asset
- **Weak**: scanned/blurred document, unclear numbers, missing dates/units,
  document mismatch possible, handwritten or low quality
- **Unreadable**: cannot reliably extract key information, image too blurry,
  table unavailable, wrong file type, corrupted text

This mirrors the rubric published on the live `/document-reader-agent-training-pack/` page.
