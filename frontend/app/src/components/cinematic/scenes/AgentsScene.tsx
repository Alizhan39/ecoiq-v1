/**
 * AgentsScene — Scene 3 (29–50%, widened this pass — see sceneRanges.ts).
 * Five agent labels stagger in around the central visual via the shared
 * `popIn` preset, each with a small status node. The robotic arms get a
 * restrained overlay glow (opacity only) rather than any transform on the
 * source image itself.
 *
 * Sub-staged via AGENTS_SUB_RANGES: rotation begins early, arms engage in
 * the middle (and stay engaged through waste and repair), waste (left arm)
 * plays out, then repair (right arm) activates only once waste is mostly
 * settled, then verify gets its own dedicated window (not a sliver of
 * repair's tail) before the scene releases into Pillars. `flags` are
 * independent booleans (one per sub-stage) rather than a single
 * mutually-exclusive phase — waste and repair's ranges overlap slightly for
 * a continuous feel, so both need to be able to read `true` at once without
 * one clobbering the other. `restoreSettled`/`stabilizeSettled` gate the
 * metrics specifically: they only flip true once each intervention's *later*
 * portion is reached, so a metric appears after its physical result is
 * visually established, not the instant the beat starts (Phase 4 — "metric
 * appears only after restoration/stabilization is visibly established").
 */
import { m, useTransform, useMotionValueEvent, type MotionValue } from 'framer-motion'
import { useState } from 'react'
import { popIn } from '../../../motion'
import { useCountUp } from '../../../hooks/useCountUp'
import { agents, stewardship, type StewardshipMetric } from '../content'
import { AGENTS_SUB_RANGES, GLOBE_RESPONSE_RANGES } from '../sceneRanges'
import { VERIFY_BADGE, CANVAS_W, CANVAS_H, AGENT_POSITIONS } from '../sceneLayout'
import ArmEngagement from './ArmEngagement'
import WasteRestoration from './WasteRestoration'
import RepairSequence from './RepairSequence'

const SCENE_START = 0.29
const SCENE_END = 0.5

const VERIFY_START = GLOBE_RESPONSE_RANGES.verify[0]
/** Metrics wait until the later portion of each intervention — result-first, not beat-first. */
const RESTORE_SETTLED_AT = AGENTS_SUB_RANGES.waste[0] + (AGENTS_SUB_RANGES.waste[1] - AGENTS_SUB_RANGES.waste[0]) * 0.72
const STABILIZE_SETTLED_AT =
  AGENTS_SUB_RANGES.repair[0] + (AGENTS_SUB_RANGES.repair[1] - AGENTS_SUB_RANGES.repair[0]) * 0.72

interface AgentsFlags {
  rotation: boolean
  arms: boolean
  waste: boolean
  repair: boolean
  restoreSettled: boolean
  stabilizeSettled: boolean
  verify: boolean
}

function useAgentsFlags(scrollYProgress: MotionValue<number>): AgentsFlags {
  const [flags, setFlags] = useState<AgentsFlags>({
    rotation: false,
    arms: false,
    waste: false,
    repair: false,
    restoreSettled: false,
    stabilizeSettled: false,
    verify: false,
  })
  useMotionValueEvent(scrollYProgress, 'change', (v) => {
    const next: AgentsFlags = {
      rotation: v >= AGENTS_SUB_RANGES.rotation[0],
      arms: v >= AGENTS_SUB_RANGES.arms[0],
      waste: v >= AGENTS_SUB_RANGES.waste[0],
      repair: v >= AGENTS_SUB_RANGES.repair[0],
      restoreSettled: v >= RESTORE_SETTLED_AT,
      stabilizeSettled: v >= STABILIZE_SETTLED_AT,
      verify: v >= VERIFY_START,
    }
    setFlags((prev) =>
      prev.rotation === next.rotation &&
      prev.arms === next.arms &&
      prev.waste === next.waste &&
      prev.repair === next.repair &&
      prev.restoreSettled === next.restoreSettled &&
      prev.stabilizeSettled === next.stabilizeSettled &&
      prev.verify === next.verify
        ? prev
        : next,
    )
  })
  return flags
}

function pct(v: number, span: number) {
  return `${(v / span) * 100}%`
}

/**
 * Renders a single count-up metric. useCountUp rounds to an integer
 * internally (by design — see hooks/useCountUp.ts, not modified here since
 * v1 primitives are locked), so a fractional target like 2.4 is animated as
 * a scaled integer (24) and divided back down for display — keeps the
 * hook untouched while still landing on the correct final value.
 */
