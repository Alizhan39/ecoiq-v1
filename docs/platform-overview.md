# EcoIQ Intelligence Platform — Overview

**Version:** 1.0  
**Status:** Production  
**URL:** `/platform/`  
**Last updated:** June 2026

---

## Purpose

EcoIQ is an investor-facing ethical climate intelligence platform. It consolidates five analytical modules into a single coherent system for responsible investors, development finance institutions (DFIs), and sovereign wealth funds operating in the UK, Kazakhstan, Saudi Arabia, and Türkiye.

All outputs are AI-assisted and indicative. They require qualified analyst or professional review before use in any investment or financing decision.

---

## Market Focus

| Market | Rationale |
|--------|-----------|
| **United Kingdom** | Core home market. Strong ESG regulatory framework (FCA SDR, TCFD mandatory). Green finance hub. |
| **Kazakhstan** | High transition exposure: carbon-intensive industrial base, JETP signatory, active DFI pipeline. |
| **Saudi Arabia** | Net-Zero by 2060 commitment, Vision 2030 diversification, large institutional investor base. |
| **Türkiye** | EU Green Deal accession pressure, major industrial base, active EBRD/IFC engagement. |

---

## Five Intelligence Modules

---

### Module 01 — Country Transition Intelligence

**Public URL:** `/countries/`  
**API:** None (UI-based; API planned)

#### Purpose
National-level transition risk and opportunity mapping. Assesses the industrial and regulatory environment of a nation relative to the demands of the low-carbon economy.

#### Scored Dimensions
1. **Policy Environment** — Clarity and ambition of climate and industrial policy frameworks.
2. **Energy Infrastructure** — Renewable capacity, grid modernisation, and fossil fuel dependency.
3. **Industrial Composition** — Sector mix, emissions intensity, and transition-sensitive employment.
4. **Climate Commitments** — NDC ambition, JETP eligibility, and bilateral climate agreements.
5. **Regulatory Trajectory** — Direction and pace of environmental and financial regulation.

#### Output
- Country transition score (0–100)
- Transition risk tier (high / medium / low)
- Sector exposure breakdown
- JETP eligibility indicators
- Narrative intelligence brief

#### Disclaimer
Country intelligence outputs are indicative and AI-assisted. They are not investment advice or country ratings as defined by regulated rating agencies.

---

### Module 02 — Company EcoIQ Assessment

**Public URL:** `/companies/`  
**API:** `GET /api/v1/companies/<slug>/` (authenticated)

#### Purpose
Six-pillar scoring for industrial companies based on public evidence. Produces an EcoIQ score from 0–100 with a moral label and structured findings.

#### Six Pillars

| Pillar | Weight | Focus |
|--------|--------|-------|
| Public Benefit | 25% | Employment quality, regional development, community investment |
| Environmental Stewardship | 25% | Pollution intensity, waste, water, biodiversity |
| Responsible Modernisation | 20% | Energy transition, digitalisation, infrastructure |
| Transparent Governance | 15% | Reporting quality, audit, procurement |
| Anti-Corruption | 10% | Governance integrity, ethical procurement |
| Ethical Alignment | 5% | Long-term value, controversy management |

#### Harm Penalty
Up to −30 points applied where severe pollution, governance failures, or profit extraction without proportionate public benefit is identified.

#### Moral Labels
- **Regenerative Leader** (score ≥ 75)
- **Responsible Builder** (score ≥ 55)
- **Public Benefit Oriented** (score ≥ 42)
- **Transitional Company** (score ≥ 28)
- **Profit-First Operator** (score ≥ 15)
- **Extractive Core** (score < 15)

#### Disclaimer
Company EcoIQ scores are AI-assisted and based on publicly available evidence. They are indicative and not investment recommendations.

---

### Module 03 — Project Readiness Review

**Public URL:** `/request-access/review/?type=project_readiness`  
**API:** `POST /api/projects/readiness/`  
**Docs:** `docs/project-readiness-score.md`

