/**
 * derive — apply a scenario's interventions to a facility and see what changed.
 *
 * This is where "the graph genuinely changes" stops being a claim about the
 * drawing and becomes a computation over the domain. `applyScenario` takes the
 * baseline plant and the intervention deltas and returns a new facility; the
 * test compares the two structurally and fails if the modernised plant is the
 * baseline with different labels.
 *
 * Roles are ids here. The deltas in domain/interventions.ts are written
 * against role names, and model/plant.ts names its equipment with exactly
 * those roles, so binding is identity. That is deliberate: a mapping layer
 * between them would be a place for the two to drift apart.
 */
import type { Equipment, Facility, ResourceFlow } from '../domain/entities';
import { INTERVENTIONS } from '../domain/interventions';
import type { Scenario } from '../domain/scenario';

/** Apply every intervention in a scenario, in order. */
export function applyScenario(facility: Facility, scenario: Scenario): Facility {
  let equipment = [...facility.equipment.filter((e) => e.origin === 'baseline')];
  let flows = [...facility.flows];

  for (const type of scenario.interventions) {
    const { delta } = INTERVENTIONS[type];

    equipment = equipment.filter((e) => !delta.retiresEquipmentRoles.includes(e.id));
    flows = flows.filter((f) => !delta.retiresFlowRoles.includes(f.id));

    for (const add of delta.addsEquipment) {
      if (equipment.some((e) => e.id === add.role)) continue;
      const template = facility.equipment.find((e) => e.id === add.role);
      equipment.push(template ?? {
        id: add.role,
        label: add.role,
        kind: add.kind,
        origin: 'introduced',
        replacesId: add.replacesRole,
        rating: null,
      } as Equipment);
    }

    for (const add of delta.addsFlows) {
      const id = `${add.fromRole}__${add.toRole}`;
      if (flows.some((f) => f.id === id)) continue;
      flows.push({
        id,
        kind: add.kind,
        from: add.fromRole,
        to: add.toRole,
        // A returning flow is reuse; a new forward flow is productive.
        state: add.closesLoop ? 'reused' : 'productive',
        quantity: null,
      } as ResourceFlow);
    }
  }

  return { ...facility, equipment, flows };
}

/** Flows that leave the system carrying something useful. */
export function lossFlows(facility: Facility): ResourceFlow[] {
  return facility.flows.filter((f) => f.state === 'lost');
}

/** Flows that return a resource to an earlier point — a closed loop. */
export function loopFlows(facility: Facility): ResourceFlow[] {
  return facility.flows.filter((f) => f.state === 'reused' || f.state === 'recovered');
}

/**
 * A structural fingerprint: the set of directed edges, ignoring labels.
 *
 * Two plants with the same fingerprint are the same graph however they are
 * captioned. The test that baseline and modernised differ compares these, so
 * "recolour the boiler and call it electrified" cannot pass.
 */
export function structuralFingerprint(facility: Facility): string {
  return facility.flows
    .map((f) => `${f.from}>${f.to}:${f.kind}`)
    .sort()
    .join('|');
}

export interface TopologyComparison {
  addedEquipment: string[];
  removedEquipment: string[];
  addedFlows: string[];
  removedFlows: string[];
  lossFlowsBefore: number;
  lossFlowsAfter: number;
  loopFlowsBefore: number;
  loopFlowsAfter: number;
  structurallyDifferent: boolean;
}

export function compareTopology(before: Facility, after: Facility): TopologyComparison {
  const beforeEquip = new Set(before.equipment.map((e) => e.id));
  const afterEquip = new Set(after.equipment.map((e) => e.id));
  const beforeFlows = new Set(before.flows.map((f) => f.id));
  const afterFlows = new Set(after.flows.map((f) => f.id));

  return {
    addedEquipment: [...afterEquip].filter((id) => !beforeEquip.has(id)),
    removedEquipment: [...beforeEquip].filter((id) => !afterEquip.has(id)),
    addedFlows: [...afterFlows].filter((id) => !beforeFlows.has(id)),
    removedFlows: [...beforeFlows].filter((id) => !afterFlows.has(id)),
    lossFlowsBefore: lossFlows(before).length,
    lossFlowsAfter: lossFlows(after).length,
    loopFlowsBefore: loopFlows(before).length,
    loopFlowsAfter: loopFlows(after).length,
    structurallyDifferent:
      structuralFingerprint(before) !== structuralFingerprint(after),
  };
}
