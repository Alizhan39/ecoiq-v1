# D3C — Writer Provenance Integration

**Plan only. Nothing here is implemented.** Refined while building D3B, which
surfaced two things the D3A writer table did not know.

D3B recorded the *first known* provenance for values that predate D3. D3C makes
every *new* metric write record its own provenance, atomically, so the estate
stops accumulating rows that need a legacy label.

---

## What D3B changed about this plan

**1. Most writes are `MODELLED`, and that is not a detail.** Most EcoIQ metric
writes are composites of other metrics, not observations. A composite is a model
output however good its inputs, so the honest labelling of a recalculation run is
`MODELLED` — which in turn means `MODELLED` will be the most common origin in the
estate for some time. Worth saying out loud, because a system whose commonest
provenance is "we computed it from other things we computed" is not one whose
scores are ready for publication on provenance alone.

**2. Provenance origin must be decided per-FIELD, not per-writer-run.** A single
`recalculate_and_save()` call writes six pillar scores plus a composite. The
pillars are `MODELLED` from their sub-scores; the composite is `MODELLED` from
the pillars. Same call, same origin here — but `ingestion/pipeline.py` writes
some fields directly from a filing (`MEASURED`) and derives others in the same
transaction (`INFERRED`). A writer-level default would mislabel half of them.

---

## The invariant D3C exists to protect

> The metric write and the provenance write must not drift.

A value saved without provenance is indistinguishable from a legacy value, and
would be re-labelled `LEGACY_UNKNOWN_PROVENANCE` by the next backfill —
laundering a known origin into an unknown one. A provenance row written without
the value is worse: it asserts an origin for a number that was never stored.

Both must be in the same `transaction.atomic()` block. Where a writer already
has a transactional service layer, D3C extends it rather than adding a second.

---

## Priority tiers

### P0 — trusted evidence ingestion

| writer | metrics | origin | evidence link | review state | transaction |
|---|---|---|---|---|---|
| `ingestion/pipeline.py` | whichever material fields the extraction populates | `MEASURED` for a field taken directly from a source; `INFERRED` where derived in the same pass | **required** — FK to the `EvidenceMemory` the extraction created | `proposed` | extend the existing per-company block around the profile save |
| `ingest_sec_edgar.py` | `transparency_anti_corruption_score` and any other directly-filled field | `MEASURED` | required | `proposed` | per company |
| `ingest_yfinance.py` | `ecoiq_total_score` deltas, financial-derived fields | `INFERRED` | required | `proposed` | per company |

**Why P0:** these are the only writers that can ever produce `MEASURED`, and
`MEASURED` is the only origin that can make a metric publicly defensible. Until
one of them records provenance, `is_publicly_defensible()` returns `False` for
every metric in the estate — which is correct today and is also the reason D5
has nothing to publish yet.

**Note:** ingestion must *not* auto-confirm review. The repository already made
this decision for KPI links — a deterministic matcher may **propose**, never
**confirm** — and provenance follows the same rule.

### P0 — human analyst / manual approval

| writer | metrics | origin | evidence link | review state | transaction |
|---|---|---|---|---|---|
| Django admin (`CompanyProfileAdmin`) | any material field edited | analyst-declared: `MEASURED` or `ESTIMATED` | optional | `confirmed`, with `reviewed_by` = the editing user | admin `save_model` |

The origin must be **chosen by the analyst**, not defaulted. A dropdown on the
admin form, because a silent default here would put the strongest claim in the
vocabulary on every hand edit.

This is the other P0 because it is the only path that can legitimately set
`review_status='confirmed'` — no automated writer may.

### P1 — Digital Twin / model outputs

| writer | metrics | origin | evidence link | review state | transaction |
|---|---|---|---|---|---|
| `digital_twin` scenarios | scenario-projected metrics | `MODELLED` | none | `proposed` | per scenario run |

`calculation_version` and `methodology` are **required** here, not optional: a
modelled value is only as attributable as the model version behind it.

### P1 — ML analytical outputs

| writer | metrics | origin | evidence link | review state | transaction |
|---|---|---|---|---|---|
| `ml/scoring_model.py::_apply_scores` | `ml_score`, `ml_score_confidence` | `MODELLED` | none | `proposed` | bulk, per batch |
| `ml/prediction.py::apply_predictions` | `ml_predicted_score_12m` | `MODELLED` | none | `proposed` | bulk, per batch |

**Neither writes a `MATERIAL_INPUTS` metric today**, so both are currently out of
scope for `CompanyMetricProvenance` as D3A defines it. Recording them needs
either a wider metric registry or a decision that ML outputs are not "material
metrics". **That decision belongs to whoever scopes D3C**, and this document
deliberately does not pre-empt it — but it is the reason ML sits at P1 rather
than P0 despite being an obvious provenance candidate.

`calculation_version` should carry the model artefact hash, so a prediction made
before a retrain is distinguishable from one made after.

### P1 — background recalculation

