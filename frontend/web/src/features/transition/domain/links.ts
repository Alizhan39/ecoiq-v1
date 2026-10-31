/**
 * links — how the physical model connects to governance and to evidence.
 *
 * TWO SEPARATE QUESTIONS, KEPT SEPARATE
 * -------------------------------------
 * The industrial model describes a physical system. The 114 principles are a
 * governance and evidence framework. They are linkable and they are not the
 * same thing, and this file is the only place they meet — deliberately, so
 * that "which principle does this intervention serve?" cannot leak into the
 * physics and "what does this equipment do?" cannot leak into the canon.
 *
 * DELIBERATELY EMPTY
 * ------------------
 * `PRINCIPLE_LINKS` and every `evidenceIds` array ship empty. The architecture
 * must be able to answer "why is this intervention relevant under the
 * 114-Principle framework"; populating that mapping speculatively would be
 * inventing the answer, and a principle mapping is a claim about meaning that
 * belongs to whoever owns the canon.
 *
 * The tests assert the mapping is EMPTY, not that it is populated. When
 * somebody with the authority to make those links makes them, that test is
 * the thing they update, and updating it is the moment the claim becomes
 * deliberate rather than accumulated.
 */
import type { InterventionType } from './interventions';
import type { LossType } from './entities';

/** What kind of thing an evidence record supports. */
export type EvidenceRole =
  /** That the loss is real and worth acting on. */
  | 'justifies_loss'
  /** That the intervention is an appropriate response. */
  | 'justifies_intervention'
  /** That the outcome actually occurred. The VERIFY half. */
  | 'verifies_outcome';

export interface EvidenceLink {
  /** EvidenceMemory id from the existing evidence layer. */
  evidenceId: string;
  role: EvidenceRole;
  /** What this record is being cited for, in one sentence. */
  note?: string;
}

/**
 * Principle relevance for a loss or an intervention.
 *
 * `principleId` is 1–114. `rationale` is required: a bare foreign key asserts
 * a relationship without saying what it is, and this model's whole reason for
 * separating governance from physics is that the connection has to be
 * arguable.
 */
export interface PrincipleLink {
  principleId: number;
  rationale: string;
  /** Evidence supporting the link itself, not the intervention. */
  evidenceIds: string[];
}

/**
 * Intervention → principles. EMPTY, on purpose. See the file header.
 */
export const PRINCIPLE_LINKS: Partial<Record<InterventionType, PrincipleLink[]>> = {};

/**
 * Loss → principles. EMPTY, on purpose.
 */
export const LOSS_PRINCIPLE_LINKS: Partial<Record<LossType, PrincipleLink[]>> = {};

/** Principles relevant to an intervention, or none if nobody has said. */
export function principlesFor(type: InterventionType): PrincipleLink[] {
  return PRINCIPLE_LINKS[type] ?? [];
}

export function principlesForLoss(type: LossType): PrincipleLink[] {
  return LOSS_PRINCIPLE_LINKS[type] ?? [];
}

/**
 * What a reader is told when no principle mapping exists.
 *
 * Not silence. An intervention with no principle link is a fact about EcoIQ's
 * current state — nobody has made the argument yet — and saying so is
 * different from implying the intervention has no governance relevance.
 */
export const NO_PRINCIPLE_MAPPING =
  'No principle mapping has been recorded for this yet. The link would state '
  + 'why the intervention matters under the 114-principle framework, and no '
  + 'one has made that argument.';

/** Whether the governance layer can say anything at all about this. */
export function hasGovernanceContext(type: InterventionType): boolean {
  return principlesFor(type).length > 0;
}
