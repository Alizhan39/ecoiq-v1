| Input | Description | Example |
|---|---|---|
| `signal_text` | Free-text description of the observed real-world signal | "High household heating costs and coal-smoke pollution across ~200 homes in the Almaty region" |
| `geography` | Region/country scope of the signal | "Kazakhstan / Almaty region" |
| `activated_lenses` | List of `{principle_id, name, mission}` for lenses that already passed the deterministic Layer 1-3 filter | `[{"principle_id": 34, "name": "Illumination & Energy Transition", ...}]` |
| `fixture_output` | (simulated/test runs only) hand-authored expected output, never invented by the adapter itself | see `test_cases.json` |
