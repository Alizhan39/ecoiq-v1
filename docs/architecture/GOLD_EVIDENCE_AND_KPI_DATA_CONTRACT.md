# Gold Intelligence — Geological Evidence & Verifiable Mine KPIs (v1)

**Status:** foundational implementation; internally reviewable, **not** independently
certified, production-data loaded, resource estimate, AI model training or
operating safety evaluation.

## Architectural placement

This is **not a new scoring engine**. The four Django records in
`gold_intelligence/geology_models.py` reuse GoldProject, its project membership,
the existing Gold Investor View and the existing EcoIQ Mizan readiness bridge.
Industry KPIs are defined in `services/kpi_definitions.py` and calculated by
`services/mine_kpis.py`. The system-level Mizan evaluator retains all **11**
dimensions at `INSUFFICIENT_DATA` until approved, evidence-backed thresholds
are introduced. Quranic principles are ethical guidance, not a source for
arbitrary mining numeric coefficients.

## Four data contracts and mandatory chain of provenance

1. **GeologicalEvidenceSource** is a *specific source/version*: project,
   identifier, publisher, citation, source URL, rights/licence terms, observation
   and acquisition dates, original coordinate reference system, spatial
   coverage notes, SHA-256 of file content, synthetic/demo flag and review.
   Hashes and citations are human-declared here; there is **no file upload,
   automatic hash verification or external laboratory API** in this milestone.
   To approve internally, an authenticated reviewer, review time, meaningful
   citation, rights terms, hash and non-synthetic evidence are required.
2. **GoldDrillhole** has a distinct per-project hole ID; source must be a
   drilling log, with **WGS84 EPSG:4326** latitude/longitude, depth in metres,
   and optional collar elevation. Original UTM or local-grid inputs must be
   transformed externally with a documented method and retained source CRS
   before storing WGS84 collars. No inferred coordinates.
3. **GoldAssayInterval** stores a drillhole-scoped assay sample with unique
   source/sample ID, interval from/to (m), Au grade (g/t, including real zero),
   lab name, laboratory certificate, and sample type: primary, duplicate,
   blank, reference standard. Interval geometry is bounded by logged hole
   depth and referenced to the project's original lab certificate. An
   approved assay depends on an approved lab source and hole. QAQC *types*
   are recorded, but no automated standard-acceptance or resource estimation
   is claimed.
4. **MineKPIObservation** has a named approved method, exact period,
   matched numerator/denominator, evidence source/version, method version,
   review state and reviewer. Source/data may be pending, rejected, or
   *internally reviewed*. Both source and observation must be reviewed for
   its result to be labelled `INTERNALLY_REVIEWED`. This designation
   is **not** independent assurance, legal compliance or a certified KPI.

All four records remain private to the project's authorised members via
existing GoldProject access checks on the Investor View. Admin write access
is limited to the usual Django staff permissions; do not expose a generic
source or sample API without equivalent access and permission tests.

Approved records cannot be edited through model `.save()` without first
returning them to pending for re-review. This does **not** prevent privileged
bulk updates, direct SQL or tampering with a source file; database auditing,
immutable external object storage and signed third-party verification
remain future requirements.

## Metric definitions, required raw inputs and units

Each numerator and denominator must come from the **same site/scope and period**.
Definitions are version 1. Values use Decimal arithmetic; missing inputs
remain null; denominators must be positive; percent ratios above 100% are
rejected, never clipped.

| Metric | Numerator / denominator | Output | Mizan dimension |
| --- | --- | --- | --- |
| gold_recovery_pct | recovered Au g / feed-contained Au g × 100 | % | resource_efficiency |
| freshwater_m3_per_t | freshwater withdrawal m³ / dry ore processed t | m³/t | water |
| process_water_reuse_pct | recirculated water m³ / process water supplied m³ × 100 | % | water |
| electricity_kwh_per_t | electricity kWh / dry ore processed t | kWh/t | energy |
| tailings_t_per_t | dry tailings t / dry ore processed t | t/t | environment |
| rehabilitation_pct | restored/accepted hectares / disturbed hectares × 100 | % | intergenerational |
| local_procurement_pct | eligible local spend USD / eligible procurement spend USD × 100 | % | justice |
| lost_time_injury_frequency | lost-time injuries / work hours × 1,000,000 | per 1m hours | worker |
| ghg_tco2e_per_t | tCO₂e in declared boundary / dry ore processed t | tCO₂e/t | environment |

**Boundary clarity:** measure feed-contained gold from a documented metallurgical
balance, not from one drill-core interval; energy and emissions need stated
Scope 1/2 boundaries; reused water must not be inflated by recursive counting;
local supplier eligibility and incident definitions require approved written
policies. No scores are provided for data-free dimensions.

## Data onboarding sequence — before ML training

- **Licensing and access:** verify Kazakhstan mineral block polygon,
  acquisition/use rights and third-party geological data licences. Do not
  infer vacant licences from satellite images.
- **Geological source manifest:** secure original published reports, cadastral
  layers, field logs, survey footprints, assay certificates and QAQC material;
  capture hashes, timestamp and terms. Potential sources include government
  geological/cadastre records, licensed prospecting archives, company technical
  reports and accredited laboratories, **subject to availability and rights**.
- **Spatial QA:** verify EPSG code, control points, WGS84 conversion, valid
  lat/lon, drillhole IDs and survey deviations; collar location alone is not
  a 3D downhole path. Add survey stations in a later schema iteration.
- **Sample QA/QC:** chain of custody, core recovery, duplicate/blanks/standards,
  detection limits, lab accreditation, sample interval overlap controls and
  third-party lab re-assays. Current schema records identity and approval
  but **does not automatically execute** these QA checks.
- **Independent technical gate:** qualified geological assessment, NI 43-101/
  JORC or otherwise appropriate disclosure if applicable, mineralogical
  study, drilling programme and resource estimation using the governing
  reporting standard. No resource/reserve inference from isolated assays.
- **Predictive ML:** only after provenance and QAQC pass; hold out entire
  deposits or geographic regions (not adjacent samples randomly), check
  spatial leakage, document labels, precision/recall/calibration and publish
  an abstention state for out-of-distribution prospects.
- **Operations and KPI calibration:** time series from meters, validated plant
  mass balance, safety register, environmental baseline; expert review of
  thresholds and site permits. Mizan remains a multi-dimensional decision
  framework, never a shortcut to certify a mine.

## How to use this milestone

After GitHub PR review/CI and DB migrations, authorised staff may enter
source manifests, drillholes, assay intervals and operating KPI observations
through **Django Admin**. The project Investor View then exposes period-matched
KPI calculation results with explicit `MISSING_INPUT`,
`SOURCE_REVIEW_REQUIRED`, `KPI_REVIEW_REQUIRED`, `DEMO_UNVERIFIED`
or `INTERNALLY_REVIEWED` status.

**Not delivered by this PR:** live Kazakhstan source imports, file upload,
automatic SHA verification, QAQC thresholds, drillhole directional surveys,
geostatistical interpolation, JORC/NI43-101 resources, ore-body 3D certainty,
operational environmental certification, actual ML training or bankable
feasibility economics.

## Tests / rollout

Run `python manage.py makemigrations --check --dry-run`,
`python manage.py check`, and
`python manage.py test gold_intelligence.tests_geological_kpis gold_intelligence.tests_mizan_bridge`.
The PR's normal CI also runs broad regression checks.
Run the migrations in **staging first**, test with synthetic sources and
private project memberships, then promote with backups and rollback plan.
Do not import licensed geological source files into the public GitHub repository.
