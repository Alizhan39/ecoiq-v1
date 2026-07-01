# EcoIQ — AI Industrial Audit Platform

An AI-powered facility modernisation platform that analyses industrial operations and delivers McKinsey-grade audit reports with ranked recommendations, ROI analysis, and phased implementation roadmaps.

Built with Django, Anthropic Claude, and WeasyPrint. Synchronous architecture — no workers, no containers, just `python manage.py runserver`.

---

## Hackathon Work Started Today

EcoIQ existed before this hackathon as a climate intelligence and industrial modernisation
platform. On **2026-07-01**, we started building **EcoIQ LegacySafe AI** as a new AI agents
module inside EcoIQ. This new module adds permission-aware memory, deterministic retrieval
controls, lineage tracking, revocation, audit logs, and agentic legacy modernisation workflows
for the **Conduct AI** and **BasedAI** bounties.

Everything below in this section (and the `legacy_safe` Django app) is new as of today. The
rest of this README describes the pre-existing EcoIQ platform. See also
[`legacy_safe/DEMO_SCRIPT.md`](legacy_safe/DEMO_SCRIPT.md) for the 60-second pitch and 3-minute
walkthrough, [`legacy_safe/PITCH.md`](legacy_safe/PITCH.md) for shorter pitches, and
[`legacy_safe/SUBMISSION_SUMMARY.md`](legacy_safe/SUBMISSION_SUMMARY.md) for the full hackathon
submission writeup.

`New AI Agents Module — started today for hackathon`
&nbsp;·&nbsp; `Conduct-aligned: enterprise legacy modernisation`
&nbsp;·&nbsp; `BasedAI-aligned: permission-aware memory and model-provider readiness`
&nbsp;·&nbsp; `Repository-aware`
&nbsp;·&nbsp; `Language-aware`
&nbsp;·&nbsp; `Permission-aware`
&nbsp;·&nbsp; `Model-provider-ready`

### Project: EcoIQ LegacySafe AI

**One-line:** A permission-aware agentic change-management layer that lets enterprises
modernise legacy systems without ever leaking restricted content through an LLM.

LegacySafe AI plans the full EcoIQ modernisation pathway: solar PV, battery storage, heat
pumps, boiler replacement, insulation, smart meters, IoT sensors, grid optimisation,
procurement, finance, process optimisation, worker transition, and Justice/Maqasid governance.

### Problem

Enterprises sit on decades of legacy systems, code, process manuals, and reports. Modernising
them safely requires reading sensitive, mixed-permission material — but handing all of that
material to an LLM at once means access control disappears the moment retrieval happens.

### Solution

LegacySafe AI is a permission-aware, agentic change-management layer. It retrieves only the
legacy content a specific user is allowed to see, tracks the lineage of every derived summary
back to its sources, propagates revocation automatically, and logs every access decision —
before any content ever reaches a model or a user.

### Why Conduct

- Reads legacy documents, code snippets, process manuals, ESG reports, and policy documents
- Maps dependencies between systems, documents, teams, risks, and required changes
- Produces controlled change proposals and modernisation plans
- Supports human-in-the-loop approval (`ChangeProposal` status workflow)

### Why BasedAI

- Permission-aware memory: `MemoryChunk` and `DerivedMemory` carry an explicit `access_level`
- Access enforced **before** retrieval, not after LLM generation
- Deterministic permission checks (`legacy_safe/services/permissions.py`) — never an LLM decision
- Source lineage tracked from raw document → chunk → derived memory
- Revocation propagates: source document → its chunks → any derived memory built from it
- Audit log (`AuditLog`) for every question, retrieval, blocked source, allowed source, and revocation

### Architecture

```
legacy_safe/
  models.py            LegacyProject, SourceDocument, MemoryChunk, DerivedMemory,
                        AuditLog, ChangeProposal
  services/
    permissions.py      deterministic access matrix (role × access_level → allow/deny)
    retrieval.py         permission-filtered keyword retrieval + audit logging
    planner.py           mock structured modernisation-plan generator (LLM seam for later)
    revocation.py        cascading revocation (source → chunks → derived memories)
    graph_builder.py      NetworkX dependency/lineage graph → JSON
    audit.py             AuditLog writer
    seed_demo.py          idempotent demo data (Samruk Energy)
  views.py / urls.py     dashboard, ask agent, permission demo, audit logs,
                          dependency graph, revocation demo — mounted at /legacy-safe/
```

