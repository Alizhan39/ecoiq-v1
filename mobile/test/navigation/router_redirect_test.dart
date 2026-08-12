import 'package:ecoiq_app/core/api/mock_api_client.dart';
import 'package:ecoiq_app/core/auth/auth_models.dart';
import 'package:ecoiq_app/core/auth/auth_service.dart';
import 'package:ecoiq_app/core/storage/secure_token_storage.dart';
import 'package:ecoiq_app/features/auth/login_screen.dart';
import 'package:ecoiq_app/features/home/home_screen.dart';
import 'package:ecoiq_app/navigation/router.dart';
import 'package:ecoiq_app/state/providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// A test double that never touches secure storage or the network -- its
/// AuthStatus is set directly, apiClient is the same in-memory mock used
/// for offline dev (see MockEcoIqApiClient), and restoreSession() is a
/// no-op so no platform channel call happens during the test.
class _FakeAuthService extends AuthService {
  _FakeAuthService(AuthStatus initial) : super(storage: SecureTokenStorage()) {
    apiClient = MockEcoIqApiClient();
    state = initial;
  }

  @override
  Future<void> restoreSession() async {}
}

void main() {
  // PART 19 of the app spec: "Every link must enforce authentication and
  // permissions server-side" -- these tests cover the CLIENT-SIDE UX guard
  // (don't show an authenticated screen to a logged-out user); the actual
  // access-control boundary is the Django backend (see mobile_auth/tests.py
  // and api/tests.py, which cover that server-side).
  group('router auth redirect', () {
    testWidgets('unauthenticated user hitting a protected route is redirected to /login', (tester) async {
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();

      final container = ProviderContainer(overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
        authServiceProvider.overrideWith((ref) => _FakeAuthService(AuthStatus.unauthenticated)),
      ]);
      addTearDown(container.dispose);

      final router = buildRouter(container);
      await tester.pumpWidget(UncontrolledProviderScope(
        container: container,
        child: MaterialApp.router(routerConfig: router),
      ));
      await tester.pumpAndSettle();

      expect(find.byType(LoginScreen), findsOneWidget);
      expect(find.byType(HomeScreen), findsNothing);
    });

    testWidgets('authenticated user hitting /login is redirected to home', (tester) async {
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();

      final container = ProviderContainer(overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
        authServiceProvider.overrideWith((ref) => _FakeAuthService(AuthStatus.authenticated)),
      ]);
      addTearDown(container.dispose);

      final router = buildRouter(container);
      router.go(AppRoutes.login);
      await tester.pumpWidget(UncontrolledProviderScope(
        container: container,
        child: MaterialApp.router(routerConfig: router),
      ));
      await tester.pumpAndSettle();

      expect(find.byType(HomeScreen), findsOneWidget);
      expect(find.byType(LoginScreen), findsNothing);
    });
  });
}
