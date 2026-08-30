/**
 * interventions — what an engineering change DOES to the plant.
 *
 * THE POINT OF THIS FILE
 * ----------------------
 * An intervention that only changes a label is a slogan. Every entry here must
 * answer "what physical topology changes?", and the type makes that
 * unanswerable by omission: `TopologyDelta` has no optional escape hatch, and
 * `describeDelta()` refuses to produce a description for a delta that adds and
 * removes nothing.
 *
 * So "PROCESS_ELECTRIFICATION" cannot be satisfied by recolouring the boiler.
 * It retires the fired heat equipment, retires the fuel flow into it,
 * introduces an electric heater, and introduces an electricity flow from the
 * grid connection. If a delta does not say that, the catalogue test fails.
 *
 * WHAT IS DELIBERATELY ABSENT
 * ---------------------------
 * Cost, saving, payback, emissions. An intervention type knows what it does to
 * the plant; it does not know what it costs, because that depends on the
 * facility, the market and the year. Those live in Scenario.outcome and are
 * null until a real facility is surveyed.
 */
import type { EquipmentKind, LossType, ResourceKind } from './entities';

export type InterventionType =
  | 'HEAT_RECOVERY'
  | 'PROCESS_ELECTRIFICATION'
  | 'VARIABLE_SPEED_DRIVE'
  | 'WATER_REUSE'
  | 'MATERIAL_RECOVERY'
  | 'PROCESS_OPTIMISATION'
  | 'STORAGE'
  | 'RENEWABLE_INTEGRATION'
  | 'EQUIPMENT_REPLACEMENT';

/** Equipment this intervention introduces, by role rather than by product. */
export interface EquipmentAddition {
  role: string;
  kind: EquipmentKind;
  /** The equipment role it supersedes, when it is a substitution. */
  replacesRole?: string;
}

/** A flow this intervention introduces or removes, by role. */
export interface FlowChange {
  fromRole: string;
  toRole: string;
  kind: ResourceKind;
  /** A returning flow closes a loop rather than extending a line. */
  closesLoop?: boolean;
}

/**
 * The structural change, stated as adds and removes.
 *
 * Roles, not ids: a delta is a rule about any facility with the relevant
 * equipment, not an edit to one particular drawing. Binding roles to a
 * specific plant happens in scenario.ts.
 */
export interface TopologyDelta {
  addsEquipment: EquipmentAddition[];
  retiresEquipmentRoles: string[];
  addsFlows: FlowChange[];
  retiresFlowRoles: string[];
}

export interface InterventionDefinition {
  type: InterventionType;
  label: string;
  /** What it physically does, in one sentence, for the semantic layer. */
  summary: string;
  /** The losses it is capable of addressing. Not a promise about magnitude. */
  addresses: LossType[];
  delta: TopologyDelta;
  /**
   * Optional link to the governance layer.
   *
   * EMPTY ON PURPOSE. The architecture must support answering "why is this
   * intervention relevant under the 114-Principle framework", and populating
   * it speculatively would be inventing the answer. A principle mapping is a
   * claim about meaning and belongs to whoever owns the canon, not to a
   * prototype that happens to need a foreign key.
   */
  principleIds: number[];
  /** Evidence justifying the intervention. Empty until it exists. */
  evidenceIds: string[];
}

// ── The catalogue ────────────────────────────────────────────────────────────

