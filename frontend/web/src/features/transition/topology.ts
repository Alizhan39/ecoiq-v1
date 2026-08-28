/**
 * topology — the industrial system, and how it changes as you scroll.
 *
 * WHAT THIS DESCRIBES, AND WHAT IT DOES NOT CLAIM
 * -----------------------------------------------
 * A schematic of industrial modernisation: grid, process heat, motors, water,
 * materials, waste. It is a drawing of what a transition looks like, not a
 * picture of anything EcoIQ operates.
 *
 * Nothing here is labelled as a sensor, a live feed, an agent, or anything
 * under EcoIQ's control. `platform_registry/agents.py` states plainly that
 * EcoIQ has no PRODUCTION AI agents and no sensor ingestion, and the same
 * discipline that stopped the stashed cinematic hero from drawing robot arms
 * applies here: a claim made in pictures is still a claim.
 *
 * DETERMINISTIC BY CONSTRUCTION
 * -----------------------------
 * Every value is a pure function of `progress`. No elapsed time, no timer, no
 * randomness that is not seeded. The same scroll offset always produces the
 * same frame, which is what lets a test assert one still frame instead of
 * chasing a moving target — the property `pipelinePainter` established and the
 * reason its canvas needs no requestAnimationFrame loop.
 *
 * THE TOPOLOGY ITSELF IMPROVES
 * ----------------------------
 * The system does not merely recolour. Edges that carry loss are removed,
 * loops close, and lost flows become recovered flows. A reader watching should
 * be able to see the engineering reasoning, not a palette change.
 */

/** Scroll stages, each a closed interval of progress. */
export const STAGES = [
  { key: 'legacy', label: 'Legacy system', from: 0, to: 0.15 },
  { key: 'diagnose', label: 'Diagnose', from: 0.15, to: 0.30 },
  { key: 'retrofit', label: 'Retrofit', from: 0.30, to: 0.48 },
  { key: 'electrify', label: 'Electrify', from: 0.48, to: 0.64 },
  { key: 'circularity', label: 'Close the loops', from: 0.64, to: 0.78 },
  { key: 'optimise', label: 'Optimise', from: 0.78, to: 0.90 },
  { key: 'verify', label: 'Measure, verify, learn', from: 0.90, to: 1 },
] as const;

export type StageKey = (typeof STAGES)[number]['key'];

/** What a flow carries. Never distinguished by colour alone — see the painter. */
export type FlowKind =
  | 'electricity' | 'heat' | 'water' | 'material' | 'waste' | 'evidence';

export interface Node {
  id: string;
  label: string;
  /** Schematic position in a unit square; the painter scales it. */
  x: number;
  y: number;
  kind: 'grid' | 'process' | 'thermal' | 'motor' | 'water' | 'store' | 'recovery' | 'measure';
  /** Progress at which this node exists. Below it, the node is not drawn. */
  appearsAt: number;
  /** Progress at which it is replaced. Above it, the node fades out. */
  retiredAt?: number;
}

export interface Edge {
  id: string;
  from: string;
  to: string;
  kind: FlowKind;
  appearsAt: number;
  retiredAt?: number;
  /** A loss edge leaves the system carrying something useful. */
  loss?: boolean;
  /** Curvature for return loops, so recovery reads as a loop, not a line. */
  bow?: number;
}

/** Linear map with clamping. The one piece of arithmetic the scene needs. */
export function span(value: number, from: number, to: number): number {
  if (to <= from) return value >= to ? 1 : 0;
  return Math.min(1, Math.max(0, (value - from) / (to - from)));
}

/** How far through a named stage the scroll currently is, 0 to 1. */
export function stageProgress(progress: number, key: StageKey): number {
  const stage = STAGES.find((s) => s.key === key);
  if (!stage) return 0;
  return span(progress, stage.from, stage.to);
}

/**
 * The stage a given progress sits in. Always exactly one.
 *
 * The final stage is named explicitly rather than indexed from the end so the
 * return type is a stage, not `stage | undefined` — an "impossible" undefined
 * that every caller then has to handle is worse than saying which stage
 * catches progress of exactly 1.
 */
