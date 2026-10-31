# EcoIQ — Phase 1 Architecture

**Base:** `origin/main` @ `3ea737a` · **Branch:** `feat/ecoiq-khalifah-simplification`
**Status:** planning only. No redesign implemented. Read-only audit + proposal.
**Companion:** [`CURRENT_STATE.md`](CURRENT_STATE.md) — measurements and corrections
to the earlier stale-branch audit.

> **Governing product definition.** EcoIQ helps humanity act as responsible stewards
> — *khalifah* — of the Earth. It examines human systems and determines how they can
> be improved: less harm, less waste, better technology, better capital allocation,
> real execution, verified results, learning.
>
> **The question EcoIQ answers:** *Given this system, these resources and these
> constraints, what should a responsible steward do?*
>
> EcoIQ is **not** a company-ranking product. Rankings remain internally; they stop
> being the public story.

---

## 1. Exact latest-main inventory

| Metric | Value |
|---|---|
| Django apps | **82** |
| Apps with models | 44 |
| Apps with 0 models **and** 0 migrations | 36 |
| — of those, touching **no ORM at all** | **31** |
| `include()` mounts in root URLconf | **77** |
| `urls.py` files | 73 |
| `path()` declarations | 626 |
| Templates | 336 |
| Tests | 4,637 (green) |
| App-package Python LOC | ~186,000 |

### Largest real subsystems

| App | LOC | Models | Migr |
|---|---|---|---|
| `capital_guardian` | 9,071 | 7 | 4 |
| `core` | 12,898 | 3 | 4 |
| `company_intelligence` | 5,901 | **14** | 6 |
| `companies` | 5,747 | 6 | 8 |
| `ai_gateway` | 5,064 | 0 (stateless) | — |
| `good_agents` | 4,998 | **30** | 7 |
| `harvester` | 3,968 | 9 | 8 |
| `ecoiq_commerce` | 3,357 | **23** | 4 |
| `audit` | 3,288 | 9 | 5 |
| `leads` | 3,220 | 6 | 9 |
| `league` | 3,078 | 6 | 6 |
| `partner_participation` | 2,573 | 9 | 2 |
| `digital_twin` | 1,990 | **22** | 4 |
| `global_research` | 1,967 | **19** | 2 |
| `khalifa_stewardship_tour_operating_system` | 1,561 | 13 | 3 |
| `collaboration_rooms` | 1,531 | 9 | 1 |

### Stateless service layers (0 models, but real engines — they read other apps' models)

`ai_gateway` (5,064 LOC / 147 tests) · `plotly_visual_intelligence` (1,308 / 53) ·
`ai_agent_workbench` (1,105 / 41) · `intelligence_analytics_engine` (931 / 24) ·
`pandas_scoring_engine` (579 / 19)

### Hard-coded presentation apps (0 models, 0 migrations, **no ORM anywhere**) — 31

Legitimate content apps (keep public): `gcc_investors` (2,718 LOC — deliberate SEO
pages), `projects` (326 LOC — the static Projects dataset).

The other **29 are architecture descriptions published as product modules**:

`ai_agent_operations_console` · `amanah_autopilot` · `api_integration_layer` ·
`asset_passport` · `certification_trust_badge_engine` · `command_centre` ·
`customer_success_renewal_engine` · `data_room_evidence_vault` ·
`deployment_devops_reliability_centre` · `document_reader_agent_training_pack` ·
`executive_briefing_board_pack_generator` ·
`frontend_experience_google_stitch_design_system` · `frontend_implementation_roadmap` ·
`governance_expert_review_board` · `impact_mrv_layer` · `industrial_playbook_library` ·
`institutional_finance_engine` · `knowledge_graph_relationship_map` ·
`microsoft_core_stack` · `mobile_inspection_mode` · `mrv_agent_training_pack` ·
`omnimodal_evidence_panel` · `portfolio_country_transition_atlas` ·
`product_analytics_kpi_engine` · `public_trust_impact_portal` ·
`revenue_pricing_engine` · `sales_crm_partner_pipeline` ·
`security_privacy_compliance_centre` · `supplier_funding_marketplace`

Verified by reading `command_centre/views.py`: hard-coded dicts (`CONNECTED_MODULES`,
`PIPELINE_STAGES`, `CORE_PURPOSE`) rendered into a template. No database access.

---

## 2. Public route inventory

All probed anonymously against `https://ecoiq.uk`.

### Already correctly gated (302 → login) — no action needed

`/intelligence/` · `/portfolio/` · `/command-centre/` · `/capability-graph/` ·
`/partner-network/` · `/collaboration/` · `/outreach-readiness/` ·
`/public-need-discovery/` · `/public-action-preparation/` · `/ai-assistant/` ·
`/transition/` · `/audit/` · `/ingest/`

*(The earlier audit reported several of these as public. `main` had already fixed
them — see `CURRENT_STATE.md` corrections 8–9.)*

### Business-critical, keep reachable

