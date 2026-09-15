#!/usr/bin/env bash
# Render Free START command. The build environment cannot reach the private
# database, and the Free plan has no Pre-Deploy command, so migrations run in
# the runtime network before Gunicorn opens the HTTP port.
set -euo pipefail

echo "==> [start] Applying database migrations..."
migrated=0
for attempt in 1 2 3 4 5; do
  if python manage.py migrate --no-input; then
    migrated=1
    break
  fi
  if [ "${attempt}" -lt 5 ]; then
    echo "    migrate attempt ${attempt} failed — retrying in 5s..."
    sleep 5
  fi
done

if [ "${migrated}" -ne 1 ]; then
  echo "[start] Migrations failed after 5 attempts — refusing to start." >&2
  exit 1
fi

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
