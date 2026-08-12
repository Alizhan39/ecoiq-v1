import '../../data/models/app_config.dart';
import '../../data/models/company.dart';
import '../../data/models/user.dart';
import '../auth/auth_models.dart';

/// The API client abstraction. Every screen/repository depends on THIS
/// interface, never on Dio or on mock data directly -- that's what lets
/// Environment.mock swap in MockEcoIqApiClient with zero changes anywhere
/// else (PART 1 of the app spec: "API client" as its own architectural
/// layer; PART 29: "company search using staging or mocked API").
abstract class EcoIqApiClient {
  // ── Auth (unauthenticated calls -- mobile_auth app) ──
  Future<TokenPair> login({
    required String username,
    required String password,
    required String deviceId,
    required String deviceName,
    required String platform,
    required String appVersion,
  });

  Future<TokenPair> refresh(String refreshToken);
  Future<void> logout();
  Future<void> logoutAll();
  Future<List<DeviceSessionInfo>> listSessions();
  Future<void> revokeSession(int sessionId);

  // ── App shell ──
  Future<EcoIqUser> getMe();
  Future<EcoIqAppConfig> getAppConfig();

  // ── Companies ──
  Future<List<CompanySummary>> searchCompanies(String query);
  Future<CompanyProfileData> getCompanyProfile(String slug);
}
