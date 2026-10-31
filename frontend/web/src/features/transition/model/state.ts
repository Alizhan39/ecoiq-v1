/**
 * state — the transition model's six state functions.
 *
 * WHAT THESE NUMBERS ARE
 * ----------------------
 * They describe A DRAWING'S MODEL of an industrial transition. They are not
 * measurements, not estimates, and not derived from any facility. A reader is
 * never shown them as a percentage of anything real, and `assertNotPresentable`
 * exists so that stays true when someone later reaches for one to fill a
 * dashboard tile.
 *
 * The distinction matters more here than almost anywhere else in this codebase.
 * "Heat loss is down 80%" is exactly the sentence EcoIQ must never produce
 * without a metered plant behind it, and a function called
 * `heatLossFraction()` returning 0.2 is one careless template away from
 * producing it.
 *
 * WHY THEY ARE DERIVED, NOT AUTHORED
 * ----------------------------------
 * Each function is computed from the SAME stage boundaries that drive the
 * topology. So the number and the picture cannot disagree: if an edge that
 * carries loss retires at the recover stage, heatLossFraction falls across
 * exactly that interval, because both read `STAGES`. Hand-tuned curves would
 * drift from the drawing the first time a stage moved.
 *
 * SHARED CONTRACT
 * ---------------
 * Every function in this file:
 *   - accepts any number and clamps its input to [0, 1];
 *   - returns a value in [0, 1];
 *   - is deterministic — same input, same output, no clock, no randomness;
 *   - is monotonic in the direction declared in MONOTONICITY below.
 * All four properties are enforced by tests over the whole catalogue, so a
 * seventh function added later inherits them or fails.
 */
import { STAGES, clampProgress, ramp, stageProgress } from './stages';

/** A state function: progress in, fraction out. */
export type StateFunction = (progress: number) => number;

/**
 * Heat leaving the system unrecovered, as a fraction of the heat the legacy
 * plant loses.
 *
 * 1 means the legacy plant's full thermal loss. 0 means none of that loss
 * still leaves the system — because electrification removed the fired heat's
 * flue loss, and recovery captured what the process rejects.
 *
 * Falls in two steps, not one, because two different interventions act on it:
 * ELECTRIFY removes the combustion loss, RECOVER captures the process loss.
 * A single smooth ramp would imply one cause.
 */
export function heatLossFraction(progress: number): number {
  const p = clampProgress(progress);
  const combustionLossRemoved = stageProgress(p, 'electrify');
  const processLossRecovered = stageProgress(p, 'recover');
  // The two halves of the legacy loss, weighted equally: the model does not
  // know a real split and must not imply one.
  return 1 - 0.5 * combustionLossRemoved - 0.5 * processLossRecovered;
}

/**
 * Heat CAPTURED at the exchanger, as a fraction of the heat the process
 * rejects.
 *
 * Capture is not recovery. A heat exchanger takes heat out of a stream that
 * was leaving; whether that heat then does any work depends entirely on
 * whether something needs it when it is available. This function answers only
 * the first question, and it is the honest thing to report during RECOVER —
 * at which point the plant has an exchanger and nowhere to send its output.
 */
export function heatCaptureFraction(progress: number): number {
  return stageProgress(clampProgress(progress), 'recover');
}

/**
 * Heat captured AND delivered to a useful sink, as a fraction of the heat the
 * process rejects.
 *
 * THE DISTINCTION THIS FUNCTION EXISTS FOR
 * ----------------------------------------
 * These were one function, `heatRecoveryFraction`, weighted half on capture
 * and half on the return path. That average was defensible as animation
 * pacing and wrong as engineering: it reported 50% "recovery" for a plant with
 * an exchanger and no sink, which is not partial recovery — it is a captured
 * stream going nowhere. Heat with no demand and no store is not recovered, and
 * a model that scores it as half-recovered teaches the reader the wrong thing
 * about the most common way retrofits underdeliver.
 *
 * So: bounded by capture (you cannot deliver what you did not take) and gated
 * on the sink existing — the thermal store and the return path that CIRCULARISE
 * installs.
 */
export function usefulHeatRecoveryFraction(progress: number): number {
  const p = clampProgress(progress);
  const captured = heatCaptureFraction(p);
  const sinkAvailable = stageProgress(p, 'circularise');
  return Math.min(captured, sinkAvailable);
}

/**
 * Process water returned to the process rather than discharged, as a fraction
 * of the water the legacy plant discharges.
 *
 * Rises across CIRCULARISE only. Treatment without a return path is not reuse,
 * and the model refuses to credit it as such.
 */
export function waterReuseFraction(progress: number): number {
  return stageProgress(clampProgress(progress), 'circularise');
}

/**
 * Material re-entering the process as feedstock, as a fraction of the legacy
 * waste stream.
 *
 * Rises across CIRCULARISE. Reaches 1 only at the end of that stage — the
 * model does not claim a plant recovers everything, it claims the drawing's
 * waste stream has been fully replaced by a recovery loop.
 */
export function materialRecoveryFraction(progress: number): number {
  return stageProgress(clampProgress(progress), 'circularise');
}

