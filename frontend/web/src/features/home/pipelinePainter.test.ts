import { describe, expect, it } from 'vitest';
import {
  buildParticlePool, clamp01, createSeededRng, envelope, paintPipeline,
  PARTICLE_BUDGET, REDUCED_BUDGET, stageX,
} from './pipelinePainter';

describe('the pipeline painter', () => {
  it('is deterministic across builds', () => {
    /**
     * Particle "aliveness" comes from (seed, progress), never elapsed time.
     * That is what makes a single frame assertable instead of a moving target
     * — and what lets a reader scrub the page and see the same thing twice.
     */
    expect(buildParticlePool(1234)).toEqual(buildParticlePool(1234));
  });

  it('gives different seeds different pools', () => {
    expect(buildParticlePool(1)).not.toEqual(buildParticlePool(2));
  });

  it('honours the particle budget', () => {
    expect(buildParticlePool(1)).toHaveLength(PARTICLE_BUDGET);
    expect(buildParticlePool(1, REDUCED_BUDGET)).toHaveLength(REDUCED_BUDGET);
  });

  it('keeps the budget small enough for a phone', () => {
    expect(PARTICLE_BUDGET).toBeLessThanOrEqual(40);
    expect(REDUCED_BUDGET).toBeLessThan(PARTICLE_BUDGET);
  });

  it('stops most evidence short of a decision', () => {
    /**
     * The drawing's whole argument. "Published only when the evidence carries
     * it" is what the list says; a pool where everything arrived would draw
     * the opposite.
     */
    const pool = buildParticlePool(20260827);
    const arrive = pool.filter((p) => p.reaches >= 1).length;
    expect(arrive).toBeGreaterThan(0);
    expect(arrive).toBeLessThan(pool.length / 2);
  });

  it('never places a particle past the end', () => {
    for (const particle of buildParticlePool(99)) {
      expect(particle.reaches).toBeGreaterThan(0);
      expect(particle.reaches).toBeLessThanOrEqual(1);
    }
  });

  it('clamps progress at both ends', () => {
    expect(clamp01(-5)).toBe(0);
    expect(clamp01(5)).toBe(1);
    expect(clamp01(0.4)).toBe(0.4);
  });

  it('envelopes from 0 to 1 across their range', () => {
    expect(envelope(0, 0.2, 0.6)).toBe(0);
    expect(envelope(0.4, 0.2, 0.6)).toBeCloseTo(0.5);
    expect(envelope(1, 0.2, 0.6)).toBe(1);
  });

  it('survives a zero-width envelope rather than dividing by zero', () => {
    expect(Number.isNaN(envelope(0.5, 0.3, 0.3))).toBe(false);
  });

  it('lays stages out in order and inside the canvas', () => {
    const dims = { w: 800, h: 120, stages: 6 };
    const xs = Array.from({ length: 6 }, (_, i) => stageX(i, dims));
    expect(xs).toEqual([...xs].sort((a, b) => a - b));
    expect(Math.min(...xs)).toBeGreaterThan(0);
    expect(Math.max(...xs)).toBeLessThan(dims.w);
  });

  it('centres a single stage rather than dividing by zero', () => {
    expect(stageX(0, { w: 800, h: 120, stages: 1 })).toBe(400);
  });

  it('paints the same frame for the same progress', () => {
    const calls: string[] = [];
    const ctx = {
      clearRect: () => calls.push('clear'),
      beginPath: () => calls.push('begin'),
      moveTo: (x: number) => calls.push(`moveTo:${x.toFixed(2)}`),
      lineTo: (x: number) => calls.push(`lineTo:${x.toFixed(2)}`),
      arc: (x: number, y: number) => calls.push(`arc:${x.toFixed(2)},${y.toFixed(2)}`),
      stroke: () => calls.push('stroke'),
      fill: () => calls.push('fill'),
      globalAlpha: 1, fillStyle: '', strokeStyle: '', lineWidth: 1,
    } as unknown as CanvasRenderingContext2D;

    const pool = buildParticlePool(7);
    const dims = { w: 600, h: 120, stages: 6 };
    const colors = {
      line: '#000', node: '#111', nodeReached: '#0a0',
      particle: '#0a0', particleStopped: '#999',
    };

    paintPipeline(ctx, 0.5, pool, dims, colors);
    const first = [...calls];
    calls.length = 0;
    paintPipeline(ctx, 0.5, pool, dims, colors);
    expect(calls).toEqual(first);
  });

  it('has no evidence in flight at zero progress', () => {
    /**
     * Distinguished by radius: particles are drawn at 1.6-2.4, stage nodes at
     * 5 and their halo larger still. Counting every arc would also count the
     * six nodes and the first node's halo, which are supposed to be there.
     */
    const radii: number[] = [];
    const ctx = {
      clearRect: () => {}, beginPath: () => {}, moveTo: () => {},
      lineTo: () => {}, stroke: () => {}, fill: () => {},
      arc: (_x: number, _y: number, r: number) => { radii.push(r); },
      globalAlpha: 1, fillStyle: '', strokeStyle: '', lineWidth: 1,
    } as unknown as CanvasRenderingContext2D;

    const colors = {
      line: '#000', node: '#111', nodeReached: '#0a0',
      particle: '#0a0', particleStopped: '#999',
    };
    const dims = { w: 600, h: 120, stages: 6 };

    paintPipeline(ctx, 0, buildParticlePool(7), dims, colors);
    expect(radii.filter((r) => r < 5)).toHaveLength(0);
    expect(radii.filter((r) => r >= 5)).toHaveLength(7); // 6 nodes + first halo

    radii.length = 0;
    paintPipeline(ctx, 1, buildParticlePool(7), dims, colors);
    expect(radii.filter((r) => r < 5).length).toBeGreaterThan(0);
  });

  it('produces a stable stream from the seeded rng', () => {
    const a = createSeededRng(42);
    const b = createSeededRng(42);
    expect([a(), a(), a()]).toEqual([b(), b(), b()]);
  });
});
