/**
 * pipelinePainter — pure paint functions for the "How it works" canvas.
 *
 * WHAT THIS IS A PORT OF, AND WHAT IT IS NOT
 * ------------------------------------------
 * The technique comes from the cinematic hero held in stash@{0}: framework-
 * agnostic paint functions, particle "aliveness" derived from
 * (seed, progress) rather than (seed, elapsedMs), one pre-allocated pool with
 * a fixed budget, no wall-clock timer anywhere. That work is scroll-driven and
 * deterministic by construction, which is what makes it verifiable — snap to a
 * scroll position, read one static frame.
 *
 * What is NOT ported is what it drew. Those scenes showed robot arms repairing
 * pollution, "Sensor Networks" as an evidence source, and specialist agents
 * investigating together. platform_registry/agents.py says plainly that EcoIQ
 * has no PRODUCTION AI agents, there is no sensor ingestion, and render.yaml
 * has Redis and the Celery worker commented out. Drawing them would have made
 * the same claim in pictures that the copy was corrected for making in words.
 *
 * WHAT IT DRAWS INSTEAD
 * ---------------------
 * The six stages HowItWorks already lists, and which the platform genuinely
 * runs. Evidence enters at the left and moves right. Crucially, NOT every
 * particle reaches Decision: some stop partway, because most evidence does not
 * carry a publishable conclusion. The list says "Published only when the
 * evidence carries it"; this is that sentence, drawn.
 *
 * DECORATION WITH A TEXT PRIMARY
 * ------------------------------
 * The canvas is aria-hidden. Every stage it paints exists as a real <li> in
 * HowItWorks, which is what a screen reader, a crawler and a reader with
 * JavaScript off all get. Nothing is communicated here that is not already
 * communicated there.
 */

export interface Particle {
  /** Deterministic per-particle seed. The only source of "randomness". */
  seed: number;
  /** Lane offset, -1..1, so particles do not travel in a single line. */
  lane: number;
  /**
   * Where this particle stops, 0..1 along the pipeline.
   *
   * Below 1 means this evidence never reaches a published decision — the
   * common case, and the point of the drawing.
   */
  reaches: number;
}

/**
 * Small on purpose. The stashed engine capped at 60 across every active
 * effect; this draws one effect, so it needs fewer. A homepage decoration
 * must not be the reason a mid-range phone drops frames.
 */
export const PARTICLE_BUDGET = 28;
export const REDUCED_BUDGET = 10;

/** Mulberry32. Seeded so the same build always paints the same frame. */
export function createSeededRng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function buildParticlePool(
  seed = 20260827, budget: number = PARTICLE_BUDGET,
): Particle[] {
  const rng = createSeededRng(seed);
  return Array.from({ length: budget }, () => {
    const roll = rng();
    return {
      seed: rng(),
      lane: rng() * 2 - 1,
      // Roughly a third of evidence carries all the way through. The exact
      // split is illustrative and the drawing claims no measured rate — it is
      // shaped so "most stops short" reads at a glance, which is true.
      reaches: roll < 0.34 ? 1 : 0.25 + rng() * 0.5,
    };
  });
}

export function clamp01(value: number): number {
  return Math.min(1, Math.max(0, value));
}

/** 0 before `start`, 1 after `end`, linear between. No easing library. */
export function envelope(progress: number, start: number, end: number): number {
  if (end <= start) return progress >= end ? 1 : 0;
  return clamp01((progress - start) / (end - start));
}

export interface PipelineDims {
  w: number;
  h: number;
  /** How many stage nodes to lay out. */
  stages: number;
}

export interface PipelineColors {
  line: string;
  node: string;
  nodeReached: string;
  particle: string;
  particleStopped: string;
}

export function stageX(index: number, dims: PipelineDims): number {
  const inset = dims.w * 0.08;
  const span = dims.w - inset * 2;
  return dims.stages <= 1 ? dims.w / 2 : inset + (span * index) / (dims.stages - 1);
}

/**
 * Paint one frame.
 *
 * A pure function of (progress, pool, dims, colors). Called from a scroll
 * callback and from a ResizeObserver, never from a timer, so there is no loop
 * to leak and nothing continues once the section leaves the viewport.
 */
export function paintPipeline(
  ctx: CanvasRenderingContext2D,
  progress: number,
  pool: Particle[],
  dims: PipelineDims,
  colors: PipelineColors,
): void {
  const p = clamp01(progress);
  ctx.clearRect(0, 0, dims.w, dims.h);

  const midY = dims.h / 2;

  // The rail the stages sit on, drawn as far as the reader has scrolled.
  ctx.strokeStyle = colors.line;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(stageX(0, dims), midY);
  ctx.lineTo(
    stageX(0, dims) + (stageX(dims.stages - 1, dims) - stageX(0, dims)) * p,
    midY,
  );
  ctx.stroke();

  // Evidence in flight.
  for (const particle of pool) {
    // Each particle starts at a slightly different point, so they arrive as a
    // stream rather than a rank. Position is a pure function of progress.
    const offset = particle.seed * 0.35;
    const travel = clamp01((p - offset) / (1 - offset || 1));
    if (travel <= 0) continue;

    const reached = Math.min(travel, particle.reaches);
    const stopped = travel > particle.reaches;

    const x = stageX(0, dims)
      + (stageX(dims.stages - 1, dims) - stageX(0, dims)) * reached;
    // A gentle, deterministic drift. sin(seed, progress) — never elapsed time.
    const drift = Math.sin(particle.seed * 12 + reached * 6) * (dims.h * 0.16);
    const y = midY + particle.lane * (dims.h * 0.1) + drift;

    ctx.globalAlpha = stopped ? 0.28 : 0.85;
    ctx.fillStyle = stopped ? colors.particleStopped : colors.particle;
    ctx.beginPath();
    ctx.arc(x, y, stopped ? 1.6 : 2.4, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.globalAlpha = 1;

  // Stage nodes, filling as the rail reaches them.
  for (let i = 0; i < dims.stages; i += 1) {
    const at = dims.stages <= 1 ? 0 : i / (dims.stages - 1);
    const lit = envelope(p, at - 0.04, at + 0.02);
    const x = stageX(i, dims);

    ctx.beginPath();
    ctx.arc(x, midY, 5, 0, Math.PI * 2);
    ctx.fillStyle = lit > 0.5 ? colors.nodeReached : colors.node;
    ctx.fill();

    if (lit > 0.5) {
      ctx.beginPath();
      ctx.arc(x, midY, 5 + lit * 4, 0, Math.PI * 2);
      ctx.strokeStyle = colors.nodeReached;
      ctx.globalAlpha = 0.35 * (1 - lit);
      ctx.stroke();
      ctx.globalAlpha = 1;
    }
  }
}
