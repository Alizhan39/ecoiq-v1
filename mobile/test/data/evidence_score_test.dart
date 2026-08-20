import 'package:ecoiq_app/config/environment.dart';
import 'package:ecoiq_app/data/models/company.dart';
import 'package:ecoiq_app/data/models/evidence.dart';
import 'package:flutter_test/flutter_test.dart';

/// Evidence semantics on the client.
///
/// The invariant every test here serves: **unknown must stay unknown**. The
/// previous parser was
///
///     double.tryParse('${json['ecoiq_score']}') ?? 0
///
/// which turned a missing score into 0 — the worst possible score — and, because
/// it stringified first, did the same to an explicit null (`'null'` does not
/// parse). A company EcoIQ knows nothing about was shown as a company EcoIQ had
/// rated at zero.
void main() {
  group('parseNullableDouble', () {
    test('A: JSON null stays null', () {
      expect(parseNullableDouble(null), isNull);
    });

    test('A: a missing key stays null', () {
      final json = <String, dynamic>{};
      expect(parseNullableDouble(json['ecoiq_score']), isNull);
    });

    test('B: a real 0 stays 0 and is not confused with unknown', () {
      final zero = parseNullableDouble(0);
      expect(zero, 0.0);
      expect(zero, isNotNull);
    });

    test('C: a real 50 stays 50', () {
      expect(parseNullableDouble(50), 50.0);
      expect(parseNullableDouble('50.0'), 50.0);
    });

    test('unparseable input is null, never a substitute number', () {
      expect(parseNullableDouble('not-a-number'), isNull);
      expect(parseNullableDouble('null'), isNull);
    });

    test('the old ?? 0 behaviour is gone', () {
      // Every one of these produced 0.0 before.
      for (final input in <dynamic>[null, 'null', 'N/A', '']) {
        expect(parseNullableDouble(input), isNull,
            reason: '$input must not become a number');
      }
    });
  });

  group('ScoreStatus', () {
    test('maps the server vocabulary', () {
      expect(ScoreStatus.fromJson('PUBLISHED'), ScoreStatus.published);
      expect(ScoreStatus.fromJson('INSUFFICIENT_EVIDENCE'),
          ScoreStatus.insufficientEvidence);
    });

    test('fails closed on anything unrecognised', () {
      for (final input in <dynamic>[null, '', 'SOMETHING_NEW', 42]) {
        expect(ScoreStatus.fromJson(input), ScoreStatus.insufficientEvidence,
            reason: 'an unknown status must not be treated as published');
      }
    });
  });

  group('EvidenceScore', () {
    test('D: an unevidenced API response yields the pending state', () {
      final score = EvidenceScore.fromJson(const {
        'ecoiq_score': null,
        'score_status': 'INSUFFICIENT_EVIDENCE',
        'evidence_coverage': 0,
        'evidence_note': 'EcoIQ does not currently have sufficient evidence.',
      });

      expect(score.value, isNull);
      expect(score.canDisplay, isFalse);
      expect(score.coveragePercent, 0);
      expect(score.note, isNotNull);
    });

    test('an evidenced response yields a displayable score', () {
      final score = EvidenceScore.fromJson(const {
        'ecoiq_score': 78.4,
        'score_status': 'PUBLISHED',
        'evidence_coverage': 87,
      });

      expect(score.value, 78.4);
      expect(score.canDisplay, isTrue);
      expect(score.coveragePercent, 87);
    });

    test('B: a measured 0 is displayable and stays 0', () {
      final score = EvidenceScore.fromJson(const {
        'ecoiq_score': 0,
        'score_status': 'PUBLISHED',
        'evidence_coverage': 64,
      });

      expect(score.value, 0.0);
      expect(score.canDisplay, isTrue,
          reason: 'a measured zero is a finding and must be shown');
    });

    test('C: a measured 50 is displayable and stays 50', () {
      final score = EvidenceScore.fromJson(const {
        'ecoiq_score': 50,
        'score_status': 'PUBLISHED',
        'evidence_coverage': 71,
      });

      expect(score.value, 50.0);
      expect(score.canDisplay, isTrue);
    });

    test('a measured 0 and an unknown are distinguishable', () {
      final measuredZero = EvidenceScore.fromJson(
          const {'ecoiq_score': 0, 'score_status': 'PUBLISHED'});
      final unknown = EvidenceScore.fromJson(
          const {'ecoiq_score': null, 'score_status': 'INSUFFICIENT_EVIDENCE'});

      expect(measuredZero.value, 0.0);
      expect(unknown.value, isNull);
      expect(measuredZero.canDisplay, isNotNull);
      expect(measuredZero.canDisplay != unknown.canDisplay, isTrue);
    });

    test('a contradictory response fails closed', () {
      // A number with INSUFFICIENT_EVIDENCE, or PUBLISHED with no number:
      // both are contradictions, and neither may be displayed.
      final numberWithoutEvidence = EvidenceScore.fromJson(
          const {'ecoiq_score': 71.4, 'score_status': 'INSUFFICIENT_EVIDENCE'});
      final publishedWithoutNumber = EvidenceScore.fromJson(
          const {'ecoiq_score': null, 'score_status': 'PUBLISHED'});

      expect(numberWithoutEvidence.canDisplay, isFalse);
      expect(publishedWithoutNumber.canDisplay, isFalse);
    });
  });

  group('CompanySummary / CompanyProfileData parsing', () {
    test('an unevidenced company parses with a null score and null rank', () {
      final summary = CompanySummary.fromJson(const {
        'slug': 'acme',
        'name': 'Acme',
        'sector': 'energy',
        'country': 'UK',
        'ecoiq_score': null,
        'score_status': 'INSUFFICIENT_EVIDENCE',
        'evidence_coverage': 0,
        'rank': null,
      });

      expect(summary.score.value, isNull);
      expect(summary.score.canDisplay, isFalse);
      expect(summary.rank, isNull,
          reason: 'F: an unranked company must not enter a list as rank 0');
    });

    test('F: a null rank is null, not zero', () {
      final summary = CompanySummary.fromJson(const {
        'slug': 'acme',
        'name': 'Acme',
        'sector': '',
        'country': '',
        'ecoiq_score': null,
        'score_status': 'INSUFFICIENT_EVIDENCE',
        'rank': null,
      });
      expect(summary.rank, isNot(0));
      expect(summary.rank, isNull);
    });

    test('a profile keeps its descriptive fields regardless of score state',
        () {
      final profile = CompanyProfileData.fromJson(const {
        'slug': 'acme',
        'name': 'Acme',
        'sector': 'energy',
        'country': 'UK',
        'city': 'Leeds',
        'website': 'https://example.org',
        'description': 'A description.',
        'is_public': true,
        'verified': true,
        'ecoiq_score': null,
        'score_status': 'INSUFFICIENT_EVIDENCE',
        'harm_signals': <dynamic>[],
      });

      expect(profile.score.canDisplay, isFalse);
      expect(profile.description, 'A description.');
      expect(profile.verified, isTrue,
          reason: 'the score gate must not suppress facts about the company');
    });
  });

  group('G/H: environment routing', () {
    test('G: production company data uses the canonical v2 API', () {
      const env = EcoIqEnvName.production;
      final production = Environment.fromName(env);
      expect(production.apiV2BaseUrl, endsWith('/api/v2'));
      expect(production.apiV2BaseUrl, startsWith('https://'));
    });

    test('auth stays on v1 — v2 does not define those endpoints', () {
      final production = Environment.fromName(EcoIqEnvName.production);
      expect(production.apiBaseUrl, endsWith('/api/v1'));
    });

    test('every non-mock environment derives its own v2 base', () {
      for (final name in [
        EcoIqEnvName.dev,
        EcoIqEnvName.staging,
        EcoIqEnvName.production,
      ]) {
        final env = Environment.fromName(name);
        expect(env.apiV2BaseUrl, endsWith('/v2'),
            reason: '$name must not silently fall back to v1');
        expect(env.apiV2BaseUrl, isNot(contains('/v1')));
      }
    });

    test('H: the mock environment is unchanged', () {
      final mock = Environment.fromName(EcoIqEnvName.mock);
      expect(mock.isMock, isTrue);
      expect(mock.apiBaseUrl, 'mock://ecoiq');
    });
  });
}
