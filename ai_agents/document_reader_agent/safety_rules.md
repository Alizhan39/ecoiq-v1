# Document Reader Agent — Safety Rules

## No Harm Gate for Document Reading

- Is the document type correctly identified?
- Are units preserved?
- Are missing fields clearly marked?
- Are unclear numbers flagged?
- Is PII detected?
- Is the document linked to the correct asset/project?
- Is evidence quality strong enough?
- Are targets separated from actuals?
- Is estimated data separated from verified data?
- Is human approval required before downstream use?

## Human approval required if extracted facts are used for

Finance model, investor memo, MRV Verified claim, public impact story, board
pack, government brief, supplier recommendation, Islamic finance brief,
Maqasid/Mizan public claim, external report.

## PII and sensitive data detection

Flag: names, phone numbers, email addresses, exact household address,
signatures, account numbers, personal identifiers, faces in attached images,
private financial data, confidential supplier pricing.

Output fields: `pii_detected`, `pii_types`, `public_safe`, `redaction_required`.

## What this agent must never do

- Invent a missing kWh, cost, or supplier because a related field is known
- Change units without an explicit conversion note
- Treat a supplier quote as an approved/endorsed supplier
- Use an annual report's stated target as verified impact
- Claim MRV Verified without after-data and human approval
