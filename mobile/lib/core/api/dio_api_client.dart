import 'package:dio/dio.dart';

import '../../config/environment.dart';
import '../../data/models/app_config.dart';
import '../../data/models/company.dart';
import '../../data/models/user.dart';
import '../auth/auth_models.dart';
import '../auth/auth_token_provider.dart';
import 'api_exception.dart';
import 'ecoiq_api_client.dart';

/// Real backend client. Talks to Django's /api/v1/ exactly as documented in
/// docs/MOBILE-API-ADDITIONS.md. Business logic (scoring, screening,
/// entitlements, publication status) stays server-side -- this class only
/// serializes requests and deserializes responses, per PART 1 of the app
/// spec ("Do not duplicate scoring, compliance, subscription or
/// publication logic inside the app").
class DioEcoIqApiClient implements EcoIqApiClient {
  DioEcoIqApiClient({required Environment environment, required AuthTokenProvider tokenProvider})
      : _tokenProvider = tokenProvider,
        _dio = Dio(BaseOptions(
          baseUrl: environment.apiBaseUrl,
          connectTimeout: const Duration(seconds: 15),
          receiveTimeout: const Duration(seconds: 15),
        )),
        // A second, un-intercepted Dio for the refresh call itself --
        // using the main _dio here would recurse into the 401 handler.
        _rawDio = Dio(BaseOptions(baseUrl: environment.apiBaseUrl)) {
    _dio.interceptors.add(_AuthInterceptor(tokenProvider: _tokenProvider, rawDio: _rawDio, dio: _dio));
    if (environment.enableLogging) {
      _dio.interceptors.add(LogInterceptor(requestBody: false, responseBody: false));
    }
  }

  final Dio _dio;
  final Dio _rawDio;
  final AuthTokenProvider _tokenProvider;

  EcoIqApiException _wrap(Object error) {
    if (error is DioException) {
      final status = error.response?.statusCode;
      final detail = (error.response?.data is Map)
          ? ((error.response!.data as Map)['detail']?.toString() ?? error.message ?? 'Request failed')
          : (error.message ?? 'Request failed');
      switch (status) {
        case 401:
          return EcoIqApiException(EcoIqApiErrorType.unauthorized, detail, statusCode: status);
        case 403:
          return EcoIqApiException(EcoIqApiErrorType.forbiddenSubscriptionRequired, detail, statusCode: status);
        case 404:
          return EcoIqApiException(EcoIqApiErrorType.notFound, detail, statusCode: status);
        case null:
          return EcoIqApiException(EcoIqApiErrorType.network, detail);
        default:
          if (status != null && status >= 500) {
            return EcoIqApiException(EcoIqApiErrorType.server, detail, statusCode: status);
          }
          return EcoIqApiException(EcoIqApiErrorType.unknown, detail, statusCode: status);
      }
    }
    return EcoIqApiException(EcoIqApiErrorType.unknown, error.toString());
  }

  @override
  Future<TokenPair> login({
    required String username,
    required String password,
    required String deviceId,
    required String deviceName,
    required String platform,
    required String appVersion,
  }) async {
    try {
      final resp = await _rawDio.post('/auth/login/', data: {
        'username': username,
        'password': password,
        'device_id': deviceId,
        'device_name': deviceName,
        'platform': platform,
        'app_version': appVersion,
      });
      return TokenPair.fromJson(resp.data as Map<String, dynamic>);
    } catch (e) {
      throw _wrap(e);
    }
  }

  @override
  Future<TokenPair> refresh(String refreshToken) async {
    try {
      final resp = await _rawDio.post('/auth/refresh/', data: {'refresh_token': refreshToken});
      return TokenPair.fromJson(resp.data as Map<String, dynamic>);
    } catch (e) {
      throw _wrap(e);
    }
  }

  @override
  Future<void> logout() async {
    try {
      await _dio.post('/auth/logout/');
    } catch (e) {
      throw _wrap(e);
    }
  }

  @override
  Future<void> logoutAll() async {
    try {
      await _dio.post('/auth/logout-all/');
    } catch (e) {
      throw _wrap(e);
    }
  }

  @override
  Future<List<DeviceSessionInfo>> listSessions() async {
    try {
      final resp = await _dio.get('/auth/sessions/');
      final sessions = (resp.data as Map<String, dynamic>)['sessions'] as List;
      return sessions.map((e) => DeviceSessionInfo.fromJson(e as Map<String, dynamic>)).toList();
    } catch (e) {
      throw _wrap(e);
    }
  }

  @override
  Future<void> revokeSession(int sessionId) async {
    try {
      await _dio.post('/auth/sessions/$sessionId/revoke/');
    } catch (e) {
      throw _wrap(e);
    }
  }

  @override
  Future<EcoIqUser> getMe() async {
    try {
      final resp = await _dio.get('/me/');
      return EcoIqUser.fromJson(resp.data as Map<String, dynamic>);
    } catch (e) {
      throw _wrap(e);
    }
  }

  @override
  Future<EcoIqAppConfig> getAppConfig() async {
    try {
      final resp = await _rawDio.get('/app-config/');
      return EcoIqAppConfig.fromJson(resp.data as Map<String, dynamic>);
    } catch (e) {
      throw _wrap(e);
    }
  }

  @override
  Future<List<CompanySummary>> searchCompanies(String query) async {
    try {
      final resp = await _dio.get('/search/', queryParameters: {'q': query});
      final results = (resp.data as Map<String, dynamic>)['results'] as List;
      return results.map((e) => CompanySummary.fromJson(e as Map<String, dynamic>)).toList();
    } catch (e) {
      throw _wrap(e);
    }
  }

  @override
  Future<CompanyProfileData> getCompanyProfile(String slug) async {
    try {
      final resp = await _dio.get('/companies/$slug/');
      return CompanyProfileData.fromJson(resp.data as Map<String, dynamic>);
    } catch (e) {
      throw _wrap(e);
    }
  }
}

/// Injects `Authorization: Bearer <access_token>` on every request, and on
/// a 401 attempts exactly one refresh-and-retry before giving up (avoids
/// infinite retry loops if the refresh token is also dead).
class _AuthInterceptor extends QueuedInterceptor {
  _AuthInterceptor({required this.tokenProvider, required this.rawDio, required this.dio});

  final AuthTokenProvider tokenProvider;
  final Dio rawDio;
  final Dio dio;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final token = tokenProvider.currentAccessToken;
    if (token != null) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) async {
    final isAuthEndpoint = err.requestOptions.path.startsWith('/auth/');
    if (err.response?.statusCode != 401 || isAuthEndpoint || err.requestOptions.extra['retried'] == true) {
      handler.next(err);
      return;
    }

    final refreshToken = tokenProvider.currentRefreshToken;
    if (refreshToken == null) {
      await tokenProvider.handleRefreshFailed();
      handler.next(err);
      return;
    }

    try {
      final resp = await rawDio.post('/auth/refresh/', data: {'refresh_token': refreshToken});
      final pair = TokenPair.fromJson(resp.data as Map<String, dynamic>);
      await tokenProvider.handleTokensRefreshed(pair);

      final retryOptions = err.requestOptions;
      retryOptions.extra['retried'] = true;
      retryOptions.headers['Authorization'] = 'Bearer ${pair.accessToken}';
      final retryResp = await dio.fetch(retryOptions);
      handler.resolve(retryResp);
    } catch (_) {
      await tokenProvider.handleRefreshFailed();
      handler.next(err);
    }
  }
}
