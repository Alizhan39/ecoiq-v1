/**
 * GlobeRotationOverlay — fakes a slow globe rotation from the single static
 * photo. The base image never moves; three faint layers (rotating spoke
 * texture, drifting highlight, drifting shadow) are clipped to a circle over
 * the globe's screen position, all bound to scroll position within
 * AGENTS_SUB_RANGES.rotation — a bounded sweep, not a free-running loop, so
 * it naturally starts, plays once, and settles as the reader scrolls.
 */
import { m, useTransform, type MotionValue } from 'framer-motion'
import { AGENTS_SUB_RANGES } from './sceneRanges'
import { GLOBE_CENTER, GLOBE_DIAMETER_VH, CANVAS_W, CANVAS_H, pct } from './sceneLayout'

export default function GlobeRotationOverlay({ scrollYProgress }: { scrollYProgress: MotionValue<number> }) {
  const [start, end] = AGENTS_SUB_RANGES.rotation

  const overlayOpacity = useTransform(scrollYProgress, [start - 0.02, start + 0.01], [0, 1])
  const spokeRotate = useTransform(scrollYProgress, [start, end], [0, 48])
  const highlightShift = useTransform(scrollYProgress, [start, end], ['0%', '14%'])
  const shadowShift = useTransform(scrollYProgress, [start, end], ['0%', '-10%'])

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
    </m.div>
  )
}
