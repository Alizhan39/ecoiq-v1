/**
 * The three layers, checked against each other.
 *
 * The model, the drawing and the narrative are separate on purpose. That
 * separation is only worth having if they cannot drift, so this file asserts
 * the couplings that matter:
 *
 *   - the drawing's stages ARE the model's stages, not a parallel list;
 *   - a state function falls exactly where the drawing removes the loss it
 *     describes;
 *   - the narrative's steps are the same steps, in the same order.
 *
 * This is the file that fails if somebody retimes an edge without moving the
 * stage, or moves a stage without retiming the edge.
 */
import { describe, expect, it } from 'vitest';

import { EDGES, NODES, presence, recoveredFraction, sceneAt } from '../topology';
import { narrativeAt } from '../semantic/narrative';
import { STAGES, stageAt } from './stages';
import {
  electrificationFraction, heatLossFraction, materialRecoveryFraction,
  waterReuseFraction,
} from './state';

const SAMPLES = Array.from({ length: 201 }, (_, i) => i / 200);

describe('one stage list, three consumers', () => {
  it('the drawing reports the same stage as the model', () => {
    for (const p of SAMPLES) {
      expect(sceneAt(p).stage.key, `progress ${p}`).toBe(stageAt(p).key);
    }
  });

  it('the narrative reports the same stage as the drawing', () => {
    for (const p of SAMPLES) {
      const fromNarrative = narrativeAt(p).find((s) => s.current)!.key;
      expect(fromNarrative, `progress ${p}`).toBe(sceneAt(p).stage.key);
    }
  });

  it('the stage list has eight entries and covers 0 to 1 with no gap', () => {
    expect(STAGES).toHaveLength(8);
    expect(STAGES[0]!.from).toBe(0);
    expect(STAGES[STAGES.length - 1]!.to).toBe(1);
    for (let i = 1; i < STAGES.length; i += 1) {
      expect(STAGES[i]!.from, `gap before ${STAGES[i]!.key}`)
        .toBe(STAGES[i - 1]!.to);
    }
  });
});

describe('the numbers agree with the picture', () => {
  it('electrification completes exactly when the fired heater leaves', () => {
    const boiler = NODES.find((n) => n.id === 'boiler')!;
    // The heater retires inside ELECTRIFY, and the fraction reaches 1 at the
    // end of that stage. If someone retimes one without the other, this fails.
    const electrify = STAGES.find((s) => s.key === 'electrify')!;
    expect(boiler.retiredAt!).toBeGreaterThanOrEqual(electrify.from);
    expect(boiler.retiredAt!).toBeLessThanOrEqual(electrify.to);
    expect(electrificationFraction(electrify.to)).toBeCloseTo(1, 6);
  });

  it('heat loss reaches zero only once no loss edge is still drawn', () => {
    const stillDrawn = (p: number) => EDGES
      .filter((e) => e.loss && e.kind === 'heat')
      .some((e) => presence(e, p) > 0.01);
    // Find where the model says heat loss is gone.
    const zeroAt = SAMPLES.find((p) => heatLossFraction(p) < 1e-6)!;
    expect(zeroAt).toBeDefined();
    expect(stillDrawn(zeroAt), `heat loss edges still drawn at ${zeroAt}`)
      .toBe(false);
  });

  it('water reuse rises only after the discharge edge has gone', () => {
    const discharge = EDGES.find((e) => e.id === 'loss-water')!;
    const risesAt = SAMPLES.find((p) => waterReuseFraction(p) > 0)!;
    // The edge must be on its way out by the time reuse is credited.
    expect(discharge.retiredAt!).toBeLessThanOrEqual(
      STAGES.find((s) => s.key === 'circularise')!.to,
    );
    expect(risesAt).toBeGreaterThanOrEqual(
      STAGES.find((s) => s.key === 'circularise')!.from,
    );
  });

  it('material recovery rises only after the waste node is retired', () => {
    const waste = NODES.find((n) => n.id === 'waste')!;
    const circularise = STAGES.find((s) => s.key === 'circularise')!;
    expect(waste.retiredAt!).toBeGreaterThanOrEqual(circularise.from);
    expect(materialRecoveryFraction(circularise.from)).toBe(0);
  });

  it('the drawing and the model both end with nothing lost', () => {
    expect(recoveredFraction(1)).toBe(1);
    expect(heatLossFraction(1)).toBeCloseTo(0, 6);
    const lossEdgesAtEnd = sceneAt(1).edges.filter((e) => e.edge.loss);
    expect(lossEdgesAtEnd).toEqual([]);
  });

  it('the drawing and the model both start with everything lost', () => {
    expect(recoveredFraction(0)).toBe(0);
    expect(heatLossFraction(0)).toBeCloseTo(1, 6);
    const lossEdgesAtStart = sceneAt(0).edges.filter((e) => e.edge.loss);
    expect(lossEdgesAtStart.length).toBeGreaterThanOrEqual(3);
  });
});

describe('reverse scroll retraces exactly', () => {
  it('the drawn scene is the same going back up', () => {
    const forward = SAMPLES.map((p) => JSON.stringify(sceneAt(p)));
    const backward = [...SAMPLES].reverse()
      .map((p) => JSON.stringify(sceneAt(p))).reverse();
    expect(backward).toEqual(forward);
  });

  it('the narrative is the same going back up', () => {
    const forward = SAMPLES.map((p) => JSON.stringify(narrativeAt(p)));
    const backward = [...SAMPLES].reverse()
      .map((p) => JSON.stringify(narrativeAt(p))).reverse();
    expect(backward).toEqual(forward);
  });

  it('recovered fraction never decreases going forward', () => {
    let previous = -1;
    for (const p of SAMPLES) {
      const value = recoveredFraction(p);
      expect(value, `progress ${p}`).toBeGreaterThanOrEqual(previous);
      previous = value;
    }
  });
});
