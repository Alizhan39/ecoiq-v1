# Capital Allocation Agent — Demo Scenarios

## Golden case: Meat Cold-Chain Loss Prevention — "Where should the next £1 go?"

**Audience:** an investor or judge evaluating whether EcoIQ's capital
allocation recommendations are trustworthy, not just its loss detection.

**Inputs:** the same Meat Cold-Chain case Waste & Leakage Agent, Finance
Modelling Agent, MRV Agent and Governance Agent have already deliberated —
£80,000 inventory value, £12,000 projected capital at risk, a 36-hour
intervention window — and the same 7 real, already finance-modelled
intervention options:

```
A. Dynamic discount now
B. Transfer to another branch (dynamic, discounted resale)
C. Sell to processor
D. Safe donation where appropriate
E. Freeze / reprocess
F. Cold-chain equipment intervention
G. Anaerobic digestion as last resort
```

**Required conclusion:** the Capital Allocation Agent ranks **Cold-chain
equipment intervention** first — it scores highest across the materiality-
scaled dimensions (financial return, loss avoided) that matter most for a
recurring risk, even though several tactical options (A, B, C) score higher
on raw capital efficiency because their capex is small. The agent states
this distinction explicitly: **highest capital efficiency and highest
overall ranking are not the same thing**, and answers all 10 required
questions:

1. **Which option deserves capital first?** Cold-chain equipment intervention.
2. **Why?** It is the only option that prevents this loss from recurring
   every cycle, not just this one; its financial return and loss-avoided
   scores, scaled against the case's own £12,000 capital-at-risk ceiling,
   outweigh its lower raw capital efficiency.
3. **What evidence supports the ranking?** The real `InterventionOption`
   fields Finance Modelling Agent already produced (capex, estimated annual
   savings, estimated loss avoided, payback, readiness scores) — this agent
   invents no new finance numbers.
4. **Which assumptions affect the result?** That a same-cycle tactical
   action (no multi-month payback) is treated as realising its value within
   this cycle, not as a stronger or weaker claim than that.
5. **What risks remain unresolved?** Governance Agent's food-safety review
   and MRV Agent's post-intervention verification are both still open.
6. **Highest capital efficiency?** One of the small-capex tactical options
   (e.g. Dynamic discount now) — a genuine ratio result, reported honestly
   even though it isn't the top-ranked option overall.
7. **Fastest value recovery?** A tactical resale/redistribution option
   realises value within the 36-hour window; the equipment option's value
   accrues over future cycles instead.
8. **Longest-term CAPEX?** Cold-chain equipment intervention — the only
   option with multi-month payback and physical asset investment.
9. **What requires human approval?** Any autonomous movement of capital,
   supplier outreach, funder outreach, and investor communication — the
   ranking itself is a recommendation for Council/human review, never an
   autonomous investment decision.
10. **What should MRV measure afterward?** Post-intervention temperature and
    spoilage data, to convert the equipment option's estimated annual
    savings into a verified return.

**Why it lands:** it demonstrates EcoIQ compares real options honestly —
including reporting where the top-ranked option is *not* the most capital-
efficient one — rather than quietly picking whichever number looks best,
exactly the discipline a serious capital allocator needs before trusting any
recommendation this platform makes.

## Enterprise use case

**Audience:** an operations or finance team with several competing
intervention options and a limited capital budget.

Capital Allocation Agent produces one ranked list across all 13 dimensions,
with the assumptions and unresolved risks stated explicitly, giving the team
an evidence-backed starting point for a governed capital committee decision
— not a fully autonomous allocation.

## Amanah alignment

This agent never authorises autonomous capital movement, automatic supplier
outreach, automatic funder outreach, or automatic investor communication —
it produces a ranked recommendation and states clearly when human approval
is required, leaving the actual capital decision with a qualified human
reviewer and the governed AI Agent Council process.
