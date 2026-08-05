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
set -euo pipefail

# NOTE: dependencies are installed by render.yaml's buildCommand
#   pip install -r requirements.txt && ./build.sh
# so this script must NOT install them again — doing so doubled build time and
# could resolve a different version than the one the build command pinned.

echo "==> Compiling translation messages..."
# Optional: msgfmt (gettext) is not guaranteed on the build image, and no
# non-English locale is currently enabled in settings.LANGUAGES. A failure here
# must not fail the build, unlike every other step in this script.
python manage.py compilemessages || echo "   (skipped — gettext unavailable)"

echo "==> Collecting static files... (no database access)"
python manage.py collectstatic --no-input

echo "==> Build complete (database untouched — migrations run in predeploy.sh)."
