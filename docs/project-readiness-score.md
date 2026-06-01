# EcoIQ Project Readiness Score — Reference Document

**Version: 1.0 — June 2026**
**Audience: Internal methodology, investor briefings, API documentation**

---

## Purpose

The EcoIQ Project Readiness Score assesses how ready a transition project is for investor, development bank, or climate finance review. It is designed to answer the question development banks and climate funds ask before entering due diligence:

> *"Is this project sufficiently developed to be worth the cost of formal appraisal?"*

The score evaluates ten structured dimensions, returns a 0–100 score and tier label, and provides a prioritised list of missing documents, main blockers, and the most appropriate financing pathway.

> ⚠ **This assessment is indicative only.** It does not constitute investment advice, a credit assessment, or a guarantee of finance eligibility. Independent technical, legal, and financial due diligence is required before any capital commitment.

---

## Endpoint

| Method | URL |
|---|---|
| `POST` | `/api/projects/readiness/` |

---

## Ten Assessment Dimensions

Weights sum to exactly 1.0.

| # | Dimension | Weight | What it measures |
|---|-----------|--------|-----------------|
| 1 | **Problem clarity** | 0.12 | Is the transition problem specifically defined and quantified? Is supporting data available? |
| 2 | **Emissions baseline** | 0.12 | Is there a documented, independently verified baseline with a recognised methodology? |
| 3 | **Technical feasibility** | 0.12 | Is the technology proven? Is there a bankable feasibility study and a technical advisor? |
| 4 | **CAPEX / OPEX clarity** | 0.12 | Are cost estimates detailed and independently reviewed? Is a contingency provision included? |
| 5 | **Revenue or repayment model** | 0.12 | Is there a contracted offtake, market revenue, or confirmed grant/subsidy? Are projections documented? |
| 6 | **Governance and procurement plan** | 0.10 | Is the governance framework defined (IFC/EBRD/national)? Is the procurement plan documented? |
| 7 | **Public benefit measurement** | 0.08 | Are community benefits quantified, jobs counted, and metrics defined? |
| 8 | **Risk mitigation** | 0.10 | Is there a risk register, EIA, social assessment, and insurance plan? |
| 9 | **Evidence confidence** | 0.07 | What key documents are available? Are land rights and permits confirmed? |
| 10 | **Finance structure readiness** | 0.05 | Is a financial model available? Is the legal structure defined? Are co-financiers identified? |

---

## Scoring Formula

```
project_readiness_score =
    problem_clarity        × 0.12
  + emissions_baseline     × 0.12
  + technical_feasibility  × 0.12
  + capex_opex_clarity     × 0.12
  + revenue_model          × 0.12
  + governance_procurement × 0.10
  + public_benefit         × 0.08
  + risk_mitigation        × 0.10
  + evidence_confidence    × 0.07
  + finance_structure      × 0.05
```

All dimension scores are 0–100. Final score is 0–100.

---

## Label Tiers

| Label | Score Range | Meaning |
|-------|-------------|---------|
| **investment-ready** | 75 – 100 | Bankable. Proceed to mandate discussions and formal due diligence. |
| **advanced** | 58 – 74 | Strong foundations with addressable gaps. Estimated 6–12 months to investment-ready. |
| **developing** | 40 – 57 | Partial readiness. Project preparation support (feasibility, EIA, financial model) required. |
| **early-stage** | 0 – 39 | Foundational development work required before investor or DFI engagement. |

---

## Dimension Detail

### 1. Problem Clarity (0.12)

| Signal | Score contribution |
|--------|-------------------|
| `problem_statement = detailed` | 85 pts base |
| `problem_statement = clear` | 65 pts base |
| `problem_statement = partial` | 40 pts base |
| `problem_statement = vague` | 20 pts base |
| `problem_statement = none` | 5 pts base |
| `quantified_impact_target = true` | +10 pts |
| `baseline_problem_data = true` | +8 pts |

### 2. Emissions Baseline (0.12)

| Signal | Score contribution |
|--------|-------------------|
| `emissions_baseline_documented = false` | Max ~10 pts (methodology scaled) |
| `emissions_baseline_documented = true` | 55 pts base |
| `baseline_independently_verified = true` | +25 pts |
| Methodology: `iso_14064` | +18 pts |
| Methodology: `ghg_protocol` | +16 pts |
| Methodology: `sector_specific` | +12 pts |
| Methodology: `internal` | +6 pts |

