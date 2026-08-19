# CURRENT_STATE.md — EcoIQ

**Re-verified:** 2026-08-19 against `origin/main` @ `3ea737a`
**Method:** read-only inspection of the `main` worktree + anonymous HTTPS probes of
production (`https://ecoiq.uk`).

## Provenance and status of the earlier audit

A Phase 0 audit was produced on 2026-08-19 and left in the frozen working tree at
`/CURRENT_STATE.md` (555 lines, sha1 `30a0475…`). That file is **deliberately not
moved or modified** — the `feat/stripe-billing-integration` tree is frozen.

That audit was measured against a branch **207 commits behind `main`**. It is
retained as historical input only. **Every material claim below was re-measured
against `main`.** Where the earlier audit was wrong, it is marked
**`[OBSOLETE]`** rather than quietly corrected.

---

## Corrections to the earlier audit

| # | Earlier claim | Verified on `main` | Status |
|---|---|---|---|
| 1 | 70 Django apps | **82** | `[OBSOLETE]` — understated by 12 |
| 2 | 55 `include()` mounts | **77** | `[OBSOLETE]` |
| 3 | ~416 `path()` declarations | **626** across 73 `urls.py` | `[OBSOLETE]` |
| 4 | 2,881 tests | **4,622** (now 4,637) | `[OBSOLETE]` |
| 5 | Homepage runs ~7 DB queries | **12**, measured | `[OBSOLETE]` |
| 6 | ~24 `default=50.0` fields in `companies` | **27** in `companies`, **39 repo-wide across 6 model files** | `[OBSOLETE]` — understated, and the problem is not confined to `companies` |
| 7 | 28 zero-model "concept" apps | **36** zero-model/zero-migration; of those **31 touch no ORM at all**; 29 are genuinely concept pages (`gcc_investors` and `projects` are legitimate content apps) | `[OBSOLETE]` — refined |
| 8 | `/command-centre/` publicly reachable (200) | **302 → login**. Already gated on `main` | `[OBSOLETE]` — fixed upstream |
| 9 | `/intelligence/`, `/transition/`, `/audit/`, `/ingest/` public | All **302 → login** on `main` | `[OBSOLETE]` |
| 10 | Templates: ~103 | **336** `.html` files | `[OBSOLETE]` |
| 11 | No `/healthz/`; no `healthCheckPath` | **Fixed.** PR #234 merged as `3ea737a`; `/healthz/` returns 200 in production | Resolved |
| 12 | `CLAUDE.md` §7 Tailwind-CDN claim is stale | Still stale — 0 Tailwind CDN references in `templates/` | Confirmed, unfixed |

**Claims that survived re-verification unchanged:**

- The 2.59 MB hero PNG is still `<link rel="preload">`-ed on the homepage.
- `/companies/` still ships 1.18 MB / 20,599 DOM elements with no pagination.
- `sitemap.xml` still advertises 401 company URLs.
- `evidence_memory` still carries the correct pattern (`confidence` nullable,
  *"Never fabricated — null until a real confidence value is known"*).
- ~29 internal concept/architecture pages are still anonymously reachable.

---

## What the earlier audit missed entirely

`main` contains four substantial, high-quality subsystems that did not exist on the
stale branch. These materially change the plan, because they mean **most of the
target architecture is already built**:

| App | Models | What it actually is |
|---|---|---|
| `digital_twin` | **22** | `IndustrialAsset` → `DigitalTwin` → `ProcessNode`/`ProcessEdge`/`ResourceFlow` → `OperationalMetric` → `LossDetection` → `ModernisationScenario` → `StewardshipAssessment` → `HumanDecision` → `ImplementationAction` → `MeasuredOutcome`. Also `TwinDataGap`. |
| `global_research` | **19** | `ResearchMission` → `TechnologyCandidate` → `CompatibilityAssessment` → `ComparativeEvaluation` → `ResearchRecommendation`, with `ResearchClaim`/`ClaimAssessment`, `ContradictionRecord`, `SupplyChainRiskFlag`, `ResearchHumanDecision`. |
| `company_intelligence` | **14** | Evidence-linked KPI assessment: `CompanyKPIAssessment`, `CompanyKPIEvidenceLink`, `EvidenceReviewAction`, `StewardshipAlert`, `CompanyRefreshRun`. |
| `capability_graph` | 5 | `Organisation` → `OrganisationCapability` (evidence-backed, scoped, verified) → `PublicRoute` (how a human actually reaches it). Deduplicated real-world org graph. |

