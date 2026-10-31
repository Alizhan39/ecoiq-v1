import { EDGES, NODES, presence, type Edge, type FlowKind } from './topology';

/**
 * flowPainter — what moves through the industrial schematic.
 *
 * SAME CONTRACT AS pipelinePainter
 * --------------------------------
 * Pure paint functions, framework-agnostic, no DOM. A pulse's position comes
 * from `(seed, progress)` and never from elapsed milliseconds, so the canvas
 * host needs no requestAnimationFrame loop and no timer: it repaints when
 * scroll progress changes and does nothing at all when the section is off
 * screen.
 *
 * That is what makes this testable. Snap to a progress value, read one still
 * frame, assert it. A time-driven version could only be sampled and hoped at.
 *
 * SVG DRAWS THE STRUCTURE, CANVAS DRAWS THE MOTION
 * ------------------------------------------------
 * Equipment, pipes, labels and topology are SVG in the scene component: they
 * are few, they need text, and they benefit from being real elements. Pulses
 * are many and move, so they live here. Hundreds of animated DOM nodes is the
 * thing this split exists to avoid.
 *
 * NEVER COLOUR ALONE
 * ------------------
 * Each flow kind carries a dash pattern and a stroke width as well as a hue,
 * so the six kinds stay distinguishable without colour vision — the same rule
 * the matrix follows for evidence states.
 */

export interface FlowStyle {
  /** Dash pattern in device-independent px. Empty means solid. */
  dash: number[];
  width: number;
  /** Pulse shape: a square reads as discrete material, a bar as continuous. */
  pulse: 'square' | 'bar' | 'dot';
  speed: number;
}

export const FLOW_STYLE: Record<FlowKind, FlowStyle> = {
  electricity: { dash: [], width: 1.6, pulse: 'bar', speed: 1.35 },
  heat: { dash: [6, 4], width: 2.0, pulse: 'dot', speed: 0.85 },
  water: { dash: [2, 3], width: 1.4, pulse: 'dot', speed: 0.7 },
  material: { dash: [10, 3], width: 2.2, pulse: 'square', speed: 0.55 },
  waste: { dash: [1, 5], width: 1.4, pulse: 'square', speed: 0.5 },
  evidence: { dash: [4, 3, 1, 3], width: 1.2, pulse: 'dot', speed: 1.0 },
  // Fuel: the heaviest dash in the set. It is the flow the whole exercise
  // exists to remove, so it must read as substantial before it goes.
  fuel: { dash: [12, 4], width: 2.4, pulse: 'square', speed: 0.45 },
};

export interface Pulse {
  edgeId: string;
  /** Fixed offset along the edge, 0 to 1. Position derives from this + progress. */
  offset: number;
  seed: number;
}

export const PULSE_BUDGET = 120;
export const REDUCED_PULSE_BUDGET = 0;
export const MOBILE_PULSE_BUDGET = 48;

/** Deterministic 0–1 from an integer. Same generator as pipelinePainter. */
function rand(seed: number): number {
  const x = Math.sin(seed * 12.9898) * 43758.5453;
  return x - Math.floor(x);
}

/**
 * A fixed pool, allocated once.
 *
 * Pulses are distributed across edges by index rather than randomly, so every
 * edge carries flow regardless of how the seed falls — an edge that silently
 * drew nothing would read as a broken pipe.
 */
export function buildPulsePool(seed: number, budget: number): Pulse[] {
  const pool: Pulse[] = [];
  if (budget <= 0 || EDGES.length === 0) return pool;
  for (let i = 0; i < budget; i += 1) {
    // EDGES is non-empty (guarded above), so the modulo always lands on a real
    // entry; the check keeps the compiler honest without an assertion.
    const edge = EDGES[i % EDGES.length];
    if (!edge) continue;
    pool.push({
      edgeId: edge.id,
      offset: rand(seed + i * 7.31),
      seed: seed + i,
    });
  }
  return pool;
}

