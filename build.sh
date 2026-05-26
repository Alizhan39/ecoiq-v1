#!/usr/bin/env bash
# Render build script — runs once per deploy before the server starts.
set -o errexit

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Collecting static files..."
python manage.py collectstatic --no-input

echo "==> Running database migrations..."
python manage.py migrate --no-input

echo "==> Setting up Wagtail site structure..."
python manage.py setup_wagtail_site

echo "==> Bootstrapping admin superuser..."
python manage.py bootstrap_superuser

echo "==> Seeding country intelligence profiles..."
python manage.py seed_countries

echo "==> Build complete."
echo ""
echo "NOTE: Company data seeds must be run manually via Render Shell:"
echo "  python manage.py seed_global_companies"
echo "  python manage.py seed_phase2_companies"
