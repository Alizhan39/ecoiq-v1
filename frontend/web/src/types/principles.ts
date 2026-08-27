/**
 * The 114 stewardship principles: the registry, and one organisation's state
 * across all of them.
 *
 * Mirrors `api/v2_principles.py`. As with `kpi.ts`, the server decides every
 * state and this file only describes the shape, so a component cannot quietly
 * invent a rule the backend does not apply.
 *
 * NOTE ON WHAT IS ABSENT — the same note as `kpi.ts`, for the same reason.
 * There is no surah number, name, Arabic term, ayah text or translation in
 * this contract, and there must not be. The sacred-source layer is internal
 * (docs/governance-principles-surah-map.md). A type that cannot express it is
 * one more place the rule cannot be broken by accident.
 *
 * NOTE ON WHAT IS ALSO ABSENT — there is no overall score, rating or grade.
 * The matrix reports evidence state. `assessed_pct` says how much of the
 * framework has been investigated, which is a statement about EcoIQ's work
 * and not a verdict on the organisation.
 */
import type { Verdict } from './kpi';

/** The category taxonomy. Ten groups, and every principle is in exactly one. */
export interface PrincipleCategory {
  key: string;
  label: string;
  principle_count: number;
}

/** A category as it appears on a company matrix — carries progress too. */
export interface CompanyPrincipleCategory extends PrincipleCategory {
  assessed_count: number;
}

/** The principle itself: what EcoIQ assesses against, with no organisation. */
export interface Principle {
  kpi_id: number;
  title: string;
  category: string;
  tagline: string;
  /** The investigation question. A principle without one is a label. */
  question: string;
  metrics: string[];
  principle_statement: string;
}

export interface PrincipleRegistry {
  total: number;
  categories: PrincipleCategory[];
  principles: Principle[];
}

/** How much evidence sits behind one cell, and how much of it counts. */
export interface PrincipleEvidenceCounts {
  total: number;
  confirmed: number;
  supports: number;
  conflicts: number;
  context: number;
  insufficient_to_conclude: number;
  /** Present but not counted — unreviewed, disputed or rejected. */
  excluded_from_assessment: number;
}

/**
 * One principle, for one organisation.
 *
 * `state` is the real status and the only verdict. The fields beside it are
 * orthogonal facts, not a second status enum: a cell that is `conflict` with
 * `remediation_step_count > 0` is "conflict, remediation recorded", composed
 * here from facts rather than asserted by the server as a new state. That is
 * deliberate — remediation is shown alongside a finding, never instead of it.
 */
export interface CompanyPrinciple extends Principle {
  state: Verdict;
  state_label: string;
  counts: PrincipleEvidenceCounts;
  /** Evidence awaiting review. Visible, and counting toward nothing. */
  pending_review_count: number;
  remediation_step_count: number;
  /** True only when a CONFIRMED conflict rests on a final or court finding. */
  has_material_conflict: boolean;
  is_demo: boolean;
  last_assessed_at: string | null;
}

export interface CompanyPrincipleSummary {
  total: number;
  assessed: number;
  not_assessed: number;
  /** Share of the framework investigated. NOT a score for the organisation. */
  assessed_pct: number;
  counts: Record<string, number>;
  pending_review_total: number;
}

export interface CompanyPrincipleMatrix {
  company: { slug: string; name: string; sector: string };
  summary: CompanyPrincipleSummary;
  categories: CompanyPrincipleCategory[];
  principles: CompanyPrinciple[];
}

/** A principle nobody has investigated yet. Not a finding about anyone. */
export function isUnassessed(principle: CompanyPrinciple): boolean {
  return principle.state === 'not_assessed';
}

/**
 * Has anyone looked at this principle for this organisation?
 *
 * Distinct from `isUnassessed`: a principle can be assessed and still conclude
 * `insufficient_evidence`, which is a real finding — we looked, and there was
 * not enough. Collapsing the two would report absence of work as absence of
 * evidence.
 */
export function hasBeenInvestigated(principle: CompanyPrinciple): boolean {
  return !isUnassessed(principle);
}
