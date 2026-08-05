# Django improvement backlog

Findings from the Phase 2 review that were **not** implemented, because they
exceed the scope limit for a reviewable patch (≈10–15 files), require schema
migrations against live data, or are behaviour changes that deserve their own
review.

Items implemented in this pass are listed at the bottom for reference and are
not repeated here.

Priorities: **P0** active security or data-loss risk · **P1** production
reliability or authorisation risk · **P2** significant maintainability or
performance issue · **P3** cleanup or consistency.

---

## P0

None outstanding. The two P0 findings from this review (insecure `SECRET_KEY`
fallback, deploy scripts swallowing migration failures) were fixed in this pass.
The administrator-credential P0 was fixed in the Phase 1 security patch, but
**production password rotation remains outstanding** — see
[`docs/security/admin-credential-rotation.md`](../security/admin-credential-rotation.md).

---

## P1

### P1-0 — CI cannot be made blocking until two stale good_agents assertions are fixed

- **Files:** `good_agents/tests.py` (two assertions), caused by
  `good_agents/management/commands/seed_signal_providers.py`
- **Evidence:** Commit `a15329c` (2026-07-25, PR13) raised the seeded provider
  count from 3 to 5 without updating `good_agents/tests.py`. Two tests still
  hard-code 3 and fail on `origin/main` on **both** SQLite and PostgreSQL:
  `IngestionOrchestrationTests.test_one_provider_failure_does_not_stop_others`
  (4 != 2) and `GoodWhileYouSleepCommandTests.test_seeds_all_114_and_real_providers`
  (5 != 3). CI never caught it because the test job carries
  `continue-on-error: true`.
- **Production code is correct** — one provider failing does not stop the
  others, and all five providers seed. Only the assertions are stale.
- **Fix:** branch `fix/good-agents-stale-provider-assertions` — assertions
  derive expected providers from the seed command's own `PROVIDERS` list
  instead of a literal, and additionally assert provider identity (strictly
  stronger; mutation-verified).
- **Behaviour change:** none. **Migration:** No.
- **Must land before** the `continue-on-error` removal.

### P1-1 — `.delay()` is called although no Celery worker exists in production

- **Files:** `backend_intelligence_engine/admin.py:69`, `backend_intelligence_engine/tasks.py:543`
- **Evidence:** `render.yaml` defines no worker service and no `REDIS_URL`
  (both are commented out at lines 166–230, deliberately, as a cost decision).
  `settings.REDIS_URL` therefore falls back to `redis://localhost:6379/0`,
  which does not exist on the Render instance. The admin action *Retry selected
  failed tasks* calls `task.delay(...)`, so using it in production raises a
  broker connection error rather than retrying anything.
- **Risk:** A staff-facing admin action fails with a 500. Operators may believe
  work was re-queued when nothing was.
- **Fix:** Add a `CELERY_WORKER_AVAILABLE`-style guard (derived from whether
  `REDIS_URL` is explicitly set) and either disable the admin action with a
  clear message, or run the task inline via `.apply()` when no worker exists.
  Do not silently pretend it was queued.
- **Behaviour change:** Yes (the action starts reporting honestly).
  **Migration:** No. **Tests:** admin action with and without a worker.

### P1-2 — Anonymous API rate limit is effectively half its configured value

- **Files:** `ecoiq/settings.py` (`DEFAULT_THROTTLE_CLASSES`), `api/throttles.py`
- **Evidence:** Already documented in `api/tests.py:301-313`. `AnonRateThrottle`
  and `APIKeyRateThrottle` both resolve to the same cache key for an anonymous
  request (same scope, ident, and `cache_format`), so each anonymous request
  consumes two slots. The real anonymous limit is 10/day, not the configured
  20/day.
- **Risk:** The documented public rate limit is wrong; legitimate anonymous
  users are cut off at half the intended allowance.
- **Fix:** Have `APIKeyRateThrottle` return `None`/defer for unauthenticated
  requests so only `AnonRateThrottle` counts them, or drop `AnonRateThrottle`
  from the defaults.
- **Behaviour change:** Yes (anonymous callers get the documented allowance).
  **Migration:** No. **Tests:** exists — extend the existing throttle test.

