/**
 * The organisation assessment. Mirrors api/v2_assessment.py.
 *
 * Every panel is OPTIONAL, and that is the contract, not laziness: an
 * organisation without a publishable assessment gets identity, evidence state
 * and gaps, and the panel keys are absent from the payload entirely.
 *
 * Optional rather than nullable for the same reason the API omits them.
 * `ethics: null` would typecheck a component that renders an empty ethics
 * panel; `ethics?:` makes the compiler ask whether there is one at all.
 */
import type { Confidence, ScoreStatus } from './evidence';

export interface Pillar {
  key: string;
  label: string;
  /** null is unassessed. It is not zero, and must never render as a floor. */
  value: number | null;
}

export interface DecisionIntegrity {
  score: number | null;
  risk_level: string;
  verdict: string;
  evidence_status: string;
  red_line_breached: boolean;
}

export interface Controversy {
  title: string;
  category: string;
  severity: string;
  status: string;
  reported_date: string | null;
}

export interface Ethics {
  net_ethical_impact: number | null;
  transition_stewardship: number | null;
  regenerative_value: number | null;
  total_benefit_score: number | null;
  total_harm_score: number | null;
  key_harms: string[];
  key_benefits: string[];
  next_best_actions: string[];
  /** The ethics engine's own confidence. NOT companies.confidence — they
   *  measure different things and must not be rendered as one. */
  engine_confidence: string;
  analyst_reviewed: boolean;
  formula_version: string;
}

export interface FinancingReadiness {
  readiness: number | null;
  tier: string;
  evidence_completeness: number | null;
  dimensions: Record<string, number | null>;
  missing_requirements: string[];
  next_actions: string[];
  engine_confidence: string;
  analyst_reviewed: boolean;
}

export interface Shariah {
  /** Rendered with the result, always. Never as a page footnote. */
  disclaimer: string;
  methodology: string;
  overall_result: string;
  business_activity_result: string;
  business_activity_reason: string;
  financial_ratio_result: string;
  data_completeness_pct: number | null;
  review_status: string;
  screened_at: string | null;
}

export interface EvidenceGaps {
  covered: number;
  required: number;
  missing: string[];
  unevidenced: string[];
  reasons: string[];
}

export interface Assessment {
  slug: string;
  name: string;
  sector: string;
  country: string;
  score_status: ScoreStatus;
  ecoiq_score: number | null;
  evidence_coverage: number;
  confidence: Confidence;
  evidence_gaps: EvidenceGaps;
  evidence_note?: { headline: string; detail: string };
  material_evidence?: Pillar[];
  decision_risks?: { integrity: DecisionIntegrity | null; controversies: Controversy[] };
  ethics?: Ethics | null;
  financing_readiness?: FinancingReadiness | null;
  shariah?: Shariah | null;
}

/** A metric value, or an em dash. Never a substituted zero. */
export function metric(value: number | null, suffix = ''): string {
  if (value === null) return '—';
  return `${value.toFixed(1)}${suffix}`;
}
