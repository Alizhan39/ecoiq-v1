# EcoIQ

**Evidence-backed decision intelligence for companies, investments and
projects.**

EcoIQ assesses organisations and shows exactly how much evidence sits behind
every answer — and how good that evidence is. When the evidence does not
support a number, EcoIQ shows the gap instead of the number.

---

## The rule the system is built around

> **Unknown is `null`. Never `0`, never `50`, never a substitute.**

A score of `0` means an organisation was assessed at zero. A missing score is
missing. The distinction is enforced by the schema, the calculators, the API,
the TypeScript types and a lint rule — not by convention.

---

## Architecture

```
React / TypeScript            frontend/web — public product SPA
        │                     Vite · React Router · strictNullChecks
        ▼
      API v2                  api/v2_* — the canonical contract
        │                     score · score_status · evidence_coverage
        │                     confidence · rank
        ▼
      Django 5.2              70 apps, session auth, DRF
        │
        ▼
Decision / Evidence /         companies/{evidence,provenance,eligibility,
Provenance engines            confidence,metric_registry,scoring}.py
        │                     ethics/ · financing/ · qdf/ · mizan/ · ml/
        ▼
    PostgreSQL
```

Three frontend directories, **none** of which is a runtime dependency:

| path | what | built to |
|---|---|---|
| `frontend/web` | public product SPA | `static/spa/` — committed |
| `frontend/app` | React islands for the server-rendered pages | `static/dist/` — committed |
| `frontend/remotion` | offline video authoring | not deployed |

Django serves the SPA itself, from one origin — no second hostname, no separate
static host, no SSR framework. Render's build runs Python only; the built SPA
is committed, and CI rebuilds it and fails the PR if the committed artefact
does not match a fresh build.

After changing anything under `frontend/web/src`:

```bash
npm --prefix frontend/web ci && npm --prefix frontend/web run build
```

and commit `static/spa/` with the source change.

See [`docs/product/FRONTEND_DEPLOYMENT.md`](docs/product/FRONTEND_DEPLOYMENT.md)
for the routing, the catch-all's exclusions, the SEO position and the rollback.

---

## Evidence integrity

Four concepts, deliberately separate. Collapsing any two was the original
defect.

| concept | question | authority |
|---|---|---|
| **Provenance** | where did this number come from? | `companies/provenance.py` |
| **Coverage** | how much of what we need is supported? | `companies/evidence.py` |
| **Confidence** | how good is that support? | `companies/confidence.py` |
| **Review** | did a person look? | `companies/analyst.py` |

Provenance is per-metric and append-only. Derived values record the exact
provenance **rows** they consumed, so history stays pinned to what was actually
read. Defensibility is transitive — contamination anywhere beneath a value
disqualifies it.

**Publication requires full coverage.** Seeded and legacy data can never
satisfy it, however much of it exists.

Full architecture: [`docs/product/EVIDENCE_INTEGRITY_FINAL.md`](docs/product/EVIDENCE_INTEGRITY_FINAL.md)

---

## Product status

Statuses come from the code-owned registry
([`platform_registry/agents.py`](platform_registry/agents.py)). This README
does **not** restate counts that can drift — read them from
`GET /api/v2/platform/`.

| tier | what it means |
|---|---|
| **Production** | active path, meaningful tests, dependencies available, and an evaluation basis |
| **Beta** | real code and tests; evaluation incomplete |
| **Experimental** | working experiment, no readiness claim |
| **Planned** | not functional |

**There are no production AI agents.** No LLM-backed module has a measured
evaluation, and for a generative system output quality is precisely what an
evaluation measures. The production modules are **deterministic engines** —
formulas pinned by tests, recording provenance for every value they write.
That is a different claim from "our AI is validated", and the difference is
deliberate.

`ai_agents/` contains **298 markdown files and no Python**. Those are
training-pack specifications — designs, not running software — and are counted
separately.

---

## Running locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8731
```

```bash
cd frontend/web
npm ci
npm run dev          # :5173, proxies /api to :8731
```

Or, to see it exactly as production serves it — Django rendering the built
shell — run `npm run build` and use `:8731`.

---

## Testing

```bash
python manage.py test          # backend
ruff check .
python manage.py makemigrations --check --dry-run

cd frontend/web
npm run typecheck && npm run lint && npm test && npm run build
```

CI runs `ruff`, `mypy`, Django checks, the full suite, Gitleaks, a mobile gate
and the frontend job on every PR. The frontend job rebuilds `static/spa/` from
a clean `npm ci` and fails if the committed artefact is stale — a committed
build artefact is only trustworthy if something proves it matches its source.

---

## Deployment

One Render web service and one PostgreSQL database. Migrations run in
`preDeployCommand`, so a failing migration fails the deploy rather than serving
half-migrated.

**Redis and Celery are not deployed.** They are commented out in `render.yaml`.
The code contains `@shared_task` definitions, which makes it look otherwise —
nothing in the request path calls them asynchronously.

Runbook: [`docs/operations/PRODUCTION_RUNBOOK.md`](docs/operations/PRODUCTION_RUNBOOK.md)

---

## Limitations

Stated because a README listing only capabilities is a brochure.

- **No organisation currently has a published score.** All 467 carry legacy
  provenance, so coverage is 0% and the product says so. This is the system
  working, not failing.
- **No AI evaluation has been performed.** Citation precision, groundedness and
  hallucination rate are unmeasured.
- **No certifications.** Not SOC 2 audited, not ISO certified.
- **No case studies.** No project has been executed through to measured
  outcome.
- **`ml.predicted_12m` lineage is partial** — its primary path reads
  `ScoreHistory`, which carries no provenance.
- **Single web instance, no staging, no tested restore.**

---

## Navigating this repository

Start with [`docs/repo-map/OBSIDIAN_BRIDGE.md`](docs/repo-map/OBSIDIAN_BRIDGE.md)
— it maps knowledge areas to subsystems and authoritative files, so a question
takes two files rather than a scan of 70 apps.

Code is the source of truth. Where a document disagrees with it, the code is
right.
