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

/**
 * Stages come from model/stages.ts, not from a second list here.
 *
 * They used to be declared in this file, seven of them, while the semantic
 * narrative declared eight. Two lists describing the same sequence is how the
 * words beside a picture start disagreeing with the picture — the exact defect
 * class the burn-down spent a day removing from companies/visibility.py, where
 * one status list had been copied into six files and every copy had gone
 * stale. Re-exported rather than re-declared so there is one.
 */
import { ramp, stageAt } from './model/stages';

export { STAGES, stageProgress, ramp as span } from './model/stages';
export type { Stage, StageKey } from './model/stages';

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

/**
 * The stage a given progress sits in.
 *
 * Kept as a named export because the scene and its tests use it; it delegates
 * to the shared model rather than reimplementing the lookup.
 */
export { stageAt as currentStage, FINAL_STAGE } from './model/stages';

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
  { id: 'boiler', label: 'Fired process heat', x: 0.26, y: 0.16, kind: 'thermal', appearsAt: 0, retiredAt: 0.50 },
  { id: 'motor', label: 'Fixed-speed motor', x: 0.26, y: 0.62, kind: 'motor', appearsAt: 0, retiredAt: 0.36 },
  { id: 'water', label: 'Water system', x: 0.44, y: 0.80, kind: 'water', appearsAt: 0 },
  { id: 'waste', label: 'Waste stream', x: 0.80, y: 0.72, kind: 'process', appearsAt: 0, retiredAt: 0.78 },
  { id: 'output', label: 'Product output', x: 0.86, y: 0.42, kind: 'process', appearsAt: 0 },

  // Modernised equipment. Each appears where its predecessor retires.
  { id: 'drive', label: 'Variable-speed drive', x: 0.26, y: 0.62, kind: 'motor', appearsAt: 0.32 },
  { id: 'exchanger', label: 'Heat recovery', x: 0.62, y: 0.16, kind: 'recovery', appearsAt: 0.60 },
  { id: 'electricHeat', label: 'Electrified process heat', x: 0.26, y: 0.16, kind: 'thermal', appearsAt: 0.48 },
  { id: 'store', label: 'Thermal store', x: 0.44, y: 0.06, kind: 'store', appearsAt: 0.64 },
  { id: 'recovery', label: 'Material recovery', x: 0.80, y: 0.72, kind: 'recovery', appearsAt: 0.74 },
  { id: 'measure', label: 'Measurement', x: 0.62, y: 0.92, kind: 'measure', appearsAt: 0.86 },
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
  { id: 'grid-boiler', from: 'grid', to: 'boiler', kind: 'electricity', appearsAt: 0, retiredAt: 0.50 },
  { id: 'grid-motor', from: 'grid', to: 'motor', kind: 'electricity', appearsAt: 0, retiredAt: 0.36 },
  { id: 'boiler-process', from: 'boiler', to: 'process', kind: 'heat', appearsAt: 0, retiredAt: 0.50 },
  { id: 'motor-process', from: 'motor', to: 'process', kind: 'electricity', appearsAt: 0, retiredAt: 0.36 },
  { id: 'water-process', from: 'water', to: 'process', kind: 'water', appearsAt: 0 },
  { id: 'process-output', from: 'process', to: 'output', kind: 'material', appearsAt: 0 },
  { id: 'process-waste', from: 'process', to: 'waste', kind: 'waste', appearsAt: 0, retiredAt: 0.78 },

  // Losses in the legacy system. These do not move — they leave.
  { id: 'loss-heat', from: 'boiler', to: 'boiler', kind: 'heat', appearsAt: 0, retiredAt: 0.50, loss: true },
  { id: 'loss-process', from: 'process', to: 'process', kind: 'heat', appearsAt: 0, retiredAt: 0.62, loss: true },
  { id: 'loss-water', from: 'water', to: 'water', kind: 'water', appearsAt: 0, retiredAt: 0.76, loss: true },

  // Retrofit: the lost heat becomes recovered heat, returned to the process.
  { id: 'process-exchanger', from: 'process', to: 'exchanger', kind: 'heat', appearsAt: 0.60 },
  { id: 'exchanger-process', from: 'exchanger', to: 'process', kind: 'heat', appearsAt: 0.72, bow: -0.22 },

  // Electrify.
  { id: 'grid-electricHeat', from: 'grid', to: 'electricHeat', kind: 'electricity', appearsAt: 0.48 },
  { id: 'electricHeat-process', from: 'electricHeat', to: 'process', kind: 'heat', appearsAt: 0.48 },
  { id: 'grid-drive', from: 'grid', to: 'drive', kind: 'electricity', appearsAt: 0.32 },
  { id: 'drive-process', from: 'drive', to: 'process', kind: 'electricity', appearsAt: 0.32 },
  { id: 'store-electricHeat', from: 'store', to: 'electricHeat', kind: 'heat', appearsAt: 0.72, bow: 0.18 },
  { id: 'exchanger-store', from: 'exchanger', to: 'store', kind: 'heat', appearsAt: 0.64 },

  // Circularity: waste becomes recovery, and both material and water return.
  { id: 'process-recovery', from: 'process', to: 'recovery', kind: 'material', appearsAt: 0.74 },
  { id: 'recovery-process', from: 'recovery', to: 'process', kind: 'material', appearsAt: 0.76, bow: 0.28 },
  { id: 'process-water', from: 'process', to: 'water', kind: 'water', appearsAt: 0.76, bow: 0.24 },

  // Verify. Evidence is the one flow that leaves and does not come back —
  // it is the record, not a resource.
  { id: 'process-measure', from: 'process', to: 'measure', kind: 'evidence', appearsAt: 0.86 },
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
    : ramp(progress, item.appearsAt, item.appearsAt + FADE);
  if (item.retiredAt === undefined) return inward;
  const outward = 1 - ramp(progress, item.retiredAt, item.retiredAt + FADE);
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
  return { nodes, edges, stage: stageAt(clamped) };
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
