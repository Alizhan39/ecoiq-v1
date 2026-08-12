/// Mirrors GET /api/v1/app-config/ — see api/app_views.py:AppConfigView.
/// PART 22 of the app spec: "Do not hard-code important commercial or
/// compliance decisions into the application binary" — this is why
/// min-version/maintenance-mode/force-update all come from here, not from
/// a constant in the Dart source.
class EcoIqAppConfig {
  const EcoIqAppConfig({
    required this.minSupportedVersion,
    required this.latestVersion,
    required this.maintenanceMode,
    required this.forceUpdate,
    required this.supportContact,
  });

  final String minSupportedVersion;
  final String latestVersion;
  final bool maintenanceMode;
  final bool forceUpdate;
  final String supportContact;

  factory EcoIqAppConfig.fromJson(Map<String, dynamic> json) => EcoIqAppConfig(
        minSupportedVersion: json['min_supported_version'] as String,
        latestVersion: json['latest_version'] as String,
        maintenanceMode: json['maintenance_mode'] as bool? ?? false,
        forceUpdate: json['force_update'] as bool? ?? false,
        supportContact: (json['support_contact'] as String?) ?? '',
      );

  /// Safe fallback used only when app-config genuinely cannot be reached
  /// (e.g. first launch, fully offline) -- never used to SKIP checking,
  /// only to avoid a hard crash before connectivity exists.
  static const unknown = EcoIqAppConfig(
    minSupportedVersion: '0.0.0',
    latestVersion: '0.0.0',
    maintenanceMode: false,
    forceUpdate: false,
    supportContact: 'support@ecoiq.uk',
  );
}
