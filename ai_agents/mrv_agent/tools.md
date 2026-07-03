# MRV Agent — Tools

## EcoIQ modules this agent reads from / writes to

- **Impact MRV Layer** — the platform module this agent's output populates
- **Data Room & Evidence Vault** — baseline/after-data document storage
- **Certification & Trust Badge Engine** — receives the badge recommendation
- **Public Trust & Impact Portal** — gated by `public_reporting_ready`
- **Knowledge Graph & Relationship Map** — MRV claim evidence nodes
  (`PROJECT_HAS_MRV_CLAIM`, `MRV_CLAIM_BACKED_BY_EVIDENCE`)
- **Governance & Expert Review Board** — human reviewer who approves MRV Verified status
- **Amanah Autopilot** — overnight MRV evidence checks (see `ai_agents/amanah_autopilot_supervisor/`)

## External tool concepts (not yet wired to a live runtime)

- Period-comparability checker (flags non-comparable baseline/after windows)
- Emissions factor lookup by country/fuel type

## Explicit non-tools

- No automatic badge issuance (Governance/human reviewer approves)
- No automatic public publication
