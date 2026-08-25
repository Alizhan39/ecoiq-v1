---
name: ecoiq-growth
description: Go-to-market work for EcoIQ — positioning, ICP definition, landing-page strategy, conversion paths, lead magnets, evidence-led case studies, email sequences, ethical CRO, and experiment design for government pilots, industrial clients, utilities, municipalities, investors, transition-finance partners, and ESG buyers. Use when writing or reviewing marketing copy, a pricing or landing page, or an outbound sequence. Not for product UI copy inside the authenticated app.
---

# EcoIQ growth

## The conversion path that already exists

Do not design a parallel funnel. What is built:

| Stage | Where | Notes |
|---|---|---|
| Public discovery | `/companies/`, `/countries/`, `/league/`, embeddable badges (`companies/embed_views.py`) | Badges are the highest-reach surface and are read as certification — see `ecoiq-impact-claims` |
| Lead capture | `/request-access/` → `leads.AccessRequest` | Already captures industry, facility type, company size, country, role, target company, sector, product interest, challenge |
| Qualification | `AccessRequest.status` + internal `notes` | Analyst-driven, not automated |
| Manual deliverable | `draft_score_summary` / `draft_risk_summary` / `draft_recommendations` / `draft_roadmap` → Investor Readiness Report | Staff previews at `/admin-report-preview/`, `/client-report-preview/` |
| Self-serve | `/products/` (`ecoiq_commerce`), Stripe checkout at `/billing/` | Tiers `explorer` / `professional` / `enterprise`, mapped to `api.APIKey` tiers |
| Profile claim | `leads.ProfileClaim` (`CLM-YYYYMMDD-XXXX`) | The "your company is already listed" motion |

The Investor Readiness Report **is** the lead magnet. It is analyst-prepared,
not generated on submit — never write copy that promises an instant report.

Enterprise plans can have `price = null`, which means "Contact Sales". Copy
must match that, not invent a number.

## ICPs — and what actually changes per ICP

Seven audiences, one product. The differences that matter are the buying
process and the proof required, not the feature list.

| ICP | Buys on | Proof they need | Blocker to design around |
|---|---|---|---|
| Government pilot (UK, KZ, SA, TR) | Mandate + budget cycle | Methodology transparency, data provenance | Procurement, not persuasion |
| Industrial operator | Cost, compliance exposure | Site-level specificity | "Is this real for a refinery like mine?" |
| Utility | Regulatory reporting burden | Auditability | Existing incumbent tooling |
| Municipality | Reporting duty + public trust | Plain-language output | Small teams, no analyst |
| Investor | Portfolio risk | Comparability across companies | Coverage gaps |
| Transition-finance partner | Deal screening | Traceable evidence chain | Needs to defend it downstream |
| ESG / climate-intelligence buyer | Data quality | Where each number came from | Vendor fatigue |

Every one of them ultimately asks the same question: *where did this number
come from?* That is why the evidence chain — not the feature list — is the
pitch. `ecoiq-evidence-audit` is the source for how to answer it.

## Ethical CRO — bound by KPI 114

Principle 114 in [`docs/governance-principles-surah-map.md`](../../../docs/governance-principles-surah-map.md)
is surfaced publicly as **Consumer Protection & Anti-Manipulation**. It binds
EcoIQ's own marketing, not only the companies EcoIQ scores. Shipping a dark
pattern would make the platform fail its own principle.

**Prohibited outright:** fake or arbitrary countdowns; invented scarcity
("3 seats left"); fabricated logos, testimonials, or case studies;
"trusted by" lists including non-customers; pre-ticked consent; roach-motel
cancellation; confirmshaming decline copy; a price that differs at checkout;
implying certification or regulatory endorsement EcoIQ does not have.

**Allowed and encouraged:** real deadlines stated plainly, genuine capacity
limits, honest defaults, one-click unsubscribe, showing the full price,
publishing the methodology, and naming what the product cannot do.

## Terminology — public copy is English-only

No Surah names, Arabic terminology, or Qur'anic references in marketing.
Approved language list: `docs/platform-overview.md` (Module 05). Details in
`ecoiq-brand`.

## Language claims

The site ships English only (`LANGUAGES` in `ecoiq/settings.py`); the
assistant supports en/ar/ru; Kazakh is a catalogue with no runtime support.
Do not put a language on a marketing page that a visitor cannot select.

## Case studies

Every claim in a case study passes `ecoiq-impact-claims`: source evidence,
metric with boundary, baseline, intervention, result, verification. A case
study without a baseline is a testimonial — label it as one. Named customers
require written permission; anonymise by sector and size otherwise.

## Experiment design

State the hypothesis, the single metric, the minimum detectable effect, and
the stop date *before* launching. Do not test anything that would ship a
prohibited pattern if it won. Report losses; a growth experiment that only
ever reports wins is not measuring anything.
