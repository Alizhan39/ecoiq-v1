import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_exception.dart';
import '../../data/models/company.dart';
import '../../design/tokens.dart';
import '../../shared/widgets/state_views.dart';
import '../../shared/widgets/status_chip.dart';
import '../../state/providers.dart';

/// PART 6 of the app spec. Reuses api.serializers.CompanyDetailSerializer
/// exactly as the backend returns it -- no client-side scoring, no
/// client-side inference of ethical status. Stock price/market data (PART
/// 7) is intentionally NOT shown here: CompanyDetailSerializer doesn't
/// return it and fabricating a price field client-side would violate the
/// "server is the source of truth" rule -- wiring the real stock-profile
/// endpoint into this screen is a Phase 2 item (see final report).
class CompanyProfileScreen extends ConsumerWidget {
  const CompanyProfileScreen({super.key, required this.slug});
  final String slug;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profileFuture = ref.watch(_companyProfileProvider(slug));

    return Scaffold(
      appBar: AppBar(title: const Text('Company')),
      body: profileFuture.when(
        data: (profile) => _CompanyProfileBody(profile: profile),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => EcoIqErrorView(
          error: err is EcoIqApiException
              ? err
              : const EcoIqApiException(
                  EcoIqApiErrorType.unknown, 'Failed to load company.'),
          onRetry: () => ref.invalidate(_companyProfileProvider(slug)),
        ),
      ),
    );
  }
}

final _companyProfileProvider =
    FutureProvider.family<CompanyProfileData, String>(
  (ref, slug) => ref.watch(companyRepositoryProvider).getProfile(slug),
);

class _CompanyProfileBody extends StatelessWidget {
  const _CompanyProfileBody({required this.profile});
  final CompanyProfileData profile;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(EcoIqSpace.lg),
      children: [
        // ── Header ──
        Row(
          children: [
            CircleAvatar(
              radius: 28,
              backgroundColor: EcoIqColors.accent.withValues(alpha: 0.12),
              child: Text(
                profile.name.isNotEmpty ? profile.name[0].toUpperCase() : '?',
                style:
                    const TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
              ),
            ),
            const SizedBox(width: EcoIqSpace.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(profile.name,
                      style: Theme.of(context).textTheme.titleLarge),
                  Text(
                    [profile.sector, profile.country]
                        .where((s) => s.isNotEmpty)
                        .join(' · '),
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
            IconButton(
              tooltip: 'Add to watchlist',
              icon: const Icon(Icons.bookmark_add_outlined),
              onPressed: () => ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                    content:
                        Text('Watchlists are coming in a future release.')),
              ),
            ),
          ],
        ),
        if (!profile.isPublic)
          const Padding(
            padding: EdgeInsets.only(top: EcoIqSpace.sm),
            child: EcoIqStatusChip(
                label: 'Private company', tone: EcoIqStatusTone.neutral),
          ),
        const SizedBox(height: EcoIqSpace.lg),

        // ── Key EcoIQ overview ──
        Card(
          child: Padding(
            padding: const EdgeInsets.all(EcoIqSpace.lg),
            child: Row(
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('EcoIQ Score',
                        style: Theme.of(context).textTheme.labelSmall),
                    Text(
                      profile.ecoiqScore.toStringAsFixed(0),
                      style: Theme.of(context)
                          .textTheme
                          .headlineMedium
                          ?.copyWith(color: EcoIqColors.accent),
                    ),
                  ],
                ),
                const Spacer(),
                EcoIqStatusChip(
                  label: profile.verified ? 'Verified' : 'Unverified',
                  tone: profile.verified
                      ? EcoIqStatusTone.positive
                      : EcoIqStatusTone.caution,
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: EcoIqSpace.lg),

        // ── What this company does ──
        if (profile.description.isNotEmpty) ...[
          Text('What this company does',
              style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: EcoIqSpace.sm),
          Text(profile.description),
          const SizedBox(height: EcoIqSpace.lg),
        ],

        // ── Ethical Impact & Conflict Exposure ──
        Text('Ethical impact & conflict exposure',
            style: Theme.of(context).textTheme.titleSmall),
        const SizedBox(height: EcoIqSpace.sm),
        if (profile.harmSignals.isEmpty)
          const EcoIqEmptyView(
            message: 'No exposure signals recorded for this company yet.',
            icon: Icons.shield_outlined,
          )
        else
          ...profile.harmSignals
              .map((signal) => _HarmSignalTile(signal: signal)),
        const SizedBox(height: EcoIqSpace.lg),

        Card(
          child: Padding(
            padding: const EdgeInsets.all(EcoIqSpace.md),
            child: Text(
              'Stock profile, evidence detail, ethical screening, and Islamic '
              'screening are available on ecoiq.uk today and are planned for '
              'this screen in a future release.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
        ),
      ],
    );
  }
}

class _HarmSignalTile extends StatelessWidget {
  const _HarmSignalTile({required this.signal});
  final HarmSignal signal;

  (EcoIqStatusTone, String) get _display => switch (signal.status) {
        'verified_direct' => (
            EcoIqStatusTone.negative,
            'Verified — direct involvement'
          ),
        'verified_indirect' => (
            EcoIqStatusTone.caution,
            'Verified — indirect involvement'
          ),
        'under_investigation' => (
            EcoIqStatusTone.caution,
            'Official investigation'
          ),
        'disputed' => (EcoIqStatusTone.info, 'Disputed claim'),
        'allegation_only' => (EcoIqStatusTone.info, 'Allegation only'),
        'historical' => (EcoIqStatusTone.neutral, 'Historical exposure'),
        'insufficient_evidence' => (
            EcoIqStatusTone.neutral,
            'Insufficient evidence'
          ),
        _ => (EcoIqStatusTone.neutral, signal.status),
      };

  @override
  Widget build(BuildContext context) {
    final (tone, statusLabel) = _display;
    return Card(
      margin: const EdgeInsets.only(bottom: EcoIqSpace.sm),
      child: ListTile(
        title: Text(signal.label),
        subtitle: EcoIqStatusChip(label: statusLabel, tone: tone),
      ),
    );
  }
}
