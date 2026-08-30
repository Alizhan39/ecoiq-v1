/**
 * The domain model's own rules.
 *
 * Three things this file is really enforcing:
 *   1. an intervention changes physical topology, not a label;
 *   2. no economic or environmental figure is ever fabricated;
 *   3. the physical model does not depend on the governance model.
 */
import fs from 'node:fs';
import path from 'node:path';

import { describe, expect, it } from 'vitest';

import type { InterventionType } from './interventions';
import { INTERVENTIONS, changesTopology, describeDelta } from './interventions';
import { LOSS_PRINCIPLE_LINKS, PRINCIPLE_LINKS, hasGovernanceContext, principlesFor } from './links';
import { baselineScenario, hasQuantifiedOutcome, scenarioWith } from './scenario';
import { displayQuantity, hasAnyMeasurement, isReportable, unknownOutcome } from './unknown';
import { FACILITY, LOSSES } from '../model/plant';

const TYPES = Object.keys(INTERVENTIONS) as InterventionType[];
const HERE = path.join(process.cwd(), 'src/features/transition');

describe('every intervention changes the plant', () => {
  it('has a delta that adds or removes something', () => {
    for (const type of TYPES) {
      expect(changesTopology(INTERVENTIONS[type].delta), type).toBe(true);
    }
  });

  it('can describe that change in physical terms', () => {
    for (const type of TYPES) {
      const lines = describeDelta(INTERVENTIONS[type].delta);
      expect(lines.length, type).toBeGreaterThan(0);
      for (const line of lines) {
        expect(line, type).toMatch(
          /retires|introduces|removes flow|routes|returns/,
        );
      }
    }
  });

  it('refuses to describe a delta that changes nothing', () => {
    expect(() => describeDelta({
      addsEquipment: [], retiresEquipmentRoles: [],
      addsFlows: [], retiresFlowRoles: [],
    })).toThrow(/only changes a label is not an intervention/);
  });

  it('names at least one loss category it addresses', () => {
    for (const type of TYPES) {
      expect(INTERVENTIONS[type].addresses.length, type).toBeGreaterThan(0);
    }
  });

  it('electrification removes the fuel flow rather than relabelling it', () => {
    const delta = INTERVENTIONS.PROCESS_ELECTRIFICATION.delta;
    expect(delta.retiresFlowRoles).toContain('fuel_boiler');
    expect(delta.retiresEquipmentRoles).toContain('boiler');
    expect(delta.addsEquipment.map((e) => e.role)).toContain('electric_heater');
  });

  it('the loop-closing interventions actually return a flow', () => {
    for (const type of ['HEAT_RECOVERY', 'WATER_REUSE', 'MATERIAL_RECOVERY'] as const) {
      const returns = INTERVENTIONS[type].delta.addsFlows.filter((f) => f.closesLoop);
      expect(returns.length, type).toBeGreaterThan(0);
    }
  });
});

describe('nothing is costed, and nothing pretends to be', () => {
  it('a fresh outcome is entirely unknown', () => {
    const outcome = unknownOutcome();
    for (const [field, value] of Object.entries(outcome)) {
      expect(value, field).toBeNull();
    }
    expect(hasAnyMeasurement(outcome)).toBe(false);
  });

  it('an unknown quantity renders as an em dash, never a zero', () => {
    expect(displayQuantity(null)).toBe('—');
    expect(displayQuantity(null)).not.toContain('0');
  });

  it('an illustrative quantity is not reportable as fact', () => {
    expect(isReportable({ value: 42, unit: 'kWh', basis: 'illustrative' })).toBe(false);
    expect(isReportable({ value: 42, unit: 'kWh', basis: 'assumed' })).toBe(false);
    expect(isReportable({ value: 42, unit: 'kWh', basis: 'measured' })).toBe(true);
  });

  it('no scenario the prototype builds carries a number', () => {
    const baseline = baselineScenario(FACILITY);
    const full = scenarioWith(FACILITY, 'x', 'X', TYPES, LOSSES);
    expect(hasQuantifiedOutcome(baseline)).toBe(false);
    expect(hasQuantifiedOutcome(full)).toBe(false);
  });

  it('every loss magnitude is unknown', () => {
    for (const loss of LOSSES) {
      expect(loss.magnitude, loss.id).toBeNull();
    }
  });

  it('no source file contains a fabricated payback or saving figure', () => {
    // The failure this guards is somebody adding "payback: 3.4" to make a
    // demo look finished. Greps the domain and model, not the tests.
    const files = ['domain', 'model', 'semantic'].flatMap((dir) =>
      fs.readdirSync(path.join(HERE, dir))
        .filter((f) => f.endsWith('.ts') && !f.includes('.test.'))
        .map((f) => path.join(HERE, dir, f)));
    for (const file of files) {
      const body = fs.readFileSync(file, 'utf8');
      expect(body, file).not.toMatch(/payback\s*:\s*[0-9]/i);
      expect(body, file).not.toMatch(/capex\s*:\s*[0-9]/i);
      expect(body, file).not.toMatch(/annualSavings\s*:\s*[0-9]/i);
      expect(body, file).not.toMatch(/emissionsAvoided\s*:\s*[0-9]/i);
    }
  });
});

