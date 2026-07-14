/**
 * canvasEngine — pure paint functions for the hero's single canvas layer.
 *
 * Deliberately framework-agnostic (no React, no requestAnimationFrame). Every
 * effect is a pure function of `progress` (the raw scrollYProgress, 0–1) —
 * there is no wall-clock timer anywhere in this module. That's not a
 * simplification for its own sake: it's what makes every effect here
 * "scroll-driven, never an uncontrolled infinite loop" by construction
 * (motion-style-guide.md §2), and it's what makes each beat verifiable by
 * snapping to a fixed scroll position and reading one static frame, exactly
 * like the existing DOM/SVG overlays in this tree already are.
 *
 * A particle's "aliveness" comes from deterministic functions of
 * (seed, progress) — e.g. `sin(seed*k1 + progress*k2)` — never
 * (seed, elapsedMs). Scrubbing the scrollbar deterministically animates every
 * particle; the same progress value always paints the same frame.
 *
 * Deliberate v1.1-style addition (see docs/motion-library-v1.md): a fixed
 * budget of <= 60 particles total across all active effects in one pool,
 * allocated once and mutated in place — no per-call allocation.
 */
import { color } from '../../design/tokens'
import { AGENTS_SUB_RANGES, GLOBE_RESPONSE_RANGES, SCENE_RANGES } from './sceneRanges'
import {
  CANVAS_W,
  CANVAS_H,
  GLOBE_CENTER,
  LEFT_ARM_CLAW,
  RIGHT_ARM_CLAW,
  WASTE_TARGETS,
  POLLUTION_AREA,
  REPAIR_TARGETS,
  SMOKE_AREA,
  VERIFY_BADGE,
  AGENT_POSITIONS,
} from './sceneLayout'

export interface Particle {
  /** Deterministic per-particle seed — the only source of "randomness". */
  seed: number
  /** Role determines which paint pass moves this particle and where. */
  kind: 'atmosphereFar' | 'atmosphereNear' | 'waste' | 'restore' | 'repair' | 'verify'
  /** Index within its kind's group (e.g. which target/arc this particle belongs to). */
  groupIndex: number
  /** Scratch fields written each paint call — never reallocated. */
  x: number
  y: number
}

const ATMOSPHERE_FAR_COUNT = 13
const ATMOSPHERE_NEAR_COUNT = 10
const WASTE_COUNT = 12
const RESTORE_COUNT = 8
const REPAIR_COUNT = 12
const VERIFY_COUNT = 5 // one per AGENT_POSITIONS source, matching the existing evidence/repair convention

export const PARTICLE_BUDGET =
  ATMOSPHERE_FAR_COUNT + ATMOSPHERE_NEAR_COUNT + WASTE_COUNT + RESTORE_COUNT + REPAIR_COUNT + VERIFY_COUNT // 60 — stated budget, see docstring

