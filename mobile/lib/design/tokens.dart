/// EcoIQ design tokens — ported 1:1 from `frontend/app/src/design/tokens.ts`,
/// the single source of truth for the web "Visual Intelligence" dark
/// institutional design system. Keeping the same hex values here means the
/// app and the website read as the same brand, not two different products.
///
/// Aesthetic target: a premium, evidence-led sustainability-intelligence
/// platform — deep near-black greens, restrained luminous accents. NOT a
/// gamified trading app: no flashing prices, no red/green "buy signal"
/// visuals (see EcoIqColors.statusNeutral and the "no color-only status"
/// rule enforced by EcoIqStatusChip in shared/widgets).
library;

import 'package:flutter/widgets.dart';

class EcoIqColors {
  EcoIqColors._();

  // Background scale — deepest to surface (dark theme).
  static const bg900 = Color(0xFF03100C);
  static const bg800 = Color(0xFF06140F);
  static const bg700 = Color(0xFF0A1C16);
  static const surface = Color(0xFF0C211A);
  static const surfaceRaised = Color(0xFF0F2A21);

  // Accents.
  static const accent = Color(0xFF00E89A);
  static const accentDim = Color(0xFF0BBF82);
  static const accentGlow = Color(0x2E00E89A); // ~18% alpha
  static const gold = Color(0xFFE8C46A);

  // Signal colors — used for data visualisation ONLY, never as the sole
  // carrier of an ethical-risk status (PART 17: "must never be conveyed
  // only by red, amber or green colours" — pair with EcoIqStatusChip's
  // icon + text label).
  static const warn = Color(0xFFF2A65A);
  static const danger = Color(0xFFEF6F6F);
  static const info = Color(0xFF5AB0F2);

  // Text (dark theme).
  static const ink = Color(0xFFE7F3EE);
  static const inkStrong = Color(0xFFFFFFFF);
  static const muted = Color(0xFF8FA9A0);
  static const faint = Color(0xFF5F746C);

  // Lines.
  static const border = Color(0x0FFFFFFF); // 6% white
  static const borderAccent = Color(0x2900E89A); // ~16% accent

  // Light theme — same accent/brand colors, lightened surfaces. Not part of
  // tokens.ts (which is dark-only); derived to satisfy the app spec's
  // "light theme" + "Windows dark and light themes" requirement while
  // keeping one visual identity.
  static const lightBg = Color(0xFFF6FAF8);
  static const lightSurface = Color(0xFFFFFFFF);
  static const lightSurfaceRaised = Color(0xFFEFF6F2);
  static const lightInk = Color(0xFF0B1F17);
  static const lightMuted = Color(0xFF4B6158);
  static const lightBorder = Color(0x140B1F17);
}

class EcoIqRadius {
  EcoIqRadius._();
  static const sm = 10.0;
  static const md = 14.0;
  static const lg = 18.0;
  static const xl = 24.0;
  static const pill = 999.0;
}

class EcoIqSpace {
  EcoIqSpace._();
  static const xs = 6.0;
  static const sm = 10.0;
  static const md = 16.0;
  static const lg = 24.0;
  static const xl = 32.0;
  static const xxl = 48.0;
}

class EcoIqDuration {
  EcoIqDuration._();
  static const fast = Duration(milliseconds: 180);
  static const base = Duration(milliseconds: 420);
  static const slow = Duration(milliseconds: 700);
}

/// EcoIQ-wide breakpoints for adaptive layout (bottom nav vs sidebar — see
/// shared/widgets/adaptive_scaffold.dart and PART 3/16 of the app spec).
class EcoIqBreakpoints {
  EcoIqBreakpoints._();

  /// Below this: mobile layout (bottom nav, single column).
  static const compact = 600.0;

  /// Below this: tablet layout (rail nav, may still be touch-primary).
  static const medium = 1024.0;

  /// At/above this: desktop layout (sidebar nav, multi-column, keyboard-first).
  static const expanded = 1024.0;
}
