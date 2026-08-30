/**
 * plant — one worked facility, and the scenarios applied to it.
 *
 * This is the bridge between the domain types and the drawing: a concrete
 * Facility built from the generic entities, the losses a diagnosis would find
 * in it, and the scenarios that address them.
 *
 * ILLUSTRATIVE, AND SAYS SO IN ITS OWN ID
 * ---------------------------------------
 * The facility id is `illustrative-plant`, not a site name, and its operator
 * is undefined rather than a real organisation. Nothing here describes a plant
 * anyone operates. Every quantity is null: this file names equipment and flows
 * and says nothing about how big any of them are.
 */
import type { Equipment, Facility, LossPoint, ResourceFlow } from '../domain/entities';
import type { Scenario } from '../domain/scenario';
import { baselineScenario, scenarioWith } from '../domain/scenario';

/** Role ids, shared with the intervention deltas. */
export const ROLE = {
  grid: 'grid',
  boiler: 'boiler',
  motor: 'motor',
  process: 'process',
  waterSource: 'water_source',
  wasteSink: 'waste_sink',
  output: 'output',
  drive: 'drive',
  electricHeater: 'electric_heater',
  heatExchanger: 'heat_exchanger',
  thermalStore: 'thermal_store',
  waterTreatment: 'water_treatment',
  materialRecovery: 'material_recovery',
  metering: 'metering',
} as const;

const equipment: Equipment[] = [
  { id: ROLE.grid, label: 'Grid connection', kind: 'grid_connection', origin: 'baseline', rating: null },
  { id: ROLE.boiler, label: 'Fired process heat', kind: 'boiler', origin: 'baseline', rating: null },
  { id: ROLE.motor, label: 'Fixed-speed motor', kind: 'motor', origin: 'baseline', rating: null },
  { id: ROLE.process, label: 'Industrial process', kind: 'process_unit', origin: 'baseline', rating: null },
  { id: ROLE.waterSource, label: 'Water system', kind: 'pump', origin: 'baseline', rating: null },
  { id: ROLE.wasteSink, label: 'Waste stream', kind: 'process_unit', origin: 'baseline', rating: null },
  { id: ROLE.output, label: 'Product output', kind: 'process_unit', origin: 'baseline', rating: null },

  { id: ROLE.drive, label: 'Variable-speed drive', kind: 'variable_speed_drive', origin: 'introduced', replacesId: ROLE.motor, rating: null },
  { id: ROLE.electricHeater, label: 'Electrified process heat', kind: 'electric_heater', origin: 'introduced', replacesId: ROLE.boiler, rating: null },
  { id: ROLE.heatExchanger, label: 'Heat recovery', kind: 'heat_exchanger', origin: 'introduced', rating: null },
  { id: ROLE.thermalStore, label: 'Thermal store', kind: 'storage', origin: 'introduced', rating: null },
  { id: ROLE.waterTreatment, label: 'Water treatment', kind: 'water_treatment', origin: 'introduced', rating: null },
  { id: ROLE.materialRecovery, label: 'Material recovery', kind: 'material_recovery', origin: 'introduced', rating: null },
  { id: ROLE.metering, label: 'Measurement', kind: 'metering', origin: 'introduced', rating: null },
];

/** The baseline flows: three of them leave the system carrying something. */
const baselineFlows: ResourceFlow[] = [
  { id: 'grid_boiler', kind: 'electricity', from: ROLE.grid, to: ROLE.boiler, state: 'productive', quantity: null },
  { id: 'fuel_boiler', kind: 'fuel', from: 'fuel_supply', to: ROLE.boiler, state: 'productive', quantity: null },
  { id: 'boiler_process', kind: 'thermal_energy', from: ROLE.boiler, to: ROLE.process, state: 'productive', quantity: null },
  { id: 'grid_motor', kind: 'electricity', from: ROLE.grid, to: ROLE.motor, state: 'productive', quantity: null },
  { id: 'motor_process', kind: 'electricity', from: ROLE.motor, to: ROLE.process, state: 'productive', quantity: null },
  { id: 'water_process', kind: 'water', from: ROLE.waterSource, to: ROLE.process, state: 'productive', quantity: null },
  { id: 'process_output', kind: 'material', from: ROLE.process, to: ROLE.output, state: 'productive', quantity: null },
  { id: 'process_waste', kind: 'waste', from: ROLE.process, to: ROLE.wasteSink, state: 'lost', quantity: null },

  { id: 'loss_heat_boiler', kind: 'thermal_energy', from: ROLE.boiler, to: 'atmosphere', state: 'lost', quantity: null },
  { id: 'loss_heat_process', kind: 'thermal_energy', from: ROLE.process, to: 'atmosphere', state: 'lost', quantity: null },
  { id: 'loss_water_discharge', kind: 'water', from: ROLE.process, to: 'discharge', state: 'lost', quantity: null },
];

export const FACILITY: Facility = {
  id: 'illustrative-plant',
  label: 'Illustrative industrial plant',
  // No operatorSlug: this is not anybody's site.
  processes: [{ id: ROLE.process, label: 'Industrial process', equipmentIds: [ROLE.process] }],
  equipment,
  flows: baselineFlows,
};

/**
 * What a diagnosis finds. Categories only — every magnitude is unknown.
 */
export const LOSSES: LossPoint[] = [
  { id: 'l_heat_boiler', type: 'HEAT_LOSS', label: 'Flue heat leaving the fired heater', atFlowId: 'loss_heat_boiler', magnitude: null, evidenceIds: [] },
  { id: 'l_heat_process', type: 'HEAT_LOSS', label: 'Heat rejected by the process', atFlowId: 'loss_heat_process', magnitude: null, evidenceIds: [] },
  { id: 'l_idle', type: 'IDLE_LOAD', label: 'Fixed-speed motor running above demand', atEquipmentId: ROLE.motor, magnitude: null, evidenceIds: [] },
  { id: 'l_water', type: 'WATER_DISCHARGE', label: 'Process water discharged after single use', atFlowId: 'loss_water_discharge', magnitude: null, evidenceIds: [] },
  { id: 'l_material', type: 'MATERIAL_WASTE', label: 'Material leaving as waste', atFlowId: 'process_waste', magnitude: null, evidenceIds: [] },
];

export const BASELINE: Scenario = baselineScenario(FACILITY);

/** The full modernisation the drawing walks through. */
export const FULL_MODERNISATION: Scenario = scenarioWith(
  FACILITY,
  'full',
  'Full modernisation',
  [
    'VARIABLE_SPEED_DRIVE',
    'PROCESS_ELECTRIFICATION',
    'HEAT_RECOVERY',
    'STORAGE',
    'WATER_REUSE',
    'MATERIAL_RECOVERY',
    'PROCESS_OPTIMISATION',
  ],
  LOSSES,
);

/**
 * A narrower alternative, so scenario comparison is real rather than a
 * placeholder for one.
 *
 * Deliberately NOT ranked against the other: ranking needs costs, costs need
 * a surveyed facility, and this model has neither. Two scenarios exist so the
 * shape supports comparison; nothing here says which is better.
 */
export const HEAT_ONLY: Scenario = scenarioWith(
  FACILITY,
  'heat-only',
  'Heat measures only',
  ['PROCESS_ELECTRIFICATION', 'HEAT_RECOVERY', 'STORAGE'],
  LOSSES,
);

export const SCENARIOS: readonly Scenario[] = [BASELINE, HEAT_ONLY, FULL_MODERNISATION];
