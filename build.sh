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

# ── React SPA artefact ────────────────────────────────────────────────────────
#
# The built SPA lives at static/spa/ and is COMMITTED to the repository. Render's
# Python environment has no Node toolchain, and this repo's two other Node layers
# (frontend/app islands, frontend/remotion) are already build-time-only by design
# — Node is never a runtime dependency here.
#
# So the build does not compile the frontend; it verifies that what was committed
# is complete, and REFUSES TO DEPLOY otherwise. A missing or half-committed
# artefact would otherwise ship as a blank white page with a 404 in the console
# and no server-side error at all.
#
# CI rebuilds from source and diffs the result (see .github/workflows/django.yml,
# job `frontend`), so a stale artefact fails the pull request. This check is the
# last line of defence, not the only one.
echo "==> Verifying the committed React SPA artefact..."
SPA_INDEX="static/spa/index.html"
if [ ! -f "$SPA_INDEX" ]; then
  echo "ERROR: $SPA_INDEX is missing." >&2
  echo "       Run: npm --prefix frontend/web ci && npm --prefix frontend/web run build" >&2
  echo "       then commit static/spa/." >&2
  exit 1
fi
if ! grep -q 'ecoiq:head:start' "$SPA_INDEX"; then
  echo "ERROR: $SPA_INDEX has no <!--ecoiq:head:start--> block." >&2
  echo "       Per-route metadata cannot be injected. See core/spa.py." >&2
  exit 1
fi
# Every hashed asset the shell names must actually be on disk.
python - <<'PYCHECK'
import re, sys
from pathlib import Path

shell = Path('static/spa/index.html')
referenced = re.findall(r'/static/(spa/assets/[^"\']+)', shell.read_text())
if not referenced:
    sys.exit('ERROR: static/spa/index.html references no assets at all.')
missing = [a for a in referenced if not (Path('static') / a).exists()]
if missing:
    sys.exit('ERROR: the committed SPA artefact is stale. Missing: '
             + ', '.join(missing))
print(f'   {len(referenced)} entry asset(s) verified present.')
PYCHECK

echo "==> Collecting static files... (no database access)"
python manage.py collectstatic --no-input

echo "==> Build complete (database untouched — migrations run in predeploy.sh)."