### Demo flow

1. **Dashboard** (`/legacy-safe/`) — module overview, Conduct/BasedAI alignment, hackathon badge
2. **Ask Agent** (`/legacy-safe/ask/`) — ask "What is the full industrial modernisation plan,
   from solar panels and equipment upgrades to process optimisation?" and see the answer built
   only from evidence you're allowed to see
3. **Permission Demo** (`/legacy-safe/permission-demo/`) — the same question run as four roles
   (public, engineering, finance, executive) side by side
4. **Audit Logs** (`/legacy-safe/audit-logs/`) — every retrieval decision, logged
5. **Dependency Graph** (`/legacy-safe/dependency-graph/`) — NetworkX nodes/edges for the demo project
6. **Revocation Demo** (`/legacy-safe/revocation-demo/`) — revoke a source and watch its chunks
   and derived memories go dark in the same request

### Security model

- Access decisions are pure functions of `(access_level, roles, is_revoked)` — no LLM is ever
  asked whether a user may see something
- A seeded "Malicious Prompt Injection Document" (public access) demonstrates that document
  *content* is never treated as instructions, regardless of what it says
- Revoked sources and their derived memories are excluded from retrieval unconditionally

### Permission-aware memory

Every `MemoryChunk` and `DerivedMemory` stores its own `access_level` (public / engineering /
finance / executive) rather than inheriting it implicitly at read time. `retrieve_allowed_chunks()`
partitions every chunk in a project into `allowed` / `blocked` *before* any relevance scoring or
answer generation happens, by calling the deterministic `can_access()` matrix in
`services/permissions.py`. There is no code path where restricted content reaches the planner
unfiltered.

### Revocation

`revoke_source_document()` in `services/revocation.py` does three things in one call: marks the
`SourceDocument` revoked, marks all of its `MemoryChunk`s revoked, and marks any `DerivedMemory`
whose `lineage` names that document as revoked. A derived summary can never outlive the source
it was built from — there is no separate cleanup job or delay.

### Audit log

Every retrieval (`ask`), every permission-demo run, and every revocation writes an `AuditLog`
row via `services/audit.py` — recording the acting user (or `None` for anonymous), the action,
the question asked, the decision, the allowed/blocked source titles, and a reason. The log is
written as a side effect of the operation itself, not reconstructed afterwards, so it can't
drift from what actually happened.

### Tech stack

Django, PostgreSQL, Django auth groups, NetworkX (dependency/lineage graph). Planned:
pgvector (semantic retrieval), LangGraph (agent workflow), LlamaIndex, pycasbin, PyVis
(interactive graph rendering), Pydantic/Instructor (structured LLM output), Semgrep/Tree-sitter
(legacy code scanning), Langfuse (observability), Ragas (evaluation).

### Roadmap

- Wire `planner.py` to a real Anthropic/OpenAI call, with the injection-safety guarantee
  enforced by a system prompt (never just relying on retrieval filtering)
- Real embeddings + pgvector for retrieval instead of keyword overlap
- LangGraph multi-step agent workflow (retrieve → plan → propose → await approval)
- PyVis interactive rendering of the dependency/lineage graph
- Legacy code scanning via Semgrep/Tree-sitter feeding into `ChangeProposal`

### Model + Enterprise Integration Readiness

This is our own hackathon MVP, built inside EcoIQ and inspired by the Conduct AI and BasedAI
bounty requirements — not a clone of either. See the full breakdown at
`/legacy-safe/model-integration-readiness/`.

**LegacySafe AI is model-agnostic.** The permission layer sits before the model, so we can
switch between Claude, OpenAI-compatible endpoints, BasedAPIs, Mistral, GLM, local open-weight
models, or future code-focused agents without changing the security model.

#### Model Switching & Open-Weight Readiness

