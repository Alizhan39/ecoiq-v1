# EcoIQ Platform Maturity Roadmap
## From Intelligence Prototype to Global Ethical Industrial Intelligence Infrastructure

*Internal strategic document — not for public distribution*
*Classification: Founder / Strategic*

---

## Current Maturity Stage: **Institutional Intelligence Prototype**

### Where We Are Today (v1.0 — May 2026)

EcoIQ has successfully established the foundation of a world-class ethical industrial intelligence platform. The current system represents a mature prototype — not an MVP, but a fully operational intelligence product with institutional-grade UX, scoring depth, and data richness.

**What exists today:**
- **38 company intelligence profiles** across global industrial sectors — Oil & Gas, Technology, Energy, Semiconductors, Automotive, Consumer Goods, Finance
- **11 country intelligence pages** — UK, USA, Germany, France, South Korea, China, Saudi Arabia, Kazakhstan, UAE, Denmark, Turkey
- **6-pillar EcoIQ scoring architecture** (Public Benefit 25%, Environmental Stewardship 25%, Responsible Modernization 20%, Transparent Governance 15%, Anti-Corruption 10%, Ethical Alignment 5%) with Harm Penalty (0–30 pts)
- **Bloomberg × Palantir institutional UX** — dark glassmorphism, animated score rings, harm signal matrices, financing eligibility cards, AI confidence indicators
- **Harm Signal Matrix** — 5-vector hidden harm detection (pollution severity, controversy risk, transparency deficit, profit extraction, transition gap)
- **Development Bank Compatibility Engine** — IFC, EBRD, ADB, AIIB, GCF eligibility assessment per country
- **AI intelligence layer** — overview, transition narrative, risk summary, investment thesis per company and country
- **Financing Eligibility Engine** — Green Bond, ESG Fund, IFC/EBRD, Climate Finance, Just Transition per company
- **Path to 100 roadmap** — per-company improvement timeline

**Technology stack:**
- Django 5.2 + Python 3.11
- SQLite (dev) / PostgreSQL (Render prod)
- Anthropic Claude API (`claude-opus-4-5`)
- Render deployment (web service + auto-deploy)
- Wagtail CMS (editorial layer, in progress)

---

## Platform Maturity Scale

| Stage | Description | EcoIQ Status |
|-------|-------------|--------------|
| 1 — Prototype | Proof of concept, no real data | ✅ Completed Q1 2026 |
| 2 — Intelligence Prototype | Real scoring, AI content, institutional UX | ✅ **Current** |
| 3 — Data-Rich Platform | Automated data ingestion, 500+ companies | 🔄 In Progress (Q3 2026) |
| 4 — Verified Intelligence | Company-verified profiles, sourced citations | 📋 Q4 2026 |
| 5 — Institutional Product | B2B subscriptions, API, institutional clients | 📋 H1 2027 |
| 6 — Market Standard | Regulatory citations, index inclusion, sovereign use | 📋 2028+ |

---

## Phase Roadmap

### Phase 1 — Foundation ✅ (Q1 2026 — Complete)
*20 global companies, 5-pillar scoring, basic UX, Bloomberg dark theme leaderboard*

**Delivered:**
- League leaderboard (20 companies)
- `league.Company` model with 5-pillar scores
- `companies.CompanyProfile` model with 6-pillar + harm penalty
- Admin interface for data management
- Render deployment pipeline
- Seed commands (idempotent)

---

### Phase 2 — Intelligence Expansion ✅ (Q2 2026 — Complete)
*8 new companies, 10 country intelligence pages, strategic roadmap*

**Delivered:**
- 8 Phase 2 companies: NVIDIA, Siemens, Samsung, CATL, BYD, EDF, Schneider Electric, Ørsted
- 10 country intelligence profiles
- `countries.CountryProfile` model
- Country directory + detail pages (Phase 1 UX)
- Navigation integration across all templates
- `ROADMAP.md` strategic document
- `build.sh` deployment automation

---

### Phase 3 — Platform Polish ✅ (Q2 2026 — Complete)
*Bloomberg × Palantir institutional UX, intelligence depth, harm detection, Turkey added*

