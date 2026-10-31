/**
 * The narrative layer, checked against the model it is supposed to mirror.
 *
 * The property that matters: a reader who cannot see the drawing gets the same
 * information, from the same source, at the same scroll position. Not a
 * description of the picture — the thing the picture is drawn from.
 */
import { describe, expect, it } from 'vitest';

import { INTERVENTIONS } from '../domain/interventions';
import { BASELINE, FULL_MODERNISATION, HEAT_ONLY } from '../model/plant';
import { STAGES, stageAt } from '../model/stages';
import {
  NARRATIVE_DISCLAIMER, lossSummaries, narrativeAt, scenarioSummary,
} from './narrative';

const SAMPLES = Array.from({ length: 101 }, (_, i) => i / 100);

describe('the narrative matches the stage the drawing is in', () => {
  it('marks exactly one step current, at every scroll position', () => {
    for (const p of SAMPLES) {
      const current = narrativeAt(p).filter((s) => s.current);
      expect(current.length, `progress ${p}`).toBe(1);
    }
  });

  it('the current step is the stage the model reports', () => {
    for (const p of SAMPLES) {
      const fromNarrative = narrativeAt(p).find((s) => s.current)!.key;
      expect(fromNarrative, `progress ${p}`).toBe(stageAt(p).key);
    }
  });

  it('always lists every step, never a partial sequence', () => {
    for (const p of [0, 0.5, 1]) {
      expect(narrativeAt(p).map((s) => s.key)).toEqual(STAGES.map((s) => s.key));
    }
  });

  it('marks steps reached in order, and never un-reaches one', () => {
    let previousCount = -1;
    for (const p of SAMPLES) {
      const count = narrativeAt(p).filter((s) => s.reached).length;
      expect(count, `progress ${p}`).toBeGreaterThanOrEqual(previousCount);
      previousCount = count;
    }
  });

  it('has reached only the legacy step at the start', () => {
    const reached = narrativeAt(0).filter((s) => s.reached).map((s) => s.key);
    expect(reached).toEqual(['legacy']);
  });

  it('has reached every step at the end', () => {
    expect(narrativeAt(1).every((s) => s.reached)).toBe(true);
  });

  it('carries the eight stages the north star names', () => {
    expect(STAGES.map((s) => s.label)).toEqual([
      'Legacy system', 'Diagnose', 'Retrofit', 'Electrify',
      'Recover', 'Circularise', 'Optimise', 'Verify',
    ]);
  });
});

describe('every step explains itself without the picture', () => {
  it('has a meaning long enough to be a sentence, not a label', () => {
    for (const step of narrativeAt(0)) {
      expect(step.meaning.length, step.key).toBeGreaterThan(60);
    }
  });

  it('states the physical change where one happens', () => {
    const withChanges = narrativeAt(1).filter((s) => s.changes.length > 0);
    // Retrofit, electrify, recover, circularise, optimise all change the plant.
    expect(withChanges.length).toBeGreaterThanOrEqual(5);
  });

  it('describes changes in physical terms, not visual ones', () => {
    for (const step of narrativeAt(1)) {
      for (const change of step.changes) {
        expect(change, step.key).not.toMatch(/colour|color|fade|animate|draw/i);
      }
    }
  });

  it('the diagnose step changes nothing, because diagnosis does not', () => {
    const diagnose = narrativeAt(1).find((s) => s.key === 'diagnose')!;
    expect(diagnose.changes).toEqual([]);
    expect(diagnose.meaning).toMatch(/Nothing is changed/i);
  });

  it('names the losses each step addresses', () => {
    const circularise = narrativeAt(1).find((s) => s.key === 'circularise')!;
    const categories = circularise.addresses.map((l) => l.type);
    expect(categories).toContain('WATER_DISCHARGE');
    expect(categories).toContain('MATERIAL_WASTE');
  });
});

describe('the narrative reports no measurements', () => {
  it('every loss magnitude renders as an em dash', () => {
    for (const loss of lossSummaries()) {
      expect(loss.magnitude, loss.label).toBe('—');
    }
  });

  it('reports that no loss is evidenced yet', () => {
    expect(lossSummaries().every((l) => l.evidenced === false)).toBe(true);
  });

  it('contains no percentage anywhere in the rendered narrative', () => {
    const text = JSON.stringify(narrativeAt(1)) + JSON.stringify(lossSummaries());
    expect(text).not.toMatch(/\d+\s*%/);
  });

  it('says plainly that no scenario is costed', () => {
    for (const scenario of [BASELINE, HEAT_ONLY, FULL_MODERNISATION]) {
      const summary = scenarioSummary(scenario);
      expect(summary.quantified, scenario.id).toBe(false);
      expect(summary.outcomeNote).toMatch(/unknown rather than zero/);
    }
  });

  it('says nothing has been verified, and why that is different from failing', () => {
    const summary = scenarioSummary(FULL_MODERNISATION);
    expect(summary.verification).toMatch(/Not verified/);
    expect(summary.verification).toMatch(/not a record of one that happened/);
  });

  it('carries a disclaimer naming what the illustration is not', () => {
    expect(NARRATIVE_DISCLAIMER).toMatch(/no specific facility/i);
    expect(NARRATIVE_DISCLAIMER).toMatch(/no measured data/i);
  });
});

describe('the scenario summary is derived, not authored', () => {
  it('lists the physical change behind each intervention', () => {
    const summary = scenarioSummary(FULL_MODERNISATION);
    for (const intervention of summary.interventions) {
      expect(intervention.changes.length, intervention.label).toBeGreaterThan(0);
    }
  });

  it('every intervention it names exists in the catalogue', () => {
    const labels = Object.values(INTERVENTIONS).map((i) => i.label);
    for (const intervention of scenarioSummary(FULL_MODERNISATION).interventions) {
      expect(labels).toContain(intervention.label);
    }
  });

  it('the baseline summary claims nothing', () => {
    const summary = scenarioSummary(BASELINE);
    expect(summary.interventions).toEqual([]);
    expect(summary.expected).toEqual([]);
  });
});

describe('the narrative layer stands alone', () => {
  it('imports nothing from the view layer', async () => {
    const fs = await import('node:fs');
    const path = await import('node:path');
    const file = path.join(
      process.cwd(), 'src/features/transition/semantic/narrative.ts');
    // Comments stripped first. The header legitimately EXPLAINS that this
    // module knows nothing about canvas or SVG, and a grep over the raw file
    // would flag the documentation of the rule as a breach of it.
    const code = fs.readFileSync(file, 'utf8')
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/\/\/.*$/gm, '');
    expect(code).not.toMatch(/from ['"]react['"]/);
    expect(code).not.toMatch(/flowPainter|IndustrialTransitionScene/);
    expect(code).not.toMatch(/canvas|svg/i);
    expect(code).not.toMatch(/document\.|window\./);
  });

  it('is a pure function of progress', () => {
    expect(narrativeAt(0.42)).toEqual(narrativeAt(0.42));
  });

  it('clamps out-of-range progress rather than throwing', () => {
    expect(() => narrativeAt(-3)).not.toThrow();
    expect(() => narrativeAt(9)).not.toThrow();
    expect(narrativeAt(-3).find((s) => s.current)!.key).toBe('legacy');
    expect(narrativeAt(9).find((s) => s.current)!.key).toBe('verify');
  });
});
