# D4 — Nullable Schema Plan

Companion to [`NULLABILITY_READINESS.md`](NULLABILITY_READINESS.md), which is the
raw survey. This document prioritises it and proposes a migration sequence.

**Nothing here is implemented.** D4 begins only when D3 provenance is in place
and the P0 sites below are None-safe.

---

## The rule this plan exists to enforce

> **The migration that makes a column nullable must not be the migration that
> discovers what breaks.**

D2/D2b/D2c made the calculation layer *produce* `None`. D4 makes the database
*store* it. Between those two, 167 sites read those columns with operations that
assume a number — and they are invisible to the fallback sweeps, because they
fabricate nothing. `round(profile.public_benefit_score, 1)` is honest code that
raises `TypeError` the instant the column is nullable.

---

## Priority tiers

| tier | meaning | sites | modules |
|---|---|---|---|
| **P0** | public / runtime crash — a 500 on a page a visitor can reach | **70** | 10 |
| **P1** | background jobs, API, ML pipelines — silent failure or a broken response | 35 | 13 |
| **P2** | internal, admin, services not on a public path | 47 | 23 |
| **P3** | seed and management commands, dev tooling | 15 | 5 |

### P0 — must be fixed *before* the nullable migration

| sites | module |
|---|---|
| 17 | `league/views.py` |
| 13 | `companies/ai_helpers.py` |
| 10 | `companies/views.py` |
| 10 | `intelligence/views.py` |
| 9 | `companies/investment_report.py` |
| 5 | `countries/views.py` |
| 2 | `companies/embed_views.py` |
| 2 | `league/pdf_report.py` |
| 1 | `core/views.py` |
| 1 | `harvester/views.py` |

**The D1.5 evidence gate does not protect these.** That gate covers organisations
with *no* evidence, returning `detail_evidence_pending.html` before the page
body renders. D4 introduces something different: organisations with **partial**
evidence, which render the full page and hit every one of these expressions.

`companies/views.py:636-641` is the canonical example — `radar_scores` calls
`round()` on six pillar fields with no guard. Six nullable columns, one 500.

### P1 — fix in the same PR or immediately after

`ml/features.py` (11) is the exception: its 11 sites are None-safe **by
construction** and must not be "fixed". `_safe_float` imputes 50.0 to satisfy a
committed `GradientBoostingRegressor` whose scaler was fitted on that imputation
— see the note at the top of that module. Changing it requires retraining.

That leaves ~24 genuine P1 sites across `intelligence/compute.py`,
`ml/finance/islamic_finance_fit.py`, `qdf/api_views.py`, `transition/engine.py`
and others.

### P2 / P3 — after the migration

P3 (seed and ingest commands) should **skip unscored rows** rather than gain
None-guards. A seeder has no business inventing a value for a company with no
score — the same rule the rest of the programme follows.

---

## Proposed sequence

### D4A — None-safety preparation *(no schema change)*

Fix all 70 P0 sites and the ~24 genuine P1 sites. Purely defensive: every change
is a guard, no behaviour changes while the columns remain NOT NULL, so the PR is
verifiable against the current data and reversible without consequence.

Add a repo guard test in the style of `core/tests_no_hardcoded_secrets.py`,
asserting that no *new* unguarded numeric operation on a score field appears on a
public path. Without it, D4A's work erodes.

### D4B — nullable schema migration

One migration, covering **both**:

- the `CompanyProfile` score columns, and
- the `CompanyScoreSnapshot` mirror columns.

They must move together. `CompanyScoreSnapshot.create_from_profile()` copies
profile values verbatim into a table whose columns are also NOT NULL — so
nullable profile columns alone would make every background refresh raise
`IntegrityError`. That model fabricates nothing, which is exactly why it does not
appear in the readiness survey, and exactly why it is easy to miss.

Remove `default=50.0` in the same operation. A nullable column that still
defaults to 50 will keep acquiring 50s from every writer that omits the field.

### D4C — legacy default removal and backfill

Only where **D3 provenance** shows the stored value was never evidenced.

**Bulk `50 → NULL` remains forbidden.** That instruction has stood since the P0
brief and D4 does not relax it: a company genuinely measured at 50 is
indistinguishable from a seeded 50 by value alone, which is the entire reason
provenance exists. D3B's deterministic labelling is the prerequisite, and only
rows labelled `SEEDED` are candidates.

---

## Verification for D4B

The forward/backward/forward cycle run for D3A applies with one addition: a
nullable migration has a **data** dimension a `CreateModel` does not.

1. `migrate` forward on a copy of production data.
2. Assert row counts and a checksum of the score columns are unchanged — the
   migration must alter nullability, not values.
3. `migrate` backward. This is the one that can fail: reverting NULL → NOT NULL
   requires every NULL to have gone. If D4C has run, **the backward migration is
   no longer safely reversible**, and that must be stated in the PR rather than
   discovered during an incident.
4. Exercise the P0 pages against data containing real NULLs.

---

## Dependency order

```
D3A  provenance foundation          ← this PR
D3B  deterministic labelling
D3C  writer integration
D3D  evidence / confidence / review
D4A  None-safety (P0 + P1)          ← the gate
D4B  nullable migration
D4C  legacy defaults + backfill
D5   coverage, eligibility, publication
```

D4A is the gate. D4B before it converts a data-integrity improvement into a
public outage.