| writer | metrics | origin | evidence link | review state | transaction |
|---|---|---|---|---|---|
| `companies/scoring.py::recalculate_and_save` | the six pillars + composite | `MODELLED` | none | `proposed` | already atomic per profile — extend it |
| `ethics/scoring.py::compute_and_save` | NEI/TSS/RVI *(not material metrics today)* | `MODELLED` | none | `proposed` | existing `update_or_create` block |
| `financing/matching.py`, `qdf/scoring.py`, `mizan/scoring.py` | derived assessments *(not material metrics today)* | `MODELLED` | none | `proposed` | existing service block |
| `backend_intelligence_engine/tasks.py` | triggers the above | **inherits** — must not record its own | — | — | inside the triggered write |

The last row is the subtle one. A background task that recorded provenance
*separately* from the recalculation it triggered would produce two rows for one
logical write, and they could disagree. The task records nothing; the
recalculation it calls does.

### P2 — imports

| writer | metrics | origin | evidence link | review state | transaction |
|---|---|---|---|---|---|
| CSV / dataset import paths | as imported | `MEASURED` if the source is primary, else `INFERRED` | required where a source document exists | `proposed` | per import batch |

### P3 — seed / demo commands

| writer | metrics | origin | evidence link | review state | transaction |
|---|---|---|---|---|---|
| `add_400_companies.py`, `seed_companies.py`, `seed_global_companies.py`, `seed_phase2_companies.py`, `seed_score_history.py` | all material metrics they write | `SEEDED` | none | `proposed` | per company |

Lowest priority to *implement*, but **highest value per line of code**, and the
D3B experience is why: on the current dataset **zero** profiles carried provable
seed lineage, so 100% of the estate had to be labelled
`LEGACY_UNKNOWN_PROVENANCE`. Had the seed commands recorded `SEEDED` at write
time, that would have been knowable exactly rather than unknowable entirely.

Every future seed run should make its own provenance a fact rather than a
forensic exercise.

---

## Re-ranked after D3C-2 (registry landed)

The registry changed the ordering, because it changed what is *possible*.

| PR | scope | status |
|---|---|---|
| D3C-1 | seed command provenance | **done** (#247) |
| D3C-2 | derived metric registry | **done** (this PR) |
| **D3C-3** | **derived writer integration** | **next — recommended** |
| D3C-4 | trusted evidence ingestion | after D3C-3 |
| D3C-5 | human analyst workflow | last |

**Why derived writers now come before ingestion.** Before the registry, only the
16 material metrics could be recorded, so ingestion was the only writer that
could do anything at all. That is no longer true: sixteen derived metrics are
now registerable, `record_derived()` exists, and the calculators that produce
them (`companies.scoring`, `ethics.scoring`, `mizan`, `qdf`, `financing`, `ml`)
already know which inputs they consumed — the D2 re-normalisation work made that
knowable.

Ingestion also has a dependency the derived writers do not: the D3C-1 finding
that an assessed score written by ingestion should be `INFERRED`, not
`MEASURED`. Settling that is a semantics decision (see
`DERIVED_METRIC_REGISTRY.md` §8), and it is better made deliberately than under
the pressure of shipping an ingestion PR.

### D3C-3 shape

Start with **one** calculator — `companies.scoring.recalculate_and_save` — because
it produces the composite every other surface reads, it already runs inside a
transaction, and its inputs are exactly the 16 material metrics the registry
already covers. Extend to ethics, financing, QDF, Mizan and ML once the pattern
is proven on one.

The invariant is D3C-1's, unchanged: the value write and the provenance write
are one atomic operation, and `record_derived()` must be called inside the
caller's block.

---

## Recommended first D3C PR (superseded — kept for the record)

**D3C-1 — seed command provenance.**

- Smallest blast radius: seed commands do not run in production request paths.
- Immediately testable: run the seeder on a disposable database and assert every
  written metric has `SEEDED` provenance, and that none of it is publicly
  defensible.
- Establishes the `transaction.atomic()` pattern that P0 ingestion will copy,
  where getting it wrong on a live ingestion path would be far more expensive.
- Directly closes the gap D3B exposed.

Explicitly **not** first: admin integration, because it needs a UI decision (how
the analyst declares origin) that should not be made in the same PR that
establishes the write pattern.

---

## Open question for whoever scopes D3C

`MATERIAL_INPUTS` covers 16 metrics. Several writers above produce values that
are **not** in it — `ecoiq_total_score`, `ml_score`, `ml_predicted_score_12m`,
NEI/TSS/RVI, QDF and Mizan composites.

Three options, in the order they should be considered:

1. **Leave them out.** Provenance covers material inputs; composites inherit
   their defensibility from their inputs. Simplest, and arguably correct — a
   composite's provenance is a function of its parts.
2. **Widen the registry** to a `MATERIAL_INPUTS + DERIVED_METRICS` union. More
   complete, more rows, and raises the question of what a composite's
   `evidence` FK would even point at.
3. **A separate composite-provenance concept.** Most work; only worth it if D5
   needs to publish composites with their own independent lineage.

D3A deliberately did not decide this, and neither does D3B. It should be decided
**before** D3C-2, because the answer changes which writers D3C touches at all.