- The current hackathon MVP uses `MockProvider` — a deterministic provider where needed; no
  external API calls are required for the demo
- Future providers can include Anthropic Claude, OpenAI-compatible endpoints, BasedAPIs,
  Mistral, GLM, and local open-weight models — **roadmap-ready, not already integrated**
- Future code-focused agents can analyse repositories, but only after permission-aware retrieval
- The model never receives blocked finance, engineering, or executive memory
- The same retrieval guard and audit logs apply regardless of model provider
- This supports lower cost, data sovereignty, and enterprise flexibility

```
User request → Permission Guard → Allowed context only → Selected model provider → Agent output → Audit log
```

- **Provider abstraction** — `services/llm_provider.py` defines `LLMProvider`, with `MockProvider`
  (fully deterministic, no network call, no API key) shipped for the hackathon, and typed stubs
  for `OpenAICompatibleProvider` and `AnthropicProvider` describing the integration seam
- **Open-weight model readiness** — the same provider interface accommodates BasedAPIs, Mistral,
  GLM, or a locally hosted open-weight model; permission filtering never changes based on which
  provider is plugged in
- **OpenAI-compatible endpoint readiness** — any drop-in-compatible chat completions server can
  implement `OpenAICompatibleProvider.generate()` without touching retrieval or permissions
- **Data sovereignty design** — every provider, including local/air-gapped models, receives only
  permission-filtered `allowed_context`; no provider ever sees blocked finance, engineering, or
  executive memory
- **Enterprise integrations roadmap** — SAP/ERP, Salesforce/CRM, Oracle databases, Workday/HR,
  Jira, Confluence, ServiceNow, GitHub/GitLab, SAP Signavio, SAP LeanIX, ESG reporting systems,
  and climate/asset data repositories, each mapped to a specific agent use case and the
  permission risk it handles
- **Conduct-style lifecycle mapping** — business change request → classify → find affected
  systems/documents/code → build dependency graph → generate change proposal → audit trail →
  human approval → testing checklist
- **BasedAI-style AI workforce mapping** — five specialised agents (Legacy Scanner, Permission
  Guard, Dependency Mapper, Modernisation Planner, Audit & Compliance), each with a defined
  input, output, and optimisation value

### AI Agent Ecosystem 200

A curated, 17-category roadmap of open-source agent, RAG, permissions, code-analysis, evaluation,
security, document-ingestion, workflow-automation, frontend, MCP, climate/ESG, geospatial, data
science, and justice/responsible-AI repositories that could strengthen LegacySafe AI — plus a
dedicated Microsoft/Enterprise AI Stack section (AutoGen, Semantic Kernel, GraphRAG, Presidio,
MarkItDown, Playwright, TypeScript, VS Code, and an Azure OpenAI-ready deployment option). Every
entry is labelled MVP now, Next integration, Roadmap-ready, or Research watchlist — nothing is
claimed as already integrated beyond what's genuinely true today. See
[`legacy_safe/AI_AGENT_ECOSYSTEM_200.md`](legacy_safe/AI_AGENT_ECOSYSTEM_200.md) and
`/legacy-safe/ai-agent-ecosystem-200/`.

### Microsoft Ecosystem Readiness

An architecture-alignment layer mapping LegacySafe AI onto a Microsoft-style enterprise AI
project pattern (User → Agent → Model, Data → Action) and a Design Thinking flow (Empathise →
Define → Ideate → Prototype → Test), for industrial modernisation across energy, factories,
heating, water, mining, logistics, and public-sector infrastructure — not just the Samruk
Energy demo scenario. Includes a Microsoft ecosystem mapping (Azure AI, Fabric, Digital Twins,
IoT, Entra ID, Power BI, Teams/Copilot, SharePoint, GitHub Copilot), a Microsoft open-source
tools table (AutoGen, Semantic Kernel, GraphRAG, Presidio, MarkItDown, Playwright, TypeScript,
VS Code), a suggested pilot proposal, enterprise safety principles, and questions for Microsoft
advisers. The current hackathon MVP does not claim full Microsoft/Azure integration — every
item is marked MVP now, Next integration, Roadmap-ready, or Research watchlist. See
[`legacy_safe/MICROSOFT_ECOSYSTEM_READINESS.md`](legacy_safe/MICROSOFT_ECOSYSTEM_READINESS.md)
and `/legacy-safe/microsoft-ecosystem-readiness/`.

