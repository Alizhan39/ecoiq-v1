import { describe, expect, it } from 'vitest';
import {
  currentStage, EDGES, NODES, presence, recoveredFraction, sceneAt, span,
  stageProgress, STAGES,
} from './topology';

/**
 * The topology is the argument the drawing makes, so these test the argument
 * rather than the pixels: losses are replaced by recovery, legacy equipment is
 * replaced by modern equipment, and the system ends coordinated.
 */

describe('stage mapping is deterministic', () => {
  it('covers 0 to 1 with no gap and no overlap', () => {
    const stages = [...STAGES];
    expect(stages.at(0)?.from).toBe(0);
    expect(stages.at(-1)?.to).toBe(1);
    for (let i = 1; i < stages.length; i += 1) {
      expect(stages[i]?.from).toBe(stages[i - 1]?.to);
    }
  });

  it('resolves every progress to exactly one stage', () => {
    for (let p = 0; p <= 1.0001; p += 0.01) {
      expect(currentStage(p)).toBeDefined();
    }
  });

  it('starts in legacy and ends in verify', () => {
    expect(currentStage(0).key).toBe('legacy');
    expect(currentStage(1).key).toBe('verify');
  });

  it('clamps out-of-range progress rather than throwing', () => {
    expect(currentStage(-5).key).toBe('legacy');
    expect(currentStage(99).key).toBe('verify');
  });

  it('gives the same answer for the same input, always', () => {
    const a = sceneAt(0.42);
    const b = sceneAt(0.42);
    expect(a.nodes.map((n) => n.node.id)).toEqual(b.nodes.map((n) => n.node.id));
    expect(a.edges.map((e) => e.edge.id)).toEqual(b.edges.map((e) => e.edge.id));
  });
});

describe('span', () => {
  it('clamps at both ends', () => {
    expect(span(-1, 0, 1)).toBe(0);
    expect(span(2, 0, 1)).toBe(1);
  });

  it('does not divide by zero on a degenerate range', () => {
    expect(Number.isFinite(span(0.5, 0.5, 0.5))).toBe(true);
  });

  it('is linear in between', () => {
    expect(span(0.5, 0, 1)).toBeCloseTo(0.5);
    // Midpoint DERIVED from the stage, not hardcoded. This test held 0.225,
    // the midpoint of diagnose under the seven-stage boundaries, and went
    // stale the moment RECOVER was split out of CIRCULARISE. A test that
    // repeats a constant the source owns is a second copy of it.
    const diagnose = STAGES.find((s) => s.key === 'diagnose')!;
    const middle = (diagnose.from + diagnose.to) / 2;
    expect(stageProgress(middle, 'diagnose')).toBeCloseTo(0.5, 6);
  });
});

