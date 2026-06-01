# EcoIQ Islamic & Ethical Finance Fit — Reference Document

**Version: 1.0 — June 2026**
**Audience: Internal methodology, investor briefings, API documentation**

---

## Purpose

The EcoIQ Islamic & Ethical Finance Fit assessment evaluates whether a transition project may be structurally suitable for:

- **Sukuk** (Islamic capital market instruments — Ijara, Wakala, Istisna, Musharakah)
- **Islamic project finance** (Murabaha, Diminishing Musharakah)
- **Ethical finance frameworks** (Green Bond Principles, EBRD Environmental Policy, IFC Performance Standards)
- **Development-bank blended finance** (IFC, EBRD, ADB, World Bank co-investment structures)

> ⚠ **This assessment is indicative only. It does not constitute a religious ruling, Shariah determination, or certification of any kind. All Islamic finance suitability conclusions require review by a qualified Shariah scholar or accredited Shariah advisory board. EcoIQ does not issue religious opinions.**

---

## Where It Appears

| Access point | How included |
|---|---|
| `POST /api/v1/finance/islamic-fit/` | Standalone endpoint — direct project input |
| `POST /api/mizan/project/` | `islamic_finance_fit` object nested in the Mizan Engine project response |

---

## Nine Assessment Dimensions

Weights sum to exactly 1.0.

| # | Dimension | Weight | What it measures |
|---|-----------|--------|-----------------|
| 1 | **Real asset / real economy linkage** | 0.15 | Is there a specific, identifiable underlying asset? Can ownership or beneficial interest be transferred to investors? Does it generate recurring income? |
| 2 | **Public benefit** | 0.15 | Does the project create genuine societal value — jobs, community benefit, regional development, additionality? |
| 3 | **Transparency of use of proceeds** | 0.15 | Are proceeds clearly specified, ring-fenced, and subject to independent reporting? |
| 4 | **Harm reduction** | 0.12 | Does the project avoid sectors excluded by Islamic and ethical finance frameworks? Are environmental impacts actively mitigated? |
| 5 | **Avoidance of excessive uncertainty** | 0.10 | Is the project structure clear, contractually documented, and at an advanced enough stage to reduce ambiguity? |
| 6 | **Fair risk-sharing potential** | 0.10 | Can investors participate in project returns and risks through equity or profit-sharing mechanisms? |
| 7 | **Governance and accountability** | 0.10 | Is ownership disclosed? Is there independent oversight? Has a Shariah advisory board been engaged? |
| 8 | **Environmental stewardship** | 0.08 | Does the project demonstrate long-horizon custodianship — renewable energy, biodiversity, climate risk disclosure? |
| 9 | **Measurable impact** | 0.05 | Can outcomes be independently measured and verified against a quantified baseline? |

---

## Scoring Formula

```
finance_fit_score =
    real_asset_linkage        × 0.15
  + public_benefit            × 0.15
  + transparency_proceeds     × 0.15
  + harm_reduction            × 0.12
  + uncertainty_avoidance     × 0.10
  + fair_risk_sharing         × 0.10
  + governance_accountability × 0.10
  + environmental_stewardship × 0.08
  + measurable_impact         × 0.05
```

All dimension scores are 0–100. Final score is 0–100.

**Excluded sectors hard-cap** at the `weak` ceiling (37.9) regardless of other dimension scores.

---

## Label Tiers

| Label | Score Range | Meaning |
|-------|-------------|---------|
| **high-potential** | 75 – 100 | Strong structural fit across core dimensions. Recommended for Shariah advisory pre-screening and formal instrument structuring. |
| **strong** | 58 – 74 | Good fit with addressable gaps. Specific conditions should be met before engaging a Shariah advisory board. |
| **possible** | 38 – 57 | Partial structural compatibility. Key conditions — asset linkage, proceeds specificity, governance — must be strengthened first. |
| **weak** | 0 – 37 | Poor structural fit. Fundamental restructuring required before Islamic finance structuring is viable. |

---

## Dimension Detail

### 1. Real Asset / Real Economy Linkage (0.15)

