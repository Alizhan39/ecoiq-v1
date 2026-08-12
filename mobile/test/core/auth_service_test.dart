import 'package:ecoiq_app/core/api/api_exception.dart';
import 'package:ecoiq_app/core/api/ecoiq_api_client.dart';
import 'package:ecoiq_app/core/auth/auth_models.dart';
import 'package:ecoiq_app/core/auth/auth_service.dart';
import 'package:ecoiq_app/core/storage/secure_token_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';

class _MockApiClient extends Mock implements EcoIqApiClient {}

class _MockStorage extends Mock implements SecureTokenStorage {}

const _tokenPair = TokenPair(
  accessToken: 'access-1',
  accessTokenExpiresIn: 900,
  refreshToken: 'refresh-1',
  sessionId: 42,
);

void main() {
  late _MockApiClient apiClient;
  late _MockStorage storage;
  late AuthService authService;

  setUp(() {
    apiClient = _MockApiClient();
    storage = _MockStorage();
    when(() => storage.saveTokens(accessToken: any(named: 'accessToken'), refreshToken: any(named: 'refreshToken')))
        .thenAnswer((_) async {});
    when(() => storage.clearTokens()).thenAnswer((_) async {});

    authService = AuthService(storage: storage);
    authService.apiClient = apiClient;
  });

  group('AuthService.login', () {
    test('transitions to authenticated and persists tokens on success', () async {
      when(() => apiClient.login(
            username: any(named: 'username'),
            password: any(named: 'password'),
            deviceId: any(named: 'deviceId'),
            deviceName: any(named: 'deviceName'),
            platform: any(named: 'platform'),
            appVersion: any(named: 'appVersion'),
          )).thenAnswer((_) async => _tokenPair);

      await authService.login(
        username: 'ali',
        password: 'pw',
        deviceId: 'd1',
        deviceName: 'Test',
        platform: 'ios',
        appVersion: '1.0.0',
      );

      expect(authService.state, AuthStatus.authenticated);
      expect(authService.currentAccessToken, 'access-1');
      verify(() => storage.saveTokens(accessToken: 'access-1', refreshToken: 'refresh-1')).called(1);
    });

    test('propagates the exception and stays unauthenticated on bad credentials', () async {
      when(() => apiClient.login(
            username: any(named: 'username'),
            password: any(named: 'password'),
            deviceId: any(named: 'deviceId'),
            deviceName: any(named: 'deviceName'),
            platform: any(named: 'platform'),
            appVersion: any(named: 'appVersion'),
          )).thenThrow(const EcoIqApiException(EcoIqApiErrorType.unauthorized, 'Invalid credentials'));

      await expectLater(
        authService.login(
          username: 'ali', password: 'wrong', deviceId: 'd1', deviceName: 'T', platform: 'ios', appVersion: '1',
        ),
        throwsA(isA<EcoIqApiException>()),
      );
      expect(authService.state, isNot(AuthStatus.authenticated));
    });
  });

  group('AuthService.restoreSession', () {
    test('unauthenticated when no refresh token is stored', () async {
      when(() => storage.readRefreshToken()).thenAnswer((_) async => null);
      await authService.restoreSession();
      expect(authService.state, AuthStatus.unauthenticated);
    });

    test('authenticated after a successful eager refresh', () async {
      when(() => storage.readRefreshToken()).thenAnswer((_) async => 'stored-refresh');
      when(() => apiClient.refresh('stored-refresh')).thenAnswer((_) async => _tokenPair);

      await authService.restoreSession();

      expect(authService.state, AuthStatus.authenticated);
      expect(authService.currentAccessToken, 'access-1');
    });

    test('unauthenticated and clears storage when the stored refresh token is dead', () async {
      when(() => storage.readRefreshToken()).thenAnswer((_) async => 'stale-refresh');
      when(() => apiClient.refresh('stale-refresh'))
          .thenThrow(const EcoIqApiException(EcoIqApiErrorType.unauthorized, 'expired'));

      await authService.restoreSession();

      expect(authService.state, AuthStatus.unauthenticated);
      verify(() => storage.clearTokens()).called(1);
    });
  });

  group('AuthService logout', () {
    test('clears local state even when the server call fails (offline logout)', () async {
      when(() => storage.readRefreshToken()).thenAnswer((_) async => 'r1');
      when(() => apiClient.refresh('r1')).thenAnswer((_) async => _tokenPair);
      await authService.restoreSession();

      when(() => apiClient.logout()).thenThrow(const EcoIqApiException(EcoIqApiErrorType.network, 'offline'));

      await authService.logout();

      expect(authService.state, AuthStatus.unauthenticated);
      expect(authService.currentAccessToken, isNull);
      verify(() => storage.clearTokens()).called(1);
    });
  });

  group('AuthTokenProvider contract (used by DioEcoIqApiClient interceptor)', () {
    test('handleTokensRefreshed persists and updates in-memory tokens', () async {
      await authService.handleTokensRefreshed(_tokenPair);
      expect(authService.currentAccessToken, 'access-1');
      expect(authService.currentRefreshToken, 'refresh-1');
    });

    test('handleRefreshFailed clears tokens and flips to unauthenticated', () async {
      await authService.handleTokensRefreshed(_tokenPair);
      await authService.handleRefreshFailed();
      expect(authService.currentAccessToken, isNull);
      expect(authService.state, AuthStatus.unauthenticated);
    });
  });
}
