# Calculation Context Provenance

**Architecture note. Nothing here is implemented, and this PR deliberately
changes no schema.**

Raised by #253 (Mizan lineage) and confirmed by #254 (ML and greenwashing
lineage). Both PRs hit the same wall from different directions.

---

## The problem

`CompanyMetricProvenance` can express one kind of dependency: *this derived
number was computed from those provenance rows*. That covers most of what the
EcoIQ calculators consume.

It does not cover everything. Several deterministic calculators read values
that materially change their output but are not metrics and therefore leave no
row to point at:

| input | read by | effect |
|---|---|---|
| `pollution_level` | Mizan, greenwashing, responsible finance | harm-reduction dimension; fossil-fuel exposure proxy; a penalty of up to −30 |
| `is_verified` | Mizan, greenwashing | evidence-confidence dimension: 92 vs 55/40/30 |
| `status` | Mizan, greenwashing | evidence-confidence dimension |
| `ai_summary` | Mizan | placeholder-marker probe → evidence confidence 40 |
| `ScoreHistory` rows | `ml.predicted_12m` | the entire OLS trend — the primary path |
| `DataIngestionLog` signals | `ml.predicted_12m` | ±10 points of delta on the fallback path |
| model artefact + scaler | `ml.score` | the function itself |
| feature-set definition and order | `ml.score` | what each column means |

A lineage row that lists only the metric inputs, for a calculation that also
consumed the things above, is not false in what it says. It is incomplete in a
way the reader cannot detect — which for an evidence-integrity system is the
more dangerous failure.

---

## Classification of the four Mizan context inputs

The brief asked for each to be classified rather than blanket-registered. The
classification matters, because three of the four turn out not to be metrics at
all.

### `pollution_level` — **A. MATERIAL METRIC**

Genuine primary evidence about the company: an assessed environmental
classification, of exactly the same epistemic kind as the 16 registered
material scores. It feeds a *substantive* dimension, not a meta one.

It is not registered today for one structural reason: it is a **categorical
enum** (`low` / `medium` / `high` / `severe`) and every registered metric is a
0–100 float. `CompanyMetricProvenance` itself is indifferent — it stores
origin, methodology and lineage, and `recorded_value` is the only numeric part.