Sukuk structures require a specific, identifiable underlying asset. The score increases with:

| Signal | Score contribution |
|--------|-------------------|
| `tangible_asset_linked = true` | +42 pts |
| `asset_ownership_transferable = true` | +22 pts (SPV / beneficial interest transfer) |
| `asset_generates_income = true` | +15 pts (Ijara / lease suitability) |
| Sector naturally produces tangible assets (renewables, infrastructure, water…) | +8 pts |
| Budget ≥ USD 50 million | +5 pts (scale signal) |

### 2. Public Benefit (0.15)

| Signal | Score contribution |
|--------|-------------------|
| `community_benefit = high` | 85 pts base |
| `community_benefit = medium` | 58 pts base |
| `community_benefit = low` | 30 pts base |
| `community_benefit = none` | 8 pts base |
| Direct jobs (per job × 0.06, cap 12 pts) | up to +12 pts |
| Local procurement (pct × 0.10, max 10 pts) | up to +10 pts |
| `additionality_demonstrated = true` | +8 pts |
| `community_benefit_sharing = true` | +5 pts |

### 3. Transparency of Use of Proceeds (0.15)

| Signal | Score contribution |
|--------|-------------------|
| `use_of_proceeds_specificity = specific` | 82 pts base |
| `use_of_proceeds_specificity = general` | 52 pts base |
| `use_of_proceeds_specificity = vague` | 22 pts base |
| `use_of_proceeds_specificity = none` | 5 pts base |
| `third_party_verified = true` | +14 pts |
| `ring_fenced_account = true` | +10 pts |
| `reporting_commitment = annual` | +8 pts |
| `reporting_commitment = bi-annual` | +4 pts |

### 4. Harm Reduction (0.12)

- **Excluded sectors** → dimension score = **0** (hard zero; also caps overall at `weak`)
- **Cautionary sectors** → base score drops to **18** (coal, heavy chemicals)
- All other sectors → base **55**
- `environmental_assessment = true` → +22 pts
- `pollution_mitigation_plan = true` → +14 pts
- `renewable_energy_share` → up to +10 pts (× 0.10)

### 5. Avoidance of Excessive Uncertainty (0.10)

| Project stage | Base certainty |
|---|---|
| `operational` | 90 |
| `construction` | 70 |
| `development` | 52 |
| `feasibility` | 32 |

Combined 45% with contractual clarity (high=85, standard=58, low=28) at 40%.
`performance_guarantees = true` → +12 pts.
`use_of_proceeds_specificity` adds +10 (specific) to −15 (none).

### 6. Fair Risk-Sharing (0.10)

| Structure | Score |
|---|---|
| `fixed_return_only = true` (pure conventional debt, no P&L sharing) | 20 |
| Default (no declaration) | 30 |
| `profit_loss_sharing = true` | +40 pts |
| `investor_equity_participation = true` | +20 pts |
| `community_benefit_sharing = true` | +12 pts |

### 7. Governance and Accountability (0.10)

Governance framework base score (70% weight):

| Framework | Base |
|---|---|
| IFC / EBRD | 88 |
| ADB / World Bank | 83 |
| AAOIFI | 82 |
| EU Taxonomy | 80 |
| IFSB | 80 |
| GBP / ICMA | 75 |
| National | 52 |
| None | 18 |

Additional bonuses (30% weight): `ownership_disclosed` (+12), `independent_board_oversight` (+10), `shariah_advisory_engaged` (+8, process signal only — not a ruling).

### 8. Environmental Stewardship (0.08)

- Renewable energy share × 0.55 (max 55 pts)
- `nature_positive = true` → +18 pts
- `climate_risk_disclosure = true` → +14 pts
- `biodiversity_plan = true` → +10 pts

### 9. Measurable Impact (0.05)

- Base: 10 pts
- `emission_reduction_target` → +25 pts
- `impact_measurement_plan` → +25 pts
- `baseline_data_available` → +22 pts
- `independent_verification_plan` → +15 pts

---

## Suitable Instruments

The assessment returns a list of instruments potentially suitable for the project, based on dimension scores and input characteristics. Each item uses cautious, conditional language.

