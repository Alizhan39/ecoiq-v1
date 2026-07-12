/**
 * Cinematic homepage hero — shared screen-space layout.
 *
 * All overlay positioning across scenes uses the same virtual 1600×900
 * canvas (resolution-independent — converted to % via `pct()`), so the
 * globe, arm claws, and repair targets line up consistently regardless of
 * viewport size. GLOBE_CENTER matches the existing HUB used by
 * EvidenceScene's convergence lines.
 */
export const CANVAS_W = 1600
export const CANVAS_H = 900

export function pct(v: number, span: number): string {
  return `${(v / span) * 100}%`
}

export const GLOBE_CENTER = { x: 860, y: 380 }
/** Circle diameter for the rotation overlay, in vh — keeps it screen-size relative. */
export const GLOBE_DIAMETER_VH = 46

export const LEFT_ARM_CLAW = { x: 155, y: 235 }
export const RIGHT_ARM_CLAW = { x: 1430, y: 250 }

/** Repair targets scattered over the industrial/smoke area, right of the globe. */
export const REPAIR_TARGETS = [
  { x: 1180, y: 340 },
  { x: 1300, y: 420 },
  { x: 1220, y: 500 },
  { x: 1350, y: 460 },
]

/** Two agent positions (from AgentsScene) nearest the repair area — sources for the connection lines. */
export const REPAIR_SOURCES = [
  { x: 1100, y: 250 }, // Capital Guardian
  { x: 1350, y: 380 }, // Verification Agent
]

/** Approximate screen position of the smoke plume in the source image. */
export const SMOKE_AREA = { x: 1240, y: 400 }