export const FINAL_STAGE = STAGES[STAGES.length - 1] as (typeof STAGES)[number];

export function currentStage(progress: number): (typeof STAGES)[number] {
  const clamped = Math.min(1, Math.max(0, progress));
  return STAGES.find((s) => clamped < s.to) ?? FINAL_STAGE;
}

/**
 * The nodes.
 *
 * Legacy equipment carries `retiredAt`; its replacement carries a matching
 * `appearsAt`, so a retrofit reads as one thing becoming another rather than
 * as a crossfade between unrelated shapes.
 */
export const NODES: Node[] = [
  { id: 'grid', label: 'Grid connection', x: 0.08, y: 0.30, kind: 'grid', appearsAt: 0 },
  { id: 'process', label: 'Industrial process', x: 0.44, y: 0.42, kind: 'process', appearsAt: 0 },
  { id: 'boiler', label: 'Fired process heat', x: 0.26, y: 0.16, kind: 'thermal', appearsAt: 0, retiredAt: 0.56 },
  { id: 'motor', label: 'Fixed-speed motor', x: 0.26, y: 0.62, kind: 'motor', appearsAt: 0, retiredAt: 0.42 },
  { id: 'water', label: 'Water system', x: 0.44, y: 0.80, kind: 'water', appearsAt: 0 },
  { id: 'waste', label: 'Waste stream', x: 0.80, y: 0.72, kind: 'process', appearsAt: 0, retiredAt: 0.74 },
  { id: 'output', label: 'Product output', x: 0.86, y: 0.42, kind: 'process', appearsAt: 0 },

  // Modernised equipment. Each appears where its predecessor retires.
  { id: 'drive', label: 'Variable-speed drive', x: 0.26, y: 0.62, kind: 'motor', appearsAt: 0.36 },
  { id: 'exchanger', label: 'Heat recovery', x: 0.62, y: 0.16, kind: 'recovery', appearsAt: 0.32 },
  { id: 'electricHeat', label: 'Electrified process heat', x: 0.26, y: 0.16, kind: 'thermal', appearsAt: 0.52 },
  { id: 'store', label: 'Thermal store', x: 0.44, y: 0.06, kind: 'store', appearsAt: 0.56 },
  { id: 'recovery', label: 'Material recovery', x: 0.80, y: 0.72, kind: 'recovery', appearsAt: 0.68 },
  { id: 'measure', label: 'Measurement', x: 0.62, y: 0.92, kind: 'measure', appearsAt: 0.88 },
];

/**
 * The edges.
 *
 * The legacy system leaks: heat leaves at the top, material leaves as waste,
 * water leaves the loop. Each of those `loss` edges retires and is replaced by
 * a recovery edge that returns the same quantity to the system. That
 * substitution is the whole argument the drawing makes.
 */
