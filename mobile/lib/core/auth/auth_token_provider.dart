import 'auth_models.dart';

/// Breaks the circular dependency between the API client (needs the
/// current token, and needs to trigger+persist a refresh on 401) and
/// AuthService (needs the API client to make the actual login/refresh HTTP
/// calls). AuthService implements this; DioEcoIqApiClient only depends on
/// the interface.
abstract class AuthTokenProvider {
  String? get currentAccessToken;
  String? get currentRefreshToken;

  /// Called by the API client after it successfully refreshed on a 401.
  /// Must persist the new pair and update in-memory state.
  Future<void> handleTokensRefreshed(TokenPair pair);

  /// Called when refresh itself fails (refresh token expired/revoked) —
  /// must clear stored tokens and flip auth state to unauthenticated so
  /// the app routes back to the login screen.
  Future<void> handleRefreshFailed();
}
