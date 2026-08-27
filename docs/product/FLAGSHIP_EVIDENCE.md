# Flagship investigations — what real ingestion actually produced

Recorded 2026-08-27, against `origin/main`. Every figure below came from a real
run of the two ingestion commands, not from an estimate.

## Why this document exists

The plan was "3–5 flagship evidence-backed investigations". Running the
pipeline does not produce one, and the reason is a deliberate design rule
rather than a gap:

> the system that proposes a KPI match must never silently confirm its own
> proposal. Every mutation here requires an explicit, named human action; there
> is no code path that moves a link to `confirmed` without a reviewer.
> — `company_intelligence/services/evidence_review.py`

`kpi_candidate_matching` emits `review_state='proposed'` and nothing else, and
`kpi_engine.derive_status_from_evidence` counts only `confirmed` links. So
ingestion produces **real evidence that correctly counts toward nothing** until
a named reviewer works the queue at `/companies/review/`.

That is the system working. It also means a flagship investigation is finished
by a person, not by a command, and this document records the state ingestion
can reach on its own.

## What was ingested

Two commands, both idempotent, both against real sources:

```
python manage.py ingest_real_company_evidence --slug <slug>      # SEC EDGAR XBRL
python manage.py ingest_real_sustainability_evidence             # official documents
```

### SEC EDGAR — financial facts

| Organisation | Revenue (real, XBRL) | Shariah screen | Completeness |
|---|---|---|---|
| Apple | $416,161,000,000 | insufficient_data | 50.0% |
| Tesla | $94,827,000,000 | conditional | 66.7% |
| ExxonMobil | $332,238,000,000 | conditional | 66.7% |
| Coca-Cola | $47,941,000,000 | conditional | 66.7% |
| National Grid | — | not run | — |

`market_cap_usd` and `interest_bearing_securities_usd` are **not obtainable**
from SEC EDGAR XBRL and are left `NULL` for every organisation above. They are
not zero, and the shortfall is why Apple's screen is `insufficient_data` rather
than a pass — the completeness figure is doing real work.

National Grid has no SEC CIK mapped. The command reported
*"real ingestion is unavailable for this company; nothing was fetched or
fabricated"* and moved on.

### Official documents — principle evidence

| Organisation | Document | Proposed links |
|---|---|---|
| Walmart | corporate.walmart.com/purpose/sustainability | 9 |
| ExxonMobil | corporate.exxonmobil.com/publications/sustainability | 4 |
| Microsoft | microsoft.com/…/sustainability | 0 |
| Coca-Cola | coca-colacompany.com/about-us/environment | 0 |
| Apple | apple.com/…/Apple_Environmental_Progress_Report_2024.pdf | fetch refused |
| National Grid | — | source inactive |

Thirteen real proposed links across two organisations, spread over seven
principles. Every one of them is `confirmed=0`, counts toward nothing, and
leaves its principle reading `not_assessed`.

## The three honest failures

None of these is worked around, and each is worth keeping visible.

**Apple — 30 MB against a 5 MB cap.** The environmental report is real and
reachable; `backend_intelligence_engine/services/http_client.py` refuses it
because the whole body is buffered in memory and the cap exists to bound that.
It refuses rather than truncating, on the stated grounds that *"half a document
silently becoming evidence is worse than no document"*, which is the right call.
Raising `MAX_RESPONSE_BYTES` globally would let every fetch buffer 30 MB+ on a
512 MB instance with four threads, so it should not be raised as a side effect
of wanting one document. A per-call override for the staff-triggered,
low-concurrency document path is the change worth considering, and it is a
change to a memory-exhaustion control, so it wants its own review.

**Tesla — HTTP 403.** An Akamai/WAF restriction on tesla.com, documented in
`ingest_real_sustainability_evidence`. Not bypassed. Tesla's honest state is
real SEC financial evidence and no narrative stewardship evidence.

**National Grid — no mapped identifier.** A non-US filer with no SEC CIK. Both
commands declined rather than guessing.

## What a reviewer does next

The queue is built and staff-gated: `/companies/review/`, with detail, explain
and bulk actions in `company_intelligence/review_views.py`. Verified end to end
against the ingested data — a proposed link on Walmart's principle #103 moved
from `not_assessed` to `support` on `confirm_supports`, writing one immutable
`EvidenceReviewAction` naming the reviewer. Nothing else changed, and the
proposal's history was preserved rather than overwritten.

Until that review happens, the matrix at
`/api/v2/companies/<slug>/principles/` reports these organisations as having
evidence on file and no assessed principles. Both halves of that are true, and
showing them together is the point.
