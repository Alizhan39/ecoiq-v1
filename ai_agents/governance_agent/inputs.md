# Governance Agent — Inputs

| Input | Description |
|---|---|
| `project_risks` | Risks identified across the pipeline (Asset Passport, Playbook Matching) |
| `evidence` | Evidence quality summary |
| `finance_memo` | Finance Modelling Agent's draft |
| `mrv_claim` | MRV Agent's status and claim |
| `public_summary` | Draft public-facing summary, if any |
| `supplier_match` | Supplier/Funding Match information, if any |

## Reviewer types

Technical, Financial, Environmental, Safety, Maqasid/Mizan, Islamic finance,
Public summary approval — matched to the content type in the packet.

## What it does NOT accept as input

- A request to skip assembling a full packet and jump straight to "approved"
