import 'package:flutter/material.dart';

import 'tokens.dart';

/// EcoIQ ThemeData — dark is the primary/default surface (matches the web
/// "Visual Intelligence" institutional system); light is a first-class
/// alternative, not an afterthought (Windows explicitly needs both).
class EcoIqTheme {
  EcoIqTheme._();

  static ThemeData get dark => _build(
        brightness: Brightness.dark,
        bg: EcoIqColors.bg900,
        surface: EcoIqColors.surface,
        surfaceRaised: EcoIqColors.surfaceRaised,
        ink: EcoIqColors.ink,
        muted: EcoIqColors.muted,
        border: EcoIqColors.border,
      );

  static ThemeData get light => _build(
        brightness: Brightness.light,
        bg: EcoIqColors.lightBg,
        surface: EcoIqColors.lightSurface,
        surfaceRaised: EcoIqColors.lightSurfaceRaised,
        ink: EcoIqColors.lightInk,
        muted: EcoIqColors.lightMuted,
        border: EcoIqColors.lightBorder,
      );

  static ThemeData _build({
    required Brightness brightness,
    required Color bg,
    required Color surface,
    required Color surfaceRaised,
    required Color ink,
    required Color muted,
    required Color border,
  }) {
    final colorScheme = ColorScheme(
      brightness: brightness,
      primary: EcoIqColors.accent,
      onPrimary: EcoIqColors.bg900,
      secondary: EcoIqColors.gold,
      onSecondary: EcoIqColors.bg900,
      error: EcoIqColors.danger,
      onError: Colors.white,
      surface: surface,
      onSurface: ink,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: bg,
      canvasColor: bg,
      dividerColor: border,
      splashFactory: InkRipple.splashFactory,
      visualDensity: VisualDensity.standard,
      // Reduced-motion respect (PART 17 accessibility): platform default
      // page transitions honour MediaQuery.disableAnimations already; no
      // custom PageTransitionsTheme override needed on top of that.
      appBarTheme: AppBarTheme(
        backgroundColor: bg,
        foregroundColor: ink,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: ink,
          fontSize: 18,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.2,
        ),
      ),
      cardTheme: CardThemeData(
        color: surfaceRaised,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(EcoIqRadius.lg),
          side: BorderSide(color: border),
        ),
        margin: EdgeInsets.zero,
      ),
      chipTheme: ChipThemeData(
        backgroundColor: surfaceRaised,
        labelStyle: TextStyle(color: ink, fontSize: 12, fontWeight: FontWeight.w600),
        shape: StadiumBorder(side: BorderSide(color: border)),
        padding: const EdgeInsets.symmetric(horizontal: EcoIqSpace.sm, vertical: 4),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: EcoIqColors.accent,
          foregroundColor: EcoIqColors.bg900,
          textStyle: const TextStyle(fontWeight: FontWeight.w700),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(EcoIqRadius.sm)),
          padding: const EdgeInsets.symmetric(horizontal: EcoIqSpace.lg, vertical: EcoIqSpace.sm),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: ink,
          side: BorderSide(color: border),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(EcoIqRadius.sm)),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surfaceRaised,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(EcoIqRadius.sm),
          borderSide: BorderSide(color: border),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: EcoIqSpace.md, vertical: EcoIqSpace.sm),
      ),
      textTheme: Typography.material2021(platform: TargetPlatform.iOS)
          .black
          .apply(bodyColor: ink, displayColor: ink)
          .copyWith(
            bodySmall: TextStyle(color: muted),
            bodyMedium: TextStyle(color: ink),
            labelSmall: TextStyle(color: muted, fontFeatures: const [FontFeature.tabularFigures()]),
          ),
    );
  }
}
