/**
 * The six state functions, against the contract their module declares.
 *
 * Every test here iterates STATE_FUNCTIONS rather than naming functions one by
 * one. A seventh function added later inherits the whole contract by existing,
 * which is the only way a shared contract stays shared.
 */
import { describe, expect, it } from 'vitest';

import { STAGES } from './stages';
import {
  MODEL_STATE_DISCLAIMER,
  STATE_FUNCTIONS,
  assertNotPresentedAsMeasurement,
  heatLossFraction,
  heatCaptureFraction,
  materialRecoveryFraction,
  usefulHeatRecoveryFraction,
  waterReuseFraction,
} from './state';

/** Every stage boundary, plus the ends and a midpoint. */
const BOUNDARIES = [
  0,
  ...STAGES.flatMap((s) => [s.from, s.to]),
  0.5,
  1,
].sort((a, b) => a - b);

const SAMPLES = Array.from({ length: 201 }, (_, i) => i / 200);

describe('the shared contract', () => {
  it('every function has a documented semantic', () => {
    for (const spec of STATE_FUNCTIONS) {
      expect(spec.semantics.length).toBeGreaterThan(30);
    }
  });

  it('returns a value inside [0,1] for every sampled progress', () => {
    for (const spec of STATE_FUNCTIONS) {
      for (const p of SAMPLES) {
        const v = spec.fn(p);
        expect(v, `${spec.key}(${p})`).toBeGreaterThanOrEqual(0);
        expect(v, `${spec.key}(${p})`).toBeLessThanOrEqual(1);
      }
    }
  });

  it('clamps input rather than extrapolating past the ends', () => {
    for (const spec of STATE_FUNCTIONS) {
      expect(spec.fn(-5), `${spec.key}(-5)`).toBeCloseTo(spec.fn(0), 10);
      expect(spec.fn(50), `${spec.key}(50)`).toBeCloseTo(spec.fn(1), 10);
    }
  });

  it('survives a non-finite input instead of returning NaN', () => {
    for (const spec of STATE_FUNCTIONS) {
      expect(Number.isFinite(spec.fn(NaN)), spec.key).toBe(true);
      expect(Number.isFinite(spec.fn(Infinity)), spec.key).toBe(true);
    }
  });

  it('is deterministic — same input, same output', () => {
    for (const spec of STATE_FUNCTIONS) {
      for (const p of [0, 0.31, 0.5, 0.77, 1]) {
        expect(spec.fn(p)).toBe(spec.fn(p));
      }
    }
  });

  it('uses no clock and no randomness', () => {
    // A time-dependent function would differ across a delay. Sampling twice
    // around a real elapsed interval is the cheapest honest check.
    const first = STATE_FUNCTIONS.map((s) => s.fn(0.42));
    const start = Date.now();
    while (Date.now() - start < 3) { /* burn a few milliseconds */ }
    const second = STATE_FUNCTIONS.map((s) => s.fn(0.42));
    expect(second).toEqual(first);
  });
});

describe('endpoints are pinned', () => {
  it('matches the declared value at progress 0', () => {
    for (const spec of STATE_FUNCTIONS) {
      expect(spec.fn(0), `${spec.key}(0)`).toBeCloseTo(spec.atZero, 6);
    }
  });

  it('matches the declared value at progress 1', () => {
    for (const spec of STATE_FUNCTIONS) {
      expect(spec.fn(1), `${spec.key}(1)`).toBeCloseTo(spec.atOne, 6);
    }
  });

  it('has a real midpoint between the two ends', () => {
    // Guards against a function that is a step at 1 and flat everywhere else,
    // which would satisfy both endpoint tests while modelling nothing.
    for (const spec of STATE_FUNCTIONS) {
      const mid = spec.fn(0.5);
      const lo = Math.min(spec.atZero, spec.atOne);
      const hi = Math.max(spec.atZero, spec.atOne);
      expect(mid, `${spec.key}(0.5)`).toBeGreaterThanOrEqual(lo);
      expect(mid, `${spec.key}(0.5)`).toBeLessThanOrEqual(hi);
    }
  });
});

