import 'package:ecoiq_app/design/tokens.dart';
import 'package:ecoiq_app/shared/widgets/adaptive_scaffold.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  const destinations = [
    EcoIqNavDestination(
        label: 'Home',
        icon: Icons.home_outlined,
        selectedIcon: Icons.home,
        path: '/home'),
    EcoIqNavDestination(
        label: 'Search',
        icon: Icons.search_outlined,
        selectedIcon: Icons.search,
        path: '/search'),
  ];

  Widget wrap(Size size) => MaterialApp(
        home: MediaQuery(
          data: MediaQueryData(size: size),
          child: AdaptiveScaffold(
            destinations: destinations,
            selectedIndex: 0,
            onDestinationSelected: (_) {},
            body: const SizedBox.shrink(),
          ),
        ),
      );

  testWidgets('shows bottom navigation below the compact breakpoint (mobile)',
      (tester) async {
    await tester.pumpWidget(wrap(const Size(390, 844))); // iPhone-sized
    expect(find.byType(NavigationBar), findsOneWidget);
    expect(find.byType(NavigationRail), findsNothing);
  });

  testWidgets(
      'shows a sidebar rail at/above the expanded breakpoint (Windows desktop)',
      (tester) async {
    await tester.pumpWidget(wrap(const Size(1280, 800)));
    expect(find.byType(NavigationRail), findsOneWidget);
    expect(find.byType(NavigationBar), findsNothing);
  });

  testWidgets(
      'sidebar rail is extended (labelled) once wide enough, not just icon-only',
      (tester) async {
    await tester.pumpWidget(wrap(Size(EcoIqBreakpoints.expanded + 100, 900)));
    final rail = tester.widget<NavigationRail>(find.byType(NavigationRail));
    expect(rail.extended, isTrue);
  });
}
