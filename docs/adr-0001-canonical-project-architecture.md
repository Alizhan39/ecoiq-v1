# ADR-0001: Canonical Project Architecture (Planning Only — No Code Changes)

**Status:** Accepted (planning stage only — implementation not started)
**Date:** 2026-07-11
**Phase:** Phase 1A, Task 6 (Canonical Architecture Decision Analysis)

This is a planning/documentation artifact. It records a direction, not an
implementation. No `Project` model changes, no migrations, and no rename of
`GoldProject` were made as part of this ADR.

## Context

EcoIQ's Canonical Architecture Decision Analysis (the audit preceding this
Phase 1A) found multiple "Project"-shaped concepts across the codebase:
`projects/` (a static marketing-pilot list, no database), `api/projects_urls.py`
(a stateless readiness-scoring calculator, no persisted model),
`gold_intelligence.GoldProject`, `heating.PilotProject`,
`khalifa_stewardship_tour_operating_system.StewardshipTour`,
`legacy_safe.LegacyProject`, and `league.EnvironmentalProject`. EcoIQ needs
one canonical Project concept to build future sectors on (Mining, Metals,
Mineral Processing, Oil & Gas, Uranium, Energy, Manufacturing, Agriculture,
Food Systems, Infrastructure, Water, Heating, Real Estate, Tourism,
Community Projects) without creating one giant model with every sector's
fields baked in, and without breaking the working systems built on
`GoldProject` today (Capital Guardian, Gold Intelligence's project-finance
engine).

## Current State

`gold_intelligence.GoldProject` is the most mature project model in the
codebase:

- **Commodity-agnostic by design already**: its `commodity` field already
  includes non-gold choices (copper, infrastructure, energy, agriculture,
  other) — its own docstring states a non-gold project "can reuse this
  exact model... rather than a second Project model per commodity."
- **Geography**: FK to `countries.CountryProfile`.
- **Project status**: exploration/licensing/construction/production/expansion.
- **CAPEX/production/financials**: `total_capex_usd`, `annual_opex_usd`,
  `expected_annual_production_oz`, `gold_price_assumption_usd_per_oz`,
  `aisc_usd_per_oz`, `discount_rate_pct`, `total_committed_capital_usd`.
- **Insurance**: `insurance_coverage_usd`, `insurance_expiry_date`.
- **Project finance**: `gold_intelligence/services/project_finance.py` computes
  real NPV/IRR/payback/sensitivity from these fields (Newton's-method IRR,
  no external financial library).
- **Capital Guardian relationships**: `ProjectGovernance`, `CapitalTraceEntry`,
  `RedFlag`, `RedFlagRuleConfig`, `OperationalSnapshot`, and the child models
  `CapitalBudgetLine`, `MineTimelineMilestone`, `EquipmentSpec` all hard-FK
  to `GoldProject`. 481 lines of tests exercise it.

No other Project-like model has anywhere near this ecosystem. `heating.PilotProject`
is small and self-contained (KZT currency, "homes" units, no FK to anything).
`khalifa_stewardship_tour_operating_system.StewardshipTour` models an
event/expedition (dated start/end, participant capacity), not a capital
asset. `league.EnvironmentalProject` is thin (10 fields, company-anchored,
no downstream ecosystem). `waste_to_value_capital_allocation_engine`
deliberately keeps `organisation`/`asset`/`project` as plain text fields —
its own docstring states no trustworthy Project model exists elsewhere to
FK to.

## Decision

**Do not rename `GoldProject` yet.** It remains the canonical project
anchor for now, exactly as it is, under its current name, with its current
table.

**Future direction — generalise gradually, in place:**

1. `GoldProject` continues to serve as the canonical multi-sector Project
   concept. Its already-generic fields (country, status, CAPEX/OPEX,
   committed capital, insurance) are the shared "core" every sector uses.
2. Sector-specific fields that only make sense for one sector (e.g.
   `ore_grade_g_per_tonne`, `gold_price_assumption_usd_per_oz`) stay as
   nullable/optional fields on the core model **only if** a future sector
   can plausibly reuse them (e.g. any commodity priced per-unit-of-output).
   Where a sector's data genuinely does not fit the core model's shape
   (e.g. `heating.PilotProject`'s "scale = A/B/C homes tiers" or
   `khalifa_stewardship_tour_operating_system.StewardshipTour`'s
   participant/date-range fields), it gets its own **extension model**
   with a FK back to the canonical Project, added only when that sector is
   actually being onboarded — not speculatively for all 14 sectors up
   front.
