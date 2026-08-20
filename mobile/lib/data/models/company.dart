import 'evidence.dart';

/// Mirrors api.v2_serializers.CompanyV2Serializer — used by
/// GET /api/v2/companies/?q= and the company search screen's result list.
///
/// The score is an [EvidenceScore], not a bare double: v2 returns null when
/// EcoIQ cannot support a score with evidence, and that must stay
/// distinguishable from a real score of 0.
class CompanySummary {
  const CompanySummary({
    required this.slug,
    required this.name,
    required this.sector,
    required this.country,
    required this.score,
    required this.rank,
    required this.isPublic,
    required this.verified,
  });

  final String slug;
  final String name;
  final String sector;
  final String country;
  final EvidenceScore score;

  /// Null when the score is not publishable — a rank asserts the comparison
  /// the score is withholding, so the server omits it and so do we.
  final int? rank;
  final bool isPublic;
  final bool verified;

  factory CompanySummary.fromJson(Map<String, dynamic> json) => CompanySummary(
        slug: json['slug'] as String,
        name: json['name'] as String,
        sector: (json['sector'] as String?) ?? '',
        country: (json['country'] as String?) ?? '',
        score: EvidenceScore.fromJson(json),
        rank: parseNullableInt(json['rank']),
        isPublic: json['is_public'] as bool? ?? true,
        verified: json['verified'] as bool? ?? false,
      );
}

/// One row from CompanyDetailSerializer.harm_signals — deliberately kept
/// as a labelled status, never a bare accusation string (PART 6: "Never
/// display an unsupported definitive accusation").
class HarmSignal {
  const HarmSignal(
      {required this.id,
      required this.label,
      required this.status,
      required this.penalty});

  final String id;
  final String label;

  /// One of: verified_direct | verified_indirect | under_investigation |
  /// disputed | allegation_only | historical | insufficient_evidence
  /// (server-authoritative vocabulary -- the app renders it, never infers it).
  final String status;
  final int penalty;

  factory HarmSignal.fromJson(Map<String, dynamic> json) => HarmSignal(
        id: json['id'] as String,
        label: json['label'] as String,
        status: json['status'] as String,
        penalty: json['penalty'] as int? ?? 0,
      );
}

/// Mirrors api.v2_serializers.CompanyProfileV2Serializer — the company profile
/// screen. Descriptive fields come through unchanged; only the score carries
/// evidence semantics.
class CompanyProfileData {
  const CompanyProfileData({
    required this.slug,
    required this.name,
    required this.sector,
    required this.country,
    required this.city,
    required this.website,
    required this.logoUrl,
    required this.description,
    required this.isPublic,
    required this.verified,
    required this.score,
    required this.rank,
    required this.harmSignals,
  });

  final String slug;
  final String name;
  final String sector;
  final String country;
  final String city;
  final String website;
  final String? logoUrl;
  final String description;
  final bool isPublic;
  final bool verified;
  final EvidenceScore score;
  final int? rank;
  final List<HarmSignal> harmSignals;

  factory CompanyProfileData.fromJson(Map<String, dynamic> json) =>
      CompanyProfileData(
        slug: json['slug'] as String,
        name: json['name'] as String,
        sector: (json['sector'] as String?) ?? '',
        country: (json['country'] as String?) ?? '',
        city: (json['city'] as String?) ?? '',
        website: (json['website'] as String?) ?? '',
        logoUrl: json['logo_url'] as String?,
        description: (json['description'] as String?) ?? '',
        isPublic: json['is_public'] as bool? ?? true,
        verified: json['verified'] as bool? ?? false,
        score: EvidenceScore.fromJson(json),
        rank: parseNullableInt(json['rank']),
        harmSignals: ((json['harm_signals'] as List?) ?? [])
            .map((e) => HarmSignal.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}