### 3. Technical Feasibility (0.12)

| Signal | Score contribution |
|--------|-------------------|
| Technology: `operational` | 90 pts base |
| Technology: `proven` | 72 pts base |
| Technology: `pilot` | 52 pts base |
| Technology: `prototype` | 32 pts base |
| Technology: `concept` | 12 pts base |
| Feasibility study: `bankable` | +22 pts |
| Feasibility study: `standard` | +12 pts |
| Feasibility study: `preliminary` | +6 pts |
| `technical_advisor_engaged = true` | +8 pts |
| `technology_local_availability = true` | +5 pts |

### 4. CAPEX / OPEX Clarity (0.12)

| Signal | Score contribution |
|--------|-------------------|
| CAPEX: `detailed` | 80 pts base |
| CAPEX: `order_of_magnitude` | 52 pts base |
| CAPEX: `preliminary` | 28 pts base |
| CAPEX: `none` | 5 pts base |
| OPEX: `detailed` | +18 pts |
| OPEX: `order_of_magnitude` | +10 pts |
| OPEX: `preliminary` | +5 pts |
| `independent_cost_review = true` | +12 pts |
| `contingency_provision = true` | +8 pts |

### 5. Revenue or Repayment Model (0.12)

| Signal | Score contribution |
|--------|-------------------|
| Revenue: `contracted` | 88 pts base |
| Revenue: `hybrid` | 70 pts base |
| Revenue: `market` | 58 pts base |
| Revenue: `grant` | 50 pts base |
| Revenue: `none` | 5 pts base |
| `offtake_agreement = true` | +15 pts |
| `subsidy_or_grant_confirmed = true` | +10 pts |
| `revenue_projections_available = true` | +8 pts |

### 6. Governance and Procurement Plan (0.10)

| Signal | Score contribution |
|--------|-------------------|
| Framework: `IFC` or `EBRD` | 88 pts base |
| Framework: `ADB` or `World Bank` | 83 pts base |
| Framework: `EU Taxonomy` | 80 pts base |
| Framework: `GBP` | 75 pts base |
| Framework: `TCFD` | 68 pts base |
| Framework: `national` | 52 pts base |
| Framework: `none` | 18 pts base |
| `procurement_plan_documented = true` | +10 pts |
| `ownership_structure_disclosed = true` | +8 pts |
| `shareholder_agreement = true` | +5 pts |

### 7. Public Benefit Measurement (0.08)

| Signal | Score contribution |
|--------|-------------------|
| Community benefit: `high` | 80 pts base |
| Community benefit: `medium` | 55 pts base |
| Community benefit: `low` | 30 pts base |
| Community benefit: `none` | 8 pts base |
| Direct jobs (per job × 0.05, cap 12 pts) | up to +12 pts |
| `public_benefit_metrics_defined = true` | +10 pts |
| `gender_inclusion_plan = true` | +6 pts |

### 8. Risk Mitigation (0.10)

Starts from base 10.

| Signal | Score contribution |
|--------|-------------------|
| `risk_register_documented = true` | +30 pts |
| `environmental_assessment = true` | +22 pts |
| `social_risk_assessment = true` | +18 pts |
| `insurance_plan = true` | +12 pts |
| `force_majeure_coverage = true` | +8 pts |

### 9. Evidence Confidence (0.07)

| Signal | Score contribution |
|--------|-------------------|
| Evidence type: `verified` | 85 pts base |
| Evidence type: `analyst-reviewed` | 65 pts base |
| Evidence type: `ai-seeded` | 40 pts base |
| Evidence type: `model-estimate` | 20 pts base |
| Each key document present (up to 5 docs × 8 pts) | up to +40 pts |
| `legal_land_rights_confirmed = true` | +12 pts |
| `permits_in_progress = true` | +8 pts |

**Recognised key documents** (`key_documents_available` list values):
`feasibility_study` · `eia` · `business_plan` · `financial_model` · `legal_opinion` · `land_rights` · `offtake_agreement` · `permits` · `social_assessment` · `technical_report`

### 10. Finance Structure Readiness (0.05)

Starts from base 10.

| Signal | Score contribution |
|--------|-------------------|
| `financial_model_available = true` | +30 pts |
| `legal_structure_defined = true` | +22 pts |
| `co_financing_identified = true` | +18 pts |
| `development_bank_engaged = true` | +15 pts |
| `finance_instrument` specified (non-empty) | +8 pts |

---

## Output Fields

