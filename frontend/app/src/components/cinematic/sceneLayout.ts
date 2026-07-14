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

// LEFT_ARM_CLAW / RIGHT_ARM_CLAW are defined further down, after
// `imageSpaceToCanvasPoint` (they're derived the same way as the joint points below).

/**
 * Raw source PNG dimensions and its `object-fit:cover` / `object-position`
 * crop (from `cinematic.css`'s `.eiq-cine__bg-img`) — the actual geometry
 * needed to convert a measured pixel in the source image into this file's
 * virtual 1600×900 canvas space, instead of guessing.
 */
export const HERO_IMAGE_SPACE = { w: 1536, h: 1024 }
export const HERO_OBJECT_POSITION = { x: 0.58, y: 0.42 } // desktop/tablet >1024px value
/** Reference viewport this file's derived points below were computed against. */
const REFERENCE_VIEWPORT = { w: 1920, h: 1080 }

/**
 * Converts a pixel measured directly in the source PNG into this file's
 * virtual 1600×900 canvas, replicating the browser's `object-fit:cover`
 * crop math for a given viewport. Exported so a future recalibration pass
 * can re-derive (or spot-check) any point here from a fresh pixel reading
 * instead of eyeballing a rendered screenshot.
 */
export function imageSpaceToCanvasPoint(
  px: number,
  py: number,
  viewport: { w: number; h: number } = REFERENCE_VIEWPORT,
  objectPosition: { x: number; y: number } = HERO_OBJECT_POSITION,
): { x: number; y: number } {
  const scale = Math.max(viewport.w / HERO_IMAGE_SPACE.w, viewport.h / HERO_IMAGE_SPACE.h)
  const scaledW = HERO_IMAGE_SPACE.w * scale
  const scaledH = HERO_IMAGE_SPACE.h * scale
  const cropX = (scaledW - viewport.w) * objectPosition.x
  const cropY = (scaledH - viewport.h) * objectPosition.y
  const screenX = px * scale - cropX
  const screenY = py * scale - cropY
  return { x: (screenX / viewport.w) * CANVAS_W, y: (screenY / viewport.h) * CANVAS_H }
}

/**
 * Joint points tracing each arm from its base pedestal to the claw, for the
 * joint-light/energy-travel effect. Derived systematically (not eyeballed):
 * pixel-measured directly in the source PNG via cropped/gridded inspection
 * (base/shoulder near the pedestal, elbow at the main visible bend, wrist
 * just before the tool head), then run through `imageSpaceToCanvasPoint`
 * above at the reference 1920×1080 viewport. Left-arm raw pixels: shoulder
 * (250,590), elbow (275,340), wrist (400,390). Right-arm raw pixels: wrist
 * (1150,390), elbow (1290,340), shoulder (1430,590).
 *
 * Previously flagged discrepancy — now resolved: the old `LEFT_ARM_CLAW`/
 * `RIGHT_ARM_CLAW` constants (155,235)/(1430,250) predated this derivation
 * and, run through the reverse of this same math, landed 15-20 canvas-percent
 * away from the actual claws (in empty background, not on the tool heads).
 * Confirmed visually via Playwright screenshots of the rendered hero and by
 * gridding/measuring the source PNG directly: the true claw/tool-head tips
 * sit just past each wrist point, at raw pixels (430,395) and (1125,395).
 * See LEFT_ARM_CLAW/RIGHT_ARM_CLAW below, now derived the same way as these.
 */
export const LEFT_ARM_SHOULDER = imageSpaceToCanvasPoint(250, 590)
export const LEFT_ARM_ELBOW = imageSpaceToCanvasPoint(275, 340)
export const LEFT_ARM_WRIST = imageSpaceToCanvasPoint(400, 390)

export const RIGHT_ARM_WRIST = imageSpaceToCanvasPoint(1150, 390)
export const RIGHT_ARM_ELBOW = imageSpaceToCanvasPoint(1290, 340)
export const RIGHT_ARM_SHOULDER = imageSpaceToCanvasPoint(1430, 590)

/** Claw / tool-head tip, just past the wrist — where beams originate and particles converge. */
export const LEFT_ARM_CLAW = imageSpaceToCanvasPoint(430, 395)
export const RIGHT_ARM_CLAW = imageSpaceToCanvasPoint(1125, 395)

/** Repair targets scattered over the industrial/smoke area, right of the globe. */
export const REPAIR_TARGETS = [
  { x: 1180, y: 340 },
  { x: 1300, y: 420 },
  { x: 1220, y: 500 },
  { x: 1350, y: 460 },
]

/** Approximate screen position of the smoke plume in the source image. */
export const SMOKE_AREA = { x: 1240, y: 400 }

/** Waste targets scattered over the pollution/water area, left of the globe — mirrors REPAIR_TARGETS. */
export const WASTE_TARGETS = [
  { x: 540, y: 340 },
  { x: 420, y: 420 },
  { x: 500, y: 500 },
  { x: 370, y: 460 },
]

/** Approximate screen position of the pollution/water area in the source image — mirrors SMOKE_AREA. */
export const POLLUTION_AREA = { x: 390, y: 380 }

/** Approximate screen position of the baked-in "VERIFIED / Outcomes" badge, bottom-center of the source image. */
export const VERIFY_BADGE = { x: 901, y: 830 }

/**
 * The five agent-label positions, hoisted here from AgentsScene.tsx's former
 * local constant so HeroCanvas's verify-beat data arcs and AgentsScene's
 * labels share one source of truth instead of two independently-maintained
 * copies.
 */
export const AGENT_POSITIONS = [
  { x: 300, y: 380 }, // near the left robotic arm
  { x: 620, y: 250 },
  { x: 860, y: 200 }, // near the globe
  { x: 1100, y: 250 },
  { x: 1350, y: 380 }, // near the right robotic arm
]
