#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# Render PRE-DEPLOY command — runs once per deploy in the RUNTIME network, where
# the internal Postgres hostname (dpg-…-a) resolves. This is the correct place
# for database migrations + seeding (NOT the build phase).
#
# Best-effort by design: every step is guarded and the script always exits 0, so
# a temporarily-unavailable database can never block a deploy. Migrations are
# retried briefly in case the database is still waking up.
# ══════════════════════════════════════════════════════════════════════════════
set +e   # never abort the deploy on a database hiccup

echo "==> [pre-deploy] Applying database migrations (with brief retry)..."
migrated=0
for attempt in 1 2 3 4 5; do
  if python manage.py migrate --no-input; then
    migrated=1
    break
  fi
  echo "    migrate attempt ${attempt} failed (database not reachable yet) — retrying in 5s..."
  sleep 5
done

if [ "${migrated}" -ne 1 ]; then
  echo "⚠  [pre-deploy] Database unreachable — skipping migrate + seed this deploy."
  echo "   The app will still start; migrations apply on the next start once the DB is back."
  exit 0
fi

echo "==> [pre-deploy] Bootstrapping admin superuser..."
python manage.py bootstrap_superuser || echo "   (skipped)"

echo "==> [pre-deploy] Seeding country intelligence profiles..."
python manage.py seed_countries || echo "   (skipped)"

echo "==> [pre-deploy] Seeding phase-1 / phase-2 company profiles (idempotent)..."
python manage.py seed_global_companies  2>/dev/null || true
python manage.py seed_phase2_companies  2>/dev/null || true

echo "==> [pre-deploy] Seeding strategic companies — UK / Saudi / Kazakhstan / Global..."
python manage.py add_400_companies || echo "   (skipped)"

echo "==> [pre-deploy] Seeding score-history snapshots (idempotent)..."
python manage.py seed_score_history || echo "   (skipped)"

echo "==> [pre-deploy] Focusing public profiles on UK / Kazakhstan / Saudi Arabia / Türkiye..."
python manage.py focus_target_markets || echo "   (skipped)"

echo "==> [pre-deploy] Complete."
exit 0
