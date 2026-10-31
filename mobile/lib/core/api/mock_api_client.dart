import '../../data/models/app_config.dart';
import '../../data/models/evidence.dart';
import '../../data/models/company.dart';
import '../../data/models/user.dart';
import '../auth/auth_models.dart';
import 'api_exception.dart';
import 'ecoiq_api_client.dart';

/// Offline development client — no backend required. Used when
/// Environment.isMock is true (the default for `flutter run` with no
/// --dart-define). Lets the functional shell (login → home → search →
/// company profile) be demoed/reviewed without a running Django server.
/// Data here is clearly synthetic and mirrors the SHAPE of the real API
/// responses, never real company findings.
class MockEcoIqApiClient implements EcoIqApiClient {
  static const _mockCompanies = [
    CompanyProfileData(
      slug: 'mock-orion-energy',
      name: 'Orion Renewable Energy',
      sector: 'Energy',
      country: 'United Kingdom',
      city: 'London',
      website: 'https://example.com',
      logoUrl: null,
      description:
          'Illustrative mock company — utility-scale solar and wind development.',
      isPublic: true,
      verified: true,
      score: EvidenceScore(
          value: 78, status: ScoreStatus.published, coveragePercent: 91),
      rank: 12,
      harmSignals: [],
    ),
    CompanyProfileData(
      slug: 'mock-atlas-defence',
      name: 'Atlas Defence Systems',
      sector: 'Aerospace & Defence',
      country: 'United States',
      city: 'Arlington',
      website: 'https://example.com',
      logoUrl: null,
      description:
          'Illustrative mock company — used to demo defence-involvement labelling.',
      isPublic: true,
      verified: true,
      score: EvidenceScore(
          value: 41, status: ScoreStatus.published, coveragePercent: 74),
      rank: 340,
      harmSignals: [
        HarmSignal(
            id: 'defence-1',
            label: 'Defence contracts',
            status: 'verified_direct',
            penalty: 15),
        HarmSignal(
            id: 'hr-1',
            label: 'Human-rights allegation',
            status: 'allegation_only',
            penalty: 5),
      ],
    ),
    CompanyProfileData(
      slug: 'mock-verdant-foods',
      name: 'Verdant Foods Group',
      sector: 'Consumer Staples',
      country: 'Kazakhstan',
      city: 'Almaty',
      website: 'https://example.com',
      logoUrl: null,
      description:
          'Illustrative mock company — used to demo insufficient-evidence states.',
      isPublic: true,
      verified: false,
      // Was 55/rank 890. This fixture exists to demo insufficient
      // evidence, so it now exercises the real pending path: null score,
      // null rank, evidence-pending UI. Without one such fixture the
      // mock environment could never reach that branch.
      score: EvidenceScore(
          value: null,
          status: ScoreStatus.insufficientEvidence,
          coveragePercent: 0),
      rank: null,
      harmSignals: [
        HarmSignal(
            id: 'ev-1',
            label: 'Evidence under review',
            status: 'insufficient_evidence',
            penalty: 0),
      ],
    ),
  ];

  Future<void> _latency() => Future.delayed(const Duration(milliseconds: 350));

  @override
  Future<TokenPair> login({
    required String username,
    required String password,
    required String deviceId,
    required String deviceName,
    required String platform,
    required String appVersion,
  }) async {
    await _latency();
    if (username.trim().isEmpty || password.isEmpty) {
      throw const EcoIqApiException(
          EcoIqApiErrorType.unauthorized, 'Invalid username or password.');
    }
    return const TokenPair(
      accessToken: 'mock-access-token',
      accessTokenExpiresIn: 900,
      refreshToken: 'mock-refresh-token',
      sessionId: 1,
    );
  }

  @override
  Future<TokenPair> refresh(String refreshToken) async {
    await _latency();
    return const TokenPair(
      accessToken: 'mock-access-token-2',
      accessTokenExpiresIn: 900,
      refreshToken: 'mock-refresh-token-2',
      sessionId: 1,
    );
  }

  @override
  Future<void> logout() => _latency();

  @override
  Future<void> logoutAll() => _latency();

  @override
  Future<List<DeviceSessionInfo>> listSessions() async {
    await _latency();
    return [
      DeviceSessionInfo(
        id: 1,
        deviceName: 'This device (mock)',
        platform: 'mock',
        lastUsedAt: DateTime.now(),
        isCurrent: true,
      ),
    ];
  }

  @override
  Future<void> revokeSession(int sessionId) => _latency();

  @override
  Future<EcoIqUser> getMe() async {
    await _latency();
    return const EcoIqUser(
      id: 1,
      username: 'demo',
      email: 'demo@example.com',
      isStaff: false,
      plan: null,
      entitlements: {
        'company_profiles_basic': true,
        'company_profiles_advanced': false,
        'portfolio_intelligence': true,
        'ethical_screening': false,
        'islamic_screening': false,
        'evidence_access': false,
        'report_download': false,
        'dataset_export': false,
      },
    );
  }

  @override
  Future<EcoIqAppConfig> getAppConfig() async {
    await _latency();
    return const EcoIqAppConfig(
      minSupportedVersion: '1.0.0',
      latestVersion: '1.0.0',
      maintenanceMode: false,
      forceUpdate: false,
      supportContact: 'support@ecoiq.uk',
    );
  }

  @override
  Future<List<CompanySummary>> searchCompanies(String query) async {
    await _latency();
    final q = query.trim().toLowerCase();
    return _mockCompanies
        .where((c) =>
            q.isEmpty ||
            c.name.toLowerCase().contains(q) ||
            c.sector.toLowerCase().contains(q))
        .map((c) => CompanySummary(
              slug: c.slug,
              name: c.name,
              sector: c.sector,
              country: c.country,
              score: c.score,
              rank: c.rank,
              isPublic: c.isPublic,
              verified: c.verified,
            ))
        .toList();
  }

  @override
  Future<CompanyProfileData> getCompanyProfile(String slug) async {
    await _latency();
    final match = _mockCompanies.where((c) => c.slug == slug);
    if (match.isEmpty) {
      throw const EcoIqApiException(
          EcoIqApiErrorType.notFound, 'Company not found.');
    }
    return match.first;
  }
}
