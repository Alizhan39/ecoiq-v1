# Report Generator Agent — Tools

## EcoIQ modules this agent reads from / writes to

- **Executive Briefing & Board Pack Generator** — the platform module this agent's output feeds
- **Public Trust & Impact Portal** — public summary output, gated by governance approval
- **Data Room & Evidence Vault** — the evidence pack referenced in every report
- **Knowledge Graph & Relationship Map** — graph trace source
- **Governance & Expert Review Board** — approval-status source

## External tool concepts (not yet wired to a live runtime)

- Report templating per `report_type` (investor memo vs public summary have
  different tone/detail requirements)

## Explicit non-tools

- No automated external sending/publishing
- No bypassing governance approval for public content
