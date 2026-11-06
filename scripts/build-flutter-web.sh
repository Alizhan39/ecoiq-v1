#!/usr/bin/env bash
# Build the browser client as a static Cloudflare Pages deployment.
# Run from repository root with Flutter 3.27.x available on PATH.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR/mobile"

# Historical EcoIQ Flutter builds target iOS, Android and Windows; generate
# any missing web runner files only. Tracked custom index/manifest are retained.
# Never use --overwrite (would destroy reviewed project source).
flutter create --platforms web --project-name ecoiq_app --org uk.ecoiq .
flutter pub get --enforce-lockfile

# CRITICAL: the default Environment.fromDartDefine() is mock; production must
# point to the *real* Django API. Defines are PUBLIC client-side configuration,
# NEVER insert secrets, private keys, auth credentials or service tokens here.
flutter build web --release --dart-define=ECOIQ_ENV=production --base-href=/

test -s build/web/index.html
test -s build/web/flutter_bootstrap.js
test -s build/web/main.dart.js

# Cloudflare Pages serves static files itself, including deep-link rewrites and
# caching/security headers. Do not cache index.html across API contract changes.
cp "$ROOT_DIR/deploy/cloudflare/flutter-web/_headers" build/web/_headers
cp "$ROOT_DIR/deploy/cloudflare/flutter-web/_redirects" build/web/_redirects

echo "Flutter Web production build: $ROOT_DIR/mobile/build/web"
