/**
 * Shared Kazakhstan geometry for the Transition Brief visuals.
 *
 * A stylized, recognizable Kazakhstan silhouette (not survey-accurate borders —
 * intentionally designed for an institutional data visual) in a 1000×480
 * viewBox, plus the relative positions of the four focus regions used across
 * the Hero and Transition Map.
 */

export const KZ_VIEWBOX = '0 0 1000 480'

/** Stylized landmass outline. */
export const KZ_PATH =
  'M120,170 L185,128 L255,118 L300,80 L362,98 L420,78 L472,102 L520,86 ' +
  'L560,116 L640,104 L700,134 L762,122 L840,152 L902,142 L952,184 ' +
  'L928,236 L876,256 L902,300 L850,332 L800,322 L762,360 L700,382 ' +
  'L660,360 L600,384 L540,360 L470,384 L420,360 L360,382 L300,360 ' +
  'L250,332 L200,344 L150,302 L132,252 L162,212 Z'

export interface RegionGeo {
  id: string
  x: number
  y: number
}

/** Focus regions (southern Kazakhstan cluster), spread for legibility. */
export const KZ_REGIONS: RegionGeo[] = [
  { id: 'almaty', x: 872, y: 338 },
  { id: 'shymkent', x: 648, y: 378 },
  { id: 'turkistan', x: 584, y: 360 },
  { id: 'karatau', x: 536, y: 346 },
]

export function regionXY(id: string): RegionGeo | undefined {
  return KZ_REGIONS.find((r) => r.id === id)
}
