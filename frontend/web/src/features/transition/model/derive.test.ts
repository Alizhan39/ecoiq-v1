/**
 * Baseline versus modernised, compared structurally.
 *
 * The claim this file exists to check is the one the whole prototype rests on:
 * the plant is not recoloured, it is rewired. Edges that carried loss are gone,
 * loops that did not exist are present, and the equipment on each end of the
 * heat path is different equipment.
 *
 * Comparing fingerprints rather than labels is deliberate. A test that asserted
 * "the label says Electrified" would pass on a plant that had changed nothing
 * but its captions, which is precisely the failure mode being guarded.
 */
import { describe, expect, it } from 'vitest';

import { BASELINE, FACILITY, FULL_MODERNISATION, HEAT_ONLY, ROLE } from './plant';
import {
  applyScenario, compareTopology, loopFlows, lossFlows, structuralFingerprint,
} from './derive';

const baseline = applyScenario(FACILITY, BASELINE);
const modernised = applyScenario(FACILITY, FULL_MODERNISATION);
const heatOnly = applyScenario(FACILITY, HEAT_ONLY);

describe('the baseline plant leaks', () => {
  it('has flows that leave the system carrying something useful', () => {
    const lost = lossFlows(baseline);
    expect(lost.length).toBeGreaterThanOrEqual(3);
    const kinds = lost.map((f) => f.kind);
    expect(kinds).toContain('thermal_energy');
    expect(kinds).toContain('water');
    expect(kinds).toContain('waste');
  });

  it('closes no loops at all', () => {
    expect(loopFlows(baseline)).toEqual([]);
  });

  it('burns fuel', () => {
    expect(baseline.flows.some((f) => f.kind === 'fuel')).toBe(true);
  });

  it('applying no interventions changes nothing', () => {
    expect(structuralFingerprint(baseline))
      .toBe(structuralFingerprint(FACILITY));
  });
});

describe('the modernised plant is a different graph', () => {
  it('has a different structural fingerprint', () => {
    expect(structuralFingerprint(modernised))
      .not.toBe(structuralFingerprint(baseline));
  });

  it('removed every loss flow it set out to address', () => {
    const before = lossFlows(baseline).length;
    const after = lossFlows(modernised).length;
    expect(after).toBeLessThan(before);
    // Heat, water and material losses are all addressed by the full scenario.
    expect(after).toBe(0);
  });

  it('closed loops that did not exist', () => {
    const loops = loopFlows(modernised);
    expect(loops.length).toBeGreaterThanOrEqual(3);
    expect(loopFlows(baseline).length).toBe(0);
  });

  it('retired the fired heater and introduced an electric one', () => {
    const ids = modernised.equipment.map((e) => e.id);
    expect(ids).not.toContain(ROLE.boiler);
    expect(ids).toContain(ROLE.electricHeater);
  });

  it('retired the fixed-speed motor and introduced a drive', () => {
    const ids = modernised.equipment.map((e) => e.id);
    expect(ids).not.toContain(ROLE.motor);
    expect(ids).toContain(ROLE.drive);
  });

  it('no longer burns fuel', () => {
    expect(modernised.flows.some((f) => f.kind === 'fuel')).toBe(false);
  });

  it('turned the waste sink into a recovery loop', () => {
    const ids = modernised.equipment.map((e) => e.id);
    expect(ids).not.toContain(ROLE.wasteSink);
    expect(ids).toContain(ROLE.materialRecovery);
    const returns = modernised.flows.filter(
      (f) => f.from === ROLE.materialRecovery && f.to === ROLE.process,
    );
    expect(returns.length).toBe(1);
  });

  it('routes water back to the process instead of discharging it', () => {
    expect(baseline.flows.some((f) => f.id === 'loss_water_discharge')).toBe(true);
    expect(modernised.flows.some((f) => f.id === 'loss_water_discharge')).toBe(false);
    const reuse = modernised.flows.find(
      (f) => f.from === ROLE.waterTreatment && f.to === ROLE.process,
    );
    expect(reuse?.state).toBe('reused');
  });

  it('reports the change as adds and removes, not as a redraw', () => {
    const diff = compareTopology(baseline, modernised);
    expect(diff.structurallyDifferent).toBe(true);
    expect(diff.removedEquipment).toContain(ROLE.boiler);
    expect(diff.addedEquipment).toContain(ROLE.electricHeater);
    expect(diff.lossFlowsAfter).toBeLessThan(diff.lossFlowsBefore);
    expect(diff.loopFlowsAfter).toBeGreaterThan(diff.loopFlowsBefore);
  });
});

describe('a partial scenario changes only what it addresses', () => {
  it('heat-only leaves the water discharge in place', () => {
    expect(heatOnly.flows.some((f) => f.id === 'loss_water_discharge')).toBe(true);
  });

  it('heat-only leaves the waste stream in place', () => {
    expect(heatOnly.flows.some((f) => f.id === 'process_waste')).toBe(true);
  });

  it('heat-only still electrifies', () => {
    expect(heatOnly.equipment.map((e) => e.id)).toContain(ROLE.electricHeater);
    expect(heatOnly.flows.some((f) => f.kind === 'fuel')).toBe(false);
  });

  it('sits structurally between baseline and full modernisation', () => {
    const fp = structuralFingerprint(heatOnly);
    expect(fp).not.toBe(structuralFingerprint(baseline));
    expect(fp).not.toBe(structuralFingerprint(modernised));
  });

  it('is not ranked against the other — no scenario claims to be better', () => {
    // Ranking needs costs; costs need a surveyed facility. Both scenarios
    // report unknown, so neither can be preferred by this model.
    expect(HEAT_ONLY.outcome.economic.capex).toBeNull();
    expect(FULL_MODERNISATION.outcome.economic.capex).toBeNull();
  });
});

describe('applying a scenario is pure', () => {
  it('does not mutate the facility it was given', () => {
    const before = structuralFingerprint(FACILITY);
    applyScenario(FACILITY, FULL_MODERNISATION);
    applyScenario(FACILITY, HEAT_ONLY);
    expect(structuralFingerprint(FACILITY)).toBe(before);
  });

  it('gives the same result every time', () => {
    const a = structuralFingerprint(applyScenario(FACILITY, FULL_MODERNISATION));
    const b = structuralFingerprint(applyScenario(FACILITY, FULL_MODERNISATION));
    expect(a).toBe(b);
  });

  it('applying twice is the same as applying once', () => {
    const once = applyScenario(FACILITY, FULL_MODERNISATION);
    const twice = applyScenario(once, FULL_MODERNISATION);
    expect(structuralFingerprint(twice)).toBe(structuralFingerprint(once));
  });
});
