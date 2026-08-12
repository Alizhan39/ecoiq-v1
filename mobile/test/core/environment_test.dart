import 'package:ecoiq_app/config/environment.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Environment', () {
    test('defaults to mock when no --dart-define is passed', () {
      final env = Environment.fromDartDefine();
      expect(env.name, EcoIqEnvName.mock);
      expect(env.isMock, isTrue);
    });

    test('mock environment never points at a real host', () {
      final env = Environment.fromDartDefine();
      expect(env.apiBaseUrl, startsWith('mock://'));
    });
  });
}
