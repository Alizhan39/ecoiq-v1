# AI Gold Targeting System — MVP v0.1

**Status: experimental, evidence-gated desktop screening.** Integrated as a pure Python service in EcoIQ's existing `gold_intelligence` app, not yet an API or live map.

## What it does
- Accepts independently reviewed, normalized target evidence for host rock, structures, geochemistry, geophysics and alteration.
- Records source, document reference, observation date and methodology for every supplied value.
- Provides a 0–100 **expert-weighted screening index only when all five features are supplied**. Missing inputs stay `null`; the system never invents a 50/100 baseline or a probability of gold.
- Makes missing data, rights status and human-review gates explicit.
- Never authorizes drilling or claims licence availability, mineral reserves, grades, or discovery.

## Input
```python
from gold_intelligence.services.gold_targeting import evaluate_target
result = evaluate_target({
    "id": "KZ-PILOT-001",
    "name": "Example target (illustrative only)",
    "rights_status": "unknown",
    "evidence": {
        "host_rock_favourability": {
            "value": 0.7,
            "source": "reviewed geological map",
            "reference": "map-sheet-and-page",
            "observed_at": "2026-10-01",
            "method": "documented geologist normalization"
        }
    }
})
assert result["score"] is None  # other 4 features missing
```

## Recommended data ingestion next
1. Licensed Kazakhstan geological map packages and historical reports, preserving CRS, scale, date and source licence.
2. Public satellite scenes (Sentinel-2 / Landsat) for alteration hypotheses, atmospheric corrections and ground validation.
3. Documented geological structures and reliable geophysics / geochemistry; never infer gold presence from image colour alone.
4. Cadastral lease and protected-area snapshots, always source-dated. `unknown` must not become `confirmed_available` automatically.
5. Geologist labels and *spatially blocked* validation before any trained ML ranking is claimed.

## Planned next work
- GeoJSON/PostGIS target records with coordinate reference systems, polygons and source footprints
- Django access-controlled read-only API and React / map-layer integration
- Public sector pilot: Kalba, Kokshetau, Akbakai and northern Almaty / Qonaev desk study
- Calibrate feature normalization regionally; bias and uncertainty audits
- Human-signed decision record and explicit no-go if legal, environmental or land-access approvals fail

Run tests:
```bash
python -m unittest gold_intelligence.tests_targeting
```