3. Candidate future extension models (**none created now**):
   `MiningProjectExtension`, `EnergyProjectExtension`,
   `HeatingProjectExtension`, `AgricultureProjectExtension`,
   `InfrastructureProjectExtension`, `TourismProjectExtension`. Each would
   hold only the fields genuinely specific to that sector; the canonical
   Project row remains the single source of identity, geography, status,
   and core financials regardless of sector.
4. `heating.PilotProject`, `khalifa_stewardship_tour_operating_system.StewardshipTour`,
   `league.EnvironmentalProject`, and `legacy_safe.LegacyProject` are **not**
   migrated or merged in Phase 1A or in this ADR. Each stays exactly as it
   is until its own sector is deliberately onboarded into the canonical
   model — migrating a working, tested model preemptively, with no
   consuming feature ready to use the merge, would be exactly the kind of
   premature over-generalisation this ADR is trying to avoid.
5. The five static `projects/` marketing pilots are explicitly out of scope
   for this generalisation (per founder decision — they may eventually
   become real trackable Project rows, but are not converted now).

### Options considered

| Option | Description | Verdict |
|---|---|---|
| **A — Project + sector-specific extension models** (chosen) | Keep `GoldProject` as the generic core, add thin extension models per sector only when needed | Reuses the most mature, most tested, most-depended-upon model; no premature work |
| B — Project + flexible/JSON structured data | Replace typed fields with a JSON blob for sector-specific data | Rejected: `project_finance.py`'s NPV/IRR math depends on typed Decimal/Float fields; a JSON blob would break or duplicate that validation |
| C — Project + ProjectAsset + ProjectResource + ProjectFinancialProfile + ProjectImpactProfile | Fully decompose into satellite tables up front | Rejected as premature: only 4 real `GoldProject` rows exist today; no usage evidence demands this granularity; would force an immediate rewrite of Capital Guardian's 5 hard-FK'd models for a problem that hasn't materialised |
| D — Something else | (not identified as better than A during the audit) | Not pursued |

## Non-Goals (Explicit)

- This ADR does **not** rename `GoldProject`.
- This ADR does **not** create any extension model now.
- This ADR does **not** migrate `heating.PilotProject`, `StewardshipTour`,
  `EnvironmentalProject`, or `LegacyProject` data into `GoldProject`.
- This ADR does **not** convert the static `projects/` marketing pilots into
  database rows.
- This ADR does **not** change any URL, view, or template.
- This ADR does **not** create a migration of any kind.

## Migration Risks (for whenever generalisation actually begins)

- **HIGH** — Renaming `GoldProject` → `Project` (not proposed here, but
  flagged for the future): touches Capital Guardian's 5 models,
  `gold_intelligence`'s 3 child models, `project_finance.py`,
  `investor_dashboard.py`, every seed command, and every existing test that
  imports `GoldProject`. Requires its own dedicated ADR and founder sign-off
  before any code is written.
- **MEDIUM** — Adding a new sector extension model with a FK to `GoldProject`:
  additive, but still touches a model with 5+ hard-FK dependents, so it
  needs careful additive-only migration discipline (new nullable FK on the
  extension side, no changes to `GoldProject` itself).
- **LOW** — Continuing to add optional, nullable, sector-agnostic fields
  directly to `GoldProject` when a field is genuinely reusable across
  sectors (e.g. a generic `price_assumption_usd_per_unit` alongside the
  existing gold-specific one) — this is the same kind of additive change
  already made safely across Capital Guardian Phases 1–3.

## Compatibility Requirements (for whenever generalisation actually begins)

- Every existing gold-specific computation (`project_finance.py`,
  `investor_dashboard.py`, `capital_protection.py`, `red_flag_engine.py`)
  must continue to null-guard on gold-specific fields exactly as it already
  does — generalisation must never assume those fields are populated for a
  non-gold project.
- No existing `GoldProject` row, migration, or FK relationship may be
  altered in a way that breaks Capital Guardian's current test suite.
- Any new extension model must be additive (new table, new nullable FK) —
  never a change to `GoldProject`'s existing columns.

## Consequences

- Short term: nothing changes. `GoldProject` keeps its name, its schema,
  and its role exactly as today.
- Medium term: as new sectors are onboarded, thin extension models get
  added one at a time, each reviewed on its own merits, rather than as one
  large speculative migration.
- This ADR gives the founder and future engineers a documented, agreed
  direction to point to before the first real sector-extension model is
  proposed, so that decision doesn't have to be re-litigated from scratch.
