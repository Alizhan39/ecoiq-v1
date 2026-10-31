/**
 * stages — the eight steps of the modernisation narrative.
 *
 * These are the SEMANTIC stages. Each has a name, a plain-language meaning and
 * a closed interval of scroll progress, and the accessible narrative and the
 * drawing are both derived from this one list — which is what stops the words
 * on the page and the picture beside them from describing different things.
 *
 * WHY EIGHT AND NOT SEVEN
 * -----------------------
 * The earlier prototype folded RECOVER into CIRCULARISE. They are different
 * engineering acts: recovery captures a resource on its way out, and
 * circularisation returns it to a useful input. A plant can do the first
 * without the second — captured heat with nowhere to go is a common and real
 * failure — so collapsing them hides the step where most retrofits stall.
 */

export interface Stage {
  key: StageKey;
  /** Short label, used as the heading in the semantic layer. */
  label: string;
  /** What this step actually does, for a reader who cannot see the drawing. */
  meaning: string;
  /** Closed-open interval of progress: [from, to). The last one includes 1. */
  from: number;
  to: number;
}

export type StageKey =
  | 'legacy'
  | 'diagnose'
  | 'retrofit'
  | 'electrify'
  | 'recover'
  | 'circularise'
  | 'optimise'
  | 'verify';

export const STAGES: readonly Stage[] = [
  {
    key: 'legacy',
    label: 'Legacy system',
    meaning:
      'The plant as it runs today: fired process heat, a fixed-speed motor, '
      + 'water discharged after use, and a waste stream leaving the site. '
      + 'Heat, water and material all leave carrying something useful.',
    from: 0,
    to: 0.13,
  },
  {
    key: 'diagnose',
    label: 'Diagnose',
    meaning:
      'Identify where energy, heat, water and material are lost, and which '
      + 'losses are large enough to be worth acting on. Nothing is changed at '
      + 'this step — it establishes what is true.',
    from: 0.13,
    to: 0.28,
  },
  {
    key: 'retrofit',
    label: 'Retrofit',
    meaning:
      'Modify existing equipment before replacing it. A variable-speed drive '
      + 'matches motor output to demand instead of running flat out and '
      + 'throttling the difference away.',
    from: 0.28,
    to: 0.44,
  },
  {
    key: 'electrify',
    label: 'Electrify',
    meaning:
      'Replace fired process heat with electric heat drawn from the grid '
      + 'connection. The fuel flow into the plant is removed rather than '
      + 'reduced.',
    from: 0.44,
    to: 0.58,
  },
  {
    key: 'recover',
    label: 'Recover',
    meaning:
      'Capture resources on their way out. A heat exchanger takes heat that '
      + 'was leaving the process, and a thermal store holds it so supply and '
      + 'demand need not coincide.',
    from: 0.58,
    to: 0.70,
  },
  {
    key: 'circularise',
    label: 'Circularise',
    meaning:
      'Return what was captured to a useful input. Treated water goes back to '
      + 'the process, recovered material re-enters as feedstock, and stored '
      + 'heat supplies the heater. Capture without a return is not a loop.',
    from: 0.70,
    to: 0.84,
  },
  {
    key: 'optimise',
    label: 'Optimise',
    meaning:
      'Coordinate the equipment that now exists — sequencing, setpoints and '
      + 'load balancing — so the parts run as one system rather than '
      + 'independently.',
    from: 0.84,
    to: 0.93,
  },
  {
    key: 'verify',
    label: 'Verify',
    meaning:
      'Meter the result and compare it with what the scenario expected. '
      + 'Until this step produces measured data, every figure about the '
      + 'outcome is unknown rather than zero.',
    from: 0.93,
    to: 1,
  },
] as const;

export const FIRST_STAGE = STAGES[0] as Stage;
export const FINAL_STAGE = STAGES[STAGES.length - 1] as Stage;

/** Clamp to the domain every function in this model accepts. */
export function clampProgress(progress: number): number {
  if (!Number.isFinite(progress)) return 0;
  return Math.min(1, Math.max(0, progress));
}

/**
 * Linear ramp from `from` to `to`, clamped at both ends.
 *
 * The one piece of arithmetic the whole model needs. A degenerate range
 * returns a step rather than dividing by zero.
 */
export function ramp(value: number, from: number, to: number): number {
  if (to <= from) return value >= to ? 1 : 0;
  return Math.min(1, Math.max(0, (value - from) / (to - from)));
}

/** The stage a given progress sits in. Always exactly one. */
export function stageAt(progress: number): Stage {
  const p = clampProgress(progress);
  return STAGES.find((s) => p < s.to) ?? FINAL_STAGE;
}

/** How far through a named stage the progress currently is, 0 to 1. */
export function stageProgress(progress: number, key: StageKey): number {
  const stage = STAGES.find((s) => s.key === key);
  if (!stage) return 0;
  return ramp(clampProgress(progress), stage.from, stage.to);
}

/** Has this stage been reached at all? */
export function stageReached(progress: number, key: StageKey): boolean {
  const stage = STAGES.find((s) => s.key === key);
  return stage ? clampProgress(progress) >= stage.from : false;
}
