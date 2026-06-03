#!/usr/bin/env bash
# Render build script — runs once per deploy before the server starts.
set -o errexit

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Compiling translation messages..."
python manage.py compilemessages || true

echo "==> Collecting static files..."
python manage.py collectstatic --no-input

echo "==> Running database migrations..."
python manage.py migrate --no-input

echo "==> Bootstrapping admin superuser..."
python manage.py bootstrap_superuser

echo "==> Seeding country intelligence profiles..."
python manage.py seed_countries

echo "==> Seeding phase-1 and phase-2 company profiles (idempotent)..."
python manage.py seed_global_companies  2>/dev/null || true
python manage.py seed_phase2_companies  2>/dev/null || true

echo "==> Seeding 186 strategic companies — UK / Saudi / Kazakhstan / Global (idempotent)..."
python manage.py add_400_companies

echo "==> Seeding score-history snapshots for Chart.js trend charts (idempotent)..."
python manage.py seed_score_history

echo "==> Focusing public profiles on 4 target markets: UK / Kazakhstan / Saudi Arabia / Türkiye..."
python manage.py focus_target_markets

echo "==> Build complete."
