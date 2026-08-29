/**
 * equipmentGlyphs — P&ID-flavoured symbols, one per equipment class.
 *
 * WHY RECOGNISABLE SHAPES AND NOT ICONS
 * -------------------------------------
 * The visual language is a process and instrumentation diagram, not a landing
 * page. An engineer should recognise a heat exchanger because it looks like the
 * symbol for one, and a reader who is not an engineer should still be able to
 * tell two pieces of equipment apart at a glance — which they cannot do if
 * everything is a rounded rectangle with a different colour.
 *
 * Colour is never the only difference. Every glyph has a distinct outline, so
 * the drawing survives greyscale, colour-blindness and a low-contrast screen.
 *
 * All paths are drawn in a 40×40 box centred on the origin, so a node can be
 * translated without scaling and the stroke width stays consistent.
 */
import type { EquipmentKind } from './domain/entities';

export interface Glyph {
  /** Path data, centred on (0,0) in a 40×40 box. */
  d: string;
  /** Whether the interior is filled — hollow reads as a vessel, filled as a block. */
  filled?: boolean;
  /** Extra strokes drawn inside, e.g. the tubes in an exchanger. */
  detail?: string;
}

export const EQUIPMENT_GLYPH: Record<EquipmentKind, Glyph> = {
  // Fired vessel: a drum with a flame beneath it.
  boiler: {
    d: 'M -11 -10 L 11 -10 L 11 8 L -11 8 Z',
    detail: 'M -6 12 q 2 -4 0 -6 q 3 2 3 6 M 3 12 q 2 -4 0 -6 q 3 2 3 6 M -11 -2 L 11 -2',
  },
  furnace: {
    d: 'M -11 -10 L 11 -10 L 11 10 L -11 10 Z',
    detail: 'M -5 10 L -5 -2 L 5 -2 L 5 10 M -11 -6 L 11 -6',
  },
  // Electric heat: the same vessel, with a resistive element instead of a flame.
  electric_heater: {
    d: 'M -11 -10 L 11 -10 L 11 8 L -11 8 Z',
    detail: 'M -7 0 l 3 -5 l 3 10 l 3 -10 l 3 5 M -11 -2 L 11 -2',
  },
  // The standard exchanger symbol: a circle crossed by the tube path.
  heat_exchanger: {
    d: 'M 0 -12 A 12 12 0 1 1 0 12 A 12 12 0 1 1 0 -12',
    detail: 'M -12 -5 L 6 -5 A 4 4 0 0 1 6 3 L -12 3',
  },
  // Motor: circle with M. The letter is drawn, not typeset, so it needs no font.
  motor: {
    d: 'M 0 -11 A 11 11 0 1 1 0 11 A 11 11 0 1 1 0 -11',
    detail: 'M -5 4 L -5 -4 L 0 1 L 5 -4 L 5 4',
  },
  // VSD: the motor circle inside a drive enclosure, with the speed ramp.
  variable_speed_drive: {
    d: 'M -12 -10 L 12 -10 L 12 10 L -12 10 Z',
    detail: 'M -8 6 L 8 -6 M -8 -6 L -8 6 M -8 6 L 8 6',
  },
  // Pump: circle with an impeller triangle.
  pump: {
    d: 'M 0 -10 A 10 10 0 1 1 0 10 A 10 10 0 1 1 0 -10',
    detail: 'M -4 -6 L 6 0 L -4 6 Z',
  },
  compressor: {
    d: 'M 0 -10 A 10 10 0 1 1 0 10 A 10 10 0 1 1 0 -10',
    detail: 'M -7 6 L 7 -2 L -7 -2',
  },
  // Process unit: the block everything else serves.
  process_unit: {
    d: 'M -14 -11 L 14 -11 L 14 11 L -14 11 Z',
    detail: 'M -14 -5 L 14 -5 M -8 -11 L -8 11 M 6 -11 L 6 11',
  },
  // Grid connection: the supply comb.
  grid_connection: {
    d: 'M -10 -10 L 10 -10 M -10 -3 L 10 -3 M -10 4 L 10 4',
    detail: 'M 0 -10 L 0 11 M -5 11 L 5 11',
  },
  // Storage: a tank with a level line.
  storage: {
    d: 'M -10 -9 A 10 4 0 0 1 10 -9 L 10 9 A 10 4 0 0 1 -10 9 Z',
    detail: 'M -10 2 A 10 4 0 0 0 10 2',
  },
  // Water treatment: a vessel with settling layers.
  water_treatment: {
    d: 'M -11 -9 L 11 -9 L 11 9 L -11 9 Z',
    detail: 'M -11 0 q 5 -4 11 0 q 5 4 11 0 M -11 5 q 5 -4 11 0 q 5 4 11 0',
  },
  // Material recovery: the sorting chevrons feeding a return.
  material_recovery: {
    d: 'M -12 -9 L 12 -9 L 6 9 L -6 9 Z',
    detail: 'M -7 -3 L 0 3 L 7 -3',
  },
  // Metering: the instrument bubble, which in P&ID is exactly a circle.
  metering: {
    d: 'M 0 -10 A 10 10 0 1 1 0 10 A 10 10 0 1 1 0 -10',
    detail: 'M -10 0 L 10 0 M -5 5 L -1 -3 L 3 2 L 7 -5',
  },
};

/** Fallback for a kind with no glyph, so an unknown never renders as nothing. */
export const UNKNOWN_GLYPH: Glyph = {
  d: 'M -10 -10 L 10 -10 L 10 10 L -10 10 Z',
  detail: 'M -10 -10 L 10 10 M 10 -10 L -10 10',
};

export function glyphFor(kind: string): Glyph {
  return EQUIPMENT_GLYPH[kind as EquipmentKind] ?? UNKNOWN_GLYPH;
}
