import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config/environment.dart';
import '../core/analytics/analytics_service.dart';
import '../core/api/dio_api_client.dart';
import '../core/api/ecoiq_api_client.dart';
import '../core/api/mock_api_client.dart';
import '../core/auth/auth_models.dart';
import '../core/auth/auth_service.dart';
import '../core/device/device_info_service.dart';
import '../core/notifications/notification_service.dart';
import '../core/storage/secure_token_storage.dart';
import '../data/models/app_config.dart';
import '../data/repositories/company_repository.dart';

final environmentProvider =
    Provider<Environment>((ref) => Environment.fromDartDefine());

final secureTokenStorageProvider =
    Provider<SecureTokenStorage>((ref) => SecureTokenStorage());

final deviceInfoServiceProvider = Provider<DeviceInfoService>(
  (ref) => DeviceInfoService(storage: ref.watch(secureTokenStorageProvider)),
);

/// Overridden in main.dart with the resolved instance before runApp() —
/// SharedPreferences.getInstance() is async and must complete before the
/// widget tree needs it (see main.dart).
final sharedPreferencesProvider = Provider<SharedPreferences>(
  (ref) => throw UnimplementedError(
      'sharedPreferencesProvider must be overridden in main.dart'),
);

/// Two-phase wiring: AuthService and EcoIqApiClient each need a reference
/// to the other (the client needs a token provider for its 401-refresh
/// interceptor; AuthService needs the client to make the actual login/
/// refresh HTTP calls). AuthService is constructed first with `apiClient`
/// unset, the client is constructed with `authService` as its
/// AuthTokenProvider, then attached back onto authService -- all
/// synchronously within this provider callback, so nothing ever observes
/// authService.apiClient in an unset state.
final authServiceProvider =
    StateNotifierProvider<AuthService, AuthStatus>((ref) {
  final storage = ref.watch(secureTokenStorageProvider);
  final env = ref.watch(environmentProvider);

  final authService = AuthService(storage: storage);
  final EcoIqApiClient client = env.isMock
      ? MockEcoIqApiClient()
      : DioEcoIqApiClient(environment: env, tokenProvider: authService);
  authService.apiClient = client;
  return authService;
});

final apiClientProvider = Provider<EcoIqApiClient>(
    (ref) => ref.watch(authServiceProvider.notifier).apiClient);

final companyRepositoryProvider = Provider<CompanyRepository>(
  (ref) => CompanyRepository(
    apiClient: ref.watch(apiClientProvider),
    prefs: ref.watch(sharedPreferencesProvider),
  ),
);

final analyticsServiceProvider =
    Provider<AnalyticsService>((ref) => NoOpAnalyticsService());

final notificationServiceProvider =
    Provider<NotificationService>((ref) => NoOpNotificationService());

/// App-config is fetched once at startup and refreshed on demand (e.g.
/// pull-to-refresh on the maintenance/force-update screen) — never cached
/// forever, since it's the backend's way of pushing urgent flags.
final appConfigProvider = FutureProvider<EcoIqAppConfig>((ref) async {
  final client = ref.watch(apiClientProvider);
  try {
    return await client.getAppConfig();
  } catch (_) {
    return EcoIqAppConfig.unknown;
  }
});

final meProvider = FutureProvider((ref) {
  ref.watch(authServiceProvider); // re-fetch whenever auth status changes
  final client = ref.watch(apiClientProvider);
  return client.getMe();
});
