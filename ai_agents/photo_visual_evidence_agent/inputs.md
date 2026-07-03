# Photo / Visual Evidence Agent — Inputs

| Input | Description |
|---|---|
| `asset_photos` | Photos of the asset itself (boiler, compressor, tank, etc.) |
| `equipment_photos` | Close-up photos of specific components |
| `meter_photos` | Photos of meters/gauges/displays showing a reading |
| `site_videos` | Short video walk-throughs of a site or asset |
| `asset_reference` | The Asset Passport / project this imagery belongs to |
| `site_name` | Site or facility name |

## Sector-specific notes

- **Heating/boilers, utilities**: boiler house photos, flue/stack condition, insulation state
- **Manufacturing**: compressor and production line photos, visible leak points
- **Oil and gas**: flare stack and wellhead photos, visible flaring/venting
- **Mining, uranium**: tailings dam condition, haul road condition, visible dust/erosion
- **Agriculture, food processing**: irrigation equipment, storage/refrigeration condition
- **Public infrastructure**: pumping stations, substations, public building condition

## What it does NOT accept as input

- Photos with no visible connection to an EcoIQ asset/project (flagged as
  unlinked, not processed as if relevant)
- Requests to assess a written description as if it were a photo
