# Waste & Leakage Agent — Demo Scenarios

## Golden case: Meat Cold-Chain Loss Prevention

**Audience:** an investor or judge evaluating whether EcoIQ's capital
allocation recommendations are trustworthy.

**Inputs:** £80,000 inventory value, a refrigeration temperature excursion,
a 15% historical spoilage rate, a 36-hour intervention window, an electricity
bill, a maintenance record, and a supplier quote for a cold-chain equipment
upgrade.

**Required conclusion:**

```
Projected capital at risk: £12,000
Classification: Forecast
Confidence: Medium
```

The agent never says "Verified loss: £12,000" — nothing has actually been
lost yet, and no independent post-incident evidence exists. The £12,000
figure comes from the real `calculate_capital_at_risk()` service
(`inventory_value × historical_loss_rate` = `80000 × 0.15`), not a number
this agent invents independently. The refrigeration temperature excursion is
treated as a signal worth investigating, not a confirmed equipment failure —
and the supplier's quote is treated as a price offer, not independent
technical verification. Missing data (an independent technical inspection)
is stated explicitly. The case is then routed to Document Reader Agent
(to extract the bill, maintenance record and supplier quote in full) and
onward through the same real AI Agent Council pipeline that already handles
this case — Finance Modelling Agent, MRV Agent, Governance Agent and Report
Generator Agent — ending in a governed, human-approved decision.

**Why it lands:** it demonstrates EcoIQ will not let urgency or a compelling
story turn a projection into a claimed fact — exactly the discipline a
serious capital allocator needs before trusting any of the platform's other
numbers.

## Enterprise use case

**Audience:** an operations team deciding which of several loss signals
deserves the next intervention budget.

Waste & Leakage Agent triages incoming signals (temperature excursions,
utility bill anomalies, maintenance flags) into `capital_at_risk` estimates
with explicit confidence and missing-data lists, giving the team a ranked,
evidence-backed starting point rather than a gut-feel priority list.

## Amanah alignment

This agent never authorises supplier outreach, funder outreach, investor
communication, external financial recommendations, food redistribution
action, public impact publication, or high-impact industrial intervention —
it states clearly when human approval is required and leaves the decision
with a qualified human reviewer.
