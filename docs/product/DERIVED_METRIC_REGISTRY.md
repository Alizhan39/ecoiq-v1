# Derived Metric Registry

**D3C-2 deliverable.** The inventory behind `companies/metric_registry.py`, plus
the decisions that shaped it.

Companion to [`DERIVED_METRIC_PROVENANCE.md`](DERIVED_METRIC_PROVENANCE.md),
which sets out *why* material and derived metrics differ. This document records
*what actually exists* and *where each value lives*.

---

## 1. The problem this solves

D3C-1 found the blocker. `CompanyMetricProvenance` validated `metric_key`
against `MATERIAL_INPUTS` **and** resolved the value with
`getattr(profile, metric_key)`. Both assumptions fail for derived metrics:

| metric | actually lives on | `getattr(profile, key)` |
|---|---|---|
| `ethics.nei` | `CompanyEthicsProfile` (OneToOne) | fails |
| `ml.score` | `league.Company` | fails |
| `qdf.decision_integrity` | `DecisionAssessment` (ForeignKey, many) | fails |
| `mizan.score` | a dataclass that is never persisted | fails |

So a registry entry has to carry **where the value lives**, not just its name.

---

## 2. Inventory

**32 metrics: 16 material, 16 derived, of which 3 are ephemeral.**

### Material (16) — unchanged

The `MATERIAL_INPUTS` field names, registered as-is. Keys remain bare
`CompanyProfile` field names (`water_impact_score`, not `material.water_impact`).

**Why the asymmetry is deliberate:** renaming them would invalidate every
provenance row D3B and D3C-1 already wrote — 2976 legacy rows plus every seed
row — for cosmetic consistency. The registry tolerates two key styles; the data
does not tolerate a rename.

### Derived (16)

| key | value location | ephemeral |
|---|---|---|
| `company.ecoiq_total` | `companies.CompanyProfile.ecoiq_total_score` | no |
| `company.public_benefit` | `companies.CompanyProfile.public_benefit_score` | no |
| `company.environmental` | `companies.CompanyProfile.environmental_responsibility_score` | no |
| `company.modernization` | `companies.CompanyProfile.modernization_score` | no |
| `company.transparency_governance` | `companies.CompanyProfile.transparency_anti_corruption_score` | no |
| `company.harm_penalty` | `companies.CompanyProfile.harm_penalty` | no |
| `ethics.nei` | `ethics.CompanyEthicsProfile.net_ethical_impact` | no |
| `ethics.tss` | `ethics.CompanyEthicsProfile.transition_stewardship` | no |
| `ethics.rvi` | `ethics.CompanyEthicsProfile.regenerative_value` | no |
| `financing.readiness` | `financing.CompanyFinancingProfile.financing_readiness` | no |
| `qdf.decision_integrity` | `qdf.DecisionAssessment.decision_integrity_score` (latest) | no |
| `ml.score` | `league.Company.ml_score` | no |
| `ml.predicted_12m` | `league.Company.ml_predicted_score_12m` | no |
| **`mizan.score`** | `mizan.scoring.MizanResult` dataclass | **yes** |
| **`ml.responsible_finance`** | dict returned by the scorer | **yes** |
| **`greenwashing.risk`** | `GreenwashingAssessment` dataclass | **yes** |

Every entry was verified against the models. Nothing aspirational is registered.

**Deliberately not registered:** `audit.greenwashing_score` and
`good_agents.greenwashing_risk` exist but belong to different subject models,
not to a `CompanyProfile` metric. Registering them would conflate three
different things called "greenwashing".

---

## 3. Registry architecture

**Python, not a database table.** Definitions are code: they change when a
formula changes, they belong in review, and they must be importable without a
query. `MATERIAL_INPUTS` is already a Python structure for the same reasons. A
table would add a migration, an admin surface and a join to restate names the
code already has — and would let a definition drift from the calculation it
describes.

Lookup is a dict access: constant time, no query, safe per row (STEP 18).

**Resolvers are explicit callables.** No dynamic import from a stored string, no
`getattr` chain assembled from data. A metric that moves fails at import rather
than returning `None` somewhere far away.

```python
MetricDefinition(
    key='ethics.nei',
    kind=DERIVED,
    value_location='ethics.CompanyEthicsProfile.net_ethical_impact',
    resolver=_related_field('ethics', 'net_ethical_impact'),
    allowed_origins=DERIVED_ORIGINS,
    calculation='ethics.scoring.compute_net_ethical_impact',
)
```

### Two kinds only