#### Purpose
Ten-dimension assessment of how prepared a climate or transition project is for review by investors, DFIs, or climate finance programmes.

#### Ten Dimensions

| Dimension | Weight |
|-----------|--------|
| Problem Clarity | 12% |
| Emissions Baseline | 12% |
| Technical Feasibility | 12% |
| CAPEX / OPEX Clarity | 12% |
| Revenue Model | 12% |
| Governance & Procurement | 10% |
| Public Benefit | 8% |
| Risk Mitigation | 10% |
| Evidence Confidence | 7% |
| Finance Structure | 5% |

#### Readiness Labels
- **investment-ready** (score ≥ 75)
- **advanced** (score ≥ 58)
- **developing** (score ≥ 40)
- **early-stage** (score < 40)

#### Recommended Finance Routes
The engine maps readiness label + revenue model + sector to 11 finance routes including IFC blended finance, EBRD Early Transition Country window, Green Bond issuance, ADB co-financing, grant + DFI blending, and others.

#### API Request (minimal)
```json
POST /api/projects/readiness/
Content-Type: application/json
X-API-Key: <key>

{
  "sector": "renewables"
}
```

#### API Response (excerpt)
```json
{
  "project_readiness_score": 11.0,
  "readiness_label": "early-stage",
  "dimension_scores": { ... },
  "missing_documents": ["feasibility_study", "EIA", ...],
  "main_blockers": ["No feasibility study", ...],
  "investor_note": "...",
  "next_steps": ["Commission feasibility study", ...],
  "recommended_finance_route": "grant funding or early-stage DFI technical assistance",
  "_meta": { "disclaimer": "..." }
}
```

#### Disclaimer
Project Readiness outputs are AI-assisted and indicative. All outputs require analyst review before use in any investment or financing decision.

---

### Module 04 — Capital Integrity Score

**Public URL:** `/platform/#capital-integrity`  
**Request review:** `/request-access/review/?type=investor_readiness`  
**Docs:** `docs/capital-integrity-score.md`

#### Purpose
Assesses whether the financial structure of a company or fund aligns with responsible investment principles — including debt transparency, profit reinvestment ratios, ownership accountability, and long-term orientation.

#### Scored Dimensions
1. **Ownership Transparency** — Beneficial ownership clarity and related-party structures.
2. **Debt Structure** — Debt profile, covenants, and alignment with responsible finance norms.
3. **Profit Reinvestment** — Ratio of profit reinvested vs. extracted.
4. **Shareholder Accountability** — Board independence, minority protection, voting structure.
5. **Long-Term Orientation** — Capital allocation toward durable, transition-aligned assets.
6. **DFI Compatibility** — Alignment with IFC, EBRD, and ADB responsible finance criteria.

#### Output
- Capital Integrity Score (0–100)
- DFI compatibility rating
- Green Bond framework eligibility indicators
- Structured findings with recommended actions

#### Disclaimer
Capital Integrity outputs are AI-assisted and indicative. They do not constitute financial, legal, or investment advice. Independent professional review is required.

---

### Module 05 — Ethical Finance Fit

**Public URL:** `/platform/#ethical-finance-fit`  
**Request review:** `/request-access/review/?type=islamic_finance`  
**Docs:** `docs/islamic-ethical-finance-fit.md`

#### Purpose
Assesses the compatibility of a company, fund, or project with responsible capital frameworks emphasising ethical stewardship, public benefit, equitable value distribution, and long-term resilience.

#### Important Language Guidance
This module uses the following approved language only. **Do not use** any of the prohibited terms in public-facing content, API responses, or marketing.

| ✅ Approved | ❌ Prohibited |
|-------------|--------------|
| ethical finance fit | Shariah-compliant |
| ethical stewardship | halal / haram |
| responsible capital | fatwa |
| potentially suitable for Sharia review | religiously permissible |
| requires qualified review | religious scoring |
| ethical compatibility | faith-based scoring |
| Islamic finance fit (noun, not adjective) | Shariah score |