### P1-3 — 27 silent `except Exception: pass` blocks

- **Files:** 27 sites across 78 files that use broad handlers
  (`git grep -A1 "except Exception" | grep "pass$"`).
- **Risk:** Failures are invisible. The `semantic_search` case fixed in this
  pass is the pattern: a permanently-broken branch looked like a working
  feature for as long as nobody read the response body carefully.
- **Fix:** Triage each site. At a genuine boundary, log with
  `logger.exception(...)` and continue; elsewhere, narrow to the specific
  exception. `settings.LOGGING` (added in this pass) now makes the logs
  actually reach the Render stream.
- **Behaviour change:** No (logging only). **Migration:** No.
  **Tests:** per-site as triaged. **Suggested PR boundary:** one app at a time.

### P1-4 — Email silently discarded in production

- **File:** `ecoiq/settings.py` (`EMAIL_BACKEND`)
- **Evidence:** Defaults to the console backend. `render.yaml` sets no
  `EMAIL_*` variables, so lead notifications and enquiry emails are written to
  the deploy log and never delivered.
- **Mitigation applied:** A loud startup warning now prints in production. The
  underlying delivery gap is unchanged.
- **Fix:** Configure SMTP in the Render dashboard, then consider promoting the
  warning to `ImproperlyConfigured`.
- **Behaviour change:** Yes, once SMTP is configured (email starts sending).
  **Migration:** No. **Tests:** backend selection per environment.

---

## P2

### P2-1 — Monetary values stored as `FloatField`

- **Files:** `capital_guardian/models.py:140,204`,
  `gold_intelligence/models.py:79-94`,
  `agent_runtime_model_router/models.py:176`, and others
  (`git grep FloatField -- "*/models.py" | grep -iE "cost|amount|usd|capex|opex"`).
- **Risk:** Binary floating point cannot represent decimal currency exactly;
  sums drift. These feed investor-facing capital-allocation figures.
- **Fix:** Migrate to `DecimalField(max_digits=…, decimal_places=2)`.
- **Behaviour change:** Values round-trip exactly; some totals will shift in the
  last decimal place. **Migration:** **Yes** — `AlterField` per column, with a
  data-safety review. Postgres casts `double precision → numeric` in place; the
  table is locked for the rewrite, so schedule it.
  **Tests:** arithmetic round-trip per model.
  **Suggested PR boundary:** one app per PR.

### P2-2 — 79 installed apps, 194 models, mostly undifferentiated

- **File:** `ecoiq/settings.py` (`INSTALLED_APPS`)
- **Evidence:** Counted at runtime. Many are described in their own comments as
  hackathon, demo, training-pack, or presentation-only modules
  (`legacy_safe`, `*_training_pack`, `frontend_implementation_roadmap`,
  `ai_agent_workbench`, …), yet all load unconditionally in production.
- **Risk:** Startup cost, admin surface, URL surface, and migration surface for
  code that is not production-active. Hard to reason about what is real.
- **Fix:** Classify each app (`production-active` / `internal-active` /
  `experimental` / `demo` / `deprecated`) in a manifest, then gate experimental
  URLs behind a flag. **Do not rename or delete apps** — that breaks migrations
  and content types.
- **Behaviour change:** Experimental URLs stop resolving in production.
  **Migration:** No (as long as apps stay installed). **Tests:** URL resolution
  per classification. **Suggested PR boundary:** manifest first (docs only),
  gating second.

### P2-3 — Unpinned production dependencies

- **File:** `requirements.txt`
- **Evidence:** 9 exact pins; ~20 `>=` ranges including `pandas`, `numpy`,
  `scikit-learn`, `celery`, `djangorestframework`, `geopandas`, `shap`.
- **Risk:** Builds are not reproducible — a Render rebuild can pull a new major
  version of a numeric or ML dependency and change scoring output or fail.
- **Fix:** Pin exactly, ideally with a lock file. Split dev-only and optional
  ML/geo/PDF extras into separate requirement files.
- **Behaviour change:** No (pin at currently-resolved versions).
  **Migration:** No. **Tests:** CI build is the test.
  **Note:** Do not combine with a dependency *upgrade* — pin first, upgrade
  separately.

