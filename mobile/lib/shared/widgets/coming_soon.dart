import 'package:flutter/material.dart';

/// Honest placeholder for nav destinations whose backend doesn't exist yet
/// (Watchlist, Portfolio — see docs/MOBILE-API-ADDITIONS.md). Never shows
/// fabricated data; never silently hides the tab either.
class ComingSoonScreen extends StatelessWidget {
  const ComingSoonScreen({super.key, required this.title});
  final String title;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.construction_outlined, size: 40),
              const SizedBox(height: 16),
              Text('$title is coming in a future release',
                  style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              Text(
                'This screen is not yet connected to live data.',
                style: Theme.of(context).textTheme.bodySmall,
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
