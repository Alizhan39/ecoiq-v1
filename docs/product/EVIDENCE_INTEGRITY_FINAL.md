# Evidence Integrity — Final Architecture

**Status: P0 complete.** This document describes what EcoIQ does now, not what
it was planned to do. Where a limit remains it is stated as a limit.

---

## The chain

```
SOURCE FACT                     a filing, an audit, a disclosure
  ↓                             somebody else measured this
MEASURED
  ↓                             EcoIQ reads it and forms a judgement
ASSESSED MATERIAL METRIC        one of 16 registered inputs
  ↓
INFERRED / ESTIMATED            an assessment, not a reading
  ↓                             re-normalised across known inputs
PILLAR                          6 of them
  ↓
MODELLED
  ↓                             weighted across all six
COMPOSITE                       company.ecoiq_total
  ↓
MODELLED
  ↓                             Mizan, QDF, financing, ML, greenwashing
DECISION OUTPUT
  ↓
PUBLIC ELIGIBILITY              coverage × confidence × defensibility
  ↓
PUBLISHED / PROVISIONAL / INSUFFICIENT_EVIDENCE
```

**The step that matters most is the second one.** A real source does not make a
0–100 EcoIQ score `MEASURED`. The pipeline reads filings and an LLM turns them
into five pillar signals fanned across sixteen fields; the *source fact* may be
measured, but the number EcoIQ stores is an assessment derived from it. So
ingestion writes `INFERRED`, and `MEASURED` stays reserved for a value taken
from a source with no EcoIQ judgement in between.

---

## Four concepts, deliberately separate

They are related and they are not interchangeable. Collapsing any two of them
was the original defect.

### 1. Provenance — *where did this number come from?*

A per-metric, append-only record. Seven states:

| origin | meaning |
|---|---|
| `MEASURED` | taken from a source with no EcoIQ judgement in between |
| `INFERRED` | EcoIQ's assessment derived from a source fact |
| `ESTIMATED` | an assumption someone stated |
| `MODELLED` | a calculator's output |
| `SEEDED` | demo data |
| `LEGACY_UNKNOWN_PROVENANCE` | predates the store; cannot be reconstructed |
| `UNKNOWN` | no value, so no origin |

Derived metrics carry **lineage**: a self-referential M2M to the provenance
*rows* they consumed, not to metric keys, so history stays pinned to what was
actually read. Defensibility is **transitive** — contamination anywhere beneath
a value disqualifies it, with cycle protection for the diamonds this graph
contains.

### 2. Coverage — *how much of what we need is supported?*

Weighted by the scoring engine's own composite weights, so a missing
25%-weighted pillar does not read like a missing 5%-weighted one. Reported as a
ratio **and** its two halves: *"78% — 11 of 16 material inputs supported."*

`MEASURED`, `INFERRED` and `ESTIMATED` count. **`MODELLED` does not** — a
material input carrying `MODELLED` is a model output wearing an input's
clothes, and counting it would let a model corroborate itself. `SEEDED` and
`LEGACY` never count.

`missing` and `unevidenced` are reported separately: *"we hold nothing"* and
*"we hold a number we cannot stand behind"* need different work to fix.

### 3. Confidence — *how good is what we do hold?*

`HIGH` / `MEDIUM` / `LOW` / `INSUFFICIENT_EVIDENCE`. **Never a percentage** —
the inputs are categorical, and rendering them as `0.72` would manufacture
precision the data cannot support.

Independent of coverage. 100% coverage from unverified press releases is
complete and weak; 40% from independently verified audits is incomplete and
strong. Staleness can only ever lower a label.

### 4. Human review — *did a person look?*

`review_status` on the provenance row. **Every automated writer proposes.**
Only `companies.analyst.declare_metric` can produce `confirmed`, and only for a
user holding `change_companymetricprovenance`.

---

## Coverage formula

```
coverage = Σ weight(f) for f in evidenced      ÷   Σ weight(f) for f in required
```

where `weight` comes from `MATERIAL_INPUTS` (the scoring engine's own composite
weights, summing to 1.0), and a field feeding two pillars is counted **once** in
the denominator while keeping the sum of both contributions as its weight.
Counting it twice would ask for 17 pieces of evidence when 16 exist and put
100% permanently out of reach.

For a derived metric, `derived_coverage_for` walks the recorded lineage to its
**material ancestors** and counts each distinct one once — diamonds resolve
rather than inflating the figure.

Display precision is whole percent. The denominator is 16; `82.4%` would imply
a precision the data cannot support.

---

## Eligibility rule

```python
PUBLISHED  requires  coverage == 100%  AND  a score  AND  confidence != INSUFFICIENT
```

Every other outcome is `INSUFFICIENT_EVIDENCE`. `PROVISIONAL` is defined and
reachable but currently maps to nothing.