#### Scored Dimensions
1. **Asset Structure Alignment** — Tangible vs. speculative asset composition and leverage profile.
2. **Revenue Stream Composition** — Proportion of revenue from ethically aligned vs. excluded activities.
3. **Prohibited Activity Exposure** — Exposure to sectors or practices incompatible with ethical frameworks.
4. **Governance Stewardship** — Board quality, accountability structures, and ethical procurement.
5. **Social Impact Orientation** — Employment, community investment, and equitable value sharing.
6. **Long-Term Resilience** — Capital resilience, sustainability commitments, and transition readiness.

#### Internal Note: Maqasid Mapping
Internally, dimension weights are informed by Maqasid al-Shariah principles (life, intellect, progeny, wealth, faith). This mapping is **internal only** and must **never** appear in API responses, UI copy, or marketing materials.

#### Output
- Ethical Finance Fit score (0–100)
- Compatibility tier (high / moderate / limited / incompatible)
- Dimension-level findings
- Areas requiring qualified professional review
- Recommended next steps

#### Disclaimer
Ethical Finance Fit outputs are AI-assisted and indicative. They are **not** a determination of permissibility under any religious, legal, or regulatory framework. Any use in investment or financing decisions requires independent review by a qualified finance professional.

---

## Lead Generation — Request EcoIQ Review

**URL:** `/request-access/review/`  
**Model:** `leads.ReviewRequest`  
**Form:** `leads.ReviewRequestForm`

### Supported Review Types
| Value | Display Label |
|-------|--------------|
| `company_assessment` | Company EcoIQ Assessment |
| `country_intelligence` | Country Transition Intelligence |
| `investor_readiness` | Investor Readiness Review |
| `islamic_finance` | Islamic & Ethical Finance Fit |
| `project_readiness` | Project Readiness Review |
| `greenwashing_review` | Greenwashing Risk Review |

### Pre-selection via URL
Any review type can be pre-selected by appending `?type=<value>` to the review URL:
```
/request-access/review/?type=project_readiness
/request-access/review/?type=islamic_finance
/request-access/review/?type=greenwashing_review
```

### Optional PDF Upload
The form accepts an optional sustainability report upload (PDF, max 10 MB). Files are saved to `MEDIA_ROOT/review_reports/YYYY/MM/`.

### CTA Partial
The reusable 3-button CTA strip is available via:
```django
{% include 'partials/_review_cta.html' %}
```
Pass `calendly_url` in context to enable the Calendly booking link.

---

## API Endpoints

| Endpoint | Method | Auth | Module |
|----------|--------|------|--------|
| `GET /api/v1/companies/` | GET | API key | Company Assessment |
| `GET /api/v1/companies/<slug>/` | GET | API key | Company Assessment |
| `POST /api/projects/readiness/` | POST | API key | Project Readiness |
| `POST /api/mizan/score/` | POST | API key | Mizan Engine |

---

## Deployment Notes

- All five modules run synchronously — no Celery, Redis, or background workers required.
- File uploads are stored in `MEDIA_ROOT` (configured to Render persistent disk or equivalent).
- `CALENDLY_URL` is read from environment/settings. If not set, the Calendly button falls back to `mailto:alizhan@ecoiq.uk?subject=Investor Briefing Request`.
- `LEAD_NOTIFY_EMAIL` is read from settings to determine the team notification recipient for review requests.

---

## Disclaimers (Public-Facing Text)

The following disclaimer must appear on the platform page, individual module sections, and all email templates:

> All EcoIQ intelligence outputs — including country scores, company assessments, project readiness reviews, capital integrity scores, and ethical finance fit assessments — are AI-assisted and indicative in nature. They are derived from publicly available information and rule-based scoring models. They do not constitute investment advice, financial advice, legal advice, or any regulatory determination. EcoIQ scores should be used as one input among many in a professional due diligence process, not as a standalone basis for any investment or financing decision.
