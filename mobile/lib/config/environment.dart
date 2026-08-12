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

  static Environment fromDartDefine() {
    const raw = String.fromEnvironment('ECOIQ_ENV', defaultValue: 'mock');
    switch (raw) {
      case 'dev':
        return _dev;
      case 'staging':
        return _staging;
      case 'production':
        return _production;
      default:
        return _mock;
    }
  }

  bool get isMock => name == EcoIqEnvName.mock;
}