### Justice & Maqasid Intelligence Layer

A hackathon MVP and conceptual governance layer — not a certified ethics or compliance
product — at `/legacy-safe/justice-maqasid/`.

- **Why EcoIQ adds justice beyond efficiency** — most enterprise AI tools optimise
  modernisation plans for speed, cost, and efficiency alone. EcoIQ adds a justice and
  stewardship review so plans are also evaluated for human impact, worker transition,
  community protection, environmental stewardship, fair cost/benefit allocation, future
  generations, and governance accountability
- **How this differentiates EcoIQ from normal enterprise AI** — a Justice-Aware Agent Workflow
  (Permission Guard → Evidence Retrieval → Conduct-style Legacy Analysis → Maqasid Justice
  Review Agent → Future Generations Impact Agent → Worker & Community Risk Agent → Final Just
  Transition Plan → Audit Log) runs alongside the existing permission-aware retrieval pipeline,
  so a modernisation answer isn't just permission-filtered — it's reviewed for fairness before
  being presented as final
- **How it supports responsible climate transition** — a coal-to-clean-heat plan, for example,
  is checked not only for emissions reduction but for whether the transition's costs land
  unfairly on vulnerable households, workers, or future generations
- **How it connects to Maqasid, amanah, khalifa stewardship, and intergenerational justice** —
  presented professionally, not as religious preaching: six evaluation principles (Hifz
  al-Nafs/life, Hifz al-Aql/intellect, Hifz al-Mal/wealth, Hifz al-Nasl/family & future
  generations, Hifz al-Din/values, and Amanah/Khalifa stewardship of the Earth) are reframed as
  plain modernisation-planning questions, each with an example risk and mitigation
- **Why this matters for emerging markets and industrial modernisation** — coal-to-clean-heat
  and similar transitions in emerging markets carry real risk of unfair cost transfer to
  workers and low-income households; a justice-aware review layer surfaces that risk before a
  plan is finalised, not after
- Five conceptual agents (Justice Review, Maqasid Impact, Future Generations, Worker &
  Community, Amanah Stewardship) and a set of demo "Justice Metrics" scorecards — explicitly
  labelled as demo evaluation dimensions, not final production scores

### Intellectual Property & Public Benefit

EcoIQ's core platform, brand, commercial workflows, proprietary scoring logic, the Justice &
Maqasid Intelligence framework, enterprise integrations, datasets, and patentable inventions are
intended to remain founder/company-owned intellectual property, subject to legal registration
and professional advice. No patents have been filed or granted at this stage, and nothing in
this repository should be read as claiming otherwise.

Selected public-benefit components — such as educational templates, demo data, community
climate checklists, and selected non-commercial guides — may be shared for NGOs, schools,
vulnerable communities, and public benefit under an appropriate open or community-use licence,
to be determined separately. This repository currently has no `LICENSE` file; no licence terms
are implied by this note, and none are changed by it.

---

## Features

- **Two-call AI orchestration** — Diagnostic (findings + root causes) → Recommendations (ROI + roadmap)
- **Enterprise audit reports** — 6 sections: Executive Summary, Projections, Before/After, Findings, Recommendations, Roadmap
- **PDF export** — Server-side WeasyPrint A4 PDFs
- **Priority scoring** — Composite score from ROI speed, complexity, savings scale, and quick-win status
- **Demo seeder** — Pre-built Oil Refinery and Logistics Warehouse demos

---

## Quick Start

```bash
# 1. Clone and set up virtual environment
git clone <repo-url>
cd ecoiq-v1
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 4. Apply migrations
python manage.py migrate

# 5. Run the development server
python manage.py runserver
```

Open http://127.0.0.1:8000/ in your browser.

---

## Seeding Demo Data

Run the built-in demo seeder to create two fully analysed example facilities:

