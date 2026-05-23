#!/usr/bin/env bash
# Render build script — runs once per deploy before the server starts.
# Render's Python environment is Ubuntu, so apt-get works here.
set -o errexit

echo "==> Installing WeasyPrint system dependencies..."
apt-get update -qq
apt-get install -y -qq \
  libcairo2 \
  libpango-1.0-0 \
  libpangocairo-1.0-0 \
  libgdk-pixbuf2.0-0 \
  libffi-dev \
  shared-mime-info \
  fonts-liberation \
  mime-support

echo "==> Installing Python dependencies..."
pip install -r requirements.txt

echo "==> Collecting static files..."
python manage.py collectstatic --no-input

echo "==> Running database migrations..."
python manage.py migrate --no-input

echo "==> Build complete."
