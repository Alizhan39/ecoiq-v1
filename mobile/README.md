# EcoIQ — Mobile & Desktop App (Flutter)

Client for the EcoIQ Django backend. See
[`docs/adr-0002-cross-platform-app-framework.md`](../docs/adr-0002-cross-platform-app-framework.md)
for why Flutter was chosen, and
[`docs/MOBILE-API-ADDITIONS.md`](../docs/MOBILE-API-ADDITIONS.md) for the
backend contract this app consumes.

**This project was authored without a local Flutter SDK available** (see
the final report's "known risks and limitations"). Only `pubspec.yaml` and
`lib/`/`test/` source were written — the native `ios/`, `android/`,
`windows/`, `macos/`, `linux/` platform folders that `flutter create`
normally generates do **not** exist yet. Bootstrap them first:

## 1. One-time bootstrap (generates the missing platform folders)

```bash
cd mobile
flutter create --org uk.ecoiq --project-name ecoiq_app .
```

This will **not** overwrite `lib/`, `test/`, `pubspec.yaml`, or
`analysis_options.yaml` (flutter create only fills in *missing* files by
default) — it adds `ios/`, `android/`, `windows/`, `macos/`, `linux/`,
`web/`. If you don't need every platform, pass `--platforms=ios,android,windows`
to skip the rest.

## 2. Install dependencies

```bash
flutter pub get
```

## 3. Run — mock mode (no backend required)

The default build (no `--dart-define`) uses `MockEcoIqApiClient` — canned,
clearly-synthetic data, good enough to demo the login → home → search →
company-profile flow with zero setup:

```bash
flutter run
```

## 4. Run against a real backend

Start the Django dev server first (from the repo root):

```bash
python manage.py runserver 0.0.0.0:8731
```

Then, from `mobile/`:

```bash
# Dev — talks to localhost:8731 (use 10.0.2.2 instead of localhost for
# the Android emulator; iOS Simulator can use localhost directly)
flutter run --dart-define=ECOIQ_ENV=dev

# Staging
flutter run --dart-define=ECOIQ_ENV=staging

# Production
flutter run --dart-define=ECOIQ_ENV=production --release
```

## 5. Platform-specific run commands

```bash
# iOS Simulator (macOS + Xcode required)
flutter run -d ios --dart-define=ECOIQ_ENV=dev

# Android emulator/device (Android Studio + an AVD, or a connected device)
flutter run -d android --dart-define=ECOIQ_ENV=dev

# Windows desktop (Windows + Visual Studio "Desktop development with C++" workload)
flutter config --enable-windows-desktop
flutter run -d windows --dart-define=ECOIQ_ENV=dev
```

`flutter devices` lists what's currently available to target.

## 6. Tests

```bash
flutter analyze
dart format --output=none --set-exit-if-changed .
flutter test
```

`test/` covers: environment config, AuthService's login/refresh/logout/
session-restore state machine (mocked API client via `mocktail`, no
network), the adaptive-scaffold breakpoint switch (bottom nav vs sidebar),
the status-chip accessibility rule (icon + text, never color alone), the
company-repository recently-viewed cache (`shared_preferences` mock), and
the router's authentication redirect guard.

## 7. Release builds

```bash
# Android App Bundle (for Google Play)
flutter build appbundle --release

# iOS archive (for App Store Connect via Xcode)
flutter build ios --release

# Windows (MSIX packaging for Microsoft Store is a Phase 4 item -- see
# the final report; `flutter build windows` alone produces an unsigned,
# unpackaged .exe)
flutter build windows --release
```

None of these are configured with real signing credentials yet — see the
final report's "store prerequisites" and "required environment variables"
sections.
