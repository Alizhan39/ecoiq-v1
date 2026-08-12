import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'app.dart';
import 'navigation/router.dart';
import 'state/providers.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final prefs = await SharedPreferences.getInstance();

  final container = ProviderContainer(
    overrides: [sharedPreferencesProvider.overrideWithValue(prefs)],
  );

  // Attempt to restore a persisted session BEFORE the first frame renders
  // the router's redirect decision -- see AuthService.restoreSession() and
  // EcoIqApp's AuthStatus.unknown splash branch.
  await container.read(authServiceProvider.notifier).restoreSession();

  final router = buildRouter(container);

  runApp(
    UncontrolledProviderScope(
      container: container,
      child: EcoIqApp(router: router),
    ),
  );
}
