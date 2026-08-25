/**
 * One organisation against one of the 114 stewardship principles.
 *
 * Mirrors `api/v2_kpi.py`. The server decides the verdict, the confidence and
 * what counts — this file only describes the shape, so that a component cannot
 * quietly invent a rule the backend does not apply.
 *
 * NOTE ON WHAT IS ABSENT. There is no surah number, name, Arabic term, ayah
 * text or translation in this contract, and there must not be. The sacred
 * source layer is internal (docs/governance-principles-surah-map.md) and the
 * API never emits it. A type that cannot express it is one more place the rule
 * cannot be broken by accident.
 */

/** Ordered weakest to strongest. Rendering must never flatten these. */
export type LegalStatus =
  | 'unclassified'
  | 'superseded'
  | 'company_policy'
  | 'company_disclosure'
  | 'disputed'
  | 'third_party_analysis'
  | 'remediation_record'
  | 'preliminary_regulatory_finding'
  | 'final_regulatory_finding'
  | 'court_finding';

/** What the evidence says about the principle. Remediation is NOT here. */
export type EvidenceRelation =
  | 'supports'
  | 'conflicts'
  | 'context'
  | 'insufficient_to_conclude';

export type Verdict =
  | 'strong_support'
  | 'support'
  | 'mixed'
  | 'mixed_material_conflict'
  | 'conflict'
  | 'neutral_or_no_material_link'
  | 'insufficient_evidence'
  | 'not_assessed';

/** Categorical, never a percentage — the inputs are categorical too. */
export type KpiConfidence =
  | 'INSUFFICIENT_EVIDENCE' | 'LOW' | 'MEDIUM' | 'HIGH' | 'VERY_HIGH';

export interface KpiEvidence {
  id: number;
  title: string;
  relation: EvidenceRelation;
  legal_status: LegalStatus;
  /** 0–5. Presentation ordering only; never a score. */
  legal_status_strength: number;
  source_authority: string;
  source_url: string;
  source_type: string;
  date_collected: string | null;
  review_tier: string;
  verification_status: string;
  review_state: string;
  /**
   * False for anything not `confirmed`. Such items are still returned and
   * still shown — hiding them would overstate how well evidenced the verdict
   * is — but they changed nothing.
   */
  counts_toward_assessment: boolean;
  match_basis: string;
  is_demo: boolean;
  excerpt: string;
}

export type RemediationKind =
  | 'finding' | 'company_response' | 'product_or_policy_change'
  | 'regulatory_response' | 'residual_concern';

export interface RemediationStep {
  position: number;
  kind: RemediationKind;
  kind_label: string;
  summary: string;
  detail: string;
  occurred_on: string | null;
  verification: string;
  verification_label: string;
  evidence_id: number | null;
}

export interface StewardshipPrinciple {
  kpi_id: number;
  title: string;
  tagline: string;
  question: string;
  category: string;
  principle_statement: string;
  metrics: string[];
}

export interface KpiInvestigation {
  company: { slug: string; name: string; sector: string };
  stewardship_principle: StewardshipPrinciple;
  assessment: {
    verdict: Verdict;
    verdict_label: string;
    confidence: KpiConfidence;
    confidence_reasons: string[];
    rationale: string;
    is_demo: boolean;
    last_assessed_at: string | null;
  };
  counts: {
    total: number; confirmed: number; supports: number; conflicts: number;
    context: number; excluded_from_assessment: number; remediation_steps: number;
  };
  evidence: KpiEvidence[];
  remediation: RemediationStep[];
}

/** Human labels. Kept beside the types so a new status cannot render raw. */
export const LEGAL_STATUS_LABEL: Record<LegalStatus, string> = {
  unclassified: 'Unclassified',
  superseded: 'Superseded',
  company_policy: 'Company policy',
  company_disclosure: 'Company disclosure',
  disputed: 'Disputed',
  third_party_analysis: 'Third-party analysis',
  remediation_record: 'Remediation record',
  preliminary_regulatory_finding: 'Preliminary regulatory finding',
  final_regulatory_finding: 'Final regulatory finding',
  court_finding: 'Court finding',
};

export const RELATION_LABEL: Record<EvidenceRelation, string> = {
  supports: 'Supports',
  conflicts: 'Conflicts',
  context: 'Context',
  insufficient_to_conclude: 'Insufficient to conclude',
};

export const CONFIDENCE_LABEL: Record<KpiConfidence, string> = {
  INSUFFICIENT_EVIDENCE: 'Insufficient evidence',
  LOW: 'Low', MEDIUM: 'Medium', HIGH: 'High', VERY_HIGH: 'Very high',
};

/** A finding a regulator or court has concluded, not merely opened. */
export function isEstablishedFinding(e: KpiEvidence): boolean {
  return e.legal_status === 'final_regulatory_finding'
    || e.legal_status === 'court_finding';
}

/** True when the assessment rests on nothing that counts. */
export function isInsufficient(inv: KpiInvestigation): boolean {
  return inv.assessment.verdict === 'insufficient_evidence'
    || inv.assessment.verdict === 'not_assessed';
}