**Delivered:**
- Complete company detail page redesign (Bloomberg/Palantir aesthetic)
- Animated SVG score rings (cubic-bezier animation)
- Harm Signal Matrix (5-vector hidden harm detection)
- Financing Eligibility Engine (5 product types)
- AI Confidence Score (0–100 data completeness indicator)
- 6-pillar animated score grid with sub-score drill-down
- Path-to-100 CSS timeline
- Complete country detail page redesign (macro intelligence hub)
- Energy Mix Analysis visualization
- Corruption Exposure Indicator
- Development Bank Compatibility Engine
- AI Intelligence panels with confidence pills
- Turkey country profile added (11th country)
- `_get_harm_signals()`, `_get_ai_confidence()`, `_get_financing_eligibility()` helpers
- `_get_dev_bank_compat()`, `_get_country_ai_confidence()`, `_get_corruption_exposure()` helpers

---

### Phase 4 — Data Ingestion Pipeline (Q3 2026)
*Automated data enrichment, 200+ companies, structured source tracking*

**Objectives:**
1. **Automated data ingestion** — Forbes Global 2000, SEC EDGAR, Bloomberg Open Data, Annual Reports
2. **Citation tracking** — structured source model, auto-linked citations per intelligence field
3. **Score update pipeline** — scheduled score recalculation from new data
4. **Company expansion** — 50 new companies across priority sectors
5. **Sector intelligence pages** — sector-level aggregation (Steel, Energy, Technology, etc.)

**Technical plan:**
```python
# New models needed
class DataIngestionJob(models.Model):
    company = ForeignKey(Company)
    source_url = URLField()
    source_type = CharField(choices=['sec_filing', 'annual_report', 'news', 'esg_report'])
    raw_content = TextField()
    processed_at = DateTimeField()
    quality_score = FloatField()

class ScoreUpdate(models.Model):
    profile = ForeignKey(CompanyProfile)
    field_name = CharField()
    old_value = FloatField()
    new_value = FloatField()
    evidence = TextField()
    source = ForeignKey(DataIngestionJob)
```

**Priority data sources:**
- SEC EDGAR (10-K, sustainability reports) — US companies
- UK Companies House — UK companies
- Refinitiv ESG API (if budget available)
- Annual report PDF parsing via Claude API
- News sentiment analysis for controversy risk scoring

---

### Phase 5 — Verification Layer (Q4 2026)
*Company-verified profiles, institutional credibility, legal framework*

**Objectives:**
1. **Verified Profile Programme** — companies pay to verify/claim their EcoIQ profile
2. **Evidence quality scoring** — weight each score component by source quality
3. **Contradiction detection** — flag when AI analysis conflicts with cited data
4. **Methodology portal** — public explanation of every scoring dimension
5. **Wagtail editorial layer** — analyst-published intelligence reports

**Verified Profile Tiers:**

| Tier | Features | Indicative Price |
|------|----------|-----------------|
| Basic Claim | Correct factual errors, add official sources | £400/yr |
| Verified | Full data submission, verified badge, priority listing | £1,200/yr |
| Intelligence Partner | Collaborative scoring, co-published reports, API access | £4,800/yr |

**Wagtail CMS Plan:**
- `IntelligenceReport` page type (analyst-written deep dives)
- `MethodologyPage` (scoring explanation portal)
- `DataUpdatePage` (score change log with evidence)
- `CompanyClaimRequest` workflow (admin-managed verification)

---

### Phase 6 — Institutional B2B (H1 2027)
*Subscription intelligence product, API access, institutional deployment*

**Product Architecture:**

#### EcoIQ Intelligence API
```
GET /api/v1/companies/{slug}/profile
GET /api/v1/companies/{slug}/scores
GET /api/v1/companies/{slug}/harm-signals
GET /api/v1/countries/{slug}/intelligence
GET /api/v1/sectors/{slug}/aggregate
GET /api/v1/search?q=&sector=&country=&min_score=&max_score=
GET /api/v1/leaderboard?top=100&sector=
```

**Pricing Architecture:**

| Plan | Target | Includes | Price |
|------|--------|----------|-------|
| Explorer | Analysts, researchers | 100 API calls/day, all public data | £199/mo |
| Professional | Fund analysts, ESG officers | 2,000 calls/day, bulk export, Slack integration | £599/mo |
| Enterprise | Asset managers, banks | Unlimited, dedicated data, custom sectors | £2,500/mo |
| Institutional | DFIs, sovereign wealth | Custom, white-label, data room access | £12,000–60,000/yr |

**Technical requirements for Phase 6:**
- Django REST Framework API layer
- API key authentication + rate limiting
- Webhook notifications for score changes
- Bulk CSV/Excel export
- Scheduled intelligence reports (email delivery)
- White-label deployment option

---

### Phase 7 — Government & Regulatory Intelligence (2028)
*Sovereign-grade data, regulatory compliance, policy intelligence*

