# EcoIQ Mizan Engine — Internal Reference

**Classification: Internal / Methodology**
**Version: 1.0 — June 2026**

---

## What Is the Mizan Engine?

**Mizan** (Arabic: مِيزَان) means balance, scales, or a just measure. The metaphor is ancient and
cross-cultural — appearing in the traditions of justice, philosophy, and governance across
civilisations. The scale that weighs equitably. The measure that neither overcounts nor undercounts.

EcoIQ's Mizan Engine adopts this principle as its governing metaphor:
**a company's climate transition must be weighed across multiple dimensions, not reduced to a single carbon number.**

The engine evaluates whether a company's transition activity:
- Creates genuine public benefit — or merely private gain
- Reduces measurable harm — or displaces it
- Distributes value fairly — or concentrates it
- Is transparent and evidence-backed — or asserted without proof
- Reflects long-term stewardship — or short-term optimisation

---

## The Six Dimensions

### 1. Public Benefit
*Does the company create value for society, not just shareholders?*

EcoIQ measures jobs quality, regional development contribution, infrastructure investment,
and national value creation. A company that extracts wealth from a region without reinvesting
scores poorly even if it meets emissions targets.

Computed from: `public_benefit_score`, `jobs_created_score`, `regional_development_score`,
`infrastructure_contribution_score`, `national_value_score`.

### 2. Harm Reduction
*Is the company actively reducing the harm it causes?*

Pollution level, controversy risk, and energy transition trajectory are combined into a
net harm score. A company with severe pollution that is genuinely decarbonising scores
better than one that is static at medium pollution.

Computed from: `pollution_level`, `controversy_risk_score`, `energy_transition_score`,
`harm_penalty`.

### 3. Justice & Fair Distribution
*Is value distributed equitably across stakeholders?*

Governance quality, procurement transparency, audit quality, and anti-corruption scores
are combined to assess whether the company's stated commitments match its actual conduct.
A high-governance-claim company with high controversy risk scores a balance gap penalty.

Computed from: `transparency_anti_corruption_score`, `audit_quality_score`,
`procurement_transparency_score`, `anti_corruption_score`, `controversy_risk_score`.

### 4. Transparency & Accountability
*Is the company honest about its performance and challenges?*

This dimension is captured within the Justice & Fair Distribution module and the
Evidence Confidence module. It rewards companies that disclose comprehensively and
penalises those whose disclosures are incomplete, inconsistent, or contradicted by
external evidence.

### 5. Stewardship & Long-Term Responsibility
*Is the company building something that will last?*

Future readiness, modernisation investment, water and biodiversity care, and ethical
alignment combine to assess long-term stewardship orientation. A company optimising
today at the cost of tomorrow's natural or social capital scores poorly on stewardship.

Computed from: `future_readiness_score`, `energy_transition_score`,
`digitalization_score`, `water_impact_score`, `biodiversity_impact_score`,
`ethical_alignment_score`.

### 6. Evidence Confidence
*How reliable is this profile's data?*

EcoIQ distinguishes between verified profiles (company-submitted and analyst-reviewed),
AI-seeded profiles (deterministic scoring from public sector/country data), and draft
profiles. Confidence is returned as a score (0.0–1.0) and a tier label, and is included
in every API response.

Computed from: `profile.status`, `is_verified`, `ai_summary` content inspection.

---

## Three Aggregate Lenses (from ethics/scoring.py)

The Mizan Engine feeds into three investor-grade composite signals:

| Lens | Formula | Question |
|------|---------|---------|
| NEI — Net Ethical Impact | `Benefit − (Harm × 0.30)` | Does this company create more than it destroys? |
| TSS — Transition Stewardship Score | `(energy_transition + modernisation + future) / 3 − penalty` | Is it actively reducing harm? |
| RVI — Regenerative Value Index | `(jobs + regional + infra + natval + biodiv) / 5 + pb × 0.20` | Is it building lasting societal value? |

---

## Compatibility With Ethical Finance Frameworks

The Mizan Engine's six dimensions are deliberately aligned with the foundational
principles shared across multiple ethical finance traditions. This is not accidental:
responsible capital allocation requires the same things regardless of tradition —
transparency, harm reduction, fair distribution of benefit, and long-term stewardship.

### Alignment With Islamic Finance Principles

For Islamic finance audiences and institutions (development banks, sovereign wealth funds,
and family offices operating within Shariah-compliant frameworks), EcoIQ's Mizan Engine
provides a structured, evidence-based evaluation that maps naturally to core principles:

