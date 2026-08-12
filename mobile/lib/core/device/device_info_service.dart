import 'dart:io' show Platform;
import 'dart:math';

import 'package:package_info_plus/package_info_plus.dart';

import '../storage/secure_token_storage.dart';

/// Resolves the stable device_id sent on login (generated once, cached),
/// plus a human-readable device_name, the platform string the backend
/// expects ('ios' | 'android' | 'windows' | 'other' — see
/// mobile_auth/models.py:PLATFORM_CHOICES), and the real app version (sent
/// on login, compared against app-config's min_supported_version).
class DeviceInfoService {
  DeviceInfoService({required SecureTokenStorage storage}) : _storage = storage;

  final SecureTokenStorage _storage;

  Future<String> getAppVersion() async {
    final info = await PackageInfo.fromPlatform();
    return info.version;
  }

  Future<String> getOrCreateDeviceId() async {
    final existing = await _storage.readDeviceId();
    if (existing != null) return existing;
    final generated = _generateUuidV4();
    await _storage.saveDeviceId(generated);
    return generated;
  }

  String get platform {
    if (Platform.isIOS) return 'ios';
    if (Platform.isAndroid) return 'android';
    if (Platform.isWindows) return 'windows';
    return 'other';
  }

  String get deviceName {
    // Flutter has no zero-dependency cross-platform "device model name" API
    // without a plugin (device_info_plus); kept intentionally simple for
    // Phase 1 -- a generic, still-useful label rather than pulling in
    // another dependency for a "nice to have" string.
    if (Platform.isIOS) return 'iPhone/iPad';
    if (Platform.isAndroid) return 'Android device';
    if (Platform.isWindows) return 'Windows PC';
    return 'Device';
  }

  static String _generateUuidV4() {
    final rand = Random.secure();
    final bytes = List<int>.generate(16, (_) => rand.nextInt(256));
    bytes[6] = (bytes[6] & 0x0F) | 0x40; // version 4
    bytes[8] = (bytes[8] & 0x3F) | 0x80; // variant 10
    String hex(int start, int end) =>
        bytes.sublist(start, end).map((b) => b.toRadixString(16).padLeft(2, '0')).join();
    return '${hex(0, 4)}-${hex(4, 6)}-${hex(6, 8)}-${hex(8, 10)}-${hex(10, 16)}';
  }
}
