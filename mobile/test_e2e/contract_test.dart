/// Mobile <-> Django end-to-end CONTRACT test.
///
/// This is the only test in the repository where the real Flutter API client
/// talks to a real Django server over a real socket. Everything else is
/// isolated: the Dart suite mocks its transport, and the Django suite exercises
/// views without a client. Both can stay green while the contract between them
/// breaks -- a renamed field, a changed status code, a moved path. That gap is
/// what this file closes.
///
/// NOT under test/ on purpose: `flutter test --coverage` (the analyze-and-test
/// job) runs test/ recursively and must stay hermetic. This file needs a live
/// server and is run only by the mobile-backend-e2e CI job, via
///     flutter test test_e2e/ --dart-define=ECOIQ_ENV=dev
///
/// REQUEST BUDGET -- read before adding a test here.
///
/// Every request this file makes, authenticated or not, currently draws on the
/// server's `anon` bucket of 20/day keyed by IP. That is not a test artefact:
/// api/throttles.py::APIKeyRateThrottle only recognises an APIKey, so a
/// DeviceSession-authenticated mobile request falls through to scope 'anon'.
/// See docs -- it is a real production defect this test found, filed
/// separately; the throttle is deliberately NOT relaxed here, because a
/// contract test that needed security turned down would be testing a server
/// nobody runs.
///
/// Consequence: the whole file must complete in under 20 requests. It is
/// therefore written as a few long flows rather than many small tests, and
/// assertions are folded into an existing session wherever possible. Note
/// also that the production interceptor turns a 401-with-a-stale-token into
/// three requests (original -> refresh -> retry), so each such probe costs
/// three units, not one.
///
/// Coverage deliberately deferred until the throttle defect is fixed:
/// individual session revocation by id. It needs a third login plus a
/// verification call, which does not fit. Add it once mobile requests no
/// longer land on the anon bucket.
///
/// There is deliberately NO mock transport here. The client is the production
/// DioEcoIqApiClient with the production Environment; only the server address
/// (localhost) and the credentials (CI-only, generated per run) differ.
library;

import 'dart:io';

import 'package:ecoiq_app/config/environment.dart';
import 'package:ecoiq_app/core/api/api_exception.dart';
import 'package:ecoiq_app/core/api/dio_api_client.dart';
import 'package:ecoiq_app/core/auth/auth_models.dart';
import 'package:ecoiq_app/core/auth/auth_token_provider.dart';
import 'package:flutter_test/flutter_test.dart';

/// Minimal in-memory token store. This stands in for AuthService only to hold
/// tokens -- it performs no HTTP itself, so every request/response on the wire
/// is still produced by the production client.
class _MemoryTokens implements AuthTokenProvider {
  String? _access;
  String? _refresh;
  int refreshedCount = 0;
  int refreshFailedCount = 0;

  void seed(TokenPair pair) {
    _access = pair.accessToken;
    _refresh = pair.refreshToken;
  }

  void clear() {
    _access = null;
    _refresh = null;
  }

  @override
  String? get currentAccessToken => _access;

  @override
  String? get currentRefreshToken => _refresh;

  @override
  Future<void> handleTokensRefreshed(TokenPair pair) async {
    refreshedCount++;
    seed(pair);
  }

  @override
  Future<void> handleRefreshFailed() async {
    refreshFailedCount++;
    clear();
  }
}

String _requiredEnv(String key) {
  final v = Platform.environment[key];
  if (v == null || v.isEmpty) {
    throw StateError(
      '$key is not set. This test requires the CI fixture created by the '
      'mobile-backend-e2e job; it is not runnable standalone.',
    );
  }
  return v;
}

