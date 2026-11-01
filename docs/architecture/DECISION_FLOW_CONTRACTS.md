# Decision Flow preview contracts — integration phase 1

**Status:** implemented backend preview and validated output contract; **NOT a live
visual editor or automatic decision engine**.

This change adds Pydantic 2 as an explicit dependency and a staff-only,
read-only response at `GET /api/v2/decision-flow/preview/`. The response
contains `nodes` and `edges` shaped for React Flow; the TypeScript transport
contract lives at `frontend/web/src/api/decisionFlow.ts`.

## Existing components — reuse, do not duplicate

- **AI Gateway:** `ai_gateway/service.py`, `registry.py`, `router.py`.
  It already routes through an approved free-only model pool and applies
  request caps. This change does **not** add a provider, an API key, a billable
  fallback, or a new chat entry point.
- **pgvector / Evidence Memory:** `evidence_memory/models.py` and
  `evidence_memory/services/retrieval_policy.py`. Existing project
  permission checks and provenance apply *before* vector ranking. The preview
  only **names** that step; it performs **no** search, and does not bypass the
  current access boundary.
- **React:** `frontend/web/` is the existing Vite React SPA. Do not replace it
  with Next.js or introduce a second design system. The TypeScript graph
  transport is ready for a future lazy-loaded `@xyflow/react` renderer.
  React Flow itself is **not installed** in this change; the existing
  `package-lock.json` remains reproducible.
- **Pydantic:** `ai_gateway/workflow_contracts.py` validates a fixed,
  review-gated graph and unverified AI decision drafts. Unknown attributes,
  self-approved outputs and executable graph variants are rejected. The
  validation utility does not claim to verify evidence or execute steps.

## Trust and execution boundary

Graph: question → project access → retrieval → AI draft → schema validation
→ human review → reviewed result.

`execution_enabled` is locked to `false`. A diagram is not an executable
workflow: it never publishes formulas, signs off Qur'anic interpretations,
releases capital, accesses private records, or sends an external request.
The `DecisionDraft` shape forces `requires_human_review=true` and
`publication_state=unverified_draft`. A syntactically valid model response
is not a verified claim. Projects and citations must be checked using the
existing project membership/provenance services, not by trusting model IDs.

## Next implementation, deliberately NOT included

1. Add `@xyflow/react` to `frontend/web` with a reproducible lockfile update;
   implement a lazy-loaded read-only staff view that reads
   `getDecisionFlowPreview`. Preserve EcoIQ tokens, text fallback, focus,
   keyboard interaction and reduced-motion preferences.
2. Run `npm run typecheck`, `npm run lint`, `npm test`, `npm run build`,
   and browser checks at 375/768/1280px. Do not call the UI complete until
   all required visual/keyboard checks pass.
3. In a separate PR, if product needs warrant it, add a *project-scoped*
   draft-generation operation that calls the existing gateway and retrieval
   service, validates model output with `validate_decision_draft`, then stores
   a review-pending record with source-to-claim links and a reviewer audit log.
   Do not allow model-proposed IDs to create permissions or approvals.
4. Evaluate operational pgvector indexing on real authorized corpora before
   changing embedding dimensions or approximate-nearest-neighbour strategy.
   Existing PR #337 already explores measured retrieval quality; coordinate
   that change rather than mixing unreviewed vector spaces.

## Verification

Contract tests: `python manage.py test ai_gateway.tests_workflow_contracts`.
Also run `python manage.py check` and the existing AI Gateway/Evidence
Memory test suites. No Django models, migrations, deployment settings,
secrets or production databases are changed in this PR.
