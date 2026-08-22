# Obsidian Bridge

Maps **EcoIQ knowledge areas** → **repository subsystems** → **authoritative
files**, so a question can be answered by opening two or three files instead of
scanning 70 apps.

## The two systems

| | holds | authority |
|---|---|---|
| **Obsidian vault** `~/Desktop/ecoiq` | why, decisions, strategy, sector knowledge | *rationale* |
| **This repository** | implementation | **code, always** |

The vault says so itself (Technology MOC): *"`~/ecoiq-v1` is the source of truth
for all code and configuration."* When they disagree, the code is right and the
note is stale.

**Nothing from the vault is copied here.** This file contains repository paths
and wiki-link names only.

### Vault entry points

`_MOC/EcoIQ MOC.md` is the front door. For code questions the useful ones are:

- `_MOC/Technology MOC.md` — architecture, AI, data, security, ADRs
- `07-Technology/Architecture/Implementation Status Map.md` — what actually
  works, classified
- `07-Technology/Architecture/Django Application Inventory.md` — every app
- `10-Decisions/Architecture Decisions/` — why a thing is shaped as it is

> **Staleness, partially resolved 2026-08-22.** Four notes were rewritten
> against the current architecture and now carry `updated: 2026-08-22`:
>
> - `07-Technology/Architecture/Frontend Architecture.md` — it described Django
>   templates as *"the actual runtime rendering layer"*
> - `07-Technology/Architecture/API Surface.md` — it documented v1 only
> - `07-Technology/Architecture/Implementation Status Map.md` — now defers to
>   `platform_registry/agents.py` as the authority
> - `_MOC/Technology MOC.md`
>
> **Everything else in the vault still predates the Evidence Integrity
> programme.** Notes dated `2026-08-12` contain no reference to
> `companies/eligibility.py`, `metric_registry`, `core/spa.py` or
> `core/access.py`. Use them for *why*; use this bridge for *where*.

---

## Evidence & Provenance

The core of the product. Start here for anything about scores being shown or
withheld.

| concern | file |
|---|---|
| **Publication decision** (authoritative) | `companies/eligibility.py` |
| Coverage, origins, public score state | `companies/evidence.py` |
| Confidence bands | `companies/confidence.py` |
| Provenance store, lineage, defensibility | `companies/provenance.py` |
| Metric definitions (material vs derived) | `companies/metric_registry.py` |
| Analyst declaration workflow | `companies/analyst.py` |
| Unknown semantics — the single authority | `core/unknown.py` |

**Entry point:** `companies.eligibility.decide(profile)` — the one place that
decides whether a score may be published. Every surface asks it.

**Contract:** `docs/product/FRONTEND_API_CONTRACT.md`
**Architecture:** `docs/product/EVIDENCE_INTEGRITY_FINAL.md`

Vault: [[Evidence Memory]], `02-Intelligence-Engine/Evidence/`

---

## Scoring

| engine | file | entry point |
|---|---|---|
| Composite + pillars | `companies/scoring.py` | `recalculate_and_save` |
| Ethics (NEI/TSS/RVI) | `ethics/scoring.py` | `compute_and_save` |
| Financing readiness | `financing/matching.py` | `compute_and_save` |
| QDF decision integrity | `qdf/scoring.py` | `compute_and_save` |
| Mizan balance | `mizan/scoring.py` | `score_and_record` |
| League composite | `league/models.py` | `Company.compute_score` |

All record provenance. None fabricates a value for a missing input.

Vault: [[Intelligence Engine MOC]], `03-Ethical-Framework/`

---

## ML & analytical outputs

| output | file |
|---|---|
| ML company score (GBR) | `ml/scoring_model.py` |
| 12-month forecast | `ml/prediction.py` |
| Greenwashing risk | `ml/ethics/greenwashing_risk.py` |
| Responsible finance | `ml/responsible_finance.py` |
| Feature extraction | `ml/features.py` |
| Model identity / artefact digest | `ml/model_identity.py` |

**Audit:** `docs/product/ML_PROVENANCE_AUDIT.md`

---

## Platform truth (counters & module status)

| concern | file |
|---|---|
| Canonical module registry | `platform_registry/agents.py` |
| Counter service (SSOT) | `platform_registry/stats.py` |
| API | `api/v2_platform.py` |

No count may be hard-coded anywhere else. `ai_agents/` is **documentation** —
298 markdown files, zero Python — and is counted separately as
`specification_packs`.

