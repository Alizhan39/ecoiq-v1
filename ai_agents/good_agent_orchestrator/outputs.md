```json
{
  "agent_name": "Good Agent Orchestrator",
  "positions": [
    {
      "principle_id": 34,
      "position": "support | concerns | conflicts",
      "confidence": 0,
      "concern": "",
      "recommended_next_analysis": ""
    }
  ]
}
```

`positions` must contain exactly one entry per lens in `activated_lenses` —
never more (no inventing an unactivated lens's opinion) and never fewer
(a lens that was activated must state a position, even if uncertain).
