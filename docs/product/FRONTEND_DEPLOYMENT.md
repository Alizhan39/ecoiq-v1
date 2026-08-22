# Frontend Deployment

How the React SPA reaches production, what Django still owns, and how to get
back if it goes wrong.

---

## Architecture

One domain, one service, one origin.

```
ecoiq.uk  (Render web service "ecoiq", Django + Gunicorn)
├── React SPA          served by core/spa.py from static/spa/index.html
├── /api/*             Django REST Framework (v1 + v2)
├── /admin/*           Django Admin
├── /billing/webhook/  Stripe — registered by hand in the Stripe dashboard
├── /healthz/          liveness probe, no database
└── /static/*, /media/ WhiteNoise
```

**No second hostname. No separate static host. No SSR framework.**

The API is session-authenticated. A second origin would mean `SameSite=None`
cookies, CORS preflights and a credential surface that exists only to serve an
architecture nobody asked for. Same-origin keeps the boundary
`api/v2_session.py` was built against — including the login-CSRF fix, which is
re-asserted in `core/tests_spa.py` after the routing change.

---

## The build artefact is committed

`static/spa/` is checked into the repository.

Render's Python environment has no Node toolchain, and this repo's two other
Node layers — `frontend/app` (Django islands) and `frontend/remotion` (offline
video) — are already build-time-only by design. Node has never been a runtime
dependency here and this does not make it one.

A committed artefact is only trustworthy if something proves it matches its
source. Three things do:

| check | where | fails when |
|---|---|---|
| rebuild and diff | CI job `frontend` | `static/spa/` doesn't match a fresh `npm ci && npm run build` |
| artefact present and complete | `build.sh` | a referenced asset is missing → **deploy is refused** |
| same assertions in the suite | `core/tests_spa.py` | ditto, at test time |

To change the frontend:

```bash
npm --prefix frontend/web ci && npm --prefix frontend/web run build
```

then commit `static/spa/` with the source change. CI fails the PR if you forget.

---

## The catch-all

`re_path(r'^(?P<path>.*)$', spa.spa_catch_all)` is the **last** entry in
`ecoiq/urls.py`. A test asserts it is last and that only one exists — it
matches every path, so anything registered after it is unreachable.

It is a fallback, not a router. Three outcomes:

| request | answer |
|---|---|
| unknown `/api/…` | **JSON** `404 {"detail": "Not found."}` |
| any other server-owned prefix or document suffix | plain `404`, never the shell |
| unknown frontend path | the React shell with **HTTP 404** |

Server-owned prefixes are declared once in `spa.SERVER_OWNED_PREFIXES`, and the
test suite iterates that list — adding a prefix adds its test automatically.

**Why the API case is called out separately.** An integrator whose URL is wrong
must see a 404. If the catch-all answered `200 text/html`, their client would
report a JSON parse error, and whoever debugged it would go looking for a
serialiser bug instead of a typo.

**Why unknown frontend paths get 404 and not 200.** A person sees the React
NotFound page either way. A crawler sees the truth only one way. Serving 200
for a page that does not exist is the same category of untruth as serving a
score for a company that has no evidence.

Routes migrated off Django templates keep their **existing registration and URL
name** and swap only the view, so `{% url 'about' %}` still resolves from the
templates that are still server-rendered, and prefix ordering is unchanged.

---

## SEO

Full SSR is **not** implemented, and is not required. The reasoning is
recorded here so it can be re-taken rather than re-argued.

Production holds 467 companies, **all** `INSUFFICIENT_EVIDENCE`, zero published
scores and zero ranks. There is no dynamic company or ranking content worth
optimising for, so introducing a second rendering architecture to serve it
would be paying a permanent architectural cost for content that does not exist.

### What is implemented: per-route metadata injection

Django substitutes the `<head>` of the built shell at request time
(`core/spa.py`, `head_tags`). Every route gets its own title, description,
canonical URL and Open Graph tags. This is **not** SSR — the body is still
rendered by React in the browser — and it needs no extra framework, no build
step and no prerender pass.

It also does something a build-time prerender could not: company pages carry
metadata derived from the database *at request time*, so `noindex` disappears
the moment an assessment becomes publishable, with no rebuild.

### Company pages

Title and description are built from name, sector and country. **Never** from
the score, the rank or the coverage figure — not even when the score is
publishable. A metadata path that *can* emit a score is one refactor away from
emitting a withheld one; the React page reads the number from the API, where a
single gate decides.

