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
