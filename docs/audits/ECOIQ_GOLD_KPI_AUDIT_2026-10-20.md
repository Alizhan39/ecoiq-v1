# EcoIQ KPI and Gold Intelligence integration audit — 20 October 2026

**Scope:** static inspection of the `main` branch of `Alizhan39/ecoiq-v1`.
This is a code/contract audit, **not** an executed end-to-end test, independent
methodology validation, geological resource estimate or legal assessment.

## Inventory: implemented versus registered versus proposed

| Layer / owner | Actual source | Status observed | Important limit |
| --- | --- | --- | --- |
| Company six-pillar composite | `companies/scoring.py` | Executable 25/25/20/15/10/5 weighted calculation plus separately capped harm penalty | Requires known inputs; method-specific weights are design choices, not scriptural constants |
| Company Mizan scoring | `mizan/scoring.py` | Executable six-component rules and lineage functions; dimensions use 25/25/20/15/10/5 | Not the same construct as system-level Mizan |
| Project Mizan scoring | `mizan/project.py` | Executable rule-based project scorer and feature vector | Contains heuristic sector, geography and confidence assumptions; not validated gold-specific ML |
| Ethics master formulas | `ethics/scoring.py` | `compute_net_ethical_impact` (NEI), `compute_transition_stewardship` (TSS), `compute_regenerative_value` (RVI) are executable | Historical/company profile fields, not verified mine data |
| Formula registry | `ethics/registry.py`, `ethics/models.py` | **3 masters + 33 sub-formula definitions** across eight categories | The 33 sub-formulas are descriptive records, **not** 33 standalone calculation functions |
| System-level Mizan | `mizan/system_balance.py` | Executable 11-dimension status / constraint / conflict aggregation | Deliberately no global moral score; external thresholds and evidence required |
| Decision OS | `ecoiq_os/kernel.py`, `ecoiq_os/domains.py` | Executable evidence/flow/Mizan/human review gates; mining domain registered | Does not independently validate claims, perform geological inference or run autonomous mine decisions |
| Quran / knowledge bindings | `islamic_knowledge/` and `docs/architecture/ISLAMIC_DECISION_INTELLIGENCE_PLAN.md` | Typed knowledge and review contracts; roadmap acknowledges draft interpretations | Quranic ethics are normative inspiration; the software's numerical weights are human-selected operationalisations |
| Gold economics | `gold_intelligence/services/project_finance.py` | NPV, IRR, payback, sensitivity/scenarios computed when inputs exist | Simplified constant annual net cash-flow model; not a bankable feasibility study |
| Gold risks | `gold_intelligence/services/risk_intelligence.py` | Mix of stored regional/national proxies and `available: False` gaps | Country proxies and nearby power-plant counts do not establish mine-site risks |
| Gold budgets / supplier assets | `gold_intelligence/models.py`, `services/aggregates.py` | Stored CAPEX budget lines, milestones, equipment specs, sum aggregations | Inputs are declarations, not third-party-verified quotes |
| Gold ↔ Mizan bridge | `gold_intelligence/services/mizan_bridge.py` (this PR) | Read-only mapping of seven already-declared gold inputs into Mizan readiness, and 11 unclassified dimensions | Outputs `INSUFFICIENT_DATA` until reviewed evidence and dimension criteria exist; no new claims/weights |

## Actual master formulas (code-owned)

- **Company composite:** public benefit 0.25, environmental 0.25, modernisation 0.20, transparency 0.15, anti-corruption 0.10, ethical alignment 0.05; separately applied harm penalty.
- **Mizan company/project score:** public benefit 0.25, harm reduction 0.25, justice distribution 0.20, transparency/accountability 0.15, stewardship 0.10, evidence confidence 0.05.
- **NEI:** overall benefit minus 0.30 × harm burden (see `ethics/scoring.py`). **TSS** and **RVI** use explicit components and adjustments; review the live functions rather than assuming the descriptions are exact specifications.
- **System-level Mizan:** **no numeric weighted master formula**. Records economic, resource efficiency, energy, water, environment, human, worker, social, justice, resilience, and intergenerational dimensions; hard constraints and conflicts can block automated progression.

None of these coefficients should be attributed directly to Quranic scripture without independent scholarly and methodological review.

## Safe integration in this PR

The new read-only bridge makes zero DB writes, requires no migration, does not
change canonical scoring weights, does not create AI/model predictions, and
does not classify a mine as healthy/sustainable/profitable.

Seven existing GoldProject inputs are exposed as **declared, unverified** KPI
observations with units and source-status flags; `null` stays missing, while a
measured numeric zero remains zero. Any free-text source is still unverified.
Mizan's 11 dimensions remain `INSUFFICIENT_DATA` until approved, sourced,
site-specific criteria and independent supporting evidence are supplied.

The investor view may display data collection readiness; never interpret the
count of filled inputs as validation or an investment recommendation.

## Remaining gates before any gold ML training / operational claim

1. Inventory ownership and licensing of geology, assay, drilling, remote
   sensing and operational datasets; record source, date, spatial coverage,
   geological coordinate system and uncertainty.
2. Implement sample/QAQC provenance: lab certificates, duplicates, blanks,
   standards, chain of custody, ore geometry and resource classification.
3. Create site-specific gold KPI definitions with denominator, time period,
   metric unit, version, responsible reviewer, approval status and provenance
   chain: recovery, tailings, water balance, energy intensity, injury rates,
   restoration, local value and safety constraints.
4. Approve threshold methodology and independently validate any Quran/Maqasid
   interpretation and its human-selected mathematical operationalisation.
5. For predictive ML: prevent spatial/temporal leakage, use independent
   holdout deposits/drillholes, document precision/recall/calibration and
   abstain when evidence is missing.
6. Upgrade mine economics to time-varying schedule, royalties/taxes, strip
   ratios, metallurgical variability, working capital, closures, contingencies
   and geological uncertainty; external study/review before capital commitments.
7. Add security/privacy and access-control tests for any future endpoint;
   no unreviewed or private site data on public EcoIQ pages.

## Audit caveats

- This inventory is from code inspection. CI and database-backed test suites
  must run on the PR before merging; no passing status is asserted here.
- Existing gold risk heuristics include national-level proxies; they cannot
  be promoted to site-specific safety or environmental grades.
- The historical project Mizan scorer contains heuristic defaults. The new
  bridge intentionally **does not use** that scorer for gold projects.
- A demonstrator's outputs are not validated reserves or available-for-sale gold.