Plus `partner_participation` (9), `collaboration_rooms` (9), `outreach_readiness` (7),
`public_action_preparation` (6), `public_need_discovery` (3), `ai_observatory` (3).

### The most important single finding

**A Khalifah decision layer already exists in `digital_twin`, and it is a gate, not
a score:**

```
SacredSourceReference   (tradition, surah/ayah, approved_translation,
                         translation_source, review_status, reviewed_by)
   └─> StewardshipPrinciple  (plain-language, M2M to sources)
         └─> StewardshipKPI  (formula_definition, formula_version,
                              scoring_direction, target_min/max,
                              warning_threshold, BLOCKING_THRESHOLD,
                              blocking_rule, evidence_requirements,
                              approval_status='requires_scholarly_review')
               └─> StewardshipAssessment (over a ModernisationScenario)
                     └─> HumanDecision → ImplementationAction → MeasuredOutcome
```

`blocking_threshold` + `blocking_rule` mean an intervention can be **refused**, not
merely scored lower. `approval_status` defaults to `requires_scholarly_review`, and
`SacredSourceReference.notes` defaults to a "requires scholarly review" note — the
system refuses to assert religious grounding it has not had reviewed.

`ModernisationScenario` carries `energy_impact`, `water_impact`, `waste_impact`,
`emissions_impact` — **each with its own `Unit` foreign key** — plus
`production_impact_pct`, `downtime_impact_hours`, `worker_impact`,
`community_impact`. Every impact field is `null=True`. This is already a
multi-dimensional, unit-safe, honest-about-unknowns comparison model.

---

## Verified inventory (main @ `3ea737a`)

| Metric | Value |
|---|---|
| Django apps | **82** |
| Apps with models | 44 |
| Apps with 0 models **and** 0 migrations | 36 |
| — of those, touching no ORM at all | **31** |
| `include()` mounts in root URLconf | **77** |
| `urls.py` files | 73 |
| `path()` declarations | 626 |
| Templates | 336 |
| Tests | **4,637** (green) |
| Python LOC in app packages | ~186,000 |

## Verified performance baseline (production, anonymous)

| Page | HTML | DOM elements | Time |
|---|---|---|---|
| `/healthz/` | **2 B** | — | 0.36 s |
| `/` | 149,354 B | 895 | 0.57 s |
| `/projects/` | 19,970 B | 145 | 0.39 s |
| `/about/` | 30,031 B | 209 | 0.38 s |
| `/khalifa-tours/` | 96,621 B | 708 | 1.44 s |
| `/ai-agents/` | 101,898 B | 1,185 | 2.46 s |
| `/companies/` | **1,180,739 B** | **20,599** | 1.09 s |
| `/league/` | **1,664,834 B** | 17,322 | **3.14 s** |

Server-side query counts (measured locally, empty test DB):
`/healthz/` 0 · `/projects/` 0 · `/about/` 2 · `/companies/` 4 · `/league/` 4 · `/` **12**

> The low query counts on `/companies/` and `/league/` matter: these are **not**
> N+1 problems. They are single queries whose full result set is rendered without
> pagination. Adding pagination fixes them; query optimisation would not.

## Verified homepage payload

| Asset | Bytes as served |
|---|---|
| **`img/hero/ecoiq-better-way-hero.png`** (`rel=preload`) | **2,592,714** |
| HTML document | 149,354 |
| `dist/ecoiq-islands.js` | 115,678 |
| `dist/ecoiq-islands.css` | 10,547 |
| `js/living-earth.js` | 9,555 |
| `js/hero-globe-v2.js` | 3,259 |
| `css/section-bg.css` | 1,492 |
| `brand/ecoiq-icon.svg` + `favicon.svg` | 1,331 |
| **Initial subtotal** | **≈ 2.88 MB** |
| *lazy:* `three.min.js` | 170,851 |
| *lazy:* `three-globe.min.js` | 144,713 |
| *lazy:* `countries-110m.geojson` | 188,893 |
| *lazy:* earth textures (2 × webp) | 110,708 |
| **Total** | **≈ 3.5 MB** |

Plus Google Fonts — Inter at 7 weights.

---

See [`PHASE_1_ARCHITECTURE.md`](PHASE_1_ARCHITECTURE.md) for the classification,
route inventory, redesign plan and PR sequence built on these figures.