**Target clients:**
- Development finance institutions (EBRD, ADB, IFC, AfDB)
- Sovereign wealth funds (PIF, Mubadala, GIC, Temasek)
- Central banks and financial regulators
- Ministry of Finance / Economy intelligence units
- International climate funds (GCF, CTCN, GEF)

**Product extensions:**
1. **Regulatory Readiness Reports** — How prepared is Company X for CSRD, TCFD, ISSB?
2. **Country Sovereign Briefings** — Full intelligence packages for bilateral investment
3. **Sector-Level Intelligence** — Country × Sector matrix (Steel in Turkey, EVs in China, etc.)
4. **Just Transition Analytics** — Employment impact, community vulnerability per asset
5. **Portfolio Screen** — Bulk screening of investment portfolios against EcoIQ scores

---

## AI Video Roadmap

### Current State
Each company profile in the seed data contains a `guidance_video` with:
- `title` — video concept
- `script_text` — narration script (AI-generated)
- `status: 'script_generated'`

### Phase 1 Video (Q3 2026): AI Narration
Generate audio narrations from scripts using:
- **ElevenLabs** or **Azure Neural TTS** for professional narration voice
- Output: MP3 audio + text transcript per company
- Embed as audio intelligence briefings on company pages

### Phase 2 Video (Q4 2026): Visual + Narration
Using video generation APIs:
- **Higgsfield.ai** — for industrial transition visual sequences
- **Runway ML** — for B-roll footage generation
- **Pika** — for animated data visualisation sequences

**Storyboard architecture per company video:**

```json
{
  "company": "Ørsted",
  "duration_seconds": 90,
  "segments": [
    {
      "time": "0-15s",
      "type": "opening",
      "visual_prompt": "Aerial drone shot of offshore wind farm at dawn, steel towers rising from ocean, golden light",
      "narration": "In 2012, Ørsted was DONG Energy — Denmark's most coal-intensive utility...",
      "data_overlay": {"metric": "EcoIQ Score", "value": "85.0", "animation": "count_up"}
    },
    {
      "time": "15-45s",
      "type": "transformation",
      "visual_prompt": "Time-lapse of offshore wind installation, engineers working on turbine nacelle",
      "narration": "Over the next decade, the company divested its oil and gas assets entirely...",
      "data_overlay": {"metric": "Renewable Share", "value": "100%", "animation": "bar_fill"}
    }
  ]
}
```

### Phase 3 Video (H1 2027): Cinematic Intelligence
Full production pipeline:
- Per-company 3–5 minute cinematic intelligence report
- Branded EcoIQ visual identity (glassmorphism UI overlays)
- Distribution: company profile pages, LinkedIn, investor portals
- Subscription gating: full videos for Enterprise+ subscribers

---

## Data Moat Strategy

### What Creates Defensibility

EcoIQ's competitive moat is not the data itself (which is public) but the **intelligence layer**:

1. **Proprietary Scoring Methodology** — The 6-pillar + harm penalty formula, calibrated across 38+ companies globally with consistent methodology, cannot be replicated quickly
2. **Intelligence Depth** — AI-generated synthesis that integrates quantitative scores with narrative analysis, transition roadmaps, and financing eligibility
3. **Cross-referenced dataset** — Company × Country × Sector × Development Bank compatibility matrix
4. **Institutional trust** — Verified profiles, cited sources, AI confidence scoring build credibility that accretes over time
5. **Transition intelligence** — Dynamic scoring that tracks companies moving through transition stages (the only platform tracking company improvement trajectories)
6. **Ethical intelligence layer** — Harm signals, corruption exposure, profit extraction indicators not available in standard ESG products

### Data Moat Deepening Over Time

**Year 1 (2026):** Manual + AI-seeded data, 38–100 companies
→ Moat: methodology depth, UX quality, AI intelligence layer

**Year 2 (2027):** Automated ingestion, 500+ companies, verified profiles
→ Moat: coverage breadth, citation database, company relationships

**Year 3 (2028):** Regulatory citations, institutional API clients, DFI partnerships
→ Moat: institutional credibility, network effects from citations in policy documents

**Year 5 (2030):** Market standard reference, index inclusion discussions, sovereign use
→ Moat: ecosystem lock-in, historical time series data, brand authority

---

## Enterprise Roadmap

### Target Enterprise Clients (2027)

**Asset Managers:**
- Emerging market ESG funds needing granular company-level scores
- Infrastructure debt funds (transition finance due diligence)
- Sovereign wealth fund ethical screening

