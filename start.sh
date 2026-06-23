#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# Render START command — runs at RUNTIME (internal DB hostname resolves here).
#
# A fast, best-effort `migrate` runs as a safety net so that, if the DB was
# unavailable during pre-deploy, schema is brought up to date on the next start
# once the database is back — WITHOUT requiring a fresh deploy. It never blocks
# boot: if the database is still down, we log and start gunicorn anyway, so the
# web service comes up and serves (the app has no import-time DB access).
#
# Heavy data seeding lives in predeploy.sh (once per deploy), not here, so it
# never delays the port binding / health check.
# ══════════════════════════════════════════════════════════════════════════════

echo "==> [start] Applying database migrations (best-effort)..."
python manage.py migrate --no-input || \
  echo "⚠  [start] Database unavailable — starting web server anyway (migrations deferred)."

echo "==> [start] Launching Gunicorn..."
exec gunicorn ecoiq.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --worker-class gthread \
  --threads 4 \
  --timeout 120 \
  --max-requests 300 \
  --max-requests-jitter 50 \
  --log-file -
