---
name: ecoiq-engineering-os
description: Routing map for EcoIQ's project-native skills. Use when a task touches EcoIQ domain work — evidence, formulas, the Khalifah loop, regulation, impact claims, brand, discoverability, growth, prototypes, video, external research, security, or release validation — and you need to pick which single ecoiq-* skill applies. Not for ordinary code edits that no ecoiq-* skill covers.
---

# EcoIQ Engineering OS — router

One job: pick the **smallest** set of skills for the task, then stop. This
file is a map, not a checklist. Loading every skill is a bug.

Frontend/design/motion routing is **not** here — that lives in
[`docs/AI-SKILL-ROUTER.md`](../../../docs/AI-SKILL-ROUTER.md) and is
unchanged. This router covers the domain, governance, and go-to-market
layers that sit beside it.

## Route table

| If the task is about… | Use | Not |
|---|---|---|
| Tracing company → KPI → evidence → assessment → finding → remediation | `ecoiq-evidence-audit` | `ecoiq-impact-claims` (that's about the *claim*, not the chain) |
| Where a feature sits in DETECT→…→REPEAT, or wiring a new stage | `ecoiq-khalifah-loop` | `ecoiq-khalifah-engine` (that answers *what to do*, not *where code goes*) |
| Answering a decision question across the loop, with every claim labelled | `ecoiq-khalifah-engine` | `ecoiq-khalifah-loop` (that's the architecture question) |
| A regulation, jurisdiction, effective date, or compliance conclusion | `ecoiq-regulatory-review` | — |
| A green / impact / emissions / savings claim shown to a user | `ecoiq-impact-claims` | — |
| Authn/authz, tenancy, uploads, R2, Celery, Redis, LLM input, secrets | `ecoiq-security-review` | The generic `security-review` skill (it has no EcoIQ context) |
| "Is this done?" — what to run before reporting completion | `ecoiq-release-gate` | — |
| Logo, colour, type, tone, Khalifah AI presentation, Islamic terminology | `ecoiq-brand` | `ui-ux-pro-max:brand` (generic; EcoIQ tokens win — see rule 1) |
| Crawlability, metadata, canonical, sitemap, schema, hreflang, AI search | `ecoiq-seo-audit` | — |
| Positioning, ICPs, landing pages, lead magnets, email, CRO, experiments | `ecoiq-growth` | — |
| A throwaway dashboard/calculator/simulator to explore an idea | `ecoiq-prototype` | Anything that will ship as-is — prototypes never bypass the backend |
| An evidence-based explainer or pitch video | `ecoiq-remotion` | Adding Remotion to the Django runtime — it is build-time only |
| Bringing an external source (NotebookLM, PDF, report) into EcoIQ | `ecoiq-research-ingest` | Automated login to any external account |
| Creating a *new* EcoIQ skill | `ecoiq-skill-creator` | — |

## Five invariants every skill inherits

These are enforced by the codebase, not by this file's good intentions. Each
links to the canonical source — read that, don't restate it from memory.

1. **AI output is never verified evidence.** `hikma.Evidence.confidence_tier`
   defaults to `ai-seeded` and `scholar_review_required` defaults to `True`
   ([`hikma/models.py`](../../../hikma/models.py)). `EvidenceMemory` carries
   `verification_status` / `review_tier` / `reviewer`
   ([`evidence_memory/models.py`](../../../evidence_memory/models.py)).
   Promotion to a verified tier is a human act.
2. **Never fabricate a number, citation, regulation, or Qur'anic reference.**
   Already the platform's system prompt — see the WHAT YOU MUST NOT DO block
   in [`ai_gateway/prompts.py`](../../../ai_gateway/prompts.py). Absence of
   data is a valid answer.
3. **Qur'anic and Arabic terminology is internal-only.** Public pages, API
   responses, and marketing use professional English principle names.
   Canonical rule and mapping:
   [`docs/governance-principles-surah-map.md`](../../../docs/governance-principles-surah-map.md).
4. **Deterministic decisions are never delegated to an LLM** — permissions,
   access control, scoring, and money. See
   [`docs/AI-QUALITY-GATES.md`](../../../docs/AI-QUALITY-GATES.md) §7 and
   `legacy_safe/services/permissions.py`.
5. **A system prompt is server-assembled and unreachable from user input.**
   `ai_gateway/service.py` refuses client `system`-role messages. Any new AI
   surface reuses that gateway; it does not build a second one.

## Provenance

Every third-party component this OS drew on is recorded in
[`docs/THIRD-PARTY-INTEGRATIONS.json`](../../../docs/THIRD-PARTY-INTEGRATIONS.json)
with its source URL, pinned version, licence, and what was adapted. Nothing
was vendored wholesale; no installer, hook, or MCP server from any candidate
repository was executed. Rationale per candidate is in
[`docs/ECOIQ-ENGINEERING-OS.md`](../../../docs/ECOIQ-ENGINEERING-OS.md).

Third-party **skills** installed under `.claude/skills/` (frontend-design,
canvas-design, algorithmic-art, theme-factory, web-artifacts-builder,
systematic-debugging, obsidian-markdown, context-optimization,
context-compression) and the Excel MCP server are audited separately in
[`docs/ai-tooling/THIRD_PARTY_SKILLS_AUDIT.md`](../../../docs/ai-tooling/THIRD_PARTY_SKILLS_AUDIT.md),
with their restrictions in
[`docs/ai-tooling/SECURITY_BOUNDARIES.md`](../../../docs/ai-tooling/SECURITY_BOUNDARIES.md).

## Validation

`python manage.py validate_skills` parses every `ecoiq-*` SKILL.md, checks
frontmatter, trigger uniqueness, and that referenced repo paths still exist.
It runs in CI and is covered by `core/tests_engineering_os.py`.