**Recommendation:** register it, once the registry can describe a non-numeric
material metric. This is the one of the four that genuinely belongs in the
metric graph, and it is also the one whose absence causes real harm today: an
unknown pollution level has twice been found silently substituted with
`'medium'` (fixed in greenwashing at #244, and in
`ml/responsible_finance.py` at #254).

### `is_verified` — **C. GOVERNANCE / REVIEW STATE**

Not a fact about the company. A fact about EcoIQ's relationship to the
company's data — the same category as `review_status` and `reviewed_by`, which
already live *on* the provenance row rather than being metrics pointed at by
one.

### `status` — **C. GOVERNANCE / REVIEW STATE**, bordering on **F**

A publication-lifecycle state (`public`, `draft`, …). It says where the record
sits in EcoIQ's workflow. That a publication state currently moves an
assessment score at all is questionable on its own terms; it survives only
because it is used as a coarse proxy for data quality.

### `ai_summary` — **E. UNSTRUCTURED INPUT**

Free text, and not used as text: Mizan lowercases it and probes for
placeholder markers. The real input is a boolean — *is this record
machine-generated filler?* — extracted from prose because nothing else records
it.

---

## The finding that matters

**Three of the four converge on a single dimension: evidence confidence.**

`is_verified`, `status` and `ai_summary` do not feed Mizan's harm, benefit,
jobs, transparency or stewardship dimensions. They feed exactly one term, whose
job is to express *how much the data underneath should be trusted*.

That is what the provenance system is for.

Evidence confidence is currently computed from three weak proxies —
a verification flag, a workflow state, and a substring probe on generated prose
— because when that code was written there was no better source. There now is
one. A company whose material inputs are all `MEASURED` with confirmed review
is genuinely high-confidence; one whose inputs are `SEEDED` or
`LEGACY_UNKNOWN_PROVENANCE` is not, regardless of what its `status` field says.

**So the recommendation is not to register these three as metrics.** It is to
*delete the need for them*, by deriving evidence confidence from the provenance
origins of the inputs actually consumed. That would:

- remove three unrepresented inputs from the graph rather than modelling them;
- make evidence confidence honest instead of proxied;
- make the lineage complete, because the inputs to evidence confidence would be
  the same provenance rows already attached.

`ai_summary` disappears entirely under this change: "the summary is placeholder
text" is a much worse signal for "the data is unreliable" than "the data is
labelled `SEEDED`", which is the same fact stated directly.

This is a **D5-or-later** change. It alters scores, so it needs its own
phase, its own before/after measurement, and its own approval. It is recorded
here so the option is not lost.

---

## The remaining categories

`pollution_level` (category A) is the only one that should become a metric.

The ML context inputs are a different problem again, and are **D. CALCULATION
CONTEXT**:

- **Model artefact + scaler.** Two joblib files at fixed paths, overwritten in
  place by every retrain. #254 addresses this with a content digest of the
  artefact bytes, carried in `calculation_version` — the smallest stable,
  code-owned identifier available without new schema. It is sufficient to make
  "this prediction came from a different model" *detectable*; it is not
  sufficient to make the model *retrievable*, because the previous artefact is
  gone.
- **Feature-set definition and order.** Code-owned and versioned by hand in
  #254. A reordering that is not accompanied by a version bump would be
  invisible.
- **`ScoreHistory` / `DataIngestionLog`.** Real inputs to `ml.predicted_12m`,
  and both are records rather than metrics. `ml.predicted_12m`'s primary path
  consumes *only* these, which is why #254 records its lineage as explicitly
  partial rather than pretending the metric inputs are the whole story.

---

## What is deliberately not proposed

**An opaque context blob.** A `JSONField` of "everything else the calculator
read" would make the incompleteness invisible again — worse than the current
state, where the gap is at least documented and testable. If context needs
representing, it should be represented in a typed, queryable way, decided
deliberately.

**Registering `is_verified` / `status` / `ai_summary` as metrics.** They are not
metrics. Modelling governance state as evidence would corrupt the vocabulary
that makes `is_publicly_defensible()` meaningful.

---

## The interim position, and its limits

Where a calculation is **ephemeral**, the identity rule established in #253
includes the output in the row's identity. So when an unrepresented context
input changes, the number changes, and a new provenance event is created rather
than the change being silently deduplicated.

**This is real but partial.** It guarantees *an event exists*. It does not
record *which* context input moved, or *what it moved from*. A reader can see
that two events with identical lineage produced different numbers, and can
conclude that something unrepresented changed — but not what.

That is the honest description of the current state: **change detection, not
explainability.**

It does not apply to persisted metrics at all, whose identity deliberately
excludes the output (see #253 and `DERIVED_METRIC_PROVENANCE.md`). For those,
a context change with unchanged lineage is currently invisible. `ml.score` and
`ml.predicted_12m` are both in this category, which is why #254 puts the model
digest into `calculation_version` — it converts the most important context
change, a retrain, into a lineage-visible one.

---

## Tracking

| item | state |
|---|---|
| `pollution_level` → material metric (categorical) | **open** — needs registry support for non-numeric metrics |
| evidence confidence derived from provenance origins | **open** — D5 or later; changes scores |
| `is_verified` / `status` / `ai_summary` as calculators inputs | **open** — resolved by the item above, not separately |
| ML model artefact versioning | **partial** — content digest in #254; artefacts still overwritten in place |
| feature-set version | **partial** — hand-maintained constant in #254 |
| `ScoreHistory` / `DataIngestionLog` lineage | **open** — records, not metrics; no representation today |
| ephemeral output-in-identity workaround | **in place** — #253, #254; change detection only |
| typed context representation | **not designed** — do not build a blob |
