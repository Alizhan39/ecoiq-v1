/// Provider-neutral analytics interface (PART 23 of the app spec). Screens
/// call `AnalyticsService.track(...)`, never a vendor SDK directly — so
/// swapping providers later (or adding crash reporting/perf monitoring)
/// touches one implementation file, not every screen.
///
/// Track ONLY the events PART 23 allow-lists, and NEVER put allegation
/// details, portfolio values, acquisition prices, raw sensitive search
/// terms, or evidence excerpts into `properties` — see
/// EcoIqAnalyticsEvent's allow-listed property keys below.
enum EcoIqAnalyticsEvent {
  appOpened,
  searchCompleted,
  companyViewed,
  watchlistItemAdded,
  portfolioImported,
  reportOpened,
  subscriptionScreenViewed,
  purchaseVerificationCompleted,
}

abstract class AnalyticsService {
  void track(EcoIqAnalyticsEvent event,
      {Map<String, Object?> properties = const {}});
  void setUserId(String? userId);
}

/// Default implementation: does nothing. A real provider (Firebase
/// Analytics, PostHog, etc.) is a Phase 3+ decision requiring its own
/// privacy/consent review — see PART 18 of the app spec and the final
/// report's "prepared, not operational" section. Using a no-op by default
/// means the app never silently starts sending data to a vendor before
/// that review happens.
class NoOpAnalyticsService implements AnalyticsService {
  @override
  void track(EcoIqAnalyticsEvent event,
      {Map<String, Object?> properties = const {}}) {}

  @override
  void setUserId(String? userId) {}
}