interface Point { x: number; y: number }

/**
 * Curvature of an edge that declares none.
 *
 * Named rather than written as `?? 0`, which the repository's lint rule
 * rejects — correctly, since coalescing a missing SCORE to zero fabricates a
 * measurement. This is not that: an edge without a bow is a straight line,
 * which is a real geometric default and not an unknown quantity. Saying so is
 * clearer than suppressing the rule.
 */
const STRAIGHT = 0;

const NODE_BY_ID = new Map(NODES.map((n) => [n.id, n]));

/** Where an edge runs, in unit coordinates. A loss edge leaves the system. */
export function edgePath(edge: Edge): { a: Point; b: Point; bow: number } | null {
  const from = NODE_BY_ID.get(edge.from);
  const to = NODE_BY_ID.get(edge.to);
  if (!from || !to) return null;
  if (edge.loss) {
    // A loss does not go anywhere useful: it exits upward, off the diagram.
    return { a: { x: from.x, y: from.y }, b: { x: from.x + 0.05, y: -0.08 }, bow: 0 };
  }
  return { a: { x: from.x, y: from.y }, b: { x: to.x, y: to.y }, bow: edge.bow ?? STRAIGHT };
}

/** Quadratic point at t, with the control point offset perpendicular by `bow`. */
export function pointOn(a: Point, b: Point, bow: number, t: number): Point {
  const mx = (a.x + b.x) / 2;
  const my = (a.y + b.y) / 2;
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const cx = mx - dy * bow;
  const cy = my + dx * bow;
  const u = 1 - t;
  return {
    x: u * u * a.x + 2 * u * t * cx + t * t * b.x,
    y: u * u * a.y + 2 * u * t * cy + t * t * b.y,
  };
}

export interface Colors {
  electricity: string;
  heat: string;
  water: string;
  material: string;
  waste: string;
  evidence: string;
  fuel: string;
}

export interface Size { w: number; h: number }

/**
 * One still frame of everything that moves.
 *
 * `progress` positions the pulses AND decides which edges exist, so a retired
 * edge stops carrying flow at exactly the moment it stops being drawn.
 */
export function paintFlows(
  ctx: CanvasRenderingContext2D,
  progress: number,
  pool: Pulse[],
  size: Size,
  colors: Colors,
): void {
  const { w, h } = size;
  ctx.clearRect(0, 0, w, h);
  if (w <= 0 || h <= 0) return;

  const edgeById = new Map(EDGES.map((e) => [e.id, e]));

  for (const pulse of pool) {
    const edge = edgeById.get(pulse.edgeId);
    if (!edge) continue;
    const opacity = presence(edge, progress);
    if (opacity <= 0.01) continue;

    const path = edgePath(edge);
    if (!path) continue;

    const style = FLOW_STYLE[edge.kind];
    // Travel is a pure function of progress and the pulse's own offset. No
    // clock: the same scroll position always puts this pulse in one place.
    const t = (pulse.offset + progress * style.speed * 4) % 1;
    const at = pointOn(path.a, path.b, path.bow, t);
    const x = at.x * w;
    const y = at.y * h;

    // Loss flows fade as they leave, so they read as escaping rather than
    // arriving somewhere.
    const travelFade = edge.loss ? 1 - t : 1;
    ctx.globalAlpha = Math.max(0, Math.min(1, opacity * travelFade * 0.85));
    ctx.fillStyle = colors[edge.kind];

    const s = style.width * 1.6;
    if (style.pulse === 'square') {
      ctx.fillRect(x - s / 2, y - s / 2, s, s);
    } else if (style.pulse === 'bar') {
      ctx.fillRect(x - s, y - style.width / 2, s * 2, style.width);
    } else {
      ctx.beginPath();
      ctx.arc(x, y, s / 2, 0, Math.PI * 2);
      ctx.fill();
    }
  }
  ctx.globalAlpha = 1;
}