### P2-4 — No PostgreSQL in CI

- **File:** `.github/workflows/django.yml`
- **Evidence:** `DATABASE_URL: sqlite:///db.sqlite3`. Production is Postgres,
  and the codebase uses `pgvector`, JSON fields, and constraint behaviour that
  differ between the two.
- **Fix:** Add a `postgres` service container to the workflow and run the suite
  against it (keep SQLite as a fast pre-check if desired).
- **Behaviour change:** No. **Migration:** No.
  **Risk:** Some currently-green tests may fail on Postgres — that is the point.

### P2-5 — `|safe` used in 51 template locations

- **Files:** across `templates/`
- **Risk:** Each is a potential XSS sink if the content is not
  server-generated. Not yet triaged one by one.
- **Fix:** Audit each; keep `|safe` only where the value is produced and
  sanitised by trusted server-side code, and document why at the call site.
- **Behaviour change:** No, if the audit confirms each use.
  **Tests:** rendering tests for any site that takes user content.

---

## P3

### P3-1 — Settings module is 900+ lines in one file

Splitting into `ecoiq/settings/{base,development,production,test}.py` was
considered and **deliberately deferred**: `DJANGO_SETTINGS_MODULE=ecoiq.settings`
is referenced in `render.yaml`, `manage.py`, `wsgi.py`, CI, and the docs, and
the split has no correctness benefit now that the environment guards fail fast.
The environment is already distinguishable via `DEBUG` / `RUNNING_TESTS` /
`IS_PRODUCTION`. Revisit only if per-environment divergence grows.

### P3-2 — Mid-file imports in `ecoiq/settings.py`

`import datetime as _datetime`, `from django.utils.translation import ...`, and
`import warnings` appear mid-module. Harmless; cosmetic only. Not worth a diff
on its own.

### P3-3 — No linter or formatter configured

No `ruff`, `black`, `flake8`, or `pre-commit` config exists. Adding `ruff` with
a conservative rule set would be cheap. Do **not** reformat the repository in
the same PR as a behaviour change.

### P3-4 — ~~`create_demo_user --reset` hard-deletes without confirmation~~ FIXED

Resolved in this pass: `--reset` now requires `--confirm`, refuses staff and
superuser targets outright (no override), refuses to run in production unless
`ALLOW_DEMO_USER_RESET` is set for that one command, and runs delete+recreate
inside `transaction.atomic()`. The demo account itself is no longer a
superuser — it is created with `create_user(is_staff=False,
is_superuser=False)`.

---

## Implemented in this pass (for reference)

| Area | Change |
| --- | --- |
| Settings | `SECRET_KEY` production fail-fast; `load_dotenv(override=False)`; `ALLOWED_HOSTS` wildcard rejected; `DATABASE_URL` required; `LOGGING` configured; email misconfiguration warning |
| Deployment | `predeploy.sh` fails the deploy on migration failure; deploy checks added; recurring seeds removed; `start.sh` no longer migrates; `build.sh` duplicate install removed |
| Blueprint | `render.yaml` `ALLOWED_HOSTS` is now an explicit host list |
| Demo account | `create_demo_user` no longer creates a superuser; `--reset` is guarded and atomic |
| API | `/api/v1/semantic-search/` input validated via serializer (400 not 500); dead vector branch gated and logged |
| Tests | `core/tests_deployment_safety.py` (27), `api/tests_semantic_search.py` (16) |

---

## Suggested PR sequence

1. ~~Administrator credential remediation~~ (Phase 1, done)
2. ~~Fail-safe deployment and production settings~~ (this pass, done)
3. **good_agents stale provider assertions** — prerequisite, see below
4. **CI test enforcement** (`continue-on-error` removal) — must follow (3)
5. CI on PostgreSQL (P2-4)
6. Throttle correctness (P1-2)
7. Celery worker honesty (P1-1)
8. Email delivery (P1-4)
9. Broad-exception triage, one app per PR (P1-3)
10. Dependency pinning (P2-3)
11. Decimal migration for money, one app per PR (P2-1)
12. App classification and experimental gating (P2-2)
13. Template `|safe` audit (P2-5)