```bash
# Both demos (Oil Refinery + Logistics Warehouse) — takes ~6-10 min
python manage.py seed_demos

# Single demo
python manage.py seed_demos --name refinery
python manage.py seed_demos --name warehouse

# Create sessions only, skip AI (useful for testing UI without API calls)
python manage.py seed_demos --skip-ai

# Re-create even if already exists
python manage.py seed_demos --force
```

---

## Project Structure

```
ecoiq-v1/
├── audit/                   # Industrial audit app
│   ├── models.py            # AuditSession, Finding, Recommendation, ActionPlan, AuditReport
│   ├── views.py             # All views + report context builder
│   ├── ai.py                # Two-call AI orchestration (diagnostic + recommendations)
│   ├── forms.py             # AuditSessionForm
│   ├── questions.py         # Questionnaire definitions
│   ├── urls.py              # Audit URL patterns
│   ├── templatetags/
│   │   └── audit_tags.py    # fmt_usd, fmt_num, fmt_usd_compact filters
│   └── management/commands/
│       └── seed_demos.py    # Demo data seeder
├── core/                    # ESG core app
├── templates/audit/         # All audit templates
│   ├── report.html          # Full enterprise web report
│   └── report_pdf.html      # WeasyPrint A4 PDF version
├── requirements.txt
├── .env.example
└── manage.py
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Your Anthropic API key (`sk-ant-...`) |
| `DJANGO_SECRET_KEY` | Yes (prod) | Django secret key — change in production |
| `DEBUG` | No | `True` for development, `False` for production |

---

## AI Model & Token Budget

| Call | Model | Max Tokens | Purpose |
|---|---|---|---|
| Diagnostic | `claude-sonnet-4-6` | 4,000 | 6–10 findings with root causes and financial impact |
| Recommendations | `claude-sonnet-4-6` | 16,000 | 6–10 recommendations + roadmap + projections |

A complete analysis typically takes 3–5 minutes.

---

## Tech Stack

- **Backend** — Django 5.2, SQLite, Python 3.11
- **AI** — Anthropic Claude (`claude-sonnet-4-6`) via `anthropic` SDK
- **PDF** — WeasyPrint 68.1 (server-side A4 rendering)
- **Document parsing** — pypdf (PDF text extraction)

---

## Deploying to Railway (recommended)

Railway provides free-tier hosting with zero-config Django support.

### 1. Install Railway CLI
```bash
npm install -g @railway/cli   # or brew install railway
railway login
```

### 2. Create a new project and deploy
```bash
railway init          # creates new Railway project
railway up            # deploys from current directory
```

### 3. Set environment variables in Railway dashboard
| Variable | Value |
|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-...` (your key) |
| `DJANGO_SECRET_KEY` | Generate with: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `yourapp.up.railway.app` (Railway gives you this URL) |
| `CSRF_TRUSTED_ORIGINS` | `https://yourapp.up.railway.app` |

### 4. First deploy runs automatically
- `migrate` runs via the `release` phase in `Procfile`
- `collectstatic` runs during Nixpacks build
- WeasyPrint system libraries (Cairo, Pango) are installed via `nixpacks.toml`

> **Note on SQLite + Railway:** Railway's filesystem is ephemeral — data resets on redeploy. For a persistent production database, upgrade to PostgreSQL (Railway has a one-click Postgres plugin). When ready, set `DATABASE_URL` and add `dj-database-url` to requirements.

---

## Deploying to Render (alternative)

1. Create a new **Web Service** pointing at your GitHub repo
2. Build command: `pip install -r requirements.txt && python manage.py collectstatic --no-input && python manage.py migrate`
3. Start command: `gunicorn ecoiq.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 300`
4. Add the same environment variables as above

---

## Generating a Secure Secret Key

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Set this as `DJANGO_SECRET_KEY` in your platform's environment variables. Never commit it.

---

## Roadmap (Future)

- [ ] PostgreSQL + Celery async analysis
- [ ] Multi-tenant with Wagtail CMS
- [ ] Sector benchmarking database
- [ ] Interactive charts (Chart.js)
- [ ] Email delivery of PDF reports
- [ ] CI/CD deployment (Railway / Render)
