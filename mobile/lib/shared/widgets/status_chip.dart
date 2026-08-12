import 'package:flutter/material.dart';

import '../../design/tokens.dart';

/// PART 17 accessibility requirement: "Ethical-risk categories must never
/// be conveyed only by red, amber or green colours." Every status chip in
/// the app pairs a color with an ICON and a TEXT LABEL, so removing color
/// (grayscale, color-blind, or a screen reader) never loses meaning.
enum EcoIqStatusTone { positive, caution, negative, neutral, info }

class EcoIqStatusChip extends StatelessWidget {
  const EcoIqStatusChip({super.key, required this.label, required this.tone, this.semanticsLabel});

  final String label;
  final EcoIqStatusTone tone;

  /// Override for screen readers when `label` alone is ambiguous out of
  /// context (e.g. "Passed" -> "Ethical screening: Passed").
  final String? semanticsLabel;

  (Color, IconData) get _visual => switch (tone) {
        EcoIqStatusTone.positive => (EcoIqColors.accent, Icons.check_circle_outline),
        EcoIqStatusTone.caution => (EcoIqColors.warn, Icons.error_outline),
        EcoIqStatusTone.negative => (EcoIqColors.danger, Icons.cancel_outlined),
        EcoIqStatusTone.neutral => (EcoIqColors.muted, Icons.remove_circle_outline),
        EcoIqStatusTone.info => (EcoIqColors.info, Icons.info_outline),
      };

  @override
  Widget build(BuildContext context) {
    final (color, icon) = _visual;
    return Semantics(
      label: semanticsLabel ?? label,
      child: ExcludeSemantics(
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: EcoIqSpace.sm, vertical: 4),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.14),
            borderRadius: BorderRadius.circular(EcoIqRadius.pill),
            border: Border.all(color: color.withValues(alpha: 0.4)),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 14, color: color),
              const SizedBox(width: 4),
              Text(label, style: TextStyle(color: color, fontSize: 12, fontWeight: FontWeight.w600)),
            ],
          ),
        ),
      ),
    );
  }
}
