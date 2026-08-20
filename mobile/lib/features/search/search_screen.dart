import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_exception.dart';
import '../../data/models/company.dart';
import '../../data/models/evidence.dart';
import '../../design/tokens.dart';
import '../../navigation/router.dart';
import '../../shared/widgets/state_views.dart';
import '../../shared/widgets/status_chip.dart';
import '../../state/providers.dart';

/// PART 5 of the app spec. Filters (environmental exposure, defence
/// involvement, Islamic screening, evidence confidence, etc.) are
/// server-supported on CompanyListView's query params but not yet on the
/// lightweight /search/ endpoint this screen uses -- wiring a full filter
/// UI is listed as a Phase 2 item in the final report rather than built
/// against a placeholder here.
class SearchScreen extends ConsumerStatefulWidget {
  const SearchScreen({super.key});

  @override
  ConsumerState<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends ConsumerState<SearchScreen> {
  final _controller = TextEditingController();
  Timer? _debounce;

  List<CompanySummary>? _results;
  bool _loading = false;
  EcoIqApiException? _error;

  @override
  void dispose() {
    _debounce?.cancel();
    _controller.dispose();
    super.dispose();
  }

  void _onChanged(String query) {
    _debounce?.cancel();
    if (query.trim().isEmpty) {
      setState(() {
        _results = null;
        _error = null;
      });
      return;
    }
    _debounce =
        Timer(const Duration(milliseconds: 350), () => _runSearch(query));
  }

  Future<void> _runSearch(String query) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final repo = ref.read(companyRepositoryProvider);
      final results = await repo.search(query);
      if (!mounted) return;
      setState(() => _results = results);
    } on EcoIqApiException catch (e) {
      if (!mounted) return;
      setState(() => _error = e);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: TextField(
          controller: _controller,
          autofocus: true,
          textInputAction: TextInputAction.search,
          onChanged: _onChanged,
          decoration: const InputDecoration(
            border: InputBorder.none,
            hintText: 'Search company, ticker, sector, country…',
            prefixIcon: Icon(Icons.search),
          ),
        ),
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_error != null) {
      return EcoIqErrorView(
          error: _error!, onRetry: () => _runSearch(_controller.text));
    }
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_results == null) {
      return const EcoIqEmptyView(
          message: 'Start typing to search EcoIQ\'s company coverage.');
    }
    if (_results!.isEmpty) {
      return const EcoIqEmptyView(
          message: 'No companies matched your search.',
          icon: Icons.search_off_outlined);
    }
    return ListView.separated(
      padding: const EdgeInsets.symmetric(vertical: EcoIqSpace.sm),
      itemCount: _results!.length,
      separatorBuilder: (_, __) => const Divider(height: 1),
      itemBuilder: (context, index) =>
          _CompanyResultTile(company: _results![index]),
    );
  }
}

class _CompanyResultTile extends StatelessWidget {
  const _CompanyResultTile({required this.company});
  final CompanySummary company;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      title: Text(company.name),
      subtitle: Text([company.sector, company.country]
          .where((s) => s.isNotEmpty)
          .join(' · ')),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Unknown is not poor performance. When there is no publishable
          // score the chip is NEUTRAL and says so — never a red "negative"
          // tone, which would read as a bad result rather than an absent one.
          if (company.score.canDisplay)
            EcoIqStatusChip(
              label: company.score.value!.toStringAsFixed(0),
              tone: company.score.value! >= 70
                  ? EcoIqStatusTone.positive
                  : company.score.value! >= 40
                      ? EcoIqStatusTone.caution
                      : EcoIqStatusTone.negative,
              semanticsLabel:
                  'EcoIQ score ${company.score.value!.toStringAsFixed(0)} out of 100',
            )
          else
            const EcoIqStatusChip(
              label: EvidenceScore.pendingLabelShort,
              tone: EcoIqStatusTone.neutral,
              semanticsLabel:
                  'EcoIQ has not published a score for this organisation. '
                  'Evidence assessment pending.',
            ),
          IconButton(
            tooltip: 'Add to watchlist',
            icon: const Icon(Icons.bookmark_add_outlined),
            onPressed: () => ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                  content: Text('Watchlists are coming in a future release.')),
            ),
          ),
        ],
      ),
      onTap: () => context.go(AppRoutes.companyPath(company.slug)),
    );
  }
}