| Instrument | Conditions |
|---|---|
| **Green Sukuk** (Wakala or Ijara) | Real asset ≥ 52, Proceeds transparency ≥ 45, Public benefit ≥ 40, Sector not excluded |
| **Ijara Sukuk** | Tangible asset + income-generating + ownership transferable |
| **Istisna financing** | Construction project type, early stage, Proceeds transparency ≥ 38 |
| **Murabaha facility** | Tangible asset, specific asset purchase, Proceeds ≥ 42 |
| **Musharakah / Mudarabah** | `profit_loss_sharing = true`, Public benefit ≥ 50 |
| **Diminishing Musharakah** | `investor_equity_participation = true` + tangible asset |
| **IFC / EBRD / ADB Blended Finance** | Framework = IFC/EBRD/ADB/World Bank, Public benefit ≥ 45 |
| **Green Bond** (ICMA GBP) | Proceeds transparency ≥ 58, Third-party verified, Environmental stewardship ≥ 45 |
| **Social Impact Bond / Development Finance** | Public benefit ≥ 65, Measurable impact ≥ 45 |
| **JETP Climate Finance** | Renewable share ≥ 50%, Public benefit ≥ 45 |

---

## Sukuk Potential

| Level | Conditions |
|---|---|
| `high` | Real asset ≥ 68, Proceeds ≥ 58, Governance ≥ 55, Sector not excluded |
| `moderate` | Real asset ≥ 48, Proceeds ≥ 42, Sector not excluded |
| `low` | Real asset ≥ 30, Sector not excluded |
| `none` | Sector excluded, or real asset < 30 |

---

## Blended Finance Potential

| Level | Conditions |
|---|---|
| `high` | Framework = IFC/EBRD/ADB/World Bank AND Public benefit ≥ 58 |
| `moderate` | Any recognised framework AND Public benefit ≥ 42 |
| `low` | Public benefit ≥ 35, Sector not excluded |
| `none` | Sector excluded, or no public benefit |

---

## Output Fields

| Field | Type | Description |
|---|---|---|
| `finance_fit_score` | float 0–100 | Weighted composite across nine dimensions |
| `label` | str | `weak` / `possible` / `strong` / `high-potential` |
| `dimension_scores` | dict | All nine dimension scores (0–100) |
| `suitable_instruments` | list[str] | Instruments to explore, with conditional language |
| `sukuk_potential` | str | `none` / `low` / `moderate` / `high` |
| `blended_finance_potential` | str | `none` / `low` / `moderate` / `high` |
| `required_evidence` | list[str] | What must be established before formal review |
| `structuring_notes` | list[str] | Professional structuring considerations (SPV, Istisna-to-Ijara, etc.) |
| `investor_note` | str | Investor-facing summary in cautious, professional language |
| `sharia_review_note` | str | Shariah advisory review guidance — process only, never a ruling |
| `confidence_note` | str | Always-present: indicative only, not a certification |
| `methodology` | str | Engine version reference |

---

## Sector Exclusions

The following sectors score **zero** on the Harm Reduction dimension and are **hard-capped** to the `weak` tier regardless of other dimension scores:

`tobacco` · `alcohol` · `weapons` · `arms` · `defence_controversial` · `gambling` · `adult_entertainment` · `pork` · `conventional_banking` · `speculative_trading`

The following sectors are treated as **cautionary** (Harm Reduction base = 18) and require additional scrutiny:

`coal` · `coal_mining` · `heavy_chemicals`

> Sector exclusion lists reflect criteria commonly applied by Islamic and ethical finance institutions. Individual institutions apply their own screens — EcoIQ does not define what is or is not permissible under any specific framework.

---

## Language Standards

All output fields in this module must conform to the following:

### Required language:
- "potentially suitable for Islamic finance review"
- "requires qualified Shariah scholar / advisory board review"
- "indicative only — not a religious ruling or Shariah determination"
- "may be compatible with Islamic finance principles"
- "structural indicators only"

