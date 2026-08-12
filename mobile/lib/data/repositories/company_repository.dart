import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../../core/api/ecoiq_api_client.dart';
import '../models/company.dart';

/// Thin data-access layer over EcoIqApiClient for company search/profile,
/// plus a small non-sensitive "recently viewed" cache (company slugs +
/// names only -- never scores, harm signals, or anything gated, since that
/// must always be re-fetched fresh and re-authorized; see PART 14 of the
/// app spec's cache exclusion list).
class CompanyRepository {
  CompanyRepository({required EcoIqApiClient apiClient, required SharedPreferences prefs})
      : _apiClient = apiClient,
        _prefs = prefs;

  final EcoIqApiClient _apiClient;
  final SharedPreferences _prefs;

  static const _recentlyViewedKey = 'ecoiq.recently_viewed_companies';
  static const _maxRecentlyViewed = 10;

  Future<List<CompanySummary>> search(String query) => _apiClient.searchCompanies(query);

  Future<CompanyProfileData> getProfile(String slug) async {
    final profile = await _apiClient.getCompanyProfile(slug);
    await _recordRecentlyViewed(profile.slug, profile.name);
    return profile;
  }

  /// [(slug, name)] most-recent-first — display only, always re-fetch the
  /// real profile (with a fresh authorization check) when tapped.
  List<(String slug, String name)> recentlyViewed() {
    final raw = _prefs.getString(_recentlyViewedKey);
    if (raw == null) return [];
    final decoded = jsonDecode(raw) as List;
    return decoded
        .map((e) => (e as Map<String, dynamic>))
        .map((e) => (e['slug'] as String, e['name'] as String))
        .toList();
  }

  Future<void> _recordRecentlyViewed(String slug, String name) async {
    final current = recentlyViewed().where((e) => e.$1 != slug).toList();
    current.insert(0, (slug, name));
    final trimmed = current.take(_maxRecentlyViewed).toList();
    final encoded = jsonEncode(trimmed.map((e) => {'slug': e.$1, 'name': e.$2}).toList());
    await _prefs.setString(_recentlyViewedKey, encoded);
  }
}
