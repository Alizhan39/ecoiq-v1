import 'package:ecoiq_app/core/api/ecoiq_api_client.dart';
import 'package:ecoiq_app/data/models/company.dart';
import 'package:ecoiq_app/data/repositories/company_repository.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:shared_preferences/shared_preferences.dart';

class _MockApiClient extends Mock implements EcoIqApiClient {}

const _profileA = CompanyProfileData(
  slug: 'company-a',
  name: 'Company A',
  sector: 'Energy',
  country: 'UK',
  city: '',
  website: '',
  logoUrl: null,
  description: '',
  isPublic: true,
  verified: true,
  ecoiqScore: 80,
  rank: 1,
  harmSignals: [],
);

const _profileB = CompanyProfileData(
  slug: 'company-b',
  name: 'Company B',
  sector: 'Mining',
  country: 'ZA',
  city: '',
  website: '',
  logoUrl: null,
  description: '',
  isPublic: true,
  verified: false,
  ecoiqScore: 50,
  rank: 2,
  harmSignals: [],
);

void main() {
  late _MockApiClient apiClient;
  late CompanyRepository repo;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    apiClient = _MockApiClient();
    final prefs = await SharedPreferences.getInstance();
    repo = CompanyRepository(apiClient: apiClient, prefs: prefs);
  });

  test('recentlyViewed is empty before any profile has been fetched', () {
    expect(repo.recentlyViewed(), isEmpty);
  });

  test('getProfile records the company in recentlyViewed, most-recent first', () async {
    when(() => apiClient.getCompanyProfile('company-a')).thenAnswer((_) async => _profileA);
    when(() => apiClient.getCompanyProfile('company-b')).thenAnswer((_) async => _profileB);

    await repo.getProfile('company-a');
    await repo.getProfile('company-b');

    final recent = repo.recentlyViewed();
    expect(recent.map((e) => e.$1), ['company-b', 'company-a']);
  });

  test('re-viewing a company moves it back to the front instead of duplicating it', () async {
    when(() => apiClient.getCompanyProfile('company-a')).thenAnswer((_) async => _profileA);
    when(() => apiClient.getCompanyProfile('company-b')).thenAnswer((_) async => _profileB);

    await repo.getProfile('company-a');
    await repo.getProfile('company-b');
    await repo.getProfile('company-a');

    final recent = repo.recentlyViewed();
    expect(recent.length, 2);
    expect(recent.first.$1, 'company-a');
  });

  test('search delegates straight to the api client', () async {
    when(() => apiClient.searchCompanies('foo')).thenAnswer((_) async => [
          const CompanySummary(
            slug: 'company-a', name: 'Company A', sector: 'Energy', country: 'UK',
            ecoiqScore: 80, rank: 1, isPublic: true, verified: true,
          ),
        ]);
    final results = await repo.search('foo');
    expect(results, hasLength(1));
    expect(results.first.slug, 'company-a');
  });
}
