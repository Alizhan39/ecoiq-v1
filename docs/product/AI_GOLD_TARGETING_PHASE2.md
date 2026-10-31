# EcoIQ AI Gold Targeting — Phase 2 (GeoJSON + Evidence Map)

**Stage: experimental, committed code, not yet deployed or validated by CI.**
This increment extends the v0.1 expert-weighted screening engine; **no trained gold classifier and no discovery claims**.

## New endpoints (authenticated)
- `GET /gold-intelligence/targets/`: server-rendered Folium/Leaflet interactive map.
- `GET /gold-intelligence/targets/geojson/`: machine-readable, WGS84 GeoJSON FeatureCollection.
- `?region=Kalba` and `?kind=reference_occurrence` query filters.
- Maximum 500 features per response; `metadata.truncated` signals clipping.
- Staff see all curated records; non-staff see only records tied to actively shared GoldProjects. No public read or write endpoint.

## Persisted model
`gold_intelligence.GoldTarget` holds Point / Polygon / MultiPolygon coordinates in a Django JSONField
(JSONB on PostgreSQL, JSON on SQLite). All coordinate pairs are `[longitude, latitude]`, EPSG:4326.
A native PostGIS `geometry` column and GiST indexes **have not** been enabled; this is a future
migration subject to a tested PostGIS extension, backups, ops approval and performance validation.

Records distinguish:
1. `reference_occurrence` — historical source-backed known occurrence; **not** an exploration target.
2. `research_area` — desktop research footprint; **not** evidence of gold.
3. `candidate_target` — geologist-nominated candidate; index only after independent source review.

Scores are `null` for demo/unreviewed/historical/research records, and whenever any of five sourced
features is missing. Source issuer/url/id/date/reuse terms accompany every record. Rights default
to `unknown`; an occupied/restricted site must never be presented as available.

## Historical USGS MRDS conversion (optional)
Download source records yourself from a licensed/verified USGS MRDS distribution. The USGS feature service
can serve exported GeoJSON with fields such as `dep_id`, `site_name`, `code_list` and geometry. Then:

```bash
python manage.py convert_usgs_mrds_gold /secure/mrds_source.geojson /secure/normalized_mrds.geojson --bbox 73 42 80 47
python manage.py import_gold_targets /secure/normalized_mrds.geojson
python manage.py import_gold_targets /secure/normalized_mrds.geojson --apply --real-records --confirm-data-rights
```

The bounding rectangle is **not Kazakhstan's administrative boundary**, and an MRDS point is not
proof of industrial gold or current permissions. Converted records always remain historical reference
occurrences and unreviewed until staff review; their observation dates are unknown by default.
The conversion command does not automatically fetch data, and the live service is not yet integrated.

## Safe importer
Create a local FeatureCollection with a stable `id` per feature and properties:
`name`, `feature_kind`, `region`, `source_name`, `source_url`,
`source_reference` and `source_rights`. Optionally supply `source_observed_on` (YYYY-MM-DD) **only** if the original observation date is documented; otherwise store null.
Optionally `evidence` contains the v0.1 normalized, individually sourced feature objects.
Do not supply rights availability by inference from the geology.

```bash
python manage.py migrate
python manage.py import_gold_targets /secure/target_layers.geojson
python manage.py import_gold_targets /secure/target_layers.geojson --apply --real-records --confirm-data-rights
python manage.py test gold_intelligence.tests_targeting_geojson gold_intelligence.tests_targeting
```

`--apply` writes pending-review records. `--real-records` asserts source-backed non-demo
data, but **does not** grant an approval or a positive mining-rights status.
Only authorized staff can inspect/edit records in admin; fieldwork requires separate approvals.

## Public source catalogue (manual ingestion only; no data silently fetched)
- **Kazakhstan E-Qazyna Minerals**: official interactive subsurface-licensing map. It is not
  assumed to expose a stable licensed bulk GIS API or permit map scraping.
  https://minerals-u.e-qazyna.kz/en/contracts-map
- **Kazakhstan NSDI portal**: publicly discoverable geospatial layer catalogue; re-use licence
  and scale must be checked layer by layer. https://map.gov.kz/
- **Copernicus Sentinel-2**: freely reusable EO imagery under Sentinel notice; not a gold assay
  or a proof of mineralization. https://dataspace.copernicus.eu/
- **USGS MRDS**: public historical occurrences; coverage outside USA is incomplete, mine status
  and rights not current. Must be labelled `reference_occurrence`; no 'free land' inference.
  https://www.usgs.gov/publications/mineral-resources-data-system-mrds

## Pilot regions — no inferred licence polygons or targets
North of Almaty / Qonaev; Kalba; Kokshetau; Akbakai. They are research priorities only.
Exact polygons require source-dated scientific or project-defined geometries.

