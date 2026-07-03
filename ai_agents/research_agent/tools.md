# Research Agent — Tools

## EcoIQ modules this agent reads from / writes to

- **Data Room & Evidence Vault** — stores any documents the agent retrieves or is given
- **Knowledge Graph & Relationship Map** — evidence nodes this agent's findings become (`EVIDENCE_SUPPORTS_CLAIM`)
- **Certification & Trust Badge Engine** — consumes evidence quality to help decide badge readiness
- **Country Transition Atlas** — sector/country context this agent can draw on
- **Agent Training & Evaluation Lab** — the shared training/evaluation method this pack follows

## External tool concepts (not yet wired to a live runtime)

- Web search / retrieval tool, restricted to public sources
- Company registry lookup (where available per jurisdiction)
- Regulatory filing search (per-country, where public)
- Document parsing for any PDF/report supplied directly (handed to
  **Document Reader Agent** rather than duplicated here)

## Explicit non-tools

- No access to private/internal company systems
- No web scraping of paywalled or login-gated content
- No social media scraping of individuals
- No automated public posting — Research Agent only produces draft evidence
  summaries for human and downstream-agent review
