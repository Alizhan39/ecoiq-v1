/// Mirrors GET /api/v1/me/ — see api/app_views.py:MeView.
class EcoIqPlanSummary {
  const EcoIqPlanSummary({
    required this.product,
    required this.plan,
    required this.name,
    required this.status,
  });

  final String product;
  final String plan;
  final String name;
  final String status;

  factory EcoIqPlanSummary.fromJson(Map<String, dynamic> json) =>
      EcoIqPlanSummary(
        product: json['product'] as String,
        plan: json['plan'] as String,
        name: json['name'] as String,
        status: json['status'] as String,
      );
}

class EcoIqUser {
  const EcoIqUser({
    required this.id,
    required this.username,
    required this.email,
    required this.isStaff,
    required this.plan,
    required this.entitlements,
  });

  final int id;
  final String username;
  final String email;
  final bool isStaff;
  final EcoIqPlanSummary? plan;

  /// {feature_key: allowed} — a UI hint only. Every gated read is still
  /// re-checked server-side on the endpoint that serves the data (see
  /// api/permissions.py:RequiresFeature) -- the app must NOT treat this map
  /// as the source of truth for whether a request will succeed.
  final Map<String, bool> entitlements;

  bool has(String featureKey) => entitlements[featureKey] ?? false;

  factory EcoIqUser.fromJson(Map<String, dynamic> json) => EcoIqUser(
        id: json['id'] as int,
        username: json['username'] as String,
        email: (json['email'] as String?) ?? '',
        isStaff: json['is_staff'] as bool? ?? false,
        plan: json['plan'] == null
            ? null
            : EcoIqPlanSummary.fromJson(json['plan'] as Map<String, dynamic>),
        entitlements: (json['entitlements'] as Map<String, dynamic>? ?? {})
            .map((key, value) => MapEntry(key, value as bool)),
      );
}
