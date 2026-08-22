/**
 * Projects.
 *
 * Every quantity is nullable. A project with no recorded CO2 figure has no
 * recorded figure — it did not reduce zero tonnes, and the difference is the
 * whole point.
 */
export interface Project {
  slug: string;
  name: string;
  project_type: string;
  status: string;
  location: string;
  description: string;
  company: string;
  /** Complete and unverified is a real state. Do not infer one from the other. */
  verified: boolean;
  investment_usd: number | null;
  co2_reduction_tonnes: number | null;
  households_helped: number | null;
}

/**
 * A programme concept: an intention, not an implementation.
 *
 * Kept in a separate type from `Project` so the compiler makes the distinction
 * for us. A concept has no measured quantity to report, which is why it has no
 * nullable-number field at all — `funding_amount` is editorial text that
 * travels with the label and note carrying the word "indicative".
 */
export interface ProjectConcept {
  slug: string;
  name: string;
  tagline: string;
  /** 'concept' | 'scoping' | 'design' | 'pilot' | 'scaling'. Never complete. */
  status_key: string;
  status: string;
  location: string;
  sector: string;
  timeline_label: string;
  overview: string;
  problem: string;
  solution: string;
  expected_impact: { value: string; label: string }[];
  kpis: { code: string; label: string; note: string }[];
  timeline_phases: { phase: string; window: string; detail: string }[];
  partnership_opportunities: string[];
  funding_amount: string;
  funding_label: string;
  funding_note: string;
}

export interface ProjectList {
  count: number;
  /** Carried beside `count` because "12 projects" and "12 projects, 0
   *  independently verified" are very different statements. */
  verified_count: number;
  results: Project[];
  /**
   * NEVER added to `count`, and never merged into `results`.
   *
   * Five concepts rendered alongside zero recorded projects reads as "five
   * projects" the moment they share a list. Separate arrays keep the compiler
   * on the right side of that.
   */
  concepts: ProjectConcept[];
}

/** A quantity, or an em dash. Never a substituted zero. */
export function quantity(value: number | null, unit = ''): string {
  if (value === null) return '—';
  return unit ? `${value.toLocaleString()} ${unit}` : value.toLocaleString();
}
