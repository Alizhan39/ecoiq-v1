/**
 * scenario — a named set of interventions applied to a facility.
 *
 * Baseline is a scenario with no interventions. That is not a technicality: it
 * means "the plant as it is" and "the plant as it could be" are the same kind
 * of object, comparable field by field, rather than a thing and a diff.
 *
 * NO ECONOMICS ARE CALCULATED HERE
 * --------------------------------
 * A scenario carries an Outcome whose economic and resource figures are all
 * null. Nothing in this file multiplies an assumed saving by an assumed tariff
 * to produce a payback period. When a facility is genuinely surveyed those
 * slots accept measured quantities; until then the honest value is unknown,
 * and a scenario comparison shows em dashes rather than a ranking built out of
 * defaults.
 */
import type { Facility, LossPoint, Outcome, QualitativeEffect } from './entities';
import type { InterventionType } from './interventions';
import { INTERVENTIONS } from './interventions';
import { unknownOutcome } from './unknown';

export interface Assumption {
  id: string;
  /** What is being assumed, stated so a reader can disagree with it. */
  statement: string;
  /**
   * Whether anything supports it yet. `evidenceIds` empty means this is a
   * stated assumption and must be shown to a reader as one.
   */
  evidenceIds: string[];
}

export interface Scenario {
  id: string;
  label: string;
  facilityId: string;
  /** Empty for the baseline. Order is application order. */
  interventions: InterventionType[];
  assumptions: Assumption[];
  /** Loss points this scenario is intended to address. */
  targetedLossIds: string[];
  outcome: Outcome;
}

/** The plant as it is: no interventions, nothing claimed, nothing verified. */
export function baselineScenario(facility: Facility): Scenario {
  const blank = unknownOutcome();
  return {
    id: 'baseline',
    label: 'Baseline',
    facilityId: facility.id,
    interventions: [],
    assumptions: [],
    targetedLossIds: [],
    outcome: {
      expected: [],
      economic: blank,
      resource: blank,
      verification: { state: 'NOT_VERIFIED', evidenceIds: [] },
    },
  };
}

/**
 * A scenario applying the given interventions.
 *
 * The qualitative effects are DERIVED from the intervention catalogue rather
 * than authored per scenario, so a scenario cannot claim an effect its
 * interventions do not support. The numbers stay unknown.
 */
export function scenarioWith(
  facility: Facility,
  id: string,
  label: string,
  interventions: InterventionType[],
  losses: LossPoint[] = [],
): Scenario {
  const blank = unknownOutcome();
  const expected: QualitativeEffect[] = [];
  const seen = new Set<string>();

  for (const type of interventions) {
    const definition = INTERVENTIONS[type];
    for (const lossType of definition.addresses) {
      const key = `${lossType}:${type}`;
      if (seen.has(key)) continue;
      seen.add(key);
      expected.push({
        lossType,
        // "reduces", never a percentage. A magnitude needs a measurement.
        direction: closesLoopFor(type) ? 'recovers' : 'reduces',
        rationale: definition.summary,
      });
    }
  }

  return {
    id,
    label,
    facilityId: facility.id,
    interventions,
    assumptions: [],
    targetedLossIds: losses
      .filter((l) => expected.some((e) => e.lossType === l.type))
      .map((l) => l.id),
    outcome: {
      expected,
      economic: blank,
      resource: blank,
      verification: { state: 'NOT_VERIFIED', evidenceIds: [] },
    },
  };
}

/** Does this intervention return a resource to the system? */
export function closesLoopFor(type: InterventionType): boolean {
  return INTERVENTIONS[type].delta.addsFlows.some((f) => f.closesLoop === true);
}

/**
 * Whether a scenario may be presented with numbers.
 *
 * False for everything the prototype builds. A caller that wants to render
 * capex or payback has to ask this first, and the answer is the reason the
 * semantic layer renders em dashes.
 */
export function hasQuantifiedOutcome(scenario: Scenario): boolean {
  const { economic, resource } = scenario.outcome;
  return Object.values({ ...economic, ...resource }).some((q) => q !== null);
}