/** mulberry32 — small, fast, deterministic PRNG. Same seed always produces the same sequence. */
export function createSeededRng(seed: number): () => number {
  let a = seed >>> 0
  return function () {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

/**
 * Allocates the fixed particle pool once. Never call this per paint — reuse
 * the returned array. `tier: 'reduced'` (tablet, 760-1024px) halves each
 * group's count for a lighter draw — still the same deterministic seed
 * sequence, just fewer particles per group.
 */
export function buildParticlePool(seed = 20260713, tier: 'full' | 'reduced' = 'full'): Particle[] {
  const scale = tier === 'reduced' ? 0.5 : 1
  const rng = createSeededRng(seed)
  const pool: Particle[] = []
  const push = (kind: Particle['kind'], count: number) => {
    const n = Math.max(1, Math.round(count * scale))
    for (let g = 0; g < n; g++) {
      pool.push({ seed: rng() * 1000, kind, groupIndex: g, x: 0, y: 0 })
    }
  }
  push('atmosphereFar', ATMOSPHERE_FAR_COUNT)
  push('atmosphereNear', ATMOSPHERE_NEAR_COUNT)
  push('waste', WASTE_COUNT)
  push('restore', RESTORE_COUNT)
  push('repair', REPAIR_COUNT)
  push('verify', VERIFY_COUNT)
  return pool
}

function clamp01(v: number) {
  return v < 0 ? 0 : v > 1 ? 1 : v
}

/** 0 outside [start,end], eased ramp in/out at the edges, 1 in the middle third. */
function rangeEnvelope(progress: number, start: number, end: number): number {
  if (progress < start || progress > end) return 0
  const span = end - start
  const t = (progress - start) / span
  const edge = Math.min(span * 0.25, 0.01)
  const edgeT = edge / span
  if (t < edgeT) return t / edgeT
  if (t > 1 - edgeT) return (1 - t) / edgeT
  return 1
}

function toCanvasXY(p: { x: number; y: number }, dims: { w: number; h: number }) {
  return { cx: (p.x / CANVAS_W) * dims.w, cy: (p.y / CANVAS_H) * dims.h }
}

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t
}

/**
 * Paints one frame. Call synchronously from the same scroll `onChange`
 * handler that drives every other overlay — no internal loop, no timers.
 */
export function paintHero(
  ctx: CanvasRenderingContext2D,
  progress: number,
  dims: { w: number; h: number; dpr: number },
  pool: Particle[],
): void {
  ctx.clearRect(0, 0, dims.w, dims.h)

  const agentsRange = SCENE_RANGES[2]
  const agentsEnvelope = rangeEnvelope(progress, agentsRange[0], agentsRange[1])
  if (agentsEnvelope <= 0) return // outside the hero's active window entirely — nothing to paint

  paintAtmosphere(ctx, progress, dims, pool, agentsEnvelope)
  paintWasteExtraction(ctx, progress, dims, pool)
  paintRestoreSpread(ctx, progress, dims, pool)
  paintRepairEnergy(ctx, progress, dims, pool)
  paintRepairReconstruct(ctx, progress, dims)
  paintVerifyArcs(ctx, progress, dims, pool)
}

/** Ambient depth cue: two parallax bands drifting slowly around the globe, always faint. */
function paintAtmosphere(
  ctx: CanvasRenderingContext2D,
  progress: number,
  dims: { w: number; h: number },
  pool: Particle[],
  envelope: number,
) {
  const { cx, cy } = toCanvasXY(GLOBE_CENTER, dims)
  const radius = Math.min(dims.w, dims.h) * 0.28

  for (const p of pool) {
    if (p.kind !== 'atmosphereFar' && p.kind !== 'atmosphereNear') continue
    const isNear = p.kind === 'atmosphereNear'
    const orbitR = radius * (isNear ? 1.12 + (p.seed % 10) / 40 : 1.35 + (p.seed % 10) / 25)
    const speed = isNear ? 1.6 : 0.7 // near band drifts faster — the parallax cue
    const angle = p.seed + progress * speed * Math.PI * 2
    p.x = cx + Math.cos(angle) * orbitR
    p.y = cy + Math.sin(angle) * orbitR * 0.55 // flattened orbit, reads as depth not a halo
    const r = isNear ? 1.6 : 1
    const alpha = (isNear ? 0.35 : 0.16) * envelope
    ctx.beginPath()
    ctx.arc(p.x, p.y, r, 0, Math.PI * 2)
    ctx.fillStyle = withAlpha(color.ink, alpha)
    ctx.fill()
  }
}

/** Particles converging from the pollution area toward the left claw — waste extraction. */
function paintWasteExtraction(
  ctx: CanvasRenderingContext2D,
  progress: number,
  dims: { w: number; h: number },
  pool: Particle[],
) {
  const [start, end] = AGENTS_SUB_RANGES.waste
  const envelope = rangeEnvelope(progress, start, end)
  if (envelope <= 0) return
  const t = clamp01((progress - start) / (end - start))
  const { cx: tx, cy: ty } = toCanvasXY(LEFT_ARM_CLAW, dims)

  for (const p of pool) {
    if (p.kind !== 'waste') continue
    const origin = WASTE_TARGETS[p.groupIndex % WASTE_TARGETS.length]
    const { cx: ox, cy: oy } = toCanvasXY(origin, dims)
    // Staggered convergence: each particle starts its journey at a slightly
    // different point in the range, so they arrive as a organic stream, not
    // a single synchronized snap.
    const localT = clamp01(t * 1.4 - (p.seed % 10) / 24)
    const jitter = Math.sin(p.seed + progress * 6) * 6
    p.x = lerp(ox, tx, localT) + jitter
    p.y = lerp(oy, ty, localT) + Math.cos(p.seed + progress * 6) * 6
    const alpha = 0.55 * envelope * (0.4 + 0.6 * localT)
    ctx.beginPath()
    ctx.arc(p.x, p.y, 2, 0, Math.PI * 2)
    ctx.fillStyle = withAlpha(color.accent, alpha)
    ctx.fill()
  }
}

/** Organic, noise-perturbed growth spreading outward from the pollution area — ecological recovery. */
function paintRestoreSpread(
  ctx: CanvasRenderingContext2D,
  progress: number,
  dims: { w: number; h: number },
  pool: Particle[],
) {
  const [start, end] = AGENTS_SUB_RANGES.waste
  // Recovery reads as the second half of the waste window (matches BEAT 4 in sceneRanges.ts's BEAT_LABELS).
  const recoverStart = start + (end - start) * 0.4
  const envelope = rangeEnvelope(progress, recoverStart, end + 0.02)
  if (envelope <= 0) return
  const t = clamp01((progress - recoverStart) / (end - recoverStart))
  const { cx, cy } = toCanvasXY(POLLUTION_AREA, dims)
  const maxRadius = Math.min(dims.w, dims.h) * 0.1

  for (const p of pool) {
    if (p.kind !== 'restore') continue
    const angle = p.seed * 1.7
    // Noise-perturbed radius — organic, not a perfect circle.
    const wobble = 1 + Math.sin(p.seed * 3 + progress * 4) * 0.18
    const r = maxRadius * t * wobble * (0.5 + (p.seed % 10) / 20)
    p.x = cx + Math.cos(angle) * r
    p.y = cy + Math.sin(angle) * r * 0.6
    const alpha = 0.5 * envelope * t
    ctx.beginPath()
    ctx.arc(p.x, p.y, 1.8, 0, Math.PI * 2)
    ctx.fillStyle = withAlpha(color.accent, alpha)
    ctx.fill()
  }
}

/** Steps used by both the repair particle snap and the reconstruct lines — shared so they stay in lockstep. */
const REPAIR_STEP_COUNT = 4

/**
 * Precise, staged energy transfer toward the right claw — deliberately NOT a
 * mirror of `paintWasteExtraction`'s organic converge-with-jitter (Phase 3:
 * "do not make the two arms feel like mirrored versions of the same
 * animation"). Each particle snaps between a small number of discrete
 * waypoints on a straight line (no sine-jitter drift, no organic wobble) —
 * reads as "targeting lock" steps, matching the brief's "precise, engineered,
 * geometric, sequential, controlled" language for this arm.
 */
function paintRepairEnergy(
  ctx: CanvasRenderingContext2D,
  progress: number,
  dims: { w: number; h: number },
  pool: Particle[],
) {
  const [start, end] = AGENTS_SUB_RANGES.repair
  const envelope = rangeEnvelope(progress, start, end)
  if (envelope <= 0) return
  const t = clamp01((progress - start) / (end - start))
  const { cx: tx, cy: ty } = toCanvasXY(RIGHT_ARM_CLAW, dims)

  for (const p of pool) {
    if (p.kind !== 'repair') continue
    const originPoints = REPAIR_TARGETS.length ? REPAIR_TARGETS : [SMOKE_AREA]
    const origin = originPoints[p.groupIndex % originPoints.length]
    const { cx: ox, cy: oy } = toCanvasXY(origin, dims)
    // Staggered start per particle, same as waste, but the *motion* itself is
    // quantized into discrete steps rather than continuously interpolated —
    // a "snap to the next waypoint" cadence instead of a smooth drift.
    const localT = clamp01(t * 1.4 - (p.seed % 10) / 24)
    const stepped = Math.floor(localT * REPAIR_STEP_COUNT) / REPAIR_STEP_COUNT
    p.x = lerp(ox, tx, stepped)
    p.y = lerp(oy, ty, stepped)
    const alpha = 0.6 * envelope * (0.4 + 0.6 * stepped)
    // Small square, not a soft circle — geometric mark language vs. waste's round dot.
    const s = 2.6
    ctx.fillStyle = withAlpha(color.warn, alpha)
    ctx.fillRect(p.x - s / 2, p.y - s / 2, s, s)
  }
}

/**
 * Progressive geometric reconstruction at the repair targets — short straight
 * scaffold segments that draw in sequentially (one target "locks," then the
 * next), distinct from the waste side's organic radial growth. Fires in the
 * later portion of the repair window, once energy transfer is underway.
 */
function paintRepairReconstruct(
  ctx: CanvasRenderingContext2D,
  progress: number,
  dims: { w: number; h: number },
) {
  const [start, end] = AGENTS_SUB_RANGES.repair
  const reconstructStart = start + (end - start) * 0.45
  const envelope = rangeEnvelope(progress, reconstructStart, end + 0.02)
  if (envelope <= 0) return
  const t = clamp01((progress - reconstructStart) / (end - reconstructStart))
  const targets = REPAIR_TARGETS.length ? REPAIR_TARGETS : [SMOKE_AREA]
  const perTarget = 1 / targets.length

  targets.forEach((target, i) => {
    const localT = clamp01((t - i * perTarget * 0.6) / (perTarget * 1.4))
    if (localT <= 0) return
    const { cx, cy } = toCanvasXY(target, dims)
    const size = Math.min(dims.w, dims.h) * 0.024
    const alpha = 0.5 * envelope * Math.min(1, localT * 2)
    ctx.strokeStyle = withAlpha(color.warn, alpha)
    ctx.lineWidth = 1.4
    // Draw an angular corner-bracket scaffold that "completes" as localT rises —
    // a rigid geometric mark, not an organic blob.
    const reveal = clamp01(localT)
    ctx.beginPath()
    ctx.moveTo(cx - size, cy - size + size * 2 * Math.min(1, reveal * 2))
    ctx.lineTo(cx - size, cy - size)
    ctx.lineTo(cx - size + size * 2 * Math.min(1, Math.max(0, (reveal - 0.5) * 2)), cy - size)
    ctx.stroke()
    ctx.beginPath()
    ctx.moveTo(cx + size, cy + size - size * 2 * Math.min(1, reveal * 2))
    ctx.lineTo(cx + size, cy + size)
    ctx.lineTo(cx + size - size * 2 * Math.min(1, Math.max(0, (reveal - 0.5) * 2)), cy + size)
    ctx.stroke()
  })
}

/** Verification signal traveling from each agent node to the verify badge. */
function paintVerifyArcs(
  ctx: CanvasRenderingContext2D,
  progress: number,
  dims: { w: number; h: number },
  pool: Particle[],
) {
  const [start, end] = GLOBE_RESPONSE_RANGES.verify
  const envelope = rangeEnvelope(progress, start, end)
  if (envelope <= 0) return
  const t = clamp01((progress - start) / (end - start))
  const { cx: tx, cy: ty } = toCanvasXY(VERIFY_BADGE, dims)

  for (const p of pool) {
    if (p.kind !== 'verify') continue
    const origin = AGENT_POSITIONS[p.groupIndex % AGENT_POSITIONS.length]
    const { cx: ox, cy: oy } = toCanvasXY(origin, dims)
    const localT = clamp01(t - (p.groupIndex % VERIFY_COUNT) * 0.06)
    // Slight arc (not a straight line) via a quadratic control point above the midpoint.
    const midX = (ox + tx) / 2
    const midY = Math.min(oy, ty) - 30
    const inv = 1 - localT
    p.x = inv * inv * ox + 2 * inv * localT * midX + localT * localT * tx
    p.y = inv * inv * oy + 2 * inv * localT * midY + localT * localT * ty
    const alpha = 0.6 * envelope * Math.sin(Math.PI * clamp01(localT))
    ctx.beginPath()
    ctx.arc(p.x, p.y, 2.2, 0, Math.PI * 2)
    ctx.fillStyle = withAlpha(color.inkStrong, Math.max(0, alpha))
    ctx.fill()
  }
}

function withAlpha(hexOrRgba: string, alpha: number): string {
  const a = clamp01(alpha)
  if (hexOrRgba.startsWith('rgba')) {
    // Replace the existing alpha channel.
    return hexOrRgba.replace(/[\d.]+\)$/, `${a})`)
  }
  const hex = hexOrRgba.replace('#', '')
  const r = parseInt(hex.slice(0, 2), 16)
  const g = parseInt(hex.slice(2, 4), 16)
  const b = parseInt(hex.slice(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${a})`
}
