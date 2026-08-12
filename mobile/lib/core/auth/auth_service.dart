import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_exception.dart';
import '../api/ecoiq_api_client.dart';
import '../storage/secure_token_storage.dart';
import 'auth_models.dart';
import 'auth_token_provider.dart';

/// Owns the login/refresh/logout lifecycle and the in-memory + persisted
/// token state. Implements AuthTokenProvider so DioEcoIqApiClient's 401
/// interceptor can read the current token and hand back a freshly-rotated
/// one without either class needing to fully construct the other first
/// (see state/providers.dart for the two-phase wiring).
class AuthService extends StateNotifier<AuthStatus>
    implements AuthTokenProvider {
  AuthService({required SecureTokenStorage storage})
      : _storage = storage,
        super(AuthStatus.unknown);

  final SecureTokenStorage _storage;

  /// Set once, immediately after construction, by state/providers.dart —
  /// see that file's comment for why this can't be a constructor param.
  late EcoIqApiClient apiClient;

  String? _accessToken;
  String? _refreshToken;

  @override
  String? get currentAccessToken => _accessToken;
  @override
  String? get currentRefreshToken => _refreshToken;

  /// Call once at app startup (before showing any authenticated screen).
  /// If a refresh token is on disk, eagerly rotates it to confirm the
  /// session is still valid rather than waiting for the first API call to
  /// discover it's dead ("secure session renewal").
  Future<void> restoreSession() async {
    final storedRefresh = await _storage.readRefreshToken();
    if (storedRefresh == null) {
      state = AuthStatus.unauthenticated;
      return;
    }
    try {
      final pair = await apiClient.refresh(storedRefresh);
      await _persist(pair);
      state = AuthStatus.authenticated;
    } on EcoIqApiException {
      await _storage.clearTokens();
      state = AuthStatus.unauthenticated;
    }
  }

  Future<void> login({
    required String username,
    required String password,
    required String deviceId,
    required String deviceName,
    required String platform,
    required String appVersion,
  }) async {
    final pair = await apiClient.login(
      username: username,
      password: password,
      deviceId: deviceId,
      deviceName: deviceName,
      platform: platform,
      appVersion: appVersion,
    );
    await _persist(pair);
    state = AuthStatus.authenticated;
  }

  Future<void> logout() async {
    try {
      await apiClient.logout();
    } on EcoIqApiException {
      // Best-effort server-side revoke -- still clear local state even if
      // this call failed (offline logout must always succeed locally).
    }
    await _clear();
  }

  Future<void> logoutAllDevices() async {
    try {
      await apiClient.logoutAll();
    } on EcoIqApiException {
      // ignore, see logout()
    }
    await _clear();
  }

  Future<void> _persist(TokenPair pair) async {
    _accessToken = pair.accessToken;
    _refreshToken = pair.refreshToken;
    await _storage.saveTokens(
        accessToken: pair.accessToken, refreshToken: pair.refreshToken);
  }

  Future<void> _clear() async {
    _accessToken = null;
    _refreshToken = null;
    await _storage.clearTokens();
    state = AuthStatus.unauthenticated;
  }

  @override
  Future<void> handleTokensRefreshed(TokenPair pair) => _persist(pair);

  @override
  Future<void> handleRefreshFailed() => _clear();
}
