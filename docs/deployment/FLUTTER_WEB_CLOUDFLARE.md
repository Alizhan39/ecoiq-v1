# EcoIQ Flutter Web on Cloudflare Pages

## Architecture

- **Public website**: existing React SPA (unchanged by this change).
- **Flutter app**: static web assets deployed to Cloudflare Pages; proposed
  hostname `app.ecoiq.uk` (not live until DNS and Cloudflare are configured).
- **Django**: unchanged API host `https://ecoiq.uk/api/v1` for
  authentication/app-config and `https://ecoiq.uk/api/v2` for company data.
- **PostgreSQL, formulas, provenance and AI**: stay exclusively on the Django
  backend. Flutter Web does not compute scores or fabricate evidence.

This is a separate Flutter build from the React public website: **do not**
replace the existing Render deployment or serve production Flutter assets
from a second Django worker.

## Build & verify

The pinned GitHub Actions workflow `.github/workflows/flutter-web.yml` runs
the browser-safe device test in Chrome, builds a release JS client using the
**production** Dart define, and uploads `mobile/build/web` as an Actions
artifact on PRs and pushes to main. It only performs a live Pages deployment
for a successful push to `main` **when Cloudflare GitHub secrets are set**.

Local commands with Flutter **3.27.x** on PATH:

```bash
bash scripts/build-flutter-web.sh
cd mobile
flutter test --platform chrome test/core/device_info_web_test.dart
```

The script generates any missing Flutter web runner boilerplate on a fresh
checkout, preserves the version-controlled `mobile/web/index.html` and
`mobile/web/manifest.json`, enforces `pubspec.lock`, and builds the Flutter
client with `--dart-define=ECOIQ_ENV=production` (rather than the otherwise
default, synthetic `mock` environment). It copies Pages `_headers` and
`_redirects` into `build/web`, which is the upload directory.

`--dart-define` values are **public** in compiled JavaScript: never use them
for production secrets or Cloudflare access tokens.

## One-time Cloudflare setup (account owner)

1. In Cloudflare **Workers & Pages**, create a **Pages / Direct Upload**
   project named **`ecoiq-flutter`**. Use Direct Upload, *not* the separate
   Git-integration build mode: CI already builds and uploads via Wrangler.
2. Create a Cloudflare API token scoped to the correct account with
   **Cloudflare Pages: Edit** permission.
3. In GitHub `Alizhan39/ecoiq-v1` repository secrets, set
   `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`. Do not write the
   actual values to YAML, `.env`, PR comments or this documentation.
4. After the Flutter Web PR is reviewed and merged, a **push to main**
   automatically builds and deploys the static artifact. Confirm the actual
   resulting `*.pages.dev` hostname in the Cloudflare dashboard.
5. Point **`app.ecoiq.uk`** to the Pages project using its **Custom Domains**
   tab, verify HTTPS and certificate issuance, and test direct navigation to
   `/login`, `/home`, `/search` and `/company/<slug>`.

If secrets are missing, CI still builds/tests but **does not deploy**. Do not
misinterpret green build checks as a live website.

## Django browser CORS setup (Render)

CORS is disabled until explicit, trusted origins are configured. On the
**Django Render service**, after verifying the exact Pages URLs, add:

```text
ECOIQ_CORS_ALLOWED_ORIGINS=https://app.ecoiq.uk https://ecoiq-flutter.pages.dev
```

Use only domains you control and have confirmed. Avoid wildcard
`*.pages.dev` or `*` to prevent untrusted pages from issuing browser
API requests. Production settings reject HTTP, wildcard, user-info or
path-bearing origins. Django's `corsheaders.middleware.CorsMiddleware`
is restricted to `/api/` and credentials remain disabled:
Bearer Authorization works with the standard preflight. This is CORS
**only**, not CSRF approval or authentication. Never expose private endpoints
through allow-origin settings alone.

Browser smoke check (replace with the actual deployed hostname):

```bash
curl -i -X OPTIONS 'https://ecoiq.uk/api/v1/app-config/' \
  -H 'Origin: https://app.ecoiq.uk' \
  -H 'Access-Control-Request-Method: GET' \
  -H 'Access-Control-Request-Headers: authorization,content-type'
```

Only the verified origin should receive
`Access-Control-Allow-Origin: https://app.ecoiq.uk`.

## Important browser security limits

`flutter_secure_storage` uses WebCrypto/localStorage on web, rather than
iOS Keychain or Android Keystore; this implementation is experimental, and
does not make the browser immune to XSS or malicious browser extensions.
Use HTTPS, enforce restrictive permitted hosts/origins and review the token
lifecycle before allowing high-value production accounts. Never log tokens,
embedding inputs or evidence documents in browser analytics.

- Frontend authenticated navigation is a convenience; **Django remains the
  sole authorisation boundary**.
- The Django mobile-auth model has no separate `web` enum, so browser
  clients use the existing `other` platform and the `Web browser` label;
  no migration is necessary.
- Service-worker/offline caching and push notifications are **not** enabled.
- Pages `_redirects` support Flutter GoRouter deep links;
  `_headers` provide browser-safe defaults and no-store HTML bootstrap.
- There is no proof of live Cloudflare deployment, domain ownership,
  production CORS, or browser API interoperability until exercised after
  account setup.
