# Material vs Derived Metric Provenance

**Architecture decision. Not implemented in D3C-1** — this document exists so
that D3C-2 has a decision to build against rather than one to make under
deadline.

Resolves the question D3A and D3B both deliberately left open: whether
provenance covers derived composites, and how.

---

## 1. The distinction

```
MATERIAL / SOURCE METRIC          →  calculation  →   DERIVED METRIC
emissions, energy, water,                             EcoIQ composite, NEI, TSS,
renewable share, pollution                            RVI, Mizan, QDF, ML scores,
observations, transparency                            responsible-finance score,
evidence, verified operational                        greenwashing assessment,
inputs                                                readiness composites
```

A material metric is **observed**. A derived metric is **computed**. The
provenance question is different for each, and answering it with one vocabulary
is what produced the current confusion.

### The complication EcoIQ actually has

There are **three** layers in the schema, not two, and provenance is currently
attached to the middle one:

| layer | schema | in `MATERIAL_INPUTS`? | populated |
|---|---|---|---|
| **1. Source** | `estimated_emissions` (tCO₂e), `renewable_energy_share`, `emissions_reduction_target`, `annual_revenue`, `profit`, `taxes_paid`, `community_investment`, `modernization_investment`, `state_owned_percentage` | **no** | **0 / 186** |
| **2. Assessed score** | the 16 `_score` fields — `water_impact_score`, `waste_management_score`, `anti_corruption_score`… | **yes, all 16** | **186 / 186** |
| **3. Derived** | EcoIQ composite, NEI, TSS, RVI, Mizan, QDF, ML, responsible-finance, greenwashing | **no** | populated |

Layer 2 is **not** a source metric. `water_impact_score` is declared as
*"0-100: water stewardship quality"* — a judgment about water, not water.

Measured on the current dataset: **every quantity that could be observed is
empty; every score that interprets those quantities is full.** The estate holds
a complete set of judgments and zero observations.

One detail worth noting: the layer-1 fields are all `null=True` with **no**
fabricated default. Only the score layer carried `default=50.0`. The schema was
already honest about quantities; the fabrication was confined to judgments.

---

## 2. Why composite and model scores are `MODELLED`

Because that is what they are. A composite is a model output however good its
inputs, and calling it `MEASURED` would claim an observation that never happened.

This has a consequence worth stating plainly rather than discovering at D5:

> **Under the current registry, `MEASURED` may be unreachable in principle.**

Nothing measures a 0–100 stewardship quality. An assessed score computed from a
real CO₂ figure is honestly `INFERRED`; one from analyst judgment on disclosed
assumptions is `ESTIMATED`. `MEASURED` belongs to layer 1 — which is empty.

So the honest origins available today are:

| layer | honest origins |
|---|---|
| 1. Source | `MEASURED` (a real reading), `ESTIMATED` (a disclosed estimate) |
| 2. Assessed score | `INFERRED` (derived from layer-1 or from evidence), `ESTIMATED` (analyst judgment), `SEEDED` (synthetic) |
| 3. Derived | `MODELLED`, always |

**This corrects a claim made in the D3B report**, which said ingestion is *"the
only writer that can produce MEASURED."* Ingestion writing into layer 2 should
produce `INFERRED`, not `MEASURED`. If D5 requires `MEASURED` to publish, nothing
in the current registry can ever qualify — not because evidence is missing, but
because the registry points at the wrong layer.

---

## 3. How derived values reference input lineage

A derived metric's defensibility is **a function of its inputs**, so it should
not carry an independent evidence claim.

The proposed shape, for D3C-2 to build:

```
CompanyMetricProvenance (derived row)
    origin              = MODELLED
    methodology         = 'EcoIQ six-pillar weighted composite'
    calculation_version = 'scoring.v1'
    inputs              = M2M -> the material provenance rows it consumed
```

An `inputs` many-to-many to `CompanyMetricProvenance` — not to raw field names —
so a derived row points at *the specific provenance state* its calculation read.
Recalculating after an input's provenance changes produces a new derived row
pointing at the new input rows, and the old pairing stays intact as history.

The alternative — recomputing lineage on demand by re-reading current input
provenance — was rejected: it would answer *"what would this score's lineage be
if computed now?"*, not *"what was it when computed?"*, and only the second is an
audit trail.