### Prohibited language (never appear in any output):
- "Shariah-compliant"
- "halal" / "haram"
- "fatwa"
- "religiously permissible" / "forbidden"
- Any language that constitutes or implies a religious ruling or certification

---

## Shariah Advisory Note Format

Every response includes a `sharia_review_note` field. It must:
1. State what the assessment found structurally (positive or negative)
2. Explicitly disclaim that this is not a religious ruling
3. Recommend engagement with a qualified Shariah advisory board
4. Reference AAOIFI or IFSB standards where appropriate

**Example (high-potential project):**
> "This project demonstrates structural characteristics that may be compatible with Islamic finance principles — including real asset linkage, use-of-proceeds clarity, public benefit orientation, and governance transparency. These are structural indicators only, not a Shariah determination. Recommended next step: engage an AAOIFI- or IFSB-recognised Shariah advisory board for a formal pre-screening of the proposed instrument structure. This assessment is indicative only and does not constitute a religious ruling, Shariah determination, or certification of any kind."

---

## Integration with Mizan Engine

When `POST /api/mizan/project/` is called, the `islamic_finance_fit` assessment is computed automatically from the project parameters and included in the response as a nested object.

Field mapping from `ProjectInput` to `IslamicFinanceFitInput`:

| Mizan ProjectInput field | Maps to |
|---|---|
| `sector` | `sector` |
| `country` | `country` |
| `project_type` | `project_type` |
| `budget_usd` | `budget_usd` |
| `duration_years` | `duration_years` |
| `community_benefit` | `community_benefit` |
| `direct_jobs` | `direct_jobs` |
| `local_procurement_pct` | `local_procurement_pct` |
| `environmental_assessment` | `environmental_assessment` |
| `governance_framework` | `governance_framework` + inferred `contractual_clarity` + `use_of_proceeds_specificity` |
| `renewable_energy_share` | `renewable_energy_share` + `asset_generates_income` (if ≥ 50%) |
| `climate_risk_disclosure` | `climate_risk_disclosure` |
| `sector.lower() in asset-backed sectors` | `tangible_asset_linked` (inferred) |
| `governance_framework in IFC/EBRD/ADB/World Bank` | `independent_board_oversight` (inferred) |
| `community_benefit == 'high'` | `community_benefit_sharing` (inferred) |

Fields not present in `ProjectInput` default conservatively (e.g. `asset_ownership_transferable = False`, `project_stage = 'feasibility'`). Use the standalone `POST /api/v1/finance/islamic-fit/` endpoint to provide the full input set for a more precise assessment.

---

## ML Integration Roadmap

The current implementation is rule-based and transparent. ML integration follows the same pattern as the Mizan Engine:

```python
# ML-HOOK: replace assess_islamic_finance_fit() with:
#   from joblib import load
#   clf = load('ml/models/islamic_finance_fit_clf.joblib')
#   fv  = islamic_finance_feature_vector(inp)
#   scores = clf.predict([list(fv.values())])[0]   # 9 dimension scores
```

Training data requirements:
- Historical sukuk issuance outcomes with post-issuance performance data
- AAOIFI-aligned project assessments from Islamic development banks
- IDB (Islamic Development Bank) and IsDB project finance data
- Green sukuk prospectuses with Shariah board pre-screening outcomes
- Cases where sukuk structuring was rejected at advisory review, with reasons

---

## Calibration Reference

| Project | Score | Label | Sukuk | Blended |
|---|---|---|---|---|
| IFC-backed 100% solar, Saudi Arabia, full disclosure, Shariah advisory engaged | 87.3 | high-potential | high | high |
| EBRD infrastructure, Kazakhstan, 800 jobs, EIA, annual reporting | 76.2 | high-potential | high | high |
| Musharakah P&L sharing, UAE renewables, third-party verified | 77.1 | high-potential | moderate | moderate |
| Agriculture, national framework, feasibility stage | 49.2 | possible | moderate | moderate |
| No asset, vague proceeds, no governance | 23.2 | weak | none | none |
| Tobacco (excluded sector) | 37.9 | weak | none | none |

---

*Internal use. Contains methodology details not for public reproduction.*
*Last updated: June 2026.*
