#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# Render START command — runs at RUNTIME (internal DB hostname resolves here).
#
# This script starts the web server and does nothing else. It deliberately does
# NOT migrate: schema changes belong to the release step (predeploy.sh), which
# runs exactly once per deploy and aborts the deploy on failure.
#
# Running migrate here as well meant every web process restart — including an
# autoscale event or an OOM restart — could mutate the production schema, with
# several workers potentially racing on the same migration, and it hid a
# pre-deploy migration failure behind an apparently healthy boot.
# ══════════════════════════════════════════════════════════════════════════════

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
