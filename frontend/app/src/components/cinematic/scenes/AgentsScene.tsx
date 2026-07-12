/**
 * AgentsScene — Scene 3 (29–43%). Five agent labels stagger in around the
 * central visual via the shared `popIn` preset, each with a small status
 * node. The robotic arms get a restrained overlay glow (opacity only) rather
 * than any transform on the source image itself.
 *
 * Sub-staged via AGENTS_SUB_RANGES: rotation begins early, arms engage in
 * the middle (and stay engaged through repair), repair activates late and
 * settles before the 0.43 release into Pillars. `phase` is a small discrete
 * state derived from scroll position — needed because the bounded CSS
 * pulses (arm engagement, repair targets) are gated by a boolean class
 * toggle, not a continuous scroll value.
 */
import { m, useTransform, useMotionValueEvent, type MotionValue } from 'framer-motion'
import { useState } from 'react'
import { popIn } from '../../../motion'
import { agents } from '../content'
import { AGENTS_SUB_RANGES } from '../sceneRanges'
import ArmEngagement from './ArmEngagement'
import RepairSequence from './RepairSequence'

const SCENE_START = 0.29
const SCENE_END = 0.43

type Phase = 'idle' | 'rotation' | 'arms' | 'repair'

function useAgentsPhase(scrollYProgress: MotionValue<number>): Phase {
  const [phase, setPhase] = useState<Phase>('idle')
  useMotionValueEvent(scrollYProgress, 'change', (v) => {
    let next: Phase = 'idle'
    if (v >= AGENTS_SUB_RANGES.repair[0]) next = 'repair'
    else if (v >= AGENTS_SUB_RANGES.arms[0]) next = 'arms'
    else if (v >= AGENTS_SUB_RANGES.rotation[0]) next = 'rotation'
    setPhase((prev) => (prev === next ? prev : next))
  })
  return phase
}

// Points in the same virtual 1600×900 canvas as EvidenceScene.
const POSITIONS = [
  { x: 300, y: 380 }, // near the left robotic arm
  { x: 620, y: 250 },
  { x: 860, y: 200 }, // near the globe
  { x: 1100, y: 250 },
  { x: 1350, y: 380 }, // near the right robotic arm
]

function pct(v: number, span: number) {
  return `${(v / span) * 100}%`
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
  const phase = useAgentsPhase(scrollYProgress)
  const armsEngaged = phase === 'arms' || phase === 'repair'
  const repairActive = phase === 'repair'

  return (
    <m.div className="eiq-cine__scene eiq-cine__scene--agents" style={{ opacity }}>
      <m.div className="eiq-cine__arm-glow eiq-cine__arm-glow--left" style={{ opacity: armGlow }} aria-hidden="true" />
      <m.div className="eiq-cine__arm-glow eiq-cine__arm-glow--right" style={{ opacity: armGlow }} aria-hidden="true" />

      <ArmEngagement scrollYProgress={scrollYProgress} active={armsEngaged} />
      <RepairSequence scrollYProgress={scrollYProgress} active={repairActive} />

      <div className="eiq-cine__scene-head">
        <p className="eiq-cine__scene-copy">{agents.copy}</p>
      </div>

      {POSITIONS.map((point, i) => (
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
