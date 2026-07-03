# Document Reader Agent — Inputs

## Document types and fields extracted

1. **Energy bill** — supplier, billing period, account/site reference, kWh
   used, unit rate, standing charge, total cost, VAT/tax, meter number,
   estimated vs actual reading, currency, missing fields
2. **Fuel bill** — fuel type, volume/weight, unit, cost, billing period,
   supplier, delivery date, asset/site, emissions factor required note,
   missing fields
3. **Water bill** — supplier, billing period, volume used, unit, total cost,
   meter reading, estimated vs actual, site reference, missing fields
4. **Annual report / ESG report** — company name, reporting year, emissions
   data, energy use, water use, waste data, targets, capex plans, climate
   risks, governance statements, source page/section, confidence, missing data
5. **Maintenance log** — asset name, service date, issue, action taken,
   downtime, parts replaced, engineer note, recurring issue, safety concern,
   missing fields
6. **Inspection report** — site, inspector, date, asset condition, observed
   risks, recommendations, photos referenced, measurements, required
   follow-up, missing evidence
7. **Supplier quote** — supplier name, quote date, technology/equipment,
   quantity, CAPEX, installation cost, warranty, lead time, exclusions,
   assumptions, validity period, payment terms, missing fields
8. **Invoice** — vendor, invoice date, invoice number, items, quantities,
   unit prices, total, VAT/tax, currency, project/site reference, missing fields
9. **Technical specification** — equipment type, model, capacity, efficiency,
   fuel/power requirement, operating range, safety notes, maintenance
   requirements, standards referenced, missing fields
10. **MRV evidence document** — project, baseline period, after period,
    measured metric, baseline value, after value, unit, methodology, evidence
    quality, verification status, missing data

## What it does NOT accept as input

- Documents unrelated to an EcoIQ asset/project (flagged as mismatch, not processed as if relevant)
- Requests to fabricate a document's contents from a description alone
- Personal correspondence not relevant to asset/project evidence
