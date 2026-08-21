/**
 * The evidence contract, in types.
 *
 * Mirrors docs/product/FRONTEND_API_CONTRACT.md. With `strictNullChecks` on,
 * these types are what stops the contract being violated by accident — a
 * `number | null` score cannot reach a render path without the null being
 * handled, and the compiler says so rather than a reviewer having to.
 */

/** Authoritative. This field, not the score, decides what the UI renders. */
export type ScoreStatus =
  | 'PUBLISHED'
  | 'PROVISIONAL'
  | 'INSUFFICIENT_EVIDENCE';

/**
 * Never a number, and never rendered as one. The inputs are categorical, and a
 * percentage would manufacture precision the data cannot support.
 */
export type Confidence = 'HIGH' | 'MEDIUM' | 'LOW' | 'INSUFFICIENT_EVIDENCE';

export interface CompanySummary {
  slug: string;
  name: string;
  sector: string;
  country: string;
  is_public: boolean;
  verified: boolean;
  /**
   * `null` unless `score_status === 'PUBLISHED'`.
   *
   * A `0` is a REAL, publishable score — a company genuinely assessed at zero.
   * Never treat it as missing.
   */
  ecoiq_score: number | null;
  score_status: ScoreStatus;
  /**
   * 0–100 integer, ALWAYS present. Zero coverage is a measurement ("we
   * checked, and nothing is evidenced"), not an absence — which is why this is
   * not nullable while the score is.
   */
  evidence_coverage: number;
  confidence: Confidence;
  /** `null` when the score is not publishable. Never derive one client-side. */
  rank: number | null;
  url: string;
}

export interface HarmSignal {
  id: string;
  label: string;
  /** `insufficient_evidence` is NOT `clear`. A check nobody ran is not a pass. */
  status: string;
  penalty: number;
  detail: string;
}

export interface CompanyDetail extends
  Omit<CompanySummary, 'rank' | 'url'> {
  city: string;
  website: string;
  logo_url: string | null;
  description: string;
  /** Plain-English reason a score is withheld. Render instead of the score. */
  evidence_note: string;
  harm_signals: HarmSignal[];
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/* ── Guards ────────────────────────────────────────────────────────────────
 *
 * Used instead of ad-hoc conditionals so the rule lives in one place. A
 * component asks `isPublished(company)`; it never writes `score ?? 0`.
 */

/** The only correct test before rendering a score. */
export function isPublished(
  company: Pick<CompanySummary, 'score_status' | 'ecoiq_score'>,
): company is typeof company & { ecoiq_score: number } {
  return company.score_status === 'PUBLISHED' && company.ecoiq_score !== null;
}

/**
 * A score safe to render, or null.
 *
 * Deliberately returns `null` rather than a fallback number, so a caller that
 * ignores it gets a compiler error instead of a fabricated zero.
 */
export function publishableScore(
  company: Pick<CompanySummary, 'score_status' | 'ecoiq_score'>,
): number | null {
  return isPublished(company) ? company.ecoiq_score : null;
}

/** Coverage as "11 of 16" needs the halves; the API gives only the percent. */
export function coverageLabel(percent: number): string {
  return `${percent}%`;
}

export function confidenceLabel(value: Confidence): string {
  switch (value) {
    case 'HIGH':
      return 'High';
    case 'MEDIUM':
      return 'Medium';
    case 'LOW':
      return 'Low';
    case 'INSUFFICIENT_EVIDENCE':
      return 'Insufficient evidence';
  }
}

/** `insufficient_evidence` must never render as an all-clear. */
export function isSignalClear(signal: HarmSignal): boolean {
  return signal.status === 'clear';
}
