/**
 * entities — the industrial system EcoIQ reasons about.
 *
 * FACILITY → PROCESS → EQUIPMENT → RESOURCE FLOW → LOSS → INTERVENTION
 *   → SCENARIO → OUTCOME → VERIFICATION
 *
 * WHAT IS AND IS NOT THE CENTRE
 * -----------------------------
 * A company may own a facility. It is a field on Facility, and nothing in this
 * file reaches back the other way: no type here is keyed by organisation, and
 * no function takes one. The physical system is the subject; ownership is
 * context. That is the whole reason this model exists separately from the
 * company assessment code.
 *
 * NO COORDINATES, NO OPACITY, NO STAGES
 * -------------------------------------
 * Deliberately. This file describes what a plant IS. Where a node is drawn and
 * when it fades in are questions about a picture, and they live in the model
 * and view layers that consume this one. The test that keeps them apart is
 * `domain has no presentation concepts` — it greps this directory, because
 * "we'll keep them separate" is not a mechanism.
 *
 * NOTHING HERE IS A MEASUREMENT
 * -----------------------------
 * Every economic and environmental figure is `Measured<Quantity>`, defaulting
 * to null. See ./unknown.ts for why that is load-bearing rather than tidy.
 */
import type { EconomicOutcome, Measured, Quantity, ResourceOutcome } from './unknown';

// ── Equipment ────────────────────────────────────────────────────────────────

/**
 * Generic industrial equipment classes.
 *
 * Deliberately vendor-neutral and deliberately coarse. "boiler" covers a fired
 * boiler of any make; the model has no opinion on whose. A vendor catalogue is
 * a different product with different obligations, and encoding one here would
 * make every intervention read as a recommendation to buy something.
 */
export type EquipmentKind =
  | 'boiler'            // fired process heat — the archetypal retrofit target
  | 'furnace'
  | 'heat_exchanger'
  | 'motor'
  | 'variable_speed_drive'
  | 'pump'
  | 'compressor'
  | 'process_unit'
  | 'grid_connection'
  | 'storage'
  | 'water_treatment'
  | 'material_recovery'
  | 'electric_heater'   // the electrified replacement for boiler/furnace
  | 'metering';         // how VERIFY becomes possible at all

export interface Equipment {
  id: string;
  label: string;
  kind: EquipmentKind;
  /** The process this equipment serves, if any. */
  processId?: string;
  /**
   * Whether this equipment exists in the baseline plant, was introduced by an
   * intervention, or is a replacement for something retired.
   */
  origin: 'baseline' | 'introduced';
  /** The equipment this one replaces, so a retrofit reads as a substitution. */
  replacesId?: string;
  /** Nameplate rating, when known. Unknown in the prototype. */
  rating: Measured<Quantity>;
}

// ── Resource flows ───────────────────────────────────────────────────────────

/**
 * What a flow carries.
 *
 * `recovered_heat` is deliberately distinct from `thermal_energy`: the whole
 * argument of a heat-recovery intervention is that a quantity which was
 * leaving the system now returns to it, and collapsing the two would erase
 * exactly the distinction the drawing is making.
 */
export type ResourceKind =
  | 'electricity'
  | 'thermal_energy'
  | 'fuel'
  | 'water'
  | 'material'
  | 'waste'
  | 'recovered_heat';

/** What is happening to a flow, independent of what it carries. */
export type FlowState =
  /** Doing useful work inside the system. */
  | 'productive'
  /** Leaving the system carrying something useful. A LossPoint sits here. */
  | 'lost'
  /** Captured on its way out and returned. */
  | 'recovered'
  /** Returned to an earlier stage of the same system — a closed loop. */
  | 'reused';

export interface ResourceFlow {
  id: string;
  kind: ResourceKind;
  /** Equipment or process id. Direction is from → to, always. */
  from: string;
  to: string;
  state: FlowState;
  /** Rate or annual quantity, when measured. Unknown in the prototype. */
  quantity: Measured<Quantity>;
}

// ── Processes and facilities ─────────────────────────────────────────────────

export interface Process {
  id: string;
  label: string;
  /** Equipment ids serving this process. */
  equipmentIds: string[];
}

export interface Facility {
  id: string;
  label: string;
  /**
   * The organisation that owns or operates the site, if known.
   *
   * A slug, not an object: this model must not import the company types, or
   * the physical system starts depending on the assessment layer and the
   * separation this file's header describes stops being real.
   */
  operatorSlug?: string;
  processes: Process[];
  equipment: Equipment[];
  flows: ResourceFlow[];
}

// ── Losses ───────────────────────────────────────────────────────────────────

/**
 * Conceptual loss categories.
 *
 * A category, not a measurement. `LossPoint.magnitude` is where a measured
 * quantity would go, and in the prototype it is null everywhere — naming a
 * loss is not the same as having quantified it, and a model that conflates
 * them would let an illustration masquerade as a survey.
 */
export type LossType =
  | 'HEAT_LOSS'
  | 'ENERGY_INEFFICIENCY'
  | 'WATER_DISCHARGE'
  | 'MATERIAL_WASTE'
  | 'IDLE_LOAD'
  | 'PROCESS_BOTTLENECK'
  | 'UNRECOVERED_RESOURCE';

export interface LossPoint {
  id: string;
  type: LossType;
  label: string;
  /** Where in the plant it occurs. */
  atEquipmentId?: string;
  atFlowId?: string;
  /** How much is being lost. UNKNOWN until a facility is surveyed. */
  magnitude: Measured<Quantity>;
  /**
   * Evidence that this loss is real.
   *
   * Empty in the prototype. When populated these are EvidenceMemory ids from
   * the existing evidence layer — the same records the 114-principle
   * investigations cite. EcoIQ has to be able to show why it believed a loss
   * existed, not just that it drew one.
   */
  evidenceIds: string[];
}

// ── Verification ─────────────────────────────────────────────────────────────

/**
 * Whether an outcome has been checked against reality.
 *
 * The states are ordered by how much is known, and the first two are the
 * honest answers for anything in this prototype. `VERIFIED` requires measured
 * post-implementation data; nothing may reach it by assertion.
 */
export type VerificationState =
  /** Nobody has looked. Not the same as "no effect found". */
  | 'NOT_VERIFIED'
  /** Implementation happened; measurement has not yet been collected. */
  | 'AWAITING_MEASUREMENT'
  /** Measured, and the outcome matches what the scenario expected. */
  | 'VERIFIED'
  /** Measured, and it does not match. Kept because this must be sayable. */
  | 'DIVERGED';

export interface Verification {
  state: VerificationState;
  /** Evidence for the measured outcome. Empty until VERIFIED or DIVERGED. */
  evidenceIds: string[];
  /** Why, in one sentence, for a reader. */
  note?: string;
}

// ── Outcomes ─────────────────────────────────────────────────────────────────

/**
 * What a scenario is expected to achieve, and later what it did.
 *
 * `expected` is qualitative in the prototype — a direction, not a number.
 * `economic` and `resource` carry the numeric slots, all null. Splitting them
 * means a scenario can express "this reduces heat loss" without implying it
 * has costed it.
 */
export interface Outcome {
  /** Qualitative direction per loss type this scenario addresses. */
  expected: QualitativeEffect[];
  economic: EconomicOutcome;
  resource: ResourceOutcome;
  verification: Verification;
}

export interface QualitativeEffect {
  lossType: LossType;
  /** The direction of the intended change. Never a magnitude. */
  direction: 'reduces' | 'eliminates' | 'recovers' | 'no_effect';
  /** One sentence a reader can check against the topology. */
  rationale: string;
}
