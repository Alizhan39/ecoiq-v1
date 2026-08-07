# Python static typing

**The EcoIQ repository is not fully typed, and this document does not claim it
is.** `mypy .` currently reports **957 errors across 199 files** out of 1,151
checked. That number is informational. CI blocks on a deliberately small
surface, listed below, and the rest is a roadmap rather than a promise.

## Versions

| Tool | Version |
|---|---|
| mypy | 1.18.2 |
| django-stubs | 5.2.7 (`[compatible-mypy]`) |
| djangorestframework-stubs | 3.16.4 |
| Python target | 3.11 |
| Django | 5.2.14 |

Pinned exactly in `requirements-dev.txt`, for the same reason Ruff is: an
unpinned checker turns a green branch red without anyone committing anything.
mypy and django-stubs are version-coupled, hence the `[compatible-mypy]` extra.

Plugins: `mypy_django_plugin.main` and `mypy_drf_plugin.main`. DRF is genuinely
installed and used (`rest_framework` in `INSTALLED_APPS`, 11 modules import it),
so its plugin earns its place; it was not added speculatively.

## Stage 1 — the blocking surface

```
core/client_origin.py
notifications/antispam/
companies/throttle.py
notifications/management/commands/analyse_notification_spam.py
notifications/management/commands/classify_notification_spam.py
```

These are the modules that decide whether a public request is abuse, plus the
command that can relabel 979 production notifications. They were chosen on
measured evidence, not preference: `core/client_origin.py` and
`notifications/antispam/` already had **zero** errors at baseline, the other
three had seven between them.

`core.client_origin` and `notifications.antispam.*` additionally carry
`disallow_untyped_defs` and `disallow_incomplete_defs`. Everything in them is
annotated, and an unannotated function added later fails CI — otherwise new code
in the security surface would silently opt out of the gate.

## Running it

Locally, and identically in CI:

```bash
python -m mypy \
  core/client_origin.py \
  notifications/antispam \
  companies/throttle.py \
  notifications/management/commands/analyse_notification_spam.py \
  notifications/management/commands/classify_notification_spam.py \
  --follow-imports=silent
```

The whole-repository view, which is not blocking:

```bash
python -m mypy .
```

### Why `--follow-imports=silent`

mypy follows imports, so checking `core/client_origin.py` alone surfaces errors
in the Django models it imports. `silent` keeps the type information from those
modules while reporting only the paths named on the command line.

It is **not** `follow_imports = skip`, which discards the type information
itself and would let a real error through. `skip` is not used anywhere.

## Policies

**`Any`.** Not banned globally, and Stage 1 introduces none. Where a
third-party API returns `Any`, narrow it at the adapter boundary and return a
typed internal value rather than letting it propagate into a service signature.

**Ignores.** In order of preference: correct typing, then narrowing, then
`Protocol`/`TypedDict`, then a justified `cast()`, and only then
`# type: ignore[specific-code]`. **Never a bare `# type: ignore`** when a code
is available. `warn_unused_ignores` is on, so an ignore that stops being needed
fails CI instead of rotting.

Stage 1 added **zero** ignores and **zero** casts.

**Migrations** are excluded. They are generated, they are historical records,
and we do not hand-edit them. Also excluded: `staticfiles`, `static/dist`,
`frontend`, `node_modules`, virtualenvs. No normal Django app is excluded — apps
that are not yet typed are absent from the *blocking list*, not hidden from the
baseline.

**Missing stubs.** Packages shipping no type information are listed explicitly
under `[[tool.mypy.overrides]]` with `ignore_missing_imports`. Listed one by one
rather than set globally, so the gap stays visible.

## Expanding coverage

Add paths to the CI command and to this document in the same PR. Get the surface
to zero errors *before* adding it, not after.

**Every new or substantially modified module in the Stage 1 surface must remain
mypy-clean.**

## Roadmap

Ordered by security sensitivity and defect likelihood, not by app name.

| Stage | Paths | Errors | Why |
|---|---|---|---|
| 1 (done) | origin resolver, antispam, throttle, classifier commands | 7 → 0 | decides whether a request is abuse |
| 2 | `core/`, `notifications/` remainder | ~47 | shared utilities and the notification model layer |
| 3 | `companies/`, `league/` | ~136 | largest public surface |
| 4 | `audit/` | 124 | highest single-app count; audit correctness matters |
| 5 | `api/`, DRF serializers/views | — | typed request/response boundaries |
| 6 | `investor_portfolio/`, `capital_guardian/`, `company_intelligence/` | ~155 | financial logic |
| 7 | `intelligence/`, `transition/`, `cms/`, `good_agents/` | ~170 | |
| 8 | remaining apps, ML and orchestration | remainder | most `attr-defined`/`union-attr`; lowest value per unit of work |

`union-attr` (290) and `attr-defined` (297) dominate the baseline. The
`union-attr` group is the interesting one — each is a place where a nullable
value is dereferenced without a check, which is the same class of defect Stage 1
found in `forwarded_chain()`.