describe('the topology itself improves', () => {
  it('starts with losses leaving the system', () => {
    const early = sceneAt(0.05).edges.filter((e) => e.edge.loss);
    expect(early.length).toBeGreaterThan(0);
  });

  it('ends with no loss edges at all', () => {
    const late = sceneAt(1).edges.filter((e) => e.edge.loss);
    expect(late).toHaveLength(0);
  });

  it('replaces legacy equipment rather than merely hiding it', () => {
    const legacy = sceneAt(0.05).nodes.map((n) => n.node.id);
    const modern = sceneAt(1).nodes.map((n) => n.node.id);
    expect(legacy).toContain('boiler');
    expect(legacy).toContain('motor');
    expect(modern).not.toContain('boiler');
    expect(modern).not.toContain('motor');
    expect(modern).toContain('electricHeat');
    expect(modern).toContain('drive');
  });

  it('closes loops: recovery returns flow to the process', () => {
    const late = sceneAt(1).edges.map((e) => e.edge.id);
    expect(late).toContain('recovery-process');
    expect(late).toContain('exchanger-process');
    // Water returns THROUGH treatment, not straight back. This test named a
    // direct process->water edge, which was the shortcut the drawing used
    // before the domain model said what water reuse actually requires:
    // discharged water is not reusable until something has treated it.
    expect(late).toContain('process-treatment');
    expect(late).toContain('treatment-water');
  });

  it('the legacy plant burns fuel, and the modernised one does not', () => {
    // The arrow the whole exercise exists to remove. Not recoloured — gone.
    expect(sceneAt(0).edges.map((e) => e.edge.id)).toContain('fuel-boiler');
    expect(sceneAt(1).edges.map((e) => e.edge.id)).not.toContain('fuel-boiler');
    expect(sceneAt(1).nodes.map((n) => n.node.id)).not.toContain('fuel');
  });

  it('the legacy plant discharges water to a named sink', () => {
    // A self-loop hid the fact that water LEAVES. It now goes somewhere, and
    // that somewhere disappears when the loop closes.
    expect(sceneAt(0).nodes.map((n) => n.node.id)).toContain('discharge');
    expect(sceneAt(1).nodes.map((n) => n.node.id)).not.toContain('discharge');
  });

  it('every drawn node carries a recognisable equipment class', () => {
    // Colour is never the only difference between two pieces of equipment.
    for (const { node } of sceneAt(1).nodes) {
      expect(node.equipment, node.id).toBeTruthy();
    }
    // The boiler and its electric replacement must not share a symbol — the
    // point of ELECTRIFY is that the equipment changed.
    const boiler = NODES.find((n) => n.id === 'boiler')!;
    const electric = NODES.find((n) => n.id === 'electricHeat')!;
    expect(boiler.equipment).not.toBe(electric.equipment);
  });

  it('turns waste into recovery', () => {
    expect(sceneAt(0.05).nodes.map((n) => n.node.id)).toContain('waste');
    const late = sceneAt(1).nodes.map((n) => n.node.id);
    expect(late).not.toContain('waste');
    expect(late).toContain('recovery');
  });

  it('recovers more as it progresses, and never regresses', () => {
    let previous = -1;
    for (let p = 0; p <= 1.0001; p += 0.05) {
      const value = recoveredFraction(p);
      expect(value).toBeGreaterThanOrEqual(previous);
      previous = value;
    }
    expect(recoveredFraction(0)).toBe(0);
    expect(recoveredFraction(1)).toBe(1);
  });
});

describe('the drawing makes no product claim', () => {
  it('labels nothing as a sensor, agent, or live feed', () => {
    const text = [...NODES.map((n) => n.label), ...EDGES.map((e) => e.id)]
      .join(' ').toLowerCase();
    for (const claim of ['sensor', 'agent', 'autonomous', 'real-time',
                         'realtime', 'ai ', 'monitoring', 'live']) {
      expect(text).not.toContain(claim);
    }
  });

  it('never claims the system is fully sustainable', () => {
    const text = STAGES.map((s) => s.label).join(' ').toLowerCase();
    for (const claim of ['100%', 'zero', 'fully', 'sustainable', 'net zero']) {
      expect(text).not.toContain(claim);
    }
  });
});

describe('presence', () => {
  it('is zero before a node appears', () => {
    expect(presence({ appearsAt: 0.5 }, 0.2)).toBe(0);
  });

  it('is one well after it appears and before it retires', () => {
    expect(presence({ appearsAt: 0.1, retiredAt: 0.9 }, 0.5)).toBe(1);
  });

  it('is zero well after it retires', () => {
    expect(presence({ appearsAt: 0.1, retiredAt: 0.4 }, 0.9)).toBe(0);
  });

  it('never returns a value outside 0 to 1', () => {
    for (let p = -0.5; p <= 1.5; p += 0.05) {
      const value = presence({ appearsAt: 0.3, retiredAt: 0.7 }, p);
      expect(value).toBeGreaterThanOrEqual(0);
      expect(value).toBeLessThanOrEqual(1);
    }
  });
});