export const INTERVENTIONS: Record<InterventionType, InterventionDefinition> = {
  HEAT_RECOVERY: {
    type: 'HEAT_RECOVERY',
    label: 'Heat recovery',
    summary:
      'Capture heat leaving the process and return it, so a quantity that '
      + 'was lost becomes an input.',
    addresses: ['HEAT_LOSS', 'UNRECOVERED_RESOURCE'],
    delta: {
      addsEquipment: [{ role: 'heat_exchanger', kind: 'heat_exchanger' }],
      retiresEquipmentRoles: [],
      addsFlows: [
        { fromRole: 'process', toRole: 'heat_exchanger', kind: 'thermal_energy' },
        { fromRole: 'heat_exchanger', toRole: 'process', kind: 'recovered_heat', closesLoop: true },
      ],
      retiresFlowRoles: ['loss_heat_process', 'loss_heat_boiler'],
    },
    principleIds: [],
    evidenceIds: [],
  },

  PROCESS_ELECTRIFICATION: {
    type: 'PROCESS_ELECTRIFICATION',
    label: 'Process electrification',
    summary:
      'Replace fired process heat with electric heat supplied from the grid '
      + 'connection, removing the fuel flow entirely.',
    addresses: ['ENERGY_INEFFICIENCY', 'HEAT_LOSS'],
    delta: {
      addsEquipment: [
        { role: 'electric_heater', kind: 'electric_heater', replacesRole: 'boiler' },
      ],
      retiresEquipmentRoles: ['boiler'],
      addsFlows: [
        { fromRole: 'grid', toRole: 'electric_heater', kind: 'electricity' },
        { fromRole: 'electric_heater', toRole: 'process', kind: 'thermal_energy' },
      ],
      retiresFlowRoles: ['fuel_boiler', 'boiler_process'],
    },
    principleIds: [],
    evidenceIds: [],
  },

  VARIABLE_SPEED_DRIVE: {
    type: 'VARIABLE_SPEED_DRIVE',
    label: 'Variable-speed drive',
    summary:
      'Match motor speed to demand instead of running fixed-speed, removing '
      + 'the idle load a fixed-speed motor carries whenever demand is below '
      + 'its rating.',
    addresses: ['IDLE_LOAD', 'ENERGY_INEFFICIENCY'],
    delta: {
      addsEquipment: [
        { role: 'drive', kind: 'variable_speed_drive', replacesRole: 'motor' },
      ],
      retiresEquipmentRoles: ['motor'],
      addsFlows: [
        { fromRole: 'grid', toRole: 'drive', kind: 'electricity' },
        { fromRole: 'drive', toRole: 'process', kind: 'electricity' },
      ],
      retiresFlowRoles: ['grid_motor', 'motor_process'],
    },
    principleIds: [],
    evidenceIds: [],
  },

  WATER_REUSE: {
    type: 'WATER_REUSE',
    label: 'Water reuse loop',
    summary:
      'Treat process water and return it to the process rather than '
      + 'discharging it, closing the water loop.',
    addresses: ['WATER_DISCHARGE', 'UNRECOVERED_RESOURCE'],
    delta: {
      addsEquipment: [{ role: 'water_treatment', kind: 'water_treatment' }],
      retiresEquipmentRoles: [],
      addsFlows: [
        { fromRole: 'process', toRole: 'water_treatment', kind: 'water' },
        { fromRole: 'water_treatment', toRole: 'process', kind: 'water', closesLoop: true },
      ],
      retiresFlowRoles: ['loss_water_discharge'],
    },
    principleIds: [],
    evidenceIds: [],
  },

  MATERIAL_RECOVERY: {
    type: 'MATERIAL_RECOVERY',
    label: 'Material recovery',
    summary:
      'Sort and reprocess the waste stream so recovered material re-enters '
      + 'the process as feedstock.',
    addresses: ['MATERIAL_WASTE', 'UNRECOVERED_RESOURCE'],
    delta: {
      addsEquipment: [{ role: 'material_recovery', kind: 'material_recovery' }],
      retiresEquipmentRoles: ['waste_sink'],
      addsFlows: [
        { fromRole: 'process', toRole: 'material_recovery', kind: 'material' },
        { fromRole: 'material_recovery', toRole: 'process', kind: 'material', closesLoop: true },
      ],
      retiresFlowRoles: ['process_waste'],
    },
    principleIds: [],
    evidenceIds: [],
  },

  STORAGE: {
    type: 'STORAGE',
    label: 'Thermal storage',
    summary:
      'Buffer recovered heat so supply and demand need not coincide, which is '
      + 'what makes recovery usable rather than merely captured.',
    addresses: ['UNRECOVERED_RESOURCE', 'PROCESS_BOTTLENECK'],
    delta: {
      addsEquipment: [{ role: 'thermal_store', kind: 'storage' }],
      retiresEquipmentRoles: [],
      addsFlows: [
        { fromRole: 'heat_exchanger', toRole: 'thermal_store', kind: 'recovered_heat' },
        { fromRole: 'thermal_store', toRole: 'electric_heater', kind: 'recovered_heat', closesLoop: true },
      ],
      retiresFlowRoles: [],
    },
    principleIds: [],
    evidenceIds: [],
  },

  RENEWABLE_INTEGRATION: {
    type: 'RENEWABLE_INTEGRATION',
    label: 'Renewable integration',
    summary:
      'Add on-site generation feeding the same grid connection, changing '
      + 'where electricity comes from rather than how much is used.',
    addresses: ['ENERGY_INEFFICIENCY'],
    delta: {
      addsEquipment: [{ role: 'onsite_generation', kind: 'grid_connection' }],
      retiresEquipmentRoles: [],
      addsFlows: [
        { fromRole: 'onsite_generation', toRole: 'grid', kind: 'electricity' },
      ],
      retiresFlowRoles: [],
    },
    principleIds: [],
    evidenceIds: [],
  },

  PROCESS_OPTIMISATION: {
    type: 'PROCESS_OPTIMISATION',
    label: 'Process optimisation',
    summary:
      'Coordinate the equipment that now exists — sequencing, setpoints and '
      + 'load balancing — and meter it, so the system runs as one rather than '
      + 'as parts.',
    addresses: ['PROCESS_BOTTLENECK', 'ENERGY_INEFFICIENCY', 'IDLE_LOAD'],
    delta: {
      addsEquipment: [{ role: 'metering', kind: 'metering' }],
      retiresEquipmentRoles: [],
      addsFlows: [
        { fromRole: 'process', toRole: 'metering', kind: 'electricity' },
      ],
      retiresFlowRoles: [],
    },
    principleIds: [],
    evidenceIds: [],
  },

  EQUIPMENT_REPLACEMENT: {
    type: 'EQUIPMENT_REPLACEMENT',
    label: 'Equipment replacement',
    summary:
      'Replace a unit at end of life with a more efficient equivalent, '
      + 'keeping the topology and changing the unit.',
    addresses: ['ENERGY_INEFFICIENCY'],
    delta: {
      addsEquipment: [
        { role: 'replacement_unit', kind: 'process_unit', replacesRole: 'process_unit' },
      ],
      retiresEquipmentRoles: ['process_unit'],
      addsFlows: [],
      retiresFlowRoles: [],
    },
    principleIds: [],
    evidenceIds: [],
  },
};

