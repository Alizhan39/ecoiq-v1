import type { CompanySummary } from '@/types/evidence';
import { confidenceLabel, isPublished } from '@/types/evidence';

/**
 * The score, or an honest statement that there isn't one.
 *
 * This component exists so that no page has to make the decision itself. Every
 * surface that shows a score renders this, and the rule lives in one place.
 */
export function ScoreDisplay({
  company,
  note,
}: {
  company: Pick<CompanySummary, 'score_status' | 'ecoiq_score'>;
  note?: string;
}) {
  if (!isPublished(company)) {
    return (
      <div className="score score--withheld">
        <span className="score__pending">Evidence assessment pending</span>
        {note ? <p className="score__note">{note}</p> : null}
      </div>
    );
  }

  // `company.ecoiq_score` is narrowed to `number` by isPublished(). A score of
  // 0 renders as 0 — it is a real assessment, not a missing one.
  return (
    <div className="score score--published">
      <span className="score__value">{company.ecoiq_score.toFixed(1)}</span>
      <span className="score__scale">/100</span>
    </div>
  );
}

/**
 * Coverage and confidence, side by side and never combined.
 *
 * They answer different questions and do not track each other: 100% coverage
 * from unverified sources is complete and weak; 40% from verified audits is
 * incomplete and strong. Averaging them would produce a figure true of neither.
 */
export function EvidenceSummary({
  coverage,
  confidence,
}: {
  coverage: number;
  confidence: CompanySummary['confidence'];
}) {
  return (
    <dl className="evidence">
      <div className="evidence__item">
        <dt>Evidence coverage</dt>
        {/* Always a number, including 0 — zero coverage is a measurement. */}
        <dd>{coverage}%</dd>
      </div>
      <div className="evidence__item">
        <dt>Confidence</dt>
        {/* A label, never a percentage. */}
        <dd>{confidenceLabel(confidence)}</dd>
      </div>
    </dl>
  );
}

/** A rank, or nothing. Never derived from list position. */
export function RankDisplay({ rank }: { rank: number | null }) {
  if (rank === null) return <span className="rank rank--none">—</span>;
  return <span className="rank">#{rank}</span>;
}
