import 'package:flutter/material.dart';

import '../../core/api/api_exception.dart';
import '../../design/tokens.dart';

/// PART 20 of the app spec: clear, honest empty/error states — never
/// substitute a missing result for a "clean/safe" status.
class EcoIqErrorView extends StatelessWidget {
  const EcoIqErrorView({super.key, required this.error, this.onRetry});
  final EcoIqApiException error;
  final VoidCallback? onRetry;

  String get _message => switch (error.type) {
        EcoIqApiErrorType.network =>
          'No internet connection. Check your network and try again.',
        EcoIqApiErrorType.unauthorized =>
          'Your session has expired. Please sign in again.',
        EcoIqApiErrorType.forbiddenSubscriptionRequired =>
          'Your current plan doesn\'t include this. Visit ecoiq.uk/products for options.',
        EcoIqApiErrorType.notFound => 'Not found.',
        EcoIqApiErrorType.server =>
          'EcoIQ is temporarily unavailable. Please try again shortly.',
        EcoIqApiErrorType.unknown => 'Something went wrong.',
      };

  IconData get _icon => switch (error.type) {
        EcoIqApiErrorType.network => Icons.wifi_off_outlined,
        EcoIqApiErrorType.unauthorized => Icons.lock_outline,
        EcoIqApiErrorType.forbiddenSubscriptionRequired =>
          Icons.workspace_premium_outlined,
        EcoIqApiErrorType.notFound => Icons.search_off_outlined,
        EcoIqApiErrorType.server => Icons.cloud_off_outlined,
        EcoIqApiErrorType.unknown => Icons.error_outline,
      };

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(EcoIqSpace.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(_icon,
                size: 40,
                color: Theme.of(context)
                    .colorScheme
                    .onSurface
                    .withValues(alpha: 0.6)),
            const SizedBox(height: EcoIqSpace.md),
            Text(_message,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium),
            if (onRetry != null) ...[
              const SizedBox(height: EcoIqSpace.md),
              OutlinedButton(
                  onPressed: onRetry, child: const Text('Try again')),
            ],
          ],
        ),
      ),
    );
  }
}

class EcoIqEmptyView extends StatelessWidget {
  const EcoIqEmptyView(
      {super.key, required this.message, this.icon = Icons.inbox_outlined});
  final String message;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(EcoIqSpace.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon,
                size: 40,
                color: Theme.of(context)
                    .colorScheme
                    .onSurface
                    .withValues(alpha: 0.4)),
            const SizedBox(height: EcoIqSpace.md),
            Text(message,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium),
          ],
        ),
      ),
    );
  }
}

/// PART 7: "EcoIQ provides environmental stewardship and sustainability-
/// risk intelligence. It does not provide investment advice, financial
/// recommendations or predictions of investment performance." Verbatim
/// text — reused everywhere a stock/investment-relevance surface renders.
class NotInvestmentAdviceBanner extends StatelessWidget {
  const NotInvestmentAdviceBanner({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(EcoIqSpace.sm),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(EcoIqRadius.sm),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.info_outline,
              size: 16,
              color: Theme.of(context)
                  .colorScheme
                  .onSurface
                  .withValues(alpha: 0.6)),
          const SizedBox(width: EcoIqSpace.sm),
          Expanded(
            child: Text(
              'EcoIQ provides environmental stewardship and sustainability-risk '
              'intelligence. It does not provide investment advice, financial '
              'recommendations or predictions of investment performance.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
        ],
      ),
    );
  }
}
