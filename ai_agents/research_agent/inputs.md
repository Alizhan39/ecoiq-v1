# Research Agent — Inputs

| Input | Description | Example |
|---|---|---|
| `company_name` | Legal or trading name of the company/organisation | "Karaganda Steel JSC" |
| `country` | Country or region of operation | "Kazakhstan" |
| `sector` | Industrial sector | "metals", "oil and gas", "mining" |
| `public_documents` | Uploaded or linked public reports/filings | annual report PDF, ESG report |
| `web_links` | URLs to company or regulator websites, news articles | company sustainability page |
| `user_question` | What the requester actually wants answered | "Does this company report Scope 1/2 emissions?" |

## Sector-specific input notes

- **Energy / oil and gas**: flaring disclosures, methane reporting, national
  energy regulator filings
- **Mining / metals / uranium**: reserve and resource statements (e.g. JORC/NI
  43-101 style codes), tailings dam safety disclosures, radiation safety
  reporting (uranium)
- **Heating and boilers / utilities**: tariff filings, national energy
  efficiency programme registrations
- **Agriculture / food processing**: water use disclosures, supply chain
  traceability statements
- **Manufacturing**: energy intensity reporting, industrial permit filings
- **Public infrastructure**: government procurement records, public asset
  registers

## What it does NOT accept as input

- Private, confidential or internal company documents not intended for public
  research (those go through Document Reader Agent with proper permissions)
- Personal data about individuals (flagged and declined, not processed)
- Requests to research a person rather than a company/asset/sector/country
