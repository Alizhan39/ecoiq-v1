# EcoIQ LegacySafe AI

**Permission-aware AI agents for enterprise legacy modernisation**

`New AI Agents Module — started today for hackathon`

---

## What existed before

EcoIQ existed before this hackathon as a climate intelligence and industrial modernisation
platform. On **2026-07-01**, we started building **EcoIQ LegacySafe AI** as a new AI agents
module inside EcoIQ. This new module adds permission-aware memory, deterministic retrieval
controls, lineage tracking, revocation, audit logs, and agentic legacy modernisation workflows
for the Conduct and BasedAI hackathon tracks.

## What was built today for the hackathon

The entire `legacy_safe` Django app: models, deterministic permission checks, filtered
retrieval, audit logging, cascading revocation, a mock modernisation planner, a NetworkX
dependency/lineage graph builder, an LLM provider abstraction, demo seed data, 10 web pages,
and 33 automated tests. Nothing in the pre-existing EcoIQ platform was rewritten — `legacy_safe`
was mounted with two lines: one `INSTALLED_APPS` entry and one `include()` in `ecoiq/urls.py`.

EcoIQ's unique contribution is the Justice & Maqasid Intelligence Layer: a governance layer
that evaluates enterprise modernisation not only for speed and cost, but also for fairness,
public harm reduction, resource stewardship, worker transition, community impact, and future
generations.

## Conduct bounty alignment

- Reads legacy documents, code snippets, process manuals, ESG reports, and policy documents
- Maps dependencies between systems, documents, teams, risks, and required changes
- Produces controlled change proposals and modernisation plans
- Supports human-in-the-loop approval (`ChangeProposal` draft → pending_approval → approved/rejected)

## BasedAI bounty alignment

- Permission-aware memory: every `MemoryChunk` and `DerivedMemory` carries its own `access_level`
- Access enforced **before** retrieval, never after generation, and never by asking an LLM
- Source lineage tracked from document → chunk → derived memory
- Revocation propagates: source → chunks → derived memories, in one call
- Audit log for every question, retrieval, blocked source, allowed source, and revocation

## Main demo flow

1. Dashboard (`/legacy-safe/`) — hackathon badge, Judge Demo Checklist, 6 capability cards
2. Ask Agent — ask a modernisation question, see only permission-cleared evidence in the answer
3. Permission Demo — the same question run as 4 roles side by side, plus a live prompt-injection safety check
4. Revocation Demo — revoke a source, watch its chunk and derived memory go dark in one request
5. Audit Logs — every action above already logged
6. Dependency Graph — NetworkX map of the demo project

## Architecture

```
legacy_safe/
  models.py       LegacyProject, SourceDocument, MemoryChunk, DerivedMemory, AuditLog, ChangeProposal
  services/
    permissions.py   deterministic access matrix (role × access_level → allow/deny)
    retrieval.py     permission-filtered keyword retrieval + audit logging
    planner.py       mock structured modernisation-plan generator (LLM seam for later)
    revocation.py    cascading revocation (source → chunks → derived memories)
    graph_builder.py NetworkX dependency/lineage graph → JSON
    llm_provider.py  provider abstraction (MockProvider shipped; others are typed stubs)
    audit.py         AuditLog writer
    seed_demo.py     idempotent demo data (Samruk Energy)
  views.py / urls.py  9 pages mounted at /legacy-safe/
  tests.py            27 tests
```

## Security model

Access decisions are pure functions of `(access_level, roles, is_revoked)`. No LLM is ever
asked whether a user may see something. A seeded "Malicious Prompt Injection Document" (public
access) proves document content is never treated as instructions, regardless of what it says.

## Permission-aware retrieval

`retrieve_allowed_chunks()` partitions every chunk in a project into `allowed`/`blocked` using
`can_access()` before any relevance scoring or answer generation happens. There is no code path
where restricted content reaches the planner (or a future LLM call) unfiltered.

## Revocation and lineage

`revoke_source_document()` marks the source, all its `MemoryChunk`s, and any `DerivedMemory`
naming it in `lineage` as revoked — in one call, no separate cleanup job. A derived summary can
never outlive the source it was built from.

## Audit logs

Every retrieval (`ask`), permission-demo run, and revocation writes an `AuditLog` row as a side
effect of the operation itself — user, action, question, decision, allowed/blocked sources, and
reason. The log can't drift from what actually happened because it's written by the same code
path that makes the decision.

## Repository and language support

Working today: any text content can be stored as a `SourceDocument`, tagged with a
`document_type` and `access_level`, and chunked into permission-aware memory — retrieval is
plain keyword overlap, not code-aware parsing. Roadmap only, not implemented in this hackathon
build: Tree-sitter/Semgrep-based parsing for Python, JavaScript/TypeScript, Java, COBOL, C/C++,
SQL, and ABAP, surfaced honestly at `/legacy-safe/repository-support/`.

## Model provider readiness

LegacySafe AI is model-agnostic. The permission layer sits before the model, so we can switch
between Claude, OpenAI-compatible endpoints, BasedAPIs, Mistral, GLM, local open-weight models,
or future code-focused agents without changing the security model.

`services/llm_provider.py` defines an `LLMProvider` interface. `MockProvider` (deterministic,
no network call, no API key) ships in this hackathon build. `OpenAICompatibleProvider` and
`AnthropicProvider` are typed stubs describing the integration seam for OpenAI-compatible
endpoints (including BasedAPIs, Mistral, GLM, or a local open-weight model) and Anthropic —
these are roadmap-ready, not already integrated. Every provider — including local/air-gapped
models — receives only permission-filtered context, and the same retrieval guard and audit logs
apply regardless of which provider is plugged in.

## Enterprise integration readiness

Roadmap, not connected in this build: SAP/ERP, Salesforce/CRM, Oracle databases, Workday/HR,
Jira, Confluence, ServiceNow, GitHub/GitLab, SAP Signavio, SAP LeanIX, ESG reporting systems,
and climate/asset data repositories — each mapped to a specific agent use case and the
permission risk it would need to handle, at `/legacy-safe/model-integration-readiness/`.

## Tests and verification

33 automated tests (`python manage.py test legacy_safe`): permission matrix (public/engineering/
finance/executive), Django group/superuser role mapping, retrieval filtering before planning,
the seeded prompt-injection document never widening access, revocation cascading to chunks and
derived memory, audit log creation, `MockProvider` running fully offline, and all 10 pages
returning 200 with their required content. All pages were also manually verified in a live
browser session.

## Roadmap after hackathon

- Wire `planner.py` to a real Anthropic/OpenAI call, with the injection-safety guarantee
  enforced by a system prompt
- Real embeddings + pgvector for retrieval instead of keyword overlap
- LangGraph multi-step agent workflow (retrieve → plan → propose → await approval)
- PyVis interactive rendering of the dependency/lineage graph
- Legacy code scanning via Semgrep/Tree-sitter feeding into `ChangeProposal`
- Real enterprise connectors (SAP, Jira, Confluence, ServiceNow, GitHub/GitLab, Salesforce)

## Intellectual property & public benefit

EcoIQ's core platform, brand, commercial workflows, proprietary scoring logic, the Justice &
Maqasid Intelligence framework, enterprise integrations, datasets, and patentable inventions are
intended to remain founder/company-owned intellectual property, subject to legal registration
and professional advice. No patents have been filed or granted at this stage.

Selected public-benefit components — such as educational templates, demo data, community
climate checklists, and selected non-commercial guides — may be shared for NGOs, schools,
vulnerable communities, and public benefit under an appropriate open or community-use licence,
to be determined separately. This repository currently has no `LICENSE` file.