describe('the expected effects come from the interventions, not from prose', () => {
  it('a scenario claims no effect its interventions do not support', () => {
    const scenario = scenarioWith(FACILITY, 's', 'S', ['WATER_REUSE'], LOSSES);
    const claimed = new Set(scenario.outcome.expected.map((e) => e.lossType));
    for (const lossType of claimed) {
      expect(INTERVENTIONS.WATER_REUSE.addresses).toContain(lossType);
    }
  });

  it('a baseline claims nothing at all', () => {
    const baseline = baselineScenario(FACILITY);
    expect(baseline.outcome.expected).toEqual([]);
    expect(baseline.interventions).toEqual([]);
  });

  it('no expected effect carries a magnitude', () => {
    const scenario = scenarioWith(FACILITY, 's', 'S', TYPES, LOSSES);
    for (const effect of scenario.outcome.expected) {
      expect(['reduces', 'eliminates', 'recovers', 'no_effect'])
        .toContain(effect.direction);
      expect(effect.rationale).not.toMatch(/\d+\s*%/);
    }
  });

  it('nothing is verified, because nothing has been built', () => {
    const scenario = scenarioWith(FACILITY, 's', 'S', TYPES, LOSSES);
    expect(scenario.outcome.verification.state).toBe('NOT_VERIFIED');
    expect(scenario.outcome.verification.evidenceIds).toEqual([]);
  });
});

describe('governance and physics stay separate but linkable', () => {
  it('ships no speculative principle mappings', () => {
    expect(Object.keys(PRINCIPLE_LINKS)).toEqual([]);
    expect(Object.keys(LOSS_PRINCIPLE_LINKS)).toEqual([]);
    for (const type of TYPES) {
      expect(principlesFor(type), type).toEqual([]);
      expect(hasGovernanceContext(type), type).toBe(false);
    }
  });

  it('the physical model imports nothing from the assessment layer', () => {
    // The separation is the point of the whole file layout. A grep is the only
    // thing that keeps it true once somebody needs a company name in a hurry.
    const files = fs.readdirSync(path.join(HERE, 'domain'))
      .filter((f) => f.endsWith('.ts') && !f.includes('.test.'));
    for (const file of files) {
      const body = fs.readFileSync(path.join(HERE, 'domain', file), 'utf8');
      expect(body, file).not.toMatch(/from ['"]@\/types\/kpi/);
      expect(body, file).not.toMatch(/from ['"].*\/features\/kpi/);
      expect(body, file).not.toMatch(/CompanyProfile|KpiInvestigation/);
    }
  });

  it('the domain carries no presentation concepts', () => {
    // No coordinates, no opacity, no stages. Those belong to the drawing.
    const files = fs.readdirSync(path.join(HERE, 'domain'))
      .filter((f) => f.endsWith('.ts') && !f.includes('.test.'));
    for (const file of files) {
      const body = fs.readFileSync(path.join(HERE, 'domain', file), 'utf8');
      expect(body, file).not.toMatch(/\bopacity\b/);
      expect(body, file).not.toMatch(/\bappearsAt\b/);
      expect(body, file).not.toMatch(/\bcanvas\b/i);
    }
  });

  it('every evidence slot exists and is empty', () => {
    for (const type of TYPES) {
      expect(INTERVENTIONS[type].evidenceIds, type).toEqual([]);
    }
    for (const loss of LOSSES) {
      expect(loss.evidenceIds, loss.id).toEqual([]);
    }
  });
});

describe('the facility describes nobody', () => {
  it('names no operating organisation', () => {
    expect(FACILITY.operatorSlug).toBeUndefined();
  });

  it('is labelled as illustrative in its own id', () => {
    expect(FACILITY.id).toContain('illustrative');
  });

  it('carries no equipment rating', () => {
    for (const item of FACILITY.equipment) {
      expect(item.rating, item.id).toBeNull();
    }
  });
});
