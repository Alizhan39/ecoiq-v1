# EcoIQ Business Plan 2.0 — sequential KPI React Flow

## Scope / no claims of production approval

A project-member-only visual flow of the **existing** 20 provisional KPI
definitions, in `PROVISIONAL_KPI_FORMULAS` order. These formulas are
candidates, not audited financial, social, environmental or Qur'anic verdicts.
The UI provides a typed input form and asks the Django evaluator to produce a
**read-only draft preview**. It cannot edit formulas or graph execution order.

`GET /api/v2/projects/<project_slug>/formulas/flow/` returns formulas, nodes,
edges, and `can_preview_calculate` determined by Django project permissions.

`POST` on the same route requires **ANALYSE** membership, Django session auth
and CSRF; accepts only:
```json
{
  "period": "2026-10",
  "observations": {
    "revenue": {
      "reported_revenue": {"value": "150.25", "source_ref": "document-1"}
    }
  }
}
```
All measurement values must be finite, bounded non-negative decimal strings or
integers; the browser supplies strings. Every supplied formula must provide
*all* of its declared input names and bounded nonempty source identifiers.
Formula names, expressions, units, the order and derived statuses are always
server-owned. Unknown keys or malformed inputs fail the whole request before
evaluation. No data is persisted; no provider requests are made. Absent groups
are `NOT_SUPPLIED`; undefined denominators never become zero; output values
are exact Decimal strings subject to the existing registry's bounds.

Sequence order in the response is the immutable registry order. This is **not**
data-flow composition between the 20 KPIs; each requires its own source data.
Results are `REPORTED_NOT_VERIFIED` (or an explicit blocker), **never**
approved or verified. Source IDs are untrusted text labels; they are not
proof of real documents. Independent evidence and formula-owner review remain
mandatory before any publication, investment or operational recommendation.
Neither AI Gateway nor pgvector is invoked in the calculation path. Existing
AI and evidence services remain available for separate, permission-checked
review workflows.

## UI / operations

- SPA page: `/business-os/formulas/<project_slug>/flow/`
- React Flow component (read-only, fixed edges) is lazy-loaded via SPA route.
- The page has a full keyboard-oriented text list of the 20 steps; selected
  formula inputs are plain HTML labels/controls, with empty/error states.
- Uses EcoIQ's existing design tokens; no new Tailwind or Next.js stack.
- No interactive schema editing, automated chained AI execution, or background
  financial actions are provided.
- The `frontend/web/package-lock.json` has been updated to pin React Flow
  12.12.0, and `static/spa` was rebuilt and committed through a one-off
  GitHub Actions branch build. The temporary write-enabled helper workflow
  was removed after its successful run. Production Render does **not**
  compile Node packages.

## Verified in GitHub Actions on 2026-11-01

- Frontend: `npm ci`, TypeScript, ESLint, **567 React tests**, production SPA
  build and generated artifact commit passed.
- Django: `manage.py check`, `makemigrations --check --dry-run` and **27
  targeted tests** passed, including Formula Flow project permissions and
  Pydantic gateway contracts.
- **Not yet verified:** manual real-browser checks at 375/768/1280px,
  keyboard interaction, reduced motion, and a live staging deployment.

## Local verification

```sh
python manage.py check
python manage.py test api.tests_v2_formula_flow ecoiq_os.test_formula_registry ai_gateway.tests_workflow_contracts
cd frontend/web
npm ci
npm run typecheck
npm run lint
npm test
npm run build
git diff --exit-code -- ../../static/spa
```

Then inspect in a real browser at 375, 768 and 1280 pixels: flow keyboard
navigation, source form focus, reduced motion, incorrect/empty inputs,
viewer-vs-analyst permissions, and mobile overflow. Do not mark the PR ready or
deploy without those checks.

Previous dependency: PR #373 (typed decision-flow preview). This PR is stacked
against its feature branch until #373 is reviewed or merged.
