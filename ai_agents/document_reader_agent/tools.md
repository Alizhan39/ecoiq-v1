# Document Reader Agent — Tools

## EcoIQ modules this agent reads from / writes to

- **Data Room & Evidence Vault** — source of truth for the documents it reads
- **Asset Passport** — receives baseline fields extracted from bills/reports
- **Institutional Finance Engine** — receives CAPEX/OPEX assumptions
- **Impact MRV Layer** — receives baseline/after-data from MRV evidence documents
- **Knowledge Graph & Relationship Map** — evidence-fact nodes
  (`DOCUMENT_EXTRACTED_FACT`, `DOCUMENT_LINKED_TO_ASSET`, `DOCUMENT_LINKED_TO_PROJECT`)
- **Certification & Trust Badge Engine** — evidence-quality signal for badges
- **Security, Privacy & Compliance Centre** — governs handling of detected PII

## External tool concepts (not yet wired to a live runtime)

- OCR/document parsing (PDF text + table extraction)
- Structured table extraction with confidence scoring
- PII detection classifier

## Explicit non-tools

- No automatic unit conversion
- No automatic filling of missing fields from other documents without a
  human-reviewed link
- No publishing of extracted facts directly to any public surface
