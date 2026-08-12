/// Mirrors the token response shared by POST /api/v1/auth/login/ and
/// POST /api/v1/auth/refresh/ (see mobile_auth/views.py:_token_response).
class TokenPair {
  const TokenPair({
    required this.accessToken,
    required this.accessTokenExpiresIn,
    required this.refreshToken,
    required this.sessionId,
  });

  final String accessToken;
  final int accessTokenExpiresIn; // seconds
  final String refreshToken;
  final int sessionId;

  factory TokenPair.fromJson(Map<String, dynamic> json) => TokenPair(
        accessToken: json['access_token'] as String,
        accessTokenExpiresIn: json['access_token_expires_in'] as int,
        refreshToken: json['refresh_token'] as String,
        sessionId: json['session_id'] as int,
      );
}

/// Mirrors one row of GET /api/v1/auth/sessions/ — "logout from this device" UI.
class DeviceSessionInfo {
  const DeviceSessionInfo({
    required this.id,
    required this.deviceName,
    required this.platform,
    required this.lastUsedAt,
    required this.isCurrent,
  });

  final int id;
  final String deviceName;
  final String platform;
  final DateTime lastUsedAt;
  final bool isCurrent;

  factory DeviceSessionInfo.fromJson(Map<String, dynamic> json) =>
      DeviceSessionInfo(
        id: json['id'] as int,
        deviceName: (json['device_name'] as String?)?.isNotEmpty == true
            ? json['device_name'] as String
            : json['platform'] as String,
        platform: json['platform'] as String,
        lastUsedAt: DateTime.parse(json['last_used_at'] as String),
        isCurrent: json['is_current'] as bool? ?? false,
      );
}

enum AuthStatus { unknown, authenticated, unauthenticated }