**Deliberately not proposed:** an `evidence` FK on derived rows. A composite has
no document behind it. Its evidence is its inputs' evidence, reachable through
`inputs`.

---

## 4. Is a stable Metric Registry needed?

**Yes — for layer 3, and not before it.**

`MATERIAL_INPUTS` works for layer 2: 16 names, already carrying composite
weights, already backing coverage and eligibility, already tested. Replacing it
would add a table and a join to restate names the code already has.

It cannot work for layer 3, for a structural reason: `CompanyMetricProvenance`
validates `metric_key` against `MATERIAL_INPUTS` **and** resolves `value` via
`getattr(profile, metric_key)`. Derived metrics fail both — `NEI` lives on
`CompanyEthicsProfile`, `mizan_score` on a `MizanResult` dataclass that is not
persisted per-metric at all, `ml_score` on `league.Company`. A registry entry
therefore needs to carry **where the value lives**, not just its name:

```
MetricDefinition
    key             'nei'
    layer           MATERIAL | DERIVED
    model           'ethics.CompanyEthicsProfile'
    field           'net_ethical_impact'
    accessor        how to reach it from a CompanyProfile
```

That is a real piece of work, and it is the reason D3C-2 should be the registry
rather than ingestion: **ingestion integration is blocked behind it for any
metric that is not one of the 16.**

---

## 5. `calculation_version`

Already on the D3A model. The convention:

| producer | value |
|---|---|
| deterministic formula (`companies/scoring.py`, ethics, Mizan, QDF) | `'<module>.v<N>'`, bumped when the formula changes — e.g. `'scoring.v1'` |
| ML model | the artefact hash, so a prediction made before a retrain is distinguishable from one after |
| Digital Twin | scenario id + engine version |

For a `MODELLED` row, `calculation_version` and `methodology` should be
**required**, not optional: a modelled value is only as attributable as the
model version behind it. D3A leaves both `blank=True` because it wires up no
writers; D3C-2 should enforce them at the service layer for `MODELLED`.

---

## 6. One derived metric, many material inputs

The EcoIQ composite reads six pillars, each reading three to four of the 16
material metrics. The `inputs` M2M holds the material provenance rows the
calculation actually consumed — **the ones it read**, not the ones the formula
mentions. A recalculation that skipped an unknown input did not consume it, and
recording it would overstate the lineage.

This is where the D2 work pays off: `_weighted()` and `mean_of_known()` already
know which inputs they used, because they had to in order to re-normalise.

---

## 7. Recalculation and history

Recalculation follows the D3A rule: **supersede, never mutate.**

Previous derived row → `is_current=False`. New row → `is_current=True`, with its
own `calculation_version` and its own `inputs`. The partial unique constraint
keeps exactly one current row per (company, metric).

The churn rule proven in D3C-1 applies: if origin, writer **and**
`calculation_version` are all unchanged, no new row. A recalculation that
produced the same result by the same formula is not a new provenance event.
A version bump always is, even when the number does not move — *how* it was
produced changed.

---

## 8. How D5 uses provenance and coverage together

Two independent questions, and D5 needs both:

| question | answered by |
|---|---|
| *Is this value's origin defensible?* | `is_publicly_defensible()` — provenance |
| *How much of the composite is backed?* | `coverage_for()` — evidence coverage |

A composite could have excellent provenance on three of sixteen inputs. High
provenance quality, low coverage — and it must not publish. Conversely, full
coverage of `SEEDED` inputs is total coverage of nothing.

The proposed composition, for D5 to decide the thresholds of:

```
publishable(composite) ⟺
    every material input consumed has defensible provenance
    AND coverage exceeds the D5 threshold
    AND the derived row's own origin is MODELLED with a recorded
        methodology and calculation_version
```

D3 does not set the threshold, and D3A deliberately kept it out of
`is_publicly_defensible()` so that D5 makes it visibly rather than inheriting a
guess.

---

## 9. Sequencing implication

The layer-1 emptiness is the load-bearing fact. Pointing provenance at layer 2
and integrating ingestion still leaves EcoIQ with judgments whose strongest
honest origin is `INFERRED` — defensible, but not measurement.

If the product goal is scores backed by observation, **populating layer 1 is a
prerequisite that no amount of provenance infrastructure substitutes for.** That
is a product decision, not an engineering one, and this document does not make
it.
