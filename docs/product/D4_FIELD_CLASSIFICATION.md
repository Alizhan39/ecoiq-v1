# D4 — Field-by-field nullability classification

**D4B.** Which score fields may hold NULL, and which may not.

The brief for this phase was explicit: *do not mechanically make all fields
nullable.* So every field was classified before anything was changed, and the
classification is recorded here rather than implied by the migration.

---

## The defaults are worse than "50"

The programme has been calling this "the default=50 problem". Re-scanning main
showed that is only two-thirds of it. Three different neutral values were in
use, and they do not all fail in the same direction:

| default | fields | what it claims from an absence |
|---|---|---|
| `50.0` | 15 material + 5 pillars + `profit_extraction_score` (+6 snapshot pillars) | an average company |
| `30.0` | `controversy_risk_score`, `profit_extraction_risk_score` | **low risk — favourable** |
| `0.0` | `harm_penalty` (profile + snapshot) | **no harm found — favourable** |
| `0.0` | `ecoiq_total_score` | **worst possible score — adverse** |

The `30.0` and `0.0` harm defaults are the ones worth pausing on. A company
nobody assessed was recorded as low-controversy and harm-free — a *favourable*
finding manufactured from an absence, which is the failure mode this programme
exists to remove, pointing the opposite way from the one it was named after.

`ecoiq_total_score = 0.0` fails the other way: it is the harshest possible
statement about a company, applied by default.

---

## Classification

### A. Genuine score where unknown is possible → `null=True`

**15 material metrics** — the registered inputs an analyst or ingestion
supplies. Unknown is the normal state for most companies today.

`waste_management_score`, `water_impact_score`, `biodiversity_impact_score`,
`jobs_created_score`, `regional_development_score`,
`infrastructure_contribution_score`, `national_value_score`,
`energy_transition_score`, `digitalization_score`,
`infrastructure_upgrade_score`, `future_readiness_score`,
`transparency_score_detail`, `audit_quality_score`,
`procurement_transparency_score`, `anti_corruption_score`

**2 risk scores** — `controversy_risk_score`, `profit_extraction_risk_score`.
Same category, and the correction matters more because their default was
favourable.

### B. Derived field → `null=True`

**5 pillars** — `public_benefit_score`,
`environmental_responsibility_score`, `modernization_score`,
`transparency_anti_corruption_score`, `ethical_alignment_score`.

A pillar re-normalises across the material inputs it can see. When every input
beneath it is unknown there is nothing to re-normalise, and the pillar is
unknown too — it does not become 50 by arithmetic.

**1 composite** — `ecoiq_total_score`. Same reasoning, one layer up.

### C. Measured metric where zero is valid → `null=True`, and the distinction matters

**`harm_penalty`** (profile and snapshot). Zero is a real, meaningful finding:
*no harm was identified*. That is exactly why it cannot double as "we did not
look". The default of `0.0` made those two states indistinguishable, and the
favourable one was the one it asserted.

### D. Legacy field → `null=True` for consistency

**`profit_extraction_score`**. Not in the metric registry, still read by
`profit_extraction_warning`. Left in place rather than removed — deleting a
field is a separate decision from making it honest.

### E. Snapshot fields → `null=True`, same migration

**8 fields** on `CompanyScoreSnapshot`: the 6 pillars, `harm_penalty`, and
`total_score`.

Handled together with the profile deliberately. A snapshot is the historical
record used to check what was true at a date; if it could not represent
unknown, every backfilled snapshot would silently reintroduce a fabricated
value that the live profile no longer holds — the schema quietly undoing the
programme.

`total_score` was `REQUIRED` with no default, which meant a snapshot simply
could not be written for a company with no composite. Nullable is the honest
fix: history can now record "unknown at this date".

The model's newer intelligence fields were already `null=True` with the
comment *"never fabricated to fill a gap"*. The pattern was already right
here; the six legacy pillar fields just predate it.

### F. Required categorical / default → unchanged

**`pollution_level`** (`CharField`, `default='medium'`). Not touched by this
migration because it is not numeric, but it carries the same defect and is
classified in
[`CALCULATION_CONTEXT_PROVENANCE.md`](CALCULATION_CONTEXT_PROVENANCE.md) as a
material metric that needs registry support for categorical values. Two
separate modules were found substituting `'medium'` for an unclassified
company (#244, #254). **Open.**

**`moral_label`** (`CharField`, blank). An unscored company still reports a
label; #258 stopped the LLM prompt asserting one. The field itself is
unresolved. **Open.**

### G. Unrelated default → out of scope

**11 fields with `default=50`** in other subsystems:
`digital_twin.LossDetection.confidence`,
`financial_intelligence_cloud.PortfolioSignal` (2),
`khalifa_stewardship_tour_operating_system.StewardshipProblem` (3),
`waste_to_value_capital_allocation_engine` (5).

These belong to separate engines with their own semantics, and none feeds the
company evidence graph. Changing them would be a mechanical sweep of exactly
the kind this classification exists to avoid. **Recorded, not changed.**

---

## What D4B does and does not do

**Does:** adds `null=True, blank=True` to 33 fields — 25 on `CompanyProfile`,
8 on `CompanyScoreSnapshot`.

**Does not:** remove the defaults. That is D4C, and it is a separate migration
on purpose. Splitting them means:

- D4B changes only a constraint. No existing row changes, no new row behaves
  differently, and the migration reverses cleanly.
- D4C changes behaviour — new profiles stop receiving fabricated scores — and
  can be reasoned about, and reverted, on its own.

Conflating them would produce one migration that both relaxed a constraint and
changed what every future write means.

---

## Reversibility

Verified on a disposable database, forward → backward → forward, with data
present:

| state | rows | NULLs | `SUM(water_impact_score)` | `NOT NULL` flag |
|---|---|---|---|---|
| 0011 applied | 5 / 5 | 0 | 100.0 | 0 |
| reversed to 0010 | 5 / 5 | 0 | 100.0 | 1 |
| 0011 re-applied | 5 / 5 | 0 | 100.0 | 0 |

Nothing but the constraint moves.

**One limit, stated plainly:** the reverse migration is safe *while no NULLs
exist*. Once D4C lands and real unknowns are written, reversing D4B would fail
on the `NOT NULL` constraint — correctly, because at that point reversing it
would require inventing values for the rows that are honestly unknown. Rolling
back past D4C means deciding what to write into those rows, and that is a
product decision, not a migration.