## Before launch
- Complete migration checks and CI tests; security review of map embeds and permissions.
- Get exact source packages with download/reuse rights and documented scale, CRS, date and licence.
- Review spatial registration, duplicate records and positional uncertainty with a geologist.
- Capture dated official cadastral rights + restrictions before any drilling decisions.
- Install PostGIS only if the operational stack supports it; add GIST index and spatial overlap checks.
- Trained AI classifier only after source-backed training labels and spatially blocked evaluation.


## Phase 3 — reproducible USGS pilot acquisition and **dated** cadastral overlay
Code is committed to the experimental branch; this documentation does **not** claim
that any live USGS record or national mining licence has been downloaded, loaded,
checked or independently located in Kazakhstan.

### USGS hosted ArcGIS MRDS FeatureServer
Source schema verified from the official USGS endpoint:
https://energy.usgs.gov/arcgis/rest/services/Hosted/Mineral_Resource_Data_System/FeatureServer/0
The layer exposes `objectid_1`, `dep_id`, `site_name`, `code_list` and
`dev_stat`, and advertises GeoJSON output and paginated queries. The region
`--bbox 74 42 80 46` is an approximate desktop-study envelope that includes
Qonaev and portions of Chu-Ili; it is **not** a Kazakhstan border or licence polygon.

```bash
python manage.py fetch_usgs_mrds_gold /secure/chu_ili_mrds.geojson --bbox 74 42 80 46
# Writes immutable provenance manifest chu_ili_mrds.geojson.provenance.json,
# file SHA256, retrieval timestamp and count or fails closed.
python manage.py import_gold_targets /secure/chu_ili_mrds.geojson
# Manually verify dataset rights, country placement and source record IDs
python manage.py import_gold_targets /secure/chu_ili_mrds.geojson --apply --real-records --confirm-data-rights
```

No downloaded data is committed to the repository. Source errors stop the
pipeline; a USGS error or empty source does not become invented records.
Converted points are `reference_occurrence`; even after geological reviewer
approval they have no AI score and no licence availability determination.

### Operator-acquired official Kazakhstan cadastre, not scraped
The official platform publicly displays licence reference information, but
automated bulk-export rights and a stable endpoint have not been verified.
The current importer therefore requires an **operator-obtained GeoJSON**
export with documented storage and reuse permission.

Do not manually trace polygons from a screenshot and present them as official.
The input GeoJSON must use EPSG:4326 `FeatureCollection` with
Polygon/MultiPolygon, each feature's stable official `id` or
`properties.official_id`. Optional `properties.recorded_status` must be
an explicitly sourced value from:
`unknown | licenced | application | withdrawn | expired | other`;
a recognised `expired` value is **never** interpreted as available.
`properties.official_status_text` retains source text when possible.

```bash
python manage.py import_gold_cadastre /secure/cadastre_export.geojson \
  --snapshot-date 2026-10-23 \
  --source-url https://minerals.e-qazyna.kz/en/start \
  --source-reference OFFICIAL-EXPORT-REFERENCE \
  --terms-file /secure/permissions.txt

# Only after documentary permission has been independently verified:
python manage.py import_gold_cadastre /secure/cadastre_export.geojson \
  --snapshot-date 2026-10-23 \
  --source-url https://minerals.e-qazyna.kz/en/start \
  --source-reference OFFICIAL-EXPORT-REFERENCE \
  --terms-file /secure/permissions.txt \
  --apply --confirm-permission
```

Commands above show a **template**, not a genuine obtained export or approved
permission. Import creates `GoldCadastreSnapshot` rows in `pending` state;
staff must validate every licence classification and geometry before marking
`reviewed`. This enforces separation of historical gold occurrences and
dated licensed areas, without asserting current legal availability.

### Private endpoints and displayed layers
- `/gold-intelligence/targets/`: Folium targeting map, historical gold
  references + reviewed dated cadastral snapshot outlines.
- `/gold-intelligence/targets/geojson/`: geological / reference features.
- `/gold-intelligence/targets/cadastre.geojson`: dated reviewed rights snapshots.
- Cadastral records are staff-only until assigned to a project with explicit
  membership. Unreviewed records never leave the private review workflow.
- No real known-to-be-unlicensed drill target or mineral resources are returned
  without authenticated project-specific evidence.

### Operational requirements before any public launch
1. Obtain actual archival data and check each gold feature against the source.
2. Obtain operator-approved official current cadastral export, including
   exclusions and restricted land data, not just granted licence polygons.
3. Conduct geologist and legal due diligence; classify uncertainties.
4. Run Django CI, check migrations and permissions, and obtain a reviewed PR.
5. Only then deploy. PostGIS and spatial-overlap enforcement remain unimplemented.

Tests:
```bash
python manage.py test gold_intelligence.tests_targeting_sources gold_intelligence.tests_targeting_geojson gold_intelligence.tests_targeting
```