---

## Intelligence Engine

| concern | file |
|---|---|
| Compute | `intelligence/compute.py` |
| Models | `intelligence/models.py` |
| Routes | `intelligence/urls.py` |

Status **EXPERIMENTAL** (`platform_registry/agents.py`). The vault's
`02-Intelligence-Engine/` describes the intended ten-stage loop; the
implementation is narrower. Trust the registry for status.

Vault: [[Intelligence Engine MOC]], [[Intelligence Engine Architecture]]

---

## Ingestion

| concern | file |
|---|---|
| Pipeline | `ingestion/pipeline.py` |
| Provenance writer | `ingestion/provenance.py` |

Writes `INFERRED`, never `MEASURED` — an LLM reading a PDF is an assessment,
not a measurement. See `ingestion/provenance.py` module docstring.

---

## API

| version | files | use |
|---|---|---|
| **v2 (canonical)** | `api/v2_urls.py`, `api/v2_views.py`, `api/v2_serializers.py`, `api/v2_platform.py` | all new work |
| v1 (legacy) | `api/urls.py`, `api/views.py` | compatibility only |

Vault: `07-Technology/APIs/`, [[API Surface]]

---

## Frontend

| layer | path | runtime? |
|---|---|---|
| **Public product SPA** | `frontend/web/` | yes |
| Build-time Django islands | `frontend/app/` | no → `static/dist/` |
| Offline video authoring | `frontend/remotion/` | no |
| Django templates | `templates/` | yes (being reduced) |

**Entry point:** `frontend/web/src/main.tsx` → `src/app/App.tsx` → `src/app/routes.tsx`
**Contract types:** `frontend/web/src/types/evidence.ts`

### How Django serves it

| concern | file |
|---|---|
| Shell, per-route `<head>`, catch-all | `core/spa.py` |
| Immutable caching for the Vite bundle | `core/whitenoise.py` |
| Which experimental surfaces require sign-in | `core/access.py` |
| De-published leaves under a public `/companies/<slug>/` | `core.access.COMPANY_LEAF_SUFFIXES` |
| Permanent redirects to React pages | `core/redirects.py` |
| What actually survives as a Django HTML route, measured | `docs/product/FINAL_TEMPLATE_MIGRATION.md` § Phase 10 |
| Client-side title map (mirrors `spa.ROUTE_META`) | `frontend/web/src/app/documentTitle.ts` |

**One origin.** No second hostname, no static host, no SSR — the API is
session-authenticated and a second origin would mean `SameSite=None` cookies
and CORS for no product gain. `docs/product/FRONTEND_DEPLOYMENT.md`

**Not routed on purpose:** `/companies/<slug>/`. The server-rendered
organisation page carries eleven panels the React page does not; the audit and
the decision for each are in `docs/product/COMPANY_PAGE_PANELS.md`.

**Route inventory:** `docs/product/FINAL_TEMPLATE_MIGRATION.md` — all 102
anonymous server-rendered routes classified.
**Migration state:** `docs/product/FRONTEND_MIGRATION_MATRIX.md`
**Audit:** `docs/product/FRONTEND_AUDIT.md`

Vault: [[Frontend Architecture]]

---

## Deployment

| concern | file |
|---|---|
| Service definition | `render.yaml` |
| Build | `build.sh` |
| Pre-deploy (migrations) | `predeploy.sh` |
| Start | `start.sh` |
| Settings | `ecoiq/settings.py` |
| Health check | `/healthz/` (`core/`) |

Vault: `07-Technology/Infrastructure/`, `07-Technology/Runbooks/`

---

## Where the docs live

| document | answers |
|---|---|
| `EVIDENCE_INTEGRITY_FINAL.md` | the whole evidence architecture and its limits |
| `FRONTEND_API_CONTRACT.md` | what React may rely on |
| `FRONTEND_MIGRATION_MATRIX.md` | every route, classified |
| `ML_PROVENANCE_AUDIT.md` | which ML modules exist and their status |
| `D4_FIELD_CLASSIFICATION.md` | why each field is nullable |
| `CALCULATION_CONTEXT_PROVENANCE.md` | inputs that have no provenance rows |

---

## Maintenance

Update this file when a **subsystem moves or is added** — not when code inside
one changes. A bridge that tracks line numbers is a bridge nobody trusts.