function MetricValue({ metric, run }: { metric: StewardshipMetric; run: boolean }) {
  const isDecimal = !Number.isInteger(metric.value)
  const scaledTarget = isDecimal ? Math.round(metric.value * 10) : metric.value
  const raw = useCountUp(scaledTarget, run, 1100)
  const display = isDecimal ? (raw / 10).toFixed(1) : String(raw)
  return (
    <>
      {metric.prefix}
      {display}
      {metric.suffix}
    </>
  )
}

export default function AgentsScene({
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
  const armGlow = useTransform(scrollYProgress, [SCENE_START, SCENE_START + 0.05], [0, 1])
  const verifyGlow = useTransform(scrollYProgress, [VERIFY_START, VERIFY_START + 0.005], [0, 1])
  const flags = useAgentsFlags(scrollYProgress)
  const armsEngaged = flags.arms || flags.waste || flags.repair
  const wasteActive = flags.waste
  const repairActive = flags.repair
  const leftMetricReady = flags.restoreSettled
  const rightMetricReady = flags.stabilizeSettled

  return (
    <m.div className="eiq-cine__scene eiq-cine__scene--agents" style={{ opacity }}>
      <m.div className="eiq-cine__arm-glow eiq-cine__arm-glow--left" style={{ opacity: armGlow }} aria-hidden="true" />
      <m.div className="eiq-cine__arm-glow eiq-cine__arm-glow--right" style={{ opacity: armGlow }} aria-hidden="true" />

      <ArmEngagement scrollYProgress={scrollYProgress} active={armsEngaged} />
      <WasteRestoration scrollYProgress={scrollYProgress} active={wasteActive} />
      <RepairSequence scrollYProgress={scrollYProgress} active={repairActive} />

      <div
        className="eiq-cine__verify-badge"
        style={{ left: pct(VERIFY_BADGE.x, CANVAS_W), top: pct(VERIFY_BADGE.y, CANVAS_H) }}
        aria-hidden="true"
      >
        <m.span className="eiq-cine__verify-glow" style={{ opacity: verifyGlow }} />
        <span className={`eiq-cine__verify-pulse${flags.verify ? ' is-active' : ''}`} />
      </div>

      <div className="eiq-cine__metric-panel eiq-cine__metric-panel--left">
        <m.div
          className="eiq-cine__metric-item"
          variants={popIn({ duration: 0.4 }, 0.85)}
          initial="hidden"
          animate={leftMetricReady ? 'show' : 'hidden'}
        >
          <span className="eiq-cine__metric-label">{stewardship.left.label.toUpperCase()}</span>
          <span className="eiq-cine__metric-value">
            <MetricValue metric={stewardship.left} run={leftMetricReady} />
          </span>
        </m.div>
      </div>
      <div className="eiq-cine__metric-panel eiq-cine__metric-panel--right">
        <m.div
          className="eiq-cine__metric-item"
          variants={popIn({ duration: 0.4 }, 0.85)}
          initial="hidden"
          animate={rightMetricReady ? 'show' : 'hidden'}
        >
          <span className="eiq-cine__metric-label">{stewardship.right.label.toUpperCase()}</span>
          <span className="eiq-cine__metric-value">
            <MetricValue metric={stewardship.right} run={rightMetricReady} />
          </span>
        </m.div>
      </div>

      <div className="eiq-cine__scene-head">
        <p className="eiq-cine__scene-copy">{agents.copy}</p>
      </div>

      {AGENT_POSITIONS.map((point, i) => (
        <m.div
          key={agents.roster[i]}
          className="eiq-cine__agent-label"
          style={{ left: pct(point.x, 1600), top: pct(point.y, 900) }}
          variants={popIn({ duration: 0.4, delay: i * 0.08 }, 0.85)}
          initial="hidden"
          animate={isActive ? 'show' : 'hidden'}
        >
          <m.span
            className="eiq-cine__agent-dot"
            initial={{ scale: 0.6, opacity: 0.5 }}
            animate={isActive ? { scale: [0.6, 1.15, 1], opacity: 1 } : { scale: 0.6, opacity: 0.5 }}
            transition={{ duration: 0.5, delay: i * 0.08 }}
          />
          <span>{agents.roster[i]}</span>
        </m.div>
      ))}
    </m.div>
  )
}
