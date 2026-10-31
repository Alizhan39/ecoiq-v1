/**
 * systemState — what a reader is shown instead of the animation fractions.
 *
 * WHY NOT JUST SHOW THE NUMBERS
 * -----------------------------
 * The state functions return values in [0,1] that describe a drawing's model.
 * Rendered beside an industrial schematic, "0.82" or "82%" is indistinguishable
 * from a measurement, and no caption reliably survives a screenshot. So the
 * panel shows a QUALITATIVE transition — Combustion → Electrified, Lost →
 * Captured → Reused — which is the thing that is actually true, and which
 * cannot be misread as a meter reading.
 *
 * The fractions still drive the drawing. They just never reach a reader as
 * numbers outside an explicitly labelled debug mode.
 */
import {
  electrificationFraction, heatCaptureFraction, materialRecoveryFraction,
  systemIntegrationFraction, usefulHeatRecoveryFraction, waterReuseFraction,
} from '../model/state';
import { stageReached } from '../model/stages';

/** One dimension of the plant, and the states it moves through. */
export interface SystemDimension {
  key: string;
  label: string;
  /** Ordered states. Index 0 is the legacy condition. */
  states: readonly string[];
  /** Which state applies at this progress. */
  at: (progress: number) => number;
}

/**
 * A threshold, so a transition reads as done rather than as nearly done.
 *
 * 0.999 rather than 1: a stage's ramp reaches exactly 1 at its boundary, and
 * floating-point comparison at a boundary is how an off-by-one-frame flicker
 * gets into a scroll animation.
 */
const DONE = 0.999;

export const DIMENSIONS: readonly SystemDimension[] = [
  {
    key: 'process_heat',
    label: 'Process heat',
    states: ['Combustion', 'Electrified'],
    at: (p) => (electrificationFraction(p) >= DONE ? 1 : 0),
  },
  {
    key: 'heat',
    label: 'Heat',
    states: ['Lost', 'Captured', 'Reused'],
    at: (p) => {
      if (usefulHeatRecoveryFraction(p) >= DONE) return 2;
      if (heatCaptureFraction(p) > 0) return 1;
      return 0;
    },
  },
  {
    key: 'water',
    label: 'Water',
    states: ['Discharged', 'Treated', 'Reused'],
    at: (p) => {
      if (waterReuseFraction(p) >= DONE) return 2;
      if (waterReuseFraction(p) > 0) return 1;
      return 0;
    },
  },
  {
    key: 'materials',
    label: 'Materials',
    states: ['Waste', 'Recovered'],
    at: (p) => (materialRecoveryFraction(p) >= DONE ? 1 : 0),
  },
  {
    key: 'motor_control',
    label: 'Motor control',
    states: ['Fixed-speed', 'Variable-speed'],
    at: (p) => (stageReached(p, 'electrify') ? 1 : 0),
  },
  {
    key: 'verification',
    label: 'Verification',
    states: ['Absent', 'Metered'],
    at: (p) => (systemIntegrationFraction(p) >= DONE ? 1 : 0),
  },
] as const;

export interface DimensionReading {
  key: string;
  label: string;
  /** The state the plant is in now. */
  state: string;
  /** Every state, so a reader sees the journey and not just the position. */
  states: readonly string[];
  index: number;
  /** Has this dimension finished moving? */
  complete: boolean;
}

export function systemStateAt(progress: number): DimensionReading[] {
  return DIMENSIONS.map((d) => {
    const index = d.at(progress);
    return {
      key: d.key,
      label: d.label,
      state: d.states[index] ?? d.states[0]!,
      states: d.states,
      index,
      complete: index === d.states.length - 1,
    };
  });
}

/**
 * What the plant's emissions did.
 *
 * ELECTRIFICATION IS NOT DECARBONISATION
 * --------------------------------------
 * Replacing a fired heater with an electric one moves the emissions to
 * whoever generates the electricity. Whether that is an improvement depends
 * entirely on the grid's carbon intensity at the times the plant draws power —
 * a fact about somebody else's system, which this model does not have and must
 * not assume.
 *
 * So the answer is UNKNOWN, permanently, until electricity-source data exists.
 * Not "reduced", not "improved", and not omitted — omitting it would let a
 * reader supply the optimistic answer themselves, which is the same failure
 * with an extra step.
 */
export const EMISSIONS_STATE = {
  label: 'Emissions',
  state: 'Unknown',
  explanation:
    'Electrification moves combustion off the site; it does not by itself '
    + 'reduce emissions. Whether it does depends on the carbon intensity of '
    + 'the electricity at the times this plant draws it, which is a fact about '
    + 'the grid, not about the plant. EcoIQ holds no electricity-source data '
    + 'here, so the emissions effect is unknown rather than assumed.',
} as const;

/** Label required wherever a raw [0,1] value is displayed at all. */
export const DEBUG_STATE_LABEL =
  'Illustrative animation state — not measured facility performance.';
