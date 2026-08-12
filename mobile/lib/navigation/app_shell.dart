import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../shared/widgets/adaptive_scaffold.dart';
import '../shared/widgets/coming_soon.dart';
import 'router.dart';

/// PART 3 of the app spec: Home / Discover / Watchlist / Portfolio / Profile.
/// Watchlist and Portfolio have no backend JSON API yet (investor_portfolio
/// is server-rendered HTML only today — see docs/MOBILE-API-ADDITIONS.md)
/// and Profile (account settings) wasn't part of this pass's bounded
/// functional shell, so those three tabs are wired to a clearly-labelled
/// "coming soon" placeholder rather than either hiding the tab (which
/// would misrepresent the planned nav structure) or faking data.
class AppShell extends StatelessWidget {
  const AppShell({super.key, required this.currentPath, required this.child});

  final String currentPath;
  final Widget child;

  static const _destinations = [
    EcoIqNavDestination(
        label: 'Home',
        icon: Icons.home_outlined,
        selectedIcon: Icons.home,
        path: AppRoutes.home),
    EcoIqNavDestination(
        label: 'Discover',
        icon: Icons.search_outlined,
        selectedIcon: Icons.search,
        path: AppRoutes.search),
    EcoIqNavDestination(
        label: 'Watchlist',
        icon: Icons.visibility_outlined,
        selectedIcon: Icons.visibility,
        path: '/watchlist'),
    EcoIqNavDestination(
        label: 'Portfolio',
        icon: Icons.pie_chart_outline,
        selectedIcon: Icons.pie_chart,
        path: '/portfolio'),
    EcoIqNavDestination(
        label: 'Profile',
        icon: Icons.person_outline,
        selectedIcon: Icons.person,
        path: '/profile'),
  ];

  int get _selectedIndex {
    final index = _destinations
        .indexWhere((d) => currentPath.startsWith(d.path) && d.path != '/');
    return index == -1 ? 0 : index;
  }

  @override
  Widget build(BuildContext context) {
    return AdaptiveScaffold(
      destinations: _destinations,
      selectedIndex: _selectedIndex,
      onDestinationSelected: (index) {
        final path = _destinations[index].path;
        if (path == AppRoutes.home || path == AppRoutes.search) {
          context.go(path);
        } else {
          Navigator.of(context).push(MaterialPageRoute<void>(
            builder: (_) => ComingSoonScreen(title: _destinations[index].label),
          ));
        }
      },
      body: child,
    );
  }
}
