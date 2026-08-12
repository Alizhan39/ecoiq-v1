import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Wraps flutter_secure_storage — iOS Keychain, Android Keystore (via
/// EncryptedSharedPreferences), Windows Credential Locker. This is the
/// ONLY place access/refresh tokens are ever written to disk; nothing else
/// in the app should touch FlutterSecureStorage directly (PART 12: "Do not
/// store access tokens in ordinary preferences, plaintext files or
/// insecure local storage").
class SecureTokenStorage {
  SecureTokenStorage({FlutterSecureStorage? storage})
      : _storage = storage ??
            const FlutterSecureStorage(
              aOptions: AndroidOptions(encryptedSharedPreferences: true),
              // iOS default (kSecAttrAccessibleAfterFirstUnlock) is
              // appropriate here: tokens must survive background app
              // refresh (for push-triggered API calls) but never before
              // the device's first unlock after boot.
            );

  final FlutterSecureStorage _storage;

  static const _kAccessToken = 'ecoiq.access_token';
  static const _kRefreshToken = 'ecoiq.refresh_token';
  static const _kDeviceId = 'ecoiq.device_id';

  Future<void> saveTokens({required String accessToken, required String refreshToken}) async {
    await _storage.write(key: _kAccessToken, value: accessToken);
    await _storage.write(key: _kRefreshToken, value: refreshToken);
  }

  Future<String?> readAccessToken() => _storage.read(key: _kAccessToken);
  Future<String?> readRefreshToken() => _storage.read(key: _kRefreshToken);

  Future<void> clearTokens() async {
    await _storage.delete(key: _kAccessToken);
    await _storage.delete(key: _kRefreshToken);
  }

  /// The device_id is stable but not secret — still kept alongside the
  /// tokens for simplicity, generated once on first launch (see AuthService).
  Future<String?> readDeviceId() => _storage.read(key: _kDeviceId);
  Future<void> saveDeviceId(String id) => _storage.write(key: _kDeviceId, value: id);
}
