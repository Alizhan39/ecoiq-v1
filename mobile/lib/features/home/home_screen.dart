import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_exception.dart';
import '../../design/tokens.dart';
import '../../navigation/router.dart';
import '../../shared/widgets/state_views.dart';
import '../../state/providers.dart';

/// PART 4 of the app spec describes a rich dashboard (portfolio exposure
/// summaries, watchlist alerts, "N companies received new controversy
/// evidence" cards). Those all depend on the portfolio/watchlist/alerts
/// backend, which has no JSON API yet (see docs/MOBILE-API-ADDITIONS.md).
/// Rather than fabricate example cards with invented numbers, this Phase 1
/// home screen shows what's REALLY available today: the signed-in user,
/// their entitlement summary, and recently-viewed companies -- with an
/// honest "coming soon" section for the rest, matching the same
/// "prepared, not operational" discipline used throughout this backend.
class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final meAsync = ref.watch(meProvider);
    final recentlyViewed = ref.watch(companyRepositoryProvider).recentlyViewed();

    return Scaffold(
      appBar: AppBar(
        title: const Text('EcoIQ'),
        actions: [
          IconButton(
            tooltip: 'Sign out',
            icon: const Icon(Icons.logout),
            onPressed: () => ref.read(authServiceProvider.notifier).logout(),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(meProvider),
        child: ListView(
          padding: const EdgeInsets.all(EcoIqSpace.lg),
          children: [
            meAsync.when(
              data: (user) => Card(
                child: Padding(
                  padding: const EdgeInsets.all(EcoIqSpace.lg),
                  child: Row(
                    children: [
                      CircleAvatar(
                        backgroundColor: EcoIqColors.accent.withValues(alpha: 0.15),
                        child: Text(user.username.isNotEmpty ? user.username[0].toUpperCase() : '?'),
                      ),
                      const SizedBox(width: EcoIqSpace.md),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(user.username, style: Theme.of(context).textTheme.titleMedium),
                            Text(
                              user.plan?.name ?? 'Free',
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              loading: () => const Padding(
                padding: EdgeInsets.symmetric(vertical: EcoIqSpace.xl),
                child: Center(child: CircularProgressIndicator()),
              ),
              error: (err, _) => EcoIqErrorView(
                error: err is EcoIqApiException
                    ? err
                    : const EcoIqApiException(EcoIqApiErrorType.unknown, 'Could not load your account.'),
                onRetry: () => ref.invalidate(meProvider),
              ),
            ),
            const SizedBox(height: EcoIqSpace.lg),
            FilledButton.icon(
              onPressed: () => context.go(AppRoutes.search),
              icon: const Icon(Icons.search),
              label: const Text('Search a company'),
            ),
            const SizedBox(height: EcoIqSpace.xl),
            Text('Recently viewed', style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: EcoIqSpace.sm),
            if (recentlyViewed.isEmpty)
              const EcoIqEmptyView(message: 'Companies you view will appear here.', icon: Icons.history)
            else
              ...recentlyViewed.map(
                (entry) => Card(
                  child: ListTile(
                    title: Text(entry.$2),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => context.go(AppRoutes.companyPath(entry.$1)),
                  ),
                ),
              ),
            const SizedBox(height: EcoIqSpace.xl),
            Text('Coming soon', style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: EcoIqSpace.sm),
            const Card(
              child: Padding(
                padding: EdgeInsets.all(EcoIqSpace.lg),
                child: Text(
                  'Portfolio exposure summaries, watchlist alerts, and '
                  'evidence-change notifications will appear here once the '
                  'portfolio/watchlist/alerts API is available (see the '
                  'project\'s Phase 2 plan). Nothing shown on this screen is '
                  'invented placeholder data.',
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
