import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/auth/auth_models.dart';
import '../features/auth/login_screen.dart';
import '../features/company/company_profile_screen.dart';
import '../features/home/home_screen.dart';
import '../features/search/search_screen.dart';
import '../state/providers.dart';
import 'app_shell.dart';

/// Deep-link route paths. Every ecoiq://... link maps 1:1 onto a path
/// here, and EVERY route below sits behind the same `redirect` auth guard
/// -- PART 19 of the app spec: "Every link must enforce authentication and
/// permissions server-side." The redirect only decides whether to show the
/// screen at all; the screen's own data calls still go through the normal
/// server-side entitlement checks (has_entitlement / RequiresFeature) --
/// this guard is a UX convenience (don't show a blank authenticated screen
/// to a logged-out user), never the actual access-control boundary.
class AppRoutes {
  AppRoutes._();
  static const login = '/login';
  static const home = '/home';
  static const search = '/search';
  static const company = '/company/:slug'; // ecoiq://company/<slug>
  static String companyPath(String slug) => '/company/$slug';
}

/// Bridges a Riverpod StateNotifier's changes into a ChangeNotifier so
/// GoRouter's `refreshListenable` re-evaluates `redirect` whenever auth
/// status flips (login/logout) — without pulling in a separate
/// riverpod-go_router integration package for this one hook.
class _AuthRefreshNotifier extends ChangeNotifier {
  _AuthRefreshNotifier(ProviderContainer container) {
    _sub = container.listen(authServiceProvider, (_, __) => notifyListeners());
  }
  late final ProviderSubscription<AuthStatus> _sub;

  @override
  void dispose() {
    _sub.close();
    super.dispose();
  }
}

GoRouter buildRouter(ProviderContainer container) {
  return GoRouter(
    initialLocation: AppRoutes.home,
    refreshListenable: _AuthRefreshNotifier(container),
    redirect: (context, state) {
      final status = container.read(authServiceProvider);
      final goingToLogin = state.matchedLocation == AppRoutes.login;

      if (status == AuthStatus.unknown) return null; // still restoring session -- don't redirect yet
      if (status == AuthStatus.unauthenticated && !goingToLogin) return AppRoutes.login;
      if (status == AuthStatus.authenticated && goingToLogin) return AppRoutes.home;
      return null;
    },
    routes: [
      GoRoute(path: AppRoutes.login, builder: (context, state) => const LoginScreen()),
      ShellRoute(
        builder: (context, state, child) => AppShell(currentPath: state.matchedLocation, child: child),
        routes: [
          GoRoute(path: AppRoutes.home, builder: (context, state) => const HomeScreen()),
          GoRoute(path: AppRoutes.search, builder: (context, state) => const SearchScreen()),
          GoRoute(
            path: AppRoutes.company,
            builder: (context, state) => CompanyProfileScreen(slug: state.pathParameters['slug']!),
          ),
        ],
      ),
    ],
  );
}
