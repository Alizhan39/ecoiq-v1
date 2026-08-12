# Mobile/Desktop App — Backend API Additions

Companion to `docs/adr-0002-cross-platform-app-framework.md`. Everything
here is real, migrated, and tested (`mobile_auth/tests.py`,
`api/tests.py::MobileAndAPIKeyAuthCoexistTest`). No endpoint here
duplicates business logic that already lives elsewhere in the backend —
they're either new auth/config plumbing, or thin wrappers around
`ecoiq_commerce.services.entitlements.has_entitlement`.

## New: `mobile_auth` app — end-user device auth

Deliberately separate from `api.APIKey` (long-lived B2B licensing
credential) and from the website's `SessionAuthentication` (cookie-based).
No new third-party auth dependency — access tokens are signed with
Django's own `django.core.signing` (HMAC over `SECRET_KEY`, the same
primitive behind password-reset tokens); refresh tokens are opaque,
SHA-256-hashed-at-rest, single-use-then-rotated, following the exact
pattern already established by `api.models.APIKey`.

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/api/v1/auth/login/` | POST | none | `{username, password, device_id, device_name?, platform?, app_version?}` → access + refresh token pair. Re-login on the same `device_id` replaces that device's prior session. Throttled (`auth_login` scope, 10/hour/IP). |
| `/api/v1/auth/refresh/` | POST | none | `{refresh_token}` → new pair. **Rotates** — the old refresh token stops working immediately. Replaying an already-rotated token is detected as reuse and **revokes the whole session** (suspicious-login handling). |
| `/api/v1/auth/logout/` | POST | Bearer access token | Revokes the current device's session only. |
| `/api/v1/auth/logout-all/` | POST | Bearer access token | Revokes every active session for the user ("logout from all devices"). |
| `/api/v1/auth/sessions/` | GET | Bearer access token | Lists the caller's own active sessions (device name, platform, last used, `is_current`). Never another user's. |
| `/api/v1/auth/sessions/<id>/revoke/` | POST | Bearer access token | Revokes one of the caller's own sessions. IDOR-safe: scoped to `user=request.user`, 404s (not 403) for anyone else's session id. |

Access tokens: 15 minutes (`MOBILE_AUTH_ACCESS_TOKEN_TTL_MINUTES`), and
re-checked against a live, non-revoked `DeviceSession` on **every** request
(not just at issuance) — so `logout`/`logout-all`/revocation take effect
immediately rather than waiting for the token to expire.
Refresh tokens: 60 days (`MOBILE_AUTH_REFRESH_TOKEN_TTL_DAYS`).

## New: `api/app_views.py`

| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/api/v1/me/` | GET | Bearer (mobile token or session) | Current user + an entitlement summary (`{feature_key: bool}` for the 8 app-relevant feature keys) + active plan, if any. The app must still treat every gated read as server-authoritative — this is a UI-decision hint, not a bypass (see `RequiresFeature` below). |
| `/api/v1/app-config/` | GET | none | Remote configuration: `min_supported_version`, `latest_version`, `maintenance_mode`, `force_update`, enabled products/plans, legal-document URLs+versions (currently `null` — no `/privacy/` or `/terms/` page exists on the site yet, verified by inspection), support contact, store URLs (currently `null` — nothing is published). |

## Changed: existing files, minimal and load-bearing

- **`api/commercial_views.py`** — every view's `authentication_classes` now
  lists `MobileTokenAuthentication` alongside the existing
  `APIKeyAuthentication`. Without this, a mobile app user's Bearer access
  token hit `APIKeyAuthentication` first (both schemes read the same
  header), which raises a hard 401 for anything that isn't a real API key
  — discovered and fixed via the new test suite, not left as a silent gap.
- **`api/views.py`** — the same fix applied to exactly the four endpoints
  the app's functional shell calls this pass: `search()`,
  `CompanyDetailView`, `CompanyScoresView`, `CompanyHarmSignalsView`.
  `api/views.py` has ~15 more endpoints with the identical
  `authentication_classes = [APIKeyAuthentication]` pattern (leaderboard,
  countries, capital-integrity, Hikma evidence, Islamic-finance-fit, etc.)
  that were **not** touched — they're outside what this pass's app shell
  needs, and blanket-editing all of them without reviewing each one
  individually was judged higher-risk than leaving them as a documented
  follow-up (see the final report's §17 "prepared, not operational").
- **`api/permissions.py:RequiresFeature`** — now resolves entitlement from
  EITHER an `APIKey` (existing B2B path, unchanged) OR, when the caller is
  a logged-in app user with no API key, that user's own subscription via
  the exact same `has_entitlement()` call. This is what lets the mobile
  app reuse `/companies/<slug>/evidence/`, `/ethical-screening/`,
  `/islamic-screening/`, `/investment-relevance/` without any new
  per-endpoint logic.
- **`api/throttles.py:APIKeyRateThrottle`** — was assuming `request.auth`
  is always an `api.models.APIKey` (`key_obj.prefix`, `key_obj.tier`);
  crashed with a 500 the instant a `mobile_auth.DeviceSession` showed up in
  `request.auth`. Now guarded with `isinstance(request.auth, APIKey)`,
  falling back to IP-based `anon` throttling for anything else.
- **`ecoiq/settings.py`** — `mobile_auth` added to `INSTALLED_APPS`;
  `MobileTokenAuthentication` added to `DEFAULT_AUTHENTICATION_CLASSES`
  **before** `APIKeyAuthentication` (ordering matters — see the inline
  comment in settings.py); `auth_login` throttle scope added;
  `MOBILE_AUTH_ACCESS_TOKEN_TTL` / `MOBILE_AUTH_REFRESH_TOKEN_TTL` /
  `ECOIQ_APP_*` remote-config values added, all env-overridable.

## Explicitly NOT added this pass (see final report §17)

Portfolios, watchlists, and alerts have **no JSON API today** — only
server-rendered Django views (`investor_portfolio`). The mobile app's
functional shell (login → home → search → company profile) does not need
them; wiring them up is the first Phase 2 item.
