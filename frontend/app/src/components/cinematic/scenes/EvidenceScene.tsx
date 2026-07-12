/**
 * EvidenceScene — Scene 2 (14–29%). Five evidence sources converge toward the
 * globe: SVG connection lines draw in on scroll (pathLength bound directly to
 * a scroll-derived MotionValue — the scroll-scrubbed sibling of the `drawPath`
 * preset, which is for discrete whileInView/animate triggers, not continuous
 * scroll values), labels pop in via the shared `popIn` preset once their scene
 * is active, and a handful of CSS-driven particles travel the same lines.
 */
import { m, useTransform, type MotionValue } from 'framer-motion'
import { popIn } from '../../../motion'
import { evidence } from '../content'

// Points in a virtual 1600×900 canvas (matches the background's cover-fit framing).
const HUB = { x: 860, y: 380 } // roughly where the globe sits in the source image
const SOURCES = [
  { x: 620, y: 210 },
  { x: 1080, y: 220 },
  { x: 520, y: 480 },
  { x: 1120, y: 500 },
  { x: 860, y: 680 },
]

const SCENE_START = 0.14
const SCENE_END = 0.29

function pct(v: number, span: number) {
  return `${(v / span) * 100}%`
}

function EvidenceLink({
  scrollYProgress,
  index,
}: {
  scrollYProgress: MotionValue<number>
  index: number
}) {
  const point = SOURCES[index]
  const drawStart = SCENE_START + index * 0.018
  const drawEnd = drawStart + 0.05
  const pathLength = useTransform(scrollYProgress, [drawStart, drawEnd], [0, 1])
  const opacity = useTransform(scrollYProgress, [drawStart, drawStart + 0.01], [0, 1])

  return (
    <m.line
      x1={point.x}
      y1={point.y}
      x2={HUB.x}
      y2={HUB.y}
      stroke="var(--eiq-accent)"
      strokeWidth={1.4}
      strokeOpacity={0.55}
      style={{ pathLength, opacity }}
    />
  )
}

export default function EvidenceScene({
  scrollYProgress,
  isActive,
}: {
  scrollYProgress: MotionValue<number>
  isActive: boolean
}) {
  const opacity = useTransform(
    scrollYProgress,
    [SCENE_START, SCENE_START + 0.02, SCENE_END - 0.03, SCENE_END],
    [0, 1, 1, 0],
  )

  return (
    <m.div className="eiq-cine__scene eiq-cine__scene--evidence" style={{ opacity }}>
      <div className="eiq-cine__scene-head">
        <p className="eiq-cine__scene-copy">{evidence.copy}</p>
      </div>

      <svg
        className="eiq-cine__evi-svg"
        viewBox="0 0 1600 900"
        preserveAspectRatio="xMidYMid slice"
        aria-hidden="true"
      >
        {SOURCES.map((_, i) => (
          <EvidenceLink key={evidence.sources[i]} scrollYProgress={scrollYProgress} index={i} />
        ))}
      </svg>

      {SOURCES.map((point, i) => (
        <div
          key={evidence.sources[i]}
          className={`eiq-cine__particle-track${isActive ? ' is-active' : ''}`}
          style={{
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            ['--eiq-track-d' as any]: `path("M${point.x},${point.y} L${HUB.x},${HUB.y}")`,
            animationDelay: `${i * 0.35}s`,
          }}
          aria-hidden="true"
        >
          <span className="eiq-cine__particle" />
        </div>
      ))}

      {SOURCES.map((point, i) => (
        <m.div
          key={evidence.sources[i]}
          className="eiq-cine__evi-label"
          style={{ left: pct(point.x, 1600), top: pct(point.y, 900) }}
          variants={popIn({ duration: 0.4, delay: i * 0.06 }, 0.85)}
          initial="hidden"
          animate={isActive ? 'show' : 'hidden'}
        >
          {evidence.sources[i]}
        </m.div>
      ))}
    </m.div>
  )
}
