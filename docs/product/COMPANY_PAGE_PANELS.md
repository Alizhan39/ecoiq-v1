# Company Page — Panel Audit

Phase 4. The server-rendered organisation page carries eleven panels the React
page does not. This decides which of them belong in EcoIQ v2.

**"Parity" here means parity with the product we intend, not with every legacy
feature.** Recreating all eleven would be porting a page nobody has seen rather
than building the one the product needs.

---

## The fact that shapes every decision below

The detail view **fails closed before it builds any of these panels**. An
organisation whose score is not publishable gets `detail_evidence_pending.html`
instead — name, sector, evidence state, sources on file.

467 of 467 organisations are in that state.

So **no anonymous visitor has ever seen any of these eleven panels.** They are
not a feature being taken away; they are a feature that has never shipped to a
public user. That lowers the cost of removing one and raises the bar for
porting one: each has to earn its place on the strength of what it would say
*when* an assessment finally publishes, not on the strength of being there.

---

## Decisions

| # | panel | lines | engine status | decision |
|---|---|---|---|---|
| 1 | Ethics master scores | 402 | `ethics.scoring` **PRODUCTION** | **KEEP BUT REDESIGN** |
| 2 | Improvement roadmap | 235 | derived from gaps | **KEEP BUT REDESIGN** → fold into Evidence gaps |
| 3 | Financing readiness | 393 | `financing.readiness` **PRODUCTION** | **KEEP PUBLIC** (gated) |
| 4 | Matched financing pathways | 227 | `financing.readiness` | **MOVE TO AUTHENTICATED** |
| 5 | QDF decision filter | 173 | `qdf.decision_integrity` **PRODUCTION** | **KEEP BUT REDESIGN** → Decision risks |
| 6 | Data status / source library | 114 | operational | **MOVE TO AUTHENTICATED** |
| 7 | Shariah eligibility screen | 154 | `company_intelligence`, versioned methodology | **KEEP BUT REDESIGN** |
| 8 | KPI alignment | 140 | evidence-linked, review-tiered | **KEEP BUT REDESIGN** → Material evidence |
| 9 | Controversies | 70 | harm signals | **KEEP PUBLIC** — already built |
| 10 | Watchlist action | 55 | user-scoped | **MOVE TO AUTHENTICATED** — it already is |
| 11 | Stock strip | 33 | market data | **REMOVE** |

**Ported to React: 6. Authenticated: 4. Removed: 1.**

---

## Reasoning where it is not obvious

**4 — Matched financing pathways → authenticated.** Readiness says *this
organisation could meet these criteria*. A matched pathway names an instrument
and says *this one*. Evidence Integrity already established that an eligibility
card is a stronger statement than the score beneath it, and enforced the gate
inside the helper rather than at its callers. Naming specific financing
instruments for a named company on a public page is stronger again — closer to
advice than to assessment. Readiness stays public; the shortlist moves behind
sign-in.

**6 — Data status → authenticated.** It exists so "a production user must never
confuse fixture data with real analysis", and it does that job well. But it is
an operational view of freshness, harvest sources and refresh state: the
answer to *how is our pipeline doing*, not *what should I decide*. The public
page already carries the part a decision-maker needs — coverage, confidence and
provenance.

**7 — Shariah screen → keep, redesigned.** The obvious move is to cut it: a
religious-compliance verdict is the kind of claim EcoIQ has been removing all
programme. Read, it does not make one. It says *"methodology-based screening —
never a religious ruling or individual fatwa"*, names and versions its
methodology, and separates itself explicitly from the coarser "halal" proxy in
the QDF panel. It has a model, versioning tests and real financial-ratio
inputs, and it is directly relevant to the GCC audience the investor pages
target.

Keeping it is the right call **provided the disclaimer travels with the
result**, in the same component, not as a footnote — which is what "redesign"
means here.

**11 — Stock strip → remove.** A share price beside an ethics assessment
implies a relationship EcoIQ does not assert and has no evidence for. It is
also the one panel with no engine behind it in the registry. Removing it costs
33 lines and one implication nobody intended to make.

**1, 2, 5, 8 — keep but redesign.** All four are real, all four are backed by a
PRODUCTION engine or by evidence links. None survives as its own slab of page:
they become sections of the flow below, which is the difference between a
company page and an encyclopedia.

---

## The page this produces

```
Company identity
  ↓
Evidence status            withheld, or published with the score
  ↓
Evidence Coverage          ratio, and its two halves
  ↓
Confidence                 four labels, never a percentage
  ↓
Material evidence          what is recorded, and KPI alignment
  ↓
Decision risks             QDF integrity + controversies
  ↓
Ethics / governance        where supported — ethics scores, Shariah screen
  ↓
Financing readiness        where eligible
  ↓
Evidence gaps              what is missing, and what would close it
  ↓
Provenance / methodology
```

Everything above the fold answers *can I trust this*. Everything below answers
*what does it say*. That order is deliberate and matches the Intelligence
assessment flow: evidence before conclusion, on every surface.

---

## What still has to be true before the route moves

`/companies/<slug>/` stays Django until:

1. the six retained panels have API v2 resources, each applying the existing
   eligibility gate rather than a new one;
2. the React page renders them in the order above;
3. containment is asserted for a **PUBLISHED** organisation — the state no
   production row has ever been in, and therefore the state none of this has
   been tested in;
4. the authenticated four are reachable for a signed-in user.

Until then the route is not cut over. Routing a URL is a claim to own it.
