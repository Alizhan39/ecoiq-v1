import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'core/auth/auth_models.dart';
import 'design/theme.dart';
import 'state/providers.dart';

class EcoIqApp extends ConsumerWidget {
  const EcoIqApp({super.key, required this.router});
  final GoRouter router;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authStatus = ref.watch(authServiceProvider);

    // While restoreSession() (main.dart) is still deciding whether a
    // persisted refresh token is valid, show a neutral splash rather than
    // flashing the login screen then immediately redirecting to home.
    if (authStatus == AuthStatus.unknown) {
      return MaterialApp(
        theme: EcoIqTheme.light,
        darkTheme: EcoIqTheme.dark,
        home: const Scaffold(body: Center(child: CircularProgressIndicator())),
      );
    }

    return MaterialApp.router(
      title: 'EcoIQ',
      debugShowCheckedModeBanner: false,
      theme: EcoIqTheme.light,
      darkTheme: EcoIqTheme.dark,
      themeMode: ThemeMode.system,
      routerConfig: router,
    );
  }
}