export const EDGES: Edge[] = [
  { id: 'grid-boiler', from: 'grid', to: 'boiler', kind: 'electricity', appearsAt: 0, retiredAt: 0.56 },
  { id: 'grid-motor', from: 'grid', to: 'motor', kind: 'electricity', appearsAt: 0, retiredAt: 0.42 },
  { id: 'boiler-process', from: 'boiler', to: 'process', kind: 'heat', appearsAt: 0, retiredAt: 0.56 },
  { id: 'motor-process', from: 'motor', to: 'process', kind: 'electricity', appearsAt: 0, retiredAt: 0.42 },
  { id: 'water-process', from: 'water', to: 'process', kind: 'water', appearsAt: 0 },
  { id: 'process-output', from: 'process', to: 'output', kind: 'material', appearsAt: 0 },
  { id: 'process-waste', from: 'process', to: 'waste', kind: 'waste', appearsAt: 0, retiredAt: 0.74 },

  // Losses in the legacy system. These do not move — they leave.
  { id: 'loss-heat', from: 'boiler', to: 'boiler', kind: 'heat', appearsAt: 0, retiredAt: 0.34, loss: true },
  { id: 'loss-process', from: 'process', to: 'process', kind: 'heat', appearsAt: 0, retiredAt: 0.34, loss: true },
  { id: 'loss-water', from: 'water', to: 'water', kind: 'water', appearsAt: 0, retiredAt: 0.70, loss: true },

  // Retrofit: the lost heat becomes recovered heat, returned to the process.
  { id: 'process-exchanger', from: 'process', to: 'exchanger', kind: 'heat', appearsAt: 0.32 },
  { id: 'exchanger-process', from: 'exchanger', to: 'process', kind: 'heat', appearsAt: 0.36, bow: -0.22 },

  // Electrify.
  { id: 'grid-electricHeat', from: 'grid', to: 'electricHeat', kind: 'electricity', appearsAt: 0.52 },
  { id: 'electricHeat-process', from: 'electricHeat', to: 'process', kind: 'heat', appearsAt: 0.52 },
  { id: 'grid-drive', from: 'grid', to: 'drive', kind: 'electricity', appearsAt: 0.36 },
  { id: 'drive-process', from: 'drive', to: 'process', kind: 'electricity', appearsAt: 0.36 },
  { id: 'store-electricHeat', from: 'store', to: 'electricHeat', kind: 'heat', appearsAt: 0.58, bow: 0.18 },
  { id: 'exchanger-store', from: 'exchanger', to: 'store', kind: 'heat', appearsAt: 0.58 },

  // Circularity: waste becomes recovery, and both material and water return.
  { id: 'process-recovery', from: 'process', to: 'recovery', kind: 'material', appearsAt: 0.68 },
  { id: 'recovery-process', from: 'recovery', to: 'process', kind: 'material', appearsAt: 0.70, bow: 0.28 },
  { id: 'process-water', from: 'process', to: 'water', kind: 'water', appearsAt: 0.70, bow: 0.24 },

  // Verify. Evidence is the one flow that leaves and does not come back —
  // it is the record, not a resource.
  { id: 'process-measure', from: 'process', to: 'measure', kind: 'evidence', appearsAt: 0.88 },
  { id: 'recovery-measure', from: 'recovery', to: 'measure', kind: 'evidence', appearsAt: 0.90 },
];

/**
 * Opacity for something that appears and may later retire.
 *
 * Anything with `appearsAt === 0` is present at progress 0 rather than fading
 * in from nothing. Without that, the legacy system's losses were invisible on
 * the first frame and `recoveredFraction` reported a fully recovered plant at
 * the exact moment it should have shown maximum loss — the opposite of the
 * argument the drawing makes. Caught by the monotonicity test.
 */
export function presence(item: { appearsAt: number; retiredAt?: number },
                         progress: number): number {
  const FADE = 0.06;
  const inward = item.appearsAt <= 0
    ? 1
    : span(progress, item.appearsAt, item.appearsAt + FADE);
  if (item.retiredAt === undefined) return inward;
  const outward = 1 - span(progress, item.retiredAt, item.retiredAt + FADE);
  return Math.min(inward, outward);
}

/** Nodes and edges visible at a given progress, with their opacities. */
export function sceneAt(progress: number) {
  const clamped = Math.min(1, Math.max(0, progress));
  const nodes = NODES
    .map((n) => ({ node: n, opacity: presence(n, clamped) }))
    .filter((n) => n.opacity > 0.001);
  const edges = EDGES
    .map((e) => ({ edge: e, opacity: presence(e, clamped) }))
    .filter((e) => e.opacity > 0.001);
  return { nodes, edges, stage: currentStage(clamped) };
}

/**
 * How much of the system's throughput is recovered rather than lost.
 *
 * Reported so the drawing can be checked against a number rather than a
 * feeling — and deliberately NOT presented as a measurement of any real plant.
 */
export function recoveredFraction(progress: number): number {
  const clamped = Math.min(1, Math.max(0, progress));
  const losses = EDGES.filter((e) => e.loss);
  const stillLost = losses.filter((e) => presence(e, clamped) > 0.5).length;
  return losses.length === 0 ? 1 : 1 - stillLost / losses.length;
}
