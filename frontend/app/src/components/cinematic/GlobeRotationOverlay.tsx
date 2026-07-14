/**
 * GlobeRotationOverlay — fakes a slow globe rotation from the single static
 * photo. The base image never moves; three faint layers (rotating spoke
 * texture, drifting highlight, drifting shadow) are clipped to a circle over
 * the globe's screen position, all bound to scroll position within
 * AGENTS_SUB_RANGES.rotation — a bounded sweep, not a free-running loop, so
 * it naturally starts, plays once, and settles as the reader scrolls. Quiet
 * during Observe/Detect by construction (opacity 0 until `rotation` begins).
 *
 * Refinement pass: the previous version's arm-response layer was one uniform
 * glow ring around the *whole* globe for both arms — generic "sci-fi noise"
 * rather than a localized response (Phase 6 finding). It's now two small
 * spot-glows positioned at the actual intervention points (`POLLUTION_AREA`
 * for waste, `SMOKE_AREA` for repair), each active only during its own arm's
 * window, so the cause→effect reads as "that specific spot changed," not
 * "the globe glows." `settledGlow` gives Phase 6's "after VERIFY, settle into
 * a visibly healthier, more stable state" — it ramps in once and holds
 * (doesn't fade back to zero) through Continue Monitoring, unlike the two
 * spot-glows which are transient per-intervention.
 */
import { m, useTransform, type MotionValue } from 'framer-motion'
import { AGENTS_SUB_RANGES, GLOBE_RESPONSE_RANGES } from './sceneRanges'
import { GLOBE_CENTER, GLOBE_DIAMETER_VH, CANVAS_W, CANVAS_H, POLLUTION_AREA, SMOKE_AREA, pct } from './sceneLayout'

export default function GlobeRotationOverlay({ scrollYProgress }: { scrollYProgress: MotionValue<number> }) {
  const [start, end] = AGENTS_SUB_RANGES.rotation

  const overlayOpacity = useTransform(scrollYProgress, [start - 0.02, start + 0.01], [0, 1])
  const spokeRotate = useTransform(scrollYProgress, [start, end], [0, 48])
  const highlightShift = useTransform(scrollYProgress, [start, end], ['0%', '14%'])
  const shadowShift = useTransform(scrollYProgress, [start, end], ['0%', '-10%'])

  const [verifyStart, verifyEnd] = GLOBE_RESPONSE_RANGES.verify
  const verifyPulse = useTransform(scrollYProgress, [verifyStart, verifyStart + 0.004, verifyEnd], [0, 1, 0.6])
  // Ramps in with verify and holds — the "healthier, stable" resting state, not a transient pulse.
  const settledGlow = useTransform(scrollYProgress, [verifyStart, verifyEnd], [0, 0.4])

  return (
    <m.div
      className="eiq-cine__globe-rotate"
      aria-hidden="true"
      style={{
        left: pct(GLOBE_CENTER.x, CANVAS_W),
        top: pct(GLOBE_CENTER.y, CANVAS_H),
        width: `${GLOBE_DIAMETER_VH}vh`,
        height: `${GLOBE_DIAMETER_VH}vh`,
        opacity: overlayOpacity,
      }}
    >
      <m.div className="eiq-cine__globe-spokes" style={{ rotate: spokeRotate }} />
      <m.div className="eiq-cine__globe-highlight" style={{ x: highlightShift, y: highlightShift }} />
      <m.div className="eiq-cine__globe-shadow" style={{ x: shadowShift, y: shadowShift }} />
      <m.div className="eiq-cine__globe-verify-pulse" style={{ opacity: verifyPulse }} />
      <m.div className="eiq-cine__globe-settled" style={{ opacity: settledGlow }} />
    </m.div>
  )
}

/**
 * Localized spot-glow, positioned in the *source-image* coordinate space
 * (POLLUTION_AREA/SMOKE_AREA are virtual-canvas points, not globe-relative),
 * so it's rendered as a sibling of the globe circle rather than a child —
 * kept in this file since it's part of the same "globe responds" system.
 */
export function GlobeInterventionSpots({ scrollYProgress }: { scrollYProgress: MotionValue<number> }) {
  const [wasteStart, wasteEnd] = GLOBE_RESPONSE_RANGES.waste
  const [repairStart, repairEnd] = GLOBE_RESPONSE_RANGES.repair
  const wasteSpotGlow = useTransform(scrollYProgress, [wasteStart, wasteStart + 0.015, wasteEnd], [0, 0.75, 0.3])
  const repairSpotGlow = useTransform(scrollYProgress, [repairStart, repairStart + 0.015, repairEnd], [0, 0.8, 0.35])

  return (
    <>
      <m.div
        className="eiq-cine__intervention-spot eiq-cine__intervention-spot--waste"
        style={{ left: pct(POLLUTION_AREA.x, CANVAS_W), top: pct(POLLUTION_AREA.y, CANVAS_H), opacity: wasteSpotGlow }}
        aria-hidden="true"
      />
      <m.div
        className="eiq-cine__intervention-spot eiq-cine__intervention-spot--repair"
        style={{ left: pct(SMOKE_AREA.x, CANVAS_W), top: pct(SMOKE_AREA.y, CANVAS_H), opacity: repairSpotGlow }}
        aria-hidden="true"
      />
    </>
  )
}
