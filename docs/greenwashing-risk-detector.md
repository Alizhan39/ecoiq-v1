# EcoIQ Greenwashing Risk Detector — Reference Document

**Version: 1.0 — June 2026**
**Audience: Internal methodology, investor briefings, API documentation**

---

## Purpose

The EcoIQ Greenwashing Risk Detector identifies structural signals that suggest a company, country, or project may be overstating its climate or sustainability performance relative to the independently verifiable evidence available.

It does not make definitive findings. Every output is framed as a structured signal for investor due diligence:

> *"may indicate" — "requires verification" — "based on public data only"*

The detector does not name specific acts of greenwashing. It surfaces gaps between stated claims and available evidence, and recommends targeted verification steps. It is not a legal determination and must not be presented as one.

---

## Where It Appears

The Greenwashing Risk Detector is embedded in three places:

| Endpoint | How Included |
|----------|-------------|
| `GET /api/mizan/company/<slug>/` | `greenwashing_risk` dict in the Mizan Engine response |
| `GET /api/mizan/country/<slug>/` | Aggregated `greenwashing_risk` dict across all company profiles |
| `POST /api/mizan/project/` | `greenwashing_risk` dict derived from project parameters |
| `GET /api/v1/companies/<slug>/ethical-intelligence/` | `greenwashing_risk` dict in the Ethical Intelligence response |

High or severe greenwashing risk signals are also surfaced in the `risk_flags` list of the Mizan Engine response, so they are visible to consumers who read only the top-level flags.

The **Capital Integrity Score** (`POST /api/v1/capital-integrity/`) has its own dedicated greenwashing risk dimension (weight 20%) that evaluates instrument-level label–substance alignment. That is separate from this detector, which operates at the entity level.

---

## Nine Inputs

All inputs are normalised to 0–100 (floats) unless noted.

| Input | Description | Derived From |
|-------|-------------|--------------|
| `climate_claims_strength` | Strength of stated environmental or transition claims | `energy_transition_score × 0.55 + future_readiness_score × 0.45` (company); `renewable_energy_share × 0.45 + gov_score × 0.35 + climate_disclosure × 0.15` (project) |
| `verified_emissions_data` | Degree to which emissions figures are independently verified | `is_verified → 90`; else `audit_quality_score × 0.35` (company); `EIA present → 50 + climate_disclosure → 25` (project) |
| `third_party_assurance` | Level of external certification or audit | `is_verified → 85`; else `audit_quality_score × 0.30` (company); `gov_score × 0.75` (project) |
| `transition_capex_disclosure` | Disclosed capital investment towards transition | `energy_transition × 0.55 + infrastructure_upgrade × 0.45` (company); `renewable_share × 0.60 + EIA bonus` (project) |
| `fossil_fuel_exposure` | Exposure to fossil fuels or high-carbon activities | Pollution level proxy: low→10, medium→35, high→65, severe→85; discounted by active energy transition |
| `target_quality` | Specificity and credibility of published climate targets | `future_readiness_score` (company); `evidence_confidence` score (project) |
| `evidence_confidence` | Overall data quality and profile confidence | `is_verified→92 / status=public→55 / other→35` |
| `controversy_flags` | Count of active controversy or enforcement signals (integer) | `controversy_risk_score`: <40→0, 40–59→1, 60–79→2, ≥80→3 |
| `ownership_transparency` | Transparency of ownership and governance | `mean(transparency_anti_corruption_score, procurement_transparency_score)` (company); `governance_framework` score (project) |

---

## Scoring Formula

```
greenwashing_risk_score =
    claim_evidence_gap   × 0.40    ← primary signal
  + ff_risk              × 0.25    ← sector amplifier
  + controversy_score    × 0.20    ← direct evidence of past misalignment
  + capex_gap            × 0.10    ← investment vs. ambition gap
  + ownership_opacity    × 0.05    ← verification barrier
```

### Component Definitions

**Claim-evidence gap (40% weight):**
```
evidence_composite = verified_emissions_data × 0.30
                   + third_party_assurance   × 0.30
                   + target_quality          × 0.25
                   + evidence_confidence     × 0.15

claim_evidence_gap = max(0, climate_claims_strength − evidence_composite)
```
This is the core greenwashing signal: strong environmental claims unsupported by verification evidence.

**Fossil fuel risk (25% weight):**
```
ff_risk = (fossil_fuel_exposure / 100) × (climate_claims_strength / 100) × 100
```
High fossil fuel exposure combined with high green claims is the canonical greenwashing pattern (e.g. coal company claiming carbon neutrality).

**Controversy score (20% weight):**
```
controversy_score = min(controversy_flags × 25, 100)
```
Each verified controversy flag is treated as direct evidence that stated performance may not match actual performance.

**Capex gap (10% weight):**
```
capex_gap = max(0, climate_claims_strength − transition_capex_disclosure)
```
Claiming transition ambition without disclosing investment to back it up.

**Ownership opacity (5% weight):**
```
ownership_opacity = max(0, 70 − ownership_transparency)
```
Opaque governance structures make independent verification structurally impossible.

---

## Risk Level Tiers

| Risk Level | Score Range | Meaning |
|-----------|-------------|---------|
| **Low** | 0 – 29 | Limited indicators based on available public data. Standard due diligence applies. Monitoring recommended. |
| **Medium** | 30 – 49 | Moderate indicators. Specific gaps in evidence require follow-up. Not suitable for responsible finance labelling without further verification. |
| **High** | 50 – 69 | Significant indicators. Independent verification urgently recommended before capital allocation. |
| **Severe** | 70 – 100 | Material indicators across multiple dimensions. Capital commitment not recommended without a comprehensive independent audit of all environmental claims. |

