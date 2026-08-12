import 'package:flutter/material.dart';

import '../../design/tokens.dart';

class EcoIqNavDestination {
  const EcoIqNavDestination(
      {required this.label,
      required this.icon,
      required this.selectedIcon,
      required this.path});
  final String label;
  final IconData icon;
  final IconData selectedIcon;
  final String path;
}

/// PART 3 / PART 16 of the app spec: bottom nav on mobile, LEFT SIDEBAR on
/// Windows desktop -- "Do not simply stretch the mobile interface across
/// the Windows screen." Switches by available WIDTH (not Platform.isX) so
/// a resized Windows window, a tablet, or a large phone in landscape all
/// get the layout that actually fits, rather than a layout hard-tied to
/// which OS compiled the binary.
class AdaptiveScaffold extends StatelessWidget {
  const AdaptiveScaffold({
    super.key,
    required this.destinations,
    required this.selectedIndex,
    required this.onDestinationSelected,
    required this.body,
    this.floatingActionButton,
  });

  final List<EcoIqNavDestination> destinations;
  final int selectedIndex;
  final ValueChanged<int> onDestinationSelected;
  final Widget body;
  final Widget? floatingActionButton;

  @override
  Widget build(BuildContext context) {
    final width = MediaQuery.sizeOf(context).width;

    if (width < EcoIqBreakpoints.compact) {
      return _MobileScaffold(
        destinations: destinations,
        selectedIndex: selectedIndex,
        onDestinationSelected: onDestinationSelected,
        body: body,
        floatingActionButton: floatingActionButton,
      );
    }

    return _DesktopScaffold(
      destinations: destinations,
      selectedIndex: selectedIndex,
      onDestinationSelected: onDestinationSelected,
      body: body,
      extended: width >= EcoIqBreakpoints.expanded,
    );
  }
}

class _MobileScaffold extends StatelessWidget {
  const _MobileScaffold({
    required this.destinations,
    required this.selectedIndex,
    required this.onDestinationSelected,
    required this.body,
    required this.floatingActionButton,
  });

  final List<EcoIqNavDestination> destinations;
  final int selectedIndex;
  final ValueChanged<int> onDestinationSelected;
  final Widget body;
  final Widget? floatingActionButton;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(child: body), // iOS Safe Area (PART 16)
      floatingActionButton: floatingActionButton,
      bottomNavigationBar: NavigationBar(
        selectedIndex: selectedIndex,
        onDestinationSelected: onDestinationSelected,
        destinations: [
          for (final d in destinations)
            NavigationDestination(
                icon: Icon(d.icon),
                selectedIcon: Icon(d.selectedIcon),
                label: d.label),
        ],
      ),
    );
  }
}

class _DesktopScaffold extends StatelessWidget {
  const _DesktopScaffold({
    required this.destinations,
    required this.selectedIndex,
    required this.onDestinationSelected,
    required this.body,
    required this.extended,
  });

  final List<EcoIqNavDestination> destinations;
  final int selectedIndex;
  final ValueChanged<int> onDestinationSelected;
  final Widget body;
  final bool extended;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Row(
        children: [
          // NavigationRail supports keyboard focus traversal and hover
          // states out of the box (PART 16: "hover and focus states,
          // keyboard shortcuts") — extended (labelled) once the window is
          // wide enough for a true sidebar, compact/icon-only otherwise.
          NavigationRail(
            selectedIndex: selectedIndex,
            onDestinationSelected: onDestinationSelected,
            extended: extended,
            minExtendedWidth: 220,
            labelType: extended
                ? NavigationRailLabelType.none
                : NavigationRailLabelType.all,
            leading: const Padding(
              padding: EdgeInsets.symmetric(vertical: EcoIqSpace.md),
              child: FlutterLogo(size: 28), // placeholder for the EcoIQ mark
            ),
            destinations: [
              for (final d in destinations)
                NavigationRailDestination(
                  icon: Icon(d.icon),
                  selectedIcon: Icon(d.selectedIcon),
                  label: Text(d.label),
                ),
            ],
          ),
          const VerticalDivider(width: 1),
          Expanded(child: body),
        ],
      ),
    );
  }
}