| EcoIQ Mizan Dimension | Alignment With Islamic Finance Principle |
|------------------------|------------------------------------------|
| Public Benefit | Maslaha (public interest); companies must serve a genuine societal purpose |
| Harm Reduction | Avoidance of darar (harm); transactions must not cause net harm to people or nature |
| Justice & Fair Distribution | Adl (justice); equitable distribution of value across stakeholders |
| Transparency & Accountability | Amanah (trustworthiness); honest disclosure and accountability |
| Stewardship & Long-Term Responsibility | Khalifah (stewardship); responsible custodianship of resources |
| Evidence Confidence | Ilm (knowledge); decisions must be based on verified evidence, not speculation |

**Maqasid al-Shariah mapping** (for internal methodology documentation only):

| Maqasid | EcoIQ Signal |
|---------|-------------|
| Hifdh al-Nafs (life) | Environmental harm, pollution level, biodiversity |
| Hifdh al-'Aql (intellect) | Evidence quality, transparency, disclosure completeness |
| Hifdh al-Mal (wealth) | Fair value distribution, governance, anti-corruption |
| Hifdh al-Nasab (lineage/community) | Jobs, regional development, public benefit |
| Hifdh al-Din (purpose/values) | Ethical alignment, long-term stewardship |

> **Critical Rule**: This Maqasid mapping is for internal methodology and investor briefings only.
> It must NEVER appear in public-facing copy, API responses, UI text, or marketing materials.
> Public-facing language must use: justice, balance, stewardship, public benefit, evidence confidence,
> harm reduction, responsible finance.

### Alignment With Other Ethical Finance Frameworks

| Framework | EcoIQ Mizan Alignment |
|-----------|----------------------|
| IFC Performance Standards | Harm reduction, environmental stewardship, community benefit |
| EBRD Environmental Policy | Pollution control, governance quality, evidence confidence |
| UN Sustainable Development Goals | Public benefit, fair distribution, long-term stewardship |
| EU Taxonomy (Environmental Objectives) | Harm reduction, energy transition, environmental care |
| Green Bond Principles | Evidence confidence, transparency, measurable benefit |
| JETP Country Partnerships | Transition stewardship, sectoral modernisation score |

---

## Public-Facing Language Rules

The following table defines the approved public language mapping:

| Internal Concept | Approved Public Language |
|-----------------|--------------------------|
| Mizan Engine | Ethical Balance Engine / Mizan Engine |
| Maqasid framework | Ethical intelligence framework |
| Hifdh al-Nafs | Environmental & community harm reduction |
| Khalifah | Long-term stewardship |
| Adl | Justice & fair distribution |
| Amanah | Transparency & accountability |
| Religious scoring | Stewardship-based scoring |
| Faith-based finance | Responsible finance / ethical capital |
| Shariah compliance | Ethical finance alignment |
| Islamic finance ready | Compatible with ethical finance frameworks |

### What NOT to say publicly:
- ❌ "Built for Shariah compliance"
- ❌ "Qur'anic principles underpin our scoring"
- ❌ "EcoIQ is Islamic finance software"
- ❌ Any reference to fatwa, halal, haram, or specific religious rulings

### What TO say publicly:
- ✅ "The Mizan Engine evaluates balance, public benefit, and stewardship"
- ✅ "Compatible with ethical finance frameworks including responsible investment and development finance"
- ✅ "Built for development banks, ESG teams, and long-horizon stewardship investors"
- ✅ "Designed for capital frameworks that prioritise long-term public benefit over short-term extraction"

---

## API Design Rules

The Mizan Engine powers the following endpoints:

```
GET /api/v1/companies/<slug>/ethical-intelligence/
GET /api/v1/countries/<slug>/ethical-intelligence/
GET /api/v1/intelligence/ethical-score/?company=<slug>
```

**Do NOT create endpoints named:**
- `/api/v1/maqasid/`
- `/api/v1/shariah-score/`
- `/api/v1/halal-finance/`
- `/api/v1/islam/`

**Endpoint response naming conventions:**
- Use `ethical_intelligence`, `public_benefit`, `harm_reduction`, `stewardship`
- Do not use Arabic terms in JSON field names
- `confidence_tier` values: `verified`, `analyst-reviewed`, `ai-seeded`, `draft`

---

## Deployment Notes

- Mizan Engine computation is fully synchronous — no async tasks, no external API calls
- All six dimension scores are derived from existing `CompanyProfile` field values
- Confidence scoring inspects `ai_summary` text for placeholder markers
- Country-level aggregation loops over all public profiles — cache results if latency is a concern
- The `docs/` folder is internal; it is not served by Django and is not publicly accessible

---

*This document is for internal methodology, investor briefings, and engineering reference only.
It contains terminology and mappings that must not be reproduced in public-facing surfaces.*
*Last updated: June 2026.*
