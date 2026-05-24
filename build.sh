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

echo "==> Build complete."
