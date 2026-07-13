/**
 * RepairSequence — late AI Agents sub-scene. Connection lines draw from two
 * nearby agents to a handful of repair targets over the industrial/smoke
 * area, a scan band sweeps once, bounded pulses fire at each target, and a
 * dark "smoke suppression" overlay ramps in followed by a soft green
 * "clean energy" reveal — both continuous scroll-linked opacity ramps, so
 * the change is progressive and fully reversible by scrolling back up.
 */
import { m, useTransform, type MotionValue } from 'framer-motion'
import { AGENTS_SUB_RANGES } from '../sceneRanges'
import { REPAIR_TARGETS, REPAIR_SOURCES, SMOKE_AREA, CANVAS_W, CANVAS_H, pct } from '../sceneLayout'

const LINKS: [number, number][] = [
  [0, 0],
  [0, 1],
  [1, 2],
  [1, 3],
]

function RepairLink({
  scrollYProgress,
  sourceIndex,
  targetIndex,
  index,
}: {
  scrollYProgress: MotionValue<number>
  sourceIndex: number
  targetIndex: number
  index: number
}) {
  const [start] = AGENTS_SUB_RANGES.repair
  const drawStart = start + index * 0.008
  const pathLength = useTransform(scrollYProgress, [drawStart, drawStart + 0.02], [0, 1])
  const opacity = useTransform(scrollYProgress, [drawStart, drawStart + 0.005], [0, 1])
  const from = REPAIR_SOURCES[sourceIndex]
  const to = REPAIR_TARGETS[targetIndex]

  return (
    <m.line
      x1={from.x}
      y1={from.y}
      x2={to.x}
      y2={to.y}
      stroke="var(--eiq-accent)"
      strokeWidth={1.2}
      strokeOpacity={0.5}
      strokeDasharray="4 3"
      style={{ pathLength, opacity }}
    />
  )
}

export default function RepairSequence({
  scrollYProgress,
  active,
}: {
  scrollYProgress: MotionValue<number>
  active: boolean
}) {
  const [start, end] = AGENTS_SUB_RANGES.repair
  const smokeOpacity = useTransform(scrollYProgress, [start, end], [0, 0.7])
  const cleanOpacity = useTransform(scrollYProgress, [start + 0.015, end], [0, 0.35])
  const scanX = useTransform(scrollYProgress, [start, start + 0.02], ['-20%', '120%'])
  const scanOpacity = useTransform(scrollYProgress, [start, start + 0.005, start + 0.018, start + 0.02], [0, 1, 1, 0])

  return (
    <>
      <m.div
        className="eiq-cine__smoke-suppress"
        style={{ left: pct(SMOKE_AREA.x, CANVAS_W), top: pct(SMOKE_AREA.y, CANVAS_H), opacity: smokeOpacity }}
        aria-hidden="true"
      />
      <m.div
        className="eiq-cine__clean-reveal"
        style={{ left: pct(SMOKE_AREA.x, CANVAS_W), top: pct(SMOKE_AREA.y, CANVAS_H), opacity: cleanOpacity }}
        aria-hidden="true"
      />

      <svg className="eiq-cine__repair-svg" viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        {LINKS.map(([s, t], i) => (
          <RepairLink key={`${s}-${t}`} scrollYProgress={scrollYProgress} sourceIndex={s} targetIndex={t} index={i} />
        ))}
      </svg>

      <div
        className="eiq-cine__repair-scan-track"
        style={{ left: pct(SMOKE_AREA.x - 180, CANVAS_W), top: pct(SMOKE_AREA.y - 140, CANVAS_H) }}
        aria-hidden="true"
      >
        <m.div className="eiq-cine__repair-scan" style={{ x: scanX, opacity: scanOpacity }} />
      </div>

      {REPAIR_TARGETS.map((point, i) => (
        <div
          key={`${point.x}-${point.y}`}
          className="eiq-cine__repair-target"
          style={{ left: pct(point.x, CANVAS_W), top: pct(point.y, CANVAS_H) }}
          aria-hidden="true"
        >
          <span className={`eiq-cine__repair-pulse${active ? ' is-active' : ''}`} style={{ animationDelay: `${i * 0.25}s` }} />
          <span className="eiq-cine__repair-dot" />
        </div>
      ))}
    </>
  )
}
