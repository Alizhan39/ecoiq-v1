---
name: ecoiq-release-gate
description: What to actually run before calling an EcoIQ change done — the smallest useful check during development, and the full CI-equivalent suite before reporting completion. Use when finishing any code change in this repo, or when asked whether something is ready to merge or deploy. Not needed for documentation-only edits that touch no code path.
---

# Release gate

Two tiers. Use the narrow one while working; the full one before you report
completion. Never report a result you did not run **this session**
(root `CLAUDE.md` rule 13).

## Tier 1 — while developing (seconds)

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py test <app> [<app> ...]
```

Pick the apps your diff touches. `manage.py check` is cheap and catches most
settings/URL/model mistakes immediately.

## Tier 2 — before reporting done (CI-equivalent, ~1 minute)

Exactly what `.github/workflows/django.yml` runs, plus the skills validator:

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py validate_skills
.venv/bin/python manage.py test --parallel 4
```

`makemigrations --check` is a real gate: a model change without a migration
fails CI. `--parallel 4` is safe here and cuts the suite to under a minute.

**Recorded baseline (2026-08-25, pre-change, this repo):** 2881 tests, `OK
(skipped=2)`, 54.1s, exit 0; `check` clean; `makemigrations --check` reports
no changes. Compare against this, and state any difference explicitly rather
than describing a new failure as pre-existing.

## Frontend changes additionally require

```bash
cd frontend/app && npm run build     # runs tsc --noEmit then vite build
```

and browser evidence per [`docs/AI-QUALITY-GATES.md`](../../../docs/AI-QUALITY-GATES.md)
§9 — dev server on port 8731 via `.claude/launch.json`, console clean,
network clean, three viewports, interactions actually exercised. A frontend
change is **not** done on a green test suite alone; tests verify code, not
appearance.

`static/dist/` is a committed build artifact — if the island bundle changed,
the rebuilt files belong in the same commit.

## Remotion changes

`frontend/remotion/` is build-time only and is **not** in the Django runtime
or in CI. Verify with `npm run studio` locally; never add it to
`requirements.txt`, `build.sh`, or `start.sh`.

## What does not count as verification

- A green suite for a UI change.
- "Should work" / "the types check out."
- Re-reading your own diff.
- A test you weakened, skipped, or deleted to get green — prohibited. If a
  test now fails legitimately because behaviour intentionally changed, change
  the test *and say so*, with the reason.

## Deployment boundary

This gate stops at "ready." It never deploys. `render.yaml`, `build.sh`,
`predeploy.sh`, and `start.sh` are production deployment config — changing
them, running migrations against a non-local database, or triggering a deploy
requires explicit user approval first (root `CLAUDE.md` rule 15).