| Field | Type | Description |
|---|---|---|
| `project_readiness_score` | float 0–100 | Weighted composite across ten dimensions |
| `readiness_label` | str | `early-stage` / `developing` / `advanced` / `investment-ready` |
| `dimension_scores` | dict | All ten dimension scores (0–100) |
| `missing_documents` | list[str] | Documents expected by investors / DFIs that are absent from the project file |
| `main_blockers` | list[str] | Highest-priority structural gaps (up to 5, ordered by severity) |
| `investor_note` | str | Investor-facing narrative summary with estimated preparation timeline |
| `next_steps` | list[str] | Ordered, actionable preparation steps (up to 5) |
| `recommended_finance_route` | str | Most appropriate financing pathway given project stage and characteristics |
| `confidence` | str | Mirrors `evidence_type` input — `verified` / `analyst-reviewed` / `ai-seeded` / `model-estimate` |
| `methodology` | str | Engine version reference |

---

## Recommended Finance Routes

The engine selects a financing pathway based on `readiness_label`, `revenue_model`, `governance_framework`, `budget_usd`, and `sector`:

| Readiness | Route |
|---|---|
| `early-stage` + DFI engaged | Project Preparation Facility (IFC-MCPP, EBRD ECT, GCF Readiness) |
| `early-stage` | Technical Assistance (TA) Grant — GCF, UNDP/GEF, bilateral donor |
| `developing` + DFI + governance | Development Bank Project Preparation Facility |
| `developing` + co-financing identified | Blended Finance — project preparation stage |
| `developing` | Impact Equity + TA Grant (18–24 months to bankable) |
| `advanced` + contracted offtake + USD 50M+ | Project Finance (limited recourse) |
| `advanced` + DFI framework | Blended Finance — DFI first-loss tranche + commercial senior debt |
| `advanced` + grant confirmed | Concessional debt + grant co-financing |
| `investment-ready` + renewables + USD 100M+ + DFI | Green Bond or DFI Senior Facility |
| `investment-ready` + contracted + financial model | Project Finance — financial close ready |
| `investment-ready` (default) | Investment-grade blended finance or direct senior debt |

---

## Missing Documents Logic

The engine checks for the following documents based on project characteristics:

| Missing condition | Document flagged |
|---|---|
| No bankable feasibility study | Bankable feasibility study (AACE Class 3 or equivalent) |
| No financial model | Financial model with 20-year cash flow projections |
| No EIA in relevant sectors | Environmental and Social Impact Assessment (ESIA / EIA) |
| No emissions baseline | Quantified emissions baseline with measurement methodology |
| No land rights | Land rights documentation — title, lease, or government letter |
| No permits in progress | Permits and regulatory approvals |
| No offtake / contracted revenue | Offtake agreement or revenue framework |
| No legal opinion or structure | Independent legal opinion on project structure |
| No social assessment | Social risk and stakeholder engagement assessment |
| Ownership not disclosed | Beneficial ownership structure (UBO register or equivalent) |

---

## Calibration Reference

| Project | Score | Label |
|---|---|---|
| IFC solar 120 MW, bankable FS, contracted PPA, full EIA, financial model, all 8 key docs, analyst-reviewed | 99.5 | investment-ready |
| National framework, standard FS, proven tech, market revenue, EIA done, 3 docs, no DFI | 73.2 | advanced |
| Pilot technology, preliminary FS, grant revenue (confirmed), national gov, ai-seeded, 1 doc | 46.6 | developing |
| Agriculture concept stage, no FS, no baseline, no governance, model-estimate | 11.0 | early-stage |

---

## ML Integration Roadmap

The current implementation is rule-based and transparent. ML integration follows the same pattern as the Mizan Engine:

```python
# ML-HOOK: replace assess_project_readiness() with:
#   from joblib import load
#   clf = load('ml/models/project_readiness_clf.joblib')
#   fv  = project_readiness_feature_vector(inp)
#   scores = clf.predict([list(fv.values())])[0]   # 10 dimension scores
```

**Training data requirements:**
- IFC/EBRD project preparation facility outcomes (time from concept to financial close)
- Green Climate Fund project readiness grant assessments
- MDB project pipeline data with financial close dates by project type and country
- GCF/JETP programme preparation timelines
- Failed or stalled project files with documented blocker categories
- Successful green bond and sukuk issuance preparation histories

---

*Internal use. Contains methodology details not for public reproduction.*
*Last updated: June 2026.*