| Route | Bytes | Note |
|---|---|---|
| `/` | 149,354 | homepage |
| `/healthz/` | 2 | liveness (PR #234) |
| `/projects/` | 19,970 | 0 queries, static — already ideal |
| `/about/`, `/contact/` | ~30 K | |
| `/pricing/`, `/products/`, `/billing/*` | 12 K | **revenue path** |
| `/request-access/`, `/claim/` | — | lead capture |
| `/api/v1/`, `/api/ai/`, `/api/mizan/`, `/api/qdf/` | — | API surface |
| `/embed/` | — | third-party badge embeds |
| `/sitemap.xml`, `/robots.txt` | — | SEO |

### Demote from primary navigation, keep reachable + redirect

`/companies/` (1.18 MB) · `/league/` (1.66 MB) · `/countries/` · `/rankings/` ·
`/evidence/` · `/heating/` · `/khalifa-tours/` · `/methodology/` ·
`/governance-principles/` · `/ethical-governance/` · `/platform/` · `/stewardship/`

### Anomaly

`/ai-observatory/` is mounted in the root URLconf but returns **404** at its index.
Worth a one-line check — either it needs an index route or the mount is dead.

---

## 3. Internal routes accidentally public

**All of the following return HTTP 200 to an anonymous visitor.** They publish
internal roadmap, DevOps posture, sales strategy and pricing design as if they were
customer-facing product.

| Route | Bytes | What it exposes |
|---|---|---|
| `/frontend-implementation-roadmap/` | 44,375 | internal delivery roadmap |
| `/deployment-devops-reliability-centre/` | 40,578 | production/DevOps posture |
| `/sales-crm-partner-pipeline/` | 45,044 | sales & partner pipeline design |
| `/revenue-pricing-engine/` | 43,275 | pricing/monetisation strategy |
| `/customer-success-renewal-engine/` | 41,855 | renewal/churn strategy |
| `/product-analytics-kpi-engine/` | 39,911 | internal KPI design |
| `/security-privacy-compliance-centre/` | 43,669 | security & compliance posture |
| `/knowledge-graph-relationship-map/` | 60,765 | internal data architecture |
| `/frontend-experience-google-stitch-design-system/` | 38,789 | internal design system |
| `/microsoft-ecosystem-core-stack/` | 39,180 | vendor architecture plan |
| `/api-integration-layer/` | 40,090 | integration architecture |
| `/data-room-evidence-vault/` | 46,664 | due-diligence architecture |
| `/executive-briefing-board-pack-generator/` | 42,135 | board-pack architecture |
| `/governance-expert-review-board/` | 36,864 | review-board design |
| `/institutional-finance-engine/` | 39,160 | finance-model architecture |
| `/industrial-playbook-library/` | 43,174 | playbook architecture |
| `/supplier-funding-marketplace/` | 36,294 | marketplace architecture |
| `/mobile-inspection-mode/` | 35,018 | field-app architecture |
| `/impact-mrv-layer/` | 31,755 | MRV architecture |
| `/asset-passport/` | 30,186 | asset-passport architecture |
| `/omnimodal-evidence-panel/` | 29,123 | evidence-panel architecture |
| `/certification-trust-badge-engine/` | 41,907 | badge architecture |
| `/portfolio-country-transition-atlas/` | 47,875 | atlas architecture |
| `/public-trust-impact-portal/` | 37,483 | portal architecture |
| `/ai-agent-operations-console/` | 44,447 | agent ops architecture |
| `/document-reader-agent-training-pack/` | 48,055 | agent training pack |
| `/mrv-agent-training-pack/` | 44,198 | agent training pack |
| `/agent-training-evaluation-lab/` | 43,189 | agent evaluation design |
| `/amanah-autopilot/` | 26,062 | product concept |

**~1.1 MB of internal design documentation served publicly.** Two risks: it reads as
shipped capability when it is a plan (the "never present conceptual work as
completed" rule), and `/deployment-devops-reliability-centre/` +
`/security-privacy-compliance-centre/` describe the production security posture to
anyone who asks.

**This is the single most urgent item in the whole plan** and is also the safest to
fix — these apps hold no data, so gating them cannot break anything.

---

## 4. Existing capabilities worth preserving

Ranked by strategic value to the new direction.

1. **`digital_twin` (22 models)** — the loop, already built. Observe → understand →
   generate → simulate → assess → decide → execute → measure, with `Unit`-typed
   quantities and `TwinDataGap` for honest unknowns.
2. **`global_research` (19 models)** — the technology-comparison engine.
   `TechnologyCandidate` → `CompatibilityAssessment` → `ComparativeEvaluation`, with
   `ResearchClaim`/`ClaimAssessment`, `ContradictionRecord`, `SupplyChainRiskFlag`.
   This is what makes the aviation example real rather than a graphic.
3. **`khalifa_stewardship_tour_operating_system` (13 models)** — Eco Tours,
   PII-safe by construction.
4. **`waste_to_value_capital_allocation_engine` (9 models)** — `OperationalLoss` →
   `InterventionOption` (with `technical_readiness`) → `InterventionScenario` →
   `FundingGap` → `CapitalRouteMatch` → `CapitalAllocationDecision` →
   `VerifiedCapitalOutcome`.
5. **`capital_guardian` (9,071 LOC, 7 models)** — capital traceability, governance,
   milestone control, red-flag engine.
6. `company_intelligence` (14) — evidence-linked KPI assessment with explicit
   evidence links and review actions.
7. `capability_graph` (5) — deduplicated real-world organisation graph with
   evidence-backed capabilities and verified public routes.
8. `evidence_memory`, `ai_gateway`, `harvester`, `ecoiq_commerce`, `leads`,
   `langgraph_orchestration`, `pandas_scoring_engine`.

---

## 5. CORE / BETA / LABS / INTERNAL classification

Nothing is deleted. This is about *where a thing is surfaced*, not whether it exists.

### CORE — public, invested in
`core` (home, about, contact) · `projects` · `khalifa_stewardship_tour_operating_system`
(as Eco Tours) · `ecoiq_commerce` (billing) · `leads` · `mobile_auth` · `gcc_investors`
· `ai_gateway`

### CORE — keep, but behind `app.ecoiq.uk` / auth
`digital_twin` · `global_research` · `capital_guardian` ·
`waste_to_value_capital_allocation_engine` · `company_intelligence` · `companies` ·
`league` · `countries` · `harvester` · `evidence_memory` · `capability_graph` ·
`good_agents` · `gold_intelligence` · `decision_studio` · `geo_intelligence` ·
`investor_portfolio` · `financial_intelligence_cloud` · `audit` · `api` · `mizan` ·
`qdf` · `pandas_scoring_engine` · `intelligence_analytics_engine` ·
`langgraph_orchestration` · `plotly_visual_intelligence` · `partner_participation` ·
`collaboration_rooms` · `outreach_readiness` · `public_need_discovery` ·
`public_action_preparation`

### BETA — authenticated, labelled as beta
`ai_agent_council` · `ai_agent_workbench` · `agent_runtime_model_router` ·
`agent_training_evaluation_lab` · `ai_observatory` · `backend_intelligence_engine` ·
`hikma` · `heating` · `transition` · `intelligence` · `ethics` · `financing` ·
`ingestion` · `notifications`

### LABS / INTERNAL — code retained, removed from the public web
The 29 concept apps in §1 · `legacy_safe` (hackathon) · `tazkiyah-114*` staff previews ·
`/video-studio/` · `/visual-lab/`

### DEPRECATED CANDIDATE — propose only, delete nothing
`cms` (Wagtail already unregistered; tables orphaned) · `railway.toml` ·
`nixpacks.toml` (Render is the target) · committed binaries `db.sqlite3`,
`test_render.db`, `dump.rdb`

> **Rule:** no deletion without proof of non-use *and* explicit approval.

---

## 6. Current navigation vs proposed navigation

### Current (measured in `templates/base.html` on `main`)

- **Primary nav: 21 links.** Rankings · Countries · About · Methodology ·
  Stewardship · Projects · Khalifa Heat · Khalifa Tours · Pricing · Geo Intelligence ·
  Gold Intelligence · Capital Guardian · Ask EcoIQ AI · Contact · My Portfolios ·
  Dashboard · Register · Sign In · Command Centre · Ingest · Admin
- **Footer: 16 product links.**
- **Homepage:** 895 DOM elements, 6 lazy islands, a three.js globe.
- **Internal-platform links exposed publicly in nav:** Geo Intelligence, Gold
  Intelligence, Capital Guardian, Ask EcoIQ AI, Command Centre (5).

### Proposed

```
Intelligence · Eco Tours · Projects · About · Contact        [ Sign in ]
```

**5 items + Sign in.** Removed from primary nav (technology retained):
Companies · Countries · Rankings · AI Agents · Compendium · Framework · Methodology ·
Geo Intelligence · Gold Intelligence · Capital Guardian · Khalifa Heat · Pricing ·
Command Centre · Ingest · Admin.

Footer reduced to: Pricing · API · Press · Privacy · Terms · Contact + company
registration line.

---

## 7. Routes to hide / move

| Group | Action | Mechanism |
|---|---|---|
| 29 concept apps (§3) | Remove from public web | `@staff_member_required` on the view, or a single `INTERNAL_ONLY` middleware allowlist |
| `/companies/`, `/league/`, `/countries/`, `/rankings/` | Demote from nav; keep URLs live | nav edit only — **no redirect yet**, SEO value is real |
| `/ai-agents/`, `/ai-agent-council/`, `/agent-runtime-model-router/`, `/intelligence-dashboard/`, `/decision-studio/`, `/geo-intelligence/` | Move behind auth | login required |
| `/methodology/`, `/ethical-governance/`, `/governance-principles/`, `/platform/`, `/stewardship/` | Fold into `/about/` | 301 to `/about/#section` |
| `/tazkiyah-114*`, `/video-studio/`, `/visual-lab/`, `/legacy-safe/` | Staff-only | `@staff_member_required` |

---

## 8. Redirect strategy

**Principle: nothing 404s. Ever.**

1. **Preserve the 401 indexed company URLs.** `/companies/<slug>/` keeps working.
   They are the site's accumulated SEO. Demote from nav; do not redirect.
2. **Concept apps → 302, not 301.** They are being gated, not permanently relocated,
   and 302 is reversible if we change our minds. A staff user still gets the page.
3. **Consolidations → 301** (`/methodology/` → `/about/`), because those are
   permanent.
4. **Update `sitemap.xml` in the same PR as any nav change.** `StaticSitemap._pages`
   currently lists `home`, `companies:directory`, `countries:directory`,
   `methodology`, `pricing`, `about`, `api_docs`.
5. **Update `robots.txt` in the same PR.** It currently `Allow:`s
   `/platform/`, `/ethical-governance/`, `/governance-principles/`, `/methodology/`.
6. **Add a redirect regression test.** Every removed public path asserted to return
   200/301/302 — never 404.

---

## 9. Existing loop-component mapping

**Reuse before building. Do not create 11 apps for 11 stages.**

| Stage | Existing components | Gap | Recommendation |
|---|---|---|---|
| **Observe** | `harvester` (9 models), `ingestion`, `company_intelligence` (`CompanyRefreshRun`, `DiscoveredSource`), `geo_intelligence`, `digital_twin.OperationalMetric`, `evidence_memory` | No single "system under study" entry point; observation is per-vertical | Add a thin façade, not a new app |
| **Understand** | `evidence_memory` (+`confidence`), `pandas_scoring_engine`, `intelligence_analytics_engine`, `hikma`, `digital_twin.ProcessNode/ResourceFlow/LossDetection`, `TwinDataGap` | `default=50.0` corrupts "understanding" with fake certainty (§17) | Fix scoring integrity first |
| **Generate** | `global_research.TechnologyCandidate`, `good_agents` (30 models), `waste_to_value.InterventionOption`, `digital_twin.ModernisationScenario` | Not driven from a sector taxonomy | Add sector taxonomy (§11) as data, not code |
| **Simulate** | `digital_twin` (`DigitalTwin`, `ProcessEdge`, `ModernisationScenario` with unit-typed energy/water/waste/emissions impacts), `waste_to_value.InterventionScenario` | No public-facing simulation surface | Expose read-only on Intelligence page |
| **Optimise** | `intelligence_analytics_engine`, `waste_to_value` (`FundingGap`, `CapitalRouteMatch`), `global_research.ComparativeEvaluation` | No portfolio-level "£1bn across N options" comparator | **The one genuine new build** (§12) |
| **Finance** | `waste_to_value.CapitalAllocationDecision`, `capital_guardian` (9,071 LOC), `financing`, `ecoiq_commerce`, `financial_intelligence_cloud` | — | Reuse as-is |
| **Execute** | `projects`, `khalifa_stewardship_tour_operating_system`, `digital_twin.ImplementationAction`, `partner_participation`, `public_action_preparation`, `collaboration_rooms` | Static `projects/data.py` not linked to real execution records | Bridge `projects` → `digital_twin.ImplementationAction` |
| **Verify** | `digital_twin.MeasuredOutcome`, `TourMRVPlan` (`verification_status`, `public_reporting_ready`), `waste_to_value.VerifiedCapitalOutcome`, `governance_expert_review_board` *(hard-coded)* | `impact_mrv_layer` is a **concept page, not an engine** | Use `digital_twin.MeasuredOutcome` as canonical MRV; do not build out `impact_mrv_layer` |
| **Measure** | `league`, `companies` scoring, `company_intelligence.CompanyKPIAssessment`, `digital_twin.StewardshipKPI`, `outreach_readiness` | Two parallel scoring systems (`companies` vs `digital_twin.StewardshipKPI`) | Converge on `StewardshipKPI` long-term |
| **Learn** | `evidence_memory`, `agent_training_evaluation_lab`, `ai_observatory` (`AnalysisSession`, `ModelInvocation`), `global_research.ContradictionRecord` | No feedback edge from `MeasuredOutcome` back into `StewardshipKPI` calibration | Smallest high-value addition |

**Conclusion: 9 of 11 stages already have a real implementation.** Only *Optimise*
(portfolio-level) and *Learn* (feedback edge) need genuine new work. **No new Django
app is required for the loop.**

---

## 10. Khalifah Engine architecture

**It already exists, in `digital_twin`, and it is a gate — not a score, not a
chatbot, not branding.**

```
SacredSourceReference  ── tradition · surah/ayah · approved_translation
      │                   translation_source · review_status · reviewed_by
      ▼
StewardshipPrinciple   ── plain-language statement, M2M to sources
      │
      ▼
StewardshipKPI         ── formula_definition · formula_version
      │                   scoring_direction · target_min/max
      │                   warning_threshold · BLOCKING_THRESHOLD
      │                   blocking_rule · evidence_requirements
      │                   approval_status = 'requires_scholarly_review'
      ▼
StewardshipAssessment  ── evaluated against a ModernisationScenario
      │
      ▼
HumanDecision ──> ImplementationAction ──> MeasuredOutcome
```

Why this satisfies the brief:

- **Not a score.** `blocking_threshold` + `blocking_rule` let an intervention be
  *refused*, not merely ranked lower.
- **Not religious branding without implementation.** `SacredSourceReference` carries
  `approved_translation`, `translation_source`, `review_status`, `reviewed_by`, and
  defaults to a "requires scholarly review" note. The system will not assert
  grounding it has not had reviewed.
- **Authentic yet universal.** `source_tradition` is a field, and `StewardshipKPI`
  is expressed as formula + thresholds + evidence requirements. A government or fund
  reads a governance gate; the Islamic foundation is visible but never a
  prerequisite to using the product.
- **Human-governed.** `HumanDecision` sits between assessment and action.

### The 15 Khalifah questions → where each is answered

| # | Question | Component |
|---|---|---|
| 1–3 | What harm exists? Can it be reduced? What is wasted? | `LossDetection`, `OperationalLoss`, `TwinDataGap` |
| 4 | Consequences over time? | `implementation_phases`, `MeasuredOutcome` |
| 5–6 | Who benefits / bears cost? | `worker_impact`, `community_impact`, `TourBeneficiary` |
| 7 | Moving damage between systems? | the four unit-typed impact axes together |
| 8–10 | Water / biodiversity / people? | `water_impact`, `community_impact` — **biodiversity is a gap** |
| 11 | Technically feasible? | `InterventionOption.technical_readiness`, `CompatibilityAssessment` |
| 12 | Economically viable? | `capital_guardian`, `waste_to_value.FundingGap` |
| 13 | Better use of the same capital? | **gap — §12** |
| 14 | Can damaged systems be restored? | gap (nature sector) |
| 15 | Independently verifiable? | `MeasuredOutcome`, `TourMRVPlan.verification_status` |

**Recommended work: add a `biodiversity_impact` axis and a restoration scenario type
to `ModernisationScenario`. Do not build a new Khalifah app.**

---

## 11. Sector model

Nine sectors, expressed as **data** (a taxonomy table + seeded rows), not nine
Django apps. Each maps onto the existing `digital_twin` / `global_research` schema.

| Sector | Current-system baseline | Candidate pathways |
|---|---|---|
| **Aviation** | kerosene → aircraft → emissions + fuel cost + noise | battery-electric · hybrid-electric · SAF · hydrogen · lightweight materials · aerodynamics · route optimisation · airport electrification · renewable airport energy |
| **Energy** | coal / gas | renewables · nuclear where appropriate · storage · grids · demand management · efficiency |
| **Buildings** | poor insulation + fossil heating | insulation · heat pumps · solar · storage · smart energy management |
| **Transport** | petrol/diesel, congestion, inefficient logistics | EV · rail · public transport · charging · route & logistics optimisation |
| **Industry** | high energy/material intensity | electrification · process optimisation · material substitution · recycling · circular manufacturing |
| **Agriculture** | water + fertiliser + methane + degraded soil | precision agriculture · water optimisation · methane reduction · soil restoration · regenerative systems · waste utilisation |
| **Water** | leakage, pollution, scarcity | detect · conserve · reuse · treat · optimise · restore |
| **Waste** | landfill | avoid · reuse · repair · recycle · recover · safe residual processing |
| **Nature** | degradation | protect · restore · monitor · measure · verify recovery |

**Mapping:** sector → `AssetType` + `StewardshipKPI.applicable_asset_types`;
pathway → `global_research.TechnologyCategory` → `TechnologyCandidate`;
evaluation → `CompatibilityAssessment` + `ComparativeEvaluation` →
`ModernisationScenario`.

**Feasibility over theoretical minimum** is already enforced by
`InterventionOption.technical_readiness` and `CompatibilityAssessment` — the schema
will not let "hydrogen aviation" outrank "route optimisation" on emissions alone.

---

## 12. Capital allocation architecture

**"Where should the next £1 billion go?"** — the one genuinely new engine.

Everything downstream exists (`CapitalAllocationDecision`, `capital_guardian`,
`FundingGap`, `CapitalRouteMatch`). What is missing is the **portfolio comparator**:
given a budget and a constraint set, rank *N* interventions across sectors.

Proposed as a **stateless service** (like `pandas_scoring_engine`), not a new app:

```
Input:  budget · location · sector filter · constraints · time horizon
        ↓
Candidates: ModernisationScenario ∪ InterventionOption ∪ TechnologyCandidate
        ↓
Per-candidate vector (each dimension nullable + evidence-graded):
  CO₂ avoided · CO₂ per £ · capital required · operating cost · financial return
  payback · implementation time · technology readiness · resource intensity
  energy security · water impact · biodiversity impact · health impact
  employment · social outcomes · implementation risk · evidence confidence
        ↓
Khalifah gate: StewardshipKPI blocking_threshold → candidate REFUSED
        ↓
Efficient frontier — NOT a single scalar
        ↓
HumanDecision
```

**Rules.** Never collapse to CO₂ alone. Never rank a candidate whose evidence
confidence is unknown above one that is measured. Always show the vector, not just
the winner. A blocked candidate is shown as blocked, with the rule that blocked it.

---

## 13. Eco Tours reuse plan

`khalifa_stewardship_tour_operating_system` is **already privacy-safe and
MRV-aware**. Build a consumer front end over it; add no new models.

| Model | Reuse |
|---|---|
| `StewardshipTour` | slug, country FK, region, `tour_type`, dates, `participant_capacity`, `estimated_price_per_participant`, currency, `safety_level`, `human_approved` |
| `TourBeneficiary` | `display_reference` is explicitly *"Safe public label"*; `private_contact_reference`, `address_reference`, `vulnerability_notes_private` are *"never rendered in any public view"* |
| `ConsentRecord` | granular `consent_type`/`status`/`granted_at`/`withdrawn_at` — gates any photo or story |
| `TourMRVPlan` | `verification_status` ∈ {not_started, baseline_collected, after_data_pending, **verified**} and `public_reporting_ready` |
| `TourLocalPartner`, `SupplierQuote`, `IncidentReport`, `LaunchChecklistItem` | operations, stay internal |

**`tour_type` already matches the Kazakhstan themes:** `mountain` (Tian Shan),
`lake_water` (alpine lakes), `wildlife` (nature restoration), `clean_heat`,
`food_surplus`, `greenhouse`.

**Publication gate — the honesty rule, expressible today:**

```python
human_approved is True
  AND mrv_plan.public_reporting_ready is True
  AND mrv_plan.verification_status == 'verified'
      → impact figures may be shown as achieved
otherwise → show the journey; label impact "planned", never "delivered"
```

`PIPELINE_STATUS_CHOICES` already ends `mrv_pending` → `verified_legacy`.

**Page composition — 70 / 20 / 10.** Photography and landscape first; community and
people second; a single quiet verified-impact strip last. The technology stays
underneath. Not a dashboard.

> **Content gap:** the tour models exist but real photography, itineraries and
> partner agreements do not. The page cannot ship as "book now" — it ships as
> *"Join the first journey"* with an interest form.

---

## 14. Public/static-site architecture options

| Option | What | Pros | Cons |
|---|---|---|---|
| **A. Render Static Site** | `ecoiq.uk` → prebuilt static; `app.ecoiq.uk` → Django | Zero DB for marketing; best CWV; cheapest | Two deploy pipelines; content edits need a build |
| **B. Same Django, cached** | Keep one service; add `CACHES` + `@cache_page` on public pages | Smallest change; no DNS work | Still 512 MB shared with WeasyPrint/sklearn; no CWV win from the 2.59 MB PNG |
| **C. Hybrid (recommended)** | Fix payload + add caching now; static split later as a separate decision | Captures ~95 % of the user-visible win with ~5 % of the risk | Defers the architectural cleanliness |

**Recommendation: C, then A.** The measured evidence says the dominant problem is
**payload, not architecture** — one 2.59 MB preloaded PNG plus ~500 KB of globe
assets. Replacing that image is a one-line template change worth more than the
entire domain split. Note also that `settings.py` currently defines **no `CACHES`
block at all**, so option B is not yet available without adding one.

**Which problems the static split does *not* solve:** `/companies/` (1.18 MB) and
`/league/` (1.66 MB) are data-driven and must stay on Django — they need
pagination regardless.

---

## 15. `ecoiq.uk` / `app.ecoiq.uk` migration risks

| # | Risk | Severity | Detail |
|---|---|---|---|
| 1 | **Canonical tag hard-coded** | **High** | `templates/base.html:14,19` emit `https://ecoiq.uk{{ request.path }}` for canonical *and* `og:url` on **every page**. After a split, every `app.ecoiq.uk` page would declare a canonical pointing at a non-existent `ecoiq.uk` URL. Must become `SITE_URL`-driven **before** any DNS change. |
| 2 | **Stripe webhook** | **High** | See §16 |
| 3 | `SITE_URL` fallbacks | Medium | `https://ecoiq.uk` hard-coded as fallback in 8 places incl. `league/pdf_report.py:349` (PDF asset base URL) |
| 4 | 39 templates contain `ecoiq.uk` | Medium | Audit each before cutover |
| 5 | Cookies | Medium | No `SESSION_COOKIE_DOMAIN`/`CSRF_COOKIE_DOMAIN` set → host-only cookies. Fine for a static public site; any cross-subdomain flow needs explicit config |
| 6 | `CSRF_TRUSTED_ORIGINS` | Medium | Env-driven; must add `https://app.ecoiq.uk` **before** cutover or all POSTs break |
| 7 | `ALLOWED_HOSTS` | Medium | Same; `settings.py` refuses `*` in production (correct) |
| 8 | `sitemap.xml` / `robots.txt` | Medium | Both assume one host; 401 company URLs would move |
| 9 | Email links | Medium | `LEAD_NOTIFY_EMAIL`, `DEFAULT_FROM_EMAIL` and report links use `SITE_URL` |
| 10 | `/embed/` badges | Medium | Third parties have embedded these; the host **cannot** change |
| 11 | Admin | Low | `/admin/` moves with the app |
| 12 | CORS | Low | No CORS package installed — if the static site calls the API, this becomes required new work |
| 13 | OAuth callbacks | Low | None found |

---

## 16. Stripe / domain dependencies

**`/billing/webhook/` is the highest-risk path in the codebase.**

`ecoiq_commerce/billing_urls.py` states it plainly:

> *"The webhook path is fixed at exactly `/billing/webhook/` — it is configured by
> hand in the Stripe Dashboard, so renaming it silently breaks payment provisioning
> in production with no local test failure to warn you."*

**What breaks if the domain changes:**

1. Stripe posts to `https://ecoiq.uk/billing/webhook/`. If `ecoiq.uk` becomes a
   static site, that POST hits a host with no Django — **payment provisioning
   silently stops**. Subscriptions charge; entitlements never activate.
2. Failure is **silent from the user's side** and visible only in the Stripe
   Dashboard's webhook delivery log.
3. `checkout_subscription` / `portal` build success/cancel URLs from `SITE_URL`.
4. `render.yaml` currently ships `ECOIQ_BILLING_PROVIDER: "none"` and
   `STRIPE_LIVE_MODE_ALLOWED: "false"` — **billing is not live today**, which is why
   this is a planning risk and not a live incident.

**Mandatory sequencing if the split proceeds:**
`/billing/*` must remain served from `ecoiq.uk` (proxied to the app), **or** the
Stripe Dashboard endpoint must be re-registered to `app.ecoiq.uk` **and verified
with a test event before** DNS moves. Never both at once, never DNS first.

**No Stripe configuration is changed in this phase.**

---

## 17. Scoring-integrity migration plan

**Principle: UNKNOWN ≠ 50.**

**Verified scope:** 27 `default=50.0` fields in `companies/models.py`; **39 across 6
model files** (`companies`, `good_agents`, `digital_twin`,
`waste_to_value_capital_allocation_engine`, `financial_intelligence_cloud`,
`khalifa_stewardship_tour_operating_system`). Broader than the earlier audit found.

**The correct pattern already exists in the codebase** —
`evidence_memory/models.py:84`: *"Never fabricated — null until a real confidence
value is known."* And every `ModernisationScenario` impact axis is already
`null=True`. The fix is to propagate an existing convention, not invent one.

**Proposed evidence grade** (new small enum, reused everywhere):

```
MEASURED · ESTIMATED · MODELLED · INFERRED · UNKNOWN
```

### Migration, in strict order

| Step | Action | Reversible |
|---|---|---|
| 1 | Add `EvidenceGrade` choices + a nullable `*_grade` companion to each score field. **No default change.** | yes |
| 2 | Backfill: any value still exactly `50.0` and never explicitly set → grade `UNKNOWN` | yes |
| 3 | Change public **rendering** to show "Insufficient evidence" wherever grade = `UNKNOWN`. **Data untouched.** | yes — template-only |
| 4 | Exclude `UNKNOWN`-graded dimensions from composite aggregation; publish coverage % alongside every composite | yes |
| 5 | Only then, `default=50.0` → `null=True`, with a data migration | **no** — needs approval |
| 6 | Add a test forbidding new `default=50` in any `models.py` | yes |

**Steps 1–4 are non-destructive and deliver the honesty win.** Step 5 is the only
irreversible one and should be a separate, explicitly approved PR.

**Do not attempt this before the branch/nav work** — it touches 6 apps and the
public ranking pages simultaneously.

---

## 18. Performance baseline

### Pages (production, anonymous)

| Page | HTML | DOM | Time | Queries* |
|---|---|---|---|---|
| `/healthz/` | **2 B** | — | 0.36 s | **0** |
| `/` | 149,354 B | 895 | 0.57 s | **12** |
| `/projects/` | 19,970 B | 145 | 0.39 s | 0 |
| `/about/` | 30,031 B | 209 | 0.38 s | 2 |
| `/khalifa-tours/` | 96,621 B | 708 | 1.44 s | — |
| `/ai-agents/` | 101,898 B | 1,185 | 2.46 s | — |
| `/companies/` | **1,180,739 B** | **20,599** | 1.09 s | 4 |
| `/league/` | **1,664,834 B** | 17,322 | **3.14 s** | 4 |

\* measured locally against an empty test DB.

> `/companies/` and `/league/` are **not** N+1 problems — few queries, but the entire
> result set is rendered with no `Paginator` anywhere in `companies/views.py`.
> Pagination fixes them; query tuning would not.

### Homepage payload ≈ **3.5 MB**

| Asset | Bytes |
|---|---|
| **`ecoiq-better-way-hero.png`** — `<link rel="preload" as="image">` | **2,592,714** |
| HTML | 149,354 |
| `ecoiq-islands.js` | 115,678 |
| `three.min.js` *(lazy)* | 170,851 |
| `three-globe.min.js` *(lazy)* | 144,713 |
| `countries-110m.geojson` *(lazy)* | 188,893 |
| earth textures ×2 *(lazy)* | 110,708 |
| `ecoiq-islands.css` | 10,547 |
| `living-earth.js` | 9,555 |
| `hero-globe-v2.js` | 3,259 |
| `section-bg.css` | 1,492 |
| icons ×2 | 1,331 |
| Google Fonts — Inter, 7 weights | not measured |

**The single worst item.** `preload` gives the 2.59 MB PNG *highest* fetch priority,
so the largest asset on the site is downloaded before anything else and directly
gates LCP. On mobile this alone is disqualifying.

### What a static public site fixes — and what it does not

| Problem | Fixed by static? |
|---|---|
| 12 homepage DB queries | ✅ |
| Marketing sharing 512 MB with WeasyPrint/sklearn | ✅ |
| **2.59 MB preloaded PNG** | ❌ — image problem, fix it directly |
| 500 KB globe assets | ❌ |
| `/companies/` 1.18 MB, `/league/` 1.66 MB | ❌ — data-driven, needs pagination |
| Google Fonts 7 weights | ❌ |

**Most of the win is payload, not architecture.**

---

## 19. Proposed final information architecture

```
ecoiq.uk                          lightweight public experience
│
├─ /                              "Make every system on Earth work better."
│                                 EcoIQ identifies how technology, capital and
│                                 human action can reduce waste, emissions and
│                                 environmental harm while improving prosperity
│                                 and quality of life.
│                                 [ Explore Solutions ]  [ Discover Eco Tours ]
│                                 → 9 sectors, visually simple, no explanations
│
├─ /intelligence/                 "Where should the next £1 billion go?"
│                                 problem → options → simulation → optimisation
│                                 → finance → execution → verification
│                                 2–3 worked examples (Aviation first)
│
├─ /eco-tours/                    "Travel somewhere extraordinary.
│                                  Leave it better than you found it."
│                                 Kazakhstan. 70 travel / 20 people / 10 impact
│
├─ /projects/                     CONCEPT · SCOPING · PILOT · IN EXECUTION · VERIFIED
│                                 never conceptual work shown as delivered
│
├─ /about/                        purpose · stewardship · Khalifah · how
│                                 technology supports rather than replaces
│                                 responsibility
│
├─ /contact/                      extremely simple
│
└─ [ Sign in ] ──────────────────> app.ecoiq.uk

app.ecoiq.uk                      the full platform, unchanged
  /companies/ /league/ /countries/ /capital-guardian/ /gold-intelligence/
  /digital-twin/ /global-research/ /decision-studio/ /good-agents/
  /geo-intelligence/ /portfolio/ /billing/ /api/ /admin/ … + all LABS/INTERNAL
```

**Naming conflict.** `/intelligence/` is currently the Environmental Intelligence OS
hub (live, auth-gated, 302). The public Intelligence page needs that path. Proposal:
existing hub → `app.ecoiq.uk/intelligence-os/` with a 301.

`/projects/` is already static (0 queries, 19 KB) and already has the right status
vocabulary — it needs the two missing statuses (`IN EXECUTION`, `VERIFIED`) and
nothing else.

---

## 20. Recommended sequence of small PRs

Ordered by **dependency and risk**, not by the illustrative order in the brief. Each
is independently revertible.

| PR | Scope | Risk | Why here |
|---|---|---|---|
| **A** | **Gate the 29 internal concept pages** (`@staff_member_required` + redirect test + `robots.txt`) | **Low** | Highest value, lowest risk. They hold no data — nothing can break. Removes ~1.1 MB of public internal documentation and stops presenting plans as capability. **Do this first.** |
| **B** | **Homepage payload**: replace 2.59 MB PNG with responsive WebP/AVIF; drop/repoint the `preload`; trim Inter to 2–3 weights | **Low** | Biggest measurable user win. Pure asset change, no redesign, no IA decision. Independent of everything else. |
| **C** | **Paginate `/companies/` and `/league/`** | Low-Med | 1.18 MB → ~40 KB and 1.66 MB → ~40 KB. Needed whether or not the domain splits. Touches a public page, so its own PR. |
| **D** | **`SITE_URL`-drive canonical + `og:url`** in `base.html` | Low | **Blocks the domain split.** Trivial now, painful later. Ship early. |
| **E** | **Scoring integrity steps 1–4** (grades, backfill, "Insufficient evidence" rendering, coverage %) | Medium | Non-destructive. Must land before rankings are demoted, so demotion isn't hiding a data-quality problem. |
| **F** | **Minimal public navigation** (5 items) + footer + `sitemap.xml` + `robots.txt` + redirect tests | Medium | Depends on A (pages gated) and E (scores honest). |
| **G** | **New homepage** | Medium | Depends on F. |
| **H** | **Intelligence page** (aviation worked example over `global_research` + `digital_twin`) | Medium | Depends on G. Reuses existing models — no new app. |
| **I** | **Eco Tours landing** over `khalifa_stewardship_tour_operating_system` | Medium | Depends on G. **Blocked on real photography/content, not code.** |
| **J** | **Capital comparator service** (§12) | High | The only genuinely new engine. Deserves its own ADR first. |
| **K** | **Static/public architecture preparation** | High | Depends on B, C, D. Propose; do not execute without a separate decision. |
| **L** | **Scoring integrity step 5** (`default=50.0` → `null=True`) | High | Irreversible. Separate, explicitly approved. |

**Deliberately deferred:** domain split, Stripe changes, any deletion, `/readyz/`,
Obsidian knowledge vault.

### Recommended first PR

**PR A — gate the internal concept pages.** It is the highest-value, lowest-risk
change available: it touches no data, cannot break a user flow, immediately removes
~1.1 MB of internal roadmap/DevOps/sales/security documentation from the public web,
and it is the change most directly required by the new product direction.

---

## Open questions for the founder

1. **`/ai-observatory/` returns 404** at its index despite being mounted. Dead mount,
   or missing index route?
2. **Two parallel scoring systems** — `companies.CompanyProfile` (27 × `default=50.0`)
   and `digital_twin.StewardshipKPI` (formula + thresholds + evidence requirements).
   The second is much better. Converge, or keep both?
3. **Eco Tours content.** The models are ready; photography, itineraries and partner
   agreements are not. Ship as "Join the first journey" interest capture?
4. **`/companies/` SEO.** 401 indexed URLs are real accumulated value. Confirmed
   intent is to demote from navigation but keep the URLs live?
5. **Biodiversity axis** is absent from `ModernisationScenario`. Add it as part of
   the Nature sector work?
