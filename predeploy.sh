#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# Render PRE-DEPLOY command — runs once per deploy in the RUNTIME network, where
# the internal Postgres hostname (dpg-…-a) resolves. This is the correct place
# for database migrations (NOT the build phase, which has no database access).
#
# FAIL-SAFE by design: if migrations or the deployment checks fail, this script
# exits non-zero and Render aborts the deploy, leaving the previous known-good
# release serving. It previously swallowed every failure and exited 0, which
# meant a broken migration produced a green deploy and a half-migrated schema
# behind live traffic.
#
# A short retry loop is still allowed for the *connection* only — a Render
# Postgres instance can take a few seconds to accept connections after a
# restart. Exhausting the retries is a deploy failure, not a skip.
#
# What this script deliberately does NOT do:
#   - create administrators (see docs/security/admin-credential-rotation.md)
#   - seed demo/reference data (see docs/engineering/deployment-runbook.md)
# Both are explicit, idempotent operator actions, not deploy side effects.
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

echo "==> [pre-deploy] Applying database migrations..."
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
  echo "✗  [pre-deploy] Migrations failed after 5 attempts — aborting the deploy."
  echo "   The previous release stays live. Fix the migration or the database"
  echo "   connection and redeploy; do not bypass this check."
  exit 1
fi

# Deployment-security checks (secure cookies, HSTS, SSL redirect, ALLOWED_HOSTS).
# ERROR-level findings abort the deploy; warnings are printed for visibility.
echo "==> [pre-deploy] Running Django deployment checks..."
python manage.py check --deploy --fail-level ERROR

echo "==> [pre-deploy] Complete."
