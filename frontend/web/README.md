# EcoIQ Web

The **public product frontend**: a standalone React SPA consuming API v2.

## Why there are three frontend directories

| directory | what it is | runtime? |
|---|---|---|
| `frontend/web` | **this** — the public product SPA | yes |
| `frontend/app` | build-time React islands that hydrate into Django templates | no — compiles to `static/dist/` |
| `frontend/remotion` | offline video authoring | no |

`app` and `remotion` are deliberately untouched. They are working
build-time-only layers with their own purpose; replacing them is not what this
programme is for.

## The rule this app exists to uphold

A missing value is `null` — never `0`, never `50`, never a substitute.

Three things enforce it rather than leaving it to review:

1. **`strictNullChecks`** plus `noUncheckedIndexedAccess`. A
   `number | null` score cannot reach a render path without the null being
   handled.
2. **Guards in `src/types/evidence.ts`.** Components ask `isPublished(company)`;
   nothing writes `score ?? 0`.
3. **An ESLint rule** that rejects `?? 0` and `?? 50` outright, with a message
   explaining what to do instead.

`0` is a **real, publishable score**. Code that treats it as falsy is wrong,
and there are tests for exactly that case.

## Commands

```bash
npm install
npm run dev        # Vite on :5173, proxying /api to Django on :8731
npm run typecheck
npm run lint
npm test
npm run build
```

## Architecture

```
src/
  api/            one client; components never call fetch
  app/            shell, router, navigation
  components/     evidence display, loading/error/empty states
  design-system/  tokens mirrored from frontend/app/src/design/tokens.ts
  hooks/          useApi — a discriminated union, not {data, loading, error}
  pages/          one per route, lazily loaded
  types/          the API v2 contract, with guards
```

`useApi` returns a union so a component cannot render `data` while it is still
undefined — which is how loading states end up showing zeros.

**No business logic here.** Scoring, coverage, confidence and eligibility are
computed by Django and presented by React. If a number needs deciding, it is
decided server-side.

## Auth

Django session cookies, same-origin, `credentials: 'same-origin'`. CSRF token
read from the `csrftoken` cookie and sent on unsafe methods. Django remains the
authentication authority — this app implements no crypto and stores no
credentials.