An organisation with no publishable assessment gets `noindex, follow`. The page
stays truthful and reachable; it is simply not worth indexing, and inviting a
crawler to rank it would be asking to be judged on content EcoIQ is
deliberately withholding. `follow` keeps its outbound links alive.

### League

The league truthfully contains **zero ranked organisations**. There is no
ranking SEO to preserve, and no hidden scores are embedded for crawlers — the
regression that made that necessary is covered by `league/tests.py`.

### When to reconsider SSR

When production has a meaningful number of genuinely `PUBLISHED` companies or
projects — content a crawler would rank on, that a client-rendered page cannot
show it. Not before. This is future optimisation, not present debt.

---

## Caching

| asset | header | why |
|---|---|---|
| `/static/spa/assets/*` | `immutable`, far-future | Vite content-hashes the filename; a change produces a new name |
| `index.html` (every SPA route) | `no-store, must-revalidate` | it *names* the hashed assets — a stale copy points at a bundle that no longer exists, which presents as a blank page nobody can reproduce |

WhiteNoise recognises Django's `name.<hash>.ext` convention; Vite hashes with a
dash. `core/whitenoise.py` subclasses the middleware to close that gap.

### A defect found while doing this

`STATICFILES_STORAGE` was **removed in Django 5.1**. This project pins Django
5.2, so the setting naming `CompressedManifestStaticFilesStorage` was silently
ignored and production had been serving every static file with **no gzip, no
brotli and no hashing**. Verified by reading `settings.STORAGES['staticfiles']`
on a booted instance.

Replaced with a `STORAGES` block using `CompressedStaticFilesStorage`.
Compression is restored; content hashing is deliberately still off, because the
manifest backend rewrites every `url()` reference it finds and fails the build
when one is missing — across 338 templates and a large legacy asset tree that
has never been through that check, that is its own piece of work with its own
failure mode.

---

## Verified live

Confirmed against `ecoiq.uk` after the cutover deploy:

| check | result |
|---|---|
| 11 React routes | 200, React mounted, correct per-route `<title>` |
| console | zero errors, zero failed requests |
| direct deep-link refresh | renders, correct title |
| client-side navigation | routes without a page load |
| `/api/v2/` | `200 application/json` |
| unknown `/api/…` | `404 {"detail": "Not found."}` |
| `/admin/` | 302 to login, no React shell |
| `/healthz/` | `200 ok`, plain text |
| unknown page | 404 with the shell and `noindex` |
| SPA assets | `content-encoding: br`, `cache-control: max-age=315360000, public, immutable` |
| shell | `cache-control: no-store, must-revalidate` |
| every built chunk | 200, no 404s |
| unpublished company page | `noindex, follow`, no JSON-LD, no `ratingValue`, API score `null` |
| sitemap | 0 company URLs, static pages only |
| league | `count: 0`, `withheld: 467`, zero embedded chart payloads |

The brotli encoding is the visible result of the `STATICFILES_STORAGE` fix: the
entry bundle is 173 kB on disk and **49.5 kB on the wire**. Before it, that
setting was dead config and nothing was compressed at all.

### One defect this verification found

Client-side navigation left the browser tab showing the previous route's title.
Django titles the document for the URL that was requested, which is right for a
direct load and for a crawler — but a click replaces no document. Fixed with a
route→title map on the client, and `core/tests_spa.TitleMapsAgreeTests` reads
the TypeScript source from disk and fails if the two maps ever disagree.

---

## Rollback

The cutover is deliberately reversible, and was sequenced so that it stays
reversible:

```
1. SPA infrastructure + new-only routes   deploy → verify live
2. React pages (About, Contact, …)        deploy → verify live
3. cut existing routes over to the SPA    deploy → verify live
4. delete the obsolete templates          deploy → verify live
```

Templates are deleted only at step 4, **after** the React routing has been
verified in production. Between steps 3 and 4 the Django templates still exist
on disk, so rollback is a single revert with no content restoration.

### To roll back

```bash
git revert --no-edit <merge-sha-of-the-cutover-PR>
git push origin main
```

Render redeploys from `main` automatically. Or, faster, in the Render dashboard:
**ecoiq → Deploys → the last known-good deploy → Redeploy**.

| step | last-good SHA to return to |
|---|---|
| before any SPA work | `ad47ef23d8a10269534551480ca8eea9b141012f` |

Recorded here rather than in a runbook nobody opens under pressure.

### What rollback does not need

No migration is reversed — this programme adds none. No data is restored. No
Stripe, DNS or Render configuration changes, because none was made.
