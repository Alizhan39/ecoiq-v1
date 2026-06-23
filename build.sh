#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# Render BUILD script — runs in the build environment, which has NO access to
# the private database network. The internal Postgres hostname (dpg-…-a) does
# NOT resolve here, so this script must never touch the database.
#
#   Database migrations + seeding run at RUNTIME instead — see predeploy.sh
#   (Render Pre-Deploy Command) and start.sh (web start command), where the
#   internal database hostname resolves.
#
# Keeping the build DB-free means the service builds and deploys even when the
# database is temporarily unavailable.
# ══════════════════════════════════════════════════════════════════════════════
set -o errexit

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Compiling translation messages..."
python manage.py compilemessages || true

echo "==> Collecting static files... (no database access)"
python manage.py collectstatic --no-input

echo "==> Build complete (database untouched — migrate/seed run at runtime)."