**Investment Banks:**
- Green bond underwriting due diligence
- ESG-linked loan structuring support
- CSRD/TCFD compliance reporting

**Consulting Firms:**
- EY, Deloitte, KPMG, McKinsey — embedded EcoIQ scores in transition strategy reports
- White-label API integration

**Corporates:**
- Supply chain sustainability screening
- Competitor ethical benchmarking
- Investor relations positioning intelligence

### Enterprise Integration Paths

```
EcoIQ API → Bloomberg Terminal (data feed)
EcoIQ API → Refinitiv (data license)
EcoIQ API → Salesforce (CRM enrichment)
EcoIQ API → Tableau / PowerBI (BI integration)
EcoIQ API → Custom institutional data room
```

---

## Development Bank Roadmap

### Target DFI Partners

EcoIQ is uniquely positioned to serve development finance institutions — the organisations with the largest need for ethical industrial intelligence in emerging markets.

| Institution | Region | Mandate | EcoIQ Relevance |
|------------|--------|---------|-----------------|
| EBRD | Europe, Central Asia, MENA | Transition economy support | Country + company intelligence for deal origination |
| IFC | Global | Private sector development | Company ethical scoring for investment screening |
| ADB | Asia-Pacific | Infrastructure + development | Country intelligence for sector programs |
| AIIB | Asia, Europe | Infrastructure investment | Country compatibility scoring |
| GCF | Global | Climate finance | Transition readiness assessment |
| AfDB | Africa | African development | Future country expansion |
| IsDB | OIC countries | Islamic development finance | Ethical alignment intelligence |

### DFI Product Suite

1. **Country Intelligence Packages** — Full sovereign briefings with company landscape, transition gaps, development bank eligibility, financing needs
2. **Pipeline Screen Tool** — Bulk screening of investment pipeline against EcoIQ scores
3. **Portfolio Monitoring** — Track EcoIQ score changes for companies in active loan portfolios
4. **Sector Due Diligence Reports** — Deep-dive sector intelligence for new program development

---

## Long-Term Vision: EcoIQ as Global Ethical Industrial Intelligence Standard

### 5-Year Vision

EcoIQ becomes the reference standard for ethical industrial intelligence — the system that institutional capital, development banks, governments, and corporations use to understand, evaluate, and act on industrial transition.

**The world EcoIQ serves:**
- A development bank evaluating a $500M industrial transition loan in Kazakhstan checks the EcoIQ country intelligence dashboard before initiating due diligence
- A European pension fund running ESG screens uses EcoIQ API to flag steel companies with high CBAM exposure
- A sovereign wealth fund reviews EcoIQ transition roadmaps when evaluating green bond allocations
- A government ministry uses EcoIQ sector intelligence to design industrial policy and just transition frameworks
- A company seeking green bond issuance uses EcoIQ's verified profile to demonstrate transparency to underwriters

### What Makes This Vision Achievable

1. **No incumbent owns this space** — Bloomberg has pricing data; Refinitiv has ESG ratings; CB Insights has venture intelligence. No one owns *ethical industrial transition intelligence* at this depth and accessibility.
2. **Structural tailwinds** — CBAM, CSRD, ISSB, TCFD, green taxonomy requirements are creating regulatory demand for exactly this type of granular industrial intelligence.
3. **AI makes it scalable** — The intelligence quality achievable per company with Claude API at current costs makes global coverage economically viable.
4. **Global trust gap** — Emerging market industrial intelligence is systematically underserved by Western ESG providers. EcoIQ can become the neutral global standard.
5. **Founder credibility** — Deep understanding of industrial transition challenges in Central Asia, Gulf, and emerging markets creates authentic institutional credibility.

### Platform Principles (Non-Negotiable)

1. **Universal ethical framework** — Applicable across all cultures, industries, and geopolitical contexts. Not ideological. Not activist. Analytically neutral and evidence-based.
2. **Institutional quality** — Every output must meet the standard of a major consulting firm intelligence report.
3. **Honest uncertainty** — AI confidence scores, explicit disclaimers, and evidence citations build long-term trust through intellectual honesty.
4. **Public benefit mission** — EcoIQ exists to accelerate industrial transition and ethical investment, not merely to monetise data. The mission comes first.
5. **Long-term over short-term** — No compromises on data quality for growth metrics. The platform builds trust by being right, not by being fast.

---

*Document version: 1.0 — May 2026*
*Next review: Platform Maturity Assessment — Q4 2026*