void main() {
  // Credentials are generated per CI run and exported by the workflow. They
  // are never hardcoded, never reused, and die with the runner.
  final username = _requiredEnv('E2E_USERNAME');
  final password = _requiredEnv('E2E_PASSWORD');

  late Environment env;
  late _MemoryTokens tokens;
  late DioEcoIqApiClient client;

  setUp(() {
    env = Environment.fromDartDefine();
    tokens = _MemoryTokens();
    client = DioEcoIqApiClient(environment: env, tokenProvider: tokens);
  });

  test('the client is pointed at a local server, never production', () {
    // Costs no requests.
    expect(env.isMock, isFalse,
        reason: 'the mock client would not exercise the contract at all');
    expect(env.apiBaseUrl, contains('localhost'),
        reason: 'E2E must never run against production');
    expect(env.apiBaseUrl, isNot(contains('ecoiq.uk')));
  });

  test('public config, enforced auth, and the full session lifecycle',
      () async {
    // ── 1. public endpoint parses (1 request) ────────────────────────────
    final config = await client.getAppConfig();
    expect(config.minSupportedVersion, isNotEmpty);
    expect(config.latestVersion, isNotEmpty);
    expect(config.maintenanceMode, isA<bool>());
    expect(config.forceUpdate, isA<bool>());

    // ── 2. /me/ is NOT public (1 request -- no stale token, so no retry) ──
    late EcoIqApiException unauth;
    try {
      await client.getMe();
      fail('/me/ must not be reachable without authentication');
    } on EcoIqApiException catch (e) {
      unauth = e;
    }
    expect(unauth.statusCode, 401);
    expect(unauth.type, EcoIqApiErrorType.unauthorized);
    expect(unauth.message, isNotEmpty,
        reason: 'Django must still return {"detail": ...} and the client must '
            'still find it');
    expect(unauth.message, isNot(contains('<html')),
        reason: 'an HTML body means the server 500ed, not a contract 401');

    // ── 3. login (1 request) ─────────────────────────────────────────────
    final pair = await client.login(
      username: username,
      password: password,
      deviceId: 'e2e-primary',
      deviceName: 'ci-runner',
      platform: 'android',
      appVersion: '1.0.0',
    );
    expect(pair.accessToken, isNotEmpty);
    expect(pair.refreshToken, isNotEmpty);
    expect(pair.accessTokenExpiresIn, greaterThan(0));
    expect(pair.sessionId, greaterThan(0));
    tokens.seed(pair);

    // ── 4. authenticated /me/ (1 request) ────────────────────────────────
    final me = await client.getMe();
    expect(me.username, username);
    expect(me.id, greaterThan(0));
    expect(me.entitlements, isA<Map<String, bool>>());
    expect(me.entitlements, isNotEmpty,
        reason: 'the app gates features on these keys; an empty map means the '
            'entitlement contract changed');

    // ── 5. sessions list (1 request) ─────────────────────────────────────
    final sessions = await client.listSessions();
    expect(sessions, isNotEmpty);
    final current = sessions.firstWhere((s) => s.isCurrent);
    expect(current.id, pair.sessionId);
    expect(current.platform, isNotEmpty);

    // ── 6. refresh, then prove the new token works (2 requests) ──────────
    final refreshed = await client.refresh(pair.refreshToken);
    expect(refreshed.accessToken, isNotEmpty);
    expect(refreshed.sessionId, pair.sessionId,
        reason: 'refresh must rotate the token, not the session identity');
    tokens.seed(refreshed);
    final meAfterRefresh = await client.getMe();
    expect(meAfterRefresh.id, me.id);

    // ── 7. logout (1 request) ────────────────────────────────────────────
    await client.logout();

    // ── 8. the revoked refresh token must be dead (1 request) ────────────
    //     Checked before the access-token probe on purpose: refresh is not
    //     wrapped by the retry interceptor, so it costs one unit rather than
    //     three.
    late EcoIqApiException deadRefresh;
    try {
      await client.refresh(refreshed.refreshToken);
      fail('a refresh token from a revoked session must be rejected');
    } on EcoIqApiException catch (e) {
      deadRefresh = e;
    }
    expect(deadRefresh.statusCode, 401);
  });

  test('logout-all revokes a session other than the calling one', () async {
    // Two devices, one user. Proving logout-all reaches a session the call
    // was NOT made from is the property worth testing.
    final first = await client.login(
      username: username,
      password: password,
      deviceId: 'e2e-multi-a',
      deviceName: 'ci-a',
      platform: 'android',
      appVersion: '1.0.0',
    );
    final otherTokens = _MemoryTokens();
    final otherClient =
        DioEcoIqApiClient(environment: env, tokenProvider: otherTokens);
    final second = await otherClient.login(
      username: username,
      password: password,
      deviceId: 'e2e-multi-b',
      deviceName: 'ci-b',
      platform: 'ios',
      appVersion: '1.0.0',
    );
    expect(second.sessionId, isNot(first.sessionId),
        reason: 'two devices must get distinct sessions');

    tokens.seed(first);
    otherTokens.seed(second);

    // Verified from the first device's own session list, which is an
    // authenticated call and confirms the server really tracks both.
    final before = await client.listSessions();
    expect(before.map((s) => s.id), containsAll([first.sessionId, second.sessionId]));

    await client.logoutAll();

    late EcoIqApiException error;
    try {
      await otherClient.getMe();
      fail('logout-all must revoke sessions other than the calling one');
    } on EcoIqApiException catch (e) {
      error = e;
    }
    expect(error.statusCode, 401);
  });
}
