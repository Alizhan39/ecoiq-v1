# Industrial Playbook Matching Agent — Tools

## EcoIQ modules this agent reads from / writes to

- **Industrial Playbook Library** — the catalogue of playbooks this agent matches against
- **Asset Passport** — the evidence source for matching
- **Finance Modelling Agent** — receives the matched actions to cost out
- **Supplier & Funding Marketplace** — receives the supplier needs implied by the playbook
- **Impact MRV Layer** — receives the MRV metrics the playbook implies

## External tool concepts (not yet wired to a live runtime)

- Playbook similarity/matching logic against structured passport fields

## Explicit non-tools

- No finance modelling (Finance Modelling Agent's job)
- No supplier selection/endorsement (Supplier & Funding Marketplace's job, human-reviewed)
