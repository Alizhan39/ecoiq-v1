# Asset Passport Agent — Inputs

| Input | Description |
|---|---|
| `asset_name` | Name/identifier of the asset |
| `location` | Site/location |
| `owner` | Owning company or municipality |
| `evidence` | Combined bundle from Document Reader Agent extractions |
| `photos` | Combined bundle from Photo/Visual Evidence Agent findings |
| `bills` | Energy/fuel/water bill extractions |
| `inspection_notes` | Inspection report extractions |

## Sector-specific asset examples

Boiler house (heating/boilers), compressor system (manufacturing), wellhead
or flare stack (oil and gas), mine haul truck or tailings dam (mining,
uranium), processing line (food processing), irrigation pump (agriculture),
public building or pumping station (public infrastructure), substation
(utilities).

## What it does NOT accept as input

- An asset with no owner/location context at all (insufficient to create a
  meaningful passport — flagged as blocked, not fabricated)