---

## Output Fields

Every Greenwashing Risk assessment returns:

| Field | Type | Description |
|-------|------|-------------|
| `greenwashing_risk_score` | float 0–100 | Composite risk score (higher = more risk indicators) |
| `risk_level` | str | `low` / `medium` / `high` / `severe` |
| `main_red_flags` | list[str] | Specific signals detected, in cautious language |
| `missing_evidence` | list[str] | Key verification items absent from available data |
| `explanation` | str | Human-readable narrative with "may indicate" framing |
| `investor_warning` | str | Capital-allocation-focused risk statement |
| `recommended_due_diligence` | list[str] | Targeted verification steps |
| `confidence_note` | str | Always-present caveat: public data only, not a legal finding |

---

## Language Standards

Every output field must use the following language principles. Violations in code or communications are a compliance failure.

### Required:
- "may indicate" — not "proves" or "confirms"
- "public-data-based" — not "factual" or "verified"
- "requires verification" — not "is fraudulent" or "is misleading"
- "signals" or "indicators" — not "evidence" or "findings"

### Prohibited:
- Naming specific greenwashing acts as confirmed fact
- Implying regulatory violation without regulatory source
- Using language that could be defamatory under UK, EU, or Kazakhstan law
- Presenting scores as investment advice or legal determinations

---

## Red Flag Logic

The following conditions generate specific red flags:

| Condition | Red Flag Generated |
|-----------|-------------------|
| `claim_evidence_gap ≥ 40` | Large gap between stated climate ambition and verification evidence — may indicate claims are not fully substantiated |
| `claim_evidence_gap ≥ 20` | Moderate gap — requires third-party assurance to confirm accuracy |
| `fossil_fuel_exposure ≥ 60` AND `climate_claims_strength ≥ 55` | High fossil fuel exposure alongside strong green claims — transition credibility requires verification |
| `controversy_flags ≥ 2` | Multiple controversy signals — indicators of potential misalignment |
| `controversy_flags == 1` | Controversy signal — warrants review of stated commitments |
| `capex_gap ≥ 45` AND `climate_claims_strength ≥ 50` | Transition investment disclosure low relative to climate claims |
| `third_party_assurance < 20` AND `climate_claims_strength ≥ 50` | No external verification for entities making climate claims |
| `ownership_transparency < 35` | Low ownership transparency — opaque structures limit assessment |
| `target_quality < 25` AND `climate_claims_strength ≥ 50` | Climate targets appear vague relative to the strength of claims |

---

## Integration with Mizan Engine

High or severe greenwashing risk signals are also surfaced in the Mizan Engine `risk_flags` list using the following format:

```
"Greenwashing risk indicators: high (score 61/100, public-data based) —
 independent verification of climate claims required"
```

This ensures they are visible to API consumers who read only the top-level response rather than the nested `greenwashing_risk` object.

**Country aggregation:** The `/api/mizan/country/<slug>/` endpoint returns:
```json
{
  "greenwashing_risk": {
    "greenwashing_risk_score":   42.3,
    "risk_level":                "medium",
    "high_or_severe_count":      12,
    "high_or_severe_pct":        28.6,
    "risk_level_distribution":   {"medium": 22, "high": 10, "low": 8, "severe": 2},
    "confidence_note":           "..."
  }
}
```

---

## ML Integration Roadmap

The current implementation is fully rule-based and transparent. ML integration follows the same pattern as the Mizan Engine:

```python
# ML-HOOK: replace assess_greenwashing_risk() with:
#   from joblib import load
#   clf = load('ml/models/greenwashing_clf.joblib')
#   fv  = [inp.climate_claims_strength, inp.verified_emissions_data,
#           inp.third_party_assurance, inp.transition_capex_disclosure,
#           inp.fossil_fuel_exposure, inp.target_quality,
#           inp.evidence_confidence, inp.controversy_flags,
#           inp.ownership_transparency]
#   score = clf.predict([fv])[0]  # float 0-100
```

Training data requirements:
- Labelled greenwashing enforcement cases (SEC, FCA, BaFin, EU Taxonomy enforcement)
- CBI certification data with verified vs. rejected bond applications
- Historical company ESG scores cross-referenced with regulatory findings
- Emissions data discrepancy datasets (reported vs. satellite-derived)

---

## Differentiation from Capital Integrity Score

| | Greenwashing Risk Detector | Capital Integrity Score (CIS) |
|---|---|---|
| **Unit of analysis** | Company, country, project | Financing instrument / transaction |
| **Primary question** | Does the entity overstate climate performance? | Does the capital instrument deliver genuine public benefit? |
| **Greenwashing dimension** | Full assessment, 5-component formula | One of 7 CIS dimensions (weight 20%) |
| **Output scope** | Risk signal only | Full instrument integrity rating + responsible finance eligibility |
| **Integration** | Embedded in Mizan + Ethical Intelligence responses | Standalone `POST /api/v1/capital-integrity/` endpoint |

---

## Confidentiality and Use

- Results must be presented with the `confidence_note` caveat in all investor-facing materials
- Scores are public-data based and indicative only
- Not a substitute for an independent Environmental, Social, and Governance (ESG) audit
- Not investment advice
- Not a regulatory or legal determination

*Internal use. Contains methodology details not for public reproduction.*
*Last updated: June 2026.*
