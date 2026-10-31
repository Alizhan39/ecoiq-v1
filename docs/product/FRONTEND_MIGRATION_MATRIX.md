# Frontend Migration Matrix

**Measured from the running application**, not from memory. Route counts come
from walking Django's resolver; template counts from disk; live status codes
from production.

---

## The scale, measured

| | count |
|---|---|
| URL routes total | **2,123** |
| …of which Django admin (auto-generated) | 1,560 |
| **non-admin routes** | **563** |
| non-admin routes that render a template | **324** |
| non-admin routes returning JSON/API | 77 |
| non-admin routes doing something else (redirects, files, webhooks) | 162 |
| HTML templates on disk | 338 in `templates/`, 410 total incl. app dirs |
| Django apps with routes | 75 |

**This is the finding that shapes the whole programme.** "Move the frontend to
React" is not one migration; it is 324 template-rendering routes across 75 apps,
and the overwhelming majority of them are not public product.

---

## Classification

Applied to the 324 template-rendering routes.

| class | meaning | disposition |
|---|---|---|
| **PUBLIC PRODUCT** | anonymous users, part of the product proposition | **migrate to React** |
| **AUTHENTICATED PRODUCT** | signed-in customer surfaces | migrate to React |
| **STAFF TOOL** | internal operations | keep Django templates |
| **DJANGO ADMIN** | model administration | keep — explicitly out of scope |
| **EMAIL / PDF** | server-rendered documents | keep — correct as server-rendered |
| **LABS** | working experiments | keep behind an EcoIQ Labs boundary |
| **LEGACY** | superseded by a newer surface | delete after redirect |
| **DEAD** | unreachable or unreferenced | delete, do not port |

The goal is **not** to rewrite Django Admin in React. The goal is that no
**public product** route depends on a Django template.

---

## Public product surface — the actual target

Probed live against `https://ecoiq.uk`.

| route | live | app | class | disposition |
|---|---|---|---|---|
| `/` | 200 | `core` | PUBLIC PRODUCT | **rebuild** (Phase 8) |
| `/intelligence/` | 200 | `intelligence` | PUBLIC PRODUCT | **rebuild** (Phase 9) |
| `/projects/` | 200 | `league` | PUBLIC PRODUCT | migrate (Phase 10) |
| `/khalifa-tours-impact/` | 200 | `core` | PUBLIC PRODUCT | migrate as **Eco Tours** (Phase 11) |
| `/about/` | 200 | `core` | PUBLIC PRODUCT | migrate |
| `/contact/` | 200 | `core` | PUBLIC PRODUCT | migrate |
| `/companies/` | 200 | `companies` | PUBLIC PRODUCT | migrate, de-emphasised (Phase 12) |
| `/companies/<slug>/` | 200 | `companies` | PUBLIC PRODUCT | migrate (Phases 12–13) |
| `/league/` | 200 | `league` | PUBLIC PRODUCT | migrate, **not** the hero |
| `/pricing/` | 200 | `core` | PUBLIC PRODUCT | migrate |
| `/healthz/` | 200 | `core` | INFRASTRUCTURE | keep — not a page |
| `/api/v2/*` | 200 | `api` | API | keep — this is the contract |

**Note on Eco Tours.** The canonical navigation calls for `/tours/`. That route
returns **404** today; the live surface is `/khalifa-tours-impact/`. The React
route should be `/tours/` with a redirect from the old path — the navigation
target does not currently exist, and pretending otherwise would put a dead link
in the primary nav.

`/labs/` also 404s. The Labs boundary (Phase 14) is new, not a migration.

---

## Where the other 314 template routes are

Top apps by template-rendering route count:

| app | routes | class |
|---|---|---|
| `core` | 44 | mixed — a handful public, most marketing/legacy |
| `capital_guardian` | 41 | **LABS** |
| `legacy_safe` | 14 | **LEGACY** — named accordingly |
| `digital_twin` | 14 | LABS |
| `leads` | 13 | STAFF TOOL |
| `company_intelligence` | 13 | STAFF TOOL |
| `financial_intelligence_cloud` | 10 | LABS |
| `khalifa_stewardship_tour_operating_system` | 10 | LABS (the operating system, not the public tours page) |
| `global_research` | 10 | LABS |
| `investor_portfolio` | 9 | AUTHENTICATED PRODUCT |
| `good_agents` | 9 | LABS |
| `audit` | 8 | LABS |
| `gold_intelligence` | 8 | LABS |
| `partner_participation` | 8 | LABS |
| `ecoiq_commerce` | 7 | LABS |
| `ai_agent_workbench` | 7 | LABS |
| `intelligence` | 6 | PUBLIC PRODUCT |
| `transition` | 6 | LABS |
| `companies` | 5 | PUBLIC PRODUCT |
| `ai_agent_council` | 5 | LABS |

**Roughly 250 of the 324 template routes are Labs, staff tooling or legacy.**
They are not public product and must not be rewritten in React. Most should end
up behind the Labs boundary or deleted; none blocks the public migration.

---

## Deliberately retained as Django templates

Listed now so the final audit has something to check against.

1. **Django Admin** — 1,560 auto-generated routes. Out of scope by instruction.
2. **Email templates** — server-rendered is correct; an email client is not a
   React runtime.
3. **PDF generation** (`league/pdf_report.py`, WeasyPrint) — server-rendered
   HTML is the input to the PDF engine.
4. **Staff tools** — `leads`, `company_intelligence` review queues, admin
   actions. Internal, authenticated, low-traffic; React would add risk and
   remove nothing.
5. **`/healthz/`** — infrastructure, not a page.

---

## Sequencing

The order is chosen so that nothing is deleted before its replacement is proven.

1. **API gap closure** (Phase 5) — `/api/v2/platform/` for counters is the only
   confirmed gap for the homepage; everything else public is already served.
2. **React foundation** (Phase 4) — app, router, API client, types from
   `FRONTEND_API_CONTRACT.md`.
3. **Route-by-route migration** — public product only, in the order above.
4. **Template removal** (Phase 15) — only after React parity, API tests, mobile
   layout, SEO/meta and redirects are each confirmed for that route.

## Honest risks

- **SEO.** The company and league pages are indexed server-rendered HTML. A
  client-rendered replacement changes how they are crawled. This needs a real
  decision (prerender, SSR, or accept the change) and is not a detail.
- **`core` has 44 template routes** and mixes public product with marketing and
  legacy. It needs its own pass before anything in it is deleted.
- **`/tours/` does not exist.** The nav target must be created, not migrated.
- **Two public routes are rebuilds, not ports** (`/` and `/intelligence/`), and
  both depend on product decisions about what EcoIQ can truthfully claim to do.
