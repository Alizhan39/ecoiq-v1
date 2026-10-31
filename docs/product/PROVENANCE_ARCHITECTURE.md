# D3 — Provenance Architecture

**Audit first, schema second.** This document is the STEP 1 deliverable: what
EcoIQ already has, what D3A reuses, and what it adds. Written before any model
was defined.

D3 answers one question:

> Where did this value come from?

It does **not** answer *"should the score columns become nullable?"* — that is
D4, and nothing here touches the 39 existing score fields.

---

## 1. The headline finding

**The canonical provenance vocabulary already exists.** It shipped in D1 (#238)
as constants in `companies/evidence.py`:

```python
PROVENANCE_MEASURED  = 'MEASURED'
PROVENANCE_ESTIMATED = 'ESTIMATED'
PROVENANCE_MODELLED  = 'MODELLED'
PROVENANCE_INFERRED  = 'INFERRED'
PROVENANCE_SEEDED    = 'SEEDED'
PROVENANCE_UNKNOWN   = 'LEGACY_UNKNOWN_PROVENANCE'
```

That is five of the brief's six states plus an answer to its STEP 7 question,
already agreed and already in use by `field_provenance()`. D3A adopts it rather
than defining a parallel one.

The brief asked whether `SYNTHETIC` should be a seventh state. **The repository
already made that decision and called it `SEEDED`** — same meaning, different
name. Introducing `SYNTHETIC` alongside it would create exactly the
near-identical duplicate vocabulary the brief warns against. D3A uses `SEEDED`
and records the mapping below.

One state genuinely is missing, and D3A adds it.

---

## 2. Inventory — what exists on main (`23a495e`)

### 2.1 `companies/evidence.py` — the D1 foundation

| concept | what exists |
|---|---|
| provenance vocabulary | the six constants above |
| per-field provenance | `field_provenance(profile, field)` — a *derivation*, not a store |
| material metric registry | `MATERIAL_INPUTS` — 15 fields, weights mirroring the composite |
| coverage | `CoverageReport`, `coverage_for()` |
| eligibility | `eligibility()`, `ELIGIBILITY_{ELIGIBLE,PROVISIONAL,UNAVAILABLE}` |
| publication gate | `public_score_state()`, `STATUS_{PUBLISHED,INSUFFICIENT_EVIDENCE}` |

`field_provenance()` is the honest placeholder D3 exists to replace. Its own
docstring says so: *"There is no per-field provenance store yet, so this reports
what can be established rather than guessing… It never returns MEASURED: nothing
in the current schema can justify that claim."*

### 2.2 `evidence_memory.EvidenceMemory` — the evidence record

Already carries everything D3 would otherwise be tempted to duplicate:
`source_url`, `source_type`, `source_reference`, `confidence` (nullable, with the
explicit comment *"Never fabricated — null until a real confidence value is
known"*), `date_collected`, `verification_status`, `review_tier`, `reviewer`,
`expiry_date`, `integrity_reference`, `is_demo`.

**D3A references it by FK. It copies nothing.**

Note `review_tier` — `uploaded` → `system_checked` → `human_reviewed` →
`independently_verified` — with the comment *"never claim a tier stronger than
what actually happened to it."* That is the same discipline as the provenance
vocabulary, applied to evidence rather than to values.

### 2.3 `company_intelligence.CompanyFinancialFactSource` — **the precedent**

This is the model D3A is shaped after, because the repository already solved
this problem once for financial facts:

```python
metric   = CharField(choices=METRIC_CHOICES)          # enumerated, not free text
evidence = FK('evidence_memory.EvidenceMemory', null=True, SET_NULL)
is_derived = BooleanField(...)                        # reported vs derived
interpretation_note = TextField(...)                  # required when derived
UniqueConstraint(fields=['financial_facts', 'metric'])
@property
def value(self):                                      # RESOLVES, never copies
    return getattr(self.financial_facts, self.metric, None)
```

Every architectural question the brief raises is answered here already:
enumerated metric identity (STEP 4), evidence by reference (STEP 4), no value
copy (STEP 5), one row per parent+metric (STEP 10). D3A follows this shape at
`CompanyProfile` scope instead of `CompanyFinancialFacts` scope.

### 2.4 Other systems examined

| system | relevant to D3? |
|---|---|
| `company_intelligence.CompanyKPIEvidenceLink` | **yes** — `review_state` (`proposed`/`confirmed`/`rejected`/`needs_more_evidence`/`disputed`) is the repo's review vocabulary; `relationship` separates *does this evidence discuss the KPI* from *what does it conclude* |
| `company_intelligence/services/evidence_provenance.py` | **yes as precedent, not as storage** — classifies evidence by WHO produced it (regulatory / independent / self-reported), reusing `harvester.verification.SOURCE_TIER_BY_TYPE`. That is **evidence quality**, not value provenance — STEP 3's distinction, already implemented |
| `decision_studio` | **yes** — `DATA_AVAILABILITY_CHOICES` and `CONFIDENCE_CHOICES` (`HIGH`/`MEDIUM`/`LOW`/`INSUFFICIENT_EVIDENCE`). Already the source of the D1 taxonomy |
| `companies.CompanyScoreSnapshot` | **partly** — dated value history, but no lineage. Not a provenance store |
| `digital_twin.StewardshipKPI` | **no** — see §4 |
| `countries` macro fields | precedent only: `data_sources` free-text citation + `data_last_updated`. Honest for a country page, too weak for per-metric lineage |
| `audit`, `ingestion`, `global_research` | domain-specific; no reusable per-metric provenance |

---

## 3. Canonical vocabulary for D3A

Reused unchanged from `companies/evidence.py`, with one addition:

| state | meaning | new? |
|---|---|---|
| `MEASURED` | directly observed from defensible source data | reused |
| `ESTIMATED` | calculated estimate on disclosed assumptions | reused |
| `MODELLED` | output of an explicit model or simulation | reused |
| `INFERRED` | derived indirectly from other evidence | reused |
| `SEEDED` | synthetic development/demo data | reused (**= the brief's `SYNTHETIC`**) |
| `LEGACY_UNKNOWN_PROVENANCE` | a value exists; its lineage cannot be reconstructed | reused |
| `UNKNOWN` | **no defensible value exists at all** | **added** |

### Why `UNKNOWN` is a distinct state

`LEGACY_UNKNOWN_PROVENANCE` and `UNKNOWN` are not synonyms, and collapsing them
would undo the whole D2 programme:

- `LEGACY_UNKNOWN_PROVENANCE` — **there is a number**, and we cannot say where it
  came from. It must not be published, but it exists and may later be traced.
- `UNKNOWN` — **there is no number**. This is what D2/D2b/D2c spent three PRs
  making representable in the calculation layer.

### Mapping to the brief's names

| brief | EcoIQ | note |
|---|---|---|
| `SYNTHETIC` | `SEEDED` | same meaning; the repo's name wins |
| the other six | identical | |

---

## 4. Metric identity

The brief is right that free-form strings are fragile (`"env score"` vs
`"environmental"` vs `"environment_score"`). Three candidates were examined:

1. **`digital_twin.StewardshipKPI`** — **rejected.** Per the standing product
   decision, StewardshipKPI is the Khalifah/governance framework and must not
   become the storage table for every analytical `CompanyProfile` field. Its
   identifiers are also scoped to scenarios, not to company profiles. The brief
   said not to force this relationship, and it does not fit.

2. **A new `MetricDefinition` model** — **rejected for D3A.** A registry table
   whose only content would be the field names already declared in
   `MATERIAL_INPUTS` adds a migration, an admin surface and a join, and buys
   nothing D3A needs. It remains available if D3C finds metrics that are not
   `CompanyProfile` fields.

3. **`companies.evidence.MATERIAL_INPUTS` as the registry** — **adopted.** It
   already enumerates the 15 material fields with their composite weights, it is
   already the basis of coverage and eligibility, and it is already tested. D3A
   validates `metric_key` against it, so a typo is rejected at write time rather
   than becoming a silently orphaned row.

This follows `CompanyFinancialFactSource` exactly: an enumerated key validated
against a canonical list, not free text.

---

## 5. Value provenance vs evidence quality (STEP 3)

Kept as two independent dimensions, because they genuinely vary independently:

```
origin = MODELLED   +  evidence quality = HIGH    (a good model, well sourced)
origin = MEASURED   +  evidence quality = LOW     (a real reading, poor source)
```

- **Origin** lives on the new provenance row (`origin` field).
- **Evidence quality** is *not* duplicated. It is read through the FK from
  `EvidenceMemory` (`source_type`, `verification_status`, `review_tier`) and
  from `evidence_provenance.py`, which already classifies producers.

The only quality-ish field D3A stores locally is `source_quality`, and only as an
optional analyst override for cases with no `EvidenceMemory` row.

---

## 6. No value copy (STEP 5)

D3A stores **no copy of the metric value**. The provenance row references the
company and the metric key, and resolves the value through
`getattr(profile, metric_key)` — precisely as `CompanyFinancialFactSource.value`
already does.

**Why not an immutable observation model?** It was considered and deferred:

- `CompanyScoreSnapshot` already provides dated value history, so a second
  historical value store would be a third place a company's numbers live.
- An observation/event model is the right answer *if* EcoIQ later needs multiple
  concurrent competing observations of the same metric. Nothing needs that today.
- Deciding it now would make D3A large and hard to reverse; deciding it later
  costs one migration.

The append-only provenance history in §7 gives auditability without duplicating
values.

---

## 7. History and current-record strategy (STEP 10)

**Append-only, with exactly one current row per (company, metric).**

```
UniqueConstraint(company, metric_key, condition=Q(is_current=True))
```

A partial unique index — supported on both SQLite and PostgreSQL — so history
accumulates while the current state stays unambiguous and cheap to query.

Rejected alternative: one mutable row per (company, metric). It is simpler, but
it destroys the previous provenance on every rewrite, which is the specific thing
STEP 11 says D3 must not make impossible.

Indexes: the partial unique constraint, plus one composite index on
`(company, metric_key)` for lookups. **No index on `origin`, `review_status` or
`created_at`** — the brief says not to add unnecessary indexes, and no query
pattern justifies them yet.

---

## 8. Human review kept separate (STEP 12)

`origin`, `review_status`, `reviewed_by` and `reviewed_at` are four independent
fields. Nothing derives one from another:

- a `MEASURED` value is **not** auto-marked reviewed;
- a `MODELLED` value is **not** auto-marked untrusted.

`review_status` reuses `CompanyKPIEvidenceLink.REVIEW_STATE_CHOICES` rather than
inventing a sixth review vocabulary.

---

## 9. Confidence (STEP 13)

`confidence` is nullable and **has no default**. Unknown confidence is `NULL`,
never `50`. Where an `EvidenceMemory` is linked, its own nullable `confidence`
is the source of truth and this field stays null.

The categorical `HIGH`/`MEDIUM`/`LOW`/`INSUFFICIENT_EVIDENCE` scale from
`decision_studio` is available for a future D3D; D3A stores the numeric field
only, to avoid shipping two confidence representations at once.

---

## 10. Publication hook (STEP 14)

One helper, `is_publicly_defensible(company, metric_key)`, so no template ever
reproduces the rules. In D3A it is **advisory only** — nothing calls it from a
public path, and public eligibility is unchanged.

It rejects `SEEDED`, `LEGACY_UNKNOWN_PROVENANCE`, `UNKNOWN` and *absence of any
provenance row*. It does not encode coverage thresholds; those belong to D5.

The `SEEDED` rejection is enforced by test, not only by documentation, per the
brief's STEP 7.

---

## 11. API v2 forward compatibility (STEP 15)

The model supports the target shape without exposing it in D3A:

```json
{ "ecoiq_score": 74.2, "score_status": "PUBLISHED",
  "provenance": { "origin": "MODELLED", "confidence": "HIGH", "review_status": "confirmed" } }
```

`origin`, `confidence` and `review_status` are all first-class fields on one row
reachable by a single `(company, metric_key, is_current=True)` lookup, so a
future serializer needs a `prefetch_related`, not a schema change.

---

## 12. Writer inventory (STEP 8)

Every legitimate writer of material `CompanyProfile` metrics, with the provenance
it *should* attach. **None are wired up in D3A** — that is D3C.

| writer | class | provenance |
|---|---|---|
| `add_400_companies.py`, `seed_companies.py`, `seed_global_companies.py`, `seed_phase2_companies.py` | seed | `SEEDED` |
| `seed_score_history.py` | seed | `SEEDED` |
| `ingest_yfinance.py`, `ingest_sec_edgar.py` | ingestion | `MEASURED` (direct field) / `INFERRED` (derived) |
| `ingestion/pipeline.py` | evidence extraction | `INFERRED`, or `MEASURED` where a primary source is linked |
| `companies/scoring.py::recalculate_and_save` | derived calculation | `MODELLED` — a composite of other metrics |
| `ethics/scoring.py::compute_and_save` | derived calculation | `MODELLED` |
| `financing/matching.py`, `qdf/scoring.py`, `mizan/scoring.py` | derived calculation | `MODELLED` |
| `ml/scoring_model.py::_apply_scores` | ML | `MODELLED` |
| `ml/prediction.py::apply_predictions` | ML | `MODELLED` |
| `digital_twin` scenarios | simulation | `MODELLED` |
| Django admin | manual/analyst | `ESTIMATED` or `MEASURED`, analyst-declared |
| `backend_intelligence_engine/tasks.py` | background | inherits from the recalculation it triggers |
| rows written before D3 | historical | `LEGACY_UNKNOWN_PROVENANCE` |

**Observation:** most writers are `MODELLED`, because most EcoIQ scores are
composites of other scores. That is worth stating plainly — a composite is a
model output, not a measurement, however good its inputs.

---

## 13. Historical data (STEP 6)

No backfill in D3A. When D3B runs, the rules are:

- a value exists, lineage not reconstructible → `LEGACY_UNKNOWN_PROVENANCE`
- no value → `UNKNOWN`
- written by an identifiable seed command → `SEEDED`, **only** where the writer
  is deterministically identifiable

**Provenance is never inferred from the number itself.** 50 does not imply
unknown; 72 does not imply modelled; 0 does not imply measured. The existing
`field_provenance()` heuristic — value equals model default *and* no linked
evidence → `SEEDED` — is the single narrow exception, and it is deterministic
rather than a guess about the number's meaning.

---

## 14. What D3A does *not* touch

Score field nullability · scoring formulas · public eligibility thresholds ·
homepage · rankings UI · API v1 · API v2 output · mobile · Eco Tours · agents ·
the 39 existing score fields (no alteration, no default removal, no rename).

The migration is purely additive; rollback drops the new table.

---

## 15. Proposed sequence

| PR | scope |
|---|---|
| **D3A** | provenance schema foundation *(this PR)* |
| D3B | deterministic legacy/seed labelling — no guessing |
| D3C | trusted writer integration, transactional |
| D3D | evidence/confidence/review integration where required |
| D4A | None-safety preparation (P0 sites from `NULLABILITY_READINESS.md`) |
| D4B | nullable schema migration |
| D4C | legacy default removal |
| D5 | evidence coverage + eligibility + publication |