/**
 * Process heat supplied by electricity rather than combustion.
 *
 * 0 in the legacy plant (all fired), 1 once the electric heater has replaced
 * the boiler. Rises across ELECTRIFY only, because that is the single
 * intervention that changes where the heat comes from.
 */
export function electrificationFraction(progress: number): number {
  return stageProgress(clampProgress(progress), 'electrify');
}

/**
 * How much of the plant is operated as one coordinated system rather than as
 * independent units.
 *
 * The only function that spans the whole scroll, because integration is
 * cumulative: each intervention adds a part that has to be coordinated, and
 * OPTIMISE is where the coordination itself is installed. Rises slowly from
 * RETROFIT and completes at the end of OPTIMISE.
 */
export function systemIntegrationFraction(progress: number): number {
  const p = clampProgress(progress);
  const retrofitStart = STAGES.find((s) => s.key === 'retrofit')!.from;
  const optimiseEnd = STAGES.find((s) => s.key === 'optimise')!.to;
  return ramp(p, retrofitStart, optimiseEnd);
}

// ── The catalogue, so tests and the semantic layer share one list ───────────

export type StateFunctionKey =
  | 'heatLossFraction'
  | 'heatCaptureFraction'
  | 'usefulHeatRecoveryFraction'
  | 'waterReuseFraction'
  | 'materialRecoveryFraction'
  | 'electrificationFraction'
  | 'systemIntegrationFraction';

export type Monotonicity = 'increasing' | 'decreasing';

export interface StateFunctionSpec {
  key: StateFunctionKey;
  fn: StateFunction;
  /** What the number means, in one sentence, for a reader. */
  semantics: string;
  /**
   * Which way it must move as progress increases.
   *
   * Declared as DATA so the monotonicity test iterates the catalogue rather
   * than naming functions one by one — a seventh function inherits the check
   * by existing.
   */
  monotonicity: Monotonicity;
  /** Expected value at progress 0 and 1, so the ends are pinned too. */
  atZero: number;
  atOne: number;
}

export const STATE_FUNCTIONS: readonly StateFunctionSpec[] = [
  {
    key: 'heatLossFraction',
    fn: heatLossFraction,
    semantics:
      'Share of the legacy plant’s thermal loss that still leaves the system.',
    monotonicity: 'decreasing',
    atZero: 1,
    atOne: 0,
  },
  {
    key: 'heatCaptureFraction',
    fn: heatCaptureFraction,
    semantics:
      'Share of rejected process heat taken out of the stream by an exchanger. '
      + 'Capture only — says nothing about whether the heat is then used.',
    monotonicity: 'increasing',
    atZero: 0,
    atOne: 1,
  },
  {
    key: 'usefulHeatRecoveryFraction',
    fn: usefulHeatRecoveryFraction,
    semantics:
      'Share of rejected process heat that is captured AND delivered to a sink '
      + 'that needs it. Heat with nowhere to go is not recovered.',
    monotonicity: 'increasing',
    atZero: 0,
    atOne: 1,
  },
  {
    key: 'waterReuseFraction',
    fn: waterReuseFraction,
    semantics:
      'Share of process water returned to the process rather than discharged.',
    monotonicity: 'increasing',
    atZero: 0,
    atOne: 1,
  },
  {
    key: 'materialRecoveryFraction',
    fn: materialRecoveryFraction,
    semantics:
      'Share of the legacy waste stream re-entering the process as feedstock.',
    monotonicity: 'increasing',
    atZero: 0,
    atOne: 1,
  },
  {
    key: 'electrificationFraction',
    fn: electrificationFraction,
    semantics:
      'Share of process heat supplied by electricity rather than combustion.',
    monotonicity: 'increasing',
    atZero: 0,
    atOne: 1,
  },
  {
    key: 'systemIntegrationFraction',
    fn: systemIntegrationFraction,
    semantics:
      'How much of the plant is operated as one coordinated system rather '
      + 'than as independent units.',
    monotonicity: 'increasing',
    atZero: 0,
    atOne: 1,
  },
] as const;

/**
 * The sentence that must accompany any of these values wherever they appear.
 *
 * Exported so the semantic layer cannot render a state value without also
 * having the disclaimer to hand — a caller that wants the number has already
 * imported the reason it is not a measurement.
 */
export const MODEL_STATE_DISCLAIMER =
  'Values describe this illustration’s model of a modernisation sequence. '
  + 'They are not measurements of any facility, and EcoIQ holds no metered '
  + 'data behind them.';

/**
 * Guard for the boundary these values must never cross.
 *
 * Call it wherever a state value would otherwise reach a surface that presents
 * facility performance. It throws, loudly, because the failure it prevents —
 * an illustration rendered as a finding — is one this codebase has already
 * had to fix twice, in the ML cluster label and the harm-signal thresholds.
 */
export function assertNotPresentedAsMeasurement(context: string): never {
  throw new Error(
    `Refusing to present a transition model value as a measurement (${context}). `
    + MODEL_STATE_DISCLAIMER,
  );
}
