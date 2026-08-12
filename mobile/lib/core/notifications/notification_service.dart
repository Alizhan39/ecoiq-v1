/// Provider-neutral push-notification interface (PART 11 of the app spec).
/// Real delivery needs APNs (iOS), Firebase Cloud Messaging (Android), and
/// Windows push (WNS/MSIX) — each requires its own platform credentials
/// and store-review-relevant setup that hasn't been provisioned yet (see
/// the final report's "prepared, not operational" section). This
/// interface exists now so the rest of the app (settings screen, deep-link
/// routing from a tapped notification) can be built against a stable
/// contract before that wiring lands.
///
/// Notification bodies must NEVER include the underlying allegation/
/// evidence detail (PART 11: "Do not include highly sensitive accusations
/// in the lock-screen notification body") — the safe, generic copy lives
/// server-side once the real notification-composition endpoint exists;
/// this client-side type only carries a category + a link to open once
/// the user has authenticated inside the app.
enum EcoIqNotificationCategory {
  newVerifiedControversy,
  officialInvestigation,
  legalOrRegulatoryDecision,
  sanctionsDesignation,
  newMilitaryContract,
  controversialWeaponsExposure,
  classificationChange,
  reportPublished,
  companyResponseOrCorrection,
  evidenceConfidenceChange,
}

class EcoIqNotificationPayload {
  const EcoIqNotificationPayload({required this.category, required this.deepLink});
  final EcoIqNotificationCategory category;

  /// e.g. ecoiq://company/<slug>/ethical-impact — resolved through the
  /// same authenticated router guard as any other deep link (PART 19).
  final String deepLink;
}

abstract class NotificationService {
  Future<void> requestPermission();
  Future<String?> getDeviceToken();
  Stream<EcoIqNotificationPayload> get onNotificationTapped;
}

/// Default implementation: no-op, no permission prompt, no token. Wiring a
/// real provider (APNs/FCM/WNS) is a Phase 3 item requiring platform
/// credentials this environment doesn't have — see the final report.
class NoOpNotificationService implements NotificationService {
  @override
  Future<void> requestPermission() async {}

  @override
  Future<String?> getDeviceToken() async => null;

  @override
  Stream<EcoIqNotificationPayload> get onNotificationTapped => const Stream.empty();
}
