import 'package:ecoiq_app/core/device/device_info_service.dart';
import 'package:ecoiq_app/core/storage/secure_token_storage.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('device identity is compatible with Django mobile_auth choices', () {
    final service = DeviceInfoService(storage: SecureTokenStorage());
    expect(service.platform, isIn(['ios', 'android', 'windows', 'other']));
    expect(service.deviceName, isNotEmpty);

    if (kIsWeb) {
      // Calling dart:io Platform.is* on the web raises UnsupportedError.
      expect(service.platform, 'other');
      expect(service.deviceName, 'Web browser');
    }
  });
}
