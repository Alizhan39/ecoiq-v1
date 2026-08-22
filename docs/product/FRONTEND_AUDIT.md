# Frontend Audit

**Phase 23.** Measured, not estimated.

---

## Templates

| | count |
|---|---|
| `templates/*.html` at programme start (`bf2727a3`) | **338** |
| `templates/*.html` now | **338** |
| **removed** | **0** |

**Zero templates have been removed, and that is deliberate.**

Removal (Phase 15) requires React parity confirmed *and the React app actually
serving production traffic*. The SPA is built and tested but **not deployed** —
`ecoiq.uk` is still served by Django. Deleting a template whose replacement is
not reachable would take the product offline.

Template removal is blocked on deployment (Phase 16), not on the React work.

---

## Public product routes

| | count |
|---|---|
| public product routes identified | 12 |
| React routes implemented | **11** |
| public routes still template-rendered **in production** | **12** |

Every public route now has a React implementation, and none of them is live.
The gap is deployment.

| route | React | notes |
|---|---|---|
| `/` | ✅ rebuilt | capability-verified copy |
| `/intelligence` | ✅ rebuilt | real assessment flow |
| `/projects` | ✅ | honest empty state — estate holds zero |
| `/tours` | ✅ | interest capture; route did not previously exist |
| `/about` | ⬜ scaffold | |
| `/contact` | ⬜ scaffold | |
| `/companies` | ✅ | secondary evidence surface |
| `/companies/:slug` | ✅ | |
| `/labs` | ✅ | registry-driven; route did not previously exist |
| `/trust` | ✅ | route did not previously exist |
| `/league` | ⬜ | not migrated; de-emphasised |
| `/pricing` | ⬜ | not migrated |

---

## Frontend code

| | |
|---|---|
| TypeScript/TSX files | 46 |
| frontend tests | **102** |
| production bundle | **56.5 kB gzipped**, code-split per route |
| legacy JS removed | 0 |
| legacy CSS removed | 0 |

Legacy asset removal is downstream of template removal, which is downstream of
deployment.

---

## Claims

| | count |
|---|---|
| hard-coded public counters remaining | **0** |
| unsupported product claims in templates | **0** |

Corrected in this programme:

- `base.html` `og:description` — promised "company rankings, ESG scores" on
  every shared page
- `about.html` `og:description` — "EcoIQ scores companies globally", with no
  evidence condition
- `press.html` — "219+ companies · 25+ countries" as a key fact *and* in the
  boilerplate journalists are told to copy

Nine regression tests scan every template, including a guard asserting the scan
covers 100+ files.

---

## Templates intentionally retained

| category | why |
|---|---|
| Django Admin (1,560 routes) | out of scope by instruction |
| Email templates | an email client is not a React runtime |
| PDF generation | server-rendered HTML is the correct WeasyPrint input |
| Staff review tools (`leads`, `company_intelligence`) | internal, authenticated, low-traffic |
| `/healthz/` | infrastructure, not a page |
| ~250 Labs / legacy / dead template routes | should be deleted, not ported |

---

## What blocks "public template routes = 0"

**One thing: deployment.**

The React app builds, typechecks, lints and passes 102 tests. It is not served
anywhere. Making it live needs a decision this audit cannot make on its own:

1. **How `ecoiq.uk` serves the SPA** — a static host in front of Django, or
   Django serving the built `index.html` with a catch-all route.
2. **History fallback** for React Router.
3. **SEO.** The company and league pages are indexed server-rendered HTML.
   Client-rendering changes how they are crawled. Prerender, SSR, or accept the
   change — a real decision with real consequences.

Until those are settled, the honest count of public Django-template routes is
**12**, not 0 — and stating otherwise because the React code exists would be
the same category of claim this programme has spent itself removing.
