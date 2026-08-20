/// Environment configuration — dev / staging / production, selected at
/// build time via `--dart-define=ECOIQ_ENV=staging` (see mobile/README.md
/// for exact commands). Never hard-code an API base URL anywhere else in
/// the app; always go through Environment.current.apiBaseUrl.
enum EcoIqEnvName { dev, staging, production, mock }

class Environment {
  const Environment._({
    required this.name,
    required this.apiBaseUrl,
    required this.enableLogging,
  });

  final EcoIqEnvName name;
  final String apiBaseUrl;
  final bool enableLogging;

  static const _dev = Environment._(
    name: EcoIqEnvName.dev,
    apiBaseUrl: 'http://localhost:8731/api/v1',
    enableLogging: true,
  );

  static const _staging = Environment._(
    name: EcoIqEnvName.staging,
    apiBaseUrl: 'https://staging.ecoiq.uk/api/v1',
    enableLogging: true,
  );

  static const _production = Environment._(
    name: EcoIqEnvName.production,
    apiBaseUrl: 'https://ecoiq.uk/api/v1',
    enableLogging: false,
  );

  /// No backend at all — the functional shell's default for `flutter run`
  /// without a Django server, per the app spec's "company search using
  /// staging or mocked API". See core/api/mock_api_client.dart.
  static const _mock = Environment._(
    name: EcoIqEnvName.mock,
    apiBaseUrl: 'mock://ecoiq',
    enableLogging: true,
  );

  /// Resolve an environment by name.
  ///
  /// Public so tests can assert the non-mock environments. Without it the dev,
  /// staging and production configurations are unreachable from a test —
  /// fromDartDefine() returns mock under `flutter test` — and the v1/v2 split
  /// they encode would go unverified.
  static Environment fromName(EcoIqEnvName name) => switch (name) {
        EcoIqEnvName.dev => _dev,
        EcoIqEnvName.staging => _staging,
        EcoIqEnvName.production => _production,
        EcoIqEnvName.mock => _mock,
      };

  static Environment fromDartDefine() {
    const raw = String.fromEnvironment('ECOIQ_ENV', defaultValue: 'mock');
    switch (raw) {
      case 'dev':
        return fromName(EcoIqEnvName.dev);
      case 'staging':
        return fromName(EcoIqEnvName.staging);
      case 'production':
        return fromName(EcoIqEnvName.production);
      default:
        return fromName(EcoIqEnvName.mock);
    }
  }

  bool get isMock => name == EcoIqEnvName.mock;

  /// Base URL for the canonical, evidence-aware API.
  ///
  /// Derived from [apiBaseUrl] rather than declared separately so the two can
  /// never point at different hosts — every environment gets its own v2 for
  /// free, including dev and staging.
  ///
  /// Only company data has moved to v2. Auth, /me and app-config stay on v1
  /// because v2 does not define them and they carry no score, which is why the
  /// cutover is per-endpoint rather than a change of [apiBaseUrl].
  String get apiV2BaseUrl =>
      apiBaseUrl.replaceFirst(RegExp(r'/v1/?$'), '/v2');
}
