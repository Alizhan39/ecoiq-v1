/// Evidence semantics shared by every score the app displays.
///
/// The API decides whether a score is publishable; the app reports that
/// decision. Nothing here classifies anything itself, and the status strings
/// are the server's own (companies.evidence, which mirrors decision_studio) —
/// mapped, never re-invented, so the two cannot drift.
///
/// The rule this file exists to enforce:
///
///     unknown stays unknown
///
/// It must never become 0. A score of 0 is a finding; no score is the absence
/// of one, and rendering the second as the first states something about a
/// company that EcoIQ has not established.
library;

/// Whether the server could publish a score.
enum ScoreStatus {
  /// Evidence supports the score. The number is real and may be shown.
  published,

  /// EcoIQ cannot support a score with evidence. There is no number to show.
  insufficientEvidence;

  /// Maps the server's `score_status`. Unrecognised values fail closed to
  /// [insufficientEvidence]: if the app cannot understand the status, it has
  /// no basis for presenting the score as evidenced.
  static ScoreStatus fromJson(dynamic value) => switch (value) {
        'PUBLISHED' => ScoreStatus.published,
        _ => ScoreStatus.insufficientEvidence,
      };

  bool get isPublished => this == ScoreStatus.published;
}

/// Parses a JSON number that may legitimately be absent.
///
/// Returns null for null, for a missing key, and for anything unparseable —
/// never a substitute number. This replaces
///
///     double.tryParse('${json['ecoiq_score']}') ?? 0
///
/// which turned every one of those cases into 0, the worst possible score.
/// Note the old form also stringified null into the literal "null", so even an
/// explicit null from the server became 0.
double? parseNullableDouble(dynamic value) {
  if (value == null) return null;
  if (value is num) return value.toDouble();
  return double.tryParse(value.toString());
}

/// Parses an integer that may legitimately be absent, with the same rule.
int? parseNullableInt(dynamic value) {
  if (value == null) return null;
  if (value is int) return value;
  if (value is num) return value.toInt();
  return int.tryParse(value.toString());
}

/// A score together with the evidence state that decides whether to show it.
///
/// Kept as one object so a widget cannot read the number without also having
/// been handed the reason it might not be there.
class EvidenceScore {
  const EvidenceScore({
    required this.value,
    required this.status,
    this.coveragePercent,
    this.note,
  });

  /// Null when there is no publishable score. Never a stand-in.
  final double? value;
  final ScoreStatus status;

  /// Whole percent of material inputs backed by real evidence, if reported.
  final int? coveragePercent;

  /// Server-supplied explanation shown when there is no score.
  final String? note;

  /// True only when there is a real number AND the server says it is publishable.
  ///
  /// Both conditions on purpose: a null value with PUBLISHED, or a number with
  /// INSUFFICIENT_EVIDENCE, are both contradictions, and the safe reading of a
  /// contradiction is that there is nothing to show.
  bool get canDisplay => value != null && status.isPublished;

  /// What to render when [canDisplay] is false. Matches the web wording.
  static const String pendingLabel = 'Evidence assessment pending';

  static const String pendingLabelShort = 'Evidence pending';

  factory EvidenceScore.fromJson(
    Map<String, dynamic> json, {
    String valueKey = 'ecoiq_score',
  }) =>
      EvidenceScore(
        value: parseNullableDouble(json[valueKey]),
        status: ScoreStatus.fromJson(json['score_status']),
        coveragePercent: parseNullableInt(json['evidence_coverage']),
        note: json['evidence_note'] as String?,
      );

  /// For mock data and tests that need a known-good published score.
  factory EvidenceScore.published(double value, {int coveragePercent = 100}) =>
      EvidenceScore(
        value: value,
        status: ScoreStatus.published,
        coveragePercent: coveragePercent,
      );

  /// For mock data and tests that need the pending-evidence path.
  factory EvidenceScore.pending() => const EvidenceScore(
        value: null,
        status: ScoreStatus.insufficientEvidence,
        coveragePercent: 0,
      );
}
