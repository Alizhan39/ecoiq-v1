# EcoIQ Ethical Intelligence Engine — Internal Architecture Reference

**Classification: Internal / Methodology**
**Version: 1.0 — June 2026**

---

## Overview

The EcoIQ Ethical Intelligence Engine scores industrial companies across six pillars of responsible business conduct, then synthesises those pillar scores into three high-level investor lenses: Net Ethical Impact (NEI), Transition Stewardship Score (TSS), and Regenerative Value Index (RVI).

The engine operates entirely on structured data already captured in `CompanyProfile` fields. No additional data collection is required to produce ethical intelligence scores.

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│  PUBLIC API  /api/v1/companies/<slug>/ethical-intelligence/ │
│              /api/v1/countries/<slug>/ethical-intelligence/ │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  ml/ethics/ethical_score.py  ← aggregate orchestrator       │
│    calls: public_benefit, harm_reduction, justice_balance,  │
│            stewardship, evidence_confidence                  │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  ethics/scoring.py  ← three master formulas (NEI, TSS, RVI) │
│    used by: ml/ethics/ modules as underlying computation    │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│  companies/models.py  CompanyProfile                        │
│    6 pillars + 20 sub-scores + harm_penalty + moral_label   │
└─────────────────────────────────────────────────────────────┘
```

---

## Pillar Structure (Public-Facing)

| # | Pillar | Weight | Sub-scores |
|---|--------|--------|------------|
| 1 | Public Benefit | 25% | Jobs, regional development, infrastructure, national value |
| 2 | Environmental Responsibility | 25% | Waste, water, biodiversity, pollution level |
| 3 | Modernisation | 20% | Energy transition, digitalisation, infrastructure upgrade, future readiness |
| 4 | Governance & Transparency | 15% | Transparency, audit quality, procurement |
| 5 | Anti-Corruption & Accountability | 10% | Anti-corruption score |
| 6 | Ethical Alignment | 5% | Long-term stewardship, balance of interests |

**Harm Penalty** (applied after pillar aggregation): −0 to −12 pts based on pollution severity.

---

## Three Master Formulas

### NEI — Net Ethical Impact
*Does this company create more value than it destroys?*

```
NEI = Total_Benefit − (Total_Harm × 0.30)

Benefit (0-100) = equal-weighted mean of all 6 pillar scores
Harm    (0-100) = weighted composite of:
  • Pollution severity   (50% weight)
  • Controversy risk     (30% weight)
  • Governance opacity   (20% weight)
```

### TSS — Transition Stewardship Score
*Is this company actively reducing harm over time?*

```
TSS = (energy_transition + modernisation + future_readiness) / 3
    − harm_penalty × 1.5
    + improvement_bonus (if score_history shows upward trend)
```

### RVI — Regenerative Value Index
*Is this company building lasting societal value?*

```
RVI = (jobs_created + regional_development + infrastructure_contribution
      + national_value + biodiversity_impact) / 5
    + public_benefit_score × 0.20
```

---

## ml/ethics/ Module Breakdown

| Module | Responsibility |
|--------|---------------|
| `public_benefit.py` | Computes expanded public benefit composite from sub-scores |
| `harm_reduction.py` | Quantifies harm mitigation trajectory from pillar trend data |
| `justice_balance.py` | Assesses equitable value distribution across stakeholders |
| `stewardship.py` | Long-horizon stewardship signal from governance + alignment pillars |
| `evidence_confidence.py` | Data quality confidence score (0–1): verified vs. seeded profiles |
| `ethical_score.py` | Top-level orchestrator: produces full ethical intelligence payload |

---

## Terminology Rules (Public vs. Internal)

| Internal (methodology only) | Public-facing equivalent |
|-----------------------------|--------------------------|
| Maqasid al-Shariah mapping | Ethical intelligence framework |
| Hifdh al-Nafs (life protection) | Environmental & community harm reduction |
| Hifdh al-'Aql (intellect) | Transparency, evidence quality |
| Hifdh al-Mal (wealth stewardship) | Long-term financial resilience |
| Hifdh al-Nasab (community) | Public benefit, regional development |
| Hifdh al-Din (purpose) | Ethical alignment, long-term stewardship |
| Faith-based scoring | Stewardship-based allocation |
| Religious finance | Responsible finance / ethical capital |

**Do NOT expose Maqasid terminology in any public-facing surface** — API responses, UI copy, marketing materials, or documentation visible to end-users.

---

## Evidence Confidence

Profiles are assigned a confidence tier based on data origin:

| Tier | Description | Confidence |
|------|-------------|------------|
| `verified` | Company submitted and EcoIQ reviewed disclosures | 0.90–1.00 |
| `analyst-reviewed` | EcoIQ analyst used public filings | 0.70–0.89 |
| `ai-seeded` | Deterministic model from public sector/country data | 0.40–0.69 |

All API responses for seeded profiles include `"data_confidence": "ai-seeded"` and a
`"requires_verification": true` flag.

---

## Deployment Notes

- All ethical intelligence computation is **synchronous** — no Celery, no background tasks.
- Computation is **stateless** — scores are re-derived on each API call from stored pillar values.
- No calls to external services or LLMs at scoring time.
- `ANTHROPIC_API_KEY` is used only for the `/api/v1/semantic-search/` endpoint, not for scoring.

---

*This document is for internal methodology and engineering reference only. Last updated: June 2026.*
