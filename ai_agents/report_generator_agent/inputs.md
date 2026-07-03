# Report Generator Agent — Inputs

| Input | Description |
|---|---|
| `asset_passport` | Completed asset record |
| `finance_model` | Finance Modelling Agent's draft |
| `mrv_status` | MRV Agent's stage and claim |
| `evidence` | Underlying evidence bundle |
| `governance_review` | Governance Agent's packet and approval status |
| `graph_trace` | Knowledge Graph relationship trace |
| `report_type` | investor memo, board pack, public summary, country brief |

## What it does NOT accept as input

- A request to generate a public summary or investor memo with no governance
  approval recorded at all — the request is declined until governance review completes