`MATERIAL` and `DERIVED`. "AI", "ethical", "finance", "climate" are **domains** —
what a metric is *about* — not provenance semantics, which are about how its
value came to exist. Adding them as kinds would fragment the distinction that
matters.

---

## 4. Persisted vs ephemeral — the STEP 9 decision

**Material provenance stores no value. Derived provenance may, and only when
nothing persists it.**

D3A's rule stands wherever a value has a home: no duplicate, because two copies
drift. `recorded_value` is `NULL` for every metric with a resolver, enforced in
`clean()`.

For Mizan, responsible-finance and greenwashing there is no home. They are
recomputed per request and discarded. Provenance recording only their *method*
could not reconstruct what was actually computed — the lineage would describe a
number nobody can see again. So `recorded_value` is **required** for an
ephemeral metric and **rejected** for any other.

This did not require generalising `CompanyMetricProvenance` into something else.
One nullable column and one validation rule was the minimum safe design.

---

## 5. Input lineage

`inputs` is a self-referential M2M to **provenance rows**, not to metric keys.

Keys would resolve to whatever is current when asked — answering *"what would
this metric's lineage be if computed now?"* Only *"what was it when computed?"*
is an audit trail. A test supersedes an input and asserts the derived row still
names the row it actually read.

**What to record:** the rows the calculation *consumed*, not the ones the
formula mentions. A calculation that re-normalised around an unknown input did
not consume it. The D2 work makes this knowable — `_weighted()` and
`mean_of_known()` already track which inputs they used, because they had to in
order to re-normalise.

### Cycles (STEP 8)

Direct self-reference is rejected: a row cannot be its own input. Full DAG
validation across the whole graph is **deferred and recorded here as a hardening
item** — it needs a traversal on every write, and no writer produces multi-level
derived chains yet.

Note that citing a *prior row of the same metric* is legitimate, not a cycle: a
recalculation may reference the state it superseded. A test pins that.

---

## 6. Calculation version

Required for every derived row, alongside `methodology`. A `MODELLED` row
without a version cannot answer *"which formula produced this?"* — the question
derived provenance exists for.

| producer | convention |
|---|---|
| deterministic formula | `'<module>.v<N>'` — `scoring.v1`, `ethics-nei:v1` |
| ML model | artefact hash, so a prediction before a retrain is distinguishable from one after |
| Digital Twin | scenario id + engine version |

A git SHA may be supplemental metadata; it is not the human-facing version.

---

## 7. Public eligibility

`is_derived_publicly_defensible()` requires **both**:

1. the derived row's own origin is defensible — `MODELLED` qualifies, `SEEDED`
   does not; and
2. **every input it consumed** is defensible.

The second is what stops a `MODELLED` composite laundering `SEEDED` inputs into
a publishable number. A perfectly-executed calculation over synthetic data is
still synthetic.

A derived row with **no recorded inputs returns False** — the honest reading
before D3C-4 wires the calculators up: we cannot show the lineage, so we cannot
defend it.

**Not encoded here:** coverage thresholds, or how many inputs a composite needs.
Those are D5's, and guessing at them now would make them invisible when D5 comes
to decide them properly.

---

## 8. Open item: material-layer origin honesty

`MATERIAL_ORIGINS` permits `MEASURED`, and that is a **deliberate non-change**,
recorded rather than smuggled.

The D3C-1 finding stands: an assessed `CompanyProfile` score is not a direct
observation. `water_impact_score` is declared as *"0-100: water stewardship
quality"* — a judgment about water, not water. `INFERRED` or `ESTIMATED` would
be the truthful labels, and `MEASURED` belongs to a source layer that is
**0/186 populated**.

Enforcing that would break D3A's shipped contract, which explicitly tests and
permits `MEASURED` on material metrics, and would reject provenance a future
ingestion writer might legitimately record. D3C-2 is an identity and
storage-location PR; narrowing which origins a material metric may claim is a
semantics change that belongs with the introduction of a real source layer.

**What D3C-2 does enforce:** a derived metric may never be `MEASURED`. That is
the mislabel most likely to slip through, and it is now rejected by both the
service and the model.

---

## 9. What D3C-2 does not do

No writer integration (STEP 13) — no calculator records provenance yet. No API
exposure (STEP 14) — `/api/v2/` returns no `provenance` key, asserted by test.
No public eligibility change (STEP 15). No D4 work: no score field altered, made
nullable, dropped or renamed.

The migration is additive: one M2M through-table, one nullable column, and one
`AlterField` on `metric_key` that changes **help_text only** — `max_length`
stays 60. Verified forward → backward → forward on a disposable database.
