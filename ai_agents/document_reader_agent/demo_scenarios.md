# Document Reader Agent — Demo Scenarios

## Investor demo scenario

**Audience:** development bank reviewing a compressed-air optimisation
project in Türkiye.

1. Field team uploads a baseline electricity bill and a supplier quote for
   leak repair.
2. Document Reader Agent extracts CAPEX, exclusions, and warranty from the
   quote, and kWh/cost from the bill — flagging the quote as
   "not an endorsement, human approval required before supplier recommendation."
3. Investor sees exactly which figures are extracted, which are missing, and
   that nothing has been assumed.

**Why it lands:** investors see a system that would rather say "missing" than
guess — a direct answer to the common concern that AI tools overstate confidence.

## Enterprise / government use case

**Audience:** a national utility's engineering team standardising evidence
intake across dozens of sites.

Document Reader Agent processes maintenance logs and inspection reports at
scale, flagging recurring faults and missing measurements automatically —
turning inconsistent paperwork into a structured, comparable dataset the
utility's own engineers still review before acting on.

## Islamic ethical finance / Amanah alignment

When a supplier quote references Islamic finance terms (murabaha, ijara),
Document Reader Agent extracts the terms as stated facts only, routing any
Maqasid/Mizan classification to Governance Agent — never asserting Shariah
compliance itself.

## MRV / audit trail requirements

Every MRV evidence document extraction is stamped with
`asset_or_project_links` and `evidence_quality`, so the MRV Agent (see
`ai_agents/mrv_agent/`) can trace every baseline/after-data figure back to
its exact source document.
