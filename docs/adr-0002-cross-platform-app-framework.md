# ADR-0002: Cross-Platform Application Framework (iOS, Android, Windows/Microsoft Store)

**Status:** Accepted — Phase 1 (foundation + functional shell) implemented in this change.
**Date:** 2026-07-31

## Context

EcoIQ needs a client application for iOS, Android, and Windows desktop
(distributed via Microsoft Store), backed entirely by the existing Django
API — not a new source of truth. Before picking a framework, the existing
architecture was inspected:

- **`frontend/app`** (Vite + React + TypeScript) is explicitly a
  **build-time-only** layer — per its own `package.json` description:
  "EcoIQ Visual Intelligence layer (React islands). BUILD-TIME ONLY — never
  a Render runtime dependency." It compiles to `static/dist/` and is served
  by WhiteNoise inside Django-rendered pages. It has no app shell, no
  client-side router, no API client, and is not a runtime SPA. **There is no
  existing runtime frontend to extend into a mobile/desktop app.**
- **Authentication** is Django's default session/cookie auth
  (`rest_framework.authentication.SessionAuthentication` is the only
  configured DRF authenticator; `AUTH_USER_MODEL` is unset, i.e. the
  built-in `django.contrib.auth.User`). No token/JWT auth exists yet. The
  `api` app's `APIKeyAuthentication` is a **separate, B2B-only** scheme
  (long-lived hashed keys for institutional data licensing) — wrong shape
  for an individual end user logging into a phone (no per-device session
  concept, no short-lived/refreshable tokens). A new token-auth surface is
  required regardless of which client framework is chosen (see
  `docs/MOBILE-API-ADDITIONS.md`).
- **Commercial entitlements** (`ecoiq_commerce.services.entitlements.has_entitlement`)
  and the **API surface** (`/api/v1/...`, DRF, already versioned) are
  framework-agnostic HTTP/JSON — any client technology can consume them
  unchanged.
- **Portfolios & watchlists** (`investor_portfolio`) are currently
  **server-rendered Django views only** — no JSON endpoints exist yet. This
  is a real gap for *any* native client, independent of framework choice
  (tracked as a Phase 2 API item, not solved by this ADR).
- **Deployment** is Render (Gunicorn + Postgres), a plain HTTP/JSON API
  target — no GraphQL, no gRPC, nothing that favors one client stack over
  another.

Given the backend is a stable, versioned JSON API and there's no existing
runtime client code to reuse, the framework choice is a **fresh, unconstrained
decision** — not a migration.

## Options considered

| | Flutter | React Native (+ react-native-windows) | .NET MAUI | PWA |
|---|---|---|---|---|
| iOS maturity | High — first-class, compiled | High — industry standard | Medium — smaller ecosystem, native bindings less mature | N/A (installable web) |
| Android maturity | High | High | Medium | N/A |
| Windows (Store-distributable native app) | **Stable** desktop target since Flutter 3; produces a real Win32 app; `msix` package documents Store packaging directly | `react-native-windows` exists (Microsoft-maintained) but has a history of lagging behind RN-core releases and a much smaller community than Flutter's Windows target | **Best-in-class** — WinUI 3 native, since it's Microsoft's own framework | Can be wrapped for the Store via PWABuilder, but is not a native app; weak background push, weak secure-storage story |
| One shared codebase for all 3 | Yes — single Dart codebase | Partial — RN core code shares, but `react-native-windows` historically requires more platform-specific patching than Flutter's Windows engine | Yes — single C#/XAML codebase | Yes, but it's one web codebase, not one native codebase |
| Fits existing team/stack | Dart is new, but self-contained (doesn't collide with Python/Django or the React *islands* layer) | Reuses React *knowledge* (JSX, hooks) but not any *code* — RN's primitives (`View`, native modules) share nothing with the DOM-based islands components | Introduces C#/XAML — a second full ecosystem with zero overlap with Python/Django or React | No new language; weakest native-app fit for the actual requirement (Store-distributed Windows desktop app + true iOS/Android app-store apps) |
| Secure storage (Keychain/Keystore/Credential Locker) | `flutter_secure_storage` — covers all 3 platforms directly | Requires separate native modules per platform; Windows story is less standardized | Native `Microsoft.Maui.Storage`/DPAPI — strong on Windows, adequate elsewhere | Web Crypto / IndexedDB only — no real Keychain/Keystore access |
| Accessibility (WCAG-shaped semantics) | Strong (`Semantics` widget maps to native a11y trees on every platform) | Strong, but Windows a11y bridging is less mature | Strong on Windows; adequate on mobile | Depends entirely on HTML semantics; weakest for native screen-reader parity |

## Decision

**Flutter.** It is the only option that gives EcoIQ a **stable, actually-shipping**
native Windows target *and* mature iOS/Android support from a **single**
codebase, without introducing a second general-purpose language ecosystem
that has no overlap with the existing Python/Django backend or the
TypeScript/React islands layer. `react-native-windows` is real but
historically the highest-maintenance of the three native options for the
Windows leg specifically; `.NET MAUI` has the best pure-Windows story but
the weakest cross-platform code-sharing story once Windows-specific XAML/C#
creeps in, and it forces a second full language stack onto the team. PWA is
rejected as the primary target because the spec explicitly requires a
Microsoft-Store-distributed **desktop application** with Keychain/Keystore-grade
secure storage and native push — a PWA cannot deliver either credibly; it
remains the documented fallback if Flutter's Windows target proves
insufficient during Phase 2/3 hardening.

Dart/Flutter has zero collision with the existing stack: it doesn't touch
Python, doesn't touch the React islands build, and talks to the backend
over plain HTTP/JSON exactly like the islands' own fetch calls do.

## Consequences

- A new top-level `mobile/` directory holds the Flutter project. It is a
  **client only** — no scoring, compliance, subscription, or publication
  logic is duplicated there (see `docs/MOBILE-API-ADDITIONS.md` for the
  contract it consumes).
- The Django backend needs new endpoints this ADR's implementation adds:
  token auth, current-user/entitlement-summary, and remote app-config (see
  `docs/MOBILE-API-ADDITIONS.md`). Everything else (companies, screening,
  investment-relevance, products/plans) is reused as-is from `/api/v1/`.
- Portfolios/watchlists/alerts JSON endpoints do **not** exist yet and are
  explicitly out of scope for this Phase 1 pass — the functional shell
  built here covers auth, home shell, company search, and company-profile
  navigation only, per the bounded Phase 1 scope requested.
- This environment has no Flutter SDK installed, so the Dart code in this
  change has not been compiled or run here — see the final report's
  "known risks and limitations" and "exact local-run commands" sections.