**Why 100% and not one of the candidate thresholds.** The brief asked for
20/40/60/80% simulated against the real dataset. That simulation was run
against production and returned:

> 467 of 467 companies sit at 0% coverage.

Every candidate produces the same answer, so the distribution contains no
information to choose between them. Picking 40% over 60% on that basis would be
inventing a justification. The rule is therefore the most conservative one
available, and `simulate_thresholds()` ships so the decision can be **re-taken
against real data** when production has some — rather than re-argued from first
principles.

Tightening a threshold later is a policy change. Publishing something that
should not have been published is not recoverable.

The rule lives in **one module**. A test asserts `PUBLISH_COVERAGE` appears in
exactly one non-test file, because the detail page renders the composite in
seventeen places and a second copy would eventually disagree with the first.

---

## Financing gate

Company-specific financial claims obey the same gate. An eligibility card —
*"meets Green Bond use-of-proceeds criteria"* — is a **stronger** statement than
the score it rests on, so if the score cannot be published, the claim cannot
either. Enforced inside the helper, not by its caller: containment must be a
property of the claim, not of who happens to ask for it.

---

## API v2 contract

```json
{
  "ecoiq_score": null,
  "score_status": "INSUFFICIENT_EVIDENCE",
  "evidence_coverage": 0,
  "confidence": "INSUFFICIENT_EVIDENCE",
  "rank": null
}
```

and, only when genuinely supported:

```json
{
  "ecoiq_score": 76.4,
  "score_status": "PUBLISHED",
  "evidence_coverage": 100,
  "confidence": "HIGH",
  "rank": 12
}
```

`evidence_coverage` and `confidence` are separate fields because one number
cannot say both things. `rank` is null when the score is not publishable — a
rank is a comparative claim, and publishing one would assert exactly what the
score is withholding.

**API v1 is unchanged.** Its keys and shapes are preserved for existing
consumers. Domain truthfulness was not weakened to satisfy it; v1 simply reads
fields that now hold NULL more often.

---

## Schema

33 fields nullable across `CompanyProfile` (25) and `CompanyScoreSnapshot` (8);
32 neutral defaults removed. `new CompanyProfile()` now receives **no** scores
at all.

The defaults were worse than the "50" the programme was named after:

| default | claimed from an absence |
|---|---|
| `50.0` | an average company |
| `30.0` | **low risk** — favourable |
| `0.0` on `harm_penalty` | **no harm found** — favourable |
| `0.0` on `ecoiq_total_score` | **worst possible** — adverse |

Historical values were **not** rewritten. They stay, covered by
`LEGACY_UNKNOWN_PROVENANCE`, and public eligibility rejects them. Rewriting
them would be destroying data on a guess.

---

## What is still true, and limits

- **Every company in production is at 0% coverage** and nothing is published.
  That is the correct state, not a failure: the estate is entirely legacy data,
  and the system now says so instead of showing numbers.
- **`ml.predicted_12m` has admittedly partial lineage.** Its primary path fits
  OLS over `ScoreHistory`, which carries no provenance. Documented at the
  declaration and asserted in tests.
- **15 of `ml.score`'s 29 features are unrepresented** — legacy `Company.score_*`
  fields and runtime context.
- **`pollution_level` is a material metric that is not registered**, because the
  registry has no representation for categorical inputs. Two modules were found
  substituting `'medium'` for an unclassified company.
- **Evidence confidence inside Mizan** is still computed from `is_verified`,
  `status` and `ai_summary` rather than from provenance origins. The better
  design is recorded in `CALCULATION_CONTEXT_PROVENANCE.md`; it changes scores,
  so it needs its own phase.
- **Model artefacts are overwritten in place.** The content digest makes a
  retrain *detectable*, not the old model *retrievable*.
- **12 neutral defaults remain** — all in Labs/engine subsystems
  (`digital_twin`, `financial_intelligence_cloud`, the stewardship tour, the
  waste-to-value engine). None feeds the company evidence graph.

---

## Superseded documents

These predate the final architecture and are kept for history. Where they
disagree with this document, this one is correct.

| document | what changed |
|---|---|
| `NULLABILITY_READINESS.md` | counts were re-measured in D4A; the schema is now nullable |
| `D4_NULLABILITY_PLAN.md` | superseded by `D4_FIELD_CLASSIFICATION.md` and executed |
| `D3C_WRITER_INTEGRATION.md` | all writer families are integrated; the open question in §"Open question" was answered by the registry |
| `EVIDENCE_INTEGRITY_PLAN.md` | the plan; this is the outcome |

`PROVENANCE_ARCHITECTURE.md`, `DERIVED_METRIC_REGISTRY.md`,
`DERIVED_METRIC_PROVENANCE.md`, `CALCULATION_CONTEXT_PROVENANCE.md`,
`ML_PROVENANCE_AUDIT.md` and `D4_FIELD_CLASSIFICATION.md` remain current.
