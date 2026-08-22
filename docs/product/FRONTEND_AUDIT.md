# Frontend Audit

Measured, not estimated. Re-measured after the React cutover.

---

## Public product routes

| | count |
|---|---|
| public product routes | 13 |
| served by React **in production** | **11** |
| still server-rendered | **2** |

All eleven verified live on `ecoiq.uk` after deploy: correct status, correct
injected title, React mounted, zero console errors, zero failed requests.

| route | served by | note |
|---|---|---|
| `/` | React | |
| `/intelligence/` | React | |
| `/projects/` | React | recorded projects + programme concepts, separated |
| `/projects/<slug>/` | React | the five concepts, with per-page metadata |
| `/tours/` | React | now the Eco Tours destination in **both** navigations |
| `/about/` | React | rewritten |
| `/contact/` | React | posts to `/api/v2/contact/`, same abuse screening |
| `/pricing/` | React | enquiry-led; no figures |
| `/league/` | React | fail-closed; zero ranked organisations today |
| `/league/<slug>/` | → `/companies/<slug>/` | 404s on an unknown slug |
| `/labs/` | React | route did not previously exist |
| `/trust/` | React | route did not previously exist |
| `/companies/` | **Django** | see below |
| `/companies/<slug>/` | **Django** | see below |

### Why the two Companies routes were not cut over

**Parity is not proven, and the instruction was to migrate after parity is
proven.**

The server-rendered company profile carries eleven panels the React page does
not have: ethics master scores, improvement roadmap, financing readiness,
financing matches, the QDF decision filter, data status, Shariah screening, KPI
alignment, controversies, watchlist and the stock strip.

Today every organisation in production falls through to
`detail_evidence_pending.html`, so **nobody sees those panels** — which makes
cutting over look free. It is not: routing a URL is a claim to own it, and the
moment one organisation becomes publishable, owning it would silently delete
eleven public sections from that organisation's page.

The React components exist (`pages/Companies.tsx`, `pages/CompanyDetail.tsx`)
with their tests, and are deliberately **not routed** — the note at the top of
`app/routes.tsx` says so and says what has to be true before they are. Finishing
it means exposing those eleven panels through API v2 and proving parity against
a PUBLISHED organisation.

---

## Templates

| | count |
|---|---|
| `templates/*.html` at programme start | **338** |
| after the cutover PR | 338 |
| **now** | **330** |
| **removed** | **8** |

Removed, in the cleanup that followed live verification:

| template | lines |
|---|---|
| `landing.html` | 1,562 |
| `league/company.html` | 1,950 |
| `pricing.html` | 721 |
| `about.html` | 451 |
| `contact.html` | 275 |
| `projects/detail.html` | 246 |
| `projects/index.html` | 102 |
| `intelligence_public.html` | 73 |

With their views: `core.views.landing`, `about`, `contact`, `contact_submit`,
`pricing`, `intelligence`; `projects.views.project_index`, `project_detail`;
`league.views.company_profile`. `core/views.py` shrank from 3,421 to 3,047
lines, including nine module constants that only the deleted pages read.

`/contact/submit/` went with the form that posted to it. Leaving a second
public write endpoint into the same notification table would be a second door
into the same room — which is how the June–August abuse incident got in.

### Static assets: identified, not removed

`landing.html` was the only consumer of six hero image variants and
`hero-globe.js` — **646 kB**, now unreferenced by any template.

They are **kept**. Removing them properly means retiring the hero island from
`frontend/app` and rebuilding `static/dist/ecoiq-islands.js`, which is a second
Node layer and a different piece of work from template cleanup. Deleting the
files while the bundle still names them would break
`core/tests_hero_assets.BuiltBundleTests` for the wrong reason.

Two brand SVGs are also unreferenced, and were already unreferenced before this
programme. Not this PR's to remove.

## Templates intentionally retained

| category | why |
|---|---|
| Django Admin | out of scope by instruction |
| Email templates | an email client is not a React runtime |
| PDF generation | server-rendered HTML is the correct WeasyPrint input |
| `/league/internal/` | the full league table, **staff only** — the public one is fail-closed for everybody, including staff |
| `/companies/` and `/companies/<slug>/` | parity not proven, above |
| Staff review tools (`leads`, `company_intelligence`) | internal, authenticated |
| ~97 other public Django pages | marketing, Labs and legacy surfaces — measured below |

### The wider public surface, measured

**109 anonymously-reachable HTML routes** exist (excluding parameterised ones),
of which 11 are now React. The remaining ~97 are marketing pages
(`/methodology/`, `/platform/`, `/press/`, `/investors/`, …) and publicly
reachable Labs/experimental surfaces (`/legacy-safe/*`, `/digital-twin/`,
`/financial-intelligence-cloud/`, `/capital-guardian/`, `/gold-intelligence/`,
`/decision-studio/`, `/ai-agents/*`, …).

They are outside this phase, which covered the public **product** routes. Two
of them are worth naming as open questions rather than leaving implied:

- **Publicly reachable experimental surfaces.** A dozen Labs modules answer
  anonymously. EcoIQ Labs lists them with their real status, but the modules
  themselves are not gated.
- **`/khalifa-tours/` overclaims.** "Verified", "measured legacy", "Impact
  Ledger" describe expeditions that have not run. `/tours/` now leads with the
  real status and links there, but the deeper page's copy was not rewritten —
  that is the founder's marketing voice, not a defect to silently edit.

---

## Frontend code

| | |
|---|---|
| TypeScript/TSX files | 56 |
| frontend tests | **143** |
| production bundle | **56.7 kB gzipped** entry, code-split per route |
| total committed artefact | 225 kB across 22 files |
| legacy JS/CSS removed | 0 — downstream of template removal |

---

## What this cutover changed beyond rendering

Recorded because each is a product change, not a port:

- **`/pricing/`** no longer publishes four price bands (£15,000–£400,000) or
  their feature checklists. EcoIQ has never delivered a commercial engagement,
  and several itemised capabilities — SSO, workflow automation, overnight
  monitoring — are not built. The six engagement tracks and the
  `?engagement=` pre-selection into `leads.EnterpriseEnquiry` are unchanged.
- **`/` lost the Living Earth globe**, the agent CTAs and the harvester
  counters block. The globe API endpoints are untouched.
- **`/league/`** lost its charts and sector filter publicly. They ran on data
  that is entirely withheld; the code and its containment tests moved to
  `/league/internal/`.
- **`/tours/`** replaced an invented `hello@ecoiq.uk` address — which appears
  nowhere else in the repository — with the real `/contact/` flow.
- **`/` no longer loads a webfont.** Inter was requested by `landing.html`
  only; the SPA uses the system stack.

---

## Claims

| | count |
|---|---|
| hard-coded public counters remaining | **0** |
| unsupported product claims on migrated routes | **0** |
| price figures published without a delivered engagement | **0** |
| invented contact addresses | **0** |