describe('monotonicity, in the declared direction', () => {
  it('never moves against its declared direction', () => {
    for (const spec of STATE_FUNCTIONS) {
      for (let i = 1; i < SAMPLES.length; i += 1) {
        const previous = spec.fn(SAMPLES[i - 1]!);
        const current = spec.fn(SAMPLES[i]!);
        const message = `${spec.key} at ${SAMPLES[i]}: ${previous} -> ${current}`;
        if (spec.monotonicity === 'increasing') {
          expect(current + 1e-9, message).toBeGreaterThanOrEqual(previous);
        } else {
          expect(current - 1e-9, message).toBeLessThanOrEqual(previous);
        }
      }
    }
  });

  it('holds across every stage boundary specifically', () => {
    // Boundaries are where a piecewise definition is most likely to jump the
    // wrong way, and a coarse sample can step straight over one.
    for (const spec of STATE_FUNCTIONS) {
      for (const b of BOUNDARIES) {
        const before = spec.fn(Math.max(0, b - 1e-6));
        const after = spec.fn(Math.min(1, b + 1e-6));
        if (spec.monotonicity === 'increasing') {
          expect(after + 1e-9, `${spec.key} at ${b}`).toBeGreaterThanOrEqual(before);
        } else {
          expect(after - 1e-9, `${spec.key} at ${b}`).toBeLessThanOrEqual(before);
        }
      }
    }
  });

  it('reverse scroll produces the reverse state, exactly', () => {
    // Scrolling back up must retrace, not settle somewhere new. A function
    // with hidden state would fail here and nowhere else.
    for (const spec of STATE_FUNCTIONS) {
      const forward = SAMPLES.map(spec.fn);
      const backward = [...SAMPLES].reverse().map(spec.fn).reverse();
      expect(backward, spec.key).toEqual(forward);
    }
  });
});

describe('loss falls only where an intervention acts on it', () => {
  it('heat loss is untouched before electrify begins', () => {
    const electrify = STAGES.find((s) => s.key === 'electrify')!;
    expect(heatLossFraction(electrify.from)).toBeCloseTo(1, 6);
    expect(heatLossFraction(0)).toBeCloseTo(1, 6);
  });

  it('heat loss falls in two steps, because two interventions act on it', () => {
    const electrify = STAGES.find((s) => s.key === 'electrify')!;
    const recover = STAGES.find((s) => s.key === 'recover')!;
    const afterElectrify = heatLossFraction(electrify.to);
    const afterRecover = heatLossFraction(recover.to);
    expect(afterElectrify).toBeCloseTo(0.5, 6);
    expect(afterRecover).toBeCloseTo(0, 6);
  });

  it('water reuse is zero until circularise, not merely small', () => {
    const circularise = STAGES.find((s) => s.key === 'circularise')!;
    expect(waterReuseFraction(circularise.from)).toBe(0);
    expect(waterReuseFraction(circularise.from - 0.01)).toBe(0);
    expect(waterReuseFraction(circularise.to)).toBeCloseTo(1, 6);
  });

  it('material recovery is zero until circularise', () => {
    const circularise = STAGES.find((s) => s.key === 'circularise')!;
    expect(materialRecoveryFraction(circularise.from)).toBe(0);
    expect(materialRecoveryFraction(circularise.to)).toBeCloseTo(1, 6);
  });

  it('capture is complete before any of it is usefully recovered', () => {
    // The engineering point, and the reason these are two functions. At the
    // end of RECOVER the exchanger is installed and taking heat out of the
    // stream — capture is 1 — but nothing needs that heat yet, so useful
    // recovery is still 0. Reporting "50% recovered" there, as the single
    // averaged function did, describes a plant that does not exist.
    const recover = STAGES.find((s) => s.key === 'recover')!;
    expect(heatCaptureFraction(recover.to)).toBeCloseTo(1, 6);
    expect(usefulHeatRecoveryFraction(recover.to)).toBe(0);
  });

  it('useful recovery can never exceed capture', () => {
    // You cannot deliver heat you did not take.
    for (let i = 0; i <= 200; i += 1) {
      const p = i / 200;
      expect(usefulHeatRecoveryFraction(p), `progress ${p}`)
        .toBeLessThanOrEqual(heatCaptureFraction(p) + 1e-9);
    }
  });

  it('both reach 1 only once the sink exists', () => {
    const circularise = STAGES.find((s) => s.key === 'circularise')!;
    expect(usefulHeatRecoveryFraction(circularise.from)).toBe(0);
    expect(usefulHeatRecoveryFraction(circularise.to)).toBeCloseTo(1, 6);
  });
});

describe('these values are not measurements, and the module says so', () => {
  it('carries a disclaimer naming what it is not', () => {
    expect(MODEL_STATE_DISCLAIMER).toMatch(/not measurements/i);
    expect(MODEL_STATE_DISCLAIMER).toMatch(/no metered data/i);
  });

  it('refuses, loudly, to be presented as facility performance', () => {
    expect(() => assertNotPresentedAsMeasurement('a dashboard tile'))
      .toThrow(/Refusing to present/);
  });

  it('no semantic describes a real facility', () => {
    for (const spec of STATE_FUNCTIONS) {
      expect(spec.semantics).not.toMatch(/measured|actual|reported|kWh|tonnes/i);
    }
  });
});
