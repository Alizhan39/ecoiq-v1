# Asset Passport Agent — Tools

## EcoIQ modules this agent reads from / writes to

- **Asset Passport** (the platform module this agent's output populates)
- **Data Room & Evidence Vault** — evidence storage this agent draws from
- **Industrial Playbook Matching Agent** — receives the completed passport
- **Institutional Finance Engine** — receives baseline fields relevant to CAPEX/OPEX
- **Impact MRV Layer** — receives baseline fields relevant to MRV
- **Knowledge Graph & Relationship Map** — the asset node other evidence attaches to

## External tool concepts (not yet wired to a live runtime)

- Structured merge logic for combining Document Reader + Photo/Visual Evidence outputs
- Conflict detection across evidence sources

## Explicit non-tools

- No playbook assignment (Industrial Playbook Matching Agent's job)
- No finance readiness scoring (Finance Modelling Agent's job)
- No MRV status assignment (MRV Agent's job)