/** Does this delta change the plant at all? */
export function changesTopology(delta: TopologyDelta): boolean {
  return delta.addsEquipment.length > 0
    || delta.retiresEquipmentRoles.length > 0
    || delta.addsFlows.length > 0
    || delta.retiresFlowRoles.length > 0;
}

/**
 * A plain description of the structural change, for the semantic layer.
 *
 * Throws on an empty delta rather than returning "no change": an intervention
 * that changes nothing is a defect in the catalogue, and the place to find out
 * is here rather than in a reader's screen reader.
 */
export function describeDelta(delta: TopologyDelta): string[] {
  if (!changesTopology(delta)) {
    throw new Error(
      'Intervention delta changes no topology. An intervention that only '
      + 'changes a label is not an intervention.',
    );
  }
  const lines: string[] = [];
  for (const role of delta.retiresEquipmentRoles) lines.push(`retires ${role}`);
  for (const add of delta.addsEquipment) {
    lines.push(add.replacesRole
      ? `introduces ${add.role} in place of ${add.replacesRole}`
      : `introduces ${add.role}`);
  }
  for (const role of delta.retiresFlowRoles) lines.push(`removes flow ${role}`);
  for (const flow of delta.addsFlows) {
    lines.push(flow.closesLoop
      ? `returns ${flow.kind} from ${flow.fromRole} to ${flow.toRole}, closing a loop`
      : `routes ${flow.kind} from ${flow.fromRole} to ${flow.toRole}`);
  }
  return lines;
}
